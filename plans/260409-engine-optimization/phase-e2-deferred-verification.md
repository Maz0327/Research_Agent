---
phase: E-2
title: "Deferred Verification"
status: pending
effort: 3-4h
risk: medium
---

# E-2: Deferred Verification

**What:** Move quote verification, LLM Judge, and RAG Grounding out of the extraction thread. Run them as a background Celery task after synthesis completes.
**Why:** These 3 steps add 5-15s per source in the critical path. The brief is usable without them. Verification results update asynchronously.
**Risk:** Medium — need to track verification state, update DB when done.

## Current Flow (lines 1129-1158 of semantic_extraction.py)

```
Per source (inside ThreadPoolExecutor):
  1. Gemini extraction → result
  2. Quote verification (sequential, ~1-2s)      ← REMOVE FROM HERE
  3. LLM Judge GPT-4o (sequential, ~3-5s)        ← REMOVE FROM HERE
  4. RAG Grounding (sequential, ~2-3s)            ← REMOVE FROM HERE
  5. Return result
```

## New Flow

```
Per source (inside ThreadPoolExecutor):
  1. Gemini extraction → result
  2. Return result (FAST — no verification)

After synthesis completes (background Celery task):
  1. For each source extraction:
     a. Quote verification
     b. LLM Judge
     c. RAG Grounding
  2. Update job record with verification results
  3. Update verification_status: "pending" → "complete"
```

## Changes

### 1. `backend/pipeline/stages/semantic_extraction.py`
Remove steps 5-7 from `_extract_single_source()` (lines 1129-1158). Keep the extraction + validation only.

Add a flag to each result: `verification_status = "pending"`.

### 2. `backend/worker.py` — new Celery task
```python
@celery_app.task(name="backend.worker.run_verification_task")
def run_verification_task(job_id: str) -> dict:
    """Run deferred verification on all extracted sources."""
    # 1. Load job and extraction results from DB
    # 2. For each source:
    #    a. verify_quotes_in_extraction()
    #    b. _run_llm_judge()
    #    c. _run_rag_grounding()
    # 3. Update job with verification results
    # 4. Set verification_status = "complete"
```

### 3. `backend/worker.py` — trigger after synthesis
In `_run_mixed_input_job()`, after the synthesis stage completes, fire the verification task:

```python
# After synthesis completes (line ~469):
run_verification_task.delay(job_id)
```

### 4. `backend/app/routes/` — expose verification status
Add `verification_status` field to job response so frontend can show "Verifying..." badge.

### 5. Database — add verification_status column (optional)
Could use existing `metadata` JSONB field instead of a new column to avoid migration.

## Tests
- Extraction tests should pass faster (no verification in path)
- New test: `test_verification_task_runs_independently`
- New test: `test_extraction_returns_pending_verification`

## Success Criteria
- Extraction completes without verification blocking
- Verification runs as background task
- Job record updated with verification results
- No data loss — same verification quality, just deferred
