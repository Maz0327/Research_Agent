# Iteration Execution Failure Report

**Date**: 2026-01-24
**Debugger ID**: a2110d7
**Issue**: Iterations queued in UI but never execute

---

## Executive Summary

**Root Cause**: No Celery worker process running to consume iteration tasks

**Impact**: All iteration requests succeed at API level but remain in "queued" status indefinitely. Tasks enqueued to Redis but no worker to process them.

**Fix**: Start Celery worker process

---

## Technical Analysis

### Flow Verification

Traced complete iteration flow from UI click to worker execution:

**1. Frontend** (`frontend/pages/jobs/[id].tsx` + `frontend/store/jobs.ts`)
- ✅ UI correctly triggers `triggerIteration(jobId, request)`
- ✅ POST request sent to `/jobs/{job_id}/iterate`
- ✅ Local state updated to `iteration_status: 'queued'`

**2. Backend API** (`backend/app/routes/jobs_routes.py:1408-1612`)
- ✅ Endpoint exists: `POST /{job_id}/iterate`
- ✅ Validation passes (job completed, no running iteration)
- ✅ Iteration object created and appended to `job.artifacts.iterations[]`
- ✅ Job record updated with `iteration_status: 'queued'`
- ✅ Task enqueued: `run_iteration_task.apply_async((job_id, iteration_id, user_id), task_id=...)`

**3. Backend Worker** (`backend/worker.py:1672-1690`)
- ✅ Task defined: `@celery_app.task(name="backend.worker.run_iteration_task")`
- ✅ Celery app configured with Redis broker: `redis://localhost:6379/0`
- ❌ **MISSING**: Task route for `run_iteration_task` not in `task_routes` dict

**4. Infrastructure**
- ✅ Redis server running (port 6379, responds to PING)
- ✅ Redis queue empty (llen research = 0)
- ❌ **CRITICAL**: No Celery worker process running (confirmed via `pgrep -f "celery.*worker"`)

---

## Root Cause Breakdown

### Primary Issue: No Worker Process

```bash
$ pgrep -f "celery.*worker"
No Celery worker process found
```

Tasks are successfully enqueued to Redis but never consumed because no worker is listening.

### Secondary Issue: Multiple Missing Task Routes

`backend/worker.py:35-38` only routes:
```python
task_routes={
    "backend.worker.run_research_job": {"queue": "research"},
    "backend.worker.run_gemini_video_job": {"queue": "research"},
}
```

**Missing task routes**:
- `"backend.worker.run_iteration_task": {"queue": "research"}`
- `"backend.worker.run_booster_task": {"queue": "research"}`
- `"backend.worker.run_producer_task": {"queue": "research"}`

These tasks will route to `task_default_queue="research"` (line 39), but explicit routes ensure consistency and prevent misconfiguration.

---

## Evidence

### Backend API Successfully Enqueues Task

From `backend/app/routes/jobs_routes.py:1585-1591`:
```python
from backend.worker import run_iteration_task
logger.info(f"Enqueuing iteration task for job {job_id}, iteration {iteration_id}")
run_iteration_task.apply_async(
    (job_id, iteration_id, user.user_id),
    task_id=f"{job_id}_{iteration_id}"
)
```

### Task Definition Exists

From `backend/worker.py:1672-1679`:
```python
@celery_app.task(
    bind=True,
    name="backend.worker.run_iteration_task",
    max_retries=1,
    soft_time_limit=900,  # 15 min soft limit
    time_limit=960,  # 16 min hard limit
)
def run_iteration_task(self, job_id: str, iteration_id: str, user_id: str) -> dict:
```

### No Workers Registered

```bash
$ celery -A backend.worker inspect registered
Error: No nodes replied within time constraint
```

### Task Routing Configuration Missing

Current `task_routes` only has:
- `run_research_job`
- `run_gemini_video_job`

Does NOT have `run_iteration_task`.

---

## Actionable Recommendations

### Immediate Fix (Start Worker)

```bash
cd /Users/maz/Documents/GitHub/Research_Agent
source venv/bin/activate
celery -A backend.worker worker --loglevel=INFO --queue=research
```

### Long-term Fix (Add Task Routes)

In `backend/worker.py:35-38`, add missing task routes:
```python
task_routes={
    "backend.worker.run_research_job": {"queue": "research"},
    "backend.worker.run_gemini_video_job": {"queue": "research"},
    "backend.worker.run_iteration_task": {"queue": "research"},  # ADD
    "backend.worker.run_booster_task": {"queue": "research"},    # ADD
    "backend.worker.run_producer_task": {"queue": "research"},   # ADD
},
```

**Note**: Tasks will still route correctly due to `task_default_queue="research"`, but explicit routes prevent future configuration drift.

### Process Management (Optional)

Consider adding Celery worker to process supervision (systemd, supervisord, or pm2) to ensure worker stays running.

---

## Affected Files

**Backend**:
- `/Users/maz/Documents/GitHub/Research_Agent/backend/worker.py` (task routes missing iteration task)
- `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/jobs_routes.py` (working correctly)

**Frontend**:
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/pages/jobs/[id].tsx` (working correctly)
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/store/jobs.ts` (working correctly)

**Infrastructure**:
- No Celery worker process running (systemd/supervisord config missing)

---

## Test Plan

1. Start Celery worker with research queue
2. Trigger iteration from UI
3. Monitor worker logs for task execution
4. Verify iteration status transitions: `queued → running → completed`
5. Confirm iteration documents generated in GCS

---

## Unresolved Questions

- Is Celery worker supposed to auto-start via systemd/supervisord?
- Should worker be containerized (Docker) or run as system service?
- Do booster and producer features also fail silently due to same issue?
