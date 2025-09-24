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

    # Check for Redis Cloud configuration first, then default
    redis_host = os.environ.get("REDIS_HOST", "redis-12045.crce185.ap-seast-1-1.ec2.redns.redis-cloud.com")
    redis_port = os.environ.get("REDIS_PORT", "12045")
    redis_password = os.environ.get("REDIS_PASSWORD", "")
    
    # If REDIS_URL is set, use it (for Render deployment)
    redis_url = os.environ.get("REDIS_URL", f"redis://:{redis_password}@{redis_host}:{redis_port}")
    
    if redis_password and f"://" in redis_url and not "@@" in redis_url:
        # If we have a password but it's not in the URL, create the URL with password
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"
    
    _redis_client = Redis.from_url(redis_url, decode_responses=True, health_check_interval=30)
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