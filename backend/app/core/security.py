import hashlib
import secrets

API_KEY_PREFIX = "ogw_"
API_KEY_BYTES = 32  # 256 bits of entropy → 43-char base64url


def generate_api_key() -> str:
    """Generate a new raw API key. Show to user once; never store unhashed."""
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(API_KEY_BYTES)}"


def hash_api_key(raw_key: str) -> str:
    """SHA-256 of the raw key. Stable, fast, suitable for token lookup."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def is_well_formed(raw_key: str) -> bool:
    return raw_key.startswith(API_KEY_PREFIX) and len(raw_key) > len(API_KEY_PREFIX) + 16
