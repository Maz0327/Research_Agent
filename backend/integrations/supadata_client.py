"""Supadata API client for multi-platform transcription.

Supadata is the PRIMARY transcription source for PRD v4.3.
Supports YouTube, TikTok, Instagram, X (Twitter), and Facebook.

Pricing (validated Dec 2024):
- Native transcript: 1 credit
- AI-generated transcript: 1 credit + compute time
- Web scrape: 1 credit
- Free tier: 100 requests

API Documentation: https://docs.supadata.ai/get-transcript

Dec 2025: Removed SDK, using HTTP-only for reliability.
SDK had inconsistent behavior on cloud environments (Railway, AWS)
causing "'function' object has no attribute 'get'" errors.
"""
import os
from typing import Dict, Optional, Any
from enum import Enum

import httpx
from loguru import logger

from backend.utils.error_handling import sanitize_error_message
from backend.utils.rate_limiter import with_rate_limit


class TranscriptMode(str, Enum):
    """Transcription mode for Supadata API."""
    NATIVE = "native"      # Only fetch existing transcripts (cheaper)
    GENERATE = "generate"  # Generate with AI if not available (more expensive)
    AUTO = "auto"          # Try native first, then generate


class Platform(str, Enum):
    """Supported platforms for Supadata."""
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    FACEBOOK = "facebook"


class SupadataError(Exception):
    """Exception raised for Supadata API errors."""
    pass


class SupadataClient:
    """
    Supadata API client for multi-platform transcription (HTTP-only).

    PRIMARY source for transcripts per PRD v4.3.
    Fallback chain: Supadata → Whisper
    """

    BASE_URL = "https://api.supadata.ai/v1"

    def __init__(self):
        """Initialize Supadata HTTP client using Settings for API key."""
        from backend.config import get_settings
        settings = get_settings()
        self.api_key = settings.supadata_api_key
        if not self.api_key:
            raise ValueError("SUPADATA_API_KEY is required for transcription")

        self.http = httpx.Client(
            base_url=self.BASE_URL,
            headers={"x-api-key": self.api_key},
            timeout=60.0,  # Transcription can take up to 60s
        )

    @with_rate_limit("supadata")
    def get_transcript(
        self,
        url: str,
        mode: TranscriptMode = TranscriptMode.NATIVE,
        lang: str = "en",
    ) -> Dict[str, Any]:
        """
        Get transcript for a video URL.

        Args:
            url: Video URL (YouTube, TikTok, Instagram, Twitter, Facebook)
            mode: Transcript mode (native, generate, auto)
            lang: Language code (default: en)

        Returns:
            Dict with transcript text and metadata

        Raises:
            SupadataError: If API call fails
        """
        try:
            logger.info(f"Supadata transcript: {url[:50]}... (mode={mode.value})")

            params = {
                "url": url,
                "mode": mode.value,
                "lang": lang,
            }

            response = self.http.get("/transcript", params=params)

            if response.status_code != 200:
                error_text = response.text[:200] if response.text else "No error message"
                raise SupadataError(f"API returned {response.status_code}: {error_text}")

            data = response.json()

            # Supadata returns content as list of segments or string
            raw_content = data.get("content") or data.get("text")
            if isinstance(raw_content, list):
                # Join segment texts into single string
                text = " ".join(
                    seg.get("text", "") for seg in raw_content if isinstance(seg, dict)
                )
            elif raw_content:
                text = str(raw_content)
            else:
                text = ""

            return {
                "text": text,
                "url": url,
                "method": f"supadata_{mode.value}",
                "lang": data.get("lang", lang),
                "duration_seconds": data.get("duration"),
                "cost_credits": 1,
            }

        except httpx.HTTPError as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Supadata HTTP error: {sanitized}")
            raise SupadataError(f"HTTP error: {sanitized}") from e
        except SupadataError:
            raise
        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Supadata transcript failed: {sanitized}")
            raise SupadataError(f"Failed to get transcript: {sanitized}") from e

    def get_transcript_native(self, url: str, lang: str = "en") -> Dict[str, Any]:
        """
        Get only existing (native) transcripts.

        This is the cheapest option - only fetches transcripts
        that already exist on the platform (e.g., YouTube captions).
        """
        return self.get_transcript(url, mode=TranscriptMode.NATIVE, lang=lang)

    def generate_transcript(self, url: str, lang: str = "en") -> Dict[str, Any]:
        """
        Generate transcript using AI.

        This is more expensive but works when native transcripts
        don't exist. Uses AI to transcribe the audio.

        Cost: 1 credit + compute time (up to 60s for long videos)
        """
        return self.get_transcript(url, mode=TranscriptMode.GENERATE, lang=lang)

    @with_rate_limit("supadata")
    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape content from a web URL.

        Args:
            url: Web URL to scrape

        Returns:
            Dict with scraped content
        """
        try:
            logger.info(f"Supadata scrape: {url[:50]}...")

            response = self.http.get("/web/scrape", params={"url": url})

            if response.status_code != 200:
                raise SupadataError(f"Scrape failed: {response.status_code}")

            data = response.json()
            return {
                "content": data.get("content"),
                "url": url,
                "method": "supadata_scrape",
                "cost_credits": 1,
            }

        except httpx.HTTPError as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Supadata scrape HTTP error: {sanitized}")
            raise SupadataError(f"HTTP error: {sanitized}") from e
        except SupadataError:
            raise
        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Supadata scrape failed: {sanitized}")
            raise SupadataError(f"Failed to scrape URL: {sanitized}") from e

    @with_rate_limit("supadata")
    def fetch_metadata(self, url: str) -> Dict[str, Any]:
        """
        Fetch unified metadata for a video/content URL.

        Supadata returns a unified schema with: platform, title, author, stats,
        media (thumbnailUrl, duration), createdAt, etc.

        Args:
            url: Video URL (YouTube, TikTok, Instagram, Twitter, Facebook)

        Returns:
            Dict with unified metadata schema

        Note:
            This is an additive feature - failures should not block the pipeline.
            Callers should handle exceptions gracefully.
        """
        try:
            logger.info(f"Supadata metadata: {url[:50]}...")

            response = self.http.get("/metadata", params={"url": url})

            if response.status_code != 200:
                error_text = response.text[:200] if response.text else "No error message"
                raise SupadataError(f"Metadata API returned {response.status_code}: {error_text}")

            data = response.json()

            logger.info(f"Supadata metadata success: platform={data.get('platform')}, title={data.get('title', '')[:30]}...")

            return data

        except httpx.HTTPError as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.warning(f"Supadata metadata HTTP error: {sanitized}")
            raise SupadataError(f"HTTP error: {sanitized}") from e
        except SupadataError:
            raise
        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.warning(f"Supadata metadata failed: {sanitized}")
            raise SupadataError(f"Failed to get metadata: {sanitized}") from e

    def detect_platform(self, url: str) -> Optional[Platform]:
        """
        Detect which platform a URL belongs to.

        Args:
            url: Video URL

        Returns:
            Platform enum or None if unknown
        """
        url_lower = url.lower()

        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return Platform.YOUTUBE
        elif "tiktok.com" in url_lower:
            return Platform.TIKTOK
        elif "instagram.com" in url_lower:
            return Platform.INSTAGRAM
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return Platform.TWITTER
        elif "facebook.com" in url_lower or "fb.watch" in url_lower:
            return Platform.FACEBOOK
        else:
            return None


# Convenience functions for pipeline use

def fetch_transcript_supadata(
    url: str,
    mode: str = "native",
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to fetch transcript with Supadata.

    Returns None if Supadata is not configured or fails.
    """
    try:
        client = SupadataClient()
        transcript_mode = TranscriptMode(mode)
        return client.get_transcript(url, mode=transcript_mode)
    except Exception as e:
        sanitized = sanitize_error_message(e, include_type=False)
        logger.warning(f"Supadata transcript failed: {sanitized}")
        return None


def is_supadata_available() -> bool:
    """Check if Supadata is available and configured."""
    from backend.config import get_settings
    return bool(get_settings().supadata_api_key)


def get_platform_reliability(platform: Platform) -> str:
    """
    Get reliability rating for a platform.

    Based on PRD v4.3 specifications.
    """
    reliability = {
        Platform.YOUTUBE: "high",
        Platform.TIKTOK: "medium",
        Platform.INSTAGRAM: "medium",
        Platform.TWITTER: "medium",
        Platform.FACEBOOK: "medium",
    }
    return reliability.get(platform, "low")


def fetch_video_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to fetch video metadata with Supadata.

    Returns None if Supadata is not configured or fails.
    This is an additive feature - failures should not block the pipeline.

    Args:
        url: Video URL

    Returns:
        Metadata dict or None on failure
    """
    try:
        if not is_supadata_available():
            logger.debug("Supadata not available for metadata fetch")
            return None

        client = SupadataClient()
        return client.fetch_metadata(url)
    except Exception as e:
        sanitized = sanitize_error_message(e, include_type=False)
        logger.warning(f"Supadata metadata failed (non-blocking): {sanitized}")
        return None
