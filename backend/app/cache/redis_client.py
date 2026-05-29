from typing import Any

import redis.asyncio as redis_asyncio
from redis.asyncio import Redis

from app.core.config import get_settings

_client: "Redis[Any] | None" = None


def get_redis() -> "Redis[Any]":
    """Process-wide Redis client. Initialized lazily; closed in app lifespan."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis_asyncio.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()  # type: ignore[attr-defined]
        _client = None


__all__: list[str] = ["Redis", "close_redis", "get_redis"]
