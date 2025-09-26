from __future__ import annotations

import logging
import asyncio
from typing import Optional, Tuple
import json


from app.db.database import get_supabase_client
from app.db.redis_client import get_redis_client, NEWS_SUMMARIZATION_QUEUE, FAILED_SUMMARIZATION_QUEUE
from app.utils.content_extractor import extract_article_content, summarize_with_llm

logger = logging.getLogger(__name__)

RATE_LIMIT_DELAY = float(__import__('os').environ.get('LLM_RATE_LIMIT_DELAY', 2.0))  # seconds between requests

MAX_RETRY_ATTEMPTS = int(__import__('os').environ.get('MAX_RETRY_ATTEMPTS', 3))
FAILED_QUEUE_TTL = int(__import__('os').environ.get('FAILED_QUEUE_TTL', 3600))  # TTL in seconds for failed items

class AsyncLLMRateLimiter:
    """
    Global rate limiter to ensure Groq RPM compliance across concurrent tasks.
    Enforces a minimum interval between LLM requests (e.g., 2.0s => ~30 RPM).
    """
    def __init__(self, min_interval: float = 2.0):
        self._min_interval = float(min_interval)
        self._lock = asyncio.Lock()
        self._last_ts = 0.0

    async def acquire(self):
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            delta = now - self._last_ts
            if delta < self._min_interval:
                await asyncio.sleep(self._min_interval - delta)
            self._last_ts = loop.time()

class SummarizerWorker:
    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self.supabase = None
        self.redis_client = None
        # Create per-run rate limiter (avoid cross-loop asyncio.Lock reuse)
        self.rate_limiter: Optional[AsyncLLMRateLimiter] = None

    async def initialize(self):
        """Initialize database and Redis connections."""
        self.supabase = await get_supabase_client()
        self.redis_client = await get_redis_client()
        # Initialize limiter within the current event loop
        self.rate_limiter = AsyncLLMRateLimiter(min_interval=RATE_LIMIT_DELAY)

    async def get_next_task(self) -> Optional[Tuple[str, int]]:
        """
        Get the highest priority task from the queue.
        Returns (news_id, score) or None if queue is empty.
        """
        try:
            result = await self.redis_client.zpopmax(NEWS_SUMMARIZATION_QUEUE, count=1)
            if not result:
                return None

            if isinstance(result, list):
                member_score_pairs = result
            elif isinstance(result, dict):
                member_score_pairs = list(result.items())
            else:
                member_score_pairs = []

            if member_score_pairs:
                news_id, score = member_score_pairs[0]
                try:
                    score_val = float(score)
                except Exception:
                    score_val = 0.0
                return news_id, int(score_val)

            return None
        except Exception as e:
            logger.error(f"Error getting next task from queue: {e}")
            return None

    async def update_news_summary(self, news_id: str, summary: str) -> bool:
        """
        Update the summary field of a news item in the database.
        """
        try:
            response = self.supabase.table("news").update({"summary": summary}).eq("id", news_id).execute()
            logger.info(f"Updated summary for news item {news_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating summary for news item {news_id}: {e}")
            return False

    async def delete_news_item(self, news_id: str) -> bool:
        """
        Delete a news item from the database by ID.
        Removes incomplete/failed records to keep the DB clean.
        """
        try:
            self.supabase.table("news").delete().eq("id", news_id).execute()
            logger.info(f"Deleted news item {news_id} from database")
            return True
        except Exception as e:
            logger.error(f"Error deleting news item {news_id}: {e}")
            return False

    async def add_to_failed_queue(self, news_id: str, score: int, attempt: int = 1):
        """
        Add a news item to the failed queue for retry later.
        """
        try:
            attempt_data = json.dumps({"score": score, "attempts": attempt})
            await self.redis_client.hset(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id, attempt_data)
            await self.redis_client.zadd(FAILED_SUMMARIZATION_QUEUE, {news_id: score})
            await self.redis_client.expire(FAILED_SUMMARIZATION_QUEUE, FAILED_QUEUE_TTL)
            await self.redis_client.expire(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", FAILED_QUEUE_TTL)
            logger.info(f"Added news item {news_id} to failed queue (attempt #{attempt})")
        except Exception as e:
            logger.error(f"Error adding news item {news_id} to failed queue: {e}")

    async def process_news_item(self, news_id: str, attempt: int = 1) -> bool:
        """
        Process a single news item: extract content, summarize, and update database.
        Returns True if successful, False otherwise.
        """
        try:
            response = self.supabase.table("news").select("url, title").eq("id", news_id).execute()
            items = response.data
            
            if not items:
                logger.error(f"News item {news_id} not found in database")
                return False
            
            item = items[0]
            url = item.get('url')
            title = item.get('title', '')
            
            if not url:
                logger.error(f"News item {news_id} has no URL")
                return False
            
            logger.info(f"Extracting content from {url} (attempt #{attempt})")
            content = await extract_article_content(url)
            
            if not content:
                logger.warning(f"No content extracted from {url}")
                await self.delete_news_item(news_id)
                return True
            
            logger.info(f"Summarizing content for news item {news_id} (attempt #{attempt})")
            # Acquire per-run limiter tied to the current event loop
            if not self.rate_limiter:
                self.rate_limiter = AsyncLLMRateLimiter(min_interval=RATE_LIMIT_DELAY)
            await self.rate_limiter.acquire()
            summary = await summarize_with_llm(content, title)
            
            # If summarization failed or produced placeholder, delete the row immediately
            placeholder = "No content available for summarization"
            if not summary or (isinstance(summary, str) and summary.strip().lower() == placeholder.lower()):
                if not summary:
                    logger.error(f"Failed to generate summary for news item {news_id} (attempt #{attempt})")
                else:
                    logger.warning(f"Summary is placeholder for news item {news_id}; deleting row")
                await self.delete_news_item(news_id)
                return True
            
            success = await self.update_news_summary(news_id, summary)
            if success:
                logger.info(f"Successfully processed news item {news_id} (attempt #{attempt})")
            else:
                logger.error(f"Failed to update summary in database for news item {news_id} (attempt #{attempt})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing news item {news_id} (attempt #{attempt}): {e}")
            try:
                await self.delete_news_item(news_id)
            except Exception:
                pass
            return True

    async def retry_failed_items(self):
        """
        Move items from the failed queue back to the main queue if they haven't exceeded max attempts.
        """
        try:
            failed_items = await self.redis_client.zrange(FAILED_SUMMARIZATION_QUEUE, 0, -1, withscores=True)
            
            for news_id, score in failed_items:
                attempts_data = await self.redis_client.hget(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
                if attempts_data:
                    attempts_info = json.loads(attempts_data)
                    attempts = attempts_info.get("attempts", 1)
                    
                    if attempts < MAX_RETRY_ATTEMPTS:
                        new_score = score - 5  # Reduce score for retry
                        await self.redis_client.zadd(NEWS_SUMMARIZATION_QUEUE, {news_id: new_score})
                        await self.redis_client.zrem(FAILED_SUMMARIZATION_QUEUE, news_id)
                        await self.redis_client.hdel(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
                        logger.info(f"Moved news item {news_id} back to main queue for retry #{attempts + 1}")
                    else:
                        logger.info(f"Max retry attempts reached for news item {news_id}. Removing from failed queue.")
                        await self.redis_client.zrem(FAILED_SUMMARIZATION_QUEUE, news_id)
                        await self.redis_client.hdel(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
                else:
                    await self.redis_client.zadd(NEWS_SUMMARIZATION_QUEUE, {news_id: score - 5})
                    await self.redis_client.zrem(FAILED_SUMMARIZATION_QUEUE, news_id)
                    logger.info(f"Re-queued unknown news item {news_id} to main queue")
                    
        except Exception as e:
            logger.error(f"Error processing failed queue for retries: {e}")

    async def run(self):
        """
        Main loop of the worker - continuously process tasks from the queue.
        """
        logger.info("Starting summarizer worker...")
        
        await self.initialize()
        
        retry_check_counter = 0
        retry_check_interval = 10  # Check for retries every 10 iterations
        
        while True:
            try:
                retry_check_counter += 1
                if retry_check_counter >= retry_check_interval:
                    await self.retry_failed_items()
                    retry_check_counter = 0
                
                task = await self.get_next_task()
                
                if not task:
                    logger.debug("No tasks in queue, waiting...")
                    await asyncio.sleep(5)
                    continue
                
                news_id, score = task
                attempts_data = await self.redis_client.hget(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
                attempt = 1
                if attempts_data:
                    attempts_info = json.loads(attempts_data)
                    attempt = attempts_info.get("attempts", 1) + 1  # Next attempt number
                
                logger.info(f"Processing news item {news_id} with priority score {score} (attempt #{attempt})")
                
                success = await self.process_news_item(news_id, attempt=attempt)
                
                await self.redis_client.hdel(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
                
            except Exception as e:
                logger.error(f"Error in summarizer worker main loop: {e}")
                await asyncio.sleep(5)

    async def run_once(self) -> int:
        """
        Process up to max_concurrent tasks and return the count of processed items.
        Uses concurrent tasks to overlap content fetching and DB I/O, while a global
        LLM RPM limiter ensures Groq rate limits are respected.
        """
        logger.info("Processing a single batch of summarization tasks...")
        await self.initialize()

        processed_count = 0

        batch: list[tuple[str, int]] = []
        for _ in range(self.max_concurrent):
            task = await self.get_next_task()
            if not task:
                break
            batch.append(task)

        if not batch:
            logger.debug("No more tasks in queue")
            return 0

        async def process_one(news_id: str, score: int) -> bool:
            attempts_data = await self.redis_client.hget(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
            attempt = 1
            if attempts_data:
                attempts_info = json.loads(attempts_data)
                attempt = attempts_info.get("attempts", 1) + 1

            logger.info(f"Processing news item {news_id} with priority score {score} (attempt #{attempt})")
            success = await self.process_news_item(news_id, attempt=attempt)
            await self.redis_client.hdel(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
            return success

        results = await asyncio.gather(*(process_one(nid, sc) for nid, sc in batch), return_exceptions=False)
        processed_count = sum(1 for ok in results if ok)

        logger.info(f"Completed batch processing. Processed {processed_count} items.")
        return processed_count


