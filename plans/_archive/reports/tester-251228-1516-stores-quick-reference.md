# Frontend Stores Audit - Quick Reference

## Critical Issues (FIX IMMEDIATELY)

| # | Issue | File | Lines | Severity |
|----|-------|------|-------|----------|
| 1 | No fetch timeout - requests hang | admin.ts | 142-163 | CRITICAL |
| 2 | Production errors silent - can't debug | admin.ts | 189-267 | CRITICAL |
| 3 | 401 errors not shown to user | jobs.ts | 58-92 | CRITICAL |
| 4 | Global timeout tracking fragile | settings.ts | 85-86 | CRITICAL |

**Impact**: App hangs, silent failures, user confusion
**Effort**: 6-8 hours total
**Timeline**: Implement Day 1

---

## High Priority Issues (Before Release)

| # | Issue | File | Lines | Fix Effort |
|----|-------|------|-------|-----------|
| 5 | No error state in AdminState | admin.ts | 106-138 | 1h |
| 6 | No error state in JobsState | jobs.ts | 40-49 | 1h |
| 7 | JSON parse errors crash | admin.ts, jobs.ts, settings.ts | multiple | 2h |
| 8 | refreshJob overwrites with undefined | jobs.ts | 144-177 | 1h |
| 9 | Folder operations mutate objects | settings.ts | 306-327 | 1h |
| 10 | Supabase env var warning wrong | supabase.ts | 6-16 | 0.5h |

**Impact**: Data corruption, no error messages, crashes
**Effort**: 6.5 hours total
**Timeline**: Implement Day 2-3

---

## Code Patterns to Fix

### Pattern 1: Add Error Field to Stores
```typescript
// BEFORE
interface AdminState {
  stats: AdminStats | null;
  users: AdminUser[];
}

// AFTER
interface AdminState {
  stats: AdminStats | null;
  users: AdminUser[];
  error: string | null; // ADD THIS
}
```

Affected: admin.ts, jobs.ts

---

### Pattern 2: Wrap Fetch Calls with Timeout
```typescript
// BEFORE
const response = await fetch(url, { headers });

// AFTER
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000);
try {
  const response = await fetch(url, {
    headers,
    signal: controller.signal,
  });
} finally {
  clearTimeout(timeoutId);
}
```

Affected: admin.ts, jobs.ts, settings.ts

---

### Pattern 3: Wrap JSON Parsing
```typescript
// BEFORE
const data = await response.json();

// AFTER
let data;
try {
  data = await response.json();
} catch (e) {
  throw new Error('Invalid response format');
}
```

Affected: 6 locations

---

### Pattern 4: Set Error State on Failure
```typescript
// BEFORE
catch (error) {
  set({ isLoadingStats: false });
}

// AFTER
catch (error) {
  set({
    isLoadingStats: false,
    error: error instanceof Error ? error.message : 'Unknown error',
  });
}
```

Affected: All stores

---

### Pattern 5: Move Global Timeout to State
```typescript
// BEFORE (BAD - module level)
let saveSuccessTimeoutId: ReturnType<typeof setTimeout> | null = null;

// AFTER (GOOD - in store)
interface SettingsState {
  saveSuccessTimeoutId: ReturnType<typeof setTimeout> | null;
  // ... other fields
}

// In action
const { saveSuccessTimeoutId } = get();
if (saveSuccessTimeoutId) clearTimeout(saveSuccessTimeoutId);
```

Affected: settings.ts

---

### Pattern 6: Handle Undefined Values in Updates
```typescript
// BEFORE (BAD - overwrites good data with undefined)
status: data.status,
progress_percent: data.progress_percent,

// AFTER (GOOD - only set if defined)
...(data.status !== undefined && { status: data.status }),
...(data.progress_percent !== undefined && { progress_percent: data.progress_percent }),
```

Affected: jobs.ts refreshJob

---

### Pattern 7: Immutable Object Updates
```typescript
// BEFORE (BAD - mutation)
updatedFolders.forEach((f) => {
  f.is_default = f.folder_id === newDefaultId;
});

// AFTER (GOOD - immutable)
const updatedFolders = settings.drive_folders.map((f) => ({
  ...f,
  is_default: f.folder_id === newDefaultId,
}));
```

Affected: settings.ts folder operations

---

### Pattern 8: Show 401 Errors to User
```typescript
// BEFORE (BAD - silent)
if (response.status === 401) {
  set({ jobs: [], isLoading: false });
  return;
}

// AFTER (GOOD - show error)
if (response.status === 401) {
  set({
    jobs: [],
    isLoading: false,
    error: 'Your session expired. Please log in again.',
  });
  return;
}
```

Affected: jobs.ts, admin.ts

---

## Issue Distribution

### By File
- **admin.ts**: 4 issues (1 critical, 2 high, 2 medium)
- **jobs.ts**: 3 issues (1 critical, 2 high, 1 medium)
- **settings.ts**: 4 issues (1 critical, 2 high, 1 medium)
- **supabase.ts**: 3 issues (1 high, 2 low)
- **constants.ts**: 1 issue (low)
- **error-utils.ts**: 0 issues (not used)

### By Severity
- **Critical**: 4 issues
- **High**: 6 issues
- **Medium**: 5 issues
- **Low**: 4 issues

### By Category
- Error handling: 8 issues
- API resilience: 4 issues
- State management: 4 issues
- Type safety: 2 issues
- Performance: 1 issue

---

## Files Changed Summary

| File | Changes | Complexity |
|------|---------|-----------|
| admin.ts | Add error field, timeout, JSON parsing, logging | Medium |
| jobs.ts | Add error field, timeout, JSON parsing, 401 handling | Medium |
| settings.ts | Move timeout to state, immutable updates, timeout | Medium |
| supabase.ts | Better env var warning | Low |
| constants.ts | Optional: Make polling configurable | Low |

---

## Testing Impact

### New Tests Needed: ~25-30 test cases

| File | Test Cases | Effort |
|------|-----------|--------|
| admin.ts | 8-10 | 3h |
| jobs.ts | 6-8 | 3h |
| settings.ts | 6-8 | 3h |
| supabase.ts | 2-3 | 1h |
| **Total** | **25-30** | **10h** |

---

## Production Risk Assessment

### Current Risks
- **Hangs**: Fetch requests can hang indefinitely (HIGH)
- **Silent Failures**: Errors not shown in production (HIGH)
- **Data Corruption**: refreshJob overwrites with undefined (MEDIUM)
- **Logout Confusion**: 401 errors not explained to user (MEDIUM)
- **Race Conditions**: Concurrent folder operations may conflict (MEDIUM)

### After Fixes
- All requests have timeouts
- All errors shown to user
- No undefined overwrites
- Auth errors clearly communicated
- Race condition prevention in place

---

## Sign-Off Checklist

Before marking complete:
- [ ] All 4 critical issues fixed
- [ ] All 6 high priority issues fixed
- [ ] Tests added for all fixes
- [ ] Error-utils used consistently
- [ ] Admin/jobs stores have error fields
- [ ] All fetch requests have timeouts
- [ ] CI/CD passes all tests
- [ ] Code review approved
- [ ] Manual testing done on all paths

---

## Contact Points

**Admin Store Issues**: admin.ts - Lines 142-312
**Jobs Store Issues**: jobs.ts - Lines 58-224
**Settings Store Issues**: settings.ts - Lines 85-348
**Supabase Issues**: supabase.ts - Lines 6-86
**Utils**: error-utils.ts (not used - should be integrated)

---

## Next Steps

1. **Today**: Create tickets for critical + high priority issues
2. **Day 1-2**: Implement critical issue fixes
3. **Day 2-3**: Implement high priority fixes
4. **Day 3-4**: Add comprehensive tests
5. **Day 4**: Code review and testing
6. **Day 5**: Deploy to staging and production validation

---

**Report Generated**: 2025-12-28 15:16 UTC
**Total Issues**: 19
**Blocking Issues**: 4
**Estimated Fix Time**: 28-36 hours

