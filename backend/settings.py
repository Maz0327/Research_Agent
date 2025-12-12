# backend/settings.py

from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # <-- don't crash on unexpected env vars
    )

    # General app config
    environment: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Core external APIs
    openai_api_key: str | None = None
    perplexity_api_key: str | None = None

    # Supabase
    supabase_url: AnyHttpUrl
    supabase_service_role_key: str
    redis_url: str = "redis://localhost:6379/0"

    # YouTube
    youtube_api_key: str | None = None

    # Google Drive (optional for now)
    google_service_account_json_path: str | None = None
    google_drive_root_folder_id: str | None = None

    # Reddit / Twitter (optional; used later for scraping)
    reddit_username: str | None = None
    reddit_password: str | None = None
    twitter_username: str | None = None
    twitter_password: str | None = None


@lru_cache()
def get_settings() -> Settings:
    return Settings()
