# Dashboard Issues Investigation Report

**Date:** 2026-01-24
**Investigator:** Debugger Agent
**Issues:** 1) Job titles show "untitled" on dashboard, 2) Clicking job goes to jobs page instead of job detail

---

## Executive Summary

**Root Causes Identified:**
1. **"Untitled" Issue:** Backend returns `null` for `job.title` field - never populated during job creation/processing
2. **Navigation Issue:** Dashboard card navigation logic routes to `/queue` tabs instead of `/jobs/{id}` detail page

**Impact:**
- Users cannot identify jobs by meaningful titles on dashboard
- Users must go through queue page to access individual job details (extra click)

**Fix Complexity:** Low - Both are simple frontend/backend updates

---

## Issue #1: Job Titles Show "Untitled"

### Root Cause

Backend API endpoint `GET /jobs` returns `job.title` field but never sets it.

**Evidence:**

1. **Frontend Display Logic** (`/frontend/components/dashboard/DashboardJobCard.tsx:134`):
```tsx
{job.title || 'Untitled Job'}
```
Falls back to "Untitled Job" when `job.title` is `null/undefined`.

2. **Backend API Response** (`/backend/app/routes/jobs_routes.py:1693`):
```python
"title": job.title,  # Always None - never set
```

3. **Job Creation** (`/backend/app/routes/jobs_routes.py:581-614`):
Mixed-input endpoint creates job with `config_json` containing `topic` but does NOT set `title` field:
```python
config_json = {
    "topic": job_request.topic,
    "job_type": "mixed_input",
    # ... no title field set
}
job = create_job(config_json=config_json, user_id=user_id)
```

4. **Database Model** (`/backend/models/job_record.py:173`):
```python
title: Optional[str] = Field(None, description="AI-generated short title for the job")
```
Field exists but defaults to `None`.

5. **Pipeline Context** (`/backend/pipeline/context.py:27`):
```python
short_title: str = ""
```
Context has `short_title` but search shows it's never assigned.

### Why Title Is Never Set

- Job creation endpoints (`mixed-input`, `video-analysis`, etc.) pass `topic` in `config_json` but don't populate `title`
- Pipeline stages don't call `update_job(title=...)` to set title
- No stage generates AI title from topic/sources
- Field was designed for "AI-generated short title" but generation step missing

### Current Workaround in Code

Frontend uses `job.title || job.prompt` in some places:
- `/frontend/pages/jobs/[id].tsx:357`: `title={job.title || job.prompt}`
- `/frontend/store/jobs.ts:648,697,762,817`: Sets local `prompt` field during job creation

However, dashboard card only checks `job.title`, not `prompt`.

---

## Issue #2: Clicking Job Goes to Queue Page

### Root Cause

Dashboard card navigation routes to queue tabs instead of job detail page.

**Evidence:**

`/frontend/components/dashboard/DashboardJobCard.tsx:94-104`:
```tsx
const handleClick = () => {
  if (isActive) {
    router.push('/queue?tab=active');      // ❌ Should go to /jobs/{id}
  } else if (isCompleted) {
    router.push('/queue?tab=completed');   // ❌ Should go to /jobs/{id}
  } else if (isFailed) {
    router.push('/queue?tab=failed');      // ❌ Should go to /jobs/{id}
  } else {
    router.push(`/jobs/${job.id}`);        // ✅ This is correct
  }
};
```

### Why Navigation Is Wrong

- Logic routes **all** jobs to queue tabs by status
- Only `else` case (no status match) goes to job detail
- Likely design intent: "show all active/completed/failed jobs together"
- But user expectation: "clicking a job should show THAT job"

### Affected Jobs

- Running jobs → `/queue?tab=active`
- Queued jobs → `/queue?tab=active`
- Completed jobs → `/queue?tab=completed`
- Failed jobs → `/queue?tab=failed`

Only edge case jobs (cancelled, disambiguating) would reach the detail page fallback.

---

## Technical Details

### Files Affected

**Issue #1 (Untitled):**
- `/backend/app/routes/jobs_routes.py:1693` - Returns `job.title` (always None)
- `/backend/models/job_record.py:173` - Title field definition
- `/backend/pipeline/*` - No stage sets title
- `/frontend/components/dashboard/DashboardJobCard.tsx:134` - Display logic
- `/frontend/store/jobs.ts:205,817` - Type definition with optional title

**Issue #2 (Navigation):**
- `/frontend/components/dashboard/DashboardJobCard.tsx:94-104` - Navigation logic

### Job Detail Page Exists

Confirmed working job detail page at `/frontend/pages/jobs/[id].tsx` with:
- Artifact cards
- Active task banners
- Iteration controls
- Progress indicators

Users just can't navigate to it from dashboard.

---

## Recommended Solutions

### Fix #1: Populate Job Title

**Option A - Use Topic as Title (Quick Fix):**
```python
# backend/app/routes/jobs_routes.py:1690-1693
jobs_data.append({
    "id": job.job_id,
    "prompt": prompt,
    "title": job.title or prompt,  # Fallback to topic/prompt
    ...
})
```

**Option B - Generate AI Title (Proper Fix):**
1. Add title generation stage in pipeline (call LLM to create 3-5 word summary)
2. Call `update_job(job_id, title=generated_title)` after source identity stage
3. Store in database

**Recommendation:** Option A for immediate fix, Option B for better UX

### Fix #2: Navigate to Job Detail

```tsx
// frontend/components/dashboard/DashboardJobCard.tsx:94-104
const handleClick = () => {
  router.push(`/jobs/${job.id}`);  // Always go to detail page
};
```

Remove all status-based routing. User can see full job details regardless of status.

---

## Supporting Evidence - Data Flow

```
Job Creation (mixed-input):
  POST /jobs/mixed-input
    → create_job(config_json={topic, job_type, ...})
    → JobRecord(title=None)  ❌ Never set
    → Database stores NULL

Job Retrieval:
  GET /jobs
    → list_jobs()
    → jobs_data["title"] = job.title  ❌ Still None
    → Frontend receives null

Dashboard Display:
  <DashboardJobCard job={job} />
    → {job.title || 'Untitled Job'}  ❌ Shows "Untitled Job"
    → onClick → router.push('/queue?tab=...')  ❌ Wrong page
```

---

## Unresolved Questions

1. **Title Generation Logic:** Should title be AI-generated or just use topic? If AI-generated, which stage is appropriate?
2. **Title Length:** Max character limit for display in UI cards?
3. **Navigation Intent:** Was queue-tab routing intentional for dashboard overview? Or bug?
4. **Backward Compatibility:** Will existing jobs (with `title=null`) cause issues after fix?

---

## Next Steps

1. Confirm fix approach with owner
2. Implement title population (Option A or B)
3. Update navigation logic to route to detail page
4. Test with existing jobs (null titles)
5. Verify queue page still accessible via main nav
