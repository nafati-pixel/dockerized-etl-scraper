from functools import cache
from typing import Literal

from pydantic import PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core State
    environment: Literal["development", "staging", "production"] = "development"
    debug_mode: bool = False

    # Database
    database_url: PostgresDsn

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment == "production":
            if self.debug_mode:
                raise ValueError("SECURITY ALERT: debug_mode must be False in production.")
            
            db_host = self.database_url.hosts()[0].host
            if db_host in ["localhost", "127.0.0.1", "::1"]:
                raise ValueError("CONFIGURATION ERROR: Production database cannot be localhost.")

        return self

@cache
def get_settings() -> Settings:
    return Settings()

config = get_settings()
