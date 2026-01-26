---
title: "Migrate IterationDialog from V1 to V2 Run Types"
description: "Update frontend iteration modal to use V2 /runs endpoint with new run types"
status: done
priority: P2
effort: 2h
branch: main
tags: [frontend, iteration, v2-runs, migration]
created: 2026-01-25
completed: 2026-01-25
---

# Migrate IterationDialog from V1 to V2 Run Types

## Problem Summary

The IterationDialog in `frontend/pages/jobs/[id].tsx` and store in `frontend/store/jobs.ts` still use the deprecated V1 iteration system:

| Aspect | V1 (Current) | V2 (Expected) |
|--------|-------------|---------------|
| Options | `more_sources`, `deeper`, `different_angle`, `custom` | `add_sources`, `fix_weak`, `counter`, `angle`, `regenerate` |
| Endpoint | `POST /jobs/{id}/iterate` | `POST /jobs/{id}/runs` |
| Request Type | `IterationRequest` | `CreateRunRequest` |
| Response | `IterationResponse` | `CreateRunResponse` |

## Files to Modify

1. **`frontend/store/jobs.ts`** - Update types and API call
2. **`frontend/pages/jobs/[id].tsx`** - Update dialog UI and handlers
3. **`frontend/types/run.ts`** - Already exists with correct types (no changes)

## Phase 1: Update Store Types and API (30min)

### Task 1.1: Add V2 Run Request/Response Types

Add to `frontend/store/jobs.ts`:

```typescript
/**
 * V2 Run request parameters (replaces IterationRequest)
 */
export interface CreateRunRequest {
  /** Run type: add_sources, fix_weak, counter, angle, regenerate */
  run_type: 'add_sources' | 'fix_weak' | 'counter' | 'angle' | 'regenerate';
  /** Parent run ID to build on (default: run_0) */
  parent_run_id?: string;
  /** User guidance for the run */
  user_prompt?: string;
  /** URLs to add (for add_sources type) */
  new_source_urls?: string[];
  /** Max sources to add (for add_sources type) */
  max_new_sources?: number;
  /** Gap IDs to address (for fix_weak type) */
  gap_ids?: string[];
  /** Claim IDs to find counters for (for counter type) */
  claim_ids?: string[];
  /** New angle to explore (for angle type) */
  perspective?: string;
}

/**
 * V2 Run creation response
 */
export interface CreateRunResponse {
  job_id: string;
  run_id: string;
  run_index: number;
  run_type: string;
  parent_run_id: string;
  status: string;
  message: string;
}
```

### Task 1.2: Update triggerIteration to createRun

Rename and update the store method:

```typescript
// OLD:
triggerIteration: (jobId: string, request: IterationRequest) => Promise<IterationResponse>;

// NEW:
createRun: (jobId: string, request: CreateRunRequest) => Promise<CreateRunResponse>;
```

Implementation change:

```typescript
createRun: async (jobId: string, request: CreateRunRequest): Promise<CreateRunResponse> => {
  set({ actionInProgress: 'iteration' });
  try {
    const token = await getAccessToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // V2 endpoint
    const response = await fetch(`${API_URL}/jobs/${jobId}/runs`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        run_type: request.run_type,
        parent_run_id: request.parent_run_id || 'run_0',
        user_prompt: request.user_prompt || '',
        new_source_urls: request.new_source_urls || [],
        max_new_sources: request.max_new_sources || 4,
        gap_ids: request.gap_ids || [],
        claim_ids: request.claim_ids || [],
        perspective: request.perspective || '',
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(formatApiError(errorData, 'Failed to create run'));
    }

    const data: CreateRunResponse = await response.json();

    // Update job iteration status in local state
    set((state) => ({
      jobs: state.jobs.map((job) =>
        job.id === jobId
          ? {
              ...job,
              iteration_status: 'queued' as const,
              iteration_id: data.run_id,
            }
          : job
      ),
      actionInProgress: null,
    }));

    return data;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to create run';
    set({ error: message, actionInProgress: null });
    throw error;
  }
},
```

### Task 1.3: Keep Legacy triggerIteration as Alias (Optional)

For backward compatibility during transition:

```typescript
// Deprecated alias - remove after all callers migrate
triggerIteration: async (jobId: string, request: IterationRequest): Promise<IterationResponse> => {
  // Map V1 mode to V2 run_type
  const modeToRunType: Record<string, CreateRunRequest['run_type']> = {
    'more_sources': 'add_sources',
    'deeper': 'fix_weak',
    'different_angle': 'angle',
    'custom': 'regenerate',
  };

  const runRequest: CreateRunRequest = {
    run_type: modeToRunType[request.mode] || 'regenerate',
    user_prompt: request.user_prompt,
    max_new_sources: request.max_new_sources,
    perspective: request.angle,
  };

  const response = await get().createRun(jobId, runRequest);

  // Map V2 response to V1 format
  return {
    job_id: response.job_id,
    iteration_id: response.run_id,
    iteration_index: response.run_index,
    status: response.status,
    message: response.message,
  };
},
```

## Phase 2: Update IterationDialog Component (45min)

### Task 2.1: Update State Variables

In `frontend/pages/jobs/[id].tsx`, change the IterationDialog state:

```typescript
// OLD:
const [mode, setMode] = useState<IterationRequest['mode']>('more_sources');

// NEW:
type RunType = 'add_sources' | 'fix_weak' | 'counter' | 'angle' | 'regenerate';
const [runType, setRunType] = useState<RunType>('add_sources');
const [perspective, setPerspective] = useState('');
```

### Task 2.2: Update Dropdown Options

Replace the mode select with V2 run types:

```tsx
<select
  value={runType}
  onChange={(e) => setRunType(e.target.value as RunType)}
  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-gray-100 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
>
  <option value="add_sources">Add More Sources</option>
  <option value="fix_weak">Fix Weak Spots</option>
  <option value="counter">Find Counterarguments</option>
  <option value="angle">Different Angle</option>
  <option value="regenerate">Regenerate Analysis</option>
</select>
```

### Task 2.3: Update Description Text

```tsx
<p className="text-xs text-gray-500 mt-1">
  {runType === 'add_sources' && 'Search for additional sources to expand coverage'}
  {runType === 'fix_weak' && 'Address gaps and weaknesses in the analysis'}
  {runType === 'counter' && 'Find opposing viewpoints and counterarguments'}
  {runType === 'angle' && 'Explore a different perspective on the topic'}
  {runType === 'regenerate' && 'Re-run synthesis with current sources'}
</p>
```

### Task 2.4: Update Conditional Fields

Replace `different_angle` input with `angle` and rename state:

```tsx
{/* Perspective input (for angle run type) */}
{runType === 'angle' && (
  <div className="mb-4">
    <label className="block text-sm font-medium text-gray-300 mb-2">
      Perspective to Explore
    </label>
    <input
      type="text"
      value={perspective}
      onChange={(e) => setPerspective(e.target.value)}
      placeholder="e.g., economic impact, environmental concerns"
      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-gray-100 text-sm placeholder-gray-500 focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
    />
  </div>
)}

{/* Max new sources (for add_sources run type) */}
{runType === 'add_sources' && (
  <div className="mb-4">
    <label className="block text-sm font-medium text-gray-300 mb-2">
      Max New Sources: {maxNewSources}
    </label>
    <input
      type="range"
      min={1}
      max={10}
      value={maxNewSources}
      onChange={(e) => setMaxNewSources(Number(e.target.value))}
      className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
    />
    <div className="flex justify-between text-xs text-gray-500 mt-1">
      <span>1</span>
      <span>10</span>
    </div>
  </div>
)}
```

### Task 2.5: Update handleSubmit

```tsx
const handleSubmit = () => {
  const request: CreateRunRequest = {
    run_type: runType,
    parent_run_id: 'run_0', // Default to baseline
    user_prompt: userPrompt || undefined,
    max_new_sources: runType === 'add_sources' ? maxNewSources : undefined,
    perspective: runType === 'angle' ? perspective : undefined,
  };

  onSubmit(request);

  // Reset form
  setRunType('add_sources');
  setUserPrompt('');
  setMaxNewSources(4);
  setPerspective('');
};
```

### Task 2.6: Update Props Interface

```tsx
interface IterationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (request: CreateRunRequest) => void;  // Changed from IterationRequest
  isSubmitting: boolean;
}
```

### Task 2.7: Update Button Validation

```tsx
<button
  onClick={handleSubmit}
  disabled={isSubmitting || (runType === 'angle' && !perspective.trim())}
  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 disabled:cursor-not-allowed rounded-lg transition"
>
  {isSubmitting ? 'Starting...' : 'Start Run'}
</button>
```

## Phase 3: Update Page Handler (15min)

### Task 3.1: Update Handler in JobDetailContent

```tsx
// Import the new type
import type { CreateRunRequest } from '../../store/jobs';

// Update handler
const handleCreateRun = useCallback(
  async (request: CreateRunRequest) => {
    if (!jobId) return;
    await createRun(jobId, request);  // Changed from triggerIteration
    setIterationDialogOpen(false);
  },
  [jobId, createRun]
);
```

### Task 3.2: Update Store Destructure

```tsx
const {
  jobs,
  refreshJob,
  deleteJob,
  archiveJob,
  triggerBooster,
  triggerProducerPacket,
  createRun,  // Changed from triggerIteration
  actionInProgress,
} = useJobsStore();
```

### Task 3.3: Pass Handler to Dialog

```tsx
<IterationDialog
  isOpen={iterationDialogOpen}
  onClose={() => setIterationDialogOpen(false)}
  onSubmit={handleCreateRun}  // Changed from handleTriggerIteration
  isSubmitting={actionInProgress === 'iteration'}
/>
```

## Phase 4: Cleanup and Testing (30min)

### Task 4.1: Remove Deprecated Types

After confirming no other files use `IterationRequest`:

```bash
# Check for remaining usages
grep -r "IterationRequest" frontend/
```

If no external usages, remove from store:
- `IterationRequest` interface
- `IterationResponse` interface (keep for backward compat if needed)

### Task 4.2: Update Import in Page

```tsx
// Change from:
import { useJobsStore, type IterationRequest } from '../../store/jobs';

// To:
import { useJobsStore, type CreateRunRequest } from '../../store/jobs';
```

### Task 4.3: Manual Testing Checklist

- [ ] Dialog opens correctly
- [ ] All 5 run types appear in dropdown
- [ ] Description text updates per type
- [ ] "Add Sources" shows max sources slider
- [ ] "Different Angle" shows perspective input
- [ ] Submit sends correct payload to `/runs` endpoint
- [ ] Loading state shows during submission
- [ ] Dialog closes on successful submission
- [ ] Job polling picks up new iteration status

## Summary of Changes

| File | Changes |
|------|---------|
| `frontend/store/jobs.ts` | Add `CreateRunRequest`, `CreateRunResponse` types; add `createRun()` method; optionally keep `triggerIteration()` as alias |
| `frontend/pages/jobs/[id].tsx` | Update `IterationDialog` state, dropdown, descriptions, conditional fields, submit handler, props |
| `frontend/types/run.ts` | No changes (already has correct V2 types) |

## Unresolved Questions

1. **Parent run selection**: Current implementation defaults to `run_0`. Should the dialog allow selecting a different parent run for chained iterations?

2. **Gap/Claim IDs**: The V2 API supports `gap_ids` and `claim_ids` for targeted iterations. Should these be exposed in the dialog? If so, they'd need to be sourced from the semantic brief.

3. **Backward compatibility**: Should the legacy `/iterate` endpoint continue working or should it be removed from backend?
