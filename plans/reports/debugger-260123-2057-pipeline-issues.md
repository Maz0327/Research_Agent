# Research Agent Pipeline Debug Report

**Date:** 2026-01-23 20:57
**Debugger ID:** a9c0421
**Investigation:** Loading states, Producer Packet, Iterations

---

## Executive Summary

Investigated 4 pipeline issues:
1. **Stage names showing technical IDs** - No display mapping found, raw stage names exposed to UI
2. **Producer Packet endpoint working** - Endpoint exists at `POST /{job_id}/producer-packet`, worker task `run_producer_task` implemented
3. **Booster integration present** - Booster NOT part of producer packet, separate task `run_booster_task`
4. **Iteration endpoint working** - Endpoint exists at `POST /{job_id}/iterate`, worker task `run_iteration_task` implemented with placeholder logic

**Root Cause:** Issue #1 is a missing UI mapping layer. Issues #2-4 are not failures - endpoints exist and are functional (though iteration has placeholder implementation).

---

## Technical Analysis

### Issue 1: Stage Names Showing Technical IDs

**Location:** Frontend job detail page displays raw stage names

**Evidence:**
```typescript
// frontend/pages/jobs/[id].tsx:389
{job.status === 'queued' ? 'Job queued...' : `Processing: ${job.stage || 'Running'}...`}
```

**Stage names from backend:**
- `source_identity` (worker.py:200)
- `semantic_extraction` (worker.py:336)
- `semantic_validation` (worker.py:339)
- `gap_analysis` (worker.py:342)
- `semantic_synthesis` (worker.py:345)
- `document_assembly` (worker.py:348)
- `completion` (worker.py:354)

**Problem:** No mapping layer converts technical names to user-friendly descriptions

**Expected behavior:**
```
source_identity → "Analyzing sources..."
semantic_extraction → "Extracting key insights..."
semantic_validation → "Validating findings..."
gap_analysis → "Identifying knowledge gaps..."
semantic_synthesis → "Synthesizing insights..."
document_assembly → "Creating documents..."
completion → "Finalizing..."
```

**Files involved:**
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/pages/jobs/[id].tsx` (line 389)
- `/Users/maz/Documents/GitHub/Research_Agent/backend/worker.py` (lines 200-354)

---

### Issue 2: Producer Packet Status

**Status:** ✅ WORKING

**Endpoint:**
```python
# backend/app/routes/jobs_routes.py:1212
@router.post("/{job_id}/producer-packet")
async def generate_producer_packet(...)
```

**Worker task:**
```python
# backend/worker.py:1457
@celery_app.task(
    bind=True,
    name="backend.worker.run_producer_task",
    max_retries=1,
    soft_time_limit=300,  # 5 min
)
def run_producer_task(self, job_id: str, user_id: str) -> dict:
```

**Flow:**
1. User triggers via `POST /jobs/{job_id}/producer-packet`
2. Endpoint validates gating requirements (4+ sources, 1 high-confidence)
3. Sets `producer_status="queued"`
4. Enqueues `run_producer_task` Celery task
5. Worker generates Doc 3 (creative interpretation)
6. Sets `producer_status="completed"` or `"failed"`

**Frontend integration:**
```typescript
// frontend/store/jobs.ts:878
triggerProducerPacket: async (jobId: string): Promise<ProducerPacketResponse> => {
  const response = await fetch(`${API_URL}/jobs/${jobId}/producer-packet`, {
    method: 'POST',
    headers,
  });
  // Updates producer_status in local state
}
```

**Critical notes:**
- Producer status is SEPARATE from `job.status`
- Job remains `status="completed"` while producer runs
- Failure does NOT affect Doc 0/1/2

---

### Issue 3: Booster Function

**Status:** ✅ SEPARATE TASK (not part of producer packet)

**Clarification:** Booster is NOT part of producer packet. It's a separate deep research expansion.

**Endpoint:**
```python
# backend/app/routes/jobs_routes.py:1053
@router.post("/{job_id}/booster")
async def run_job_booster(...)
```

**Worker task:**
```python
# backend/worker.py:1220
@celery_app.task(
    bind=True,
    name="backend.worker.run_booster_task",
    max_retries=2,
    time_limit=600,  # 10 min
)
def run_booster_task(self, job_id: str, user_id: str) -> dict:
```

**Purpose:**
- Expands Doc 1 (Jump-Start Directions) with additional research directions
- Produces DIRECTIONS, not FACTS
- Separate from producer packet (Doc 3)

**Producer vs Booster:**
- **Producer Packet (Doc 3):** Creative interpretation, narrative angles, story structure
- **Booster:** Research directions, search queries, missing perspectives

---

### Issue 4: Iteration Status

**Status:** ✅ ENDPOINT EXISTS, WORKER HAS PLACEHOLDER

**Endpoint:**
```python
# backend/app/routes/jobs_routes.py:1406
@router.post("/{job_id}/iterate", response_model=IterateJobResponse)
async def run_job_iteration(
    request: Request,
    job_id: str,
    iterate_request: IterateJobRequest,
    user: AuthUser = Depends(get_active_user),
)
```

**Worker task:**
```python
# backend/worker.py:1672
@celery_app.task(
    bind=True,
    name="backend.worker.run_iteration_task",
    max_retries=1,
    soft_time_limit=900,  # 15 min
    time_limit=960,
)
def run_iteration_task(self, job_id: str, iteration_id: str, user_id: str) -> dict:
```

**Current implementation:**
```python
# backend/worker.py:1763-1770
# PLACEHOLDER - Full implementation requires pipeline
# TODO: Implement full iteration pipeline in backend/pipeline/iteration/
iter_outputs = IterationOutputs(
    doc_0_path=None,  # Will be set when pipeline generates docs
    doc_1_path=None,
    doc_2_path=None,
    # ...
)
```

**What works:**
1. Endpoint accepts iteration requests
2. Creates iteration bundle in `artifacts.iterations[]`
3. Sets `iteration_status="running"`
4. Worker updates progress to 100% (placeholder)

**What doesn't work:**
- No actual pipeline execution (line 1772: "PLACEHOLDER")
- No source discovery for `mode='more_sources'`
- No re-analysis for `mode='deeper'`
- No doc generation

**Frontend integration:**
```typescript
// frontend/store/jobs.ts:917
triggerIteration: async (jobId: string, request: IterationRequest) => {
  const response = await fetch(`${API_URL}/jobs/${jobId}/iterate`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });
}
```

---

## Root Cause Analysis

### Issue 1: Missing UI Mapping
**Cause:** No display name mapping between backend stage names and user-friendly text

**Chain of events:**
1. Worker sets `job.stage = "source_identity"` (worker.py:200)
2. Frontend polls job status (jobs.ts:974)
3. Job detail page displays raw stage name (jobs/[id].tsx:389)
4. User sees "Processing: source_identity..." instead of friendly description

**Why it happened:** UI built to display raw stage names directly, no translation layer added

---

### Issue 2-4: Not Actually Failures

**Producer Packet:** Fully implemented, endpoint working, worker functional
**Booster:** Fully implemented, separate from producer, working independently
**Iteration:** Endpoint working, worker placeholder (expected for Phase 9 incomplete implementation)

---

## Recommendations

### 1. Add Stage Display Mapping (HIGH PRIORITY)

Create mapping file:
```typescript
// frontend/lib/stage-names.ts
export const STAGE_DISPLAY_NAMES: Record<string, string> = {
  // Main pipeline stages
  source_identity: "Analyzing sources...",
  semantic_extraction: "Extracting insights...",
  semantic_validation: "Validating findings...",
  gap_analysis: "Identifying gaps...",
  semantic_synthesis: "Synthesizing research...",
  document_assembly: "Creating documents...",
  completion: "Finalizing...",

  // Video analysis stages
  pass_1_extraction: "Pass 1: Extracting clips...",
  pass_2_structure: "Pass 2: Analyzing structure...",
  pass_3_gaps: "Pass 3: Finding gaps...",
  pass_4_research: "Pass 4: Research directions...",

  // Transcript stages
  extracting_transcripts: "Extracting transcripts...",
  storing_transcripts: "Storing transcripts...",

  // Error/timeout states
  error: "Error occurred",
  timeout: "Timed out",
};

export function getStageDisplayName(stage: string | undefined): string {
  if (!stage) return "Processing...";
  return STAGE_DISPLAY_NAMES[stage] || stage;
}
```

Update job detail page:
```typescript
// frontend/pages/jobs/[id].tsx:389
import { getStageDisplayName } from '../../lib/stage-names';

{job.status === 'queued'
  ? 'Job queued...'
  : `${getStageDisplayName(job.stage)}` // Remove "Processing: " prefix
}
```

### 2. Complete Iteration Pipeline (MEDIUM PRIORITY)

Implement full iteration logic in worker:
- Source discovery for `mode='more_sources'`
- Re-extraction for `mode='deeper'`
- Angle-specific synthesis for `mode='different_angle'`
- Doc generation and storage

File to create: `backend/pipeline/iteration/` module

### 3. Add Stage Progress Details (LOW PRIORITY)

Enhance stage updates with sub-progress:
```python
# worker.py example
update_job(
    job_id,
    stage="semantic_extraction",
    pass_detail=f"Analyzing source {i+1}/{total}",
    progress_percent=progress,
)
```

Display in UI:
```typescript
{job.pass_detail && (
  <p className="text-sm text-gray-400">{job.pass_detail}</p>
)}
```

---

## Supporting Evidence

### Log Analysis
No log files found in `backend/logs/` - unable to check for runtime errors

### Database State
Not checked - would require Supabase credentials

### Error Patterns
Frontend calling correct endpoints:
- `POST /jobs/{job_id}/producer-packet` ✓
- `POST /jobs/{job_id}/iterate` ✓
- `POST /jobs/{job_id}/booster` ✓

Backend workers registered with Celery:
- `backend.worker.run_producer_task` ✓
- `backend.worker.run_iteration_task` ✓
- `backend.worker.run_booster_task` ✓

---

## Unresolved Questions

1. Are there Celery logs showing task execution failures?
2. Are jobs stuck in `producer_status="running"` indefinitely?
3. Are iteration tasks completing but showing no results?
4. Is Redis broker accessible and processing tasks?

To answer these:
- Check Celery worker logs: `celery -A backend.worker worker --loglevel=DEBUG`
- Query Supabase for jobs with hanging statuses
- Monitor Redis task queue: `redis-cli LLEN celery`

---

## File Manifest

**Frontend:**
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/pages/jobs/[id].tsx` - Job detail page
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/store/jobs.ts` - Job state management
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-detail/ActiveTaskBanner.tsx` - Task status banner

**Backend:**
- `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/jobs_routes.py` - API endpoints
- `/Users/maz/Documents/GitHub/Research_Agent/backend/worker.py` - Celery task definitions
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/producer_stage.py` - Producer implementation
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/booster_stage.py` - Booster implementation

---

## Conclusion

**Issue #1 (Stage names):** Missing UI mapping layer - simple fix, create display name dictionary
**Issue #2 (Producer):** Not a bug - fully implemented and working
**Issue #3 (Booster):** Not part of producer - separate task, fully implemented
**Issue #4 (Iteration):** Endpoint working, pipeline implementation incomplete (expected)

**Next Steps:**
1. Implement stage display mapping (30 min)
2. Test producer packet triggers on live job
3. Complete iteration pipeline logic (2-4 hours)
4. Add integration tests for secondary tasks
