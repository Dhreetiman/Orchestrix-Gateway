from app.core.security import API_KEY_PREFIX, generate_api_key, hash_api_key, is_well_formed


def test_generated_key_shape() -> None:
    k = generate_api_key()
    assert k.startswith(API_KEY_PREFIX)
    assert is_well_formed(k)


def test_hash_is_deterministic_and_64_hex() -> None:
    k = "ogw_abcdef0123456789"
    d = hash_api_key(k)
    assert d == hash_api_key(k)
    assert len(d) == 64
    assert all(c in "0123456789abcdef" for c in d)


def test_malformed_keys_rejected() -> None:
    assert not is_well_formed("")
    assert not is_well_formed("not_ogw_prefix")
    assert not is_well_formed("ogw_short")
