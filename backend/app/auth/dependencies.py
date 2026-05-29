"""Auth dependencies for FastAPI routes.

`require_user`: admin/dashboard routes. Accepts EITHER a session cookie (set by /auth/login)
or a bearer `ogw_*` API key whose owner is a real user. Returns the resolved `User`, plus
the `ApiKey` if one was used (for `last_used_at` tracking and access logs).

`require_api_key` (in app/middleware/auth.py) is unchanged — chat endpoints only accept bearer
tokens, because browsers shouldn't be invoking /v1 directly.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import SESSION_COOKIE_NAME
from app.auth.sessions import get_session_user_id, touch_session
from app.core.exceptions import AuthError
from app.core.security import hash_api_key, is_well_formed
from app.db.models import ApiKey, User
from app.db.session import get_db


async def require_user(
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a session cookie or a bearer API key."""
    if session_token:
        user_id = await get_session_user_id(session_token)
        if user_id is not None:
            user = (
                await db.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()
            if user is not None and user.is_active:
                await touch_session(session_token)
                return user

    if authorization:
        scheme, _, raw = authorization.partition(" ")
        if scheme.lower() == "bearer" and raw and is_well_formed(raw):
            digest = hash_api_key(raw)
            api_key = (
                await db.execute(select(ApiKey).where(ApiKey.key_hash == digest))
            ).scalar_one_or_none()
            if (
                api_key is not None
                and api_key.is_active
                and api_key.revoked_at is None
                and api_key.user_id is not None
            ):
                user = (
                    await db.execute(select(User).where(User.id == api_key.user_id))
                ).scalar_one_or_none()
                if user is not None and user.is_active:
                    await db.execute(
                        update(ApiKey)
                        .where(ApiKey.id == api_key.id)
                        .values(last_used_at=datetime.now(UTC))
                    )
                    await db.commit()
                    return user

    raise AuthError("Authentication required.")
