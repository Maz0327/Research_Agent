# Database QA - Action Items & Fixes
**Date**: 2025-12-28 14:45
**Severity**: 4 Critical, 6 High Priority

---

## CRITICAL FIXES (Do Immediately)

### Issue #1: InMemoryJobStore Race Condition - Warnings Append

**File**: `/backend/state/impl/in_memory.py`
**Lines**: 99-101
**Severity**: CRITICAL - Data Loss

**Current Code**:
```python
# Append warnings (merge operation)
if warnings_append:
    job.warnings.extend(warnings_append)
```

**Problem**: Lock released before warnings_append executed (line 101 after line 116 return)

**Fix**:
```python
def update_job(
    self,
    job_id: str,
    *,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    progress_percent: Optional[int] = None,
    title: Optional[str] = None,
    error: Optional[str] = None,
    partial_outputs: Optional[dict] = None,
    partial_artifacts: Optional[dict] = None,
    warnings_append: Optional[list[str]] = None,
    config_json: Optional[dict] = None,
    artifacts: Optional[Artifacts] = None,
    warnings: Optional[list[str]] = None,
) -> Optional[JobRecord]:
    """Update a job record with partial updates."""
    with self._lock:
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for update")
            return None

        # Update simple fields
        if status is not None:
            job.status = status
        if stage is not None:
            if job.stage != stage:
                job.stage_started_at = datetime.now(timezone.utc)
            job.stage = stage
        if progress_percent is not None:
            job.progress_percent = progress_percent
        if title is not None:
            job.title = title
        if error is not None:
            job.error = error
        if config_json is not None:
            job.config_json = config_json

        # Full replacements
        if artifacts is not None:
            job.artifacts = artifacts
        if warnings is not None:
            job.warnings = warnings

        # MOVE THIS INSIDE LOCK (was after the lock)
        # Append warnings (merge operation)
        if warnings_append:
            job.warnings.extend(warnings_append)

        # Merge partial outputs
        if partial_outputs:
            for key, value in partial_outputs.items():
                if hasattr(job.outputs, key) and value is not None:
                    setattr(job.outputs, key, value)

        # Merge partial artifacts
        if partial_artifacts:
            for key, value in partial_artifacts.items():
                if hasattr(job.artifacts, key) and value is not None:
                    setattr(job.artifacts, key, value)

        logger.debug(f"Updated job {job_id} in memory")
        return job  # Lock automatically released here
```

**Testing**:
```bash
pytest -k "test_concurrent_warnings_append" -v
```

**Verification**:
- Run 10-20 concurrent threads appending warnings
- All warnings should be preserved
- No race condition window

---

### Issue #2: Verify Atomic RPC Migration Applied

**File**: New startup check required
**Location**: Add to `backend/app/main.py` startup event
**Severity**: CRITICAL - Unsafe fallback path in production

**Add Startup Verification**:
```python
# In backend/app/main.py

import logging
from backend.state.impl.supabase_store import _get_supabase_client

logger = logging.getLogger(__name__)

async def verify_migrations():
    """Verify required migrations are applied."""
    try:
        # Only check if using Supabase
        from backend.state.factory import get_job_store
        store = get_job_store()

        if store.__class__.__name__ != "SupabaseJobStore":
            logger.info("Using in-memory store, skipping migration check")
            return

        # Check if atomic_update_job RPC exists
        client = _get_supabase_client()
        try:
            # Call with all-None params (no-op)
            result = client.rpc("atomic_update_job", {
                "p_job_id": "00000000-0000-0000-0000-000000000000",
                "p_status": None,
                "p_stage": None,
                "p_progress_percent": None,
                "p_title": None,
                "p_error": None,
                "p_partial_outputs": None,
                "p_partial_artifacts": None,
                "p_warnings_append": None,
                "p_update_stage_timestamp": False,
            }).execute()
            logger.info("✓ Migration 014 (atomic_update_job) verified")
        except Exception as e:
            logger.critical("✗ MIGRATION REQUIRED: atomic_update_job RPC not found")
            logger.critical("  Migration 014 must be applied to Supabase before deployment")
            logger.critical(f"  Error: {e}")
            raise RuntimeError(
                "Database migration 014 (atomic_update_job RPC) is required for safe job updates. "
                "Run migrations before deploying."
            )
    except Exception as e:
        logger.warning(f"Could not verify migrations: {e}")
        # Don't fail startup, but log warning

@app.on_event("startup")
async def startup_event():
    """Run startup checks."""
    await verify_migrations()
    # ... other startup tasks ...
```

**Testing**:
```bash
# Start server and check logs
uvicorn backend.app.main:app --reload

# Should see:
# "✓ Migration 014 (atomic_update_job) verified"
# OR
# "✗ MIGRATION REQUIRED: atomic_update_job RPC not found"
```

**Verification**:
- Logs confirm RPC availability
- If missing, error is clear and actionable
- No silent failures in fallback path

---

### Issue #3: Fix SupabaseJobStore Connection Pool

**File**: `/backend/state/impl/supabase_store.py`
**Lines**: 114-124, 160-161, 205-206, 471-472, 577-578
**Severity**: CRITICAL - Resource exhaustion in production

**Problem**: HTTP client created but never explicitly closed, causing connection pool exhaustion

**Fix - Option A: Use Context Manager (Recommended)**

Add to `backend/state/impl/supabase_store.py`:

```python
from contextlib import contextmanager

class SupabaseJobStore(JobStore):
    """Supabase job store implementation with atomic JSONB operations."""

    def __init__(self) -> None:
        """Initialize the store with HTTP client for connection pooling."""
        self._http_client: Optional[httpx.Client] = None

    @contextmanager
    def _http_client_context(self):
        """Context manager for HTTP client usage."""
        client = self._get_http_client()
        try:
            yield client
        finally:
            # Don't close - keep connection alive for reuse
            pass

    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client with connection pooling."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(
                timeout=SUPABASE_API_TIMEOUT,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._http_client
```

**Fix - Option B: Explicit Lifecycle Management**

```python
# Add to class __init__:
def __init__(self) -> None:
    self._http_client: Optional[httpx.Client] = None
    atexit.register(self.close)  # Ensure cleanup on exit

# Keep existing code, but ensure each method has clean error handling
```

**Verify Connection Reuse**:
```python
def test_connection_reuse():
    """Verify HTTP connections are reused."""
    import time
    from backend.state.impl.supabase_store import SupabaseJobStore

    store = SupabaseJobStore()

    # Time first request
    start = time.perf_counter()
    store.list_jobs(limit=1)
    first_time = time.perf_counter() - start

    # Time second request (should reuse connection)
    start = time.perf_counter()
    store.list_jobs(limit=1)
    second_time = time.perf_counter() - start

    print(f"First request: {first_time*1000:.1f}ms")
    print(f"Second request: {second_time*1000:.1f}ms")

    # Second should be significantly faster (no new socket)
    assert second_time < first_time * 0.6, "Connection not reused"
```

---

### Issue #4: Fix Settings Store Connection Pooling

**File**: `/backend/state/settings_store.py`
**Lines**: 91, 136, 220, 270
**Severity**: CRITICAL - Performance degradation

**Problem**: Creates new httpx.Client for every operation (no connection pooling)

**Fix**:

```python
"""Settings store for user preferences."""
from typing import Any, Optional
import atexit

import httpx
from loguru import logger

from backend.config import get_settings
from backend.models.user_settings import UserSettings, UserSettingsUpdate, PipelineType, SortOrder, DriveFolder
from backend.utils.error_handling import sanitize_error_message


# Constants
SUPABASE_API_TIMEOUT = 5.0
_http_client: Optional[httpx.Client] = None


def _get_http_client() -> httpx.Client:
    """Get or create shared HTTP client with connection pooling."""
    global _http_client

    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(
            timeout=SUPABASE_API_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    return _http_client


def _close_http_client():
    """Close HTTP client on shutdown."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        _http_client.close()
        _http_client = None


# Register cleanup on exit
atexit.register(_close_http_client)


def _rest_base_url() -> str:
    """Base URL for Supabase PostgREST."""
    settings = get_settings()
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")
    base_url = str(settings.supabase_url)
    return base_url.rstrip("/") + "/rest/v1"


def _headers() -> dict[str, str]:
    """Headers required by Supabase REST."""
    settings = get_settings()
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


# ... rest of file ...

# REPLACE all instances of:
# with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
#     resp = client.get(...)

# WITH:
# client = _get_http_client()
# resp = client.get(...)

# Example:
def get_user_settings(user_id: str) -> Optional[UserSettings]:
    """Get user settings from database."""
    url = _rest_base_url() + "/user_settings"
    headers = _headers()
    params = {
        "user_id": f"eq.{user_id}",
        "limit": 1,
    }

    client = _get_http_client()  # CHANGED: Use shared client
    resp = client.get(url, headers=headers, params=params)

    if resp.status_code == 404:
        return None

    try:
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(
            "Failed to fetch settings for user %s: %s",
            user_id,
            sanitize_error_message(e),
        )
        raise

    data = resp.json()
    if not data:
        return None

    return _row_to_settings(data[0])
```

**Replace ALL instances of**:
```python
with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
    resp = client.get/post/patch(...)
```

**With**:
```python
client = _get_http_client()
resp = client.get/post/patch(...)
```

**Lines to update**:
- Line 91 (get_user_settings)
- Line 136 (create_default_settings)
- Line 220 (update_user_settings)
- Line 270 (check_username_available)

---

## HIGH PRIORITY FIXES (1-2 days)

### Issue #5: Standardize Artifacts/Outputs Conversion

**Files**:
- `/backend/state/impl/in_memory.py` - Add conversion
- `/backend/state/impl/supabase_store.py` - Already has conversion
- Create utility function

**Add Conversion Utility**:

```python
# In backend/state/impl/supabase_store.py, add:

def _jsonb_to_artifacts(data: Optional[dict]) -> Artifacts:
    """Convert JSONB dict to Artifacts object."""
    if not data:
        return Artifacts()
    return Artifacts(
        drive_folder_url=data.get("drive_folder_url"),
        doc_urls=data.get("doc_urls"),
    )


def _jsonb_to_outputs(data: Optional[dict]) -> Outputs:
    """Convert JSONB dict to Outputs object."""
    if not data:
        return Outputs()
    return Outputs(
        research_map_md=data.get("research_map_md"),
        source_shortlist_md=data.get("source_shortlist_md"),
        youtube_index_md=data.get("youtube_index_md"),
        quote_bank_md=data.get("quote_bank_md"),
        claims_ledger_md=data.get("claims_ledger_md"),
        evidence_table_md=data.get("evidence_table_md"),
        missing_angles_md=data.get("missing_angles_md"),
        timeline_md=data.get("timeline_md"),
        entities_md=data.get("entities_md"),
        reddit_discussions_md=data.get("reddit_discussions_md"),
    )
```

**Update InMemoryJobStore.update_job()**:

```python
# At the end of update_job, before return:
# Convert artifacts/outputs to model objects if they're dicts
if isinstance(job.artifacts, dict):
    job.artifacts = _jsonb_to_artifacts(job.artifacts)
if isinstance(job.outputs, dict):
    job.outputs = _jsonb_to_outputs(job.outputs)

return job
```

**Testing**:
```bash
pytest -k "test_artifacts_type_consistency or test_outputs_type_consistency" -v
```

---

### Issue #6: Add Pipeline Enum to JobRecord

**File**: `/backend/models/job_record.py`

**Change from**:
```python
pipeline: str = Field(default="investigation", description="Pipeline mode")
```

**Change to**:
```python
from enum import Enum

class PipelineMode(str, Enum):
    """Research pipeline modes."""
    QUICK = "quick"
    FULL = "full"
    BREAKING_NEWS = "breaking_news"
    INVESTIGATION = "investigation"
    PROFILE = "profile"
    CONTROVERSY = "controversy"

# In JobRecord class:
pipeline: PipelineMode = Field(default=PipelineMode.INVESTIGATION, description="Pipeline mode")
```

**Update serialization**:
```python
# If needed for JSON responses, add:
class Config:
    use_enum_values = True  # Serialize enum as string value
```

---

### Issue #7: Add Pipeline Validation to CreateJobRequest

**File**: `/backend/models/job.py` - Already uses Literal, good!

No changes needed - already validates correctly:
```python
pipeline: Literal["quick", "full", "breaking_news", "investigation", "profile", "controversy"]
```

---

## MEDIUM PRIORITY FIXES (1-2 weeks)

### Issue #8: Fix Settings Migration Data Conversion

**File**: `/backend/migrations/009_settings_username_folders.sql`
**Lines**: 17-29

**Current Condition**:
```sql
WHERE drive_folder_id IS NOT NULL
  AND drive_folder_id != ''
  AND (drive_folders IS NULL OR drive_folders = '[]'::jsonb)
```

**Improved Version**:
```sql
-- Only migrate if user has legacy drive_folder_id but no multi-folder setup
WHERE drive_folder_id IS NOT NULL
  AND drive_folder_id != ''
  AND (drive_folders IS NULL OR drive_folders = '[]'::jsonb OR jsonb_array_length(drive_folders) = 0)
```

**OR Add a Manual Migration Script**:
```sql
-- Check migration status
SELECT user_id, drive_folder_id, drive_folders
FROM user_settings
WHERE drive_folder_id IS NOT NULL
  AND (drive_folders IS NULL OR drive_folders = '[]'::jsonb);

-- If any rows exist, manually fix them:
UPDATE user_settings
SET drive_folders = jsonb_build_array(
    jsonb_build_object(
        'folder_id', drive_folder_id,
        'folder_name', NULL,
        'is_default', true,
        'added_at', NOW()
    )
),
default_folder_id = drive_folder_id
WHERE drive_folder_id IS NOT NULL
  AND (drive_folders IS NULL OR drive_folders = '[]'::jsonb);
```

---

### Issue #9: Improve Cache Error Logging

**File**: `/backend/utils/cache.py`
**Lines**: 62-68

**Current Code**:
```python
def cache_get(key: str) -> Optional[Any]:
    client = _get_redis_client()
    if not client:
        return None

    try:
        value = client.get(key)
        if value:
            return json.loads(value)  # Silent JSON error
        return None
    except Exception as e:
        logger.debug(f"Cache get failed for key {key}: {e}")
        return None
```

**Improved**:
```python
def cache_get(key: str) -> Optional[Any]:
    client = _get_redis_client()
    if not client:
        return None

    try:
        value = client.get(key)
        if not value:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError as je:
            logger.warning(f"Corrupted cache value for {key}, deleting: {je}")
            client.delete(key)
            return None
    except Exception as e:
        logger.debug(f"Cache operation failed for key {key}: {e}")
        return None
```

---

### Issue #10: Remove Duplicate Index from Migration

**File**: `/backend/migrations/015_performance_improvements.sql`
**Lines**: 39-40

**Current**:
```sql
CREATE INDEX IF NOT EXISTS idx_jobs_status
ON jobs (status);
```

**Reason**: Already created in `012_add_error_column.sql:8`

**Fix**: Delete these lines from migration 015

---

## VERIFICATION CHECKLIST

After applying fixes:

- [ ] InMemoryJobStore race condition fixed
  - [ ] Warnings append inside lock
  - [ ] Test concurrent warnings append - PASS

- [ ] Atomic RPC verification added
  - [ ] Startup check logs result
  - [ ] Fails fast if migration 014 missing

- [ ] Connection pool management
  - [ ] SupabaseJobStore client reused
  - [ ] SettingsStore client reused
  - [ ] Test connection reuse - PASS

- [ ] Type conversion consistency
  - [ ] Artifacts converts JSONB->Artifacts
  - [ ] Outputs converts JSONB->Outputs
  - [ ] Test type consistency - PASS

- [ ] Pipeline enum added
  - [ ] JobRecord uses PipelineMode enum
  - [ ] Test enum validation - PASS

- [ ] Settings migration verified
  - [ ] No orphaned drive_folder_id rows
  - [ ] drive_folders populated correctly

- [ ] Cache improved
  - [ ] Corrupted JSON logged and deleted
  - [ ] No silent failures

- [ ] Duplicate index removed
  - [ ] Migration 015 cleaned

- [ ] All tests pass
  - [ ] Run: `pytest backend/tests/test_state.py -v`
  - [ ] Run: `pytest backend/tests/test_database_qa.py -v`
  - [ ] Coverage: 80%+

---

## Rollout Plan

### Phase 1: Critical Fixes (Before Next Deployment)
1. Fix InMemoryJobStore race condition
2. Add atomic RPC verification
3. Fix connection pooling (both stores)
4. Test thoroughly with concurrent access

### Phase 2: Type Safety (1-2 days)
5. Add type conversion consistency
6. Add pipeline enum validation

### Phase 3: Cleanup (1-2 weeks)
7. Fix settings migration edge cases
8. Remove duplicate index
9. Improve cache error logging

### Phase 4: Validation (Continuous)
10. Run comprehensive test suite
11. Monitor production metrics
12. Add regression tests

---

## Testing Commands

```bash
# Activate environment
source .venv/bin/activate

# Run state tests
pytest backend/tests/test_state.py -v

# Run comprehensive DB tests (once created)
pytest backend/tests/test_database_qa.py -v

# Run with coverage
pytest backend/tests/test_state.py --cov=backend.state --cov-report=html

# Check for race conditions (run multiple times)
for i in {1..10}; do pytest -k "concurrent" -v; done

# Performance testing
pytest backend/tests/test_database_qa.py::TestConnectionPerformance -v -s
```

---

## Success Criteria

✓ All critical race conditions resolved
✓ Type consistency between stores
✓ Connection pooling reduces latency by 50%+
✓ 16/16 new tests passing
✓ Zero lost job updates in production
✓ Clear error messages for missing migrations
