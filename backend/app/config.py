"""Configuration settings loaded from environment variables or .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Keys
    serpapi_key: str | None = None
    # Optional account quota used only to expose a bounded operational metric.
    # SerpApi does not include account quota in every search response.
    serpapi_quota_limit: int | None = None
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    anthropic_api_key: str | None = None
    clerk_jwt_key: str | None = None
    clerk_issuer: str | None = None
    require_auth: bool = True

    # Server configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    rate_limit_per_min: int = 10
    url_fetch_timeout_seconds: float = 10.0
    url_fetch_max_bytes: int = 2_000_000
    url_fetch_max_redirects: int = 3

    # Cache configuration
    cache_db_path: str = "app_cache.db"
    cache_ttl_hours: int = 24

    # Allow CORS origins (development + common frontend ports)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
