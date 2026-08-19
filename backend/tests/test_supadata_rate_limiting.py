"""Tests for Supadata stagger, concurrency capping, and 429 handling.

Cover for P3 work-order item A2: five parallel transcript pulls returned HTTP
429 on 2026-08-17 even though the per-minute budget was untouched, because the
limit is instantaneous. Requests are now staggered, capped in flight, and a
429's `Retry-After` is honored.
"""
import threading
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.integrations.supadata_client import (
    SupadataClient,
    SupadataError,
    SupadataRateLimitError,
    _parse_retry_after,
)
from backend.utils.rate_limiter import (
    DEFAULT_RATE_LIMITS,
    RateLimitConfig,
    get_concurrency_gate,
    get_rate_limit_config,
    get_retry_after,
    reserve_stagger_slot,
    reset_rate_limiter,
    with_rate_limit,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset rate limiter state before and after each test."""
    reset_rate_limiter()
    yield
    reset_rate_limiter()


@pytest.fixture
def staggered_api():
    """Register a fast test API with a stagger and a concurrency cap of 2."""
    name = "test_staggered_api"
    DEFAULT_RATE_LIMITS[name] = RateLimitConfig(
        requests_per_minute=600,
        requests_per_hour=6000,
        max_retries=0,
        min_interval_seconds=0.05,
        max_concurrent=2,
    )
    yield name
    DEFAULT_RATE_LIMITS.pop(name, None)


class TestSupadataConfig:
    """The Supadata bucket carries the stagger that stops the burst."""

    def test_supadata_has_stagger_and_concurrency_cap(self):
        """Config encodes the 08-17 fix: spaced starts, at most 2 in flight."""
        config = get_rate_limit_config("supadata")
        assert config.min_interval_seconds >= 1.0
        assert config.max_concurrent == 2

    def test_unstaggered_apis_are_unaffected(self):
        """APIs without a stagger keep their old behavior."""
        assert get_rate_limit_config("gemini").min_interval_seconds == 0.0
        assert get_rate_limit_config("gemini").max_concurrent == 0
        assert get_concurrency_gate("gemini") is None
        assert reserve_stagger_slot("gemini") == 0.0


class TestStaggerReservation:
    """`reserve_stagger_slot` hands each caller its own start slot."""

    def test_successive_reservations_space_out(self, staggered_api):
        """Each reservation pushes the next one further into the future."""
        first = reserve_stagger_slot(staggered_api)
        second = reserve_stagger_slot(staggered_api)
        third = reserve_stagger_slot(staggered_api)

        assert first == 0.0
        assert second >= 0.04
        assert third >= second + 0.04

    def test_concurrent_reservations_are_unique(self, staggered_api):
        """Threads racing for slots queue instead of all getting slot zero."""
        delays: list[float] = []
        lock = threading.Lock()

        def reserve():
            delay = reserve_stagger_slot(staggered_api)
            with lock:
                delays.append(delay)

        threads = [threading.Thread(target=reserve) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Five distinct slots, spaced by the configured interval.
        assert len(delays) == 5
        assert sorted(delays) == pytest.approx(
            [0.0, 0.05, 0.10, 0.15, 0.20], abs=0.02
        )


class TestConcurrencyGate:
    """The decorator never lets more than `max_concurrent` calls run at once."""

    def test_in_flight_calls_are_capped(self, staggered_api):
        """Five threads through a cap-2 API never overlap three-deep."""
        in_flight = 0
        peak = 0
        lock = threading.Lock()

        @with_rate_limit(staggered_api)
        def slow_call():
            nonlocal in_flight, peak
            with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            time.sleep(0.05)
            with lock:
                in_flight -= 1
            return "ok"

        threads = [threading.Thread(target=slow_call) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert peak <= 2


class TestRetryAfter:
    """Server-supplied retry delays beat guessed backoff."""

    def test_get_retry_after_reads_the_attribute(self):
        """An exception carrying `retry_after` surfaces its delay."""
        error = SupadataRateLimitError("rate limited", retry_after=7.0)
        assert get_retry_after(error) == 7.0

    def test_get_retry_after_ignores_plain_errors(self):
        """An ordinary exception yields no delay."""
        assert get_retry_after(ValueError("nope")) == 0.0
        assert get_retry_after(SupadataRateLimitError("no header")) == 0.0

    def test_decorator_sleeps_the_server_delay(self):
        """The retry path waits the delay the server asked for."""
        name = "test_retry_after_api"
        DEFAULT_RATE_LIMITS[name] = RateLimitConfig(
            requests_per_minute=600,
            requests_per_hour=6000,
            max_retries=1,
            base_delay=0.0,
            min_interval_seconds=0.0,
        )
        try:
            calls = {"n": 0}

            @with_rate_limit(name)
            def flaky():
                calls["n"] += 1
                if calls["n"] == 1:
                    raise SupadataRateLimitError("429", retry_after=3.0)
                return "second attempt"

            with patch("backend.utils.rate_limiter.time.sleep") as mock_sleep:
                assert flaky() == "second attempt"

            slept = [call.args[0] for call in mock_sleep.call_args_list]
            assert 3.0 in slept
        finally:
            DEFAULT_RATE_LIMITS.pop(name, None)

    def test_retry_after_is_capped_at_max_delay(self):
        """An absurd Retry-After is clamped to the configured ceiling."""
        name = "test_retry_cap_api"
        DEFAULT_RATE_LIMITS[name] = RateLimitConfig(
            requests_per_minute=600,
            requests_per_hour=6000,
            max_retries=1,
            base_delay=0.0,
            max_delay=10.0,
            min_interval_seconds=0.0,
        )
        try:
            calls = {"n": 0}

            @with_rate_limit(name)
            def flaky():
                calls["n"] += 1
                if calls["n"] == 1:
                    raise SupadataRateLimitError("429", retry_after=9999.0)
                return "ok"

            with patch("backend.utils.rate_limiter.time.sleep") as mock_sleep:
                assert flaky() == "ok"

            slept = [call.args[0] for call in mock_sleep.call_args_list]
            assert max(slept) == 10.0
        finally:
            DEFAULT_RATE_LIMITS.pop(name, None)


class TestSupadataClient429:
    """The client turns a 429 into a typed, delay-carrying error."""

    def _client(self):
        client = SupadataClient.__new__(SupadataClient)
        client.api_key = "test-key"
        client.http = MagicMock()
        return client

    def test_parse_retry_after_header(self):
        """Numeric `Retry-After` headers parse; anything else is None."""
        assert _parse_retry_after(
            httpx.Response(429, headers={"Retry-After": "12"})
        ) == 12.0
        assert _parse_retry_after(
            httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
        ) is None
        assert _parse_retry_after(httpx.Response(429)) is None

    def test_transcript_429_raises_rate_limit_error(self):
        """A 429 on /transcript raises the typed error with its delay."""
        client = self._client()
        client.http.get.return_value = httpx.Response(
            429, headers={"Retry-After": "5"}, text="rate limited"
        )

        with pytest.raises(SupadataRateLimitError) as excinfo:
            SupadataClient.get_transcript.__wrapped__(client, "https://youtu.be/abc")

        assert excinfo.value.retry_after == 5.0
        assert isinstance(excinfo.value, SupadataError)

    def test_metadata_429_raises_rate_limit_error(self):
        """A 429 on /metadata raises the typed error too."""
        client = self._client()
        client.http.get.return_value = httpx.Response(429)

        with pytest.raises(SupadataRateLimitError):
            SupadataClient.fetch_metadata.__wrapped__(client, "https://youtu.be/abc")

    def test_non_429_errors_stay_generic(self):
        """A 500 is still a plain SupadataError, not a rate-limit error."""
        client = self._client()
        client.http.get.return_value = httpx.Response(500, text="boom")

        with pytest.raises(SupadataError) as excinfo:
            SupadataClient.fetch_metadata.__wrapped__(client, "https://youtu.be/abc")

        assert not isinstance(excinfo.value, SupadataRateLimitError)
