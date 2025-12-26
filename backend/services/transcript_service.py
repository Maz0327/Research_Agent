"""Transcript extraction service.

CLOUD-COMPATIBLE (Dec 2025):
- Uses Supadata as primary (works on cloud IPs)
- Whisper as fallback
- youtube-transcript-api REMOVED (fails on Railway, AWS, GCP)
"""
from datetime import datetime
from typing import Optional

from loguru import logger

from backend.integrations.transcripts import (
    TranscriptStatus,
    fetch_transcript_v2,  # Cloud-compatible version
    _extract_video_id,
)
from backend.models.transcript_job import TranscriptResultItem


def extract_single_transcript(
    video_url: str,
    use_whisper: bool = True,
    preferred_languages: list[str] = None,
) -> TranscriptResultItem:
    """
    Extract transcript from a single video.

    CLOUD-COMPATIBLE (Dec 2025):
    1. Supadata native (existing captions)
    2. Supadata AI (generate transcript)
    3. Whisper (final fallback)

    NOTE: youtube-transcript-api REMOVED - fails on cloud IPs

    Args:
        video_url: Video URL (YouTube, TikTok, Instagram, etc.)
        use_whisper: Whether to use Whisper fallback
        preferred_languages: Preferred transcript languages

    Returns:
        TranscriptResultItem with transcript or error info
    """
    if preferred_languages is None:
        preferred_languages = ["en"]

    # Extract video ID for logging
    video_id = _extract_video_id(video_url) or ""

    # Use cloud-compatible fetch_transcript_v2
    transcript = fetch_transcript_v2(
        video_url,
        preferred_languages=preferred_languages,
        use_whisper_fallback=use_whisper,
    )

    if transcript.status == TranscriptStatus.AVAILABLE:
        logger.info(f"Transcript fetched via {transcript.source}: {video_id}")
        return TranscriptResultItem(
            video_id=transcript.video_id,
            video_url=transcript.video_url,
            status="available",
            source=transcript.source,
            text=transcript.text,
        )

    # All tiers failed
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
