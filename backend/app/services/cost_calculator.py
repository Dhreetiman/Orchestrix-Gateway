"""Static pricing tables → USD cost from token counts.

Prices are USD per 1M tokens, sourced from public provider pricing pages. Update when models
change — analytics rely on this being directionally correct, not exact to the cent.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPrice:
    input_per_million: float  # USD per 1M input tokens
    output_per_million: float  # USD per 1M output tokens


# May 2026 pricing snapshot. Adjust as tables drift.
_PRICES: dict[str, ModelPrice] = {
    # OpenAI
    "gpt-4o": ModelPrice(2.50, 10.00),
    "gpt-4o-mini": ModelPrice(0.15, 0.60),
    "gpt-4-turbo": ModelPrice(10.00, 30.00),
    "gpt-4": ModelPrice(30.00, 60.00),
    "gpt-3.5-turbo": ModelPrice(0.50, 1.50),
    "o1-preview": ModelPrice(15.00, 60.00),
    "o1-mini": ModelPrice(3.00, 12.00),
    # Anthropic (Claude)
    "claude-3-5-sonnet": ModelPrice(3.00, 15.00),
    "claude-3-5-haiku": ModelPrice(0.80, 4.00),
    "claude-3-opus": ModelPrice(15.00, 75.00),
    "claude-3-sonnet": ModelPrice(3.00, 15.00),
    "claude-3-haiku": ModelPrice(0.25, 1.25),
}

# Unknown models cost nothing rather than crashing the request pipeline.
_FALLBACK = ModelPrice(0.0, 0.0)


def _lookup(model: str) -> ModelPrice:
    if model in _PRICES:
        return _PRICES[model]
    # Best-effort prefix match (e.g. gpt-4o-2024-08-06 → gpt-4o, claude-3-5-sonnet-20241022 → claude-3-5-sonnet)
    for key, price in _PRICES.items():
        if model.startswith(key):
            return price
    return _FALLBACK


def calculate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price = _lookup(model)
    return round(
        (prompt_tokens * price.input_per_million + completion_tokens * price.output_per_million)
        / 1_000_000,
        6,
    )
