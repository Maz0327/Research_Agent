# Supabase Connection Handling Analysis

**Investigation:** Connection resilience during Supabase server updates
**Date:** 2026-01-24 17:16
**Investigator:** debugger subagent

---

## Executive Summary

**Current State:** Supabase connection handling lacks automatic reconnection logic for handling transient connection drops during server updates/maintenance.

**Risk Level:** MEDIUM - Active operations may fail during brief Supabase maintenance windows (typically 1-3 minutes during platform updates).

**Key Findings:**
- Connection pooling exists but without reconnect-on-stale detection
- No health check or heartbeat mechanism
- HTTP client timeout handling present but no retry-on-connection-failure
- Rate limiter has retry logic but only for API rate limits, not connection failures
- Frontend has basic error handling but no automatic retry on network errors

---

## Technical Analysis

### 1. Backend Connection Architecture

#### 1.1 Supabase Client Initialization

**File:** `backend/state/impl/supabase_store.py`

```python
# Lines 23-32: Singleton client creation
@lru_cache()
def _get_supabase_client() -> Client:
    """Get singleton Supabase client for RPC calls."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")
    return create_client(
        str(settings.supabase_url),
        settings.supabase_service_role_key,
    )
```

**Analysis:**
- Uses `@lru_cache()` for singleton pattern
- Client created ONCE per process lifetime
- No mechanism to detect stale connections
- No reconnect on connection drop

**Gap:** If Supabase server disconnects (e.g., during update), the cached client remains stale until process restart.

---

#### 1.2 HTTP Client Connection Pooling

**File:** `backend/state/impl/supabase_store.py`

```python
# Lines 180-187: HTTP client with connection pooling
def _get_http_client(self) -> httpx.Client:
    """Get or create HTTP client with connection pooling."""
    if self._http_client is None or self._http_client.is_closed:
        self._http_client = httpx.Client(
            timeout=SUPABASE_API_TIMEOUT,  # 15.0 seconds
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return self._http_client
```

**Strengths:**
- Checks `is_closed` state before reusing
- Connection pooling (10 keepalive, 20 max)
- 15s timeout configured

**Gaps:**
- No detection of stale/broken connections within the pool
- No retry-on-connection-failure logic
- Relies on httpx default behavior for stale connection detection

---

#### 1.3 Timeout Configuration

**File:** `backend/config.py`

```python
# Lines 191-194: Supabase timeout
timeout_supabase: float = Field(
    default=5.0, alias="TIMEOUT_SUPABASE",
    description="Timeout for Supabase/database queries"
)
```

**Note:** Timeouts in `supabase.py` use 5.0s, but `supabase_store.py` uses 15.0s (inconsistent).

---

#### 1.4 Error Handling

**File:** `backend/state/impl/supabase_store.py`

**Error handling pattern across all operations:**

```python
# Example from create_job (lines 226-230)
try:
    resp.raise_for_status()
except httpx.HTTPError as e:
    logger.error("Failed to create job in Supabase: %s", sanitize_error_message(e))
    raise  # Re-raise without retry
```

**Analysis:**
- Catches `httpx.HTTPError` (parent of all httpx errors)
- Logs sanitized error message
- **Does NOT retry on connection failures**
- **Does NOT attempt reconnection**

**Exception types NOT handled separately:**
- `httpx.ConnectError` (connection refused/timeout)
- `httpx.TimeoutException` (request timeout)
- `httpx.NetworkError` (DNS/routing failures)

All connection errors bubble up to caller without retry attempt.

---

### 2. Health Check Implementation

**File:** `backend/app/main.py` (lines 226-237)

```python
# Check Supabase
if settings.supabase_url:
    try:
        from backend.state.impl.supabase_store import get_supabase_client
        client = get_supabase_client()
        client.table("jobs").select("id").limit(1).execute()
        health["dependencies"]["supabase"] = "ok"
    except Exception:
        health["dependencies"]["supabase"] = "error"
        health["status"] = "degraded"
```

**Strengths:**
- Performs actual query test (not just connection check)
- Returns degraded status on failure

**Gaps:**
- Only runs on `/health` endpoint calls (reactive, not proactive)
- No background heartbeat/keepalive
- Health check failure does NOT trigger reconnection
- Catches broad `Exception` without granular error handling

---

### 3. Rate Limiter (Not Connection-Aware)

**File:** `backend/utils/rate_limiter.py`

```python
# Lines 71-72: Supabase rate limit config
"supabase": RateLimitConfig(requests_per_minute=500, requests_per_hour=10000),
```

**Analysis:**
- Rate limiter exists for API quota management
- Has retry logic for rate limit errors
- **Does NOT retry on connection failures** (only rate limits)
- Supabase has very high limits (1200 reads/s documented) - not a bottleneck

---

### 4. Atomic Operations (RPC Fallback)

**File:** `backend/state/impl/supabase_store.py` (lines 476-557)

```python
def _update_job_atomic(...) -> Optional[JobRecord]:
    """Update job using atomic RPC function for JSONB merges."""
    try:
        client = _get_supabase_client()
        # ... RPC call ...
        result = client.rpc("atomic_update_job", rpc_params).execute()
        # ...
    except Exception as e:
        # Log the error and fall back to non-atomic update
        logger.warning(
            f"Atomic update failed for job {job_id}, falling back to non-atomic: {sanitize_error_message(e)}"
        )
        return self._update_job_fallback(...)
```

**Strengths:**
- Graceful degradation to fallback (READ-MERGE-WRITE)
- Prevents total failure on RPC unavailability

**Gaps:**
- Fallback has race conditions (acknowledged in docstring)
- Still no connection retry - just falls back to different method
- If connection is down, fallback will also fail

---

### 5. Frontend Connection Handling

**File:** `frontend/lib/supabase.ts`

```typescript
// Lines 22-28: Client configuration
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,  // ✅ Token refresh enabled
    detectSessionInUrl: true,
  },
});
```

**Strengths:**
- Auto token refresh enabled
- Session persistence

**Gaps:**
- No custom retry configuration
- Relies on default `@supabase/supabase-js` behavior
- No manual reconnection logic
- Frontend API calls (via fetch/axios) lack retry on network errors

---

## Reconnection Logic Assessment

### What Exists:

1. **HTTP Client Recreation:**
   - `SupabaseJobStore._get_http_client()` recreates client if `is_closed`
   - Only detects hard-closed connections, not stale ones

2. **Health Check:**
   - `/health` endpoint tests Supabase connectivity
   - Reactive only (no proactive reconnection)

3. **Fallback Mechanisms:**
   - Atomic RPC → fallback to REST API
   - Doesn't solve connection issues

### What's Missing:

1. **Automatic Reconnection:**
   - No retry on `httpx.ConnectError`
   - No retry on `httpx.TimeoutException`
   - No stale connection detection in pool

2. **Connection Validation:**
   - No pre-request connection health check
   - No periodic keepalive/heartbeat

3. **Exponential Backoff:**
   - Rate limiter has backoff for rate limits
   - No backoff for connection failures

4. **Circuit Breaker:**
   - No circuit breaker pattern for repeated failures
   - Operations keep retrying indefinitely (until timeout)

---

## Gaps Identified

### Critical Gaps:

1. **No Connection Retry Logic**
   - All Supabase operations fail immediately on connection error
   - No automatic retry for transient failures (DNS, routing, server restart)

2. **Stale Client Detection**
   - Singleton client via `@lru_cache()` never refreshes
   - Stale connections in HTTP pool not proactively detected

3. **Inconsistent Timeouts**
   - `supabase.py`: 5.0s timeout
   - `supabase_store.py`: 15.0s timeout
   - Config default: 5.0s

### Medium Gaps:

4. **No Background Health Check**
   - Health endpoint only runs on-demand
   - No proactive connection testing

5. **Frontend Network Resilience**
   - No retry logic in frontend API calls
   - User sees error immediately on transient failure

6. **Error Granularity**
   - Catches broad `httpx.HTTPError`
   - Doesn't distinguish connection errors from HTTP errors

---

## Impact During Supabase Updates

### Scenario: Supabase Platform Update (1-3 minute window)

**Timeline:**
1. **T+0s:** Supabase begins server restart
2. **T+1s:** Existing connections drop
3. **T+2s:** Backend job tries to update job status
   - httpx detects connection error
   - Raises `httpx.ConnectError`
   - Worker task fails (no retry)
   - Job marked as failed in Celery
4. **T+180s:** Supabase server back online
5. **User Impact:** Job appears failed, must be manually restarted

**Current Behavior:**
- ❌ No automatic retry on connection failure
- ❌ Job fails even for 1-second disconnect
- ❌ User must manually retry job

**Expected Behavior:**
- ✅ Automatic retry with exponential backoff
- ✅ Job continues after brief disconnect
- ✅ Warning logged but operation succeeds

---

## Recommendations

### Priority 1: Connection Retry Logic

**Add retry wrapper for Supabase operations:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    reraise=True
)
def _supabase_operation_with_retry(operation: Callable) -> Any:
    """Execute Supabase operation with automatic retry on connection failures."""
    return operation()
```

**Impact:**
- Resilience to 1-3 minute outages
- 3 retries with backoff: 1s, 2s, 4s (7s total)
- Still fails fast on persistent issues

---

### Priority 2: Stale Client Detection

**Invalidate cached client on connection error:**

```python
# Clear lru_cache on connection failure
def _handle_connection_error():
    _get_supabase_client.cache_clear()  # Force new client creation
```

**Impact:**
- Fresh client after connection drop
- Minimal code change

---

### Priority 3: Standardize Timeouts

**Set consistent timeout across all Supabase calls:**

```python
# In config.py
timeout_supabase: float = Field(default=10.0)  # Increase from 5.0

# Use consistently in all files:
# - supabase.py: Use settings.timeout_supabase
# - supabase_store.py: Use settings.timeout_supabase (not hardcoded 15.0)
```

**Impact:**
- Predictable timeout behavior
- Easier to tune for network conditions

---

### Priority 4: Health Check Background Task

**Add periodic Supabase health check:**

```python
from apscheduler.schedulers.background import BackgroundScheduler

def check_supabase_health():
    """Proactive health check, logs warning if degraded."""
    try:
        client = _get_supabase_client()
        client.table("jobs").select("id").limit(1).execute()
        logger.info("Supabase health check: OK")
    except Exception as e:
        logger.warning(f"Supabase health check failed: {e}")
        _get_supabase_client.cache_clear()  # Trigger reconnect

scheduler = BackgroundScheduler()
scheduler.add_job(check_supabase_health, 'interval', minutes=5)
scheduler.start()
```

**Impact:**
- Early detection of connection issues
- Proactive reconnection before user operations fail

---

### Priority 5: Frontend Retry Logic

**Add retry interceptor for API calls:**

```typescript
// frontend/lib/api-client.ts
import axios from 'axios';
import axiosRetry from 'axios-retry';

const apiClient = axios.create({ baseURL: '/api' });

axiosRetry(apiClient, {
  retries: 3,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (error) => {
    return axiosRetry.isNetworkOrIdempotentRequestError(error) ||
           error.response?.status === 503;
  }
});
```

**Impact:**
- Frontend survives brief network glitches
- Better UX during server restarts

---

## Unresolved Questions

1. **Supabase SDK Behavior:**
   - Does `@supabase/supabase-js` client have built-in reconnect logic?
   - What's the default connection pool behavior in `supabase-py`?

2. **Celery Task Retry:**
   - Should Celery tasks auto-retry on worker-level Supabase failures?
   - Current: Tasks fail immediately, no Celery retry configured

3. **PostgREST Connection Pooling:**
   - Does PostgREST API (Supabase REST layer) maintain connections?
   - Are HTTP connections truly stateless or pooled?

4. **Monitoring:**
   - Should we track Supabase connection errors separately in metrics?
   - Alert on repeated connection failures?

5. **Testing:**
   - How to simulate Supabase server restart in tests?
   - Integration test for connection recovery?

---

## Summary

**Connection Handling State:**
- ✅ Basic timeout configuration
- ✅ Connection pooling (httpx)
- ✅ Health check endpoint
- ❌ **No automatic retry on connection failures**
- ❌ **No stale connection detection**
- ❌ **No background health monitoring**

**Recommendation:** Implement Priority 1 (retry logic) immediately to handle Supabase maintenance windows gracefully. Priorities 2-5 can follow incrementally.

**Effort Estimate:**
- Priority 1: 2-4 hours (retry decorator + testing)
- Priority 2: 1 hour (cache invalidation)
- Priority 3: 30 minutes (config standardization)
- Priority 4: 2 hours (background scheduler)
- Priority 5: 2 hours (frontend retry interceptor)

**Total:** 7.5-9.5 hours for full resilience implementation.
