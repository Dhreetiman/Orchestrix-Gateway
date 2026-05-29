"""Provider-level test against a mocked upstream using respx."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.providers.base import ChatRequest
from app.providers.http_client import close_http_client
from app.providers.openai import OpenAIProvider


@pytest.fixture(autouse=True)
async def _http_lifecycle():  # type: ignore[no-untyped-def]
    yield
    await close_http_client()


@respx.mock
async def test_complete_parses_openai_response() -> None:
    route = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "x",
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Hello!"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )
    )

    provider = OpenAIProvider(api_key="test-key")
    resp = await provider.complete(
        ChatRequest(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])
    )

    assert route.called
    assert resp.content == "Hello!"
    assert resp.usage.prompt_tokens == 5
    assert resp.usage.completion_tokens == 2


@respx.mock
async def test_complete_raises_on_upstream_error() -> None:
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(429, json={"error": "rate limited"})
    )

    provider = OpenAIProvider(api_key="test-key")
    from app.core.exceptions import ProviderError

    with pytest.raises(ProviderError):
        await provider.complete(
            ChatRequest(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])
        )
