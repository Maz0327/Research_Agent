# Run Abstraction System - Inventory

**Date:** 2026-01-25
**Phase:** 1 - Discovery & Inventory

---

## Current Iteration System Inventory

### A. Iteration Endpoints/Routes

| File | Function/Route | Lines | Description |
|------|---------------|-------|-------------|
| `backend/app/routes/jobs_routes.py` | `POST /{job_id}/iterate` | 1398-1580+ | Creates iteration entry, enqueues task |
| `backend/app/routes/jobs_routes.py` | Route handler | 1521-1561 | Appends to `artifacts.iterations[]` |

### B. Iteration Worker Task

| File | Function | Lines | Description |
|------|----------|-------|-------------|
| `backend/worker.py` | `run_iteration_task()` | 1711-1927 | Executes iteration, stores outputs |
| `backend/worker.py` | Task registration | 1711 | Celery task name: `backend.worker.run_iteration_task` |
| `backend/worker.py` | Queue config | 38 | Uses `research` queue |

### C. Iteration Storage Paths

| Path Pattern | Description |
|--------------|-------------|
| `jobs/{job_id}/iterations/{iteration_id}/doc_0.json` | Iteration Source Ledger |
| `jobs/{job_id}/iterations/{iteration_id}/doc_1.json` | Iteration Jump-Start |
| `jobs/{job_id}/iterations/{iteration_id}/doc_2.json` | Iteration Semantic Brief |

**Storage Implementation:** `backend/pipeline/iteration/storage_manager.py`

### D. Iteration Artifacts Structure

**Model:** `backend/models/job_record.py`

```python
class Artifacts(BaseModel):
    # Baseline docs (lines 84-92)
    doc_0_path: Optional[str]  # Baseline Source Ledger
    doc_1_path: Optional[str]  # Baseline Jump-Start
    doc_2_path: Optional[str]  # Baseline Semantic Brief

    # Iteration history (line 113)
    iterations: list[Iteration] = Field(default_factory=list)  # Append-only

    # Producer/Booster (lines 93-106)
    doc_3_path: Optional[str]  # Producer Packet storage path
    booster_output: Optional[dict]
    booster_expansion_md: Optional[str]
    producer_packet: Optional[dict]
    producer_packet_md: Optional[str]
```

**Iteration Bundle Structure:**
```python
class Iteration(BaseModel):
    iteration_id: str  # "it_0001", "it_0002", ...
    index: int
    request: IterationRequest
    status: str  # queued, running, completed, failed
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    outputs: Optional[IterationOutputs]
    metrics: Optional[IterationMetrics]
    error: Optional[IterationError]
```

### E. UI Components for Iterations

| File | Component | Description |
|------|-----------|-------------|
| `frontend/components/job-detail/IterationSelector.tsx` | `IterationSelector` | Dropdown to select baseline vs iterations |
| `frontend/pages/jobs/[id].tsx` | Job detail page | Uses `selectedVersion` state ('baseline' or 'it_0001') |
| `frontend/store/jobs.ts` | `IterationBundle` type | Type definition (lines 157-178) |
| `frontend/store/jobs.ts` | `startIteration()` | Action to trigger iteration (line 918+) |

### F. Iteration Modes

| File | Mode | Description |
|------|------|-------------|
| `backend/pipeline/iteration/modes/more_sources.py` | `more_sources` | Add more sources (BROKEN - generates fake URLs) |
| `backend/pipeline/iteration/modes/deeper.py` | `deeper` | Deeper analysis |
| `backend/pipeline/iteration/modes/custom.py` | `custom` | Custom prompt |
| `backend/pipeline/iteration/modes/different_angle.py` | `different_angle` | Different perspective |

---

## Required Ripgrep Search Results

### 1. `rg "iteration endpoint"`
No direct matches for "iteration endpoint" string.

### 2. `rg "iteration task"`
```
backend/worker.py:38:        "backend.worker.run_iteration_task": {"queue": "research"},
backend/worker.py:1716:def run_iteration_task(self, job_id: str, iteration_id: str, user_id: str) -> dict:
```

### 3. `rg "artifacts\.iterations"`
```
backend/worker.py:1721:    job.artifacts.iterations[]. Baseline doc_0/doc_1/doc_2 are NEVER modified.
backend/app/routes/jobs_routes.py:1428:    job.artifacts.iterations[]. Baseline doc_0/doc_1/doc_2 are NEVER modified.
```

### 4. `rg "Booster.*job_id"` (key matches)
```
backend/worker.py:1230:def run_booster_task(self, job_id: str, user_id: str) -> dict:
backend/app/routes/jobs_routes.py:1063:@router.post("/{job_id}/booster")
backend/pipeline/stages/booster_stage.py:223:    logger.info(f"Running booster for job {bundle.job_id}")
```
**Note:** Booster takes `job_id` only, no `run_id` parameter.

### 5. `rg "Producer.*job_id"` (key matches)
```
backend/worker.py:1466:def run_producer_task(self, job_id: str, user_id: str) -> dict:
backend/app/routes/jobs_routes.py:1222:@router.post("/{job_id}/producer-packet")
backend/pipeline/stages/producer_stage.py:59:    logger.info(f"Running producer pipeline for job {job_id}")
```
**Note:** Producer takes `job_id` only, no `run_id` parameter.

### 6. `rg "doc_0.*append|append.*doc_0"`
No meaningful matches - append behavior not currently implemented for Doc 0.

### 7. `rg "run_id"`
**No matches** - `run_id` concept does not exist yet.

---

## Key Findings

### 1. Producer/Booster Are Job-Level Only
- Both `run_booster_task()` and `run_producer_task()` take only `job_id`
- Outputs stored in `artifacts.booster_*` and `artifacts.producer_*` (job-level)
- **Gap:** No way to scope Producer/Booster to a specific run

### 2. Iterations Are Append-Only (Correct)
- `artifacts.iterations[]` is append-only list
- Each iteration produces its own doc_0/doc_1/doc_2
- Baseline docs never modified

### 3. Doc 0 Does Not Have Append Behavior
- Currently iteration Doc 0 is a complete replacement
- **Gap:** Need to implement "append new sources only" for Doc 0

### 4. No Unified "Run" Concept
- Baseline is implicit (no run_id)
- Iterations have `iteration_id`
- Producer/Booster have no run scoping
- **Gap:** Need unified Run model

### 5. Problematic more_sources Mode
- `backend/pipeline/iteration/modes/more_sources.py` generates fake "suggested://" URLs
- Creates synthetic extractions instead of real content
- **Action:** This needs to be completely rewritten

---

## Proposed Run Model Structure

```
job
├── runs[]
│   ├── run_0 (baseline)
│   │   ├── type: "baseline"
│   │   ├── doc_0 (Source Ledger)
│   │   ├── doc_1 (Jump-Start)
│   │   ├── doc_2 (Semantic Brief)
│   │   ├── producer_packet (optional, run-scoped)
│   │   └── booster_expansion (optional, run-scoped)
│   │
│   ├── run_1 (iteration)
│   │   ├── type: "add_sources"
│   │   ├── parent_run_id: "run_0"
│   │   ├── doc_0 (APPENDS to parent Doc 0)
│   │   ├── doc_1 (regenerated)
│   │   ├── doc_2 (regenerated)
│   │   └── producer_packet (optional)
│   │
│   └── run_2 (regenerate)
│       ├── type: "regenerate"
│       ├── parent_run_id: "run_1"
│       ├── doc_0 (same sources, no change)
│       ├── doc_1 (regenerated)
│       └── doc_2 (regenerated)
```

---

## Backward Compatibility Requirements

1. **Existing Jobs:** Jobs without `runs[]` must work with shim
2. **Baseline as run_0:** Treat `artifacts.doc_*_path` as implicit `run_0`
3. **Iteration → Run Migration:** Map existing `iterations[]` to new `runs[]`
4. **Producer/Booster:** Existing job-level outputs remain accessible
5. **API Compatibility:** Existing endpoints continue working

---

## Next Steps

1. Design Run data model (types, storage paths)
2. Implement backward compatibility shim
3. Update Producer/Booster to accept `run_id`
4. Implement run-based iteration actions
5. Update UI for run selection
