# Debugger Report: Iteration Module Shows Old Options

**Issue ID:** debugger-260125-2158-iteration-module-old-options
**Date:** 2026-01-25
**Reporter:** User
**Investigator:** Claude (debugger subagent ae31051)
**Severity:** High (UX/functionality mismatch)

---

## Executive Summary

Iteration dialog on Job Detail and Queue pages shows **legacy V1 iteration mode options** instead of **new V2 run type options**. Frontend uses deprecated modal while backend expects V2 run types.

**Root Cause:** IterationDialog component in `/jobs/[id].tsx` uses V1 mode options; no migration to V2 CreateRunRequest interface.

**Impact:** Users see old options (`more_sources`, `deeper`, `different_angle`, `custom`) that don't match new run types (`add_sources`, `fix_weak`, `counter`, `angle`, `regenerate`).

**Status:** Modal not updated after V2 run abstraction introduced (commits `95c779a`, `a79267e`, `da72e2a`).

---

## Technical Analysis

### 1. Evidence from Code

#### Frontend Modal (Current - WRONG)
**File:** `frontend/pages/jobs/[id].tsx` lines 82-91

```tsx
<select
  value={mode}
  onChange={(e) => setMode(e.target.value as IterationRequest['mode'])}
>
  <option value="more_sources">Find More Sources</option>
  <option value="deeper">Deeper Analysis</option>
  <option value="different_angle">Different Angle</option>
  <option value="custom">Custom (User Prompt)</option>
</select>
```

**Interface:** `frontend/store/jobs.ts` lines 391-400
```typescript
export interface IterationRequest {
  mode: 'more_sources' | 'deeper' | 'different_angle' | 'custom';
  user_prompt?: string;
  max_new_sources?: number;
  angle?: string;
}
```

#### Backend API (Expected - CORRECT)
**File:** `backend/app/routes/jobs_routes.py` lines 1867-1870

```python
class CreateRunRequest(PydanticBaseModel):
    run_type: str = PydanticField(
        ...,
        description="Run type: add_sources, fix_weak, counter, angle, regenerate"
    )
```

**Valid run types:** (line 1972)
```python
valid_run_types = ["add_sources", "fix_weak", "counter", "angle", "regenerate"]
```

### 2. Type Definitions Exist But Not Used

**File:** `frontend/types/run.ts` lines 11-27

New V2 run types ALREADY DEFINED:
```typescript
export type RunType =
  | 'baseline'
  | 'add_sources'
  | 'fix_weak'
  | 'counter'
  | 'angle'
  | 'regenerate';

export const RUN_TYPE_LABELS: Record<RunType, string> = {
  baseline: 'Baseline',
  add_sources: 'Add Sources',
  fix_weak: 'Fix Weak Spots',
  counter: 'Counterargument',
  angle: 'Different Angle',
  regenerate: 'Regenerate',
};
```

### 3. RunSelector Component Already Migrated

**File:** `frontend/components/job-detail/RunSelector.tsx`

✅ **RunSelector CORRECTLY displays V2 runs** with new labels:
- Shows `run_0` (Baseline)
- Shows `run_1+` with V2 run type labels (`Add Sources`, `Fix Weak Spots`, etc.)
- Falls back to V1 iterations for legacy jobs

### 4. IterationDialog NOT Migrated

**Current State:**
- IterationDialog still sends V1 `IterationRequest` with old modes
- triggerIteration() in store sends to DEPRECATED endpoint `/jobs/{job_id}/iterate`
- Backend endpoint marked `deprecated=True` (line 1641)

**Deprecated Endpoint:** `backend/app/routes/jobs_routes.py` line 1650
```python
"""
DEPRECATED: Use POST /{job_id}/runs instead.

This V1 iteration endpoint is deprecated as of 2026-01-26.
New code should use the V2 Run Abstraction via POST /jobs/{job_id}/runs.
```

---

## Root Cause Chain

1. **Phase 10** (V2 Run Abstraction) introduced new run types
2. **RunSelector** component created and migrated to V2 (commit `95c779a`)
3. **IterationSelector** deleted (commit `da72e2a`)
4. **IterationDialog** in `jobs/[id].tsx` NOT updated - still uses V1 modes
5. **Store method** `triggerIteration()` still calls deprecated `/iterate` endpoint
6. **Result:** Modal shows old options, selector shows new options → confusion

---

## Affected Components

### Pages
1. ✅ `/jobs/[id].tsx` - Job Detail page (uses IterationDialog)
2. ✅ `/queue.tsx` - Queue page (no iteration dialog, only shows completed runs)

### Components
1. ❌ **IterationDialog** (inline in `/jobs/[id].tsx` lines 34-178) - NEEDS UPDATE
2. ✅ **RunSelector** (`frontend/components/job-detail/RunSelector.tsx`) - ALREADY CORRECT
3. ✅ **ArtifactCardGrid** (`frontend/components/job-detail/ArtifactCardGrid.tsx`) - ALREADY CORRECT

### Store
1. ❌ **jobs.ts** - `triggerIteration()` method (line 936) - NEEDS UPDATE
2. ❌ **jobs.ts** - `IterationRequest` interface (line 391) - NEEDS REPLACEMENT

---

## Expected vs Actual Behavior

### Expected (V2 Behavior)
1. User clicks "Iterations" card
2. Modal opens with V2 run type options:
   - **Add Sources** (find more sources)
   - **Fix Weak Spots** (address gaps from Doc 1)
   - **Counterargument** (find opposing views)
   - **Different Angle** (explore new perspective)
   - **Regenerate** (re-synthesize same sources)
3. User selects run type, optionally adds prompt
4. Frontend calls `POST /jobs/{job_id}/runs` with `CreateRunRequest`
5. Backend creates V2 Run object
6. RunSelector shows new run after completion

### Actual (V1 Behavior)
1. User clicks "Iterations" card
2. Modal opens with V1 iteration modes:
   - **Find More Sources** (`more_sources`)
   - **Deeper Analysis** (`deeper`)
   - **Different Angle** (`different_angle`)
   - **Custom** (`custom`)
3. User selects mode
4. Frontend calls `POST /jobs/{job_id}/iterate` (DEPRECATED)
5. Backend processes V1 iteration (creates IterationBundle)
6. RunSelector shows iteration but labels as "V1 ITERATIONS (legacy)"

---

## Files Requiring Changes

### 1. Frontend Types
**File:** `frontend/store/jobs.ts`

**Change:**
- ❌ Delete `IterationRequest` interface (line 391)
- ❌ Delete `IterationResponse` interface (line 405)
- ✅ Add `CreateRunRequest` interface matching backend
- ✅ Add `CreateRunResponse` interface matching backend

### 2. Store Method
**File:** `frontend/store/jobs.ts`

**Method:** `triggerIteration` (line 936)

**Change:**
- Rename to `createRun`
- Update to call `POST /jobs/{job_id}/runs`
- Accept `CreateRunRequest` instead of `IterationRequest`
- Return `CreateRunResponse`

### 3. Iteration Dialog Component
**File:** `frontend/pages/jobs/[id].tsx`

**Component:** `IterationDialog` (lines 34-178)

**Changes:**
- Replace mode dropdown with run_type dropdown
- Update options to V2 run types:
  ```tsx
  <option value="add_sources">Add Sources</option>
  <option value="fix_weak">Fix Weak Spots</option>
  <option value="counter">Counterargument</option>
  <option value="angle">Different Angle</option>
  <option value="regenerate">Regenerate</option>
  ```
- Remove V1-specific fields (`angle` input for `different_angle` mode)
- Add V2-specific fields if needed:
  - `parent_run_id` (default: `run_0`)
  - `gap_ids` (for `fix_weak` type)
  - `claim_ids` (for `counter` type)
  - `perspective` (for `angle` type)
- Update state interface to match `CreateRunRequest`

### 4. Modal Handler
**File:** `frontend/pages/jobs/[id].tsx`

**Function:** `handleTriggerIteration` (line 276)

**Change:**
- Rename to `handleCreateRun`
- Call `createRun()` instead of `triggerIteration()`
- Pass `CreateRunRequest` instead of `IterationRequest`

### 5. Props Update
**File:** `frontend/components/job-detail/ArtifactCardGrid.tsx`

**Prop:** `onOpenIterationDialog` (line 32)

**Change:**
- Rename to `onOpenRunDialog` or keep name for backwards compat
- Ensure it opens updated modal with V2 options

---

## Implementation Plan

### Phase 1: Update Types (5 min)
1. Add `CreateRunRequest` interface to `frontend/store/jobs.ts`
2. Add `CreateRunResponse` interface to `frontend/store/jobs.ts`
3. Mark `IterationRequest` as deprecated (add JSDoc comment)

### Phase 2: Update Store (10 min)
1. Add new `createRun()` method to jobs store
2. Keep `triggerIteration()` for backwards compat (calls deprecated endpoint)
3. Test new method with Postman/curl

### Phase 3: Update Modal (20 min)
1. Rename `IterationDialog` to `RunDialog` or `CreateRunDialog`
2. Replace mode state with `run_type` state
3. Update dropdown options to V2 run types
4. Add run type descriptions
5. Remove V1-specific conditional inputs
6. Update submit handler to use `CreateRunRequest` format

### Phase 4: Wire Up (10 min)
1. Update `handleTriggerIteration` to `handleCreateRun`
2. Update modal callback to use `createRun()` store method
3. Update ArtifactCardGrid prop names if needed

### Phase 5: Test (15 min)
1. Test each run type creation
2. Verify RunSelector shows new runs
3. Verify old V1 iterations still display (legacy support)
4. Check error handling for invalid run types

### Total Estimated Time: 60 minutes

---

## Testing Checklist

- [ ] Modal opens with V2 run types
- [ ] Each run type submits correctly
- [ ] RunSelector updates with new run after completion
- [ ] Legacy V1 iterations still visible in RunSelector
- [ ] Error handling works (invalid run type, job not completed)
- [ ] Run-scoped Producer/Booster work after run completes
- [ ] Queue page unaffected (doesn't show modal)

---

## Additional Context

### Git History
```
da72e2a - chore: remove legacy IterationSelector, deprecate /iterate endpoint
a79267e - feat(frontend): integrate RunSelector in ArtifactCardGrid
95c779a - feat(frontend): add V2 run types and RunSelector component
```

### Related Files
- `backend/models/run_models.py` - Run/RunType backend models
- `backend/pipeline/runs/` - V2 run execution logic
- `backend/worker.py` - `run_iteration_task` wires to V2 modes

---

## Recommendations

### Immediate (Fix Issue)
1. Update IterationDialog with V2 run types
2. Update store to call V2 endpoint
3. Test all run types

### Future Cleanup
1. Remove deprecated `/iterate` endpoint after migration
2. Remove `IterationRequest`/`IterationResponse` types
3. Remove `triggerIteration()` store method
4. Add migration notice for V1 jobs in UI

### UX Improvements
1. Add tooltips explaining each run type
2. Show examples of when to use each type
3. Disable irrelevant run types based on job state
4. Show parent run selector (currently hardcoded to `run_0`)

---

## Unresolved Questions

1. Should we support creating runs from non-baseline parents? (UI currently assumes `run_0`)
2. Should we expose `gap_ids`/`claim_ids` in modal for `fix_weak`/`counter` types?
3. When to fully remove V1 `/iterate` endpoint? (migration timeline?)
4. Should Queue page also show run creation modal? (currently only Job Detail has it)

---

**End of Report**
