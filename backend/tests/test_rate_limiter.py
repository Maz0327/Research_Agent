"""
Tests for backend/utils/rate_limiter.py

Tests rate limiting with exponential backoff for external API integrations.
"""
import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch

from backend.utils.rate_limiter import (
    RateLimitConfig,
    get_rate_limit_config,
    get_rate_limiter_state,
    check_rate_limit,
    record_request,
    record_success,
    record_failure,
    get_backoff_delay,
    with_rate_limit,
    reset_rate_limiter,
    get_rate_limit_stats,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset rate limiter state before each test."""
    reset_rate_limiter()
    yield
    reset_rate_limiter()


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_default_config_exists(self):
        """Default config should be available."""
        config = get_rate_limit_config("unknown_api")
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000

    def test_known_api_config(self):
        """Known APIs should have specific configs."""
        openai_config = get_rate_limit_config("openai")
        assert openai_config.requests_per_minute == 60
        assert openai_config.requests_per_hour == 500

        supadata_config = get_rate_limit_config("supadata")
        assert supadata_config.requests_per_minute == 60
        assert supadata_config.requests_per_hour == 600


class TestRateLimitChecking:
    """Tests for rate limit checking."""

    def test_first_request_allowed(self):
        """First request should always be allowed."""
        can_proceed, wait_time = check_rate_limit("test_api")
        assert can_proceed is True
        assert wait_time == 0.0

    def test_minute_limit_enforcement(self):
        """Minute limit should be enforced."""
        # Record requests up to limit
        for _ in range(60):  # Default limit
            record_request("test_api")

        can_proceed, wait_time = check_rate_limit("test_api")
        assert can_proceed is False
        assert wait_time > 0

    def test_request_recording(self):
        """Requests should be recorded correctly."""
        state = get_rate_limiter_state("test_api")
        assert len(state.minute_requests) == 0

        record_request("test_api")
        assert len(state.minute_requests) == 1

        record_request("test_api")
        assert len(state.minute_requests) == 2


class TestExponentialBackoff:
    """Tests for exponential backoff."""

    def test_no_backoff_on_first_failure(self):
        """No backoff before first failure."""
        backoff = get_backoff_delay("test_api")
        assert backoff == 0.0

    def test_backoff_increases_with_failures(self):
        """Backoff should increase exponentially with failures."""
        record_failure("test_api")
        backoff1 = get_backoff_delay("test_api")
        assert backoff1 == 1.0  # Base delay

        record_failure("test_api")
        backoff2 = get_backoff_delay("test_api")
        assert backoff2 == 2.0  # 1.0 * 2^1

        record_failure("test_api")
        backoff3 = get_backoff_delay("test_api")
        assert backoff3 == 4.0  # 1.0 * 2^2

    def test_backoff_capped_at_max(self):
        """Backoff should not exceed max delay."""
        # Record many failures
        for _ in range(20):
            record_failure("test_api")

        backoff = get_backoff_delay("test_api")
        config = get_rate_limit_config("test_api")
        assert backoff == config.max_delay

    def test_success_resets_backoff(self):
        """Success should reset failure counter."""
        record_failure("test_api")
        record_failure("test_api")
        assert get_backoff_delay("test_api") > 0

        record_success("test_api")
        assert get_backoff_delay("test_api") == 0.0


class TestRateLimitStats:
    """Tests for rate limit statistics."""

    def test_stats_returned(self):
        """Stats should return useful information."""
        record_request("test_api")
        record_request("test_api")
        record_failure("test_api")

        stats = get_rate_limit_stats("test_api")

        assert stats["api_name"] == "test_api"
        assert stats["requests_last_minute"] == 2
        assert stats["consecutive_failures"] == 1
        assert stats["current_backoff"] > 0


class TestWithRateLimitDecorator:
    """Tests for with_rate_limit decorator."""

    def test_sync_function_decorated(self):
        """Sync functions should be properly decorated."""
        call_count = 0

        @with_rate_limit("test_api")
        def sync_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = sync_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_function_decorated(self):
        """Async functions should be properly decorated."""
        call_count = 0

        @with_rate_limit("test_api")
        async def async_function():
            nonlocal call_count
            call_count += 1
            return "async_success"

        result = await async_function()
        assert result == "async_success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Function should be retried on failure."""
        attempts = 0

        @with_rate_limit("test_api")
        def failing_function():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("Temporary failure")
            return "success_after_retry"

        result = failing_function()
        assert result == "success_after_retry"
        assert attempts == 3

    def test_max_retries_exceeded(self):
        """Should raise after max retries exceeded."""
        @with_rate_limit("test_api")
        def always_fails():
            raise RuntimeError("Always fails")

        with pytest.raises(RuntimeError, match="Always fails"):
            always_fails()


class TestRateLimiterReset:
    """Tests for rate limiter reset functionality."""

    def test_reset_specific_api(self):
        """Should reset specific API state."""
        record_request("api_a")
        record_request("api_b")
        record_failure("api_a")

        reset_rate_limiter("api_a")

        state_a = get_rate_limiter_state("api_a")
        state_b = get_rate_limiter_state("api_b")

        assert len(state_a.minute_requests) == 0
        assert len(state_b.minute_requests) == 1

    def test_reset_all_apis(self):
        """Should reset all API states."""
        record_request("api_a")
        record_request("api_b")

        reset_rate_limiter()

        state_a = get_rate_limiter_state("api_a")
        state_b = get_rate_limiter_state("api_b")

        assert len(state_a.minute_requests) == 0
        assert len(state_b.minute_requests) == 0
