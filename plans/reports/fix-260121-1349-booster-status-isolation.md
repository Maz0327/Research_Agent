# Fix Report: Booster Status Isolation

**Date:** 2026-01-21 13:49
**Issue:** Booster setting `status='running_booster'` broke UI completion gating

---

## Root Cause

The booster code was overwriting `jobs.status` with `"running_booster"`:

1. **Route** (`jobs_routes.py:1127`): `update_job(job_id, status="running_booster")`
2. **Worker** (`worker.py:1292`): `update_job(job_id, status="running_booster")`

This caused:
- Frontend completion check (`status in ['completed', 'completed_with_warnings']`) to fail
- Documents/actions disappeared from UI while booster ran
- Race condition: worker checked status after route changed it → self-inflicted failure

---

## Solution

Track booster state separately with dedicated fields:
- `booster_status` (queued | running | completed | failed)
- `booster_started_at`
- `booster_completed_at`
- `booster_error`
- `booster_progress_percent`

**Key Rule**: `jobs.status` NEVER changes due to booster execution.

---

## Files Changed

### Database Migration
| File | Description |
|------|-------------|
| `backend/migrations/018_add_booster_tracking.sql` | Added 5 booster columns + updated RPC function |

### Backend
| File | Changes |
|------|---------|
| `backend/models/job_record.py:113-118` | Added booster fields to JobRecord model |
| `backend/state/impl/supabase_store.py:155-159,295-299,370-382,446-455,510-519` | Added booster field support to update_job methods |
| `backend/worker.py:1268-1277,1297-1303,1351-1359,1371-1380,1386-1395` | Changed booster to use booster_status instead of status |
| `backend/app/routes/jobs_routes.py:1097-1110,1127-1137,1152-1155` | Changed route to use booster_status |

### Frontend
| File | Changes |
|------|---------|
| `frontend/store/jobs.ts:186-196,854-859` | Added booster fields to Job interface and refreshJob |
| `frontend/components/job-card/JobResults.tsx:55-59,70-75,295-335` | Added booster status display and error handling |
| `frontend/components/JobCard.tsx:219-221` | Pass booster props to JobResults |

### Tests
| File | Tests Added |
|------|-------------|
| `backend/tests/test_booster_status_isolation.py` | 7 tests verifying booster isolation |

---

## Migration SQL

```sql
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS booster_status text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS booster_started_at timestamptz DEFAULT NULL,
ADD COLUMN IF NOT EXISTS booster_completed_at timestamptz DEFAULT NULL,
ADD COLUMN IF NOT EXISTS booster_error text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS booster_progress_percent integer DEFAULT NULL;

-- Constraints
ALTER TABLE jobs ADD CONSTRAINT booster_status_check
CHECK (booster_status IS NULL OR booster_status IN ('queued', 'running', 'completed', 'failed'));

ALTER TABLE jobs ADD CONSTRAINT booster_progress_percent_check
CHECK (booster_progress_percent IS NULL OR (booster_progress_percent >= 0 AND booster_progress_percent <= 100));
```

---

## Test Results

```
backend/tests/test_booster_status_isolation.py::TestBoosterStatusIsolation::test_booster_must_not_set_running_booster_status PASSED
backend/tests/test_booster_status_isolation.py::TestBoosterStatusIsolation::test_booster_route_must_not_set_running_booster_status PASSED
backend/tests/test_booster_status_isolation.py::TestBoosterStatusIsolation::test_booster_task_uses_booster_status_fields PASSED
backend/tests/test_booster_status_isolation.py::TestBoosterStatusIsolation::test_booster_checks_booster_status_for_running PASSED
backend/tests/test_booster_status_isolation.py::TestBoosterStatusIsolation::test_job_record_has_booster_fields PASSED
backend/tests/test_booster_status_isolation.py::TestBoosterStatusIsolation::test_update_job_supports_booster_fields PASSED
backend/tests/test_booster_status_isolation.py::TestBoosterUIGating::test_completed_job_with_running_booster_is_still_completed PASSED

7 passed
```

Frontend: `npm run lint` ✓, `npm run build` ✓

---

## Why This Prevents Recurrence

1. **Test guards**: `test_booster_must_not_set_running_booster_status` fails if booster code contains `status="running_booster"`
2. **Structural separation**: Booster uses completely separate fields
3. **UI unchanged**: Frontend still gates on `job.status`, which now stays `completed`
4. **Clear semantics**: `booster_status` explicitly tracks only booster state

---

## Deployment Steps

1. Run migration 018 on production Supabase
2. Deploy backend to Railway
3. Deploy frontend to Vercel
4. Test: trigger booster on completed job, verify docs stay visible

---

## API Response Changes

Jobs now include booster fields (backward compatible - null for old jobs):

```json
{
  "id": "...",
  "status": "completed",
  "booster_status": "running",
  "booster_started_at": "2026-01-21T13:50:00Z",
  "booster_progress_percent": 50,
  "booster_error": null,
  ...
}
```
