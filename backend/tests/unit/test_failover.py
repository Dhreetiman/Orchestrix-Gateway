from collections.abc import AsyncIterator

import pytest

from app.core.exceptions import ProviderError
from app.providers.base import ChatRequest, ChatResponse, Provider, StreamChunk, Usage
from app.routing.failover import complete_with_failover
from app.routing.router import RoutePlan


class _BoomProvider(Provider):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    async def complete(self, request: ChatRequest) -> ChatResponse:
        self.calls += 1
        raise ProviderError(f"{self.name} is down")

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(data="[DONE]", done=True)


class _OkProvider(Provider):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    async def complete(self, request: ChatRequest) -> ChatResponse:
        self.calls += 1
        return ChatResponse(
            model=request.model,
            content="hi",
            usage=Usage(prompt_tokens=1, completion_tokens=1),
            raw={"model": request.model},
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(data="[DONE]", done=True)


def _req(model: str = "x") -> ChatRequest:
    return ChatRequest(model=model, messages=[{"role": "user", "content": "hi"}])


async def test_failover_falls_back_to_next_provider() -> None:
    primary = _BoomProvider("primary")
    backup = _OkProvider("backup")
    plan = RoutePlan(providers=(primary, backup))

    resp, served_by = await complete_with_failover(plan, _req())

    assert resp.content == "hi"
    assert served_by == "backup"
    assert primary.calls == 1
    assert backup.calls == 1


async def test_failover_raises_when_all_providers_fail() -> None:
    p1 = _BoomProvider("a")
    p2 = _BoomProvider("b")
    plan = RoutePlan(providers=(p1, p2))

    with pytest.raises(ProviderError) as excinfo:
        await complete_with_failover(plan, _req())
    assert "b is down" in str(excinfo.value.message)
    assert p1.calls == 1
    assert p2.calls == 1


async def test_no_failover_when_primary_succeeds() -> None:
    primary = _OkProvider("primary")
    backup = _OkProvider("backup")
    plan = RoutePlan(providers=(primary, backup))

    _, served_by = await complete_with_failover(plan, _req())
    assert served_by == "primary"
    assert backup.calls == 0
