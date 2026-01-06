# Celery Worker Audit: `run_gemini_video_job`

**Scope:** Full Research Assistant Pipeline (Phase 3)
**Files Reviewed:**
- `backend/worker.py` (789 lines)
- `backend/integrations/gemini_client.py` (1230 lines)
- `backend/pipeline/dual_output.py` (1205 lines)
- `backend/state/impl/supabase_store.py`
- `backend/models/job_record.py`

**Focus:** Task timeout, progress callbacks, error handling, artifact storage, memory leaks, race conditions, Celery task_id alignment

---

## Executive Summary

**Overall Assessment:** GOOD with 2 CRITICAL and 3 MEDIUM issues

Task appropriately structured for long-running video analysis with proper error handling, atomic DB updates, and task_id alignment. Main concerns: race condition in progress callback, missing timeout exception handling, and potential memory accumulation in large batches.

**Task Timeout Configuration:**
- ✅ Hard limit: 1800s (30 min) - appropriate for long videos
- ✅ Soft limit: 1500s (25 min) - allows 5 min cleanup window
- ✅ Configured globally (line 47-48) AND per-task (line 591-592)

**Celery Task ID Alignment:**
- ✅ `task_id=job.job_id` used in `apply_async` (line 261)
- ✅ Enables reliable cancellation via `celery_app.control.revoke(job_id)`
- ✅ Consistent pattern across all workers

---

## Critical Issues

### CRITICAL-1: Race Condition in `progress_callback` (Lines 645-668)

**Severity:** CRITICAL
**Impact:** Overwrites concurrent `config_json` updates from other stages/tasks

**Problem:**
```python
def progress_callback(pass_num: int, total_passes: int, status: str, detail: str):
    update_job(
        job_id,
        stage=stage_names.get(pass_num, f"pass_{pass_num}"),
        progress_percent=progress,
        config_json={
            **job.config_json,  # ❌ Reads stale job object
            "current_pass": pass_num,
            "total_passes": total_passes,
            "pass_status": status,
            "pass_detail": detail,
        },
    )
```

**Issue:** `job.config_json` captured in closure at line 619, never refreshed during 4-pass pipeline (potentially 30 min execution). If another worker or API endpoint updates `config_json` concurrently, those changes are silently overwritten.

**Example Race:**
1. Pass 1 starts → `job.config_json = {"model": "flash", "video_urls": [...]}`
2. User cancels via API → updates `config_json["cancelled_by_user"] = True`
3. Pass 2 callback runs → spreads `**job.config_json` (stale copy without `cancelled_by_user`)
4. Cancellation flag lost

**Fix:**
```python
# Option 1: Use partial_config_json (atomic merge)
update_job(
    job_id,
    stage=stage_names.get(pass_num, f"pass_{pass_num}"),
    progress_percent=progress,
    partial_config_json={  # ✅ Atomic merge via RPC
        "current_pass": pass_num,
        "total_passes": total_passes,
        "pass_status": status,
        "pass_detail": detail,
    },
)

# Option 2: Refresh job before each callback
def progress_callback(pass_num: int, total_passes: int, status: str, detail: str):
    current_job = get_job(job_id)  # ✅ Fresh read
    if not current_job:
        return
    update_job(
        job_id,
        stage=...,
        progress_percent=...,
        config_json={
            **current_job.config_json,  # ✅ Current state
            ...
        },
    )
```

**NOTE:** `update_job` in `backend/state/__init__.py` doesn't expose `partial_config_json` parameter. Needs interface update:
```python
def update_job(
    job_id: str,
    *,
    ...
    partial_config_json: dict | None = None,  # ADD THIS
) -> JobRecord | None:
```

---

### CRITICAL-2: Missing Timeout Exception Handling (Lines 671-789)

**Severity:** CRITICAL
**Impact:** Task killed mid-pass without cleanup, job stuck in running state

**Problem:**
```python
try:
    client = GeminiClient()
    result = client.run_full_analysis_pipeline(...)  # Can run 30 min
    # ... artifact processing ...
except Exception as e:  # ❌ Doesn't catch SoftTimeLimitExceeded
    logger.exception(f"[{job_id}] Full pipeline failed: {e}")
    update_job(job_id, status="failed", stage="error", warnings=[...])
```

**Issue:** Celery raises `SoftTimeLimitExceeded` at 1500s, which is NOT caught by generic `Exception` in some Celery versions (it's a `BaseException` subclass in Celery 4.x). Task terminates without setting `status="failed"`.

**Evidence:** No `SoftTimeLimitExceeded` imports found in codebase (grep returned 0 results).

**Fix:**
```python
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded

try:
    client = GeminiClient()
    result = client.run_full_analysis_pipeline(...)
    # ... processing ...
except (SoftTimeLimitExceeded, TimeLimitExceeded) as e:
    logger.warning(f"[{job_id}] Task timeout after {e}: partial results may exist")
    update_job(
        job_id,
        status="failed",
        stage="timeout",
        warnings=[f"Task exceeded {1500}s timeout - results incomplete"],
    )
    return {"job_id": job_id, "status": "timeout", "error": "Task timeout"}
except Exception as e:
    # ... existing error handling ...
```

---

## High Priority Issues

None identified. Error handling structure is solid.

---

## Medium Priority Issues

### MEDIUM-1: Potential Memory Leak in Large Video Batches (Lines 673-742)

**Severity:** MEDIUM
**Impact:** Memory accumulation during 4-pass pipeline on 10+ videos

**Problem:**
- `run_full_analysis_pipeline` returns large `result` dict with:
  - `clips` (list of dicts)
  - `quotes` (list of dicts)
  - `content_blueprints` (list of dataclasses)
  - `gap_analysis` (dataclass)
  - `research_starter` (dataclass)
- Dataclasses converted to dicts (lines 722-730) but originals not explicitly deleted
- No explicit garbage collection after large object processing

**Evidence:** `backend/pipeline/extraction.py` uses explicit `gc.collect()` after processing transcripts, but `worker.py` doesn't.

**Likelihood:** LOW-MEDIUM (Python's GC usually handles this, but long-running tasks benefit from explicit collection)

**Fix:**
```python
import gc

# After line 742 (after artifacts created):
# Clean up large intermediate objects
del result  # Large dict with all pass results
if 'content_blueprints_dicts' in locals():
    del content_blueprints_dicts
if 'gap_analysis_dict' in locals():
    del gap_analysis_dict
if 'research_starter_dict' in locals():
    del research_starter_dict

gc.collect()  # Force collection before final update_job

update_job(
    job_id,
    status="completed",
    ...
)
```

---

### MEDIUM-2: Dataclass to Dict Conversion Redundancy (Lines 722-730)

**Severity:** MEDIUM
**Impact:** Code duplication, inconsistent serialization if dataclass changes

**Problem:**
```python
content_blueprints_dicts = [
    bp.to_dict() for bp in result.get("content_blueprints", [])
]
gap_analysis_dict = result.get("gap_analysis")
if gap_analysis_dict:
    gap_analysis_dict = gap_analysis_dict.to_dict()  # ❌ Inline conversion
research_starter_dict = result.get("research_starter")
if research_starter_dict:
    research_starter_dict = research_starter_dict.to_dict()
```

**Issue:** Inconsistent pattern - list comprehension vs conditional checks. If dataclass doesn't have `to_dict()`, AttributeError only at runtime.

**Better Pattern:**
```python
# Helper function for safe dataclass serialization
def safe_to_dict(obj: Any) -> Optional[dict]:
    """Convert dataclass to dict if it has to_dict method."""
    return obj.to_dict() if obj and hasattr(obj, 'to_dict') else None

content_blueprints_dicts = [
    safe_to_dict(bp) for bp in result.get("content_blueprints", [])
]
gap_analysis_dict = safe_to_dict(result.get("gap_analysis"))
research_starter_dict = safe_to_dict(result.get("research_starter"))
```

---

### MEDIUM-3: Incomplete Artifact Validation Before Storage (Lines 733-742)

**Severity:** MEDIUM
**Impact:** Corrupted artifacts stored in DB if dataclass serialization fails

**Problem:**
```python
artifacts = Artifacts(
    clips=result.get("clips", []),  # ❌ No validation of structure
    quotes=result.get("quotes", []),
    producer_packet=producer_packet.to_dict(),  # ❌ Assumes to_dict() succeeds
    quality_gate_passed=passes_gate,
    content_blueprints=content_blueprints_dicts,  # ❌ May contain None values
    gap_analysis=gap_analysis_dict,
    research_starter=research_starter_dict,
)
```

**Issue:** If `to_dict()` raises exception or returns malformed data, it's silently stored. No schema validation before DB write.

**Fix:**
```python
# Validate artifacts before storage
try:
    artifacts = Artifacts(
        clips=result.get("clips", []),
        quotes=result.get("quotes", []),
        producer_packet=producer_packet.to_dict(),
        quality_gate_passed=passes_gate,
        content_blueprints=[d for d in content_blueprints_dicts if d],  # ✅ Filter None
        gap_analysis=gap_analysis_dict,
        research_starter=research_starter_dict,
    )
    # Validate Pydantic model
    artifacts.model_validate(artifacts.model_dump())
except (ValidationError, AttributeError) as e:
    logger.error(f"[{job_id}] Artifact validation failed: {e}")
    # Store partial results with warning
    artifacts = Artifacts(
        clips=result.get("clips", []),
        quotes=result.get("quotes", []),
    )
    warnings.append(f"Partial artifacts stored: {str(e)}")
```

---

## Low Priority Issues

### LOW-1: Inconsistent Error Message Formatting (Lines 686, 788)

**Severity:** LOW
**Impact:** Inconsistent logging/debugging experience

```python
# Line 686
warnings=[result.get("error", "Pipeline failed")]

# Line 788
warnings=[f"Pipeline failed: {str(e)}"]
```

One uses f-string, other doesn't. Standardize to f-strings for consistency.

---

### LOW-2: Magic Numbers in Progress Calculation (Line 647)

**Severity:** LOW
**Impact:** Maintenance - if progress ranges change, hard to update

```python
base_progress = 5 + ((pass_num - 1) / total_passes) * 90
```

Extract to constants:
```python
PROGRESS_START = 5
PROGRESS_RANGE = 90  # 5-95%
base_progress = PROGRESS_START + ((pass_num - 1) / total_passes) * PROGRESS_RANGE
```

---

## Positive Observations

✅ **Excellent Error Handling Structure:**
- Per-video error isolation in `analyze_youtube_videos_batch` (gemini_client.py:677-708)
- Graceful degradation when individual videos fail
- Warnings aggregated separately from critical errors

✅ **Atomic DB Updates:**
- Uses `update_job` with `partial_outputs` and `partial_artifacts` (via Supabase RPC)
- Prevents race conditions in artifact storage

✅ **Task ID Alignment:**
- `apply_async(..., task_id=job.job_id)` enables reliable cancellation
- Consistent pattern across all 3 workers (research, transcript, gemini)

✅ **Proper Quality Gate:**
- `passes_quality_gate()` checks thresholds before storage
- Failures logged as warnings, not blocking

✅ **Progress Granularity:**
- 4 distinct stages with clear names (`pass_1_extraction`, etc.)
- Frontend can display meaningful progress

✅ **Dataclass Serialization:**
- All Phase 3 dataclasses implement `to_dict()` (verified in dual_output.py)
- Consistent pattern across ContentBlueprint, GapAnalysis, ResearchStarter

✅ **Cost Tracking:**
- Total cost aggregated from pipeline (line 755)
- Logged in completion message (line 764)

---

## Recommended Actions (Priority Order)

1. **[CRITICAL]** Add `SoftTimeLimitExceeded` exception handler with graceful timeout handling
2. **[CRITICAL]** Fix race condition in `progress_callback` - either:
   - Add `partial_config_json` to `update_job` interface + use atomic merge, OR
   - Refresh job object before each callback
3. **[MEDIUM]** Add explicit `gc.collect()` after large object processing (follow extraction.py pattern)
4. **[MEDIUM]** Implement artifact validation before storage with fallback to partial results
5. **[MEDIUM]** Extract `safe_to_dict()` helper for consistent dataclass serialization
6. **[LOW]** Standardize error message formatting (f-strings)
7. **[LOW]** Extract progress calculation constants

---

## Test Coverage Gap

**Missing:** No tests found for:
- `run_gemini_video_job` task
- Timeout exception handling
- Progress callback concurrency
- Dataclass serialization edge cases

**Recommended Tests:**
```python
# tests/test_gemini_worker.py
def test_gemini_video_job_timeout_handling():
    """Test soft timeout doesn't leave job in running state."""

def test_progress_callback_concurrent_updates():
    """Test progress callback doesn't overwrite concurrent config_json changes."""

def test_dataclass_serialization_failure():
    """Test malformed dataclass doesn't crash artifact storage."""

def test_large_batch_memory_cleanup():
    """Test memory is released after processing 50+ videos."""
```

---

## Metrics

- **Type Coverage:** Not applicable (Python)
- **Linting Issues:** Cannot run (pytest requires activated venv)
- **Code Complexity:** MEDIUM (4-pass pipeline with nested callbacks)
- **Dependencies:** google-genai, celery, supabase (all lazy-loaded ✅)

---

## Unresolved Questions

1. Does Supabase `update_job` RPC support `partial_config_json` atomic merge?
   - If NO → must implement in `backend/state/impl/supabase_store.py`
   - If YES → just add parameter to interface

2. What is max expected video count per job?
   - If >50 videos → memory cleanup is HIGH priority
   - If <10 videos → current implementation likely sufficient

3. Is there a retry mechanism for transient Gemini API failures?
   - Not visible in worker.py → may be in gemini_client.py rate limiter

4. Should timeout jobs be retryable?
   - Current implementation marks as failed/timeout
   - Consider adding `retry_count` to job record for user-initiated retries
