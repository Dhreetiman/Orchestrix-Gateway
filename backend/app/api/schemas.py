"""Pydantic request/response schemas for the gateway API.

We keep the chat schema OpenAI-compatible so existing client libraries drop in by
just changing the base URL.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageSchema(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[ChatMessageSchema] = Field(min_length=1)
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False

    def messages_as_dicts(self) -> list[dict[str, Any]]:
        return [m.model_dump(exclude_none=True) for m in self.messages]
