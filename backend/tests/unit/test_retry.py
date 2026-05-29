import pytest

from app.providers.retry import (
    RetryableHTTPError,
    RetryPolicy,
    retry_async,
)


async def test_retry_succeeds_on_second_attempt() -> None:
    attempts = {"n": 0}

    async def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RetryableHTTPError(503, "transient")
        return "ok"

    result = await retry_async(flaky, policy=RetryPolicy(max_attempts=3, base_delay_seconds=0))
    assert result == "ok"
    assert attempts["n"] == 2


async def test_retry_gives_up_after_max_attempts() -> None:
    attempts = {"n": 0}

    async def always_503() -> str:
        attempts["n"] += 1
        raise RetryableHTTPError(503, "down")

    with pytest.raises(RetryableHTTPError):
        await retry_async(always_503, policy=RetryPolicy(max_attempts=3, base_delay_seconds=0))
    assert attempts["n"] == 3


async def test_non_transient_status_is_not_retried() -> None:
    attempts = {"n": 0}

    async def auth_error() -> str:
        attempts["n"] += 1
        raise RetryableHTTPError(401, "bad key")

    with pytest.raises(RetryableHTTPError):
        await retry_async(auth_error, policy=RetryPolicy(max_attempts=5, base_delay_seconds=0))
    assert attempts["n"] == 1  # one attempt, no retries
