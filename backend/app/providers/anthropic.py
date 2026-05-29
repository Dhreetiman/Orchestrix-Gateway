"""Anthropic provider.

The Anthropic Messages API has a different shape from OpenAI:
- `x-api-key` + `anthropic-version` headers, not Bearer.
- `system` is a top-level field, not a role inside `messages`.
- `max_tokens` is required.
- Response content lives in `content: [{type: "text", text: ...}]`.
- Streaming uses event types (`content_block_delta`, `message_delta`, …) rather than incremental
  delta objects.

This provider translates request + response shapes so the gateway maintains an OpenAI-compatible
surface regardless of which provider served the call. That way failover from gpt-4o → claude
returns a uniformly-shaped payload to the client.
"""
from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
import orjson

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.providers.base import ChatRequest, ChatResponse, Provider, StreamChunk, Usage
from app.providers.http_client import get_http_client
from app.providers.retry import RetryableHTTPError, retry_async

ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 1024


def _split_system(messages: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    """Extract leading/concatenated system messages into a single top-level `system` field."""
    system_parts: list[str] = []
    user_assistant: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content")
            if isinstance(content, str):
                system_parts.append(content)
        else:
            user_assistant.append({"role": msg["role"], "content": msg.get("content", "")})
    return ("\n\n".join(system_parts) if system_parts else None), user_assistant


def _anthropic_to_openai(data: dict[str, Any], model: str) -> dict[str, Any]:
    """Translate an Anthropic non-streaming response into OpenAI chat.completion shape."""
    content_blocks = data.get("content") or []
    text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
    usage = data.get("usage") or {}
    prompt_tokens = int(usage.get("input_tokens", 0))
    completion_tokens = int(usage.get("output_tokens", 0))
    return {
        "id": data.get("id", f"anthropic-{int(time.time() * 1000)}"),
        "object": "chat.completion",
        "model": data.get("model", model),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": _stop_reason(data.get("stop_reason")),
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _stop_reason(anthropic_reason: str | None) -> str:
    return {"end_turn": "stop", "max_tokens": "length", "stop_sequence": "stop"}.get(
        anthropic_reason or "", "stop"
    )


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.anthropic_api_key
        self._base_url = (base_url or settings.anthropic_base_url).rstrip("/")

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderError("Anthropic API key is not configured.")
        return {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    def _payload(self, request: ChatRequest) -> dict[str, Any]:
        system, messages = _split_system(request.messages)
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or DEFAULT_MAX_TOKENS,
            "temperature": request.temperature,
            "stream": request.stream,
        }
        if system:
            payload["system"] = system
        # Anthropic ignores OpenAI-only keys we'd have in `extra`; pass them anyway in case
        # the user is targeting a wrapper that accepts them.
        payload.update(request.extra)
        return payload

    async def complete(self, request: ChatRequest) -> ChatResponse:
        client = get_http_client()

        async def _attempt() -> httpx.Response:
            r = await client.post(
                f"{self._base_url}/messages",
                json=self._payload(request),
                headers=self._headers(),
            )
            if r.status_code >= 400:
                raise RetryableHTTPError(r.status_code, r.text[:1000])
            return r

        try:
            resp = await retry_async(_attempt, name="anthropic.messages")
        except RetryableHTTPError as exc:
            raise ProviderError(
                f"Anthropic returned {exc.status_code}", detail={"body": exc.body}
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Upstream Anthropic request failed: {exc!s}") from exc

        data = resp.json()
        translated = _anthropic_to_openai(data, request.model)
        choice_msg = translated["choices"][0]["message"]
        usage_block = translated["usage"]
        return ChatResponse(
            model=translated["model"],
            content=choice_msg["content"],
            usage=Usage(
                prompt_tokens=usage_block["prompt_tokens"],
                completion_tokens=usage_block["completion_tokens"],
            ),
            raw=translated,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        client = get_http_client()
        payload = self._payload(request)
        payload["stream"] = True

        try:
            async with client.stream(
                "POST",
                f"{self._base_url}/messages",
                json=payload,
                headers=self._headers(),
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise ProviderError(
                        f"Anthropic returned {resp.status_code}",
                        detail={"body": body.decode("utf-8", errors="replace")[:1000]},
                    )

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    try:
                        event = orjson.loads(data)
                    except orjson.JSONDecodeError:
                        continue

                    event_type = event.get("type")
                    if event_type == "content_block_delta":
                        delta = event.get("delta") or {}
                        if delta.get("type") == "text_delta":
                            chunk = {
                                "object": "chat.completion.chunk",
                                "model": request.model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {"content": delta.get("text", "")},
                                        "finish_reason": None,
                                    }
                                ],
                            }
                            yield StreamChunk(data=orjson.dumps(chunk).decode("utf-8"))
                    elif event_type == "message_stop":
                        final = {
                            "object": "chat.completion.chunk",
                            "model": request.model,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        }
                        yield StreamChunk(data=orjson.dumps(final).decode("utf-8"))
                        yield StreamChunk(data="[DONE]", done=True)
                        return
        except httpx.HTTPError as exc:
            raise ProviderError(f"Upstream Anthropic stream failed: {exc!s}") from exc
