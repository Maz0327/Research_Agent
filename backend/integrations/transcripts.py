"""Transcript fetching for YouTube videos."""
import re
from enum import Enum
from typing import Optional

from loguru import logger
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeRequestFailed,
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
    source: str = "youtube_transcript_api"  # "youtube_transcript_api" or "whisper"


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


def _fetch_with_youtube_transcript_api(video_id: str, languages: Optional[list[str]] = None) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Fetch transcript using youtube-transcript-api.
    
    Args:
        video_id: YouTube video ID
        languages: Preferred languages (default: ['en'])
        
    Returns:
        Tuple of (text, language, error_message)
        If successful: (text, language, None)
        If failed: (None, None, error_message)
    """
    if languages is None:
        languages = ['en']
    
    try:
        # Try to get transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        
        # Concatenate all transcript entries into a single text
        text_parts = []
        for entry in transcript_list:
            text_parts.append(entry.get('text', ''))
        
        text = ' '.join(text_parts)
        language = transcript_list[0].get('language', languages[0]) if transcript_list else languages[0]
        
        return text, language, None
    
    except NoTranscriptFound:
        return None, None, "No transcript found for this video"
    except TranscriptsDisabled:
        return None, None, "Transcripts are disabled for this video"
    except VideoUnavailable:
        return None, None, "Video is unavailable"
    except YouTubeRequestFailed as e:
        return None, None, f"YouTube API request failed: {str(e)}"
    except Exception as e:
        logger.exception(f"Unexpected error fetching transcript for {video_id}: {e}")
        return None, None, f"Unexpected error: {str(e)}"


def _fetch_with_whisper(
    video_id: str,
    video_url: str,
    api_key: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Fetch transcript using OpenAI Whisper API (hook for future use).
    
    This is a placeholder implementation. Whisper API requires:
    - Downloading the video (or providing audio URL)
    - Calling OpenAI Whisper API
    - Processing the response
    
    Args:
        video_id: YouTube video ID
        video_url: YouTube video URL
        api_key: OpenAI API key (optional)
        
    Returns:
        Tuple of (text, language, error_message)
    """
    # Placeholder - not implemented in MVP
    # This would require:
    # 1. Downloading video/audio (using yt-dlp or similar)
    # 2. Calling OpenAI Whisper API
    # 3. Processing response
    
    logger.debug(f"Whisper transcription not implemented for video {video_id}")
    return None, None, "Whisper transcription not enabled in MVP"


def fetch_transcript(
    video_url_or_id: str,
    use_whisper: bool = False,
    whisper_api_key: Optional[str] = None,
    preferred_languages: Optional[list[str]] = None,
) -> TranscriptItem:
    """
    Fetch transcript for a YouTube video.
    
    Uses youtube-transcript-api first. If transcript is missing, marks status=missing
    and returns without failing. Whisper API is available as a hook but disabled by default.
    
    Args:
        video_url_or_id: YouTube video URL or video ID
        use_whisper: Whether to use Whisper API if youtube-transcript-api fails (default: False)
        whisper_api_key: OpenAI API key for Whisper (optional, required if use_whisper=True)
        preferred_languages: List of language codes to try (default: ['en'])
        
    Returns:
        TranscriptItem with transcript text if available, or status=missing if not
        
    Example:
        >>> transcript = fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        >>> if transcript.status == TranscriptStatus.AVAILABLE:
        ...     print(f"Transcript: {transcript.text[:100]}...")
        >>> else:
        ...     print(f"Transcript missing: {transcript.error_message}")
    """
    # Extract video ID
    video_id = _extract_video_id(video_url_or_id)
    if not video_id:
        return TranscriptItem(
            video_id="",
            video_url=video_url_or_id,
            status=TranscriptStatus.ERROR,
            error_message="Could not extract video ID from input",
        )
    
    # Build video URL if input was just an ID
    if not video_url_or_id.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_id}"
    else:
        video_url = video_url_or_id
    
    # Try youtube-transcript-api first
    text, language, error_message = _fetch_with_youtube_transcript_api(video_id, preferred_languages)
    
    if text:
        logger.info(f"Successfully fetched transcript for video {video_id} (language: {language})")
        return TranscriptItem(
            video_id=video_id,
            video_url=video_url,
            text=text,
            status=TranscriptStatus.AVAILABLE,
            language=language,
            source="youtube_transcript_api",
        )
    
    # Transcript not available via youtube-transcript-api
    logger.warning(f"Transcript not available via youtube-transcript-api for video {video_id}: {error_message}")
    
    # If Whisper is enabled, try it
    if use_whisper:
        if not whisper_api_key:
            logger.warning("Whisper is enabled but no API key provided")
            return TranscriptItem(
                video_id=video_id,
                video_url=video_url,
                status=TranscriptStatus.MISSING,
                error_message=f"youtube-transcript-api failed: {error_message}. Whisper enabled but no API key.",
            )
        
        whisper_text, whisper_language, whisper_error = _fetch_with_whisper(video_id, video_url, whisper_api_key)
        
        if whisper_text:
            logger.info(f"Successfully fetched transcript via Whisper for video {video_id}")
            return TranscriptItem(
                video_id=video_id,
                video_url=video_url,
                text=whisper_text,
                status=TranscriptStatus.AVAILABLE,
                language=whisper_language,
                source="whisper",
            )
        else:
            logger.warning(f"Whisper also failed for video {video_id}: {whisper_error}")
            return TranscriptItem(
                video_id=video_id,
                video_url=video_url,
                status=TranscriptStatus.MISSING,
                error_message=f"Both methods failed. youtube-transcript-api: {error_message}. Whisper: {whisper_error}",
            )
    
    # Transcript missing, but that's okay - return with status=missing
    return TranscriptItem(
        video_id=video_id,
        video_url=video_url,
        status=TranscriptStatus.MISSING,
        error_message=error_message,
    )

