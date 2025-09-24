from __future__ import annotations

import logging
import asyncio
import time
from typing import Dict, Optional, Tuple
from uuid import UUID
import json

import httpx
from redis.asyncio import Redis

from app.db.database import get_supabase_client
from app.db.redis_client import get_redis_client, NEWS_SUMMARIZATION_QUEUE, FAILED_SUMMARIZATION_QUEUE
from app.utils.content_extractor import extract_article_content, summarize_with_llm

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_DELAY = float(__import__('os').environ.get('LLM_RATE_LIMIT_DELAY', 1.0))  # seconds between requests

# Retry configuration
MAX_RETRY_ATTEMPTS = int(__import__('os').environ.get('MAX_RETRY_ATTEMPTS', 3))
FAILED_QUEUE_TTL = int(__import__('os').environ.get('FAILED_QUEUE_TTL', 3600))  # TTL in seconds for failed items


class SummarizerWorker:
    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self.supabase = None
        self.redis_client = None

    async def initialize(self):
        """Initialize database and Redis connections."""
        self.supabase = await get_supabase_client()
        self.redis_client = await get_redis_client()

    async def get_next_task(self) -> Optional[Tuple[str, int]]:
        """
        Get the highest priority task from the queue.
        Returns (news_id, score) or None if queue is empty.
        """
        try:
            # Get the member with the highest score (ZPOPMAX returns the member with the highest score)
            result = await self.redis_client.zpopmax(NEWS_SUMMARIZATION_QUEUE, count=1)
            if result:
                # result is a list of tuples [(member, score)], we want the first one
                member_score_pairs = list(result.items())
                if member_score_pairs:
                    news_id, score = member_score_pairs[0]
                    return news_id, int(score)
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

    async def add_to_failed_queue(self, news_id: str, score: int, attempt: int = 1):
        """
        Add a news item to the failed queue for retry later.
        """
        try:
            # Store the attempt count in the value along with the score
            attempt_data = json.dumps({"score": score, "attempts": attempt})
            await self.redis_client.hset(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id, attempt_data)
            await self.redis_client.zadd(FAILED_SUMMARIZATION_QUEUE, {news_id: score})
            # Set TTL for the failed queue item
            await self.redis_client.expire(FAILED_SUMMARIZATION_QUEUE, FAILED_QUEUE_TTL)
            await self.redis_client.expire(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", FAILED_QUEUE_TTL)
            logger.info(f"Added news item {news_id} to failed queue (attempt #{attempt})")
        except Exception as e:
            logger.error(f"Error adding news item {news_id} to failed queue: {e}")

    async def retry_failed_items(self):
        """
        Move items from the failed queue back to the main queue if they haven't exceeded max attempts.
        """
        try:
            # Get all items in the failed queue
            failed_items = await self.redis_client.zrange(FAILED_SUMMARIZATION_QUEUE, 0, -1, withscores=True)
            
            for news_id, score in failed_items:
                # Get the attempt count
                attempts_data = await self.redis_client.hget(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
                if attempts_data:
                    attempts_info = json.loads(attempts_data)
                    attempts = attempts_info.get("attempts", 1)
                    
                    if attempts < MAX_RETRY_ATTEMPTS:
                        # Move the item back to the main queue with a lower score
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
                    # If we can't find attempt data, try it once more before removing
                    await self.redis_client.zadd(NEWS_SUMMARIZATION_QUEUE, {news_id: score - 5})
                    await self.redis_client.zrem(FAILED_SUMMARIZATION_QUEUE, news_id)
                    logger.info(f"Re-queued unknown news item {news_id} to main queue")
                    
        except Exception as e:
            logger.error(f"Error processing failed queue for retries: {e}")

    async def process_news_item(self, news_id: str, attempt: int = 1) -> bool:
        """
        Process a single news item: extract content, summarize, and update database.
        Returns True if successful, False otherwise.
        """
        try:
            # Fetch the news item from database to get the URL
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
            
            # Extract content from the article
            logger.info(f"Extracting content from {url} (attempt #{attempt})")
            content = await extract_article_content(url)
            
            if not content:
                logger.warning(f"No content extracted from {url}")
                # If no content could be extracted, update with a notice instead of failing
                return await self.update_news_summary(news_id, "No content available for summarization")
            
            # Rate limiting - sleep before making API call
            logger.debug(f"Rate limiting: sleeping for {RATE_LIMIT_DELAY} seconds")
            await asyncio.sleep(RATE_LIMIT_DELAY)
            
            # Generate summary using LLM
            logger.info(f"Summarizing content for news item {news_id} (attempt #{attempt})")
            summary = await summarize_with_llm(content, title)
            
            if not summary:
                logger.error(f"Failed to generate summary for news item {news_id} (attempt #{attempt})")
                return False
            
            # Update the database with the summary
            success = await self.update_news_summary(news_id, summary)
            if success:
                logger.info(f"Successfully processed news item {news_id} (attempt #{attempt})")
            else:
                logger.error(f"Failed to update summary in database for news item {news_id} (attempt #{attempt})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing news item {news_id} (attempt #{attempt}): {e}")
            return False

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
                # Periodically move failed items back to the main queue
                retry_check_counter += 1
                if retry_check_counter >= retry_check_interval:
                    await self.retry_failed_items()
                    retry_check_counter = 0
                
                # Get the next highest priority task
                task = await self.get_next_task()
                
                if not task:
                    logger.debug("No tasks in queue, waiting...")
                    # Wait before checking again
                    await asyncio.sleep(5)
                    continue
                
                news_id, score = task
                # Get attempt count for this item if it's from the failed queue
                attempts_data = await self.redis_client.hget(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
                attempt = 1
                if attempts_data:
                    attempts_info = json.loads(attempts_data)
                    attempt = attempts_info.get("attempts", 1) + 1  # Next attempt number
                
                logger.info(f"Processing news item {news_id} with priority score {score} (attempt #{attempt})")
                
                # Process the news item
                success = await self.process_news_item(news_id, attempt=attempt)
                
                if not success:
                    # If processing failed, add back to the failed queue with updated attempt count
                    await self.add_to_failed_queue(news_id, score, attempt=attempt)
                else:
                    # If successful, remove from failed attempts if it was there
                    await self.redis_client.hdel(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
                
            except Exception as e:
                logger.error(f"Error in summarizer worker main loop: {e}")
                # Wait a bit before continuing to avoid a tight error loop
                await asyncio.sleep(5)

    async def run_once(self) -> int:
        """
        Process a single batch of tasks and return the count of processed items.
        """
        logger.info("Processing a single batch of summarization tasks...")
        
        await self.initialize()
        
        processed_count = 0
        
        # Process up to max_concurrent tasks in parallel
        for _ in range(self.max_concurrent):
            # Get the next highest priority task
            task = await self.get_next_task()
            
            if not task:
                logger.debug("No more tasks in queue")
                break
            
            news_id, score = task
            # Get attempt count for this item if it's from the failed queue
            attempts_data = await self.redis_client.hget(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
            attempt = 1
            if attempts_data:
                attempts_info = json.loads(attempts_data)
                attempt = attempts_info.get("attempts", 1) + 1  # Next attempt number
            
            logger.info(f"Processing news item {news_id} with priority score {score} (attempt #{attempt})")
            
            # Process the news item
            success = await self.process_news_item(news_id, attempt=attempt)
            
            if success:
                processed_count += 1
                # If successful, remove from failed attempts if it was there
                await self.redis_client.hdel(f"{FAILED_SUMMARIZATION_QUEUE}:attempts", news_id)
            else:
                # If processing failed, add back to the failed queue with updated attempt count
                await self.add_to_failed_queue(news_id, score, attempt=attempt)
        
        logger.info(f"Completed batch processing. Processed {processed_count} items.")
        return processed_count


if __name__ == "__main__":
    # This allows running the worker as a standalone script
    worker = SummarizerWorker()
    asyncio.run(worker.run())