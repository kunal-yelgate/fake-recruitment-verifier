"""Configuration settings loaded from environment variables or .env file."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Keys
    serpapi_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"
    anthropic_api_key: Optional[str] = None
    clerk_jwt_key: Optional[str] = None
    clerk_issuer: Optional[str] = None
    require_auth: bool = True

    # Server configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    rate_limit_per_min: int = 10

    # Cache configuration
    cache_db_path: str = "app_cache.db"
    cache_ttl_hours: int = 24

    # Allow CORS origins (development + common frontend ports)
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
