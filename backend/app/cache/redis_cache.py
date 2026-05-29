"""Typed cache facade over Redis for chat completion responses."""
from __future__ import annotations

from typing import Any

import orjson

from app.cache.redis_client import get_redis
from app.core.config import get_settings


async def get_json(key: str) -> Any | None:
    raw = await get_redis().get(key)
    if raw is None:
        return None
    try:
        return orjson.loads(raw)
    except orjson.JSONDecodeError:
        return None


async def set_json(key: str, value: Any, ttl: int | None = None) -> None:
    payload = orjson.dumps(value).decode("utf-8")
    expire = ttl if ttl is not None else get_settings().cache_ttl_seconds
    await get_redis().set(key, payload, ex=expire)


def should_cache(temperature: float) -> bool:
    """Skip caching for high-temperature requests since output isn't deterministic."""
    return temperature <= get_settings().cache_max_temperature
