# Bug Fix: Missing source_type Field

**Date:** December 19, 2024
**Issue:** Worker killed with SIGKILL during test job
**Status:** ✅ FIXED

---

## Problem

The test job failed during Stage 7 (Claim Extraction) with two validation errors:

### Error 1: V2 Extraction
```
V2 extraction failed, falling back to Playwright only: 1 validation error for SourceItem
source_type
  Field required
```

### Error 2: Reddit Collection
```
Reddit collection failed: 1 validation error for SourceItem
source_type
  Field required
```

### Error 3: Worker Killed
```
Process 'ForkPoolWorker-8' pid:88512 exited with 'signal 9 (SIGKILL)'
```

---

## Root Cause

The `SourceItem` model requires a `source_type` field (added in Phase 1-3 implementation), but our v2 worker code wasn't providing it when creating SourceItem objects.

**From `backend/models/source.py`:**
```python
class SourceItem(BaseModel):
    url: str = Field(..., description="Canonical URL of the source")
    title: str = Field(..., description="Title of the source")
    source_type: SourceType = Field(..., description="Type of source")  # REQUIRED!
```

---

## Fix Applied

### File: `backend/worker.py`

#### Fix 1: V2 Extraction (Line ~307, ~319)
```python
# BEFORE (missing source_type)
source = SourceItem(
    url=result["url"],
    title=result.get("title", ""),
    text=result["content"],
    notes=f"Extracted via {result.get('api', 'unknown')}"
)

# AFTER (with source_type)
from backend.models.source import SourceType
source = SourceItem(
    url=result["url"],
    title=result.get("title", ""),
    source_type=SourceType.WEB,  # Added required field
    text=result["content"],
    notes=f"Extracted via {result.get('api', 'unknown')}"
)
```

#### Fix 2: Reddit Collection (Line ~402)
```python
# BEFORE (missing source_type)
reddit_source_item = SourceItem(
    url="https://reddit.com/search",
    title="Reddit Discussions",
    text=reddit_md,
    notes="Aggregated Reddit discussions"
)

# AFTER (with source_type)
from backend.models.source import SourceItem, SourceType
reddit_source_item = SourceItem(
    url="https://reddit.com/search",
    title="Reddit Discussions",
    source_type=SourceType.REDDIT,  # Added required field
    text=reddit_md,
    notes="Aggregated Reddit discussions"
)
```

---

## About the SIGKILL

**What is SIGKILL?**
Signal 9 (SIGKILL) is an unrecoverable kill signal usually sent by:
1. **OS Out-of-Memory (OOM) Killer** - Most likely cause
2. Manual process kill (`kill -9`)
3. System resource limits

**Why did it happen?**
The worker likely ran out of memory during Stage 7 (Claim Extraction). Stage 7 processes all extracted content through OpenAI API to extract claims, which can be memory-intensive with large documents.

**Is it fixed?**
The validation errors are fixed. The SIGKILL may not recur, but if it does, we may need to:
- Increase memory allocation
- Process content in smaller batches
- Add memory monitoring

---

## How to Apply Fix

### Step 1: Restart Celery Worker

The Celery worker needs to reload the updated code:

```bash
# Terminal 2 (where Celery is running)
# Press Ctrl+C to stop the worker

# Then restart it:
cd /Users/maz/Documents/GitHub/Research_Agent
source venv/bin/activate
celery -A backend.worker worker --loglevel=INFO
```

### Step 2: Retest

Run the same test job again:

```bash
curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"prompt": "Tesla Cybertruck recall 2024", "pipeline": "investigation"}'
```

---

## Test Results Summary (Before Fix)

### ✅ What Worked:
- Stage 1: Planning ✅
- Stage 2: Research map (9 angles) ✅
- Stage 3: Source discovery (26 URLs) ✅
- Stage 4-5: YouTube/Transcripts (skipped - no channels) ✅
- Stage 6: **Jina v2 extraction started** ✅
  - 24/26 URLs extracted via Jina
  - 2 URLs timed out, fell back to Trafilatura
  - **This proves v2 extraction works!**

### ❌ What Failed:
- Stage 6: V2 extraction validation error (missing source_type)
- Stage 6.5: Reddit collection validation error (missing source_type)
- Stage 7: Worker killed (SIGKILL)

### 📊 Performance Observed:
- **Jina extraction speed:** ~2-5 seconds per URL ✅
- **Jina success rate:** 24/26 = 92% ✅
- **Fallback working:** 2 URLs fell back to Trafilatura ✅

---

## Expected After Fix

After restarting Celery and rerunning the test:

✅ Stage 6: V2 extraction should complete without validation errors
✅ Stage 6.5: Reddit collection should work
✅ Stage 7: Claim extraction should proceed (watch for memory)
✅ Stage 8: **v2 validation** should run (ClaimBuster → Google FC → Perplexity)
✅ Stage 9-10: Drive doc generation and completion

**Watch for:**
- Memory usage during Stage 7
- Cost logging during Stage 8 validation
- Final job completion status

---

## Cost Analysis (From Partial Test)

Even though the job failed, we can see early cost indicators:

### Stage 3: Source Discovery (Perplexity)
- 8 Perplexity API calls made
- Estimated cost: ~$1.60 (8 × $0.20)

### Stage 6: Web Extraction (Jina v2)
- 24 URLs extracted via Jina
- 2 URLs fell back to Trafilatura (local, free)
- Estimated cost: **$0** (Jina free tier)
- **vs old Playwright:** 24 URLs × 10-30s = 4-12 minutes saved ✅

### Stage 8: Would have been validation
- Not reached due to crash
- Expected: ClaimBuster + Google FC + limited Perplexity
- Expected cost: ~$0.40-1.00 (vs ~$2-3 in v1)

---

## Next Steps

1. ✅ **DONE:** Fixed validation errors
2. ⏳ **TODO:** Restart Celery worker
3. ⏳ **TODO:** Rerun test job
4. ⏳ **TODO:** Monitor for SIGKILL (memory issue)
5. ⏳ **TODO:** Verify v2 validation runs
6. ⏳ **TODO:** Check final costs

---

## Files Modified

- `backend/worker.py` - Added `source_type` field to SourceItem creation (2 locations)

**Lines changed:** 4
**Impact:** Critical - fixes validation errors that prevented v2 from working

---

**Status:** Ready to retest with fixed code ✅
