"""Test fixtures.

Unit tests do not touch Postgres or Redis. Integration tests rely on the docker-compose stack
being up (run via `make up`) and use real Redis + Postgres.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("OPENAI_API_KEY", "")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
