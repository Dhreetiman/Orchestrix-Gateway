from app.cache.keys import NAMESPACE_CHAT, chat_cache_key, prompt_hash


def test_prompt_hash_stable_across_dict_order() -> None:
    a = prompt_hash(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.2,
    )
    b = prompt_hash(
        model="gpt-4o-mini",
        messages=[{"content": "hi", "role": "user"}],
        temperature=0.2,
    )
    assert a == b


def test_prompt_hash_changes_with_content() -> None:
    a = prompt_hash(model="m", messages=[{"role": "user", "content": "hi"}], temperature=0.0)
    b = prompt_hash(model="m", messages=[{"role": "user", "content": "hello"}], temperature=0.0)
    assert a != b


def test_prompt_hash_changes_with_temperature() -> None:
    msgs = [{"role": "user", "content": "hi"}]
    assert prompt_hash(model="m", messages=msgs, temperature=0.0) != prompt_hash(
        model="m", messages=msgs, temperature=0.1
    )


def test_chat_cache_key_is_namespaced() -> None:
    digest = "a" * 64
    key = chat_cache_key(prompt_digest=digest)
    assert key.startswith(NAMESPACE_CHAT + ":")
    assert key.endswith(digest)
