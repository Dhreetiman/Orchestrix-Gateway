"""Authentication endpoints: signup, login, logout, me.

Session is an opaque token stored in a server-side Redis key, transported as an httpOnly cookie.
On signup, the user automatically receives one chat API key so the dashboard isn't empty.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import (
    DEFAULT_TTL_SECONDS,
    create_session,
    get_session_user_id,
    revoke_session,
)
from app.core.config import get_settings
from app.core.passwords import hash_password, verify_password
from app.core.security import generate_api_key, hash_api_key
from app.db.models import ApiKey, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE_NAME = "ogw_session"


# ── Schemas ──────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str | None
    created_at: datetime


class SignupResponse(BaseModel):
    user: UserResponse
    api_key: str = Field(description="First API key, shown ONCE so the user can call /v1 immediately.")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=DEFAULT_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id, email=user.email, name=user.name, created_at=user.created_at
    )


async def get_current_user_optional(
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not session_token:
        return None
    user_id = await get_session_user_id(session_token)
    if not user_id:
        return None
    return (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(
    body: SignupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SignupResponse:
    normalized_email = body.email.lower()

    existing = (
        await db.execute(select(User).where(User.email == normalized_email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(body.password),
        name=body.name,
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()  # need user.id for the api key FK

    raw_key = generate_api_key()
    db.add(
        ApiKey(
            user_id=user.id,
            name="Default key",
            key_hash=hash_api_key(raw_key),
        )
    )
    await db.commit()
    await db.refresh(user)

    token = await create_session(user.id)
    _set_session_cookie(response, token)

    return SignupResponse(user=_to_user_response(user), api_key=raw_key)


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    if user is None or not verify_password(user.password_hash, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    user.last_login_at = datetime.now(UTC)
    await db.commit()

    token = await create_session(user.id)
    _set_session_cookie(response, token)
    return _to_user_response(user)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> Response:
    if session_token:
        await revoke_session(session_token)
    _clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User | None = Depends(get_current_user_optional),
) -> UserResponse:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return _to_user_response(current_user)
