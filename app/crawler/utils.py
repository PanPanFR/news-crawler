from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from html import unescape
from time import mktime
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def normalize_url(base_url: str, href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    href = href.strip()
    if href.startswith("javascript:") or href.startswith("#"):
        return None
    try:
        full = urljoin(base_url, href)
        # Drop fragments
        parsed = urlparse(full)
        full = parsed._replace(fragment="").geturl()
        return full
    except Exception:
        return None


def domain_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    s = unescape(text)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def compute_content_hash(*parts: Optional[str]) -> str:
    m = hashlib.sha256()
    for p in parts:
        if p:
            m.update(p.encode("utf-8", errors="ignore"))
            m.update(b"\x00")
    return m.hexdigest()


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_feed_datetime(entry: dict) -> Optional[datetime]:
    # feedparser uses 'published_parsed' or 'updated_parsed' (time.struct_time)
    tm = entry.get("published_parsed") or entry.get("updated_parsed") or None
    if tm:
        try:
            return datetime.fromtimestamp(mktime(tm), tz=timezone.utc)
        except Exception:
            pass
    # fallback iso-like string
    for key in ("published", "updated", "date"):
        val = entry.get(key)
        if isinstance(val, str):
            try:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                return to_utc(dt)
            except Exception:
                continue
    return None


async def fetch_text(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = 15.0,
) -> Optional[str]:
    try:
        r = await client.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        # Prefer text with apparent encoding
        return r.text
    except Exception:
        return None


async def fetch_html(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = 15.0,
) -> Optional[BeautifulSoup]:
    text = await fetch_text(client, url, timeout=timeout)
    if text is None:
        return None
    try:
        return BeautifulSoup(text, "lxml")
    except Exception:
        return None


class RateLimiter:
    """
    Simple asyncio semaphore-based rate limiter to constrain concurrency.
    """

    def __init__(self, max_concurrent: int = 5):
        self._sem = asyncio.Semaphore(max_concurrent)

    async def run(self, coro):
        async with self._sem:
            return await coro