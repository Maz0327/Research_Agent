"""Transcript fetching for YouTube and multi-platform videos.

CLOUD-COMPATIBLE STACK (Dec 2025):
- youtube-transcript-api REMOVED - fails on cloud IPs (Railway, AWS, etc.)
- Fallback chain: Supadata → Whisper

Supports:
- YouTube (via Supadata, Whisper)
- TikTok (via Supadata)
- Instagram (via Supadata)
- Twitter/X (via Supadata)
- Facebook (via Supadata)
"""
import re
from enum import Enum
from typing import Optional

from loguru import logger
from pydantic import BaseModel

# NOTE: youtube-transcript-api REMOVED - fails on cloud IPs (Railway, AWS, GCP)
# See: https://github.com/jdepoix/youtube-transcript-api/issues/303
# Fallback chain: Supadata → Whisper (no youtube-transcript-api)

# Import Supadata client (PRIMARY per PRD v4.3)
from backend.integrations.supadata_client import (
    SupadataClient,
    SupadataError,
    TranscriptMode,
    is_supadata_available,
)


class TranscriptStatus(str, Enum):
    """Status of transcript fetch attempt."""
    AVAILABLE = "available"
    MISSING = "missing"
    ERROR = "error"


class TranscriptItem(BaseModel):
    """Transcript item model."""
    video_id: str
    video_url: str
    text: Optional[str] = None
    status: TranscriptStatus = TranscriptStatus.MISSING
    language: Optional[str] = None
    error_message: Optional[str] = None
    source: str = "supadata_native"  # supadata_native, supadata_ai, whisper
    platform: str = "youtube"  # youtube, tiktok, instagram, twitter, facebook
    cost_credits: float = 0.0  # API cost tracking


def _detect_platform(url: str) -> str:
    """Detect platform from URL."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    elif "instagram.com" in url_lower:
        return "instagram"
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    elif "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    return "unknown"


def _fetch_with_supadata(
    video_url: str,
    mode: TranscriptMode = TranscriptMode.NATIVE,
) -> tuple[Optional[str], Optional[str], Optional[str], float]:
    """
    Fetch transcript using Supadata API (PRIMARY per PRD v4.3).

    Args:
        video_url: Video URL (any supported platform)
        mode: Transcript mode (native or generate)

    Returns:
        Tuple of (text, language, error_message, cost_credits)
    """
    if not is_supadata_available():
        return None, None, "Supadata not configured", 0.0

    try:
        client = SupadataClient()
        result = client.get_transcript(video_url, mode=mode)

        text = result.get("text")
        if text:
            return (
                text,
                result.get("lang", "en"),
                None,
                result.get("cost_credits", 1.0),
            )
        else:
            return None, None, "Empty transcript returned", 0.0

    except SupadataError as e:
        return None, None, f"Supadata error: {e}", 0.0
    except Exception as e:
        logger.exception(f"Supadata unexpected error: {e}")
        return None, None, f"Supadata unexpected error: {e}", 0.0


def _extract_video_id(video_url_or_id: str) -> Optional[str]:
    """
    Extract video ID from URL or return as-is if already an ID.
    
    Supports:
    - Video ID: dQw4w9WgXcQ
    - Full URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    - Short URL: https://youtu.be/dQw4w9WgXcQ
    - Embed URL: https://www.youtube.com/embed/dQw4w9WgXcQ
    
    Args:
        video_url_or_id: Video URL or video ID
        
    Returns:
        Video ID string or None if extraction fails
    """
    # If it looks like a video ID (11 characters, alphanumeric, hyphens, underscores)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', video_url_or_id):
        return video_url_or_id
    
    # Extract from various URL patterns
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_url_or_id)
        if match:
            return match.group(1)
    
    logger.warning(f"Could not extract video ID from: {video_url_or_id}")
    return None


def _fetch_with_whisper(
    video_id: str,
    video_url: str,
    api_key: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """DEPRECATED: Dead code. Whisper fallback is wired in fetch_transcript_v2 via
    whisper_client.transcribe_with_whisper(). This stub is unused — only kept
    to avoid breaking any external references. See fetch_transcript_v2 lines 290-311.
    """
    logger.debug(f"DEPRECATED _fetch_with_whisper called for {video_id} — use fetch_transcript_v2")
    return None, None, "Use fetch_transcript_v2 which has real Whisper fallback"


def fetch_transcript(
    video_url_or_id: str,
    use_whisper: bool = False,
    whisper_api_key: Optional[str] = None,
    preferred_languages: Optional[list[str]] = None,
) -> TranscriptItem:
    """
    Fetch transcript for a YouTube video.

    DEPRECATED: Use fetch_transcript_v2 instead. This function now delegates to v2.

    Args:
        video_url_or_id: YouTube video URL or video ID
        use_whisper: Whether to use Whisper as fallback (default: False)
        whisper_api_key: Unused (kept for backward compatibility)
        preferred_languages: List of language codes to try (default: ['en'])

    Returns:
        TranscriptItem with transcript text if available, or status=missing if not
    """
    # Build full URL if video ID was passed
    if not video_url_or_id.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_url_or_id}"
    else:
        video_url = video_url_or_id

    # Delegate to cloud-compatible v2 implementation
    return fetch_transcript_v2(
        video_url=video_url,
        preferred_languages=preferred_languages,
        use_whisper_fallback=use_whisper,
    )


def fetch_transcript_v2(
    video_url: str,
    preferred_languages: Optional[list[str]] = None,
    use_whisper_fallback: bool = True,
) -> TranscriptItem:
    """
    Fetch transcript using cloud-compatible fallback chain.

    CLOUD-COMPATIBLE (Dec 2025):
    1. Supadata native (existing captions) - cheapest, works on cloud
    2. Supadata AI (generate transcript) - more expensive, works on cloud
    3. Whisper (final fallback, costly) - works on cloud

    NOTE: youtube-transcript-api REMOVED - fails on cloud IPs (Railway, AWS, GCP)

    Args:
        video_url: Video URL (YouTube, TikTok, Instagram, Twitter, Facebook)
        preferred_languages: List of language codes to try (default: ['en'])
        use_whisper_fallback: Whether to use Whisper as final fallback

    Returns:
        TranscriptItem with transcript text if available

    Example:
        >>> transcript = fetch_transcript_v2("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        >>> if transcript.status == TranscriptStatus.AVAILABLE:
        ...     print(f"Got transcript via {transcript.source}")
    """
    if preferred_languages is None:
        preferred_languages = ['en']

    platform = _detect_platform(video_url)
    video_id = _extract_video_id(video_url) if platform == "youtube" else ""

    errors = []

    # Tier 1: Supadata native (existing captions)
    logger.info(f"Tier 1: Trying Supadata native for {video_url[:50]}...")
    text, language, error, cost = _fetch_with_supadata(video_url, TranscriptMode.NATIVE)

    if text:
        logger.info(f"Supadata native success for {video_url[:50]}")
        return TranscriptItem(
            video_id=video_id,
            video_url=video_url,
            text=text,
            status=TranscriptStatus.AVAILABLE,
            language=language,
            source="supadata_native",
            platform=platform,
            cost_credits=cost,
        )
    else:
        if error:
            errors.append(f"supadata_native: {error}")

    # Tier 2: Supadata AI generation
    logger.info(f"Tier 2: Trying Supadata AI for {video_url[:50]}...")
    text, language, error, cost = _fetch_with_supadata(video_url, TranscriptMode.GENERATE)

    if text:
        logger.info(f"Supadata AI success for {video_url[:50]}")
        return TranscriptItem(
            video_id=video_id,
            video_url=video_url,
            text=text,
            status=TranscriptStatus.AVAILABLE,
            language=language,
            source="supadata_ai",
            platform=platform,
            cost_credits=cost,
        )
    else:
        if error:
            errors.append(f"supadata_ai: {error}")

    # Tier 3: youtube-transcript-api - DISABLED (fails on cloud IPs)
    # See: https://github.com/jdepoix/youtube-transcript-api/issues/303
    # The library gets blocked by YouTube when running on Railway, AWS, GCP, etc.
    # Kept here for reference but not executed.

    # Tier 3: Whisper (final fallback, YouTube only)
    if use_whisper_fallback and platform == "youtube" and video_id:
        logger.info(f"Tier 3: Trying Whisper for {video_id}...")
        try:
            from backend.integrations.whisper_client import transcribe_with_whisper

            result = transcribe_with_whisper(video_id)
            if result and result.get("text"):
                logger.info(f"Whisper success for {video_id}")
                return TranscriptItem(
                    video_id=video_id,
                    video_url=video_url,
                    text=result["text"],
                    status=TranscriptStatus.AVAILABLE,
                    language=result.get("language", "en"),
                    source="whisper",
                    platform=platform,
                    cost_credits=result.get("cost", 0.0) / 0.006,  # Convert $ to credits approx
                )
        except Exception as e:
            errors.append(f"whisper: {e}")
            logger.warning(f"Whisper failed for {video_id}: {e}")

    # All tiers failed
    error_summary = "; ".join(errors) if errors else "All transcription methods failed"
    logger.warning(f"All transcription tiers failed for {video_url[:50]}: {error_summary}")

    return TranscriptItem(
        video_id=video_id,
        video_url=video_url,
        status=TranscriptStatus.MISSING,
        error_message=error_summary,
        platform=platform,
    )


def fetch_transcripts_batch(
    video_urls: list[str],
    preferred_languages: Optional[list[str]] = None,
) -> list[TranscriptItem]:
    """
    Fetch transcripts for multiple videos.

    Uses fetch_transcript_v2 for each video with the PRD v4.3 fallback chain.

    Args:
        video_urls: List of video URLs
        preferred_languages: Preferred languages

    Returns:
        List of TranscriptItem results
    """
    results = []

    for url in video_urls:
        try:
            result = fetch_transcript_v2(url, preferred_languages)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to fetch transcript for {url}: {e}")
            results.append(TranscriptItem(
                video_id="",
                video_url=url,
                status=TranscriptStatus.ERROR,
                error_message=str(e),
                platform=_detect_platform(url),
            ))

    return results

