"""Simple Redis caching utilities for performance optimization.

Provides caching decorators and functions for expensive database operations.
"""
import json
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from loguru import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed, caching disabled")

from backend.config import get_settings


# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])

# Module-level singleton for Redis client
_redis_client: Optional["redis.Redis"] = None
_redis_init_failed: bool = False


def _get_redis_client() -> Optional["redis.Redis"]:
    """Get or create Redis client singleton for caching.

    Reuses the same connection across all cache operations to avoid
    creating a new connection (and ping test) on every get/set/delete.
    Falls back gracefully if Redis is unavailable.
    """
    global _redis_client, _redis_init_failed

    if not REDIS_AVAILABLE or _redis_init_failed:
        return None

    # Return existing client if connected
    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            # Connection lost — reset and try to reconnect
            _redis_client = None

    try:
        settings = get_settings()
        if not settings.redis_url:
            _redis_init_failed = True
            return None

        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.debug(f"Redis connection failed, caching disabled: {e}")
        _redis_client = None
        return None


def cache_get(key: str) -> Optional[Any]:
    """Get value from cache.

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found/expired
    """
    client = _get_redis_client()
    if not client:
        return None

    try:
        value = client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.debug(f"Cache get failed for key {key}: {e}")
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """Set value in cache with TTL.

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        ttl_seconds: Time to live in seconds (default 5 minutes)

    Returns:
        True if cached successfully, False otherwise
    """
    client = _get_redis_client()
    if not client:
        return False

    try:
        client.setex(key, ttl_seconds, json.dumps(value))
        return True
    except Exception as e:
        logger.debug(f"Cache set failed for key {key}: {e}")
        return False


def cache_delete(key: str) -> bool:
    """Delete value from cache.

    Args:
        key: Cache key

    Returns:
        True if deleted, False otherwise
    """
    client = _get_redis_client()
    if not client:
        return False

    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Cache delete failed for key {key}: {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., "admin:stats:*")

    Returns:
        Number of keys deleted
    """
    client = _get_redis_client()
    if not client:
        return 0

    try:
        keys = list(client.scan_iter(match=pattern))
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.debug(f"Cache delete pattern failed for {pattern}: {e}")
        return 0


def cached(key_prefix: str, ttl_seconds: int = 300):
    """Decorator to cache function results.

    Args:
        key_prefix: Prefix for cache key (function name and args appended)
        ttl_seconds: Time to live in seconds

    Usage:
        @cached("admin:stats", ttl_seconds=60)
        def get_admin_stats():
            # Expensive database operation
            return {"total_users": 100}
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key from function name and args
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.extend(str(a) for a in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache the result
            if cache_set(cache_key, result, ttl_seconds):
                logger.debug(f"Cached {cache_key} for {ttl_seconds}s")

            return result

        return wrapper  # type: ignore
    return decorator


def cached_async(key_prefix: str, ttl_seconds: int = 300):
    """Decorator to cache async function results.

    Args:
        key_prefix: Prefix for cache key
        ttl_seconds: Time to live in seconds

    Usage:
        @cached_async("admin:stats", ttl_seconds=60)
        async def get_admin_stats():
            # Expensive database operation
            return {"total_users": 100}
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key from function name and args
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.extend(str(a) for a in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the result
            if cache_set(cache_key, result, ttl_seconds):
                logger.debug(f"Cached {cache_key} for {ttl_seconds}s")

            return result

        return wrapper  # type: ignore
    return decorator
