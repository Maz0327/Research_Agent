# UX Fixes - Actionable Implementation Guide
**Date**: December 28, 2025 | **Priority Level**: Medium-Low

---

## Quick Reference Table

| Priority | Issue | File(s) | Est. Hours | Impact |
|----------|-------|---------|-----------|--------|
| HIGH | Progress bar % text | `job-card/ProgressBar.tsx` | 0.5 | Clarity |
| HIGH | Pipeline tooltips | `dashboard.tsx` | 1.5 | Discoverability |
| HIGH | Session timeout toast | `jobs.ts`, `supabase.ts` | 1.0 | Error recovery |
| MEDIUM | Character counter | `dashboard.tsx` | 0.5 | User guidance |
| MEDIUM | Stage update batching | `jobs.ts`, `dashboard.tsx` | 1.0 | Performance |
| MEDIUM | Artifacts preview | `job-card/JobResults.tsx` | 1.0 | Clarity |
| MEDIUM | Inline validation | `dashboard.tsx` | 0.5 | UX feedback |
| LOW | Success toast | `dashboard.tsx` | 0.5 | Feedback |
| LOW | Completion time | `JobCard.tsx` | 0.5 | Information |
| LOW | Results in new tab | `job-card/JobResults.tsx` | 0.25 | Usability |

**Total Estimated**: ~7.25 developer hours | **Suggested Sprint**: 1 sprint (5 items) + next sprint (5 items)

---

## Detailed Implementation Guides

### FIX 1: Add Progress Percentage Text to Progress Bar
**Priority**: HIGH | **Effort**: 0.5h | **Files**: `frontend/components/job-card/ProgressBar.tsx`

**Current State**:
```tsx
<div className="bg-blue-600 h-1 rounded-full transition-all duration-300"
     style={{ width: `${progress}%` }} />
```

**Issue**: Visual bar shows progress but no percentage number

**Solution**:
```tsx
// Add text overlay on progress bar
<div className="relative mt-2">
  <div className="w-full bg-gray-800 h-1 rounded-full overflow-hidden">
    <div
      className="bg-blue-600 h-full rounded-full transition-all duration-300"
      style={{ width: `${progress}%` }}
    />
  </div>
  <span className="absolute right-0 top-3 text-xs font-medium text-gray-400">
    {progress}%
  </span>
</div>
```

**Test Cases**:
- [ ] Progress bar shows "0%" at start
- [ ] Progress updates to "50%" mid-job
- [ ] Shows "100%" when complete
- [ ] Text doesn't overflow on narrow screens

---

### FIX 2: Add Pipeline Mode Tooltips with Budget Details
**Priority**: HIGH | **Effort**: 1.5h | **Files**: `frontend/pages/dashboard.tsx`

**Current State**:
```tsx
const pipelines = [
  { value: 'quick', label: 'Quick', description: 'Fast research with basic coverage' },
  { value: 'investigation', label: 'Investigation', description: 'Deep-dive investigative research' },
  // ...
];
```

**Issue**: Descriptions are vague; users don't understand pipeline differences

**Solution** (Option A - Simple Info Icon):
```tsx
// Add InfoIcon component with tooltip library (radix-ui or headlessui)
<button
  type="button"
  role="radio"
  className="..."
  title="Quick Pipeline: 20 URLs, 60min transcription, 10 claims validated"
>
  <span className="block text-sm font-medium text-gray-200">{p.label}</span>
  <span className="mt-0.5 block text-xs text-gray-500">{p.description}</span>
  <svg className="inline h-3 w-3 ml-1 text-gray-600">
    {/* Info icon */}
  </svg>
</button>
```

**Solution** (Option B - Expandable Card):
```tsx
// Create PipelineOption component with details modal
<PipelineOption
  label={p.label}
  description={p.description}
  details={{
    urls: 20,
    transcriptionMins: 60,
    maxClaims: 10,
    estimatedTime: '30-60 min'
  }}
  selected={pipeline === p.value}
  onSelect={() => setPipeline(p.value)}
/>
```

**Backend Reference** (use these values):
```python
PIPELINE_BUDGETS = {
    "quick": {"max_web_urls": 20, "max_transcription_minutes": 60, "max_claims_to_validate": 10},
    "full": {"max_web_urls": 50, "max_transcription_minutes": 120, "max_claims_to_validate": 25},
    "breaking_news": {"max_web_urls": 15, "max_transcription_minutes": 30, "max_claims_to_validate": 8},
    "investigation": {"max_web_urls": 40, "max_transcription_minutes": 100, "max_claims_to_validate": 20},
    "profile": {"max_web_urls": 25, "max_transcription_minutes": 60, "max_claims_to_validate": 12},
    "controversy": {"max_web_urls": 30, "max_transcription_minutes": 80, "max_claims_to_validate": 15},
}
```

**Test Cases**:
- [ ] Tooltip/modal shows on hover/click
- [ ] Budget details match backend configuration
- [ ] All 6 pipelines have descriptions
- [ ] Mobile: tap reveals details, tap again closes

---

### FIX 3: Implement Session Timeout Notification
**Priority**: HIGH | **Effort**: 1.0h | **Files**: `frontend/store/jobs.ts`, `frontend/lib/supabase.ts`, `frontend/components/Layout.tsx`

**Current State**:
```tsx
if (response.status === 401) {
  set({ jobs: [], isLoading: false });
  return;
}
```

**Issue**: Silent failure on token expiration; user sees empty job list without explanation

**Solution** (Step 1 - Toast Component):
```tsx
// Create/enhance Toast component (or use existing notification system)
// File: frontend/components/Toast.tsx
interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning';
  duration?: number;
}

// Global toast store or context
const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast: Toast) => { /* ... */ },
  removeToast: (id: string) => { /* ... */ },
}));
```

**Solution** (Step 2 - Handle 401 in Jobs Store):
```tsx
// frontend/store/jobs.ts
fetchJobs: async () => {
  try {
    const response = await fetch(`${API_URL}/jobs`, { headers });

    if (response.status === 401) {
      // Show notification and redirect
      useToastStore.getState().addToast({
        id: 'session-expired',
        message: 'Session expired. Please log in again.',
        type: 'error',
        duration: 5000
      });

      // Clear auth state
      await supabase.auth.signOut();
      router.push('/login');
      return;
    }
    // ... rest of fetch logic
  }
}
```

**Solution** (Step 3 - Add Toast Container to Layout):
```tsx
// frontend/components/Layout.tsx
import { useToastStore } from '../store/toast';

export default function Layout({ children }) {
  const { toasts } = useToastStore();

  return (
    <>
      {/* Existing layout */}
      <main>{children}</main>

      {/* Toast container */}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((toast) => (
          <Toast key={toast.id} {...toast} />
        ))}
      </div>
    </>
  );
}
```

**Test Cases**:
- [ ] Job fetch with expired token shows toast
- [ ] User redirects to login after 2 seconds
- [ ] Toast displays for 5 seconds then auto-dismisses
- [ ] Multiple errors show stacked toasts

---

### FIX 4: Add Character Counter to Prompt Field
**Priority**: MEDIUM | **Effort**: 0.5h | **Files**: `frontend/pages/dashboard.tsx`

**Current State**:
```tsx
<textarea
  value={prompt}
  onChange={(e) => setPrompt(e.target.value)}
  placeholder="Enter your research topic or question..."
  rows={3}
/>
```

**Issue**: No feedback on character limit (MAX: 2000)

**Solution**:
```tsx
const MAX_CHARS = 2000;

<div className="mb-4">
  <label htmlFor="prompt" className="mb-1.5 block text-sm font-medium text-gray-400">
    Research Topic
  </label>
  <textarea
    id="prompt"
    value={prompt}
    onChange={(e) => setPrompt(e.target.value)}
    placeholder="Enter your research topic or question..."
    rows={3}
    maxLength={MAX_CHARS}
    className="..."
  />
  <div className="mt-1 flex justify-between items-center">
    <span className="text-xs text-gray-500">
      {prompt.length} / {MAX_CHARS} characters
    </span>
    {prompt.length > MAX_CHARS * 0.9 && (
      <span className="text-xs text-yellow-400">
        {MAX_CHARS - prompt.length} remaining
      </span>
    )}
  </div>
</div>
```

**Test Cases**:
- [ ] Counter shows "0 / 2000" on empty field
- [ ] Updates live as user types
- [ ] Shows "1800 / 2000 characters" at 90% capacity
- [ ] Warning appears in yellow at 90%+

---

### FIX 5: Optimize Stage Update Frequency
**Priority**: MEDIUM | **Effort**: 1.0h | **Files**: `frontend/store/jobs.ts`, `frontend/pages/dashboard.tsx`

**Current State**:
- Jobs poll for updates every 2-3 seconds
- Any change triggers re-render of entire dashboard
- Stage descriptions update frequently, causing visual flicker

**Issue**: Excessive updates cause dashboard jitter and visual noise

**Solution** (Step 1 - Track Stage Changes):
```tsx
// frontend/store/jobs.ts
interface JobUpdate {
  id: string;
  changes: Partial<Job>;
  stageChanged: boolean; // Track if stage actually changed
}

refreshJob: async (jobId: string) => {
  // ... fetch job

  // Find existing job
  const oldJob = get().jobs.find(j => j.id === jobId);

  // Check what actually changed
  const stageChanged = oldJob?.stage !== newJob.stage;
  const statusChanged = oldJob?.status !== newJob.status;
  const progressChanged = Math.abs((oldJob?.progress_percent ?? 0) - newJob.progress_percent) > 5;

  // Only update if meaningful change
  if (stageChanged || statusChanged || progressChanged) {
    // Update state
  }
}
```

**Solution** (Step 2 - Batch Updates):
```tsx
// frontend/pages/dashboard.tsx
const batchRefreshJobs = useCallback((jobIds: string[]) => {
  if (refreshTimeoutRef.current) {
    clearTimeout(refreshTimeoutRef.current);
  }

  // Increase debounce from 100ms to 500ms
  refreshTimeoutRef.current = setTimeout(() => {
    jobIds.forEach((id) => refreshJob(id));
  }, 500); // Was 100ms
}, [refreshJob]);
```

**Test Cases**:
- [ ] Stage description only updates when stage actually changes
- [ ] Progress bar smoothly animates between updates
- [ ] No visual flicker when polling
- [ ] Updates still happen within 1-2 seconds

---

### FIX 6: Add Artifacts Preview/Explanation Tooltip
**Priority**: MEDIUM | **Effort**: 1.0h | **Files**: `frontend/components/job-card/JobResults.tsx`

**Current State**:
```tsx
<a href={driveFolderUrl} className="...">
  View Results on Google Drive
</a>
```

**Issue**: Users don't know what's in the folder or how to use outputs

**Solution**:
```tsx
// Create ArtifactsInfo component
function ArtifactsInfo() {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-medium text-gray-300">
          Artifacts
        </span>
        <button
          onClick={() => setShowInfo(!showInfo)}
          className="text-gray-500 hover:text-blue-400 transition"
          aria-label="Show artifact details"
          type="button"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {showInfo && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mb-3 rounded-lg bg-blue-900/20 border border-blue-800 p-3"
        >
          <p className="text-xs text-blue-300 mb-2">
            Your research has been packaged into 2 documents:
          </p>
          <ul className="text-xs text-blue-200 space-y-1 ml-2">
            <li>
              <strong>NotebookLM Packet</strong> - Optimized for podcast generation. Contains source materials and summaries.
            </li>
            <li>
              <strong>Documentary Blueprint</strong> - Optimized for video production. Includes shot list, timeline, and narrative structure.
            </li>
          </ul>
          <p className="text-xs text-blue-300 mt-2">
            Both files are ready to use in your production tools.
          </p>
        </motion.div>
      )}

      <a
        href={driveFolderUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 px-3 py-2 text-sm font-medium text-white transition"
      >
        Open Google Drive Folder
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </a>
    </div>
  );
}
```

**Test Cases**:
- [ ] Info icon visible and clickable
- [ ] Tooltip shows artifact descriptions
- [ ] Link opens in new tab
- [ ] Mobile: Info icon tappable, description readable

---

### FIX 7: Add Inline Validation for Prompt Length
**Priority**: MEDIUM | **Effort**: 0.5h | **Files**: `frontend/pages/dashboard.tsx`

**Current State**:
```tsx
<textarea
  value={prompt}
  onChange={(e) => setPrompt(e.target.value)}
  className="... border-gray-700 ..."
/>
```

**Issue**: No visual warning when approaching limit; error only appears on submission

**Solution**:
```tsx
const MAX_CHARS = 2000;
const warningThreshold = MAX_CHARS * 0.9; // 1800 chars

const promptLength = prompt.length;
const isWarning = promptLength > warningThreshold;
const isError = promptLength >= MAX_CHARS;

<textarea
  value={prompt}
  onChange={(e) => setPrompt(e.target.value)}
  className={`w-full rounded-lg border px-4 py-3 text-gray-100 transition ${
    isError
      ? 'border-red-500 bg-red-950/20 focus:ring-red-500'
      : isWarning
      ? 'border-yellow-600 bg-yellow-950/20 focus:ring-yellow-500'
      : 'border-gray-700 bg-gray-800 focus:border-blue-500 focus:ring-blue-500'
  }`}
/>

{isError && (
  <p className="mt-2 text-sm text-red-400">
    Exceeded character limit. Remove {promptLength - MAX_CHARS} characters.
  </p>
)}

{isWarning && !isError && (
  <p className="mt-2 text-sm text-yellow-400">
    Approaching character limit ({promptLength}/{MAX_CHARS})
  </p>
)}
```

**Test Cases**:
- [ ] Textarea border gray on empty
- [ ] Border turns yellow at 1800 chars
- [ ] Border turns red at 2000 chars
- [ ] Warning message appears/disappears correctly

---

### FIX 8: Add Success Confirmation Toast
**Priority**: LOW | **Effort**: 0.5h | **Files**: `frontend/pages/dashboard.tsx`

**Current State**:
```tsx
const handleCreateJob = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!prompt.trim()) return;

  setIsCreating(true);
  try {
    await createJob(prompt, pipeline);
    setPrompt('');
  } catch (error) {
    // Handle error
  } finally {
    setIsCreating(false);
  }
};
```

**Issue**: No confirmation feedback to user; job creation feels silent

**Solution**:
```tsx
import { useToastStore } from '../store/toast';

const handleCreateJob = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!prompt.trim()) return;

  setIsCreating(true);
  try {
    await createJob(prompt, pipeline);
    setPrompt('');

    // Show success toast
    useToastStore.getState().addToast({
      id: `job-created-${Date.now()}`,
      message: 'Research job created successfully',
      type: 'success',
      duration: 2000
    });
  } catch (error) {
    useToastStore.getState().addToast({
      id: `job-error-${Date.now()}`,
      message: error instanceof Error ? error.message : 'Failed to create job',
      type: 'error',
      duration: 5000
    });
  } finally {
    setIsCreating(false);
  }
};
```

**Test Cases**:
- [ ] Toast appears after successful job creation
- [ ] Toast shows "Research job created successfully"
- [ ] Toast auto-dismisses after 2 seconds
- [ ] Error toast shows on failure

---

### FIX 9: Display Completion Time for Finished Jobs
**Priority**: LOW | **Effort**: 0.5h | **Files**: `frontend/components/JobCard.tsx`

**Current State**:
```tsx
<div>
  <h4 className="text-xs font-medium text-gray-500 uppercase">Elapsed</h4>
  <p className="text-sm text-gray-300">{elapsed}</p>
</div>
```

**Issue**: Shows total elapsed time but not actual job duration

**Solution**:
```tsx
// In JobCard.tsx, modify the time display
const jobDuration = job.status === 'completed'
  ? calculateDuration(job.created_at, job.completed_at)
  : null;

// In expanded section:
<div className="flex gap-6">
  <div>
    <h4 className="text-xs font-medium text-gray-500 uppercase">Elapsed</h4>
    <p className="text-sm text-gray-300">{elapsed}</p>
  </div>
  {jobDuration && job.status === 'completed' && (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase">Processing Time</h4>
      <p className="text-sm text-green-400">{jobDuration}</p>
    </div>
  )}
</div>

// Helper function
function calculateDuration(startStr: string, endStr: string): string {
  const start = new Date(startStr);
  const end = new Date(endStr);
  const seconds = Math.floor((end.getTime() - start.getTime()) / 1000);

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
}
```

**Backend Changes Required**:
- Ensure `completed_at` timestamp is stored in job record when job completes
- Job model should have: `completed_at: Optional[str] = None`

**Test Cases**:
- [ ] Completed jobs show "Processing Time: 5m 32s"
- [ ] Time format correct for durations under 1 minute
- [ ] Time format correct for durations over 1 hour
- [ ] Running jobs don't show processing time (only shows elapsed)

---

### FIX 10: Open Results Links in New Tab
**Priority**: LOW | **Effort**: 0.25h | **Files**: `frontend/components/job-card/JobResults.tsx`

**Current State**:
```tsx
<a href={driveFolderUrl} className="...">
  View Results on Google Drive
</a>
```

**Issue**: Link opens in same tab; user loses dashboard navigation

**Solution**:
```tsx
<a
  href={driveFolderUrl}
  target="_blank"
  rel="noopener noreferrer"
  className="... inline-flex items-center gap-2"
>
  View Results on Google Drive
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>
</a>
```

**Test Cases**:
- [ ] Link opens in new tab
- [ ] External link icon visible
- [ ] Dashboard remains accessible in original tab

---

## Implementation Checklist

### Sprint 1 (5 items, ~4 hours)
- [ ] Add progress percentage to progress bar
- [ ] Implement pipeline mode tooltips
- [ ] Implement session timeout notification
- [ ] Add character counter
- [ ] Add inline validation for prompt

### Sprint 2 (5 items, ~3.25 hours)
- [ ] Optimize stage update frequency
- [ ] Add artifacts preview tooltip
- [ ] Add success confirmation toast
- [ ] Display completion time
- [ ] Open links in new tab

### Accessibility Follow-up (1-2 hours)
- [ ] Test gradient text with WAVE/axe accessibility checker
- [ ] Verify keyboard focus indicators
- [ ] Add sr-only labels where needed

---

## Testing Checklist

Before marking each fix as "done", verify:

- [ ] Feature works on desktop (Chrome, Safari, Firefox)
- [ ] Feature works on mobile (iOS Safari, Chrome Android)
- [ ] No console errors logged
- [ ] TypeScript type checking passes
- [ ] Linting passes (`npm run lint`)
- [ ] Build succeeds (`npm run build`)
- [ ] No visual regressions in related components
- [ ] Accessibility features intact (focus states, labels, etc.)

---

## Questions to Clarify Before Implementation

1. **Toast Component**: Does a toast/notification system already exist in the codebase? Search for `useToastStore` or similar.

2. **Backend Artifact Data**: When a job completes, does `job.artifacts` include separate URLs for NotebookLM packet vs Documentary Blueprint? Or just a folder URL?

3. **Job Timestamps**: Does `Job` model include `completed_at` field? Needed for completion time calculation.

4. **Pipeline Details**: Should pipeline budget details come from frontend constants or be fetched from backend `/config` endpoint?

5. **Tooltip Library**: Is there a preferred tooltip library (Radix UI Popover, Headless UI, simple CSS, etc.)?

---

## Implementation Validation Script

After implementing fixes, use this checklist to verify:

```typescript
// Test each fix
const fixes = [
  {
    name: 'Progress bar percentage',
    test: () => {
      const progressText = document.querySelector('[data-test="progress-percent"]');
      return progressText?.textContent === '68%';
    }
  },
  {
    name: 'Pipeline tooltip',
    test: () => {
      const tooltip = document.querySelector('[data-test="pipeline-info"]');
      return tooltip?.textContent.includes('URLs');
    }
  },
  // ... continue for each fix
];
```

---

**Report Complete** | Ready for development sprint planning
