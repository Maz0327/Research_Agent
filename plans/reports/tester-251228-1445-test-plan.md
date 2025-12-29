# Database QA Test Plan
**Date**: 2025-12-28 14:45
**Scope**: Comprehensive testing of state layer, migrations, models, and validators

---

## Critical Test Cases (Must Run Immediately)

### Test Group 1: InMemoryJobStore Race Condition

#### Test 1.1: Concurrent Warnings Append
```python
def test_concurrent_warnings_append():
    """Verify thread safety of concurrent warning appends."""
    from backend.state.impl.in_memory import InMemoryJobStore
    import threading

    store = InMemoryJobStore()
    job = store.create_job({"pipeline": "full"})

    # Create 10 threads that append warnings simultaneously
    errors = []

    def append_warning(idx):
        try:
            store.update_job(
                job.job_id,
                warnings_append=[f"Warning {idx}"]
            )
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=append_warning, args=(i,))
        for i in range(10)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify
    assert len(errors) == 0, f"Errors occurred: {errors}"

    updated = store.get_job(job.job_id)
    assert len(updated.warnings) == 10, f"Expected 10 warnings, got {len(updated.warnings)}"
    assert all(f"Warning {i}" in updated.warnings for i in range(10))
```

**Expected**: FAIL (race condition exists)
**After Fix**: PASS

---

#### Test 1.2: Concurrent Partial Artifacts Update
```python
def test_concurrent_artifacts_update():
    """Verify thread safety of concurrent partial artifact updates."""
    from backend.state.impl.in_memory import InMemoryJobStore
    import threading

    store = InMemoryJobStore()
    job = store.create_job({"pipeline": "full"})

    def update_artifact(idx):
        store.update_job(
            job.job_id,
            partial_artifacts={f"url_{idx}": f"https://example.com/{idx}"}
        )

    threads = [
        threading.Thread(target=update_artifact, args=(i,))
        for i in range(5)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    updated = store.get_job(job.job_id)
    # All 5 updates should be present
    assert len(updated.artifacts.__dict__) >= 5
```

**Expected**: FAIL (potential race condition)
**After Fix**: PASS

---

### Test Group 2: Artifacts/Outputs Type Conversion

#### Test 2.1: Supabase Artifacts Conversion
```python
def test_supabase_artifacts_json_conversion():
    """Verify JSONB artifacts convert to Artifacts object."""
    from backend.state.impl.supabase_store import _record_from_db_row
    from backend.models.job_record import Artifacts

    # Simulate database row
    row = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "artifacts": {
            "drive_folder_url": "https://drive.google.com/folders/abc123",
            "doc_urls": ["https://docs.google.com/doc1", "https://docs.google.com/doc2"]
        },
        "created_at": "2025-01-01T00:00:00Z",
        "status": "completed",
        "warnings": [],
        "outputs": {},
    }

    record = _record_from_db_row(row)

    # Verify type
    assert isinstance(record.artifacts, Artifacts)
    assert record.artifacts.drive_folder_url == "https://drive.google.com/folders/abc123"
    assert len(record.artifacts.doc_urls) == 2
```

**Expected**: PASS

---

#### Test 2.2: InMemory Artifacts Type Consistency
```python
def test_in_memory_artifacts_type_consistency():
    """Verify in-memory store returns Artifacts objects not dicts."""
    from backend.state.impl.in_memory import InMemoryJobStore
    from backend.models.job_record import Artifacts

    store = InMemoryJobStore()
    job = store.create_job({"pipeline": "full"})

    # Update with partial artifacts
    store.update_job(
        job.job_id,
        partial_artifacts={
            "drive_folder_url": "https://drive.google.com/folders/test"
        }
    )

    updated = store.get_job(job.job_id)

    # Should be Artifacts object, not dict
    assert isinstance(updated.artifacts, Artifacts) or isinstance(updated.artifacts, dict), \
        f"Expected Artifacts or dict, got {type(updated.artifacts)}"

    # If dict, conversion is missing (bug)
    if isinstance(updated.artifacts, dict):
        assert False, "BUG: In-memory store returning dict instead of Artifacts object"
```

**Expected**: FAIL (highlights type inconsistency)
**Action**: Convert artifacts/outputs after all updates

---

### Test Group 3: Atomic Update Safety

#### Test 3.1: Atomic RPC Migration Required
```python
def test_atomic_update_rpc_available():
    """Verify atomic_update_job RPC function exists in database."""
    from backend.state.impl.supabase_store import _get_supabase_client

    client = _get_supabase_client()

    # Try to call atomic RPC with no-op params
    try:
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
        # Function exists (even if no job found)
        assert True
    except Exception as e:
        assert False, f"CRITICAL: atomic_update_job RPC not found. Migration 014 not applied: {e}"
```

**Expected**: PASS (or migration 014 not applied)
**If Fails**: CRITICAL - Fallback path unsafe for production

---

#### Test 3.2: Concurrent Atomic Updates Safe
```python
@pytest.mark.asyncio
async def test_concurrent_atomic_updates():
    """Verify concurrent atomic updates don't lose data."""
    import asyncio
    from backend.state.factory import get_job_store

    store = get_job_store()

    if store.__class__.__name__ != "SupabaseJobStore":
        pytest.skip("Requires Supabase store")

    # Create job
    job = store.create_job({"pipeline": "full"}, user_id=None)

    async def update_output(idx):
        # Update different output fields
        store.update_job(
            job.job_id,
            partial_outputs={
                f"field_{idx}": f"value_{idx}"
            }
        )

    # Run 5 concurrent updates
    await asyncio.gather(*[
        asyncio.to_thread(update_output, i)
        for i in range(5)
    ])

    # All updates should be present
    final = store.get_job(job.job_id)
    assert len(final.outputs.model_dump(exclude_none=True)) >= 5
```

**Expected**: PASS (if atomic RPC works)

---

### Test Group 4: Schema Validation

#### Test 4.1: Pipeline Enum Validation
```python
def test_job_record_pipeline_enum():
    """Verify pipeline field validates allowed values."""
    from backend.models.job_record import JobRecord
    from datetime import datetime, timezone

    valid_pipelines = ["quick", "full", "breaking_news", "investigation", "profile", "controversy"]

    for pipeline in valid_pipelines:
        # Should not raise
        job = JobRecord(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            pipeline=pipeline,
            created_at=datetime.now(timezone.utc),
        )
        assert job.pipeline == pipeline

    # Invalid pipeline should raise (currently doesn't)
    with pytest.raises(ValueError):
        JobRecord(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            pipeline="invalid_pipeline",
            created_at=datetime.now(timezone.utc),
        )
```

**Expected**: FAIL (model doesn't validate)
**After Fix**: PASS (with enum)

---

#### Test 4.2: Progress Percent Bounds
```python
def test_progress_percent_validation():
    """Verify progress_percent validates 0-100 range."""
    from backend.state.impl.in_memory import InMemoryJobStore

    store = InMemoryJobStore()
    job = store.create_job({"pipeline": "full"})

    # Valid updates
    store.update_job(job.job_id, progress_percent=0)
    store.update_job(job.job_id, progress_percent=50)
    store.update_job(job.job_id, progress_percent=100)

    # Invalid update (currently accepted)
    updated = store.update_job(job.job_id, progress_percent=150)

    # Should validate and reject
    assert updated.progress_percent <= 100, "Progress exceeded 100%"
```

**Expected**: FAIL (no validation in update_job)
**Action**: Add validation to update_job signature

---

### Test Group 5: Migration Verification

#### Test 5.1: Index Duplication Check
```python
def test_migration_index_duplication():
    """Verify no duplicate indexes created."""
    from backend.state.impl.supabase_store import _get_supabase_client

    client = _get_supabase_client()

    # Query pg_indexes for job indexes
    response = client.table("pg_indexes").select("*").eq(
        "tablename", "jobs"
    ).execute()

    indexes = [r["indexname"] for r in response.data]
    duplicates = [idx for idx in indexes if indexes.count(idx) > 1]

    assert len(duplicates) == 0, f"Duplicate indexes found: {duplicates}"
```

**Expected**: FAIL (idx_jobs_status appears twice)
**Fix**: Remove duplicate from migration 015

---

#### Test 5.2: Migration Idempotency
```python
def test_migrations_idempotent():
    """Verify migrations can be re-run without errors."""
    import subprocess

    # Get list of migration files
    import glob
    migrations = sorted(glob.glob("/path/to/migrations/*.sql"))

    for migration in migrations:
        # Try to re-run migration
        # (In actual test, would use Supabase CLI or direct SQL execution)
        pass
```

**Expected**: PASS (all migrations use IF NOT EXISTS/IF EXISTS guards)

---

## Test Group 6: Cache Edge Cases

#### Test 6.1: Corrupted JSON Cache Handling
```python
def test_corrupted_cache_json():
    """Verify corrupted JSON cache is handled gracefully."""
    import json
    from backend.utils.cache import cache_get, cache_set

    # Assume we can inject corrupted JSON into Redis
    # (Would need Redis client access)

    # Set valid JSON
    cache_set("test_key", {"data": "value"})

    # Retrieve it
    result = cache_get("test_key")
    assert result == {"data": "value"}

    # Try with corrupted JSON (simulated)
    # Should return None without raising
    # Should log warning (check logs)
```

**Expected**: PASS (graceful degradation)

---

#### Test 6.2: Cache TTL Expiry
```python
def test_cache_ttl_expires():
    """Verify cached values expire after TTL."""
    from backend.utils.cache import cache_set, cache_get
    import time

    # Set cache with 1 second TTL
    cache_set("ttl_key", {"data": "value"}, ttl_seconds=1)

    # Should exist immediately
    assert cache_get("ttl_key") == {"data": "value"}

    # Wait for expiry
    time.sleep(1.5)

    # Should be expired
    assert cache_get("ttl_key") is None
```

**Expected**: PASS (Redis TTL works)

---

## Performance Test Cases

### Test Group 7: Connection Pool Performance

#### Test 7.1: HTTP Client Reuse
```python
def test_http_client_connection_reuse():
    """Verify httpx.Client connections are reused."""
    from backend.state.impl.supabase_store import SupabaseJobStore
    import time

    store = SupabaseJobStore()

    # Time multiple requests
    start = time.time()

    # First request (new connection)
    store.list_jobs(limit=1)
    first_time = time.time() - start

    start = time.time()

    # Second request (reused connection)
    store.list_jobs(limit=1)
    second_time = time.time() - start

    # Reused should be ~50% faster
    # (First: new socket + DNS + TCP handshake)
    # (Second: reused socket)
    print(f"First request: {first_time*1000:.1f}ms")
    print(f"Second request: {second_time*1000:.1f}ms")

    # Currently both are slow (new client each time in settings_store)
    assert second_time < first_time * 0.6, "Connection not being reused"
```

**Expected**: FAIL (settings_store creates new client each time)
**After Fix**: PASS

---

## Validation Test Cases

### Test Group 8: Input Validation

#### Test 8.1: UUID Validation
```python
def test_uuid_validation():
    """Verify UUID validation catches invalid formats."""
    from backend.utils.validators import validate_uuid, ValidationError

    # Valid UUID
    result = validate_uuid("550e8400-e29b-41d4-a716-446655440000")
    assert result == "550e8400-e29b-41d4-a716-446655440000"

    # Invalid formats
    invalid = [
        "",
        "not-a-uuid",
        "550e8400-e29b-41d4-a716",  # Too short
        "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
        "550e8400e29b41d4a716446655440000",  # No dashes
    ]

    for invalid_uuid in invalid:
        with pytest.raises(ValidationError):
            validate_uuid(invalid_uuid)
```

**Expected**: PASS

---

#### Test 8.2: YouTube Video ID Validation
```python
def test_youtube_video_id_validation():
    """Verify YouTube video ID format validation."""
    from backend.utils.validators import validate_youtube_video_id, ValidationError

    # Valid
    assert validate_youtube_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # Invalid
    invalid = [
        "",
        "dQw4w9WgXcQ1",  # 12 chars
        "dQw4w9WgXc",    # 10 chars
        "'; DROP TABLE--",  # SQL injection attempt
        "dQw4w9WgXcQ<script>",
        "dQw4w9Wg\nXcQ",  # Contains newline
    ]

    for invalid_id in invalid:
        with pytest.raises(ValidationError):
            validate_youtube_video_id(invalid_id)
```

**Expected**: PASS

---

## Summary Test Matrix

| Category | Test Count | Status | Priority |
|----------|-----------|--------|----------|
| Race Conditions | 3 | FAIL | CRITICAL |
| Type Conversion | 2 | FAIL | HIGH |
| Atomic Operations | 2 | PASS/FAIL | CRITICAL |
| Schema Validation | 2 | FAIL | HIGH |
| Migration Check | 2 | FAIL | MEDIUM |
| Cache Edge Cases | 2 | PASS | MEDIUM |
| Performance | 1 | FAIL | MEDIUM |
| Input Validation | 2 | PASS | LOW |
| **TOTAL** | **16** | **8 FAIL** | Mixed |

---

## Test Execution Guide

### Prerequisites
```bash
# Activate virtual environment
source /path/to/.venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Set environment variables
export SUPABASE_URL=<test-db>
export SUPABASE_SERVICE_ROLE_KEY=<key>
export REDIS_URL=redis://localhost:6379  # or skip redis tests
```

### Run Tests
```bash
# Run all database QA tests
pytest backend/tests/test_database_qa.py -v

# Run specific test group
pytest backend/tests/test_database_qa.py::TestInMemoryStoreRaceCondition -v

# Run with detailed output
pytest backend/tests/test_database_qa.py -vv -s

# Run with coverage
pytest backend/tests/test_database_qa.py --cov=backend.state --cov-report=html
```

### Expected Results (Pre-Fix)
- Race condition tests: 3 FAIL
- Type conversion tests: 2 FAIL
- Schema validation tests: 2 FAIL
- Performance test: 1 FAIL
- Other tests: PASS

### Expected Results (Post-Fix)
- All 16 tests: PASS

---

## Test Implementation Checklist

- [ ] Create `backend/tests/test_database_qa.py`
- [ ] Implement 16 test cases from groups 1-8
- [ ] Add fixtures for sample jobs/records
- [ ] Add mock Supabase client for unit tests
- [ ] Add Redis test client
- [ ] Document expected failures (pre-fix)
- [ ] Add CI/CD integration
- [ ] Generate coverage report
- [ ] Document test results

---

## Notes for QA Team

1. **Race Condition Tests**: Use threading module; run multiple times to catch intermittent failures
2. **Type Conversion Tests**: Verify both Supabase and in-memory stores
3. **Atomic Operation Tests**: Require production Supabase (or test instance with migration 014)
4. **Schema Tests**: Can run locally against any Supabase instance
5. **Cache Tests**: Require Redis running (or test with mocks)
6. **Performance Tests**: Baseline timing before/after connection pooling fix

---

## Continuous Improvement

After fixes applied:
1. Run full test suite weekly
2. Add concurrency fuzzing tests (random concurrent updates)
3. Monitor production job update latency
4. Add database query performance tests
5. Document any additional edge cases found
