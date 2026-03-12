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
    
    # Admin configuration
    admin_emails: Optional[str] = Field(
        default=None, alias="ADMIN_EMAILS",
        description="Comma-separated list of admin email addresses for role-based access"
    )

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

    # Tavily API (FALLBACK search - demoted due to 10% 502 error rate)
    tavily_api_key: Optional[str] = Field(
        default=None, alias="TAVILY_API_KEY",
        description="Tavily API key for web search (FALLBACK - 10% error rate)"
    )

    # === RESEARCH-VALIDATED API STACK (Dec 2025) ===

    # Exa.ai (PRIMARY semantic search - 94.9% accuracy)
    exa_api_key: Optional[str] = Field(
        default=None, alias="EXA_API_KEY",
        description="Exa API key for semantic search (PRIMARY - 94.9% accuracy)"
    )

    # Serper (BACKUP keyword search - $1/1k, 93.5% success)
    serper_api_key: Optional[str] = Field(
        default=None, alias="SERPER_API_KEY",
        description="Serper API key for backup keyword search ($1/1k)"
    )

    # Google Gemini API (Planning + Vision)
    google_api_key: Optional[str] = Field(
        default=None, alias="GOOGLE_API_KEY",
        description="Google API key for Gemini 2.5 Flash/Pro (planning, vision)"
    )

    # Anthropic Claude API (Complex synthesis)
    anthropic_api_key: Optional[str] = Field(
        default=None, alias="ANTHROPIC_API_KEY",
        description="Anthropic API key for Claude Sonnet (complex synthesis)"
    )

    # Kimi/Moonshot API (Visual analysis)
    kimi_api_key: Optional[str] = Field(
        default=None, alias="KIMI_API_KEY",
        description="Moonshot API key for Kimi K2.5 Vision (frame analysis)"
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

    # Performance: Parallel semantic extraction
    semantic_extraction_max_workers: int = Field(
        default=3, alias="SEMANTIC_EXTRACTION_MAX_WORKERS",
        description="Max concurrent sources during semantic extraction (2-5 recommended)"
    )

    # Performance: Conditional LLM Judge
    llm_judge_conditional: bool = Field(
        default=False, alias="LLM_JUDGE_CONDITIONAL",
        description="Only run LLM Judge when confidence < HIGH or warnings > threshold"
    )
    llm_judge_warning_threshold: int = Field(
        default=2, alias="LLM_JUDGE_WARNING_THRESHOLD",
        description="Warning count threshold to trigger LLM Judge when conditional mode is on"
    )

    # Reddit PRAW configuration
    reddit_client_id: Optional[str] = Field(
        default=None, alias="REDDIT_CLIENT_ID",
        description="Reddit API client ID for PRAW"
    )
    reddit_client_secret: Optional[str] = Field(
        default=None, alias="REDDIT_CLIENT_SECRET",
        description="Reddit API client secret for PRAW"
    )
    default_subreddits: str = Field(
        default="politics,news,worldnews,OutOfTheLoop,NeutralPolitics",
        alias="DEFAULT_SUBREDDITS",
        description="Comma-separated list of default subreddits for research"
    )

    def get_default_subreddits(self) -> list[str]:
        """Get list of default subreddits from config."""
        return [s.strip() for s in self.default_subreddits.split(",") if s.strip()]

    # Jina Reader configuration
    jina_api_url: str = Field(
        default="https://r.jina.ai/",
        alias="JINA_API_URL",
        description="Jina Reader API URL"
    )
    jina_api_key: Optional[str] = Field(
        default=None, alias="JINA_AI_READER_API_KEY",
        description="Jina AI Reader API key (optional, enables higher rate limits)"
    )

    # === TIMEOUT CONFIGURATION ===
    # Centralized timeout values for HTTP requests (in seconds)
    timeout_api_default: float = Field(
        default=30.0, alias="TIMEOUT_API_DEFAULT",
        description="Default timeout for API requests"
    )
    timeout_supabase: float = Field(
        default=5.0, alias="TIMEOUT_SUPABASE",
        description="Timeout for Supabase/database queries"
    )
    timeout_transcription: float = Field(
        default=60.0, alias="TIMEOUT_TRANSCRIPTION",
        description="Timeout for transcription services (Supadata)"
    )
    timeout_whisper: float = Field(
        default=300.0, alias="TIMEOUT_WHISPER",
        description="Timeout for Whisper API (local processing)"
    )
    timeout_factcheck: float = Field(
        default=15.0, alias="TIMEOUT_FACTCHECK",
        description="Timeout for fact-checking services"
    )
    timeout_youtube: float = Field(
        default=10.0, alias="TIMEOUT_YOUTUBE",
        description="Timeout for YouTube API requests"
    )

    @field_validator('supabase_jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, v: Optional[str]) -> Optional[str]:
        """Validate JWT secret strength to prevent weak secrets.

        Security requirements (enforced in ALL environments):
        - Minimum 64 characters
        - Sufficient entropy (at least 20 unique characters)
        """
        if v is None:
            return v

        # Enforce 64+ character minimum in ALL environments
        if len(v) < 64:
            raise ValueError(
                "JWT secret must be at least 64 characters. "
                f"Current length: {len(v)}. "
                "Generate a secure secret with: openssl rand -base64 48"
            )

        # Check entropy - reject low-entropy strings (sequential/repeated patterns)
        unique_chars = len(set(v))
        if unique_chars < 20:
            raise ValueError(
                f"JWT secret has insufficient entropy ({unique_chars} unique chars). "
                "Use a randomly generated secret with high entropy."
            )

        logger.debug("JWT secret validation passed (64+ chars, good entropy)")
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


# === RESEARCH-VALIDATED API STACK HELPERS (Dec 2025) ===


def require_exa() -> Settings:
    """
    Get settings and validate Exa API key is present.

    Exa is the PRIMARY semantic search (94.9% accuracy).

    Raises:
        MissingRequiredSettingError: If Exa API key is missing
    """
    settings = get_settings()
    if not settings.exa_api_key:
        raise MissingRequiredSettingError(
            "EXA_API_KEY is required for semantic search (PRIMARY). "
            "Please set it in your .env file."
        )
    return settings


def require_serper() -> Settings:
    """
    Get settings and validate Serper API key is present.

    Serper is the BACKUP keyword search ($1/1k).

    Raises:
        MissingRequiredSettingError: If Serper API key is missing
    """
    settings = get_settings()
    if not settings.serper_api_key:
        raise MissingRequiredSettingError(
            "SERPER_API_KEY is required for backup keyword search. "
            "Please set it in your .env file."
        )
    return settings


def require_gemini() -> Settings:
    """
    Get settings and validate Google API key is present for Gemini.

    Gemini 2.5 Flash/Pro is used for planning and vision tasks.

    Raises:
        MissingRequiredSettingError: If Google API key is missing
    """
    settings = get_settings()
    if not settings.google_api_key:
        raise MissingRequiredSettingError(
            "GOOGLE_API_KEY is required for Gemini planning/vision. "
            "Please set it in your .env file."
        )
    return settings


def require_anthropic() -> Settings:
    """
    Get settings and validate Anthropic API key is present.

    Claude Sonnet is used for complex synthesis tasks.

    Raises:
        MissingRequiredSettingError: If Anthropic API key is missing
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise MissingRequiredSettingError(
            "ANTHROPIC_API_KEY is required for Claude synthesis. "
            "Please set it in your .env file."
        )
    return settings


def require_kimi() -> Settings:
    """
    Get settings and validate Kimi API key is present for visual analysis.

    Kimi K2.5 Vision is used for frame-level video content classification.

    Raises:
        MissingRequiredSettingError: If Kimi API key is missing
    """
    settings = get_settings()
    if not settings.kimi_api_key:
        raise MissingRequiredSettingError(
            "KIMI_API_KEY is required for Kimi K2.5 visual analysis. "
            "Please set it in your .env file."
        )
    return settings


def require_reddit() -> Settings:
    """
    Get settings and validate Reddit PRAW credentials are present.

    Reddit PRAW is used for collecting Reddit discussions and comments.

    Raises:
        MissingRequiredSettingError: If Reddit credentials are missing
    """
    settings = get_settings()
    if not settings.reddit_client_id:
        raise MissingRequiredSettingError(
            "REDDIT_CLIENT_ID is required for Reddit PRAW integration. "
            "Please set it in your .env file."
        )
    if not settings.reddit_client_secret:
        raise MissingRequiredSettingError(
            "REDDIT_CLIENT_SECRET is required for Reddit PRAW integration. "
            "Please set it in your .env file."
        )
    return settings


# === STARTUP VALIDATION ===


def validate_jwt_config() -> tuple[bool, str]:
    """
    Validate JWT configuration at startup.

    Returns tuple of (is_valid, message).
    - If Supabase is not configured, returns (True, "Supabase not configured - JWT auth disabled")
    - If Supabase is configured but JWT secret missing, returns (False, error_message)
    - If all valid, returns (True, "JWT configuration valid")
    """
    settings = get_settings()

    # If Supabase is not configured at all, JWT auth is disabled (valid)
    if not settings.supabase_url:
        return True, "Supabase not configured - JWT auth disabled (in-memory mode)"

    # If Supabase is configured, JWT secret is required
    if not settings.supabase_jwt_secret:
        return False, (
            "SUPABASE_JWT_SECRET is required when SUPABASE_URL is set. "
            "Get it from Supabase Dashboard > Settings > API > JWT Settings."
        )

    # Check audience is set (has default, but warn if non-standard)
    if settings.supabase_jwt_audience != "authenticated":
        logger.warning(
            f"Non-standard JWT audience: {settings.supabase_jwt_audience}. "
            "Ensure this matches your Supabase configuration."
        )

    return True, f"JWT configuration valid (audience: {settings.supabase_jwt_audience})"
