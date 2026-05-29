"""POST /v1/chat/completions — the central request pipeline.

Pipeline:
    auth → cache lookup → route to provider → call upstream → cache → log → respond
"""
from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

import orjson
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ChatCompletionRequest
from app.cache.keys import chat_cache_key, prompt_hash
from app.cache.redis_cache import get_json, set_json, should_cache
from app.core.exceptions import GatewayError, ProviderError
from app.core.logging import get_logger
from app.db.models import ApiKey
from app.db.session import get_db
from app.middleware.auth import require_api_key
from app.middleware.rate_limit import enforce_rate_limit
from app.monitoring import metrics as m
from app.providers.base import ChatRequest, Provider
from app.routing.failover import complete_with_failover
from app.routing.router import plan_for_model, provider_for_model
from app.services.cost_calculator import calculate_cost_usd
from app.services.request_logger import log_request

router = APIRouter(prefix="/v1", tags=["chat"])
log = get_logger(__name__)


def _to_provider_request(req: ChatCompletionRequest) -> ChatRequest:
    return ChatRequest(
        model=req.model,
        messages=req.messages_as_dicts(),
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        stream=req.stream,
    )


@router.post("/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    api_key: Annotated[ApiKey, Depends(require_api_key)],
    session: AsyncSession = Depends(get_db),
) -> Any:
    await enforce_rate_limit(api_key.id)

    messages = payload.messages_as_dicts()
    digest = prompt_hash(
        model=payload.model, messages=messages, temperature=payload.temperature
    )
    cache_key = chat_cache_key(prompt_digest=digest)
    started = time.perf_counter()

    # ── Streaming path ─────────────────────────────────────────────
    if payload.stream:
        provider = provider_for_model(payload.model)
        provider_req = _to_provider_request(payload)
        return StreamingResponse(
            _stream_and_log(
                provider=provider,
                provider_req=provider_req,
                session=session,
                api_key_id=api_key.id,
                model=payload.model,
                prompt_digest=digest,
                started=started,
            ),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    # ── Non-streaming: try cache first ─────────────────────────────
    cache_eligible = should_cache(payload.temperature)
    if cache_eligible:
        cached = await get_json(cache_key)
        if cached is not None:
            latency_ms = int((time.perf_counter() - started) * 1000)
            provider_name = cached.get("_provider", "unknown")
            await log_request(
                session,
                api_key_id=api_key.id,
                provider=provider_name,
                model=payload.model,
                prompt_hash=digest,
                tokens_in=cached.get("_tokens_in", 0),
                tokens_out=cached.get("_tokens_out", 0),
                cost_usd=0.0,
                latency_ms=latency_ms,
                status="ok",
                cache_hit=True,
            )
            m.requests_total.labels(
                provider=provider_name, model=payload.model, status="ok", cache_hit="true"
            ).inc()
            m.request_latency_seconds.labels(
                provider=provider_name, model=payload.model
            ).observe(latency_ms / 1000)
            log.info("cache_hit", model=payload.model, latency_ms=latency_ms)
            response_body = cached.get("body", {})
            return JSONResponse(content=response_body, headers={"X-Cache": "HIT"})

    plan = plan_for_model(payload.model)
    provider_req = _to_provider_request(payload)

    try:
        result, served_by = await complete_with_failover(plan, provider_req)
    except GatewayError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        primary_name = plan.primary.name
        await log_request(
            session,
            api_key_id=api_key.id,
            provider=primary_name,
            model=payload.model,
            prompt_hash=digest,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=latency_ms,
            status="error",
            status_code=exc.status_code,
            error_code=exc.error_code,
        )
        m.requests_total.labels(
            provider=primary_name, model=payload.model, status="error", cache_hit="false"
        ).inc()
        raise

    latency_ms = int((time.perf_counter() - started) * 1000)
    cost = calculate_cost_usd(
        payload.model, result.usage.prompt_tokens, result.usage.completion_tokens
    )

    if cache_eligible:
        await set_json(
            cache_key,
            {
                "body": result.raw,
                "_provider": served_by,
                "_tokens_in": result.usage.prompt_tokens,
                "_tokens_out": result.usage.completion_tokens,
            },
        )

    await log_request(
        session,
        api_key_id=api_key.id,
        provider=served_by,
        model=payload.model,
        prompt_hash=digest,
        tokens_in=result.usage.prompt_tokens,
        tokens_out=result.usage.completion_tokens,
        cost_usd=cost,
        latency_ms=latency_ms,
        status="ok",
        cache_hit=False,
    )

    m.requests_total.labels(
        provider=served_by, model=payload.model, status="ok", cache_hit="false"
    ).inc()
    m.request_latency_seconds.labels(provider=served_by, model=payload.model).observe(
        latency_ms / 1000
    )
    m.tokens_total.labels(
        provider=served_by, model=payload.model, direction="prompt"
    ).inc(result.usage.prompt_tokens)
    m.tokens_total.labels(
        provider=served_by, model=payload.model, direction="completion"
    ).inc(result.usage.completion_tokens)
    m.cost_usd_total.labels(provider=served_by, model=payload.model).inc(cost)

    log.info(
        "chat_completed",
        provider=served_by,
        primary_provider=plan.primary.name,
        failover_used=served_by != plan.primary.name,
        model=payload.model,
        tokens_in=result.usage.prompt_tokens,
        tokens_out=result.usage.completion_tokens,
        latency_ms=latency_ms,
        cost_usd=cost,
    )

    return JSONResponse(
        content=result.raw,
        headers={"X-Cache": "MISS", "X-Served-By": served_by},
    )


async def _stream_and_log(
    *,
    provider: Provider,
    provider_req: ChatRequest,
    session: AsyncSession,
    api_key_id: uuid.UUID,
    model: str,
    prompt_digest: str,
    started: float,
) -> AsyncIterator[bytes]:
    """Pass SSE chunks through to the client and log the aggregate when the stream completes."""
    tokens_out_estimate = 0
    content_chars = 0
    error_code: str | None = None
    status = "ok"
    status_code = 200

    m.active_streams.inc()
    try:
        async for chunk in provider.stream(provider_req):
            if chunk.done:
                yield b"data: [DONE]\n\n"
                continue
            yield f"data: {chunk.data}\n\n".encode()
            # Best-effort token estimation from OpenAI-shaped chunk text length.
            try:
                obj = orjson.loads(chunk.data)
                choices = obj.get("choices") or []
                if choices:
                    delta_content = (choices[0].get("delta") or {}).get("content") or ""
                    content_chars += len(delta_content)
            except orjson.JSONDecodeError:
                pass
    except ProviderError as exc:
        status = "error"
        status_code = exc.status_code
        error_code = exc.error_code
        log.warning("stream_error", message=exc.message)
        yield f"data: {orjson.dumps({'error': {'code': exc.error_code, 'message': exc.message}}).decode()}\n\n".encode()
        yield b"data: [DONE]\n\n"
    finally:
        m.active_streams.dec()
        latency_ms = int((time.perf_counter() - started) * 1000)
        tokens_out_estimate = content_chars // 4
        tokens_in_estimate = (
            sum(len(msg.get("content", "")) for msg in provider_req.messages) // 4
        )
        cost = calculate_cost_usd(model, tokens_in_estimate, tokens_out_estimate)
        await log_request(
            session,
            api_key_id=api_key_id,
            provider=provider.name,
            model=model,
            prompt_hash=prompt_digest,
            tokens_in=tokens_in_estimate,
            tokens_out=tokens_out_estimate,
            cost_usd=cost,
            latency_ms=latency_ms,
            status=status,
            status_code=status_code,
            error_code=error_code,
            cache_hit=False,
            streamed=True,
        )
        m.requests_total.labels(
            provider=provider.name, model=model, status=status, cache_hit="false"
        ).inc()
        m.request_latency_seconds.labels(provider=provider.name, model=model).observe(
            latency_ms / 1000
        )
        m.tokens_total.labels(
            provider=provider.name, model=model, direction="prompt"
        ).inc(tokens_in_estimate)
        m.tokens_total.labels(
            provider=provider.name, model=model, direction="completion"
        ).inc(tokens_out_estimate)
        m.cost_usd_total.labels(provider=provider.name, model=model).inc(cost)
        if error_code:
            m.provider_errors_total.labels(
                provider=provider.name, model=model, error_code=error_code
            ).inc()
