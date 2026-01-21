# Frontend Stores Audit - Action Items

**Priority**: CRITICAL - 4 blocking issues identified
**Estimated Effort**:
- Critical fixes: 6-8 hours
- High priority: 8-10 hours
- Medium priority: 10-12 hours

---

## CRITICAL - Deploy Blocker (IMMEDIATE)

### 1. Missing Timeout on Fetch Requests
**File**: admin.ts (142-163), jobs.ts, settings.ts
**Issue**: Fetch requests can hang indefinitely
**Effort**: 3 hours
**Risk**: High - production app freezes

**Fix Pattern**:
```typescript
// Create reusable fetch with timeout
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}
```

**Files to Update**:
- admin.ts: Replace authFetch with timeout-aware version
- jobs.ts: Wrap all fetch calls (lines 74, 106, 154, 195)
- settings.ts: Wrap all fetch calls (lines 127, 161, 204, 241)

**Tests Needed**:
- Test request timeout after 30 seconds
- Test error state set when timeout occurs
- Test UI shows timeout error message

---

### 2. No Error State in Admin/Jobs Stores
**Files**: admin.ts (106-138), jobs.ts (40-49)
**Issue**: Errors silently lost, UI cannot display them
**Effort**: 2 hours
**Risk**: Medium - user confusion

**Current**:
```typescript
interface AdminState {
  stats: AdminStats | null;
  users: AdminUser[];
  // ... NO ERROR FIELD
}
```

**Fix**:
```typescript
interface AdminState {
  stats: AdminStats | null;
  users: AdminUser[];
  error: string | null; // ADD THIS
}
```

**Also Update**:
- Initialize error: null in default state
- Set error in all catch blocks:
  ```typescript
  catch (error) {
    set({
      isLoadingStats: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
  ```
- Add clearError action:
  ```typescript
  clearError: () => set({ error: null }),
  ```

**Tests Needed**:
- Test error set when API fails
- Test error cleared when new action starts
- Test error displayed in UI

---

### 3. JSON Parse Errors Not Caught
**Files**: admin.ts (162), jobs.ts (85), settings.ts (142, 175, 217, 255)
**Issue**: Malformed JSON crashes without fallback
**Effort**: 2 hours
**Risk**: High - unexpected crash

**Current**:
```typescript
const data = await response.json();
```

**Fix**:
```typescript
const data = await response.json().catch(() => {
  throw new Error('Invalid response format from server');
});
```

**Or Use Wrapper**:
```typescript
async function parseJSON(response: Response) {
  try {
    return await response.json();
  } catch (e) {
    throw new Error(`Invalid JSON response: ${response.status}`);
  }
}
```

**Files to Update**: 6 locations across 3 files

**Tests Needed**:
- Test malformed JSON response
- Test error message displayed
- Test state not corrupted

---

### 4. Module-Level Global Timeout
**File**: settings.ts (85-86, 178-187)
**Issue**: Fragile global state, breaks with multiple instances
**Effort**: 1 hour
**Risk**: Medium - edge case issues

**Current**:
```typescript
let saveSuccessTimeoutId: ReturnType<typeof setTimeout> | null = null;

// In action
if (saveSuccessTimeoutId) {
  clearTimeout(saveSuccessTimeoutId);
}
saveSuccessTimeoutId = setTimeout(() => {
  set({ saveSuccess: false });
  saveSuccessTimeoutId = null;
}, 3000);
```

**Fix**: Move timeout to store state
```typescript
interface SettingsState {
  settings: UserSettings | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  saveSuccess: boolean;
  saveSuccessTimeoutId: ReturnType<typeof setTimeout> | null; // ADD THIS
  // ... rest
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  // ... default state
  saveSuccessTimeoutId: null,

  updateSettings: async (updates: Partial<UserSettings>) => {
    // Clear existing timeout
    const { saveSuccessTimeoutId: existingId } = get();
    if (existingId) clearTimeout(existingId);

    // ... rest of implementation

    const timeoutId = setTimeout(() => {
      set({ saveSuccess: false, saveSuccessTimeoutId: null });
    }, 3000);

    set({ saveSuccessTimeoutId: timeoutId });
  },
}));
```

**Tests Needed**:
- Test multiple concurrent updates
- Test timeout cleanup on unmount

---

## HIGH PRIORITY (Sprint 1 - Before Release)

### 5. refreshJob Overwrites with Undefined
**File**: jobs.ts (144-177)
**Issue**: Incomplete API response corrupts state
**Effort**: 1 hour
**Risk**: High - data loss

**Current**:
```typescript
jobs: state.jobs.map((job) =>
  job.id === jobId
    ? {
        ...job,
        status: data.status, // If undefined, overwrites good data!
        stage: data.stage,
        stage_started_at: data.stage_started_at,
        progress_percent: data.progress_percent,
        title: data.title,
        artifacts: data.artifacts,
        error: data.error,
      }
    : job
),
```

**Fix**:
```typescript
jobs: state.jobs.map((job) =>
  job.id === jobId
    ? {
        ...job,
        ...(data.status !== undefined && { status: data.status }),
        ...(data.stage !== undefined && { stage: data.stage }),
        ...(data.stage_started_at !== undefined && { stage_started_at: data.stage_started_at }),
        ...(data.progress_percent !== undefined && { progress_percent: data.progress_percent }),
        ...(data.title !== undefined && { title: data.title }),
        ...(data.artifacts !== undefined && { artifacts: data.artifacts }),
        ...(data.error !== undefined && { error: data.error }),
      }
    : job
),
```

**Or**: Add type validation
```typescript
const updated = {
  ...job,
  ...(typeof data.status === 'string' && { status: data.status }),
  ...(typeof data.progress_percent === 'number' && { progress_percent: data.progress_percent }),
  // ... etc
};
```

**Tests Needed**:
- Test API response missing fields
- Test only provided fields updated
- Test original data preserved

---

### 6. Folder Operations Mutate Objects
**File**: settings.ts (306-327)
**Issue**: Direct mutation instead of immutable updates
**Effort**: 1 hour
**Risk**: Medium - React may miss changes

**Current**:
```typescript
updatedFolders.forEach((f) => {
  f.is_default = f.folder_id === newDefaultId; // MUTATION!
});
```

**Fix**:
```typescript
const updatedFolders = settings.drive_folders.map((f) => ({
  ...f, // Create new object
  is_default: f.folder_id === newDefaultId,
}));
```

**All Locations**:
- removeFolder (lines 310-320)
- setDefaultFolder (lines 333-336)

**Tests Needed**:
- Test folder state immutability
- Test React re-renders on folder changes
- Test is_default flags correct

---

### 7. Supabase Missing Env Var Handling
**File**: supabase.ts (6-16)
**Issue**: Warning only in production, silent in dev
**Effort**: 30 minutes
**Risk**: Low - affects development experience

**Current**:
```typescript
if (!supabaseUrl || !supabaseAnonKey) {
  if (process.env.NODE_ENV === 'production') {
    console.warn('Missing Supabase environment variables...');
  }
}
```

**Fix**:
```typescript
if (!supabaseUrl || !supabaseAnonKey) {
  const msg = 'Missing required Supabase environment variables: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY';

  if (process.env.NODE_ENV === 'production') {
    console.error(msg);
  } else {
    console.warn(msg);
    // Optional: throw error in dev to catch immediately
    // throw new Error(msg);
  }
}
```

**Tests Needed**:
- Test warning displayed in dev and prod
- Test app functions with missing vars (graceful degradation)

---

### 8. 401 Error Handling in Jobs
**File**: jobs.ts (76-81)
**Issue**: Silent logout, user doesn't know
**Effort**: 1 hour
**Risk**: Medium - UX confusion

**Current**:
```typescript
if (response.status === 401) {
  set({ jobs: [], isLoading: false });
  return; // Silent! User doesn't know why
}
```

**Fix**:
```typescript
if (response.status === 401) {
  // Let caller know about auth failure
  set({
    jobs: [],
    isLoading: false,
    error: 'Your session has expired. Please log in again.'
  });

  // Optional: dispatch logout event
  window.dispatchEvent(new CustomEvent('auth-expired'));
  return;
}
```

**Also In**: admin.ts should do similar for admin operations

**Tests Needed**:
- Test 401 response
- Test error state set
- Test UI shows re-login message

---

### 9. Pagination Reset on Filter
**File**: admin.ts (119-126, 215-240)
**Issue**: Page number stale after filter change
**Effort**: 1 hour
**Risk**: Medium - wrong data displayed

**Current**:
```typescript
fetchJobs: async (page = 1, filters = {}) => {
  set({ isLoadingJobs: true, jobsPage: page }); // Page set
  // If filters provided, should reset to page 1
  // But code doesn't enforce this
}
```

**Fix**:
```typescript
fetchJobs: async (page = 1, filters = {}) => {
  // Reset to page 1 if filters provided and not first page
  const resetPage = Object.keys(filters).length > 0 && page > 1 ? 1 : page;

  set({ isLoadingJobs: true, jobsPage: resetPage });
  // ... rest of implementation
}
```

**Or**: Make filtering responsibility of caller:
```typescript
// In component
const handleFilterChange = (newFilters) => {
  store.fetchJobs(1, newFilters); // Always reset to page 1
}
```

**Tests Needed**:
- Test page resets when filter applied
- Test pagination works with filters
- Test correct page of filtered results shown

---

### 10. Use error-utils Consistently
**Files**: All stores + supabase.ts
**Issue**: Inconsistent error handling, error-utils not used
**Effort**: 2 hours
**Risk**: Low - code quality

**Current**:
```typescript
if (process.env.NODE_ENV === 'development') {
  console.error('Failed to fetch admin stats:', error);
}
```

**Should Use**:
```typescript
import { logError } from '../lib/error-utils';

// Then
catch (error) {
  logError('Failed to fetch admin stats', error);
  // ... rest of error handling
}
```

**Files to Update**:
- admin.ts: 4 catch blocks
- jobs.ts: 3 catch blocks
- settings.ts: 5 catch blocks
- supabase.ts: Add error logging to functions

**Tests Needed**:
- Test error logged in development
- Test error not logged in production

---

## MEDIUM PRIORITY (Sprint 2)

### 11. No Per-Job Loading States
**File**: jobs.ts (58-92)
**Issue**: Cannot show spinner for individual job refresh
**Effort**: 2 hours
**Risk**: Low - UX improvement

**Add to JobsState**:
```typescript
interface JobsState {
  jobs: Job[];
  isLoading: boolean; // Keep for list load
  loadingJobIds: Set<string>; // ADD: Track per-job loading
  error: string | null;
  // ... rest
}
```

**Implement**:
```typescript
refreshJob: async (jobId: string) => {
  set((state) => ({
    loadingJobIds: new Set([...state.loadingJobIds, jobId]),
  }));

  try {
    // ... fetch logic
  } finally {
    set((state) => {
      const newSet = new Set(state.loadingJobIds);
      newSet.delete(jobId);
      return { loadingJobIds: newSet };
    });
  }
}
```

**Tests Needed**:
- Test individual job loading state
- Test multiple concurrent refreshes
- Test state cleanup on error

---

### 12. Race Conditions in Async Updates
**File**: settings.ts (269-327)
**Issue**: Concurrent folder operations may conflict
**Effort**: 2 hours
**Risk**: Medium - edge case bugs

**Add Request Tracking**:
```typescript
interface SettingsState {
  // ... existing fields
  pendingOperationId: string | null;

  addFolder: async (folder: FolderValidation) => {
    const operationId = Math.random().toString(36);
    set({ pendingOperationId: operationId });

    try {
      const { settings, updateSettings } = get();
      // ... logic

      await updateSettings({...});

      // Only update if this operation is still pending
      set((state) => ({
        folderValidation: state.pendingOperationId === operationId ? null : state.folderValidation,
        pendingOperationId: state.pendingOperationId === operationId ? null : state.pendingOperationId,
      }));
    } catch (e) {
      set({ pendingOperationId: null });
      throw e;
    }
  }
}
```

**Tests Needed**:
- Test concurrent folder additions
- Test last operation wins
- Test error in one operation doesn't block others

---

### 13. Add JSON Response Validation
**Files**: All stores
**Issue**: No runtime type checking of API responses
**Effort**: 3-4 hours
**Risk**: Medium - data corruption on API changes

**Consider Using**: zod or io-ts for runtime validation

**Example with zod**:
```typescript
import { z } from 'zod';

const JobSchema = z.object({
  id: z.string(),
  prompt: z.string(),
  status: z.enum(['queued', 'running', 'completed', 'failed', 'cancelled']),
  progress_percent: z.number().min(0).max(100),
  created_at: z.string(),
});

// In action
const validated = JobSchema.parse(data);
set({ job: validated });
```

**Tests Needed**:
- Test valid response
- Test invalid response throws
- Test error state set on validation failure

---

## LOW PRIORITY (Nice to Have)

### 14. Request Cancellation on Unmount
**Files**: All stores
**Issue**: No cleanup of in-flight requests
**Effort**: 3 hours
**Risk**: Low - memory leak

Use AbortController:
```typescript
let abortControllers: Map<string, AbortController> = new Map();

fetchJobs: async () => {
  // Cancel previous request
  abortControllers.get('fetchJobs')?.abort();

  const controller = new AbortController();
  abortControllers.set('fetchJobs', controller);

  try {
    const response = await fetch(url, { signal: controller.signal });
    // ...
  } catch (e) {
    if (e.name !== 'AbortError') throw e;
  }
}
```

---

### 15. Polling Interval Configuration
**File**: constants.ts
**Issue**: Polling intervals hardcoded
**Effort**: 1 hour
**Risk**: Low - operational flexibility

**Add to .env**:
```
NEXT_PUBLIC_JOB_STATUS_POLL_INTERVAL=2000
NEXT_PUBLIC_DASHBOARD_REFRESH_INTERVAL=30000
```

**Update constants.ts**:
```typescript
export const POLLING_INTERVALS = {
  JOB_STATUS: parseInt(process.env.NEXT_PUBLIC_JOB_STATUS_POLL_INTERVAL || '2000'),
  DASHBOARD_REFRESH: parseInt(process.env.NEXT_PUBLIC_DASHBOARD_REFRESH_INTERVAL || '30000'),
};
```

---

### 16. Settings Cache with TTL
**File**: settings.ts
**Issue**: Every load re-fetches settings
**Effort**: 2 hours
**Risk**: Low - performance improvement

**Add Cache**:
```typescript
interface SettingsState {
  // ... existing
  settingsCacheTime: number | null;

  fetchSettings: async () => {
    const { settings, settingsCacheTime } = get();
    const now = Date.now();

    // Return cached if fresh (5 min TTL)
    if (settings && settingsCacheTime && now - settingsCacheTime < 5 * 60 * 1000) {
      return;
    }

    // ... fetch
    set({ settings: data, settingsCacheTime: now });
  }
}
```

---

## Implementation Checklist

### Week 1 (Critical Issues)
- [ ] Add timeouts to all fetch calls
- [ ] Add error field to AdminState and JobsState
- [ ] Wrap all response.json() in try/catch
- [ ] Move saveSuccessTimeoutId to store state
- [ ] Fix refreshJob undefined overwrites
- [ ] Fix folder mutations to be immutable

### Week 2 (High Priority)
- [ ] Fix 401 error handling
- [ ] Fix supabase env var warning
- [ ] Fix pagination reset on filter
- [ ] Use error-utils consistently

### Week 3+ (Medium/Low)
- [ ] Add per-job loading states
- [ ] Add race condition protection
- [ ] Add JSON response validation
- [ ] Add request cancellation
- [ ] Add config env vars
- [ ] Add settings caching

---

## Success Criteria

- [ ] All critical issues resolved
- [ ] All high priority issues resolved
- [ ] Admin/jobs stores have error fields
- [ ] All fetch requests have timeouts
- [ ] All JSON parsing wrapped in try/catch
- [ ] Settings store timeout in state
- [ ] Error-utils used consistently
- [ ] Unit tests added for all fixes
- [ ] No silent failures in production logs
- [ ] CI/CD passes all tests

---

## Estimated Timeline

| Priority | Issues | Effort | Timeline |
|----------|--------|--------|----------|
| Critical | 4 | 8-10h | Day 1-2 |
| High | 6 | 8-10h | Day 2-3 |
| Medium | 3 | 6-8h | Day 3-4 |
| Low | 3 | 6-8h | Day 4-5 |
| **Total** | **16** | **28-36h** | **1 week** |

**Recommendation**: Tackle critical + high priority (4-5 days), then medium/low in following sprints.

