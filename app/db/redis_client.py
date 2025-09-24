from __future__ import annotations

import os
from typing import Optional
from redis.asyncio import Redis
from dotenv import load_dotenv

# Load environment variables from .env if present (useful for local dev)
load_dotenv()

_redis_client: Optional[Redis] = None


def _get_redis_client() -> Redis:
    """
    Create and return a Redis client.
    Raises RuntimeError if required environment variables are missing.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379")
    
    _redis_client = Redis.from_url(redis_url, decode_responses=True)
    return _redis_client


async def get_redis_client() -> Redis:
    """
    Return the Redis client.
    """
    return _get_redis_client()


async def close_redis_client() -> None:
    """
    Close the Redis client connection.
    """
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


# Queue name constants
NEWS_SUMMARIZATION_QUEUE = "news_summarization_queue"
FAILED_SUMMARIZATION_QUEUE = "failed_summarization_queue"