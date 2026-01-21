# API Data Serialization Audit: Clips/Quotes Missing in Frontend

**Investigation ID:** debugger-260106-2236-clips-quotes-missing
**Date:** 2026-01-06
**Status:** Root cause identified

## Executive Summary

Job completed with 58 clips, 37 quotes but frontend cannot display them. Root cause: `_record_from_db_row()` in `supabase_store.py` only reconstructs legacy fields, dropping all video analysis fields including `clips`, `quotes`, `producer_packet`.

**Impact:** All video analysis jobs return empty artifacts to frontend despite successful extraction.

**Priority:** Critical - blocks primary product feature (video analysis mode).

## Root Cause

### Location
`backend/state/impl/supabase_store.py:107-148` - `_record_from_db_row()` function

### The Problem

When retrieving jobs from Supabase, `_record_from_db_row()` constructs the Artifacts object with **only 2 fields**:

```python
artifacts = Artifacts(
    drive_folder_url=artifacts_data.get("drive_folder_url"),
    doc_urls=artifacts_data.get("doc_urls"),
)
```

But the Artifacts model defines **11 fields** (lines 8-32 in `job_record.py`):
- `drive_folder_url` ✅ (reconstructed)
- `doc_urls` ✅ (reconstructed)
- `clips` ❌ **DROPPED**
- `quotes` ❌ **DROPPED**
- `producer_packet` ❌ **DROPPED**
- `quality_gate_passed` ❌ **DROPPED**
- `content_blueprints` ❌ **DROPPED**
- `gap_analysis` ❌ **DROPPED**
- `research_starter` ❌ **DROPPED**

### Data Flow Trace

1. **Worker saves correctly** (`worker.py:749-758`):
   ```python
   artifacts = Artifacts(
       clips=[c.to_dict() for c in producer_packet.clips],
       quotes=[q.to_dict() for q in producer_packet.quotes],
       producer_packet=producer_packet.to_dict(),
       quality_gate_passed=passes_gate,
       content_blueprints=content_blueprints_dicts,
       gap_analysis=gap_analysis_dict,
       research_starter=research_starter_dict,
   )
   update_job(job_id, artifacts=artifacts, ...)
   ```

2. **Database stores correctly** (confirmed - JSONB column has all fields)

3. **Retrieval strips fields** (`supabase_store.py:110-114`):
   ```python
   artifacts_data = _normalize_jsonb_field(row.get("artifacts"))  # Full dict
   artifacts = Artifacts(
       drive_folder_url=artifacts_data.get("drive_folder_url"),  # Only 2 fields!
       doc_urls=artifacts_data.get("doc_urls"),
   )
   ```

4. **API serializes stripped object** (`jobs_routes.py:447-451`):
   ```python
   artifacts_dict = None
   if job.artifacts:
       artifacts_dict = job.artifacts.model_dump(exclude_none=True)  # Empty dict
   ```

5. **Frontend receives empty artifacts** - cannot display clips/quotes

## Evidence

### Artifacts Model Definition
`backend/models/job_record.py:8-32` defines all fields including video analysis fields.

### Worker Sets All Fields
`backend/worker.py:749-758` constructs complete Artifacts with clips/quotes/producer_packet.

### Retrieval Only Reconstructs 2 Fields
`backend/state/impl/supabase_store.py:111-114` ignores 9 of 11 fields.

### API Returns Empty
`jobs_routes.py:447-451` (list) and `519-522` (get) serialize the stripped Artifacts object.

## Impact Assessment

**Affected Endpoints:**
- `GET /jobs` - List endpoint (line 447)
- `GET /jobs/{id}` - Detail endpoint (line 519)
- `GET /jobs/video-analysis/{id}` - Video status endpoint (line 310)

**Affected Features:**
- Video analysis job display (primary product feature)
- Phase 3 research pipeline outputs (content_blueprints, gap_analysis, research_starter)
- Quality gate status display

**Workaround:** None - data is present in database but inaccessible via API.

## Solution

Update `_record_from_db_row()` to reconstruct **all Artifacts fields**, not just legacy ones:

```python
def _record_from_db_row(row: dict[str, Any]) -> JobRecord:
    """Convert database row to JobRecord."""
    artifacts_data = _normalize_jsonb_field(row.get("artifacts"))
    artifacts = Artifacts(
        # Legacy fields (topic research mode)
        drive_folder_url=artifacts_data.get("drive_folder_url"),
        doc_urls=artifacts_data.get("doc_urls"),
        # Video analysis fields (Gemini pivot - Jan 2026)
        clips=artifacts_data.get("clips"),
        quotes=artifacts_data.get("quotes"),
        producer_packet=artifacts_data.get("producer_packet"),
        quality_gate_passed=artifacts_data.get("quality_gate_passed"),
        # Phase 3 fields (Full Research Assistant)
        content_blueprints=artifacts_data.get("content_blueprints"),
        gap_analysis=artifacts_data.get("gap_analysis"),
        research_starter=artifacts_data.get("research_starter"),
    )
    # ... rest of function
```

**File:** `backend/state/impl/supabase_store.py`
**Lines:** 111-114
**Risk:** Low - additive change, no breaking changes for existing jobs

## Outputs Model (Secondary Issue)

Same pattern affects Outputs model (lines 117-129) - only reconstructs 10 known markdown fields, but Outputs could be extended in future. Not currently blocking since topic research mode uses these fields correctly.

## Related Files

- `backend/models/job_record.py` - Artifacts/Outputs model definitions
- `backend/state/impl/supabase_store.py` - Data retrieval layer (bug location)
- `backend/state/impl/in_memory.py` - In-memory store (may have same issue)
- `backend/worker.py` - Sets artifacts correctly
- `backend/app/routes/jobs_routes.py` - API serialization (correct)

## In-Memory Store Comparison

**Status:** ✅ In-memory store handles correctly

`backend/state/impl/in_memory.py:120-125` correctly merges partial artifacts:
```python
if partial_artifacts:
    if job.artifacts is None:
        job.artifacts = Artifacts()
    for key, value in partial_artifacts.items():
        if hasattr(job.artifacts, key) and value is not None:
            setattr(job.artifacts, key, value)
```

This works because in-memory store operates on JobRecord objects directly (no serialization). Supabase store retrieves JSONB and must explicitly reconstruct all fields.

## Unresolved Questions

1. Are there other JSONB fields with partial reconstruction? (Check outputs, config_json, etc.)
2. Should we add validation to prevent this? (Pydantic model → dict → Pydantic model round-trip test)
3. Why was this not caught in testing? (No integration tests for video analysis mode)
