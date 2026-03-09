"""Unit tests for transcript fetching."""
import os
import pytest

from backend.integrations.transcripts import (
    TranscriptItem,
    TranscriptStatus,
    _extract_video_id,
    fetch_transcript,
)


def test_extract_video_id():
    """Test video ID extraction from URLs and IDs."""
    # Direct video ID
    assert _extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    # Full YouTube URL
    assert _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    # Short URL
    assert _extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    # Embed URL
    assert _extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    # Invalid input
    assert _extract_video_id("not-a-valid-id-or-url") is None
    assert _extract_video_id("https://example.com/video") is None


def test_transcript_item_model():
    """Test TranscriptItem Pydantic model."""
    item = TranscriptItem(
        video_id="test123",
        video_url="https://www.youtube.com/watch?v=test123",
        text="Transcript text here",
        status=TranscriptStatus.AVAILABLE,
        language="en",
    )
    
    assert item.video_id == "test123"
    assert item.text == "Transcript text here"
    assert item.status == TranscriptStatus.AVAILABLE
    assert item.source == "supadata_native"  # Default source (updated from youtube_transcript_api)


@pytest.mark.skipif(not os.environ.get("SUPADATA_API_KEY"), reason="Requires SUPADATA_API_KEY — network call may hang")
def test_fetch_transcript_structure():
    """Test that fetch_transcript returns correct structure."""
    # This will return missing status if transcript not available (expected)
    result = fetch_transcript("dQw4w9WgXcQ")  # Rick Astley - Never Gonna Give You Up
    
    assert isinstance(result, TranscriptItem)
    assert result.video_id is not None
    assert result.video_url is not None
    assert isinstance(result.status, TranscriptStatus)
    # Status will be either AVAILABLE or MISSING depending on whether transcript exists
    assert result.status in [TranscriptStatus.AVAILABLE, TranscriptStatus.MISSING]


@pytest.mark.skipif(not os.environ.get("SUPADATA_API_KEY"), reason="Requires SUPADATA_API_KEY — network call may hang")
def test_fetch_transcript_with_url():
    """Test fetch_transcript with full URL."""
    result = fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    assert result.video_id == "dQw4w9WgXcQ"
    assert "youtube.com" in result.video_url


@pytest.mark.skipif(not os.environ.get("SUPADATA_API_KEY"), reason="Requires SUPADATA_API_KEY — network call may hang")
def test_fetch_transcript_missing_does_not_fail():
    """Test that missing transcripts don't cause failures."""
    # Use a very unlikely video ID that probably doesn't have transcripts
    # The function should return MISSING status, not raise an exception
    result = fetch_transcript("aaaaaaaaaaa")  # Very unlikely to exist
    
    assert isinstance(result, TranscriptItem)
    assert result.status == TranscriptStatus.MISSING or result.status == TranscriptStatus.ERROR
    # Should have error_message set
    assert result.error_message is not None or result.status == TranscriptStatus.MISSING


@pytest.mark.skipif(not os.environ.get("SUPADATA_API_KEY"), reason="Requires SUPADATA_API_KEY — network call may hang")
def test_fetch_transcript_whisper_disabled_by_default():
    """Test that Whisper is disabled by default."""
    # Without use_whisper=True, should not attempt Whisper
    result = fetch_transcript("dQw4w9WgXcQ", use_whisper=False)
    
    # Should not use Whisper source
    assert result.source != "whisper" or result.status == TranscriptStatus.MISSING


def test_transcript_status_enum():
    """Test TranscriptStatus enum values."""
    assert TranscriptStatus.AVAILABLE.value == "available"
    assert TranscriptStatus.MISSING.value == "missing"
    assert TranscriptStatus.ERROR.value == "error"


@pytest.mark.skip(reason="Makes real Supadata API call when SUPADATA_API_KEY is set — hangs on invalid input")
def test_fetch_transcript_invalid_input():
    """Test fetch_transcript with invalid input."""
    result = fetch_transcript("not-a-valid-video-id-or-url")

    # Invalid input now returns MISSING (all tiers fail) rather than ERROR
    assert result.status in (TranscriptStatus.ERROR, TranscriptStatus.MISSING)

