"""
Tests for backend/utils/validators.py
"""
import pytest
from backend.utils.validators import validate_youtube_video_id, validate_uuid


class TestYouTubeVideoIdValidator:
    """Tests for YouTube video ID validation."""

    def test_valid_video_id(self):
        """Valid 11-character video IDs should pass."""
        valid_ids = [
            "dQw4w9WgXcQ",
            "jNQXAC9IVRw",
            "9bZkp7q19f0",
            "abc123def45",
            "ABC_-1234ab",
        ]
        for video_id in valid_ids:
            assert validate_youtube_video_id(video_id) == video_id

    def test_invalid_video_id_too_short(self):
        """Video IDs shorter than 11 chars should fail."""
        with pytest.raises(ValueError, match="Invalid YouTube video ID"):
            validate_youtube_video_id("abc123")

    def test_invalid_video_id_too_long(self):
        """Video IDs longer than 11 chars should fail."""
        with pytest.raises(ValueError, match="Invalid YouTube video ID"):
            validate_youtube_video_id("abc123def456789")

    def test_invalid_video_id_special_chars(self):
        """Video IDs with invalid characters should fail."""
        invalid_ids = [
            "abc123!@#45",
            "abc123 def4",
            "abc123\ndef4",
            "<script>xyz",
        ]
        for video_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid YouTube video ID"):
                validate_youtube_video_id(video_id)


class TestUuidValidator:
    """Tests for UUID validation."""

    def test_valid_uuid(self):
        """Valid UUIDs should pass."""
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        ]
        for uuid_str in valid_uuids:
            assert validate_uuid(uuid_str) == uuid_str

    def test_invalid_uuid(self):
        """Invalid UUIDs should fail."""
        invalid_uuids = [
            "not-a-uuid",
            "550e8400-e29b-41d4-a716",  # Incomplete
            "gggggggg-gggg-gggg-gggg-gggggggggggg",  # Invalid hex
            "null",
        ]
        for uuid_str in invalid_uuids:
            with pytest.raises(ValueError, match="Invalid id format"):
                validate_uuid(uuid_str)

    def test_uuid_without_dashes_is_valid(self):
        """UUID without dashes should be parsed correctly."""
        # Python's uuid module accepts UUIDs without dashes
        result = validate_uuid("550e8400e29b41d4a716446655440000")
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    def test_empty_uuid(self):
        """Empty UUID should fail with appropriate message."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_uuid("")
