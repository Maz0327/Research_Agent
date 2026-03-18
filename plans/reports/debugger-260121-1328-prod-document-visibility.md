# Debug Report: Production Document Visibility Investigation

**Date:** 2026-01-21 13:28
**Job ID:** `65c2f5f8-e57a-44f3-8b58-15a0a1b36d15`
**Issue:** UI shows NO documents despite worker completion and DB paths exist

---

## Step 0: Code Location Summary

### Frontend Configuration
- **API URL**: `frontend/lib/constants.ts:44-50`
  - Uses `NEXT_PUBLIC_API_URL` env var
  - Production: `https://your-api.up.railway.app`
  - Falls back to `http://localhost:8000`

### Backend Endpoints
- **GET /jobs**: `backend/app/routes/jobs_routes.py:1312-1371`
- **GET /jobs/{id}**: `backend/app/routes/jobs_routes.py:1374-1476`
- **GET /jobs/{id}/documents/{doc_type}**: `backend/app/routes/jobs_routes.py:944-1046`

### Key Models/Mapping
- **Artifacts Model**: `backend/models/job_record.py:8-40`
  - Has `doc_0_path`, `doc_1_path`, `doc_2_path`, `doc_3_path` fields
- **DB→Model Mapping**: `backend/state/impl/supabase_store.py:120-151`
  - `_record_from_db_row()` creates `Artifacts(**artifacts_data)`

### Frontend Document Detection
- **JobResults.tsx:124**: `hasStorageDocuments = artifacts?.doc_0_path || artifacts?.doc_1_path || artifacts?.doc_2_path`
- **JobCard.tsx:231-233**: Same check for `doc_0_path`, `doc_1_path`, `doc_2_path`

---

## Step 1: Production API Curl Commands

**Replace `YOUR_JWT_TOKEN` with a valid Supabase auth token.**

### 1.1 List Jobs (check if job appears with artifacts)
```bash
curl -s "https://your-api.up.railway.app/jobs" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" | jq '.jobs[] | select(.id == "65c2f5f8-e57a-44f3-8b58-15a0a1b36d15") | {id, status, artifacts}'
```

### 1.2 Get Job Detail (full artifacts dict)
```bash
curl -s "https://your-api.up.railway.app/jobs/65c2f5f8-e57a-44f3-8b58-15a0a1b36d15" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" | jq '{status, artifacts}'
```

### 1.3 Test Document Endpoint Directly
```bash
curl -s "https://your-api.up.railway.app/jobs/65c2f5f8-e57a-44f3-8b58-15a0a1b36d15/documents/doc_0" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

### Expected Fields in Response
Check if these keys exist in `artifacts`:
- `doc_0_path` (should be a storage path like `documents/{job_id}/doc_0.json`)
- `doc_1_path`
- `doc_2_path`
- OR legacy inline: `source_ledger`, `jump_start`, `semantic_brief`

---

## Step 2: Frontend Code Verification

### 2.1 Code in Repo Uses Correct Keys

**CONFIRMED**: Frontend code uses `doc_0_path` (NOT legacy `doc_paths`):

| File | Line | Code |
|------|------|------|
| `JobResults.tsx` | 124 | `hasStorageDocuments = artifacts?.doc_0_path \|\| ...` |
| `JobCard.tsx` | 231-233 | `job.artifacts?.doc_0_path \|\| ...` |
| `store/jobs.ts` | 130-136 | Interface has `doc_0_path?: string` |

**No references to `doc_paths` in frontend** (only in backend return values and tests).

### 2.2 Verify Production Frontend Build

**Option A: Check Vercel/deployment build output**
1. Go to Vercel dashboard → Deployments → Latest
2. Check "Build Output" for timestamp
3. Confirm commit SHA matches repo

**Option B: Inspect deployed JS bundle**
```bash
# Open browser DevTools → Network tab → filter by .js
# Search in Sources for "doc_0_path" - should find matches
```

**Option C: Add build info endpoint** (recommended for future)
```javascript
// Add to pages/api/build-info.ts
export default (req, res) => res.json({
  commit: process.env.VERCEL_GIT_COMMIT_SHA,
  buildTime: process.env.BUILD_TIME
});
```

---

## Step 3: Possible Root Causes

### Scenario A: Frontend Not Deployed (MOST LIKELY)
- **Symptom**: API returns `doc_0_path` but UI shows nothing
- **Evidence**: Code in repo is correct, but deployed build may be old
- **Fix**: Redeploy frontend (Vercel/hosting trigger)

### Scenario B: API Not Returning Fields
- **Symptom**: Curl shows `artifacts: null` or missing `doc_0_path`
- **Evidence**: Backend code looks correct but deployment may be stale
- **Fix**: Redeploy Railway API service

### Scenario C: Both Stale
- **Symptom**: Both API and frontend behave differently than repo code
- **Fix**: Redeploy both services

### Scenario D: Wrong Environment URL
- **Symptom**: Frontend pointing to wrong API instance
- **Evidence**: Check browser DevTools Network tab for API hostname
- **Fix**: Update `NEXT_PUBLIC_API_URL` in Vercel env vars

---

## Diagnostic Checklist

Run these checks to determine root cause:

| Check | Command/Action | Expected | Actual |
|-------|----------------|----------|--------|
| API returns doc_0_path | Curl 1.2 above | `"doc_0_path": "documents/..."` | ? |
| API doc endpoint works | Curl 1.3 above | Returns URL or data | ? |
| Frontend calls correct API | DevTools Network | `your-api.up.railway.app` | ? |
| Frontend has doc_0_path check | DevTools Sources search | Found in bundle | ? |
| Vercel build is recent | Vercel dashboard | Last 24h | ? |
| Railway deploy is recent | Railway dashboard | Last 24h | ? |

---

## Minimal Fix Steps

After running diagnostics:

### If API is returning fields correctly:
```bash
# 1. Trigger Vercel redeploy
# Option: Click "Redeploy" in Vercel dashboard
# OR: Push empty commit
git commit --allow-empty -m "chore: trigger frontend redeploy"
git push origin feature/vision-alignment-v1
```

### If API is NOT returning fields:
```bash
# 1. Check Railway deployment
# 2. Redeploy Railway service from dashboard
# OR: Push to trigger Railway CI
```

### If both need redeploy:
```bash
# Push triggers both CI pipelines
git commit --allow-empty -m "chore: trigger prod redeploy"
git push
```

---

## Optional Hardening

### Add Build Signature Logging
1. **Frontend**: Add `/api/build-info` endpoint returning commit SHA
2. **Backend**: Add `/health` or `/_build` endpoint with commit SHA
3. **Log on job fetch**: Log API version in browser console

### Example Frontend Build Info
```typescript
// pages/api/build-info.ts
export default function handler(req, res) {
  res.status(200).json({
    commit: process.env.VERCEL_GIT_COMMIT_SHA || 'local',
    branch: process.env.VERCEL_GIT_COMMIT_REF || 'unknown',
    timestamp: new Date().toISOString(),
  });
}
```

### Example Backend Build Info
```python
# backend/app/routes/health_routes.py
@router.get("/_build")
async def get_build_info():
    import os
    return {
        "commit": os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"),
        "deployed_at": os.getenv("RAILWAY_DEPLOYMENT_ID", "unknown"),
    }
```

---

## Summary

**Investigation Status**: Ready for production verification

**Next Steps**:
1. Run curl commands in Step 1 to check API response
2. Verify frontend build contains `doc_0_path` checks
3. Compare timestamps of deployed builds vs repo commits
4. Redeploy stale service(s)

**Unresolved Questions**:
- What is the actual API response for this job_id?
- When was the last Vercel/Railway deployment?
- Does the browser Network tab show API calls returning artifacts?
