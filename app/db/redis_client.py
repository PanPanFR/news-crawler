from __future__ import annotations

import os
from typing import Optional
from redis.asyncio import Redis
from dotenv import load_dotenv

load_dotenv()

_redis_client: Optional[Redis] = None


def _get_redis_client() -> Redis:
    """
    Create and return a Redis client.
    For local development, uses REDIS_URL (default: redis://localhost:6379)
    For Redis Cloud, uses REDIS_HOST, REDIS_PORT, and REDIS_PASSWORD
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_host = os.environ.get("REDIS_HOST")
    redis_port = os.environ.get("REDIS_PORT")
    redis_password = os.environ.get("REDIS_PASSWORD")
    
    if redis_host and redis_port:
        if redis_password:
            redis_url = f"rediss://:{redis_password}@{redis_host}:{redis_port}"
        else:
            redis_url = f"rediss://{redis_host}:{redis_port}"
    else:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    
    _redis_client = Redis.from_url(
        redis_url, 
        decode_responses=True, 
        health_check_interval=30,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True
    )
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


NEWS_SUMMARIZATION_QUEUE = "news_summarization_queue"
FAILED_SUMMARIZATION_QUEUE = "failed_summarization_queue"