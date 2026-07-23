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

# General Settings
LOG_LEVEL = logging.INFO
MAX_CONCURRENT_REQUESTS = 3
MAX_RETRIES = 3
TIMEOUT_SECONDS = 20.0

# Network Settings
DEFAULT_HEADERS = {
            "Accept": "application/json, text/html, application/xhtml+xml, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Chromium";v="120", "Google Chrome";v="120", "Not?A_Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

config = get_settings()
