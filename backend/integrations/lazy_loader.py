"""Lazy loader for optional integrations.

Prevents import errors from crashing the entire app when optional
dependencies or configurations are missing.
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


def get_google_drive_client() -> Optional[Any]:
    """Lazy-load Google Drive client."""
    try:
        from backend.integrations.google_drive_docs import (
            create_research_packet,
            create_transcript_doc,
        )
        return {
            "create_research_packet": create_research_packet,
            "create_transcript_doc": create_transcript_doc,
        }
    except ImportError as e:
        logger.warning(f"Google Drive integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Google Drive client initialization failed: {e}")
        return None


def get_reddit_client() -> Optional[Any]:
    """Lazy-load Reddit (PRAW) client."""
    try:
        from backend.integrations.reddit_client import search_reddit
        return {"search_reddit": search_reddit}
    except ImportError as e:
        logger.warning(f"Reddit integration not available (missing PRAW?): {e}")
        return None
    except Exception as e:
        logger.warning(f"Reddit client initialization failed: {e}")
        return None


def get_perplexity_client() -> Optional[Any]:
    """Lazy-load Perplexity client."""
    try:
        from backend.integrations.perplexity_client import (
            research_map,
            source_shortlist,
        )
        return {
            "research_map": research_map,
            "source_shortlist": source_shortlist,
        }
    except ImportError as e:
        logger.warning(f"Perplexity integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Perplexity client initialization failed: {e}")
        return None


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
        from backend.integrations.youtube_enumeration import enumerate_youtube_videos
        return {"enumerate_youtube_videos": enumerate_youtube_videos}
    except ImportError as e:
        logger.warning(f"YouTube integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"YouTube client initialization failed: {e}")
        return None


def get_transcript_client() -> Optional[Any]:
    """Lazy-load transcript extraction client."""
    try:
        from backend.integrations.transcripts import extract_transcripts_batch
        return {"extract_transcripts_batch": extract_transcripts_batch}
    except ImportError as e:
        logger.warning(f"Transcript integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Transcript client initialization failed: {e}")
        return None


def get_web_capture_client() -> Optional[Any]:
    """Lazy-load web capture client."""
    try:
        from backend.integrations.jina_reader import capture_web_content
        return {"capture_web_content": capture_web_content}
    except ImportError as e:
        logger.warning(f"Web capture integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Web capture client initialization failed: {e}")
        return None


def get_slack_client() -> Optional[Any]:
    """Lazy-load Slack client."""
    try:
        from backend.integrations.slack import post_slack_message
        return {"post_slack_message": post_slack_message}
    except ImportError as e:
        logger.warning(f"Slack integration not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Slack client initialization failed: {e}")
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
    """Check if an integration is available without loading it."""
    loaders = {
        "google_drive": get_google_drive_client,
        "reddit": get_reddit_client,
        "perplexity": get_perplexity_client,
        "openai": get_openai_client,
        "youtube": get_youtube_client,
        "transcripts": get_transcript_client,
        "web_capture": get_web_capture_client,
        "slack": get_slack_client,
    }
    loader = loaders.get(integration_name)
    if not loader:
        return False
    return loader() is not None
