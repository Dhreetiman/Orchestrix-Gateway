from app.providers.base import ChatRequest
from app.providers.mock import MockProvider


async def test_mock_complete_echoes() -> None:
    p = MockProvider()
    resp = await p.complete(
        ChatRequest(model="mock", messages=[{"role": "user", "content": "ping"}])
    )
    assert "ping" in resp.content
    assert resp.usage.total_tokens >= 0


async def test_mock_stream_emits_done() -> None:
    p = MockProvider()
    chunks = []
    async for c in p.stream(
        ChatRequest(model="mock", messages=[{"role": "user", "content": "ping pong"}], stream=True)
    ):
        chunks.append(c)
    assert chunks[-1].done is True
    assert chunks[-1].data == "[DONE]"
