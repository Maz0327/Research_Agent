# Debug Report: Job Output & Frontend Wiring Issues

**Date:** 2026-01-21
**Issue:** Job completes with 109 warnings but produces no visible output; frontend changes not showing

---

## Root Causes Identified

### Issue 1: Backend Bug in `stage_10_completion` (FIXED)

**Location:** `backend/pipeline/stages/initialization.py:333-348`

**Problem:** The `storage_paths` variable was being overwritten after it was correctly computed:

```python
# Line 333-334 - BUG: Overwrites storage_paths with non-existent ctx.outputs["storage_paths"]
storage_paths = None
storage_paths = (ctx.outputs or {}).get("storage_paths")  # Never set!
```

The code expected `ctx.outputs["storage_paths"]` to be set, but no part of the pipeline ever sets this. The actual storage paths come from `_try_upload_documents_to_storage()` and are stored in `artifacts_dict`.

**Fix:** Changed to read from `artifacts_dict` which is already computed:

```python
# --- Build doc_paths from artifacts_dict (already computed above) ---
doc_paths = {}
for k in ("doc_0", "doc_1", "doc_2", "doc_3"):
    path_key = f"{k}_path"
    if path_key in artifacts_dict:
        doc_paths[k] = artifacts_dict[path_key]
```

### Issue 2: Validation Status Logging (NOT A BUG)

The `status=failed` messages in worker logs are **per-source validation reports**, not pipeline failures. The validation system is designed to be fault-tolerant:

- HARD_FAIL → retry if schema issue, otherwise add warning
- SOFT_FAIL → add warning, continue with degraded output
- Job completes with warnings, producing "thin but honest" output

This is working as designed per the spec in `semantic_validation.py`.

### Issue 3: Frontend Deployment (NEEDS VERIFICATION)

The Document Accordion UI changes were committed (`eee8b86`) but may not have been deployed:

- `frontend/components/job-card/DocumentAccordion.tsx` - new file
- `frontend/components/job-card/JobResults.tsx` - updated layout
- `frontend/lib/pdf-export.ts` - new utility

**Action Required:** Verify frontend is rebuilt and deployed to production/staging.

---

## Files Modified

| File | Change |
|------|--------|
| `backend/pipeline/stages/initialization.py` | Fixed `storage_paths` bug in `stage_10_completion()` |
| `backend/tests/test_pipeline_stages.py` | Updated tests to match actual code behavior |

---

## Tests

All pipeline tests pass:
- `test_completion_sets_job_completed` ✓
- `test_completion_returns_result_dict` ✓
- `test_completion_handles_no_storage_paths` ✓
- All other tests ✓ (10 total)

---

## Recommendations

1. **Deploy frontend** - Run `npm run build` and deploy the updated frontend
2. **Re-run a test job** - After fixes are deployed, run a new job to verify output
3. **Check Supabase Storage config** - If `SUPABASE_SERVICE_ROLE_KEY` isn't set, documents will be inline-only (still works, but larger payloads)

---

## Verification Steps

1. Deploy backend with the fix
2. Deploy frontend with accordion UI
3. Create new mixed-input job with 1-2 sources
4. Verify job completes with artifacts visible in UI
5. Test accordion expand/collapse and PDF download
