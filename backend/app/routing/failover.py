"""Failover orchestrator: try providers in order, stop on first success.

Only applied to non-streaming requests — replaying mid-stream is unsafe.
"""
from __future__ import annotations

from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.monitoring import metrics as m
from app.providers.base import ChatRequest, ChatResponse
from app.routing.router import RoutePlan

log = get_logger(__name__)


async def complete_with_failover(
    plan: RoutePlan, request: ChatRequest
) -> tuple[ChatResponse, str]:
    """Run request through the route plan. Returns (response, provider_name_that_succeeded).

    Raises the final ProviderError if every provider fails.
    """
    last_error: ProviderError | None = None
    for provider in plan.providers:
        try:
            resp = await provider.complete(request)
            return resp, provider.name
        except ProviderError as exc:
            log.warning(
                "provider_failed",
                provider=provider.name,
                model=request.model,
                error_code=exc.error_code,
                message=exc.message,
            )
            m.provider_errors_total.labels(
                provider=provider.name, model=request.model, error_code=exc.error_code
            ).inc()
            last_error = exc
            continue

    assert last_error is not None  # plan is never empty
    raise last_error
