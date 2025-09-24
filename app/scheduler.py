from __future__ import annotations

import asyncio
import logging
import sys
from typing import Iterable, List, Optional

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
    
    # After crawling, run the prioritizer to add new items to the summarization queue
    logger.info("Running prioritizer after crawl...")
    await prioritize_news()
    
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
        # Process a single batch and return
        count = await worker.run_once()
        return count
    else:
        # Run continuously - this should typically be used in a separate process/thread
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
    
    # Lazy import to avoid module import errors if DB isn't configured during app startup
    from app.db.crud import delete_older_than  # type: ignore
    
    deleted = await delete_older_than(days=days, by_publish_date=by_publish_date)
    logger.info("Cleanup job completed: deleted=%d", deleted)
    return deleted


def _print_usage() -> None:
    print(
        \"Usage:\\n\"
        \"  python -m app.scheduler crawl [--concurrency N] [--domains d1,d2,...]\\n\"
        \"  python -m app.scheduler prioritize\\n\"
        \"  python -m app.scheduler summarize [--concurrency N] [--batch]\\n\"
        \"  python -m app.scheduler cleanup [--days N] [--by-publish]\\n\"
        \"\\n\"
        \"Examples:\\n\"
        \"  python -m app.scheduler crawl --concurrency 3\\n\"
        \"  python -m app.scheduler crawl --domains kompas.com,detik.com\\n\"
        \"  python -m app.scheduler prioritize\\n\"
        \"  python -m app.scheduler summarize --concurrency 1 --batch\\n\"
        \"  python -m app.scheduler cleanup --days 30 --by-publish\\n\"
    )


def _parse_args(argv: List[str]) -> int:
    if len(argv) < 2:
        _print_usage()
        return 1

    cmd = argv[1].lower()
    if cmd not in {"crawl", "prioritize", "summarize", "cleanup"}:
        _print_usage()
        return 1

    if cmd == "crawl":
        concurrency = 3
        domains: Optional[List[str]] = None
        i = 2
        while i < len(argv):
            a = argv[i]
            if a == "--concurrency" and i + 1 < len(argv):
                try:
                    concurrency = int(argv[i + 1])
                except ValueError:
                    print("Invalid --concurrency value, must be integer")
                    return 2
                i += 2
                continue
            if a == "--domains" and i + 1 < len(argv):
                domains = [d.strip() for d in argv[i + 1].split(",") if d.strip()]
                i += 2
                continue
            print(f"Unknown argument: {a}")
            return 2

        try:
            count = asyncio.run(run_crawl_job(max_concurrent=concurrency, domains=domains))
            print(f"Crawl completed. upserted={count}")
            return 0
        except Exception as e:
            print(f"Crawl failed: {e}")
            return 3

    elif cmd == "prioritize":
        try:
            count = asyncio.run(run_prioritizer())
            print(f"Prioritization completed. queued={count}")
            return 0
        except Exception as e:
            print(f"Prioritization failed: {e}")
            return 3

    elif cmd == "summarize":
        concurrency = 1
        batch_mode = True  # Default to batch mode
        i = 2
        while i < len(argv):
            a = argv[i]
            if a == "--concurrency" and i + 1 < len(argv):
                try:
                    concurrency = int(argv[i + 1])
                except ValueError:
                    print("Invalid --concurrency value, must be integer")
                    return 2
                i += 2
                continue
            if a == "--batch":
                batch_mode = True
                i += 1
                continue
            if a == "--continuous":
                batch_mode = False
                i += 1
                continue
            print(f"Unknown argument: {a}")
            return 2
        
        try:
            if batch_mode:
                count = asyncio.run(run_summarizer(max_concurrent=concurrency, batch_mode=True))
                print(f"Summarization batch completed. processed={count}")
            else:
                # Continuous mode - run forever
                print("Starting continuous summarization worker...")
                asyncio.run(run_summarizer(max_concurrent=concurrency, batch_mode=False))
            return 0
        except Exception as e:
            print(f"Summarization failed: {e}")
            return 3

    # cleanup
    days = 30
    by_publish = False
    i = 2
    while i < len(argv):
        a = argv[i]
        if a == "--days" and i + 1 < len(argv):
            try:
                days = int(argv[i + 1])
            except ValueError:
                print("Invalid --days value, must be integer")
                return 2
            i += 2
            continue
        if a == "--by-publish":
            by_publish = True
            i += 1
            continue
        print(f"Unknown argument: {a}")
        return 2

    try:
        deleted = asyncio.run(run_cleanup_job(days=days, by_publish_date=by_publish))
        print(f"Cleanup completed. deleted={deleted}")
        return 0
    except Exception as e:
        print(f"Cleanup failed: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(_parse_args(sys.argv))