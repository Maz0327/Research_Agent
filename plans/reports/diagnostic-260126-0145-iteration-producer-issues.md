# Diagnostic Report: Iteration Mode & Producer Packet Issues

**Date:** 2026-01-26 01:45
**Branch:** `claude/fix-metadata-supadata-ABW4P`

---

## Issues Reported

1. UI changes not showing in iteration mode
2. Document outputs still in markdown format
3. Producer pack produces nothing/empty

---

## Root Cause Analysis

### Issue 1: Iteration Documents Missing Markdown

**Location:**
- `backend/pipeline/iteration/storage_manager.py`
- `backend/pipeline/runs/storage.py`

**Problem:**
When iteration/run documents are stored, only the JSON dict is saved. The markdown version is not included in the inline fallback data.

**Evidence:**
```python
# iteration/storage_manager.py:71-79
outputs = IterationOutputs(
    doc_0_path=paths["doc_0_path"],
    ...
    # Include inline data as fallback if storage failed
    doc_0_inline=doc_0 if not paths["doc_0_path"] else None,  # <-- No markdown!
    ...
)
```

**Frontend expectation (ArtifactCardGrid.tsx:214-218):**
```typescript
const inlineData = run.outputs[inlineKey];
data = nestedData || inlineData;
markdown = (inlineData as { markdown?: string }).markdown;  // <-- Expects markdown field!
```

**Impact:** When viewing iteration documents, the modal shows empty/raw JSON instead of formatted markdown.

---

### Issue 2: Run-Scoped Producer Packet Not Retrieved

**Location:**
- `frontend/components/job-detail/ArtifactCardGrid.tsx:281-290`

**Problem:**
Frontend only checks job-level `artifacts.producer_packet_md` for Doc 3, not run-scoped `run.producer_packet.markdown`.

**Evidence:**
```typescript
// ArtifactCardGrid.tsx - Only checks job level, not run level
case 3:
  if (artifacts.doc_3_path) {
    const result = await fetchDocumentFromAPI(job.id, 'doc_3');
    ...
  } else if (artifacts.producer_packet_md) {  // <-- Job level only!
    data = { markdown: artifacts.producer_packet_md };
    markdown = artifacts.producer_packet_md;
  }
  break;
```

**What should happen:**
For V2 runs, check `run.producer_packet.markdown` when viewing that run's producer output.

**Impact:** Producer packet shows empty for V2 runs even when data exists in run-scoped storage.

---

### Issue 3: Rate Limit Key Missing (Previously Identified)

**Location:** `backend/app/rate_limiter.py`

**Problem:**
`RATE_LIMITS["jobs_status"]` referenced but not defined. Causes Railway API crash.

**Status:** Fix pushed to feature branch.

---

## Recommended Fixes

### Fix 1: Include Markdown in Document Storage

**File:** `backend/pipeline/iteration/storage_manager.py`

Add markdown to inline data:
```python
def store_iteration_docs(
    job_id: str,
    iteration_id: str,
    doc_0: dict[str, Any],
    doc_1: dict[str, Any],
    doc_2: dict[str, Any],
    doc_0_md: str = None,  # NEW
    doc_1_md: str = None,  # NEW
    doc_2_md: str = None,  # NEW
) -> IterationOutputs:
    # ... existing storage code ...

    # Build inline data with markdown included
    doc_0_inline = None
    if not paths["doc_0_path"]:
        doc_0_inline = {"data": doc_0, "markdown": doc_0_md}
```

**Alternative:** Store markdown as nested field in the JSON document itself:
```python
# In document_assembly.py when building dict
doc_0_with_md = {
    **doc_0.to_dict(),
    "markdown": doc_0.to_markdown()
}
```

---

### Fix 2: Handle Run-Scoped Producer Packet in Frontend

**File:** `frontend/components/job-detail/ArtifactCardGrid.tsx`

Update Doc 3 handling to check run-scoped producer:
```typescript
case 3:
  // Check run-scoped producer first (V2)
  if (!isBaseline && isV2Run(selectedVersion)) {
    const run = runs.find(r => r.run_id === selectedVersion);
    if (run?.producer_packet?.status === 'completed') {
      if (run.producer_packet.markdown) {
        data = run.producer_packet.inline || {};
        markdown = run.producer_packet.markdown;
      }
      // If found, skip job-level check
      break;
    }
  }
  // Fallback to job-level (baseline or V1)
  if (artifacts.doc_3_path) {
    const result = await fetchDocumentFromAPI(job.id, 'doc_3');
    data = result.data;
    markdown = result.markdown;
  } else if (artifacts.producer_packet_md) {
    data = { markdown: artifacts.producer_packet_md };
    markdown = artifacts.producer_packet_md;
  }
  break;
```

---

### Fix 3: Rate Limit Key (Already Applied)

Added `"jobs_status": "60/minute"` to `RATE_LIMITS` in `rate_limiter.py`.

---

## Impact Summary

| Issue | User Impact | Severity |
|-------|-------------|----------|
| Missing markdown in iterations | Documents appear empty/broken | HIGH |
| Run-scoped producer not retrieved | Producer button works but shows empty | HIGH |
| Rate limit key missing | API crashes on startup | CRITICAL |

---

## Next Steps

1. **Immediate:** Merge rate limit fix to main (PR pending)
2. **Short-term:** Apply Fix 2 (frontend run-scoped producer)
3. **Medium-term:** Apply Fix 1 (backend markdown in storage)

---

## Files Modified

### Already Modified
- `backend/app/rate_limiter.py` - Added jobs_status rate limit

### Need Modification
- `frontend/components/job-detail/ArtifactCardGrid.tsx` - Run-scoped producer handling
- `backend/pipeline/iteration/storage_manager.py` - Markdown in inline data
- `backend/pipeline/runs/storage.py` - Markdown in inline data
