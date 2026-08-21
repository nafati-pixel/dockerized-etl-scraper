from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",   # unrelated env vars on the host shouldn't crash startup
    )

    # Database
    database_url: PostgresDsn = Field(
        ...,  # no default on purpose: forces every environment to set this
              # explicitly, rather than silently defaulting to localhost in prod
        description="postgresql+psycopg://user:pass@host:5432/dbname",
    )
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10

    # Logging
    log_level: str = "INFO"
    log_json: bool = False   # False = human-readable console for local dev.
                             # True for any environment shipping logs to an aggregator.

    # DLQ
    dlq_dir: str = "./dlq_output"

    # Resilience defaults (used by future non-file extractors, e.g.
    # an api_extractor.py, that actually need retry/rate-limit/breaker)
    retry_max_attempts: int = 3
    retry_base_delay_s: float = 1.0
    rate_limit_per_second: float = 5.0
    circuit_breaker_fail_max: int = 5
    circuit_breaker_reset_timeout_s: float = 30.0

    @field_validator(
        "retry_max_attempts",
        "retry_base_delay_s",
        "rate_limit_per_second",
        "circuit_breaker_fail_max",
        "circuit_breaker_reset_timeout_s",
    )
    @classmethod
    def _must_be_positive(cls, v: float) -> float:
        # A zero or negative value here isn't a valid "off switch" - it
        # breaks the backoff/rate math outright (e.g. division by a
        # zero rate in resilience/rate_limiter.py). Reject it at startup
        # rather than letting it surface as a confusing runtime error.
        if v <= 0:
            raise ValueError("resilience settings must be positive")
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Cached: Settings() is constructed (and env vars parsed/validated)
    ONCE per process and reused everywhere, instead of redoing that work
    on every call. lru_cache on a zero-argument function is effectively
    a lazy singleton.

    Tests that need different config should NOT rely on this cached
    singleton - construct Settings(**overrides) directly, bypassing
    get_settings() entirely, so each test gets exactly the config it needs.
    """
    return Settings()
