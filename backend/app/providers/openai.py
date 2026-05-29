"""OpenAI provider — talks to the Chat Completions API over plain HTTP.

We intentionally avoid the openai SDK so the gateway owns the request lifecycle (timeouts,
retries, cache, streaming pass-through, cost calc) and stays uniformly shaped across providers.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.providers.base import ChatRequest, ChatResponse, Provider, StreamChunk, Usage
from app.providers.http_client import get_http_client
from app.providers.retry import RetryableHTTPError, retry_async


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._base_url = (base_url or settings.openai_base_url).rstrip("/")

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderError("OpenAI API key is not configured.")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, request: ChatRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": request.stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        payload.update(request.extra)
        return payload

    async def complete(self, request: ChatRequest) -> ChatResponse:
        client = get_http_client()

        async def _attempt() -> httpx.Response:
            r = await client.post(
                f"{self._base_url}/chat/completions",
                json=self._payload(request),
                headers=self._headers(),
            )
            if r.status_code >= 400:
                # Transient codes flow back into retry_async; others bubble out as ProviderError below.
                raise RetryableHTTPError(r.status_code, r.text[:1000])
            return r

        try:
            resp = await retry_async(_attempt, name="openai.chat.completions")
        except RetryableHTTPError as exc:
            raise ProviderError(
                f"OpenAI returned {exc.status_code}", detail={"body": exc.body}
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Upstream OpenAI request failed: {exc!s}") from exc

        data = resp.json()
        usage_obj = data.get("usage") or {}
        usage = Usage(
            prompt_tokens=int(usage_obj.get("prompt_tokens", 0)),
            completion_tokens=int(usage_obj.get("completion_tokens", 0)),
        )
        choices = data.get("choices") or []
        content = ""
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content") or ""

        return ChatResponse(model=data.get("model", request.model), content=content, usage=usage, raw=data)

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        client = get_http_client()
        payload = self._payload(request)
        payload["stream"] = True

        try:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise ProviderError(
                        f"OpenAI returned {resp.status_code}",
                        detail={"body": body.decode("utf-8", errors="replace")[:1000]},
                    )

                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        yield StreamChunk(data="[DONE]", done=True)
                        return
                    yield StreamChunk(data=data)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Upstream OpenAI stream failed: {exc!s}") from exc
