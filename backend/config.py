"""Configuration settings loader using Pydantic and python-dotenv."""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # API Keys (optional for Phase 1)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    perplexity_api_key: Optional[str] = Field(default=None, alias="PERPLEXITY_API_KEY")
    youtube_api_key: Optional[str] = Field(default=None, alias="YOUTUBE_API_KEY")
    google_service_account_json_path: Optional[str] = Field(
        default=None, alias="GOOGLE_SERVICE_ACCOUNT_JSON_PATH"
    )
    google_drive_root_folder_id: Optional[str] = Field(
        default=None, alias="GOOGLE_DRIVE_ROOT_FOLDER_ID"
    )
    supabase_url: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    supabase_service_role_key: Optional[str] = Field(
        default=None, alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    
    # Optional login credentials (for future phases)
    reddit_username: Optional[str] = Field(default=None, alias="REDDIT_USERNAME")
    reddit_password: Optional[str] = Field(default=None, alias="REDDIT_PASSWORD")
    twitter_username: Optional[str] = Field(default=None, alias="TWITTER_USERNAME")
    twitter_password: Optional[str] = Field(default=None, alias="TWITTER_PASSWORD")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

