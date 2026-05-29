"""Provider interface — every upstream LLM API implements this."""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(slots=True)
class ChatRequest:
    model: str
    messages: list[dict[str, Any]]
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(slots=True)
class ChatResponse:
    """Unified, provider-agnostic chat response.

    Phase 1 stores upstream's raw JSON in `raw` so we can echo back an OpenAI-shaped response
    without lossy translation. Later phases will introduce a fully-normalized form.
    """

    model: str
    content: str
    usage: Usage
    raw: dict[str, Any]


@dataclass(slots=True)
class StreamChunk:
    """A single SSE chunk on the way back to the client. `data` is the raw JSON
    object emitted by the upstream provider (or "[DONE]" sentinel)."""

    data: str
    done: bool = False


@runtime_checkable
class Provider(Protocol):
    """Contract every upstream provider must satisfy."""

    name: str

    async def complete(self, request: ChatRequest) -> ChatResponse: ...

    def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]: ...
