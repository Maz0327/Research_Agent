---
title: "Job Detail Page UX Refactor"
description: "Add dedicated job detail page with artifact cards, simplify dashboard, improve secondary task visibility"
status: pending
priority: P1
effort: 16h
branch: main
tags: [frontend, ux, dashboard, refactor]
created: 2026-01-23
---

# Job Detail Page UX Refactor

## Summary

Refactor job UX to address four core issues:
1. Secondary task status invisible without expansion
2. No polling for booster/iteration/producer after main job completes
3. Confusing output location for iteration results
4. Cluttered dashboard with everything in expandable cards

**Solution:** New `/jobs/[id]` detail page + simplified dashboard with navigation links.

---

## Phase 1: Add Job Detail Page (Foundation)

**Goal:** Create `/jobs/[id]` route with basic document viewing, move complex UI from JobCard.

### Task 1.1: Create Job Detail Page Route

**File:** `frontend/pages/jobs/[id].tsx` (NEW)

**Changes:**
- Create Next.js dynamic route page
- Wrap in `ProtectedRoute` for auth
- Fetch single job via store/API
- Basic layout: header + content area

**Complexity:** Low (1h)

**Dependencies:** None

```tsx
// Key structure
export default function JobDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  // Fetch job, render layout
}
```

---

### Task 1.2: Create JobDetailHeader Component

**File:** `frontend/components/job-detail/JobDetailHeader.tsx` (NEW)

**Changes:**
- Back button (link to `/dashboard`)
- Job title display
- Status badge (reuse existing `StatusBadge`)
- Created date (relative format)
- Action buttons: Archive, Delete

**Complexity:** Low (1h)

**Dependencies:** Task 1.1

**Props:**
```tsx
interface JobDetailHeaderProps {
  jobId: string;
  title: string;
  status: JobStatus;
  createdAt: string;
  onArchive: () => void;
  onDelete: () => void;
}
```

---

### Task 1.3: Create ActiveTaskBanner Component

**File:** `frontend/components/job-detail/ActiveTaskBanner.tsx` (NEW)

**Changes:**
- Conditionally render when secondary task active (booster/iteration/producer)
- Show task type, progress bar, percentage
- Cancel button
- Pulsing animation for queued state

**Complexity:** Medium (1.5h)

**Dependencies:** Task 1.1

**Props:**
```tsx
interface ActiveTaskBannerProps {
  taskType: 'booster' | 'iteration' | 'producer';
  status: 'queued' | 'running';
  progressPercent: number;
  iterationId?: string; // For iteration tasks
  onCancel?: () => void;
}
```

---

### Task 1.4: Create ArtifactCard Component

**File:** `frontend/components/job-detail/ArtifactCard.tsx` (NEW)

**Changes:**
- Individual card for each artifact type (Doc 0/1/2/3, Booster, Iterations)
- Visual states: not_available, ready, queued, running, completed, failed
- Click handler for view/trigger actions
- Progress indicator for running state

**Complexity:** Medium (2h)

**Dependencies:** Task 1.1

**Props:**
```tsx
interface ArtifactCardProps {
  type: 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3' | 'booster' | 'iteration';
  state: 'not_available' | 'ready' | 'queued' | 'running' | 'completed' | 'failed';
  progressPercent?: number;
  error?: string;
  onClick: () => void;
  onRetry?: () => void;
}
```

---

### Task 1.5: Create ArtifactCardGrid Component

**File:** `frontend/components/job-detail/ArtifactCardGrid.tsx` (NEW)

**Changes:**
- Grid layout (3 cols desktop, 1 col mobile)
- Orchestrate ArtifactCard components
- Determine card states from job data
- Handle click routing (view document vs trigger action)

**Complexity:** Medium (2h)

**Dependencies:** Task 1.4

**Reuses:**
- `DocumentViewerModal` from `job-card/`
- Document fetching logic from `DocumentCardGrid.tsx`

---

### Task 1.6: Create Barrel Export

**File:** `frontend/components/job-detail/index.ts` (NEW)

**Changes:**
- Export all job-detail components
- Export types

**Complexity:** Trivial (0.25h)

**Dependencies:** Tasks 1.2-1.5

---

### Task 1.7: Wire Up Detail Page

**File:** `frontend/pages/jobs/[id].tsx`

**Changes:**
- Import job-detail components
- Compose full page layout
- Add job refresh on mount
- Add polling for active secondary tasks

**Complexity:** Medium (1.5h)

**Dependencies:** Tasks 1.1-1.6

---

### Task 1.8: Add Store Methods for Single Job

**File:** `frontend/store/jobs.ts`

**Changes:**
- Add `fetchSingleJob(jobId: string)` method
- Add `selectedJobId` state
- Update polling logic to support secondary tasks

**Complexity:** Low (1h)

**Dependencies:** None (can parallel with UI tasks)

---

### Phase 1 Checkpoint

**Criteria:**
- [ ] `/jobs/[id]` renders with header and artifact grid
- [ ] Clicking card opens DocumentViewerModal
- [ ] Active tasks show progress banner
- [ ] Navigation from dashboard works
- [ ] Tests pass: `npm test -- job-detail`

---

## Phase 2: Simplify Dashboard (Update Existing)

**Goal:** Reduce dashboard JobCard complexity, add active task badges, link to detail page.

### Task 2.1: Add TaskBadges Component

**File:** `frontend/components/job-card/TaskBadges.tsx` (NEW)

**Changes:**
- Mini chip badges for active/completed tasks
- Booster: `Running 75%` / `Deep Research`
- Producer: `Doc 3...` / `Doc 3`
- Iteration: `it_0002 45%` / `2 iterations`

**Complexity:** Low (1h)

**Dependencies:** None

**Props:**
```tsx
interface TaskBadgesProps {
  boosterStatus?: 'queued' | 'running' | 'completed' | 'failed' | null;
  boosterProgressPercent?: number;
  producerStatus?: 'queued' | 'running' | 'completed' | 'failed' | null; // TODO: Backend may need to add this
  iterationStatus?: 'queued' | 'running' | 'completed' | 'failed' | null;
  iterationProgressPercent?: number;
  iterationCount?: number;
}
```

---

### Task 2.2: Simplify JobCard Component

**File:** `frontend/components/JobCard.tsx`

**Changes:**
- Remove Level 2 (full expansion) code
- Remove JobResults render from card
- Keep Level 0/1 only
- Add TaskBadges to header
- Make entire card clickable -> navigate to `/jobs/[id]`
- Update aria labels

**Complexity:** Medium (1.5h)

**Dependencies:** Task 2.1

**Before/After:**
```tsx
// BEFORE: 3 expansion levels, full results inline
// AFTER: 2 levels max, click navigates to detail

const handleCardClick = () => {
  router.push(`/jobs/${job.id}`);
};
```

---

### Task 2.3: Update Polling Logic for Secondary Tasks

**File:** `frontend/store/jobs.ts`

**Changes:**
- Update `shouldPoll` logic to include secondary tasks
- Poll completed jobs if booster/iteration/producer running

**Complexity:** Low (0.5h)

**Dependencies:** None

```tsx
// NEW polling condition
const shouldPoll = (job: Job) =>
  job.status === 'queued' ||
  job.status === 'running' ||
  job.booster_status === 'running' ||
  job.booster_status === 'queued' ||
  job.iteration_status === 'running' ||
  job.iteration_status === 'queued';
  // TODO: Add producer_status when backend supports it
```

---

### Task 2.4: Update Dashboard to Use Router

**File:** `frontend/pages/dashboard.tsx`

**Changes:**
- Import `useRouter`
- Pass router to JobCard if needed
- Alternatively, use `onClick` handler in JobCard

**Complexity:** Trivial (0.5h)

**Dependencies:** Task 2.2

---

### Phase 2 Checkpoint

**Criteria:**
- [ ] Dashboard cards show task badges
- [ ] Clicking card navigates to detail page
- [ ] No more Level 2 expansion on dashboard
- [ ] Polling continues for jobs with active secondary tasks
- [ ] Tests pass: `npm test`

---

## Phase 3: Enhance Detail Page (Polish)

**Goal:** Add iteration version selector, polish card states, add transitions.

### Task 3.1: Create IterationSelector Component

**File:** `frontend/components/job-detail/IterationSelector.tsx` (NEW)

**Changes:**
- Dropdown to select iteration version (Baseline, it_0001, it_0002...)
- Show iteration metadata (created_at, status)
- Emit selected version to parent

**Complexity:** Medium (1.5h)

**Dependencies:** Phase 1 complete

**Props:**
```tsx
interface IterationSelectorProps {
  iterations: IterationBundle[];
  selectedVersion: string; // 'baseline' | 'it_0001' | ...
  onSelectVersion: (version: string) => void;
}
```

---

### Task 3.2: Add Iteration Support to ArtifactCardGrid

**File:** `frontend/components/job-detail/ArtifactCardGrid.tsx`

**Changes:**
- Render IterationSelector when iterations exist
- Switch displayed documents based on selected iteration
- Add "Run New Pass" button within iterations card

**Complexity:** Medium (1.5h)

**Dependencies:** Task 3.1

---

### Task 3.3: Add Store Support for Iteration Selection

**File:** `frontend/store/jobs.ts`

**Changes:**
- Add `selectedIterationVersion` state
- Add `selectIterationVersion(version: string)` action
- Persist in session (optional)

**Complexity:** Low (0.5h)

**Dependencies:** Task 3.1

---

### Task 3.4: Polish Card States and Transitions

**File:** `frontend/components/job-detail/ArtifactCard.tsx`

**Changes:**
- Add Framer Motion animations
- Polish visual states (borders, backgrounds)
- Add hover effects
- Improve accessibility (focus states, aria)

**Complexity:** Low (1h)

**Dependencies:** Task 1.4 complete

---

### Task 3.5: Add Loading States

**File:** `frontend/pages/jobs/[id].tsx`

**Changes:**
- Add skeleton loader while job fetches
- Handle 404 (job not found)
- Handle unauthorized (redirect to login)

**Complexity:** Low (0.5h)

**Dependencies:** Task 1.7 complete

---

### Phase 3 Checkpoint

**Criteria:**
- [ ] Iteration dropdown works
- [ ] Selecting iteration updates displayed docs
- [ ] Card animations smooth
- [ ] Loading/error states polished
- [ ] All tests pass

---

## File Summary

### New Files (9)

| File | Description |
|------|-------------|
| `pages/jobs/[id].tsx` | Job detail page route |
| `components/job-detail/index.ts` | Barrel export |
| `components/job-detail/JobDetailHeader.tsx` | Header with title, status, actions |
| `components/job-detail/ActiveTaskBanner.tsx` | Progress banner for secondary tasks |
| `components/job-detail/ArtifactCard.tsx` | Individual artifact card |
| `components/job-detail/ArtifactCardGrid.tsx` | Grid of artifact cards |
| `components/job-detail/IterationSelector.tsx` | Dropdown for iteration version |
| `components/job-card/TaskBadges.tsx` | Mini badges for dashboard cards |
| `__tests__/job-detail/*.test.tsx` | Test files |

### Modified Files (3)

| File | Changes |
|------|---------|
| `components/JobCard.tsx` | Simplify, add badges, make navigable |
| `store/jobs.ts` | Add single job fetch, iteration selection, polling updates |
| `pages/dashboard.tsx` | Minor: router integration |

### Reused (No Changes)

| File | Reused In |
|------|-----------|
| `components/job-card/StatusBadge.tsx` | JobDetailHeader |
| `components/job-card/DocumentViewerModal.tsx` | ArtifactCardGrid |
| `components/job-card/job-card-config.ts` | Card styling config |

---

## Dependency Graph

```
Phase 1:
  1.1 ──┬─► 1.2 ──┐
        │        │
        ├─► 1.3  │
        │        │
        └─► 1.4 ─┴─► 1.5 ──► 1.6 ──► 1.7

  1.8 (parallel) ─────────────────────► 1.7

Phase 2:
  2.1 ──► 2.2 ──► 2.4
  2.3 (parallel)

Phase 3:
  3.1 ──► 3.2
  3.3 (parallel with 3.1)
  3.4 (parallel)
  3.5 (parallel)
```

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| More navigation clicks to view results | Add "View Latest" quick action on dashboard; keyboard shortcuts |
| Increased polling load | Debounce requests; batch refresh; only poll jobs with active tasks |
| Route complexity | Use Next.js dynamic routes; keep flat structure; add breadcrumbs |
| Mobile responsiveness | Design mobile-first; test on devices; stack cards vertically |
| State drift between dashboard/detail | Single source of truth in store; refresh on focus |

---

## Testing Strategy

### Unit Tests
- `ArtifactCard`: State rendering, click handlers
- `TaskBadges`: Badge visibility logic
- `IterationSelector`: Selection behavior

### Integration Tests
- Job detail page renders with mocked data
- Navigation from dashboard to detail
- Polling behavior with secondary tasks

### E2E Tests (Optional)
- Create job -> wait for completion -> view detail page
- Trigger booster -> verify progress banner

---

## Open Questions

1. **Producer status tracking** - Backend currently lacks `producer_status` field. Need backend change or derive from artifacts?
2. **Cancel secondary task** - Is there an API endpoint to cancel booster/iteration mid-flight?
3. **Deep Research rename?** - "Booster" is internal jargon. Should UI use "Deep Research" consistently?

---

## Estimated Timeline

| Phase | Tasks | Effort | Cumulative |
|-------|-------|--------|------------|
| Phase 1 | 1.1-1.8 | 10h | 10h |
| Phase 2 | 2.1-2.4 | 3.5h | 13.5h |
| Phase 3 | 3.1-3.5 | 5h | 18.5h |

**Buffer:** ~2h for testing, bug fixes, polish

**Total:** ~16-20h implementation time

---

## Next Steps

1. Begin Phase 1.1: Create `/jobs/[id]` page skeleton
2. Create component files with basic structure
3. Implement incrementally, test after each task
4. Checkpoint at end of each phase
