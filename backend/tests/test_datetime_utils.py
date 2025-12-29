"""
Tests for backend/utils/datetime_utils.py
"""
import pytest
from datetime import datetime, timezone
from backend.utils.datetime_utils import utc_now, utc_now_iso, utc_today_iso


class TestUtcNow:
    """Tests for utc_now function."""

    def test_returns_datetime(self):
        """Should return a datetime object."""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_returns_timezone_aware(self):
        """Should return timezone-aware datetime."""
        result = utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_returns_current_time(self):
        """Should return approximately current time."""
        before = datetime.now(timezone.utc)
        result = utc_now()
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestUtcNowIso:
    """Tests for utc_now_iso function."""

    def test_returns_string(self):
        """Should return a string."""
        result = utc_now_iso()
        assert isinstance(result, str)

    def test_returns_iso_format(self):
        """Should return ISO 8601 formatted string."""
        result = utc_now_iso()
        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(result)
        assert parsed is not None

    def test_includes_timezone(self):
        """Should include timezone offset."""
        result = utc_now_iso()
        assert "+00:00" in result or "Z" in result


class TestUtcTodayIso:
    """Tests for utc_today_iso function."""

    def test_returns_string(self):
        """Should return a string."""
        result = utc_today_iso()
        assert isinstance(result, str)

    def test_returns_date_only(self):
        """Should return date-only format (YYYY-MM-DD)."""
        result = utc_today_iso()
        # Should match YYYY-MM-DD format
        assert len(result) == 10
        parts = result.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # Year
        assert len(parts[1]) == 2  # Month
        assert len(parts[2]) == 2  # Day
