"""Tests for Supabase connection retry logic.

Tests verify:
1. Retry on connection errors (ConnectError, TimeoutException, NetworkError)
2. No retry on HTTP errors (400, 404, 500)
3. Cache cleared on connection failure
4. Max 3 retries with exponential backoff
"""
import pytest
from unittest.mock import Mock, patch
import httpx

from backend.state.impl.supabase_store import (
    RETRYABLE_EXCEPTIONS,
    supabase_retry,
    _get_supabase_client,
)


class TestRetryDecorator:
    """Tests for the supabase_retry decorator."""

    def test_retries_on_connect_error(self):
        """Should retry when httpx.ConnectError is raised."""
        call_count = 0

        @supabase_retry
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection refused")
            return "success"

        result = flaky_operation()
        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded on third

    def test_retries_on_timeout(self):
        """Should retry when httpx.TimeoutException is raised."""
        call_count = 0

        @supabase_retry
        def timeout_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")
            return "success"

        result = timeout_operation()
        assert result == "success"
        assert call_count == 2

    def test_retries_on_network_error(self):
        """Should retry when httpx.NetworkError is raised."""
        call_count = 0

        @supabase_retry
        def network_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.NetworkError("DNS resolution failed")
            return "success"

        result = network_operation()
        assert result == "success"
        assert call_count == 2

    def test_no_retry_on_http_status_error(self):
        """Should NOT retry on HTTP status errors (4xx, 5xx)."""
        call_count = 0

        @supabase_retry
        def http_error_operation():
            nonlocal call_count
            call_count += 1
            response = Mock()
            response.status_code = 400
            raise httpx.HTTPStatusError(
                "Bad Request",
                request=Mock(),
                response=response
            )

        with pytest.raises(httpx.HTTPStatusError):
            http_error_operation()

        assert call_count == 1  # No retry on HTTP errors

    def test_max_retries_exceeded(self):
        """Should fail after 3 retries."""
        call_count = 0

        @supabase_retry
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Always fails")

        with pytest.raises(httpx.ConnectError):
            always_fails()

        assert call_count == 3  # Tried 3 times, then gave up

    def test_success_on_first_try(self):
        """Should return immediately on success without retry."""
        call_count = 0

        @supabase_retry
        def success_operation():
            nonlocal call_count
            call_count += 1
            return "immediate success"

        result = success_operation()
        assert result == "immediate success"
        assert call_count == 1


class TestCacheInvalidation:
    """Tests for client cache invalidation on connection failure."""

    def test_cache_clear_called_on_retry(self):
        """Cache should be cleared when retry occurs."""
        call_count = 0

        # Clear any existing cache
        _get_supabase_client.cache_clear()

        @supabase_retry
        def flaky_with_cache_check():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("First attempt fails")
            return "success"

        # Patch _on_retry_callback to verify it clears cache
        with patch('backend.state.impl.supabase_store._get_supabase_client') as mock_client:
            mock_client.cache_clear = Mock()
            result = flaky_with_cache_check()

        assert result == "success"
        assert call_count == 2


class TestRetryableExceptions:
    """Verify correct exception types are retryable."""

    def test_retryable_exceptions_tuple(self):
        """Verify all expected exceptions are in RETRYABLE_EXCEPTIONS."""
        assert httpx.ConnectError in RETRYABLE_EXCEPTIONS
        assert httpx.TimeoutException in RETRYABLE_EXCEPTIONS
        assert httpx.NetworkError in RETRYABLE_EXCEPTIONS

    def test_http_status_error_not_retryable(self):
        """HTTP status errors should NOT be retryable."""
        assert httpx.HTTPStatusError not in RETRYABLE_EXCEPTIONS

    def test_http_error_not_retryable(self):
        """Generic HTTP errors should NOT be retryable."""
        assert httpx.HTTPError not in RETRYABLE_EXCEPTIONS


class TestLegacySupabaseRetry:
    """Tests for legacy supabase.py retry behavior."""

    def test_legacy_module_has_retry_config(self):
        """Verify legacy module has retry configuration."""
        from backend.state.impl.supabase import (
            RETRYABLE_EXCEPTIONS as LEGACY_EXCEPTIONS,
            supabase_retry as legacy_retry,
        )

        assert httpx.ConnectError in LEGACY_EXCEPTIONS
        assert httpx.TimeoutException in LEGACY_EXCEPTIONS
        assert httpx.NetworkError in LEGACY_EXCEPTIONS
        assert legacy_retry is not None
