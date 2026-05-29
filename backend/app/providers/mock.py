"""Deterministic mock provider — for tests and offline development."""
from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import orjson

from app.providers.base import ChatRequest, ChatResponse, Provider, StreamChunk, Usage


def _echo_content(messages: list[dict[str, Any]]) -> str:
    last = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    return f"[mock] {last['content']}" if last else "[mock]"


class MockProvider(Provider):
    name = "mock"

    async def complete(self, request: ChatRequest) -> ChatResponse:
        content = _echo_content(request.messages)
        prompt_tokens = sum(len(m.get("content", "")) for m in request.messages) // 4
        completion_tokens = len(content) // 4
        raw: dict[str, Any] = {
            "id": f"mock-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
        return ChatResponse(
            model=request.model,
            content=content,
            usage=Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
            raw=raw,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        content = _echo_content(request.messages)
        for word in content.split():
            chunk = {
                "id": "mock-stream",
                "object": "chat.completion.chunk",
                "model": request.model,
                "choices": [{"index": 0, "delta": {"content": word + " "}, "finish_reason": None}],
            }
            yield StreamChunk(data=orjson.dumps(chunk).decode("utf-8"))
        final = {
            "id": "mock-stream",
            "object": "chat.completion.chunk",
            "model": request.model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield StreamChunk(data=orjson.dumps(final).decode("utf-8"))
        yield StreamChunk(data="[DONE]", done=True)
