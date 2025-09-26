from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx
import feedparser
from bs4 import BeautifulSoup

from app.crawler.utils import (
    RateLimiter,
    clean_text,
    compute_content_hash,
    domain_from_url,
    fetch_html,
    fetch_text,
    normalize_url,
    parse_feed_datetime,
    to_utc,
)
from app.db.crud import upsert_news

logger = logging.getLogger(__name__)


def default_sources() -> Dict[str, List[str]]:
    """
    Map of domain -> list of RSS feed URLs to try in order.
    Some are heuristics; adjust as needed.
    """
    return {
        "kompas.com": [
            "https://news.kompas.com/rss",
            "https://indeks.kompas.com/rss",
        ],
        "detik.com": [
            "https://rss.detik.com/index.php",
            "https://rss.detik.com/index.php/detikcom",
        ],
        "tempo.co": [
            "https://rss.tempo.co/",
        ],
        "antaranews.com": [
            "https://www.antaranews.com/rss/terkini",
            "https://www.antaranews.com/rss/nasional",
        ],
        "bbc.com": [
            "http://feeds.bbci.co.uk/news/world/rss.xml",
            "http://feeds.bbci.co.uk/news/rss.xml",
        ],
        "cnbcindonesia.com": [
            "https://www.cnbcindonesia.com/rss/",
        ],
        "republika.co.id": [
            "https://www.republika.co.id/rss",
            "https://www.republika.co.id/rss/nasional",
        ],
        "katadata.co.id": [
            "https://katadata.co.id/rss",
        ],
        "theguardian.com": [
            "https://www.theguardian.com/world/rss",
            "https://www.theguardian.com/international/rss",
        ],
        "nytimes.com": [
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        ],
    }


def _feed_guessers(domain: str) -> List[str]:
    """
    Fallback RSS feed guessers if no explicit list succeeded.
    """
    scheme = "https"
    base = f"{scheme}://{domain}"
    return [
        f"{base}/rss",
        f"{base}/feed",
        f"{base}/feeds",
        f"{base}/rss.xml",
        f"{base}/feed.xml",
    ]


def _extract_category(entry: dict) -> Optional[str]:
    """
    Normalize RSS tags into main categories:
    politik, ekonomi, bisnis, teknologi, olahraga, hiburan, kesehatan, internasional, nasional
    """
    try:
        tags = entry.get("tags") or []
        MAIN = {
            "politik": "politik",
            "politics": "politik",
            "pemerintah": "politik",
            "ekonomi": "ekonomi",
            "economy": "ekonomi",
            "bisnis": "bisnis",
            "business": "bisnis",
            "market": "bisnis",
            "keuangan": "bisnis",
            "teknologi": "teknologi",
            "technology": "teknologi",
            "tech": "teknologi",
            "sains": "teknologi",
            "olahraga": "olahraga",
            "sport": "olahraga",
            "hiburan": "hiburan",
            "entertainment": "hiburan",
            "seleb": "hiburan",
            "kesehatan": "kesehatan",
            "health": "kesehatan",
            "internasional": "internasional",
            "world": "internasional",
            "dunia": "internasional",
            "nasional": "nasional",
            "indonesia": "nasional",
        }
        for t in tags:
            term = t.get("term")
            if isinstance(term, str) and term.strip():
                k = term.strip().lower()
                if k in MAIN:
                    return MAIN[k]
                for key in MAIN.keys():
                    if key in k:
                        return MAIN[key]
    except Exception:
        pass
    return None

def _guess_main_category(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    s = text.lower()
    if any(w in s for w in ["pemerintah", "politik", "pilpres", "pemilu", "menteri", "dpr", "presiden"]):
        return "politik"
    if any(w in s for w in ["ekonomi", "bisnis", "pasar", "market", "saham", "rupiah", "harga", "investasi", "apbn", "pajak"]):
        return "bisnis"
    if any(w in s for w in ["teknologi", "ai", "gadget", "aplikasi", "software", "internet", "startup"]):
        return "teknologi"
    if any(w in s for w in ["olahraga", "sport", "liga", "sepak bola", "badminton", "basket", "turnamen"]):
        return "olahraga"
    if any(w in s for w in ["hiburan", "artis", "film", "musik", "konser", "seleb"]):
        return "hiburan"
    if any(w in s for w in ["kesehatan", "vaksin", "rumah sakit", "dokter", "gizi"]):
        return "kesehatan"
    if any(w in s for w in ["dunia", "internasional", "global", "asing", "luar negeri"]):
        return "internasional"
    if any(w in s for w in ["indonesia", "nasional", "jakarta", "provinsi", "kabupaten", "kota"]):
        return "nasional"
    return None


async def _parse_rss_content(text: str, source_domain: str) -> List[dict]:
    parsed = feedparser.parse(text)
    items: List[dict] = []
    now = datetime.now(timezone.utc)

    for e in parsed.entries:
        url = e.get("link")
        title = clean_text(e.get("title"))
        if not url or not title:
            continue

        summary = None
        publish_date = parse_feed_datetime(e)
        if publish_date:
            publish_date = to_utc(publish_date)

        item = {
            "title": title,
            "url": url,
            "summary": None,  # Don't store summaries in crawler - let the summarizer worker handle it
            "source": source_domain,
            "category": (_extract_category(e) or _guess_main_category(title)),
            "publish_date": publish_date,
            "crawl_date": now,
            "content_hash": compute_content_hash(url, title, None),
        }
        items.append(item)
    return items


def _unique_urls(urls: Iterable[str], domain: str, limit: int = 30) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for u in urls:
        try:
            netloc = urlparse(u).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            if netloc and domain not in netloc:
                continue
        except Exception:
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= limit:
            break
    return out


def _html_candidate_links(soup: BeautifulSoup, base_url: str) -> List[Tuple[str, Optional[str]]]:
    """
    Extract candidate article links with optional titles from an HTML document.
    Heuristics: headlines, article anchors, h2/h3 within anchors, data- attributes.
    """
    candidates: List[Tuple[str, Optional[str]]] = []

    for sel in [
        "a[href][data-article-id]",
        "a[href].headline",
        "a[href].article__link",
        "article a[href]",
        "h2 a[href]",
        "h3 a[href]",
        "a[href][aria-label]",
        "a[href][title]",
    ]:
        for a in soup.select(sel):
            href = normalize_url(base_url, a.get("href"))
            if not href:
                continue
            text = clean_text(a.get_text()) or clean_text(a.get("title")) or clean_text(a.get("aria-label"))
            candidates.append((href, text))

    if not candidates:
        for a in soup.find_all("a", href=True):
            href = normalize_url(base_url, a.get("href"))
            if not href:
                continue
            text = clean_text(a.get_text()) or clean_text(a.get("title"))
            candidates.append((href, text))

    return candidates


async def _html_fallback_scrape(client: httpx.AsyncClient, domain: str) -> List[dict]:
    """
    Fallback scraping from homepage when RSS not available.
    This is best-effort and may include noise; adjust selectors per-site for better quality.
    """
    base_url = f"https://{domain}"
    soup = await fetch_html(client, base_url)
    if not soup:
        return []

    cand = _html_candidate_links(soup, base_url)
    uniq = _unique_urls((u for (u, _t) in cand if u), domain, limit=25)
    now = datetime.now(timezone.utc)
    items: List[dict] = []
    for u in uniq:
        title = None
        try:
            page = await fetch_html(client, u, timeout=8.0)
            if page:
                tnode = page.find("meta", property="og:title") or page.find("title")
                if tnode:
                    title = clean_text(tnode.get("content") if tnode.has_attr("content") else tnode.get_text())
        except Exception:
            pass

        if not title:
            try:
                title = next((t for (url, t) in cand if url == u and t), None)
            except Exception:
                title = None

        if not title:
            continue

        summary = None

        items.append(
            {
                "title": title,
                "url": u,
                "summary": None,  # Don't store summaries in crawler - let the summarizer worker handle it
                "source": domain,
                "category": _guess_main_category(title),
                "publish_date": None,
                "crawl_date": now,
                "content_hash": compute_content_hash(u, title, None),
            }
        )
    return items


async def _crawl_domain(client: httpx.AsyncClient, domain: str) -> List[dict]:
    """
    Crawl a single domain using RSS if possible; otherwise fallback to HTML heuristic scraping.
    """
    feeds = default_sources().get(domain, [])
    tried: Set[str] = set()

    async def try_feed(url: str) -> Optional[List[dict]]:
        text = await fetch_text(client, url, timeout=15.0)
        if not text:
            return None
        try:
            items = await _parse_rss_content(text, source_domain=domain)
            if items:
                logger.info("Parsed %d items from RSS %s", len(items), url)
            return items or None
        except Exception as e:
            logger.warning("RSS parse failed for %s: %s", url, e)
            return None

    for f in feeds:
        tried.add(f)
        items = await try_feed(f)
        if items:
            return items

    for f in _feed_guessers(domain):
        if f in tried:
            continue
        items = await try_feed(f)
        if items:
            return items

    logger.info("Falling back to HTML scraping for %s", domain)
    return await _html_fallback_scrape(client, domain)


async def crawl_sources(
    domains: Iterable[str],
    max_concurrent: int = 3,
) -> int:
    """
    Crawl the given list of domains with bounded concurrency.
    Upsert all discovered items into DB.
    Returns number of items processed (upserted).
    """
    limiter = RateLimiter(max_concurrent=max_concurrent)
    count = 0

    limits = httpx.Limits(max_keepalive_connections=max_concurrent, max_connections=max_concurrent * 2)
    async with httpx.AsyncClient(timeout=20.0, limits=limits, headers={"User-Agent": "news-crawler/0.1"}) as client:
        tasks = [limiter.run(_crawl_domain(client, d)) for d in domains]
        for coro in asyncio.as_completed(tasks):
            try:
                items = await coro
            except Exception as e:
                logger.error("Domain crawl error: %s", e)
                continue

            batch_size = 50  # Process up to 50 items at a time
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                # Filter out items without a valid category (skip inserting those)
                batch = [it for it in batch if (it.get("category") or "").strip()]
                
                try:
                    from app.db.crud import upsert_news_batch
                    ids = await upsert_news_batch(batch)
                    count += len(ids)
                except Exception as e:
                    logger.warning("Batch upsert failed, falling back to individual upserts: %s", e)
                    for item in batch:
                        # Skip items without category when falling back to individual upserts
                        if not (item.get("category") or "").strip():
                            continue
                        try:
                            await upsert_news(item)
                            count += 1
                        except Exception as individual_e:
                            logger.warning("Upsert failed for %s: %s", item.get("url"), individual_e)
                            continue

    logger.info("Crawl completed. Processed %d items.", count)
    return count


async def crawl_default_sources(max_concurrent: int = 3) -> int:
    domains = list(default_sources().keys())
    return await crawl_sources(domains, max_concurrent=max_concurrent)