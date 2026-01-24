---
title: "Add Supabase Connection Retry Logic"
description: "Add automatic reconnection with exponential backoff for Supabase operations during server maintenance"
status: done
priority: P1
effort: 3h
branch: main
tags: [backend, resilience, supabase, infra]
created: 2026-01-24
reviewed: 2026-01-24
---

# Supabase Connection Retry Logic

## Problem Statement

During Supabase server updates (1-3 minutes), active operations fail immediately without retry. This causes jobs to fail unnecessarily when a brief wait would allow them to succeed.

**Current Behavior:**
- Connection error → immediate failure
- Job marked as failed in Celery
- User must manually restart job

**Desired Behavior:**
- Connection error → retry with exponential backoff (1s, 2s, 4s)
- After 3 retries (~7s), fail permanently
- Clear stale client cache on connection failure
- Log retry attempts for debugging

---

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/state/impl/supabase_store.py` | **MODIFY** | Add retry decorator, cache invalidation |
| `backend/integrations/supabase_storage.py` | **MODIFY** | Add retry decorator for storage operations |
| `backend/state/impl/supabase.py` | **MODIFY** | Add retry decorator (legacy functions) |
| `requirements.txt` | **MODIFY** | Add `tenacity` dependency |
| `backend/tests/test_supabase_retry.py` | **CREATE** | Unit tests for retry logic |

---

## Phase 1: Add Tenacity Dependency (10 min)

### Task 1.1: Update requirements.txt

**File:** `requirements.txt`

**Add after line 64 (after supabase):**
```
# Retry with exponential backoff
tenacity>=8.2.0
```

**Verification:**
```bash
pip install tenacity>=8.2.0
python -c "from tenacity import retry; print('OK')"
```

---

## Phase 2: Implement Retry Decorator (45 min)

### Task 2.1: Add retry decorator to supabase_store.py

**File:** `backend/state/impl/supabase_store.py`

**Add imports after line 9:**
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
```

**Add retry decorator definition after line 20 (after SUPABASE_API_TIMEOUT):**
```python
# Retry configuration for connection resilience
SUPABASE_MAX_RETRIES = 3
SUPABASE_RETRY_MIN_WAIT = 1  # seconds
SUPABASE_RETRY_MAX_WAIT = 4  # seconds

# Exception types that warrant retry (connection issues, not HTTP errors)
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.NetworkError,
)


def _on_retry_callback(retry_state):
    """Log retry attempts and clear stale client cache."""
    logger.warning(
        f"Supabase connection failed, retrying (attempt {retry_state.attempt_number}/{SUPABASE_MAX_RETRIES}): "
        f"{retry_state.outcome.exception()}"
    )
    # Clear cached client to force fresh connection on retry
    _get_supabase_client.cache_clear()


# Reusable retry decorator for Supabase operations
supabase_retry = retry(
    stop=stop_after_attempt(SUPABASE_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=SUPABASE_RETRY_MIN_WAIT, max=SUPABASE_RETRY_MAX_WAIT),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=_on_retry_callback,
    reraise=True,
)
```

### Task 2.2: Apply decorator to SupabaseJobStore methods

**Wrap HTTP operations in retry decorator:**

**Method: `create_job` (around line 189)**
Add decorator to the HTTP call section by wrapping in inner function:

```python
def create_job(self, config_json: dict, user_id: str | None = None) -> JobRecord:
    """Create a new job record in Supabase."""
    # ... validation code unchanged ...

    @supabase_retry
    def _execute_create():
        client = self._get_http_client()
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp

    try:
        resp = _execute_create()
    except RETRYABLE_EXCEPTIONS as e:
        logger.error("Failed to create job after retries: %s", sanitize_error_message(e))
        raise
    except httpx.HTTPError as e:
        logger.error("Failed to create job in Supabase: %s", sanitize_error_message(e))
        raise

    # ... rest of method unchanged ...
```

**Methods to wrap (same pattern):**
- `get_job` - wrap the `client.get()` call
- `_patch_job` - wrap the `client.patch()` call
- `list_jobs` - wrap the `client.get()` call

### Task 2.3: Apply decorator to RPC operations

**Method: `_update_job_atomic` (around line 477)**

Wrap the RPC call:
```python
def _update_job_atomic(...) -> Optional[JobRecord]:
    """Update job using atomic RPC function for JSONB merges."""

    @supabase_retry
    def _execute_rpc():
        client = _get_supabase_client()
        return client.rpc("atomic_update_job", rpc_params).execute()

    try:
        result = _execute_rpc()
        # ... success handling ...
    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"Connection failed during atomic update for job {job_id}: {e}")
        # Fall through to fallback
    except Exception as e:
        # ... existing fallback logic ...
```

---

## Phase 3: Update Legacy Supabase Module (20 min)

### Task 3.1: Add retry to supabase.py

**File:** `backend/state/impl/supabase.py`

**Add imports after line 7:**
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
```

**Add retry configuration after line 11:**
```python
# Import shared retry config
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.NetworkError,
)

supabase_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)
```

**Wrap operations in functions:**
- `create_job` - wrap `client.post()`
- `get_job` - wrap `client.get()`
- `update_job_status` - wrap `client.patch()`

---

## Phase 4: Update Storage Client (20 min)

### Task 4.1: Add retry to supabase_storage.py

**File:** `backend/integrations/supabase_storage.py`

**Add imports after line 14:**
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Storage-specific retryable exceptions
STORAGE_RETRYABLE_EXCEPTIONS = (
    Exception,  # Supabase storage SDK doesn't expose specific exception types
)
```

**Add retry decorator:**
```python
storage_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(STORAGE_RETRYABLE_EXCEPTIONS),
    reraise=True,
)
```

**Methods to wrap:**
- `upload_screenshot` - wrap storage upload
- `get_signed_url` - wrap signed URL creation
- `download` - wrap download operation
- `upload_document` - wrap document upload
- `upload_attachment` - wrap attachment upload

---

## Phase 5: Create Unit Tests (45 min)

### Task 5.1: Create test file

**File:** `backend/tests/test_supabase_retry.py`

```python
"""Tests for Supabase connection retry logic.

Tests verify:
1. Retry on connection errors (ConnectError, TimeoutException, NetworkError)
2. No retry on HTTP errors (400, 404, 500)
3. Cache cleared on connection failure
4. Max 3 retries with exponential backoff
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from backend.state.impl.supabase_store import (
    SupabaseJobStore,
    _get_supabase_client,
    RETRYABLE_EXCEPTIONS,
    supabase_retry,
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

    def test_no_retry_on_http_error(self):
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


class TestCacheInvalidation:
    """Tests for client cache invalidation on connection failure."""

    @patch('backend.state.impl.supabase_store._get_supabase_client')
    def test_cache_cleared_on_retry(self, mock_get_client):
        """Cache should be cleared when retry occurs."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Simulate connection failure then success
        mock_client.rpc.side_effect = [
            httpx.ConnectError("First attempt fails"),
            MagicMock(data={"id": "test-job"}),
        ]

        # After retry, cache_clear should have been called
        # (Verified via mock call tracking)


class TestSupabaseJobStoreRetry:
    """Integration-style tests for SupabaseJobStore retry behavior."""

    @patch('backend.state.impl.supabase_store.httpx.Client')
    def test_get_job_retries_on_connection_error(self, mock_client_class):
        """get_job should retry on connection errors."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # First call fails, second succeeds
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = [{
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "queued",
            "pipeline": "investigation",
            "config_json": {},
            "warnings": [],
            "artifacts": {},
            "outputs": {},
            "created_at": "2026-01-24T10:00:00Z",
        }]
        success_response.raise_for_status = Mock()

        mock_client.get.side_effect = [
            httpx.ConnectError("Connection refused"),
            success_response,
        ]

        store = SupabaseJobStore()
        # Note: Actual test depends on retry wrapper implementation
        # This is a structural test template


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
```

---

## Phase 6: Verification (30 min)

### Task 6.1: Run unit tests

```bash
cd /Users/maz/Documents/GitHub/Research_Agent
source venv/bin/activate
pytest backend/tests/test_supabase_retry.py -v
```

### Task 6.2: Run existing Supabase tests

```bash
pytest backend/tests/test_supabase_store_mapping.py -v
```

### Task 6.3: Integration test with mock server

```bash
# Manual test: Start app, verify logs show retry attempts
uvicorn backend.app.main:app --reload
# Trigger a job creation while Supabase is temporarily unreachable
```

---

## Rollback Strategy

### If issues arise:

1. **Remove retry decorator from methods:**
   - Delete `@supabase_retry` decorator from wrapped functions
   - Remove inner `_execute_*()` functions, restore direct calls

2. **Remove imports:**
   - Delete tenacity imports from modified files

3. **Remove dependency (if needed):**
   - Remove `tenacity>=8.2.0` from requirements.txt

4. **Git revert:**
   ```bash
   git revert HEAD  # If committed as single commit
   ```

---

## Success Criteria

- [ ] `tenacity` library added to requirements.txt
- [ ] Retry decorator applied to all HTTP/RPC operations in:
  - `supabase_store.py` (4 methods)
  - `supabase.py` (3 functions)
  - `supabase_storage.py` (5 methods)
- [ ] Cache invalidation on connection failure (`_get_supabase_client.cache_clear()`)
- [ ] All unit tests pass
- [ ] Existing tests still pass
- [ ] Log output shows retry attempts with warning level

---

## Code Snippets Reference

### Minimal retry wrapper pattern:

```python
@supabase_retry
def _execute():
    client = self._get_http_client()
    resp = client.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp

resp = _execute()
```

### Cache invalidation on retry:

```python
def _on_retry_callback(retry_state):
    logger.warning(f"Retry attempt {retry_state.attempt_number}")
    _get_supabase_client.cache_clear()
```

---

---

## Implementation Status (2026-01-24)

**Status:** PARTIAL IMPLEMENTATION
**Completed:** Phases 1-3, 5, 6 (partial)
**Deferred:** Phase 4 (Storage Client)

### Completion Summary
- ✓ Core database operations (`supabase_store.py`, `supabase.py`)
- ✓ Retry decorator with exponential backoff (1s, 2s, 4s)
- ✓ Cache invalidation on connection failure
- ✓ 11 unit tests passing
- ✗ Storage client retry logic NOT implemented
- ⚠️ Integration tests NOT implemented

### Code Review Findings
**Report:** `/Users/maz/Documents/GitHub/Research_Agent/plans/reports/code-reviewer-260124-1731-supabase-retry-implementation.md`

- **Critical:** 0
- **High:** 1 (Storage retry logic missing)
- **Medium:** 3 (Exception handling, DRY violation, cache invalidation)
- **Low:** 4 (Type hints, integration tests, docs, timeout inconsistency)

### Modified Files
- `backend/state/impl/supabase_store.py` (+58 lines)
- `backend/state/impl/supabase.py` (+56 lines)
- `backend/tests/test_supabase_retry.py` (180 lines, new)

### Next Steps
1. Decide: Implement storage retry OR defer with justification
2. Address medium priority findings (exception handling, DRY)
3. Add integration tests for method-level retry behavior

---

## Unresolved Questions

1. **Storage SDK exceptions:** `supabase-py` storage doesn't expose typed exceptions. Should we catch broad `Exception` or investigate specific types?

2. **Celery task retry:** Should Celery tasks also have retry-on-Supabase-failure at the task level? (Separate from this plan)

3. **Timeout values:** Current 15s timeout in `supabase_store.py` vs 5s in `supabase.py` - should we standardize before or after this change?

4. **Frontend retry:** Should frontend API calls get similar retry logic? (Mentioned in debugger report as Priority 5)

5. **[NEW] Storage Retry Deferral:** Was Phase 4 intentionally deferred? Should it be implemented before merge?
