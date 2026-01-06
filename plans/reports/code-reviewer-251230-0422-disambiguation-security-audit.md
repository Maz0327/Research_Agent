# Code Review: Disambiguation Feature Security Audit

## Scope
- Files: `jobs_routes.py`, `worker.py`, `planning.py`, `DisambiguationPanel.tsx`, `jobs.ts`
- Lines analyzed: ~850
- Focus: Recently implemented disambiguation feature

## Overall Assessment
**Security Grade: B- (needs fixes)**

Disambiguation feature functional but has **critical security gaps** in persistence layer and potential race conditions. No authentication bypasses or SQL injection risks found. Input validation mostly solid but missing key parameter support in update_job interface.

---

## Critical Issues

### 1. **[CRITICAL] Unsupported Parameter in update_job() Call**
**File:** `backend/app/routes/jobs_routes.py:402-407`
**Severity:** CRITICAL
**Impact:** Feature silently fails - selected_interpretations never persisted

```python
# Line 402-407: Parameter not in interface signature
update_job(
    job_id,
    selected_interpretations=indices,  # ❌ NOT in JobStore.update_job()
    status="queued",
    stage="resuming",
)
```

**Root Cause:**
- `JobStore.update_job()` interface (lines 39-75 in `interface.py`) missing `selected_interpretations` parameter
- `SupabaseJobStore._patch_job()` would receive this in kwargs and **silently drop it**
- Job resumes without knowing which interpretations user selected

**Exploit Scenario:**
1. User selects interpretation #2
2. API accepts request, returns 200 OK
3. `update_job()` ignores `selected_interpretations=2`, only sets status/stage
4. Worker loads job, sees `selected_interpretations=None`
5. Falls through to normal pipeline instead of disambiguated flow
6. User gets wrong research output

**Fix Required:**
```python
# Add to interface.py JobStore.update_job():
interpretations: Optional[list[dict]] = None,
selected_interpretations: Optional[list[int]] = None,

# Add to supabase_store.py _update_job_simple():
if selected_interpretations is not None:
    payload["selected_interpretations"] = selected_interpretations
if interpretations is not None:
    payload["interpretations"] = interpretations
```

---

### 2. **[HIGH] Race Condition in Job State Transition**
**File:** `backend/app/routes/jobs_routes.py:402-411`
**Severity:** HIGH
**Impact:** Double-processing, duplicate Celery tasks

```python
# Line 402-411: No transaction or lock
update_job(job_id, ...)           # Update DB
run_research_job.delay(job_id, prompt)  # Enqueue task
```

**Attack Vector:**
1. User clicks "Research Selected" twice rapidly
2. Both requests pass `status != "disambiguating"` check (line 374)
3. Both calls `update_job()` + `run_research_job.delay()`
4. Two Celery workers process same job simultaneously
5. Race condition in `_run_disambiguated_job()` reading/writing context

**Proof of Concept:**
```bash
# Concurrent requests with same job_id
curl -X POST /jobs/{id}/select-interpretation & \
curl -X POST /jobs/{id}/select-interpretation
```

**Fix Required:**
```python
# Use atomic compare-and-swap
result = client.rpc("atomic_job_state_transition", {
    "p_job_id": job_id,
    "p_expected_status": "disambiguating",
    "p_new_status": "queued",
    "p_selected_interpretations": indices,
}).execute()

if not result.data:
    raise HTTPException(409, "Job already resumed")
```

---

### 3. **[HIGH] Missing Idempotency Check in Celery Re-enqueue**
**File:** `backend/app/routes/jobs_routes.py:411`
**Severity:** HIGH
**Impact:** Duplicate pipeline runs, wasted API costs

```python
# Line 411: No check if task already exists
run_research_job.delay(job_id, prompt)
```

**Issue:**
- Celery task uses job_id as task_id (default behavior)
- If user spams "Research All" button, creates multiple tasks
- Each task processes same job, causing:
  - Duplicate API calls to OpenAI/Perplexity ($$$)
  - Race conditions in Drive upload
  - Confusing job status (multiple workers updating same record)

**Fix Required:**
```python
# Use job_id as task_id for idempotency
run_research_job.apply_async(
    args=[job_id, prompt],
    task_id=f"research_{job_id}",  # Prevents duplicates
)
```

---

## High Priority Findings

### 4. **[HIGH] No Index Bounds Validation in _run_disambiguated_job**
**File:** `backend/worker.py:288-291`
**Severity:** HIGH
**Impact:** Silent data corruption, unexpected behavior

```python
# Line 288-291: Only logs warning, continues processing
for i, idx in enumerate(selected_indices):
    if idx >= len(interpretations):
        ctx.add_warning(f"Invalid interpretation index: {idx}")
        continue  # ❌ Keeps processing other indices
```

**Issue:**
- If `selected_interpretations=[0, 999]` and job has 3 interpretations:
  - Index 999 skipped silently
  - Job completes with partial results
  - User doesn't know interpretation #2 was missing

**Attack Scenario:**
- Malicious client sends `indices=[0, 1, 2, 3, ..., 100]`
- API validates bounds (line 393-396) BUT:
- Attacker could modify DB directly if they compromise service role key
- Worker would log 97 warnings, process 3 valid indices
- Fills logs, hides real errors

**Fix Required:**
```python
# Fail fast on invalid indices
invalid = [i for i in selected_indices if i >= len(interpretations)]
if invalid:
    logger.error(f"Invalid indices {invalid} for job {job_id}")
    update_job(job_id, status="failed",
               error=f"Invalid interpretation indices: {invalid}")
    return {"status": "failed", "error": "Invalid indices"}
```

---

### 5. **[HIGH] Missing CSRF/Origin Validation on State-Changing Endpoint**
**File:** `backend/app/routes/jobs_routes.py:338-430`
**Severity:** HIGH
**Impact:** CSRF attack potential

**Current State:**
- Endpoint uses `@limiter.limit()` but no CSRF token check
- No Origin/Referer header validation
- Bearer token alone insufficient for state-changing POST

**Attack Scenario:**
```html
<!-- Malicious site tricks authenticated user -->
<script>
fetch('https://api.research-agent.com/jobs/{victim_job_id}/select-interpretation', {
  method: 'POST',
  credentials: 'include',  // Sends auth cookie
  headers: {'Authorization': 'Bearer ' + stolenToken},
  body: JSON.stringify({indices: [0]})
});
</script>
```

**Fix Required:**
```python
# Add CORS origin check
from starlette.middleware.cors import CORSMiddleware
allowed_origins = ["https://research-agent.vercel.app"]

# In route:
if request.headers.get("origin") not in allowed_origins:
    raise HTTPException(403, "Invalid origin")
```

---

### 6. **[HIGH] No Rate Limit on select-interpretation Endpoint**
**File:** `backend/app/routes/jobs_routes.py:339`
**Severity:** MEDIUM-HIGH
**Impact:** API abuse, cost inflation

```python
# Line 339: Reuses jobs_create limit (10/hour)
@limiter.limit(RATE_LIMITS["jobs_create"])
```

**Issue:**
- User can cycle interpretations 10 times/hour
- Each cycle triggers full pipeline (up to $15 in API costs)
- Attacker could drain budget: 10 cycles × $15 = $150/hour

**Recommendation:**
```python
# Add dedicated limit
RATE_LIMITS["jobs_select_interpretation"] = "3/hour"  # Max 3 retries/hour
```

---

## Medium Priority Improvements

### 7. **[MEDIUM] Incomplete Authorization in Anonymous User Flow**
**File:** `backend/app/routes/jobs_routes.py:363-371`
**Severity:** MEDIUM
**Impact:** Inconsistent security policy

```python
# Lines 363-371: Auth required for owned jobs
if job.user_id is not None:
    if user is None:
        raise HTTPException(401, "Authentication required")
    if job.user_id != user.user_id:
        raise HTTPException(403, "Access denied")
```

**Gap:**
- Anonymous jobs (`user_id=None`) can be modified by **anyone** who knows job_id
- UUIDs are predictable (v4 = 122 bits entropy, but enumerable)
- No check if job was created by current session

**Fix:**
```python
# Add session tracking for anonymous jobs
if job.user_id is None:
    # Check if job_id in user's session
    session_jobs = request.session.get("job_ids", [])
    if job_id not in session_jobs:
        raise HTTPException(403, "Not your job")
```

---

### 8. **[MEDIUM] Celery Task Orphaning on Rapid Status Changes**
**File:** `backend/app/routes/jobs_routes.py:411`
**Severity:** MEDIUM
**Impact:** Wasted resources, zombie workers

**Scenario:**
1. User selects interpretation → Task A enqueued
2. User cancels job (line 323) → `celery_app.control.revoke(job_id)`
3. Revoke uses job_id as task_id, but Task A has different ID
4. Task A keeps running, wastes API budget

**Fix:**
```python
# Store celery task_id in DB
task = run_research_job.apply_async(args=[job_id, prompt])
update_job(job_id, celery_task_id=task.id)

# In cancel endpoint:
job = get_job(job_id)
if job.celery_task_id:
    celery_app.control.revoke(job.celery_task_id, terminate=True)
```

---

### 9. **[MEDIUM] Frontend Stores Sensitive Data in Local State**
**File:** `frontend/store/jobs.ts:230`
**Severity:** MEDIUM
**Impact:** XSS exposure risk

```typescript
// Line 230: Interpretations cleared but job object persists
interpretations: undefined
```

**Issue:**
- Job object with potentially sensitive prompts kept in Zustand store
- If XSS vulnerability exists elsewhere, attacker could read store
- No encryption for local storage (if persistence added later)

**Recommendation:**
- Clear job object entirely after selection
- Don't store full job in frontend state, use IDs only

---

### 10. **[MEDIUM] Missing Input Sanitization on Interpretation Labels**
**File:** `backend/pipeline/stages/planning.py:44-53`
**Severity:** MEDIUM
**Impact:** Log injection, XSS in logs

```python
# Line 45: interpretations come from LLM without sanitization
interpretations = result.get("interpretations", [])
logger.info(f"Topic is ambiguous, {len(interpretations)} interpretations found")
```

**Issue:**
- LLM could return malicious interpretation label:
  - `{"label": "\n[ERROR] ADMIN ACCESS GRANTED\n", "description": "..."}`
  - Injects fake log entries
  - If logs displayed in web UI, potential XSS

**Fix:**
```python
# Validate interpretation structure
for interp in interpretations:
    if not isinstance(interp.get("label"), str):
        raise ValueError("Invalid interpretation format")
    # Strip control characters
    interp["label"] = re.sub(r'[\x00-\x1F\x7F]', '', interp["label"])
    interp["label"] = interp["label"][:100]  # Max length
```

---

## Low Priority Suggestions

### 11. **[LOW] No Cost Budget Check Before Re-enqueuing**
**File:** `backend/app/routes/jobs_routes.py:411`
**Severity:** LOW
**Impact:** Cost overruns

**Suggestion:**
```python
# Check user's remaining budget
user_budget = get_user_budget(user.user_id)
estimated_cost = len(indices) * 10  # $10 per interpretation
if estimated_cost > user_budget:
    raise HTTPException(402, "Insufficient budget")
```

---

### 12. **[LOW] Missing Audit Log for Disambiguation Choices**
**File:** `backend/app/routes/jobs_routes.py:413-424`
**Severity:** LOW
**Impact:** Forensics gap

**Current:** Logs selection event but not:
- Which interpretations were **rejected**
- Time taken to make selection (UX metric)
- Whether user selected "all" vs manual selection

**Recommendation:**
```python
logger.info(
    "Disambiguation resolved",
    extra={
        "selected": selected_labels,
        "rejected": [interp["label"] for i, interp in enumerate(job.interpretations)
                     if i not in indices],
        "selection_time_seconds": (now - job.created_at).total_seconds(),
        "selection_mode": "all" if len(indices) == len(job.interpretations) else "manual",
    }
)
```

---

### 13. **[LOW] Frontend Lacks Optimistic UI Rollback**
**File:** `frontend/store/jobs.ts:227-233`
**Severity:** LOW
**Impact:** UX confusion

```typescript
// Line 227-233: Sets status="queued" before API confirms
set((state) => ({
  jobs: state.jobs.map((job) =>
    job.id === jobId
      ? { ...job, status: 'queued' as const, interpretations: undefined }
      : job
  ),
}));
```

**Issue:**
- If API fails (403, 500), UI shows "queued" but job still "disambiguating"
- User doesn't know to retry

**Fix:**
```typescript
// Store original state for rollback
const originalJob = get().jobs.find(j => j.id === jobId);
try {
  // optimistic update
  set(...);
  await fetch(...);
} catch (err) {
  // rollback
  set((state) => ({
    jobs: state.jobs.map(j => j.id === jobId ? originalJob : j)
  }));
  throw err;
}
```

---

### 14. **[LOW] No Metrics Collection on Disambiguation Patterns**
**File:** `backend/app/routes/jobs_routes.py`
**Severity:** LOW
**Impact:** Missed product insights

**Recommendation:**
```python
# Track selection patterns
metrics.increment("disambiguation.selections", {
    "num_options": len(job.interpretations),
    "num_selected": len(indices),
    "mode": job.config_json.get("mode"),
})
```

---

## Positive Observations

✅ **Good:** Input validation on `SelectInterpretationRequest` (lines 88-105 in `job.py`)
✅ **Good:** UUID format validation before DB calls (line 354)
✅ **Good:** Authorization checks consistent with existing patterns
✅ **Good:** Error messages sanitized, don't leak internal paths
✅ **Good:** Rate limiting applied to endpoint
✅ **Good:** Audit logging includes user context
✅ **Good:** Frontend TypeScript types prevent invalid data shapes

---

## Recommended Actions (Priority Order)

### Must Fix (Before Production)
1. **Add `selected_interpretations` to `JobStore.update_job()` interface** (Issue #1)
2. **Implement atomic state transition for disambiguation** (Issue #2)
3. **Add idempotency to Celery task re-enqueue** (Issue #3)
4. **Fail fast on invalid interpretation indices** (Issue #4)

### Should Fix (This Sprint)
5. Add CSRF/origin validation (Issue #5)
6. Create dedicated rate limit for select-interpretation (Issue #6)
7. Implement session-based auth for anonymous jobs (Issue #7)
8. Store celery_task_id for proper revocation (Issue #8)

### Nice to Have (Backlog)
9. Sanitize LLM-generated interpretation labels (Issue #10)
10. Add cost budget checks (Issue #11)
11. Enhance audit logging (Issue #12)
12. Implement optimistic UI rollback (Issue #13)

---

## Metrics

**Type Coverage:** Not measured (mypy found unrelated issues)
**Linting:** ✅ Frontend passes (ESLint clean)
**Build:** Not tested
**Security:** 14 findings (1 critical, 5 high, 4 medium, 4 low)

---

## Unresolved Questions

1. **Database schema:** Does `jobs` table have `selected_interpretations` and `interpretations` columns? Migration status unknown.
2. **Celery task routing:** Are disambiguation tasks isolated from normal queue? Could cause head-of-line blocking.
3. **Cost accounting:** Are interpretation costs tracked separately? Multi-interpretation jobs could exceed budget.
4. **Concurrent job limit:** Can user run multiple jobs simultaneously? Could spam select-interpretation on stale jobs.
5. **Frontend polling:** Does JobCard poll for status updates? Could miss transition from "disambiguating" to "queued".

---

**Report Generated:** 2025-12-30 04:22 UTC
**Reviewer:** code-reviewer agent
**Next Steps:** Address critical issues #1-4 before deploying to production
