"""Redis-backed session store.

Each session is an opaque high-entropy token issued at login. The cookie value IS the token;
the server-side mapping `session:<token> → user_id` lives in Redis with a sliding TTL.

Why not JWT? Easier revocation (single DEL invalidates the session), no need for a blacklist
table, sliding refresh comes for free, and no client-side library is needed to parse claims.
"""
from __future__ import annotations

import secrets
import uuid

from app.cache.redis_client import get_redis

SESSION_PREFIX = "ogw:session:"
DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
TOKEN_BYTES = 32  # 256 bits


def generate_session_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _key(token: str) -> str:
    return f"{SESSION_PREFIX}{token}"


async def create_session(user_id: uuid.UUID, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    token = generate_session_token()
    await get_redis().set(_key(token), str(user_id), ex=ttl_seconds)
    return token


async def get_session_user_id(token: str) -> uuid.UUID | None:
    raw = await get_redis().get(_key(token))
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


async def touch_session(token: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    """Sliding TTL: reset expiry on each successful auth check."""
    await get_redis().expire(_key(token), ttl_seconds)


async def revoke_session(token: str) -> None:
    await get_redis().delete(_key(token))
