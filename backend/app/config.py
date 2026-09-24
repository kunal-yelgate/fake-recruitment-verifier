"""Configuration settings loaded from environment variables or .env file."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Keys
    serpapi_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Cache configuration
    cache_db_path: str = "app_cache.db"
    cache_ttl_hours: int = 24

    # Allow CORS origins (development + common frontend ports)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://truerecruit-test.netlify.app",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
