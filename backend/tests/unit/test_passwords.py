from app.core.passwords import hash_password, needs_rehash, verify_password


def test_hash_and_verify_roundtrip() -> None:
    h = hash_password("correct horse battery staple")
    assert verify_password(h, "correct horse battery staple") is True


def test_wrong_password_rejected() -> None:
    h = hash_password("secret123")
    assert verify_password(h, "wrong") is False


def test_hashes_are_unique_per_call() -> None:
    """Argon2 uses a random salt, so identical inputs must produce distinct hashes."""
    a = hash_password("hello")
    b = hash_password("hello")
    assert a != b
    assert verify_password(a, "hello") and verify_password(b, "hello")


def test_garbage_hash_does_not_raise() -> None:
    """Verifier must return False (not crash) on malformed stored hashes."""
    assert verify_password("not-an-argon2-hash", "anything") is False


def test_current_hash_does_not_need_rehash() -> None:
    h = hash_password("x")
    assert needs_rehash(h) is False
