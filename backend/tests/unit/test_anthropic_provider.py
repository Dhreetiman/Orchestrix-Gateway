"""Anthropic provider unit tests against a mocked upstream."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.providers.anthropic import AnthropicProvider, _split_system
from app.providers.base import ChatRequest
from app.providers.http_client import close_http_client


@pytest.fixture(autouse=True)
async def _http_lifecycle():  # type: ignore[no-untyped-def]
    yield
    await close_http_client()


def test_split_system_extracts_system_messages() -> None:
    system, rest = _split_system(
        [
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "hi"},
        ]
    )
    assert system == "you are helpful"
    assert rest == [{"role": "user", "content": "hi"}]


def test_split_system_concatenates_multiple_system_messages() -> None:
    system, _ = _split_system(
        [
            {"role": "system", "content": "rule 1"},
            {"role": "system", "content": "rule 2"},
            {"role": "user", "content": "hi"},
        ]
    )
    assert system == "rule 1\n\nrule 2"


@respx.mock
async def test_complete_translates_to_openai_shape() -> None:
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_123",
                "type": "message",
                "role": "assistant",
                "model": "claude-3-5-sonnet-20241022",
                "content": [{"type": "text", "text": "Hello, world!"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 4},
            },
        )
    )

    provider = AnthropicProvider(api_key="test")
    resp = await provider.complete(
        ChatRequest(
            model="claude-3-5-sonnet",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=100,
        )
    )

    assert resp.content == "Hello, world!"
    assert resp.usage.prompt_tokens == 10
    assert resp.usage.completion_tokens == 4
    # raw is OpenAI-shaped now
    assert resp.raw["choices"][0]["message"]["content"] == "Hello, world!"
    assert resp.raw["choices"][0]["finish_reason"] == "stop"
    assert resp.raw["usage"]["total_tokens"] == 14
