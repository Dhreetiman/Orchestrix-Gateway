from app.services.cost_calculator import calculate_cost_usd


def test_known_model_exact_match() -> None:
    # gpt-4o: $2.50 in / $10.00 out per 1M tokens
    assert calculate_cost_usd("gpt-4o", 1_000_000, 0) == 2.5
    assert calculate_cost_usd("gpt-4o", 0, 1_000_000) == 10.0


def test_unknown_model_returns_zero() -> None:
    assert calculate_cost_usd("totally-made-up-model", 1000, 1000) == 0.0


def test_prefix_match_handles_dated_variants() -> None:
    # gpt-4o-2024-08-06 should match gpt-4o pricing via prefix
    assert calculate_cost_usd("gpt-4o-2024-08-06", 1_000_000, 0) == 2.5


def test_rounded_to_six_decimals() -> None:
    cost = calculate_cost_usd("gpt-4o-mini", 333, 777)
    # gpt-4o-mini: 0.15 / 0.60 per M
    expected = round((333 * 0.15 + 777 * 0.60) / 1_000_000, 6)
    assert cost == expected
