"""Lazy loader for optional integrations.

Prevents import errors from crashing the entire app when optional
dependencies or configurations are missing.

Updated 2026-01-19: Removed legacy integrations (google_drive, slack, reddit, perplexity).
"""
from typing import Any, Optional, Callable
from loguru import logger


class IntegrationUnavailable:
    """Placeholder for unavailable integrations."""

    def __init__(self, name: str, reason: str):
        self.name = name
        self.reason = reason

    def __call__(self, *args, **kwargs) -> None:
        raise RuntimeError(f"Integration '{self.name}' unavailable: {self.reason}")

    def __getattr__(self, item: str) -> "IntegrationUnavailable":
        return self


def get_openai_client() -> Optional[Any]:
    """Lazy-load OpenAI client functions."""
    try:
        from backend.integrations.openai_client import (
            plan_job,
            generate_short_title,
            _safe_default_config,
        )
        return {
            "plan_job": plan_job,
            "generate_short_title": generate_short_title,
            "_safe_default_config": _safe_default_config,
        }
    except ImportError as e:
        logger.warning(f"OpenAI integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"OpenAI client initialization failed: {e}")
        return None


def get_youtube_client() -> Optional[Any]:
    """Lazy-load YouTube enumeration client."""
    try:
        from backend.integrations.youtube_client import search_youtube_videos
        return {"search_youtube_videos": search_youtube_videos}
    except ImportError as e:
        logger.warning(f"YouTube integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"YouTube client initialization failed: {e}")
        return None


def get_transcript_client() -> Optional[Any]:
    """Lazy-load transcript extraction client."""
    try:
        from backend.integrations.transcripts import fetch_transcripts_batch
        return {"fetch_transcripts_batch": fetch_transcripts_batch}
    except ImportError as e:
        logger.warning(f"Transcript integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Transcript client initialization failed: {e}")
        return None


def get_web_capture_client() -> Optional[Any]:
    """Lazy-load web capture client."""
    try:
        from backend.integrations.web_capture import capture_web_content
        return {"capture_web_content": capture_web_content}
    except ImportError as e:
        logger.warning(f"Web capture integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Web capture client initialization failed: {e}")
        return None


def safe_import(import_fn: Callable, name: str) -> Optional[Any]:
    """
    Safely attempt an import, returning None on failure.

    Args:
        import_fn: A callable that performs the import
        name: Name of the integration for logging

    Returns:
        The imported module/function or None if unavailable
    """
    try:
        return import_fn()
    except ImportError as e:
        logger.warning(f"{name} not available (missing dependency): {e}")
        return None
    except Exception as e:
        logger.warning(f"{name} initialization failed: {e}")
        return None


# Convenience function for stages to check availability
def is_integration_available(integration_name: str) -> bool:
    """Check if an integration is available without loading it.

    Note: Legacy integrations have been removed (2026-01-19):
    - google_drive, slack, reddit, perplexity, exa, serper, tavily
    """
    loaders = {
        "openai": get_openai_client,
        "youtube": get_youtube_client,
        "transcripts": get_transcript_client,
        "web_capture": get_web_capture_client,
    }
    loader = loaders.get(integration_name)
    if not loader:
        return False
    return loader() is not None
