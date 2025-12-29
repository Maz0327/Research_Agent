# Phase 01: Critical Fixes

## Context Links
- [Comprehensive Quality Audit](../reports/code-reviewer-251228-1459-comprehensive-quality-audit.md)
- [Frontend Stores Audit](../reports/tester-251228-1516-frontend-stores-audit.md)
- [Integration Clients Audit](../reports/code-reviewer-251228-1819-integration-clients-audit.md)

## Overview

| Field | Value |
|-------|-------|
| Priority | P1 (Critical) |
| Status | Pending |
| Effort | 4 hours |
| Risk | Low |

Immediate fixes blocking production stability. Must complete before other phases.

## Requirements

### Functional
1. Remove deprecated youtube-transcript-api dependency
2. Add fetch timeouts to all frontend API calls
3. Add error state fields to admin/jobs stores
4. Standardize rate limiting on integration clients

### Non-Functional
- No breaking changes to existing APIs
- All fixes backward compatible
- Tests must pass after changes

## Related Code Files

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/requirements.txt` | Modify | Remove youtube-transcript-api |
| `frontend/store/admin.ts` | Modify | Add error state, fetch timeout |
| `frontend/store/jobs.ts` | Modify | Add error state, fetch timeout |
| `frontend/lib/api-client.ts` | Create | Centralized fetch with timeout |
| `backend/integrations/gemini_client.py` | Modify | Add @with_rate_limit decorator |
| `backend/integrations/supadata_client.py` | Modify | Add @with_rate_limit decorator |
| `backend/integrations/whisper_client.py` | Modify | Add @with_rate_limit decorator |
| `backend/integrations/jina_reader_client.py` | Modify | Add @with_rate_limit decorator |
| `backend/integrations/google_drive_docs.py` | Modify | Add @with_rate_limit decorator |

## Implementation Steps

### Step 1: Remove youtube-transcript-api (10 min)

1. Check if youtube-transcript-api is in requirements:
   ```bash
   grep -n "youtube-transcript-api" backend/requirements.txt
   ```

2. Remove line if present (cloud incompatible per CLAUDE.md)

3. Verify no imports exist:
   ```bash
   grep -r "youtube_transcript_api" backend/
   ```

### Step 2: Create Frontend API Client (30 min)

Create centralized fetch utility with timeout:

```typescript
// frontend/lib/api-client.ts
import { DEFAULT_TIMEOUT } from './constants';

interface FetchOptions extends RequestInit {
  timeout?: number;
}

export async function apiFetch(
  endpoint: string,
  options: FetchOptions = {}
): Promise<Response> {
  const { timeout = DEFAULT_TIMEOUT, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(endpoint, {
      ...fetchOptions,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function authFetch(
  endpoint: string,
  token: string | null,
  options: FetchOptions = {}
): Promise<Response> {
  return apiFetch(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
}
```

### Step 3: Add Error State to Admin Store (30 min)

File: `frontend/store/admin.ts`

1. Add error field to AdminState interface (~line 106):
   ```typescript
   interface AdminState {
     // ... existing fields
     error: string | null;
   }
   ```

2. Update default state (~line 109):
   ```typescript
   error: null,
   ```

3. Update fetchStats to set error (~line 189-194):
   ```typescript
   } catch (error) {
     const errorMessage = error instanceof Error ? error.message : 'Failed to fetch stats';
     set({ isLoadingStats: false, error: errorMessage });
   }
   ```

4. Repeat for fetchUsers, fetchJobs, fetchErrorLogs

### Step 4: Add Error State to Jobs Store (30 min)

File: `frontend/store/jobs.ts`

1. Add error field to JobsState interface (~line 40):
   ```typescript
   interface JobsState {
     // ... existing fields
     error: string | null;
   }
   ```

2. Fix 401 handling (~line 64-67):
   ```typescript
   if (response.status === 401) {
     set({ jobs: [], isLoading: false, error: 'Session expired. Please log in again.' });
     return;
   }
   ```

3. Wrap response.json() in try/catch (~line 74):
   ```typescript
   let data;
   try {
     data = await response.json();
   } catch {
     throw new Error('Invalid response format');
   }
   ```

### Step 5: Add Rate Limiting to Integration Clients (1h)

Add `@with_rate_limit` decorator to missing clients:

1. **gemini_client.py** (~line 58):
   ```python
   from backend.utils.rate_limiter import with_rate_limit

   @with_rate_limit("gemini")
   def generate(self, prompt: str, ...):
   ```

2. **supadata_client.py** (~line 87):
   ```python
   @with_rate_limit("supadata")
   def get_transcript(self, url: str, ...):
   ```

3. **whisper_client.py** (~line 109):
   ```python
   @with_rate_limit("whisper")
   def transcribe_youtube(self, video_id: str, ...):
   ```

4. **jina_reader_client.py** (~line 30):
   ```python
   @with_rate_limit("jina")
   def fetch(self, url: str, ...):
   ```

5. **google_drive_docs.py** (~line 201):
   ```python
   @with_rate_limit("google_drive")
   def create_research_packet(...):
   ```

### Step 6: Add Return Type Hints (30 min)

Fix missing return type hints in integration clients:

```python
# perplexity_client.py
def search(self, query: str) -> dict[str, Any] | None:

# tavily_client.py
def web_search(self, query: str) -> list[dict[str, Any]]:

# openai_client.py
def plan_job(self, prompt: str) -> dict[str, Any]:
```

### Step 7: Verify and Test (30 min)

1. Run frontend lint:
   ```bash
   cd frontend && npm run lint
   ```

2. Run frontend build:
   ```bash
   npm run build
   ```

3. Run backend tests:
   ```bash
   cd /Users/maz/Documents/GitHub/Research_Agent && pytest
   ```

## Todo List

- [ ] Remove youtube-transcript-api from requirements.txt
- [ ] Create frontend/lib/api-client.ts
- [ ] Add error field to AdminState
- [ ] Update admin store fetch methods with error handling
- [ ] Add error field to JobsState
- [ ] Fix 401 handling in jobs store
- [ ] Add try/catch for JSON parsing in jobs store
- [ ] Add @with_rate_limit to gemini_client.py
- [ ] Add @with_rate_limit to supadata_client.py
- [ ] Add @with_rate_limit to whisper_client.py
- [ ] Add @with_rate_limit to jina_reader_client.py
- [ ] Add @with_rate_limit to google_drive_docs.py
- [ ] Add return type hints to integration clients
- [ ] Run frontend lint/build
- [ ] Run backend pytest

## Success Criteria

- [ ] No youtube-transcript-api in requirements.txt
- [ ] All frontend fetch calls use apiFetch with timeout
- [ ] Admin and jobs stores have error state fields
- [ ] All integration clients have @with_rate_limit
- [ ] Frontend build passes
- [ ] Backend pytest passes

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rate limit decorator breaks existing flow | Low | Medium | Test each client after adding decorator |
| Timeout too aggressive | Low | Low | Use 30s default (already in constants) |
| Error state breaks UI | Low | Low | Error field is additive, not breaking |

## Next Steps

After completing this phase:
1. Proceed to Phase 2 (Backend Modularization) or Phase 3 (Frontend Improvements)
2. Re-run quality audit to verify fixes
