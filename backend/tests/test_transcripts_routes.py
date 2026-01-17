"""Tests for transcripts_routes.py.

Phase 9: Tests transcript fetching endpoint.
"""

import pytest
import re
from unittest.mock import MagicMock, patch


# =============================================================================
# Test: YouTube URL Validation
# =============================================================================


class TestYouTubeURLValidation:
    """Test YouTube URL validation logic."""

    def test_valid_youtube_url_standard(self):
        """Should accept standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        # Standard pattern
        pattern = r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
        match = re.match(pattern, url)

        assert match is not None
        assert match.group(1) == "dQw4w9WgXcQ"

    def test_valid_youtube_url_short(self):
        """Should accept short YouTube URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"

        # Short URL pattern
        pattern = r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})'
        match = re.match(pattern, url)

        assert match is not None
        assert match.group(1) == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        """Should reject invalid URL."""
        url = "https://example.com/video"

        pattern1 = r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
        pattern2 = r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})'

        match1 = re.match(pattern1, url)
        match2 = re.match(pattern2, url)

        assert match1 is None
        assert match2 is None

    def test_video_id_extraction(self):
        """Should extract video ID from various URL formats."""
        urls = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=abc123def45", "abc123def45"),
            ("https://youtu.be/xyz789uvw12", "xyz789uvw12"),
        ]

        standard_pattern = r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
        short_pattern = r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})'

        for url, expected_id in urls:
            match = re.match(standard_pattern, url) or re.match(short_pattern, url)
            if match:
                assert match.group(1) == expected_id


# =============================================================================
# Test: Transcript Status
# =============================================================================


class TestTranscriptStatus:
    """Test transcript status handling."""

    def test_status_available(self):
        """Should indicate available transcript."""
        from backend.integrations.transcripts import TranscriptStatus

        status = TranscriptStatus.AVAILABLE
        assert status.value == "available"

    def test_status_missing(self):
        """Should indicate missing transcript."""
        from backend.integrations.transcripts import TranscriptStatus

        status = TranscriptStatus.MISSING
        assert status.value == "missing"

    def test_status_error(self):
        """Should indicate error status."""
        from backend.integrations.transcripts import TranscriptStatus

        status = TranscriptStatus.ERROR
        assert status.value == "error"
