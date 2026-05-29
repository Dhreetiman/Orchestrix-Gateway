from app.core.logging import _redact


def test_redacts_openai_key() -> None:
    assert "sk-***REDACTED***" in _redact("OPENAI_API_KEY=sk-abc123def456ghi789jkl")


def test_redacts_anthropic_key() -> None:
    assert "sk-ant-***REDACTED***" in _redact("creds: sk-ant-api03-abcdefghijklmnop")


def test_redacts_gateway_key() -> None:
    assert "ogw_***REDACTED***" in _redact("token=ogw_abcdef0123456789xyz")


def test_redacts_bearer_token() -> None:
    out = _redact("Authorization: Bearer ogw_abcdef0123456789xyz")
    assert "***REDACTED***" in out
    assert "ogw_abcdef0123456789xyz" not in out


def test_passes_through_safe_strings() -> None:
    safe = "model=gpt-4o-mini, request_id=abc-123"
    assert _redact(safe) == safe
