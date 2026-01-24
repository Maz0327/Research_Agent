"""Rate limiting utility for external API integrations.

Provides centralized rate limiting with exponential backoff to prevent
API quota exhaustion and handle transient failures gracefully.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar
from functools import wraps

from loguru import logger


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0


@dataclass
class RateLimiterState:
    """State tracking for rate limiter."""
    minute_requests: list[float] = field(default_factory=list)
    hour_requests: list[float] = field(default_factory=list)
    last_request: float = 0.0
    consecutive_failures: int = 0


# Per-API rate limiter states
_rate_limiter_states: dict[str, RateLimiterState] = {}


# Default configurations per API service
# Updated 2026-01-24 based on actual API documentation research
DEFAULT_RATE_LIMITS: dict[str, RateLimitConfig] = {
    # OpenAI: Tier-based, 500+ RPM typical. Conservative config.
    "openai": RateLimitConfig(requests_per_minute=60, requests_per_hour=500),
    # Perplexity: Standard limits
    "perplexity": RateLimitConfig(requests_per_minute=30, requests_per_hour=300),
    # Tavily: Standard limits
    "tavily": RateLimitConfig(requests_per_minute=60, requests_per_hour=1000),
    # Serper: Higher limits available
    "serper": RateLimitConfig(requests_per_minute=100, requests_per_hour=2500),
    # Exa: Standard limits
    "exa": RateLimitConfig(requests_per_minute=60, requests_per_hour=1000),
    # YouTube: 10K units/day. Search=100 units, so ~100 searches/day max.
    # Using 6 RPM to spread across the day (6*60*24=8640 units if all searches)
    "youtube": RateLimitConfig(requests_per_minute=6, requests_per_hour=100),
    # YouTube read operations (list videos, get details) = 1 unit each
    "youtube_read": RateLimitConfig(requests_per_minute=60, requests_per_hour=1000),
    # Reddit: 60 RPM with OAuth
    "reddit": RateLimitConfig(requests_per_minute=60, requests_per_hour=600),
    # Supadata: Plan-dependent, conservative for stability
    "supadata": RateLimitConfig(requests_per_minute=10, requests_per_hour=100),
    # Whisper: 50 RPM default, keeping conservative due to upload time
    "whisper": RateLimitConfig(requests_per_minute=10, requests_per_hour=50),
    # Gemini Paid Tier 1: 150-300 RPM, 1M TPM. Using 100 RPM for safety.
    "gemini": RateLimitConfig(requests_per_minute=100, requests_per_hour=2000),
    # GDELT: Standard limits
    "gdelt": RateLimitConfig(requests_per_minute=30, requests_per_hour=300),
    # Jina with API key: 500 RPM, 2M TPM. Using 200 RPM for safety.
    "jina": RateLimitConfig(requests_per_minute=200, requests_per_hour=5000),
    # Google Drive: Standard limits
    "google_drive": RateLimitConfig(requests_per_minute=60, requests_per_hour=300),
    # Supabase: Very high limits (1200 reads/s), no real concern
    "supabase": RateLimitConfig(requests_per_minute=500, requests_per_hour=10000),
    # Default fallback
    "default": RateLimitConfig(requests_per_minute=60, requests_per_hour=1000),
}


def get_rate_limiter_state(api_name: str) -> RateLimiterState:
    """Get or create rate limiter state for an API."""
    if api_name not in _rate_limiter_states:
        _rate_limiter_states[api_name] = RateLimiterState()
    return _rate_limiter_states[api_name]


def get_rate_limit_config(api_name: str) -> RateLimitConfig:
    """Get rate limit configuration for an API."""
    return DEFAULT_RATE_LIMITS.get(api_name, DEFAULT_RATE_LIMITS["default"])


def _cleanup_old_requests(state: RateLimiterState) -> None:
    """Remove expired request timestamps from tracking lists."""
    now = time.time()
    minute_ago = now - 60
    hour_ago = now - 3600

    # Clean minute tracking
    state.minute_requests = [t for t in state.minute_requests if t > minute_ago]

    # Clean hour tracking
    state.hour_requests = [t for t in state.hour_requests if t > hour_ago]


def check_rate_limit(api_name: str) -> tuple[bool, float]:
    """
    Check if a request can be made without exceeding rate limits.

    Args:
        api_name: Name of the API to check

    Returns:
        Tuple of (can_proceed, wait_time_seconds)
    """
    state = get_rate_limiter_state(api_name)
    config = get_rate_limit_config(api_name)

    _cleanup_old_requests(state)

    now = time.time()

    # Check minute limit
    if len(state.minute_requests) >= config.requests_per_minute:
        oldest_minute_request = min(state.minute_requests)
        wait_time = 60 - (now - oldest_minute_request)
        if wait_time > 0:
            logger.debug(f"Rate limit: {api_name} minute limit reached, wait {wait_time:.1f}s")
            return False, wait_time

    # Check hour limit
    if len(state.hour_requests) >= config.requests_per_hour:
        oldest_hour_request = min(state.hour_requests)
        wait_time = 3600 - (now - oldest_hour_request)
        if wait_time > 0:
            logger.debug(f"Rate limit: {api_name} hour limit reached, wait {wait_time:.1f}s")
            return False, wait_time

    return True, 0.0


def record_request(api_name: str) -> None:
    """Record that a request was made to an API."""
    state = get_rate_limiter_state(api_name)
    now = time.time()

    state.minute_requests.append(now)
    state.hour_requests.append(now)
    state.last_request = now


def record_success(api_name: str) -> None:
    """Record a successful request (resets failure counter)."""
    state = get_rate_limiter_state(api_name)
    state.consecutive_failures = 0


def record_failure(api_name: str) -> None:
    """Record a failed request (increments failure counter)."""
    state = get_rate_limiter_state(api_name)
    state.consecutive_failures += 1


def get_backoff_delay(api_name: str) -> float:
    """
    Calculate exponential backoff delay based on failure count.

    Args:
        api_name: Name of the API

    Returns:
        Delay in seconds to wait before retrying
    """
    state = get_rate_limiter_state(api_name)
    config = get_rate_limit_config(api_name)

    if state.consecutive_failures == 0:
        return 0.0

    delay = config.base_delay * (config.exponential_base ** (state.consecutive_failures - 1))
    return min(delay, config.max_delay)


async def wait_for_rate_limit(api_name: str) -> None:
    """Wait until rate limit allows a request."""
    can_proceed, wait_time = check_rate_limit(api_name)
    if not can_proceed:
        logger.info(f"Rate limiting {api_name}: waiting {wait_time:.1f}s")
        await asyncio.sleep(wait_time)


def sync_wait_for_rate_limit(api_name: str) -> None:
    """Synchronous version - wait until rate limit allows a request."""
    can_proceed, wait_time = check_rate_limit(api_name)
    if not can_proceed:
        logger.info(f"Rate limiting {api_name}: waiting {wait_time:.1f}s")
        time.sleep(wait_time)


T = TypeVar('T')


def with_rate_limit(api_name: str):
    """
    Decorator to apply rate limiting with automatic retry and backoff.

    Usage:
        @with_rate_limit("openai")
        async def call_openai(prompt: str) -> str:
            # Make API call
            ...

        @with_rate_limit("tavily")
        def search_tavily(query: str) -> list:
            # Make API call
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                config = get_rate_limit_config(api_name)
                last_error: Optional[Exception] = None

                for attempt in range(config.max_retries + 1):
                    # Wait for rate limit
                    await wait_for_rate_limit(api_name)

                    # Apply backoff if we had failures
                    backoff = get_backoff_delay(api_name)
                    if backoff > 0:
                        logger.debug(f"Backoff {api_name}: waiting {backoff:.1f}s (attempt {attempt + 1})")
                        await asyncio.sleep(backoff)

                    try:
                        record_request(api_name)
                        result = await func(*args, **kwargs)
                        record_success(api_name)
                        return result
                    except Exception as e:
                        record_failure(api_name)
                        last_error = e

                        if attempt < config.max_retries:
                            logger.warning(
                                f"{api_name} request failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}"
                            )
                        else:
                            logger.error(f"{api_name} request failed after {config.max_retries + 1} attempts: {e}")

                # Raise the last error if all retries failed
                if last_error:
                    raise last_error
                raise RuntimeError(f"{api_name} request failed with no error captured")

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> T:
                config = get_rate_limit_config(api_name)
                last_error: Optional[Exception] = None

                for attempt in range(config.max_retries + 1):
                    # Wait for rate limit
                    sync_wait_for_rate_limit(api_name)

                    # Apply backoff if we had failures
                    backoff = get_backoff_delay(api_name)
                    if backoff > 0:
                        logger.debug(f"Backoff {api_name}: waiting {backoff:.1f}s (attempt {attempt + 1})")
                        time.sleep(backoff)

                    try:
                        record_request(api_name)
                        result = func(*args, **kwargs)
                        record_success(api_name)
                        return result
                    except Exception as e:
                        record_failure(api_name)
                        last_error = e

                        if attempt < config.max_retries:
                            logger.warning(
                                f"{api_name} request failed (attempt {attempt + 1}/{config.max_retries + 1}): {e}"
                            )
                        else:
                            logger.error(f"{api_name} request failed after {config.max_retries + 1} attempts: {e}")

                # Raise the last error if all retries failed
                if last_error:
                    raise last_error
                raise RuntimeError(f"{api_name} request failed with no error captured")

            return sync_wrapper

    return decorator


def reset_rate_limiter(api_name: Optional[str] = None) -> None:
    """
    Reset rate limiter state (for testing or error recovery).

    Args:
        api_name: Specific API to reset, or None to reset all
    """
    if api_name:
        if api_name in _rate_limiter_states:
            _rate_limiter_states[api_name] = RateLimiterState()
    else:
        _rate_limiter_states.clear()


def get_rate_limit_stats(api_name: str) -> dict[str, Any]:
    """
    Get current rate limit statistics for an API.

    Returns:
        Dict with current stats (useful for monitoring/debugging)
    """
    state = get_rate_limiter_state(api_name)
    config = get_rate_limit_config(api_name)

    _cleanup_old_requests(state)

    return {
        "api_name": api_name,
        "requests_last_minute": len(state.minute_requests),
        "requests_last_hour": len(state.hour_requests),
        "minute_limit": config.requests_per_minute,
        "hour_limit": config.requests_per_hour,
        "consecutive_failures": state.consecutive_failures,
        "current_backoff": get_backoff_delay(api_name),
    }
