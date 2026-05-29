"""API key authentication as a FastAPI dependency.

Phase 1 uses a per-request DB lookup. Phase 2 will add a Redis-backed lookup cache.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.core.security import hash_api_key, is_well_formed
from app.db.models import ApiKey
from app.db.session import get_db


async def require_api_key(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session: AsyncSession = Depends(get_db),
) -> ApiKey:
    if not authorization:
        raise AuthError("Missing Authorization header.")

    scheme, _, raw = authorization.partition(" ")
    if scheme.lower() != "bearer" or not raw:
        raise AuthError("Authorization header must use Bearer scheme.")

    if not is_well_formed(raw):
        raise AuthError("Malformed API key.")

    digest = hash_api_key(raw)
    result = await session.execute(select(ApiKey).where(ApiKey.key_hash == digest))
    api_key = result.scalar_one_or_none()

    if api_key is None or not api_key.is_active or api_key.revoked_at is not None:
        raise AuthError("Invalid or revoked API key.")

    # Best-effort last_used update; do not block the request on it.
    await session.execute(
        update(ApiKey).where(ApiKey.id == api_key.id).values(last_used_at=datetime.now(UTC))
    )
    await session.commit()

    return api_key
