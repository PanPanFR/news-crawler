from __future__ import annotations

import os
import asyncio
from typing import Optional
from redis.asyncio import Redis
from dotenv import load_dotenv

load_dotenv()

_redis_client: Optional[Redis] = None
_redis_loop: Optional[asyncio.AbstractEventLoop] = None


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
    Return a Redis client bound to the current event loop.
    Recreates the client if called from a different loop to avoid 'Future attached to a different loop'.
    """
    global _redis_client, _redis_loop

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        # Fallback if not in an async context
        current_loop = asyncio.get_event_loop()

    if _redis_client is not None and _redis_loop is current_loop:
        return _redis_client

    # Close previous client if loop changed
    if _redis_client is not None and _redis_loop is not current_loop:
        try:
            await _redis_client.close()
        except Exception:
            pass
        _redis_client = None

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
    _redis_loop = current_loop
    return _redis_client


async def close_redis_client() -> None:
    """
    Close the Redis client connection.
    """
    global _redis_client, _redis_loop
    if _redis_client is not None:
        try:
            await _redis_client.close()
        except Exception:
            pass
        _redis_client = None
    _redis_loop = None


NEWS_SUMMARIZATION_QUEUE = "news_summarization_queue"
FAILED_SUMMARIZATION_QUEUE = "failed_summarization_queue"