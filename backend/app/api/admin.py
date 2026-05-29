"""Admin / dashboard API.

Exposed at `/admin/*`. Authenticated via session cookie OR bearer API key. All queries are
scoped to the currently authenticated user — each user sees only their own keys, logs, and
analytics. This is the multi-tenant data model that backs the dashboard.

Powers the Phase 3 dashboard: stats overview, time-bucketed series, provider distribution,
paginated logs, API-key CRUD.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_user
from app.core.security import generate_api_key, hash_api_key
from app.db.models import ApiKey, RequestLog, User
from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class OverviewStats(BaseModel):
    window_seconds: int
    total_requests: int
    cache_hits: int
    cache_hit_ratio: float
    error_count: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    p50_latency_ms: int
    p95_latency_ms: int


class TimeBucket(BaseModel):
    bucket: datetime
    requests: int
    cache_hits: int
    errors: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    avg_latency_ms: float


class ProviderSlice(BaseModel):
    provider: str
    requests: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    error_count: int


class RequestLogRow(BaseModel):
    id: uuid.UUID
    created_at: datetime
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    status: str
    status_code: int
    error_code: str | None
    cache_hit: bool
    streamed: bool


class LogsPage(BaseModel):
    items: list[RequestLogRow]
    next_cursor: str | None
    total: int


class ApiKeyRow(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    is_active: bool
    key_preview: str


class ApiKeyCreated(BaseModel):
    id: uuid.UUID
    name: str
    key: str = Field(description="Full API key — shown ONCE; store immediately.")


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


# ── Helpers ──────────────────────────────────────────────────────────────────

_WINDOW_PRESETS: dict[str, int] = {
    "15m": 15 * 60,
    "1h": 60 * 60,
    "6h": 6 * 60 * 60,
    "24h": 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
}


def _resolve_window(window: str) -> int:
    if window not in _WINDOW_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown window '{window}'.")
    return _WINDOW_PRESETS[window]


def _user_api_key_ids_subquery(user_id: uuid.UUID) -> sa.Select[tuple[uuid.UUID]]:
    """Subquery returning the IDs of api_keys owned by this user. Used to scope logs."""
    return select(ApiKey.id).where(ApiKey.user_id == user_id)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/stats/overview", response_model=OverviewStats)
async def stats_overview(
    user: Annotated[User, Depends(require_user)],
    db: AsyncSession = Depends(get_db),
    window: str = Query("24h"),
) -> OverviewStats:
    seconds = _resolve_window(window)
    since = datetime.now(UTC) - timedelta(seconds=seconds)
    key_ids = _user_api_key_ids_subquery(user.id)

    stmt = select(
        func.count(RequestLog.id),
        func.coalesce(func.sum(sa.case((RequestLog.cache_hit.is_(True), 1), else_=0)), 0),
        func.coalesce(func.sum(sa.case((RequestLog.status == "error", 1), else_=0)), 0),
        func.coalesce(func.sum(RequestLog.tokens_in), 0),
        func.coalesce(func.sum(RequestLog.tokens_out), 0),
        func.coalesce(func.sum(RequestLog.cost_usd), 0),
        func.coalesce(
            func.percentile_cont(0.5).within_group(RequestLog.latency_ms.asc()), 0
        ),
        func.coalesce(
            func.percentile_cont(0.95).within_group(RequestLog.latency_ms.asc()), 0
        ),
    ).where(
        RequestLog.created_at >= since,
        RequestLog.api_key_id.in_(key_ids),
    )

    row = (await db.execute(stmt)).one()
    total, hits, errors, tin, tout, cost, p50, p95 = row

    return OverviewStats(
        window_seconds=seconds,
        total_requests=int(total),
        cache_hits=int(hits),
        cache_hit_ratio=(float(hits) / float(total)) if total else 0.0,
        error_count=int(errors),
        tokens_in=int(tin),
        tokens_out=int(tout),
        cost_usd=float(cost),
        p50_latency_ms=int(p50),
        p95_latency_ms=int(p95),
    )


@router.get("/stats/series", response_model=list[TimeBucket])
async def stats_series(
    user: Annotated[User, Depends(require_user)],
    db: AsyncSession = Depends(get_db),
    window: str = Query("24h"),
    bucket: Literal["minute", "hour", "day"] = Query("hour"),
) -> list[TimeBucket]:
    seconds = _resolve_window(window)
    since = datetime.now(UTC) - timedelta(seconds=seconds)
    key_ids = _user_api_key_ids_subquery(user.id)

    bucketed = func.date_trunc(bucket, RequestLog.created_at).label("bucket")

    stmt = (
        select(
            bucketed,
            func.count(RequestLog.id).label("requests"),
            func.coalesce(func.sum(sa.case((RequestLog.cache_hit.is_(True), 1), else_=0)), 0).label("hits"),
            func.coalesce(func.sum(sa.case((RequestLog.status == "error", 1), else_=0)), 0).label("errors"),
            func.coalesce(func.sum(RequestLog.tokens_in), 0).label("tin"),
            func.coalesce(func.sum(RequestLog.tokens_out), 0).label("tout"),
            func.coalesce(func.sum(RequestLog.cost_usd), 0).label("cost"),
            func.coalesce(func.avg(RequestLog.latency_ms), 0).label("avg_latency"),
        )
        .where(
            RequestLog.created_at >= since,
            RequestLog.api_key_id.in_(key_ids),
        )
        .group_by(bucketed)
        .order_by(bucketed)
    )
    rows = (await db.execute(stmt)).all()
    return [
        TimeBucket(
            bucket=r.bucket,
            requests=int(r.requests),
            cache_hits=int(r.hits),
            errors=int(r.errors),
            tokens_in=int(r.tin),
            tokens_out=int(r.tout),
            cost_usd=float(r.cost),
            avg_latency_ms=float(r.avg_latency),
        )
        for r in rows
    ]


@router.get("/stats/providers", response_model=list[ProviderSlice])
async def stats_providers(
    user: Annotated[User, Depends(require_user)],
    db: AsyncSession = Depends(get_db),
    window: str = Query("24h"),
) -> list[ProviderSlice]:
    seconds = _resolve_window(window)
    since = datetime.now(UTC) - timedelta(seconds=seconds)
    key_ids = _user_api_key_ids_subquery(user.id)

    stmt = (
        select(
            RequestLog.provider,
            func.count(RequestLog.id),
            func.coalesce(func.sum(RequestLog.tokens_in), 0),
            func.coalesce(func.sum(RequestLog.tokens_out), 0),
            func.coalesce(func.sum(RequestLog.cost_usd), 0),
            func.coalesce(func.sum(sa.case((RequestLog.status == "error", 1), else_=0)), 0),
        )
        .where(
            RequestLog.created_at >= since,
            RequestLog.api_key_id.in_(key_ids),
        )
        .group_by(RequestLog.provider)
        .order_by(func.count(RequestLog.id).desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        ProviderSlice(
            provider=p,
            requests=int(cnt),
            tokens_in=int(tin),
            tokens_out=int(tout),
            cost_usd=float(cost),
            error_count=int(errs),
        )
        for p, cnt, tin, tout, cost, errs in rows
    ]


@router.get("/logs", response_model=LogsPage)
async def list_logs(
    user: Annotated[User, Depends(require_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, description="ISO timestamp of the last item on the previous page."),
    provider: str | None = Query(None),
    status_filter: Literal["ok", "error"] | None = Query(None, alias="status"),
    cache_hit: bool | None = Query(None),
    model: str | None = Query(None),
) -> LogsPage:
    key_ids = _user_api_key_ids_subquery(user.id)
    filters: list[sa.ColumnElement[bool]] = [RequestLog.api_key_id.in_(key_ids)]
    if provider:
        filters.append(RequestLog.provider == provider)
    if status_filter:
        filters.append(RequestLog.status == status_filter)
    if cache_hit is not None:
        filters.append(RequestLog.cache_hit.is_(cache_hit))
    if model:
        filters.append(RequestLog.model.like(f"{model}%"))
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor.") from exc
        filters.append(RequestLog.created_at < cursor_dt)

    where = and_(*filters)

    items_stmt = (
        select(RequestLog).where(where).order_by(RequestLog.created_at.desc()).limit(limit)
    )
    count_stmt = select(func.count(RequestLog.id)).where(where)

    rows = (await db.execute(items_stmt)).scalars().all()
    total = int((await db.execute(count_stmt)).scalar_one())

    items = [
        RequestLogRow(
            id=row.id,
            created_at=row.created_at,
            provider=row.provider,
            model=row.model,
            tokens_in=row.tokens_in,
            tokens_out=row.tokens_out,
            cost_usd=float(row.cost_usd),
            latency_ms=row.latency_ms,
            status=row.status,
            status_code=row.status_code,
            error_code=row.error_code,
            cache_hit=row.cache_hit,
            streamed=row.streamed,
        )
        for row in rows
    ]
    next_cursor = items[-1].created_at.isoformat() if len(items) == limit else None
    return LogsPage(items=items, next_cursor=next_cursor, total=total)


@router.get("/api-keys", response_model=list[ApiKeyRow])
async def list_api_keys(
    user: Annotated[User, Depends(require_user)],
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyRow]:
    rows = (
        await db.execute(
            select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
        )
    ).scalars().all()
    return [
        ApiKeyRow(
            id=r.id,
            name=r.name,
            created_at=r.created_at,
            last_used_at=r.last_used_at,
            revoked_at=r.revoked_at,
            is_active=r.is_active,
            key_preview=f"ogw_…{r.key_hash[-6:]}",
        )
        for r in rows
    ]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key_endpoint(
    body: CreateApiKeyRequest,
    user: Annotated[User, Depends(require_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    raw = generate_api_key()
    record = ApiKey(user_id=user.id, name=body.name, key_hash=hash_api_key(raw))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return ApiKeyCreated(id=record.id, name=record.name, key=raw)


@router.post("/api-keys/{key_id}/revoke", response_model=ApiKeyRow)
async def revoke_api_key(
    key_id: uuid.UUID,
    user: Annotated[User, Depends(require_user)],
    db: AsyncSession = Depends(get_db),
) -> ApiKeyRow:
    record = (
        await db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    record.is_active = False
    record.revoked_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    return ApiKeyRow(
        id=record.id,
        name=record.name,
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        revoked_at=record.revoked_at,
        is_active=record.is_active,
        key_preview=f"ogw_…{record.key_hash[-6:]}",
    )
