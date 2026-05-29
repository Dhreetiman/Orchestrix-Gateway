"""Argon2id password hashing.

Argon2id is the OWASP-recommended hash for passwords in 2024+: memory-hard, side-channel
resistant, with sensible defaults from the argon2-cffi library. The parameters embedded
in each hash mean we can transparently upgrade cost factors over time without breaking
existing logins.
"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(stored_hash: str, plain: str) -> bool:
    try:
        _hasher.verify(stored_hash, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False
    return True


def needs_rehash(stored_hash: str) -> bool:
    """True if the stored hash uses older parameters than current defaults."""
    return _hasher.check_needs_rehash(stored_hash)
