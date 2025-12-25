"""Transcript extraction service."""
from datetime import datetime
from typing import Optional

from loguru import logger

from backend.config import get_settings
from backend.integrations.transcripts import (
    TranscriptStatus,
    fetch_transcript,
    _extract_video_id,
)
from backend.integrations.whisper_client import transcribe_with_whisper
from backend.models.transcript_job import TranscriptResultItem


def extract_single_transcript(
    video_url: str,
    use_whisper: bool = True,
    preferred_languages: list[str] = None,
) -> TranscriptResultItem:
    """
    Extract transcript from a single YouTube video.

    Uses youtube-transcript-api first, then Whisper as fallback.

    Args:
        video_url: YouTube video URL
        use_whisper: Whether to use Whisper fallback
        preferred_languages: Preferred transcript languages

    Returns:
        TranscriptResultItem with transcript or error info
    """
    if preferred_languages is None:
        preferred_languages = ["en"]

    settings = get_settings()

    # Extract video ID for logging
    video_id = _extract_video_id(video_url) or ""

    # Try Tier 1: youtube-transcript-api
    transcript = fetch_transcript(
        video_url,
        use_whisper=False,  # Handle Whisper separately for better control
        preferred_languages=preferred_languages,
    )

    if transcript.status == TranscriptStatus.AVAILABLE:
        logger.info(f"Transcript fetched via youtube-transcript-api: {video_id}")
        return TranscriptResultItem(
            video_id=transcript.video_id,
            video_url=transcript.video_url,
            status="available",
            source="youtube_transcript_api",
            text=transcript.text,
        )

    # Tier 1 failed - try Whisper if enabled
    if use_whisper and settings.openai_api_key:
        logger.info(f"Trying Whisper fallback for {video_id}")
        try:
            whisper_result = transcribe_with_whisper(video_id)
            if whisper_result.get("text"):
                logger.info(f"Whisper transcription successful: {video_id} (cost: ${whisper_result.get('cost', 0):.4f})")
                return TranscriptResultItem(
                    video_id=video_id,
                    video_url=video_url,
                    status="available",
                    source="whisper",
                    text=whisper_result["text"],
                    duration_seconds=int(whisper_result.get("duration_minutes", 0) * 60),
                )
        except Exception as e:
            logger.warning(f"Whisper fallback failed for {video_id}: {e}")

    # Both tiers failed
    return TranscriptResultItem(
        video_id=video_id,
        video_url=video_url,
        status="missing" if transcript.status == TranscriptStatus.MISSING else "error",
        source="failed",
        error_message=transcript.error_message,
    )


def extract_transcripts_batch(
    video_urls: list[str],
    use_whisper: bool = True,
    preferred_languages: list[str] = None,
    progress_callback: callable = None,
) -> tuple[list[TranscriptResultItem], list[str]]:
    """
    Extract transcripts from multiple YouTube videos.

    Args:
        video_urls: List of YouTube video URLs
        use_whisper: Whether to use Whisper fallback
        preferred_languages: Preferred transcript languages
        progress_callback: Optional callback(current, total) for progress updates

    Returns:
        Tuple of (transcripts, warnings)
    """
    transcripts = []
    warnings = []
    total = len(video_urls)

    for i, url in enumerate(video_urls):
        try:
            result = extract_single_transcript(
                url,
                use_whisper=use_whisper,
                preferred_languages=preferred_languages,
            )
            transcripts.append(result)

            if result.status != "available":
                warnings.append(f"Transcript unavailable for {url}: {result.error_message}")

        except Exception as e:
            logger.error(f"Error extracting transcript for {url}: {e}")
            warnings.append(f"Error processing {url}: {str(e)}")
            transcripts.append(TranscriptResultItem(
                video_id=_extract_video_id(url) or "",
                video_url=url,
                status="error",
                source="failed",
                error_message=str(e),
            ))

        if progress_callback:
            progress_callback(i + 1, total)

    return transcripts, warnings


def format_transcripts_for_doc(transcripts: list[TranscriptResultItem]) -> str:
    """
    Format transcripts into a Google Doc-friendly format.

    Args:
        transcripts: List of transcript results

    Returns:
        Formatted string for Google Doc
    """
    lines = [
        "YOUTUBE TRANSCRIPTS",
        "=" * 50,
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "SUMMARY",
        "-" * 50,
        f"Total Videos: {len(transcripts)}",
        f"Successful: {sum(1 for t in transcripts if t.status == 'available')}",
        f"Failed/Missing: {sum(1 for t in transcripts if t.status != 'available')}",
        "",
        "TABLE OF CONTENTS",
        "-" * 50,
    ]

    # Table of contents
    for i, t in enumerate(transcripts, 1):
        status_icon = "[OK]" if t.status == "available" else "[X]"
        lines.append(f"{i}. {status_icon} {t.video_url}")

    lines.extend(["", "=" * 50, ""])

    # Individual transcripts
    for i, t in enumerate(transcripts, 1):
        lines.append(f"VIDEO {i}: {t.video_id}")
        lines.append("-" * 50)
        lines.append(f"URL: {t.video_url}")
        lines.append(f"Status: {t.status}")
        lines.append(f"Source: {t.source}")
        if t.duration_seconds:
            lines.append(f"Duration: {t.duration_seconds // 60}m {t.duration_seconds % 60}s")
        lines.append("")

        if t.text:
            lines.append("TRANSCRIPT:")
            lines.append("")
            lines.append(t.text)
        else:
            lines.append(f"[No transcript available: {t.error_message}]")

        lines.extend(["", "=" * 50, ""])

    return "\n".join(lines)


def process_transcripts_sync(
    video_urls: list[str],
    use_whisper: bool = True,
    doc_title: Optional[str] = None,
    preferred_languages: list[str] = None,
) -> dict:
    """
    Process transcripts synchronously and create Google Doc.

    For small batches (≤5 videos).

    Args:
        video_urls: List of YouTube video URLs
        use_whisper: Whether to use Whisper fallback
        doc_title: Custom title for Google Doc
        preferred_languages: Preferred transcript languages

    Returns:
        Dict with success, doc_url, folder_url, transcripts, warnings
    """
    from backend.integrations.google_drive_docs import create_transcript_doc

    # Extract transcripts
    transcripts, warnings = extract_transcripts_batch(
        video_urls,
        use_whisper=use_whisper,
        preferred_languages=preferred_languages,
    )

    # Generate doc title
    if not doc_title:
        doc_title = f"YouTube Transcripts - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Format content and create doc
    content = format_transcripts_for_doc(transcripts)

    try:
        drive_result = create_transcript_doc(doc_title, content)
    except Exception as e:
        logger.error(f"Failed to create Google Doc: {e}")
        return {
            "success": False,
            "doc_url": "",
            "folder_url": "",
            "transcripts": transcripts,
            "warnings": warnings + [f"Failed to create Google Doc: {str(e)}"],
            "total_videos": len(video_urls),
            "successful_count": sum(1 for t in transcripts if t.status == "available"),
            "failed_count": sum(1 for t in transcripts if t.status != "available"),
        }

    return {
        "success": True,
        "doc_url": drive_result["doc_url"],
        "folder_url": drive_result["folder_url"],
        "transcripts": transcripts,
        "warnings": warnings,
        "total_videos": len(video_urls),
        "successful_count": sum(1 for t in transcripts if t.status == "available"),
        "failed_count": sum(1 for t in transcripts if t.status != "available"),
    }
