from __future__ import annotations

from datetime import datetime, date, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl, Field
from app.scheduler import run_crawl_job, run_cleanup_job, run_prioritizer, run_summarizer

router = APIRouter(prefix="/news", tags=["news"])


class NewsItemOut(BaseModel):
    id: str = Field(..., description="Unique identifier of the news item")
    title: str
    url: HttpUrl
    summary: Optional[str] = None
    source: str
    category: Optional[str] = None
    publish_date: Optional[datetime] = None
    crawl_date: datetime
    content_hash: Optional[str] = None


class NewsListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[NewsItemOut]


# Try to import real DB-backed CRUD; fall back to in-memory sample dataset if unavailable
HAVE_DB = False
try:
    from app.db.crud import (  # type: ignore
        fetch_news,
        fetch_news_by_id,
        count_news,
    )

    HAVE_DB = True
except Exception:
    HAVE_DB = False

    _NOW = datetime.now(timezone.utc)
    _FAKE_DATA: List[dict] = [
        {
            "id": str(uuid4()),
            "title": "Kompas: Ekonomi Indonesia Tumbuh 5%",
            "url": "https://www.kompas.com/ekonomi/read/2025/09/23/ekonomi-indonesia",
            "summary": "Pertumbuhan ekonomi mencapai 5% didorong konsumsi rumah tangga.",
            "source": "kompas.com",
            "category": "ekonomi",
            "publish_date": _NOW,
            "crawl_date": _NOW,
            "content_hash": "fakehash-1",
        },
        {
            "id": str(uuid4()),
            "title": "Detik: Teknologi AI Kian Marak",
            "url": "https://inet.detik.com/it-business/d-9999999/ai-kian-marak",
            "summary": "Adopsi AI meningkat di berbagai sektor industri.",
            "source": "detik.com",
            "category": "teknologi",
            "publish_date": _NOW,
            "crawl_date": _NOW,
            "content_hash": "fakehash-2",
        },
    ]


@router.get("", response_model=NewsListResponse)
async def list_news(
    q: Optional[str] = Query(None, description="Full-text query on title/summary"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source domain"),
    from_date: Optional[date] = Query(None, description="Publish date from (inclusive)"),
    to_date: Optional[date] = Query(None, description="Publish date to (inclusive)"),
    limit: int = Query(20, ge=1, le=50, description="Max items to return (1-50)"),
    offset: int = Query(0, ge=0, description="Items to skip for pagination"),
) -> NewsListResponse:
    """
    List news with optional filters and pagination.
    """
    if HAVE_DB:
        items: List[NewsItemOut] = await fetch_news(
            q=q,
            category=category,
            source=source,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )
        total: int = await count_news(
            q=q,
            category=category,
            source=source,
            from_date=from_date,
            to_date=to_date,
        )
        return NewsListResponse(total=total, limit=limit, offset=offset, items=items)

    # Fallback in-memory filtering (for development before DB layer is ready)
    data = _FAKE_DATA

    def _match(record: dict) -> bool:
        if q:
            qs = q.lower()
            if qs not in record["title"].lower() and qs not in (record.get("summary") or "").lower():
                return False
        if category and (record.get("category") or "").lower() != category.lower():
            return False
        if source and (record.get("source") or "").lower() != source.lower():
            return False
        if from_date:
            pd: Optional[datetime] = record.get("publish_date")
            if pd and pd.date() < from_date:
                return False
        if to_date:
            pd = record.get("publish_date")
            if pd and pd.date() > to_date:
                return False
        return True

    filtered = [r for r in data if _match(r)]
    total = len(filtered)
    page = filtered[offset : offset + limit]

    items = [NewsItemOut(**r) for r in page]
    return NewsListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/{news_id}", response_model=NewsItemOut)
async def get_news(news_id: str) -> NewsItemOut:
    """
    Retrieve a single news item by ID.
    """
    if HAVE_DB:
        item = await fetch_news_by_id(news_id)
        if item is None:
            raise HTTPException(status_code=404, detail="News not found")
        return item

    for r in _FAKE_DATA:
        if r["id"] == news_id:
            return NewsItemOut(**r)
    raise HTTPException(status_code=404, detail="News not found")


@router.post("/crawl")
async def trigger_crawl(
    concurrency: int = Query(3, ge=1, le=10, description="Max concurrent domains to crawl"),
    domains: Optional[str] = Query(None, description="Comma-separated domain list to crawl (override defaults)"),
):
    """
    Trigger a crawl job manually.
    Example: POST /api/news/crawl?concurrency=3&domains=kompas.com,detik.com
    """
    dom_list = [d.strip() for d in domains.split(",")] if domains else None
    count = await run_crawl_job(max_concurrent=concurrency, domains=dom_list)
    return {"status": "ok", "upserted": count}


@router.post("/cleanup")
async def trigger_cleanup(
    days: int = Query(30, ge=1, le=365, description="Delete items older than N days"),
    by_publish: bool = Query(False, description="Compare by publish_date instead of crawl_date"),
):
    """
    Trigger a cleanup job to delete old news.
    Example: POST /api/news/cleanup?days=30&by_publish=true
    """
    # Lazy import to avoid module import errors if DB isn't configured during app startup
    from app.db.crud import delete_older_than  # type: ignore

    deleted = await delete_older_than(days=days, by_publish_date=by_publish)
    return {"status": "ok", "deleted": deleted}


@router.post("/prioritize")
async def trigger_prioritize():
    """
    Trigger the prioritizer to score and queue unprocessed news items.
    """
    count = await run_prioritizer()
    return {"status": "ok", "queued": count}


@router.post("/summarize")
async def trigger_summarize(
    concurrency: int = Query(1, ge=1, le=5, description="Max concurrent summarization tasks"),
    batch: bool = Query(True, description="Run in batch mode (True) or continuous mode (False)")
):
    """
    Trigger the summarizer to process news items in the queue.
    In batch mode, process a single batch and return.
    In continuous mode, run indefinitely (typically used in a separate process).
    """
    count = await run_summarizer(max_concurrent=concurrency, batch_mode=batch)
    if batch:
        return {"status": "ok", "processed": count}
    else:
        return {"status": "ok", "message": "Started continuous summarization worker"}


__all__ = ["router"]