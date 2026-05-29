import pytest

from app.core.exceptions import ProviderNotFoundError
from app.providers.mock import MockProvider
from app.providers.openai import OpenAIProvider
from app.routing.router import provider_for_model, reset_registry


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_registry()


def test_gpt_routes_to_openai() -> None:
    assert isinstance(provider_for_model("gpt-4o-mini"), OpenAIProvider)


def test_o1_routes_to_openai() -> None:
    assert isinstance(provider_for_model("o1-preview"), OpenAIProvider)


def test_mock_routes_to_mock() -> None:
    assert isinstance(provider_for_model("mock"), MockProvider)


def test_unknown_model_raises() -> None:
    with pytest.raises(ProviderNotFoundError):
        provider_for_model("nonsense-model-xyz")
