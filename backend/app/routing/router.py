"""Provider registry and model→provider routing with failover.

Phase 2: each model maps to a primary provider plus an optional ordered failover chain
(equivalents in another vendor's catalog). Failover only applies to non-streaming requests —
mid-stream provider switches are unsafe to replay.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.exceptions import ProviderNotFoundError
from app.providers.anthropic import AnthropicProvider
from app.providers.base import Provider
from app.providers.mock import MockProvider
from app.providers.openai import OpenAIProvider


@dataclass(frozen=True, slots=True)
class RoutePlan:
    """Ordered list of providers to try for a given model.

    The first entry is the requested provider; subsequent entries are equivalent fallbacks.
    """

    providers: tuple[Provider, ...]

    @property
    def primary(self) -> Provider:
        return self.providers[0]


def _build_registry() -> dict[str, Provider]:
    settings = get_settings()
    registry: dict[str, Provider] = {"mock": MockProvider()}
    # Register in dev even without a key, so /docs lists them; calls without a key error
    # at request time.
    if settings.openai_api_key or settings.app_env in {"development", "test"}:
        registry["openai"] = OpenAIProvider()
    if settings.anthropic_api_key or settings.app_env in {"development", "test"}:
        registry["anthropic"] = AnthropicProvider()
    return registry


_registry: dict[str, Provider] | None = None


def get_registry() -> dict[str, Provider]:
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def reset_registry() -> None:
    """Test helper."""
    global _registry
    _registry = None


# Model prefix → (primary, *failover) provider names.
# Failover targets should be roughly equivalent in cost/capability tier.
_MODEL_ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("gpt-4o-mini", ("openai", "anthropic")),
    ("gpt-4o", ("openai", "anthropic")),
    ("gpt-4", ("openai", "anthropic")),
    ("gpt-3.5", ("openai", "anthropic")),
    ("o1-", ("openai",)),
    ("o3-", ("openai",)),
    ("claude-3-5", ("anthropic", "openai")),
    ("claude-3", ("anthropic", "openai")),
    ("mock", ("mock",)),
)


def _route_names_for_model(model: str) -> tuple[str, ...]:
    for prefix, providers in _MODEL_ROUTES:
        if model.startswith(prefix):
            return providers
    raise ProviderNotFoundError(
        f"No provider configured for model '{model}'.", detail={"model": model}
    )


def plan_for_model(model: str, *, include_failover: bool | None = None) -> RoutePlan:
    """Build the ordered provider list to try for a given model."""
    settings = get_settings()
    if include_failover is None:
        include_failover = settings.enable_failover

    names = _route_names_for_model(model)
    if not include_failover:
        names = names[:1]

    registry = get_registry()
    providers: list[Provider] = []
    for name in names:
        if name in registry:
            providers.append(registry[name])
    if not providers:
        raise ProviderNotFoundError(
            f"None of the configured providers for '{model}' are available.",
            detail={"model": model, "tried": list(names)},
        )
    return RoutePlan(providers=tuple(providers))


def provider_for_model(model: str) -> Provider:
    """Convenience for callers that don't want failover (e.g. streaming)."""
    return plan_for_model(model, include_failover=False).primary
