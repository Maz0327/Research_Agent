"""
Tests for backend/auth/ module

Tests authentication dependencies and ban checks.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Request without Authorization header should fail."""
        from backend.auth.dependencies import get_current_user

        request = MagicMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_bearer_format(self):
        """Invalid Bearer token format should fail."""
        from backend.auth.dependencies import get_current_user

        request = MagicMock()
        request.headers = {"authorization": "InvalidFormat token123"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_bearer_token(self):
        """Empty Bearer token should fail."""
        from backend.auth.dependencies import get_current_user

        request = MagicMock()
        request.headers = {"authorization": "Bearer "}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)

        assert exc_info.value.status_code == 401


class TestGetOptionalUser:
    """Tests for get_optional_user dependency."""

    @pytest.mark.asyncio
    async def test_no_auth_header_returns_none(self):
        """Request without auth header should return None."""
        from backend.auth.dependencies import get_optional_user

        request = MagicMock()
        request.headers = {}

        result = await get_optional_user(request)
        assert result is None


class TestBanCheck:
    """Tests for user ban checking."""

    @pytest.mark.asyncio
    async def test_banned_user_denied(self):
        """Banned users should be denied access via check_user_banned function."""
        from backend.auth.ban_check import check_user_banned

        # Mock Supabase client to return banned=True
        with patch("backend.auth.ban_check.get_supabase_client") as mock_client:
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()

            # Set up chain: client.table().select().eq().execute()
            mock_client.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = MagicMock(data=[{"is_banned": True}])

            result = await check_user_banned("banned-user-123")
            assert result is True

    @pytest.mark.asyncio
    async def test_active_user_allowed(self):
        """Non-banned users should be allowed via check_user_banned function."""
        from backend.auth.ban_check import check_user_banned

        # Mock Supabase client to return banned=False
        with patch("backend.auth.ban_check.get_supabase_client") as mock_client:
            mock_supabase = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_eq = MagicMock()

            # Set up chain: client.table().select().eq().execute()
            mock_client.return_value = mock_supabase
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value = MagicMock(data=[{"is_banned": False}])

            result = await check_user_banned("active-user-123")
            assert result is False


class TestJWTVerification:
    """Tests for JWT token verification."""

    def test_invalid_jwt_rejected(self):
        """Invalid JWT tokens should be rejected."""
        from backend.auth import verify_jwt, AuthError

        # Mock settings to have a valid secret
        with patch("backend.auth.get_settings") as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "test-secret-with-enough-length"
            mock_settings.return_value.supabase_jwt_audience = "authenticated"

            # Invalid token format should raise AuthError
            with pytest.raises(AuthError) as exc_info:
                verify_jwt("invalid.token.here")

            assert exc_info.value.status_code == 401

    def test_jwt_missing_secret(self):
        """Missing JWT secret should raise error."""
        from backend.auth import verify_jwt, AuthError

        # Mock settings with no JWT secret
        with patch("backend.auth.get_settings") as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = None

            with pytest.raises(AuthError) as exc_info:
                verify_jwt("any.token.here")

            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.message


class TestAuthUser:
    """Tests for AuthUser model."""

    def test_auth_user_creation(self):
        """AuthUser should be created with required fields."""
        from backend.auth import AuthUser

        user = AuthUser(
            user_id="test-123",
            email="test@example.com",
            role="authenticated"
        )

        assert user.user_id == "test-123"
        assert user.email == "test@example.com"
        assert user.role == "authenticated"

    def test_auth_user_admin_role(self):
        """AuthUser can have admin role."""
        from backend.auth import AuthUser

        user = AuthUser(
            user_id="admin-123",
            email="admin@example.com",
            role="admin"
        )

        assert user.role == "admin"
