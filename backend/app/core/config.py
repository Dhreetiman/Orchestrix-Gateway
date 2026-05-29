from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://orchestrix:orchestrix_dev@localhost:5432/orchestrix"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Cache
    cache_ttl_seconds: int = 3600
    cache_max_temperature: float = 0.3

    # Providers
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com/v1"

    # Rate limiting (Phase 2) — sliding window per API key. 0 disables.
    rate_limit_rpm: int = 60

    # Failover
    enable_failover: bool = True
    max_request_body_bytes: int = 1_048_576  # 1 MiB

    # CORS
    cors_origins: str = "http://localhost:3000"

    @field_validator("cors_origins")
    @classmethod
    def _split_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Memoized settings accessor. Override in tests with `get_settings.cache_clear()`."""
    return Settings()
