"""Tests for rate limiter thread safety."""

from concurrent.futures import ThreadPoolExecutor

from backend.utils.rate_limiter import (
    record_request,
    reset_rate_limiter,
    get_rate_limiter_state,
)


class TestRateLimiterThreadSafety:
    """Verify rate limiter handles concurrent access safely."""

    def setup_method(self):
        reset_rate_limiter()

    def test_concurrent_record_requests_no_duplicates(self):
        """Concurrent record_request calls should not lose or duplicate entries."""
        api_name = "test_concurrent"
        num_workers = 10
        requests_per_worker = 50
        total_expected = num_workers * requests_per_worker

        def worker():
            for _ in range(requests_per_worker):
                record_request(api_name)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker) for _ in range(num_workers)]
            for f in futures:
                f.result()

        state = get_rate_limiter_state(api_name)
        assert len(state.minute_requests) == total_expected
        assert len(state.hour_requests) == total_expected

    def test_concurrent_different_apis(self):
        """Concurrent access to different API states should not interfere."""
        apis = [f"api_{i}" for i in range(5)]
        requests_per_api = 20

        def worker(api_name):
            for _ in range(requests_per_api):
                record_request(api_name)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, api) for api in apis]
            for f in futures:
                f.result()

        for api in apis:
            state = get_rate_limiter_state(api)
            assert len(state.minute_requests) == requests_per_api
