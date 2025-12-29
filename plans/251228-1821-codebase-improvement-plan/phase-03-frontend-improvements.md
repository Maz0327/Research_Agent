# Phase 03: Frontend Improvements

## Context Links
- [Frontend Comprehensive Review](../reports/code-reviewer-251228-1819-frontend-comprehensive-review.md)
- [Frontend Stores Audit](../reports/tester-251228-1516-frontend-stores-audit.md)
- [Constants File](../../frontend/lib/constants.ts)

## Overview

| Field | Value |
|-------|-------|
| Priority | P2 (Medium) |
| Status | Pending |
| Effort | 8 hours |
| Risk | Low |

Address DRY violations, form validation, performance optimizations, and UX improvements.

## Requirements

### Functional
1. Centralize API_URL configuration
2. Add form input validation
3. Implement memoization for job filtering
4. Add loading states to job actions
5. Centralize magic numbers in constants

### Non-Functional
- Frontend build must pass
- No breaking changes to existing flows
- Maintain accessibility standards

## Related Code Files

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `frontend/lib/constants.ts` | Modify | Add API_URL and validation limits |
| `frontend/store/admin.ts` | Modify | Use centralized API_URL |
| `frontend/store/jobs.ts` | Modify | Use centralized API_URL, add memoization |
| `frontend/store/settings.ts` | Modify | Use centralized API_URL, fix global timeout |
| `frontend/pages/dashboard.tsx` | Modify | Memoize filteredJobs |
| `frontend/pages/transcripts.tsx` | Modify | Add form labels, cleanup intervals |
| `frontend/components/job-card/JobActions.tsx` | Modify | Add loading states |

### Files to Create

| File | Description |
|------|-------------|
| `frontend/lib/api-client.ts` | Centralized fetch with timeout (Phase 1) |
| `frontend/lib/validation.ts` | Form validation utilities |

## Implementation Steps

### Step 1: Centralize API Configuration (30 min)

Update `frontend/lib/constants.ts`:

```typescript
// frontend/lib/constants.ts

// API Configuration
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Validation Limits
export const VALIDATION_LIMITS = {
  MAX_POLL_ERRORS: 5,
  MAX_DRIVE_FOLDERS: 3,
  MAX_USERNAME_LENGTH: 30,
  MIN_USERNAME_LENGTH: 3,
  MAX_PROMPT_LENGTH: 500,
} as const;

// Keep existing constants...
export const POLLING_INTERVALS = {
  JOB_STATUS: 2000,
  ADMIN_STATS: 60000,
} as const;

// ... rest of file
```

### Step 2: Update Stores to Use Centralized API_URL (1h)

**admin.ts** (~line 8):
```typescript
import { API_URL } from '../lib/constants';
// Remove local API_URL definition
```

**jobs.ts** (~line 8):
```typescript
import { API_URL } from '../lib/constants';
```

**settings.ts** (~line 8):
```typescript
import { API_URL } from '../lib/constants';
```

### Step 3: Fix Global Timeout in Settings Store (30 min)

Move timeout tracking into store state:

**settings.ts** (~line 86):
```typescript
// REMOVE global variable
// let saveSuccessTimeoutId: ReturnType<typeof setTimeout> | null = null;

// ADD to SettingsState interface
interface SettingsState {
  // ... existing fields
  saveSuccessTimeoutId: ReturnType<typeof setTimeout> | null;
}

// ADD to initial state
saveSuccessTimeoutId: null,

// UPDATE updateSettings (~line 178):
updateSettings: async (updates) => {
  const { saveSuccessTimeoutId } = get();
  if (saveSuccessTimeoutId) {
    clearTimeout(saveSuccessTimeoutId);
  }
  // ... existing logic
  const newTimeoutId = setTimeout(() => {
    set({ showSaveSuccess: false, saveSuccessTimeoutId: null });
  }, 2000);
  set({ showSaveSuccess: true, saveSuccessTimeoutId: newTimeoutId });
},
```

### Step 4: Memoize Job Filtering (30 min)

**dashboard.tsx** (~line 106):
```typescript
import { useMemo } from 'react';

// Replace:
// const filteredJobs = jobs.filter((job) => {
//   if (statusFilter === 'all') return true;
//   return job.status === statusFilter;
// });

// With:
const filteredJobs = useMemo(() => {
  if (statusFilter === 'all') return jobs;
  return jobs.filter((job) => job.status === statusFilter);
}, [jobs, statusFilter]);
```

### Step 5: Add Loading States to Job Actions (1h)

**JobActions.tsx** - Add loading state for cancel:

```typescript
import { useState } from 'react';

interface JobActionsProps {
  jobId: string;
  status: string;
  driveFolderUrl?: string;
  onRefresh?: () => void;
}

export function JobActions({ jobId, status, driveFolderUrl, onRefresh }: JobActionsProps) {
  const [isCancelling, setIsCancelling] = useState(false);
  const cancelJob = useJobsStore((state) => state.cancelJob);

  const handleCancel = async () => {
    setIsCancelling(true);
    try {
      await cancelJob(jobId);
      onRefresh?.();
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <div className="flex gap-2">
      {/* Cancel button */}
      {(status === 'queued' || status === 'running') && (
        <button
          onClick={handleCancel}
          disabled={isCancelling}
          className="..."
        >
          {isCancelling ? 'Cancelling...' : 'Cancel'}
        </button>
      )}
      {/* ... other buttons */}
    </div>
  );
}
```

### Step 6: Add Form Labels for Accessibility (30 min)

**transcripts.tsx** (~line 139):
```typescript
// Before
<textarea
  value={videoUrls}
  onChange={(e) => setVideoUrls(e.target.value)}
  placeholder="Paste YouTube URLs..."
/>

// After
<label htmlFor="video-urls" className="sr-only">
  YouTube Video URLs
</label>
<textarea
  id="video-urls"
  aria-label="YouTube video URLs"
  value={videoUrls}
  onChange={(e) => setVideoUrls(e.target.value)}
  placeholder="Paste YouTube URLs (one per line or comma-separated)"
/>
```

### Step 7: Create Validation Utilities (1h)

Create `frontend/lib/validation.ts`:

```typescript
// frontend/lib/validation.ts
import { VALIDATION_LIMITS } from './constants';

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

export function validateUsername(username: string): ValidationResult {
  if (username.length < VALIDATION_LIMITS.MIN_USERNAME_LENGTH) {
    return {
      isValid: false,
      error: `Username must be at least ${VALIDATION_LIMITS.MIN_USERNAME_LENGTH} characters`,
    };
  }
  if (username.length > VALIDATION_LIMITS.MAX_USERNAME_LENGTH) {
    return {
      isValid: false,
      error: `Username cannot exceed ${VALIDATION_LIMITS.MAX_USERNAME_LENGTH} characters`,
    };
  }
  if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
    return {
      isValid: false,
      error: 'Username can only contain letters, numbers, underscores, and hyphens',
    };
  }
  return { isValid: true };
}

export function validatePrompt(prompt: string): ValidationResult {
  if (!prompt.trim()) {
    return { isValid: false, error: 'Research prompt is required' };
  }
  if (prompt.length > VALIDATION_LIMITS.MAX_PROMPT_LENGTH) {
    return {
      isValid: false,
      error: `Prompt cannot exceed ${VALIDATION_LIMITS.MAX_PROMPT_LENGTH} characters`,
    };
  }
  return { isValid: true };
}

export function validateDriveFolderUrl(url: string): ValidationResult {
  const drivePattern = /^https:\/\/drive\.google\.com\/drive\/folders\/[a-zA-Z0-9_-]+$/;
  if (!drivePattern.test(url)) {
    return { isValid: false, error: 'Invalid Google Drive folder URL' };
  }
  return { isValid: true };
}

export function validateYouTubeUrls(urls: string): ValidationResult {
  const lines = urls.split(/[\n,]/).filter((line) => line.trim());
  const youtubePattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;

  for (const line of lines) {
    const url = line.trim();
    if (!youtubePattern.test(url)) {
      return { isValid: false, error: `Invalid YouTube URL: ${url.slice(0, 50)}...` };
    }
  }
  return { isValid: true };
}
```

### Step 8: Add Exponential Backoff to Polling (1h)

**dashboard.tsx** (~line 73):
```typescript
const [retryDelay, setRetryDelay] = useState(POLLING_INTERVALS.JOB_STATUS);

useEffect(() => {
  if (runningJobs.length === 0) return;

  const interval = setInterval(async () => {
    try {
      await batchRefreshJobs(runningJobs.map((job) => job.id));
      setRetryDelay(POLLING_INTERVALS.JOB_STATUS); // Reset on success
    } catch {
      setRetryDelay((prev) => Math.min(prev * 2, 30000)); // Max 30s
    }
  }, retryDelay);

  return () => clearInterval(interval);
}, [runningJobs, batchRefreshJobs, retryDelay]);
```

### Step 9: Cleanup Effect in Transcripts (30 min)

**transcripts.tsx** (~line 88):
```typescript
useEffect(() => {
  if (!jobId) return;

  let pollErrors = 0;

  const pollInterval = setInterval(async () => {
    try {
      await fetchTranscriptStatus(jobId);
      pollErrors = 0; // Reset on success
    } catch {
      pollErrors++;
      if (pollErrors >= VALIDATION_LIMITS.MAX_POLL_ERRORS) {
        clearInterval(pollInterval);
        setError('Failed to check transcript status');
      }
    }
  }, 2000);

  return () => {
    try {
      clearInterval(pollInterval);
    } catch {
      // Ignore cleanup errors
    }
  };
}, [jobId, fetchTranscriptStatus]);
```

### Step 10: Verify and Test (1h)

1. Run lint:
   ```bash
   cd frontend && npm run lint
   ```

2. Run build:
   ```bash
   npm run build
   ```

3. Run tests:
   ```bash
   npm test
   ```

## Todo List

### API Configuration
- [ ] Add API_URL to constants.ts
- [ ] Add VALIDATION_LIMITS to constants.ts
- [ ] Update admin.ts to use centralized API_URL
- [ ] Update jobs.ts to use centralized API_URL
- [ ] Update settings.ts to use centralized API_URL

### Store Improvements
- [ ] Fix global timeout in settings.ts
- [ ] Add memoization to dashboard.tsx filteredJobs

### UX Improvements
- [ ] Add loading states to JobActions
- [ ] Add form labels for accessibility
- [ ] Add exponential backoff to polling
- [ ] Fix cleanup effect in transcripts.tsx

### Validation
- [ ] Create validation.ts utility
- [ ] Add username validation
- [ ] Add prompt validation
- [ ] Add URL validation

### Verification
- [ ] Run npm run lint
- [ ] Run npm run build
- [ ] Run npm test

## Success Criteria

- [ ] API_URL defined in single location (constants.ts)
- [ ] No hardcoded API endpoints in stores
- [ ] Form inputs have proper labels/validation
- [ ] Job filtering memoized
- [ ] Cancel button shows loading state
- [ ] Frontend build passes
- [ ] Lint passes with no errors

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking store state | Low | Medium | Test each store change individually |
| Accessibility regression | Low | Low | Test with screen reader |
| Performance regression | Low | Low | Measure with React DevTools |

## Security Considerations

- Validation must not leak sensitive info
- Form validation happens client-side (defense in depth only)
- Server-side validation still required

## Next Steps

After completing this phase:
1. Add frontend tests for new validation utilities (Phase 4)
2. Consider SWR/React Query for data fetching (future)
3. Add loading skeletons to admin pages (nice-to-have)
