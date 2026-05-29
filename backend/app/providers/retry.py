"""Exponential-backoff retry helper for transient upstream failures.

We retry on network errors and a tight allowlist of HTTP status codes (429, 502, 503, 504).
We do NOT retry on auth (401/403) or genuine 4xx — those won't succeed on replay.

Kept deliberately tiny — no tenacity dependency.
"""
from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from app.core.logging import get_logger

log = get_logger(__name__)

# HTTP status codes that are worth retrying. Source: provider docs + common practice.
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


class RetryableHTTPError(Exception):
    """Raised by provider call sites to signal the wrapper that this attempt is retryable.

    Wraps the underlying httpx response status_code so the wrapper can log it.
    """

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"upstream returned {status_code}")
        self.status_code = status_code
        self.body = body


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 4.0
    jitter: float = 0.1


DEFAULT_POLICY = RetryPolicy()


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, RetryableHTTPError):
        return exc.status_code in RETRYABLE_STATUS
    return isinstance(
        exc, httpx.TimeoutException | httpx.ConnectError | httpx.RemoteProtocolError
    )


async def retry_async[T](
    func: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy = DEFAULT_POLICY,
    name: str = "upstream",
) -> T:
    """Invoke `func` with exponential backoff retries on transient errors."""
    last_exc: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await func()
        except BaseException as exc:
            if not _is_transient(exc) or attempt == policy.max_attempts:
                raise
            last_exc = exc
            delay = min(
                policy.base_delay_seconds * (2 ** (attempt - 1)),
                policy.max_delay_seconds,
            )
            delay += random.uniform(0, policy.jitter)
            log.warning(
                "retrying_upstream",
                name=name,
                attempt=attempt,
                next_delay_seconds=round(delay, 3),
                reason=str(exc),
            )
            await asyncio.sleep(delay)
    # Unreachable — the loop either returns or raises.
    raise RuntimeError("retry_async exhausted without return or raise") from last_exc
