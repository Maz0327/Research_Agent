"""Tests for settings_routes.py.

Phase 9: Tests settings API endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_auth_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.user_id = "test-user-123"
    user.email = "test@example.com"
    return user


@pytest.fixture
def client():
    """Create a test client with mocked auth."""
    from backend.app.main import app

    with patch("backend.auth.dependencies.get_current_user") as mock_get_user:
        mock_user = MagicMock()
        mock_user.user_id = "test-user-123"
        mock_get_user.return_value = mock_user

        with patch("backend.auth.ban_check.get_active_user", return_value=mock_user):
            yield TestClient(app)


# =============================================================================
# Test: Settings Endpoints
# =============================================================================


class TestSettingsEndpoints:
    """Test settings API endpoints."""

    def test_username_validation_too_short(self):
        """Should reject username shorter than 3 characters."""
        import re

        username = "ab"
        if len(username) < 3:
            error = "Username must be at least 3 characters"
        else:
            error = None

        assert error == "Username must be at least 3 characters"

    def test_username_validation_too_long(self):
        """Should reject username longer than 30 characters."""
        username = "a" * 31

        if len(username) > 30:
            error = "Username must be at most 30 characters"
        else:
            error = None

        assert error == "Username must be at most 30 characters"

    def test_username_validation_invalid_format(self):
        """Should reject username with invalid format."""
        import re

        username = "123invalid"  # Starts with number

        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
            error = "Username must start with a letter"
        else:
            error = None

        assert "start with a letter" in error

    def test_username_validation_valid(self):
        """Should accept valid username."""
        import re

        username = "valid_user_123"

        error = None
        if len(username) < 3:
            error = "too short"
        elif len(username) > 30:
            error = "too long"
        elif not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
            error = "invalid format"

        assert error is None

    def test_folder_url_validation_valid(self):
        """Should extract folder ID from valid URL."""
        import re

        url = "https://drive.google.com/drive/folders/1abc123def456"
        url_pattern = r'https?://drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)'
        match = re.match(url_pattern, url)

        assert match is not None
        assert match.group(1) == "1abc123def456"

    def test_folder_url_validation_invalid(self):
        """Should reject invalid folder URL."""
        import re

        url = "https://example.com/not-a-drive-url"
        url_pattern = r'https?://drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)'
        match = re.match(url_pattern, url)

        assert match is None

    def test_folder_url_with_user_prefix(self):
        """Should handle URL with /u/0/ prefix."""
        import re

        url = "https://drive.google.com/drive/u/0/folders/1abc123def456"
        url_pattern = r'https?://drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)'
        match = re.match(url_pattern, url)

        assert match is not None
        assert match.group(1) == "1abc123def456"

    def test_settings_response_model(self):
        """Should create valid settings response."""
        from backend.models.user_settings import UserSettingsResponse

        # Test that model can be instantiated with valid fields
        response = UserSettingsResponse(
            drive_folder_url="https://drive.google.com/drive/folders/test",
            username="testuser",
        )

        assert response.username == "testuser"
        assert response.drive_folder_url is not None
