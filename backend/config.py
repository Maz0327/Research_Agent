"""Configuration settings loader using Pydantic and python-dotenv."""
from functools import lru_cache
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv
from loguru import logger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve repo root: backend/config.py -> backend -> repo root
ROOT = Path(__file__).resolve().parents[1]
env_path = ROOT / ".env"

# Load .env file from project root
load_dotenv(dotenv_path=env_path, override=False)

# Sanity check: log (debug only) that .env path was attempted
if env_path.exists():
    logger.debug(f"Loaded .env from: {env_path}")
else:
    logger.debug(f".env file not found at: {env_path} (using environment variables only)")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # General app config
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # CORS configuration
    frontend_origins: Optional[str] = Field(
        default=None, alias="FRONTEND_ORIGINS",
        description="Comma-separated list of allowed frontend origins for CORS"
    )
    
    # Supabase (optional - only needed for job persistence)
    supabase_url: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    supabase_service_role_key: Optional[str] = Field(
        default=None, alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    supabase_jwt_secret: Optional[str] = Field(
        default=None, alias="SUPABASE_JWT_SECRET",
        description="JWT secret from Supabase for verifying auth tokens"
    )
    supabase_jwt_audience: str = Field(
        default="authenticated", alias="SUPABASE_JWT_AUDIENCE",
        description="Expected JWT audience claim (default: 'authenticated' for Supabase)"
    )
    
    # Slack integration
    slack_signing_secret: Optional[str] = Field(default=None, alias="SLACK_SIGNING_SECRET")
    slack_bot_token: Optional[str] = Field(default=None, alias="SLACK_BOT_TOKEN")
    
    # OpenAI API (for LLM operations)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    
    # Perplexity AI API
    perplexity_api_key: Optional[str] = Field(default=None, alias="PERPLEXITY_API_KEY")
    
    # YouTube Data API v3
    youtube_api_key: Optional[str] = Field(default=None, alias="YOUTUBE_API_KEY")
    
    # Google OAuth (for Drive and Docs access)
    google_oauth_client_id: Optional[str] = Field(default=None, alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    google_oauth_refresh_token: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_REFRESH_TOKEN"
    )
    google_drive_root_folder_id: Optional[str] = Field(
        default=None, alias="GOOGLE_DRIVE_ROOT_FOLDER_ID"
    )
    
    # Optional login credentials (for future phases)
    reddit_username: Optional[str] = Field(default=None, alias="REDDIT_USERNAME")
    reddit_password: Optional[str] = Field(default=None, alias="REDDIT_PASSWORD")
    twitter_username: Optional[str] = Field(default=None, alias="TWITTER_USERNAME")
    twitter_password: Optional[str] = Field(default=None, alias="TWITTER_PASSWORD")

    # PRD v4.3: Tavily API (PRIMARY search)
    tavily_api_key: Optional[str] = Field(
        default=None, alias="TAVILY_API_KEY",
        description="Tavily API key for web search and extraction (PRIMARY)"
    )

    # PRD v4.3: Supadata API (PRIMARY transcription)
    supadata_api_key: Optional[str] = Field(
        default=None, alias="SUPADATA_API_KEY",
        description="Supadata API key for multi-platform transcription (PRIMARY)"
    )

    # PRD v4.3: Feature flags
    enable_quality_gate: bool = Field(
        default=True, alias="ENABLE_QUALITY_GATE",
        description="Enable Quality Gate filtering between discovery and extraction"
    )
    enable_niches: bool = Field(
        default=True, alias="ENABLE_NICHES",
        description="Enable niche overlay system for specialized research modes"
    )

    @field_validator('supabase_jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, v: Optional[str]) -> Optional[str]:
        """Validate JWT secret strength to prevent weak secrets."""
        if v is None:
            return v

        if len(v) < 32:
            logger.warning(
                "SUPABASE_JWT_SECRET is weak (< 32 characters). "
                "This is a security risk in production."
            )
            # Only raise in production environment
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("JWT secret must be at least 32 characters in production")

        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Validation helpers for different stages/features
class MissingRequiredSettingError(RuntimeError):
    """Raised when a required setting is missing for a specific feature."""
    pass


def require_supabase() -> Settings:
    """
    Get settings and validate Supabase configuration is present.
    
    Raises:
        MissingRequiredSettingError: If Supabase settings are missing
    """
    settings = get_settings()
    if not settings.supabase_url:
        raise MissingRequiredSettingError(
            "SUPABASE_URL is required for job persistence. "
            "Please set it in your .env file."
        )
    if not settings.supabase_service_role_key:
        raise MissingRequiredSettingError(
            "SUPABASE_SERVICE_ROLE_KEY is required for job persistence. "
            "Please set it in your .env file."
        )
    return settings


def require_youtube() -> Settings:
    """
    Get settings and validate YouTube API key is present.
    
    Raises:
        MissingRequiredSettingError: If YouTube API key is missing
    """
    settings = get_settings()
    if not settings.youtube_api_key:
        raise MissingRequiredSettingError(
            "YOUTUBE_API_KEY is required for YouTube integration. "
            "Please set it in your .env file."
        )
    return settings


def require_openai() -> Settings:
    """
    Get settings and validate OpenAI API key is present.
    
    Raises:
        MissingRequiredSettingError: If OpenAI API key is missing
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise MissingRequiredSettingError(
            "OPENAI_API_KEY is required for LLM operations. "
            "Please set it in your .env file."
        )
    return settings


def require_perplexity() -> Settings:
    """
    Get settings and validate Perplexity API key is present.
    
    Raises:
        MissingRequiredSettingError: If Perplexity API key is missing
    """
    settings = get_settings()
    if not settings.perplexity_api_key:
        raise MissingRequiredSettingError(
            "PERPLEXITY_API_KEY is required for web search. "
            "Please set it in your .env file."
        )
    return settings


def require_slack() -> Settings:
    """
    Get settings and validate Slack configuration is present.
    
    Raises:
        MissingRequiredSettingError: If Slack settings are missing
    """
    settings = get_settings()
    if not settings.slack_signing_secret:
        raise MissingRequiredSettingError(
            "SLACK_SIGNING_SECRET is required for Slack integration. "
            "Please set it in your .env file."
        )
    if not settings.slack_bot_token:
        raise MissingRequiredSettingError(
            "SLACK_BOT_TOKEN is required for Slack integration. "
            "Please set it in your .env file."
        )
    return settings


def require_google_oauth() -> Settings:
    """
    Get settings and validate Google OAuth configuration is present.

    Raises:
        MissingRequiredSettingError: If Google OAuth settings are missing
    """
    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise MissingRequiredSettingError(
            "GOOGLE_OAUTH_CLIENT_ID is required for Google Drive/Docs integration. "
            "Please set it in your .env file."
        )
    if not settings.google_oauth_client_secret:
        raise MissingRequiredSettingError(
            "GOOGLE_OAUTH_CLIENT_SECRET is required for Google Drive/Docs integration. "
            "Please set it in your .env file."
        )
    if not settings.google_oauth_refresh_token:
        raise MissingRequiredSettingError(
            "GOOGLE_OAUTH_REFRESH_TOKEN is required for Google Drive/Docs integration. "
            "Please set it in your .env file."
        )
    return settings


def require_tavily() -> Settings:
    """
    Get settings and validate Tavily API key is present.

    PRD v4.3: Tavily is the PRIMARY search API.

    Raises:
        MissingRequiredSettingError: If Tavily API key is missing
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        raise MissingRequiredSettingError(
            "TAVILY_API_KEY is required for web search (PRIMARY). "
            "Please set it in your .env file."
        )
    return settings


def require_supadata() -> Settings:
    """
    Get settings and validate Supadata API key is present.

    PRD v4.3: Supadata is the PRIMARY transcription API.

    Raises:
        MissingRequiredSettingError: If Supadata API key is missing
    """
    settings = get_settings()
    if not settings.supadata_api_key:
        raise MissingRequiredSettingError(
            "SUPADATA_API_KEY is required for transcription (PRIMARY). "
            "Please set it in your .env file."
        )
    return settings
