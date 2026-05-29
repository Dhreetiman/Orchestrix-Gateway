"""Persist a row to `request_logs` for each completed gateway request."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RequestLog


async def log_request(
    session: AsyncSession,
    *,
    api_key_id: uuid.UUID | None,
    provider: str,
    model: str,
    prompt_hash: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    latency_ms: int,
    status: str,
    status_code: int = 200,
    error_code: str | None = None,
    cache_hit: bool = False,
    streamed: bool = False,
) -> None:
    session.add(
        RequestLog(
            api_key_id=api_key_id,
            provider=provider,
            model=model,
            prompt_hash=prompt_hash,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=status,
            status_code=status_code,
            error_code=error_code,
            cache_hit=cache_hit,
            streamed=streamed,
        )
    )
    await session.commit()
