from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Optional
from uuid import UUID

from app.db.database import get_supabase_client
from app.db.redis_client import get_redis_client, NEWS_SUMMARIZATION_QUEUE

logger = logging.getLogger(__name__)

# Define scoring weights for different factors
SOURCE_SCORES = {
    'kompas.com': 20,
    'detik.com': 20,
    'tempo.co': 20,
    'antaranews.com': 18,
    'bbc.com': 18,
    'cnbcindonesia.com': 18,
    'republika.co.id': 15,
    'katadata.co.id': 15,
    'theguardian.com': 15,
    'nytimes.com': 15,
}

KEYWORD_SCORES = {
    'pemerintah': 10,
    'saham': 10,
    'teknologi': 10,
    'pemilu': 10,
    'ekonomi': 8,
    'kesehatan': 8,
    'olahraga': 5,
    'hiburan': 5,
    'nasional': 8,
    'internasional': 8,
    'politik': 10,
    'bisnis': 8,
    'olahraga': 5,
    'pendidikan': 5,
    'kriminal': 8,
    'cuaca': 3,
    'bencana': 8,
    'corona': 10,
    'vaksin': 10,
}


async def calculate_priority_score(title: str, source: str, publish_date: Optional[str] = None) -> int:
    """
    Calculate priority score for a news item based on source, title keywords, and publish date.
    """
    score = 0

    # Add score based on source
    source_lower = source.lower()
    for src, src_score in SOURCE_SCORES.items():
        if src in source_lower:
            score += src_score
            break

    # Add score based on keywords in title
    title_lower = title.lower()
    for keyword, keyword_score in KEYWORD_SCORES.items():
        if keyword in title_lower:
            score += keyword_score

    # Add score based on recency (newer news gets higher score)
    if publish_date:
        # This is a simplified recency calculation - in production you might want more sophisticated logic
        score += 5  # Base recency score
        
    return score


async def prioritize_news() -> int:
    """
    Fetch news items with NULL summaries from Supabase, calculate priority scores,
    and add them to the Redis priority queue.
    
    Returns the number of items added to the queue.
    """
    logger.info("Starting prioritization process...")
    
    supabase = await get_supabase_client()
    redis_client = await get_redis_client()
    
    # Fetch all news with NULL summary (unprocessed items)
    query_result = supabase.table("news").select("id, title, source, publish_date").eq("summary", None).execute()
    items = query_result.data
    
    if not items:
        logger.info("No news items to prioritize")
        return 0

    logger.info(f"Found {len(items)} news items to prioritize")
    
    prioritized_count = 0
    
    for item in items:
        try:
            # Calculate priority score
            score = await calculate_priority_score(
                title=item['title'],
                source=item['source'],
                publish_date=item.get('publish_date')
            )
            
            # Add to Redis sorted set with priority score
            await redis_client.zadd(NEWS_SUMMARIZATION_QUEUE, {item['id']: score})
            logger.debug(f"Added news item {item['id']} to queue with score {score}")
            
            prioritized_count += 1
            
        except Exception as e:
            logger.error(f"Error processing news item {item.get('id', 'unknown')}: {e}")
            continue
    
    logger.info(f"Prioritization completed. Added {prioritized_count} items to queue.")
    return prioritized_count


if __name__ == "__main__":
    # This allows running the prioritizer as a standalone script
    asyncio.run(prioritize_news())