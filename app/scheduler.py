from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from app.crawler.spider import crawl_default_sources, crawl_sources
from app.prioritizer import prioritize_news
from app.workers.summarizer_worker import SummarizerWorker

logger = logging.getLogger(__name__)


async def run_crawl_job(max_concurrent: int = 3, domains: Optional[List[str]] = None) -> int:
    """
    Run the crawl job against default sources or a provided list of domains.
    Returns the number of items upserted.
    """
    if domains:
        logger.info("Starting crawl job for domains=%s with concurrency=%d", domains, max_concurrent)
        count = await crawl_sources(domains, max_concurrent=max_concurrent)
    else:
        logger.info("Starting crawl job for default sources with concurrency=%d", max_concurrent)
        count = await crawl_default_sources(max_concurrent=max_concurrent)
    
    logger.info("Running prioritizer after crawl...")
    await prioritize_news()
    # Ensure any rows with NULL category are removed immediately after crawl
    try:
        from app.db.crud import delete_category_null  # type: ignore
        deleted_null = await delete_category_null()
        logger.info("Removed %d rows with NULL category after crawl", deleted_null)
    except Exception as e:
        logger.warning("Failed to delete rows with NULL category after crawl: %s", e)
    
    return count




async def run_prioritizer() -> int:
    """
    Run the prioritizer to score and queue unprocessed news items.
    Returns the number of items added to the queue.
    """
    logger.info("Starting prioritizer job...")
    return await prioritize_news()


async def run_summarizer(max_concurrent: int = 1, batch_mode: bool = True) -> int:
    """
    Run the summarizer worker for a single batch or continuously.
    If batch_mode is True, process a single batch and return.
    If batch_mode is False, run continuously (should be used with caution).
    Returns the number of items processed if in batch mode, or 0 if in continuous mode.
    """
    logger.info("Starting summarizer job...")
    worker = SummarizerWorker(max_concurrent=max_concurrent)
    
    if batch_mode:
        count = await worker.run_once()
        return count
    else:
        await worker.run()
        return 0  # This line won't be reached due to the infinite loop in worker.run()


async def run_cleanup_job(days: int = 30, by_publish_date: bool = False) -> int:
    """
    Delete news older than `days`.
    If by_publish_date is True, compares publish_date; otherwise compares crawl_date.
    Returns number of rows deleted.
    """
    logger.info(
        "Starting cleanup job: days=%d, by_publish_date=%s",
        days,
        by_publish_date,
    )
    
    from app.db.crud import delete_older_than  # type: ignore
    
    deleted = await delete_older_than(days=days, by_publish_date=by_publish_date)
    logger.info("Cleanup job completed: deleted=%d", deleted)
    return deleted


