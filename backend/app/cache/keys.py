"""Cache key derivation for chat completion requests.

The key must be deterministic for identical *semantic* inputs (same messages, model, temperature),
and stable across process restarts. We canonicalize JSON before hashing so dict-key ordering
doesn't break the cache.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

NAMESPACE_CHAT = "ogw:chat:v1"


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def prompt_hash(*, model: str, messages: list[dict[str, Any]], temperature: float) -> str:
    """SHA-256 over the cache-relevant request shape."""
    blob = _canonical({"model": model, "messages": messages, "temperature": temperature})
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def chat_cache_key(*, prompt_digest: str) -> str:
    return f"{NAMESPACE_CHAT}:{prompt_digest}"
