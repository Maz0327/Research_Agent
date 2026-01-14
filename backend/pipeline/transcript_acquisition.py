"""
Spec-compliant transcript acquisition with 4-tier fallback chain.

LOCKED ORDER (per RASS.md Section 8.1):
1. Supadata → transcript_grounded
2. Whisper → transcript_grounded
3. YouTube captions → caption_grounded (local only, fails on cloud IPs)
4. None → video_only

This module replaces legacy backend.integrations.transcripts with
proper terminology and analysis mode derivation for the semantic pipeline.

NOTE: YouTube captions tier uses youtube-transcript-api which fails on
cloud IPs (Railway, AWS, GCP). On cloud deployments, Tier 3 will always
fall through to video_only. This is documented behavior.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

from loguru import logger

from backend.models.semantic_units import AnalysisMode, ConfidenceLevel
from backend.models.document_outputs import TranscriptProvenance


class TranscriptSource(str, Enum):
    """Source of acquired transcript (spec-aligned terminology)."""
    SUPADATA = "supadata"
    WHISPER = "whisper"
    YOUTUBE_CAPTIONS = "youtube_captions"
    NONE = "none"


class AcquisitionStatus(str, Enum):
    """Status of transcript acquisition attempt."""
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TranscriptResult:
    """
    Result of transcript acquisition with spec-aligned terminology.

    This model replaces legacy TranscriptItem with proper:
    - transcript_source (not 'source')
    - analysis_mode derivation
    - TranscriptProvenance for downstream stages
    """
    video_url: str
    video_id: str
    text: Optional[str]
    transcript_source: TranscriptSource
    analysis_mode: AnalysisMode
    status: AcquisitionStatus
    error_message: Optional[str] = None
    language: Optional[str] = "en"
    cost_credits: float = 0.0
    platform: str = "youtube"

    def to_provenance(self) -> TranscriptProvenance:
        """
        Build TranscriptProvenance for document assembly.

        This is the canonical provenance metadata attached to Doc 0 sources.
        """
        # Derive verification capabilities from analysis mode
        if self.analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED:
            quote_verification = True
            timestamp_grounding = True
            semantic_precision = ConfidenceLevel.HIGH
            transcript_status = "success"
            captions_status = "success"
        elif self.analysis_mode == AnalysisMode.CAPTION_GROUNDED:
            quote_verification = True  # Quotes are approximate
            timestamp_grounding = True
            semantic_precision = ConfidenceLevel.MEDIUM
            transcript_status = "failed"
            captions_status = "success"
        else:  # VIDEO_ONLY
            quote_verification = False
            timestamp_grounding = False
            semantic_precision = ConfidenceLevel.LOW
            transcript_status = "failed"
            captions_status = "failed"

        return TranscriptProvenance(
            transcript_source=self.transcript_source.value,
            transcript_status=transcript_status,
            captions_status=captions_status,
            gemini_analysis_mode=self.analysis_mode,
            quote_verification=quote_verification,
            timestamp_grounding=timestamp_grounding,
            semantic_precision=semantic_precision,
            notes=self.error_message,
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage/logging."""
        return {
            "video_url": self.video_url,
            "video_id": self.video_id,
            "text": self.text[:200] + "..." if self.text and len(self.text) > 200 else self.text,
            "transcript_source": self.transcript_source.value,
            "analysis_mode": self.analysis_mode.value,
            "status": self.status.value,
            "error_message": self.error_message,
            "language": self.language,
            "cost_credits": self.cost_credits,
            "platform": self.platform,
        }


# -----------------------------------------------------------------------------
# TIER IMPLEMENTATIONS
# -----------------------------------------------------------------------------

def _extract_video_id(video_url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL.

    Supports:
    - Full URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    - Short URL: https://youtu.be/dQw4w9WgXcQ
    - Embed URL: https://www.youtube.com/embed/dQw4w9WgXcQ
    - Video ID: dQw4w9WgXcQ
    """
    # Already a video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', video_url):
        return video_url

    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)

    return None


def _detect_platform(url: str) -> str:
    """Detect video platform from URL."""
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


def _try_supadata(video_url: str) -> tuple[Optional[str], Optional[str], float]:
    """
    Tier 1: Try Supadata transcript API.

    Returns: (text, error_message, cost_credits)
    """
    try:
        from backend.integrations.supadata_client import (
            SupadataClient,
            SupadataError,
            TranscriptMode,
            is_supadata_available,
        )

        if not is_supadata_available():
            return None, "Supadata not configured", 0.0

        client = SupadataClient()

        # Try native first (cheaper)
        result = client.get_transcript(video_url, mode=TranscriptMode.NATIVE)
        if result.get("text"):
            return result["text"], None, result.get("cost_credits", 1.0)

        # Try AI generation (more expensive but more reliable)
        result = client.get_transcript(video_url, mode=TranscriptMode.GENERATE)
        if result.get("text"):
            return result["text"], None, result.get("cost_credits", 2.0)

        return None, "Supadata returned empty transcript", 0.0

    except Exception as e:
        return None, f"Supadata error: {e}", 0.0


def _try_whisper(video_id: str) -> tuple[Optional[str], Optional[str], float]:
    """
    Tier 2: Try Whisper transcription.

    Returns: (text, error_message, cost_credits)
    """
    try:
        from backend.integrations.whisper_client import transcribe_with_whisper

        result = transcribe_with_whisper(video_id, max_duration=60.0)
        if result and result.get("text"):
            # Convert dollar cost to credits (approx $0.006/min = 1 credit)
            cost = result.get("cost", 0.0) / 0.006
            return result["text"], None, cost

        return None, "Whisper returned empty transcript", 0.0

    except Exception as e:
        return None, f"Whisper error: {e}", 0.0


def _try_youtube_captions(video_id: str) -> tuple[Optional[str], Optional[str], float]:
    """
    Tier 3: Try YouTube captions via youtube-transcript-api.

    WARNING: This tier FAILS on cloud IPs (Railway, AWS, GCP).
    See: https://github.com/jdepoix/youtube-transcript-api/issues/303

    On cloud deployments, this will return None and fall through to video_only.
    This is documented and expected behavior.

    Returns: (text, error_message, cost_credits)
    """
    try:
        # youtube-transcript-api may not be installed on all deployments
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        if transcript:
            # Join all segments
            text = " ".join(entry.get("text", "") for entry in transcript)
            return text, None, 0.0

        return None, "YouTube captions not available", 0.0

    except ImportError:
        return None, "youtube-transcript-api not installed", 0.0
    except Exception as e:
        # Common on cloud: YouTube blocks these IPs
        error_str = str(e)
        if "Could not retrieve" in error_str or "blocked" in error_str.lower():
            return None, "YouTube captions blocked (cloud IP)", 0.0
        return None, f"YouTube captions error: {e}", 0.0


# -----------------------------------------------------------------------------
# MAIN ACQUISITION FUNCTION
# -----------------------------------------------------------------------------

def acquire_transcript(video_url: str) -> TranscriptResult:
    """
    Acquire transcript with spec-compliant 4-tier fallback chain.

    LOCKED ORDER (per RASS.md Section 8.1):
    1. Supadata → transcript_grounded
    2. Whisper → transcript_grounded
    3. YouTube captions → caption_grounded
    4. None → video_only

    Args:
        video_url: Video URL (YouTube, TikTok, Instagram, Twitter, Facebook)

    Returns:
        TranscriptResult with transcript text and analysis mode
    """
    platform = _detect_platform(video_url)
    video_id = _extract_video_id(video_url) or ""
    errors = []

    # Tier 1: Supadata
    logger.info(f"Tier 1 (Supadata): {video_url[:50]}...")
    text, error, cost = _try_supadata(video_url)
    if text:
        logger.info(f"✓ Supadata success for {video_url[:50]}")
        return TranscriptResult(
            video_url=video_url,
            video_id=video_id,
            text=text,
            transcript_source=TranscriptSource.SUPADATA,
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            status=AcquisitionStatus.SUCCESS,
            cost_credits=cost,
            platform=platform,
        )
    if error:
        errors.append(f"supadata: {error}")

    # Tier 2: Whisper (YouTube only)
    if platform == "youtube" and video_id:
        logger.info(f"Tier 2 (Whisper): {video_id}...")
        text, error, cost = _try_whisper(video_id)
        if text:
            logger.info(f"✓ Whisper success for {video_id}")
            return TranscriptResult(
                video_url=video_url,
                video_id=video_id,
                text=text,
                transcript_source=TranscriptSource.WHISPER,
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                status=AcquisitionStatus.SUCCESS,
                cost_credits=cost,
                platform=platform,
            )
        if error:
            errors.append(f"whisper: {error}")

    # Tier 3: YouTube captions (local only, fails on cloud)
    if platform == "youtube" and video_id:
        logger.info(f"Tier 3 (YouTube captions): {video_id}...")
        text, error, cost = _try_youtube_captions(video_id)
        if text:
            logger.info(f"✓ YouTube captions success for {video_id}")
            return TranscriptResult(
                video_url=video_url,
                video_id=video_id,
                text=text,
                transcript_source=TranscriptSource.YOUTUBE_CAPTIONS,
                analysis_mode=AnalysisMode.CAPTION_GROUNDED,
                status=AcquisitionStatus.SUCCESS,
                cost_credits=cost,
                platform=platform,
            )
        if error:
            errors.append(f"youtube_captions: {error}")

    # Tier 4: All failed → video_only
    error_summary = "; ".join(errors) if errors else "All transcription methods failed"
    logger.warning(f"All tiers failed for {video_url[:50]}: {error_summary}")

    return TranscriptResult(
        video_url=video_url,
        video_id=video_id,
        text=None,
        transcript_source=TranscriptSource.NONE,
        analysis_mode=AnalysisMode.VIDEO_ONLY,
        status=AcquisitionStatus.FAILED,
        error_message=error_summary,
        platform=platform,
    )


def acquire_transcripts_batch(video_urls: list[str]) -> list[TranscriptResult]:
    """
    Batch acquire transcripts for multiple videos.

    Args:
        video_urls: List of video URLs

    Returns:
        List of TranscriptResult, one per URL
    """
    results = []

    for url in video_urls:
        try:
            result = acquire_transcript(url)
            results.append(result)
        except Exception as e:
            logger.error(f"Unexpected error acquiring transcript for {url}: {e}")
            results.append(TranscriptResult(
                video_url=url,
                video_id=_extract_video_id(url) or "",
                text=None,
                transcript_source=TranscriptSource.NONE,
                analysis_mode=AnalysisMode.VIDEO_ONLY,
                status=AcquisitionStatus.FAILED,
                error_message=f"Unexpected error: {e}",
                platform=_detect_platform(url),
            ))

    return results


# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------------------------

def is_transcript_available(result: TranscriptResult) -> bool:
    """Check if transcript was successfully acquired."""
    return result.status == AcquisitionStatus.SUCCESS and result.text is not None


def get_confidence_ceiling(result: TranscriptResult) -> ConfidenceLevel:
    """
    Get confidence ceiling based on analysis mode.

    Per RASS.md Section 8.1:
    - transcript_grounded → HIGH
    - caption_grounded → MEDIUM
    - video_only → LOW
    """
    ceilings = {
        AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,
        AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,
        AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,
    }
    return ceilings.get(result.analysis_mode, ConfidenceLevel.LOW)
