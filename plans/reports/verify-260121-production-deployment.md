# Production Deployment Verification Report

**Date:** 2026-01-21
**Scope:** Verify production is running latest code, frontend hits expected API

---

## 1. Deployment Signatures

### Backend Health Endpoint

| Aspect | Value | Evidence |
|--------|-------|----------|
| **Endpoint** | `GET /health` | `main.py:199-224` |
| **Response** | `{status, version, service, dependencies}` | Static response |
| **Version** | `"0.1.0"` (hardcoded) | `main.py:204` |
| **Service** | `"research-agent-api"` | `main.py:205` |
| **Dependencies** | `{supabase, redis, celery}` status | Checked at health call |

**Limitation:** No `BUILD_ID` or `COMMIT_SHA` in codebase. Version is static `"0.1.0"`.

### Startup Validation Logs

**Location:** `main.py:148-192`

Logs on startup:
- `Starting Research Agent API (environment)...`
- `CORS origins: [...]`
- Supabase connection status
- Redis connection status
- Database connectivity test

---

## 2. Frontend API Base URL Configuration

### Source Chain

```
.env.example → NEXT_PUBLIC_API_URL
     ↓
constants.ts:44 → rawApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
     ↓
constants.ts:47-50 → API_URL (HTTPS enforced in production)
     ↓
api-client.ts:10 → import { API_URL } from './constants'
     ↓
api-client.ts:38 → url = `${API_URL}${endpoint}`
```

### Environment Variables

| Variable | Default | Production |
|----------|---------|------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | `https://api-production-1c52.up.railway.app` |

### HTTPS Enforcement

```typescript
// constants.ts:47-50
export const API_URL =
  process.env.NODE_ENV === 'production' && rawApiUrl.startsWith('http://')
    ? rawApiUrl.replace('http://', 'https://')
    : rawApiUrl;
```

In production, even if `http://` is set, it auto-upgrades to `https://`.

---

## 3. Completion Gating Logic

### JobResults.tsx:122-131

```typescript
// Completion status detection
const isCompleted = ['completed', 'completed_with_warnings', 'failed_insufficient'].includes(status);

// Document availability checks
const hasInlineDocuments = artifacts?.source_ledger || artifacts?.jump_start || artifacts?.semantic_brief;
const hasStorageDocuments = artifacts?.doc_0_path || artifacts?.doc_1_path || artifacts?.doc_2_path;
const hasDocuments = hasInlineDocuments || hasStorageDocuments;

// Action button gating (Booster, Producer Packet)
const canTriggerActions = status === 'completed' || status === 'completed_with_warnings';
```

### Display Condition

```typescript
// JobResults.tsx:133
if (isCompleted && hasDocuments) {
  // Show document accordions
}
```

**Conclusion:** Documents render when:
1. Status is `completed`, `completed_with_warnings`, or `failed_insufficient` AND
2. At least one doc path OR inline document exists

---

## 4. Jobs List Route Artifacts Inclusion

### Endpoint: `GET /jobs`

**Location:** `jobs_routes.py:1312-1371`

### Artifacts Handling

```python
# jobs_routes.py:1330-1334
artifacts_dict = None
if job.artifacts:
    artifacts_dict = job.artifacts.model_dump(exclude_none=True)
    if not artifacts_dict:
        artifacts_dict = None

# jobs_routes.py:1364
jobs_data.append({
    ...
    "artifacts": artifacts_dict,
    ...
})
```

**Verdict:** Artifacts ARE included in `/jobs` list response when they exist.

---

## 5. Production Verification Checklist

### A. Backend API Verification

| Check | Command/URL | Expected |
|-------|-------------|----------|
| Health check | `GET https://api-production-1c52.up.railway.app/health` | `{"status": "healthy", "version": "0.1.0", ...}` |
| Jobs list | `GET /jobs` (authenticated) | Returns `{"jobs": [...]}` with `artifacts` field |
| Document fetch | `GET /jobs/{id}/documents/doc_0` | Returns `{"url": "..."}` or `{"markdown": "..."}` |

### B. Frontend Verification

| Check | How to Verify |
|-------|---------------|
| API URL | Browser DevTools → Network → Check request URL prefix |
| HTTPS enforcement | Should show `https://api-production...` not `http://` |
| Console check | `window.__NEXT_DATA__.props.pageProps` or inspect network |

### C. End-to-End Verification

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create new job | Job starts, status updates via polling |
| 2 | Wait for completion | Status becomes `completed` or `completed_with_warnings` |
| 3 | Check job list | Job shows with `artifacts` containing `doc_0_path`, `doc_1_path`, `doc_2_path` |
| 4 | Expand Doc 0 accordion | Content loads from storage via signed URL |
| 5 | Click PDF download | PDF generates and downloads |
| 6 | Click "Generate Producer Packet" | Doc 3 appears after generation |

### D. Railway Deployment Verification

| Check | Location |
|-------|----------|
| Latest deploy | Railway dashboard → Deployments → Check commit SHA |
| Worker running | Railway logs → Filter by worker service |
| Environment vars | Railway settings → `NEXT_PUBLIC_API_URL` should match API service URL |

---

## 6. Potential Issues to Check

### If Documents Don't Show

1. **Check artifacts in API response:**
   ```bash
   curl -H "Authorization: Bearer $TOKEN" https://api-production-1c52.up.railway.app/jobs
   ```
   Look for `doc_0_path`, `doc_1_path`, `doc_2_path` in artifacts.

2. **Check browser console:** Look for fetch errors to `/jobs/{id}/documents/doc_X`

3. **Check signed URL fetch:** If signed URL returns 403, Supabase bucket permissions may be wrong

### If PDF Fails

1. Check browser console for `html2pdf` errors
2. Verify markdown content loaded before PDF button enabled

---

## Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| Backend health endpoint | Exists | `GET /health` returns version |
| Frontend API URL config | Correct | `NEXT_PUBLIC_API_URL` → `constants.ts` → `api-client.ts` |
| HTTPS enforcement | Yes | Production auto-upgrades HTTP to HTTPS |
| Completion gating | Correct | `isCompleted` checks 3 statuses |
| Artifacts in /jobs | Yes | `job.artifacts.model_dump()` included |
| Document accordions | Correct | Shows when `isCompleted && hasDocuments` |

**No code issues found. Verification requires manual production check with the checklist above.**

---

*Report generated: 2026-01-21*
