"""Per-API-key sliding-window rate limiter backed by Redis.

Implementation:
    Each API key has a sorted set keyed by `ogw:rl:<api_key_id>`. Each request is added with
    score=timestamp_ms. Before counting, we drop entries older than `window_seconds`. If
    the resulting cardinality exceeds the limit, we reject. A TTL of (window + 5s) keeps the
    sorted set bounded if a key goes quiet.

    Sliding window is preferred over fixed-window because it avoids the well-known
    burst-at-the-boundary problem where a client can fire 2*limit calls in 2 seconds by
    hitting the boundary of two adjacent windows.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from redis.asyncio import Redis

from app.cache.redis_client import get_redis
from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.monitoring import metrics as m

WINDOW_SECONDS = 60


def _key(api_key_id: uuid.UUID) -> str:
    return f"ogw:rl:{api_key_id}"


async def enforce_rate_limit(api_key_id: uuid.UUID) -> None:
    """Raise RateLimitError if the API key has exceeded RPM in the trailing 60s."""
    settings = get_settings()
    limit = settings.rate_limit_rpm
    if limit <= 0:
        return

    redis = get_redis()
    now_ms = int(time.time() * 1000)
    window_start = now_ms - WINDOW_SECONDS * 1000
    key = _key(api_key_id)

    # Pipeline: prune old entries, count current, add new, expire.
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    # Use a unique member so simultaneous adds at the same millisecond don't collapse.
    member = f"{now_ms}-{uuid.uuid4().hex[:8]}"
    pipe.zadd(key, {member: now_ms})
    pipe.expire(key, WINDOW_SECONDS + 5)
    _, current_count, _, _ = await pipe.execute()

    # `current_count` was taken BEFORE the new add, so the effective count is +1.
    if int(current_count) >= limit:
        # Roll back the speculative add — we shouldn't penalize the rejected request.
        await redis.zrem(key, member)
        m.rate_limit_rejections_total.labels(api_key_id=str(api_key_id)).inc()
        retry_after = await _seconds_until_retry(redis, key, now_ms)
        raise RateLimitError(
            f"Rate limit exceeded ({limit} requests/min).",
            detail={"retry_after_seconds": retry_after},
        )


async def _seconds_until_retry(redis: Redis[Any], key: str, now_ms: int) -> int:
    """Approximate seconds until the oldest in-window request falls off."""
    oldest = await redis.zrange(key, 0, 0, withscores=True)
    if not oldest:
        return 1
    oldest_score = int(oldest[0][1])
    expires_at = oldest_score + WINDOW_SECONDS * 1000
    return max(1, (expires_at - now_ms) // 1000)
