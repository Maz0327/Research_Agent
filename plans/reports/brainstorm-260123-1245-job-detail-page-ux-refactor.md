# Brainstorm Report: Job Detail Page UX Refactor

**Date:** 2026-01-23
**Status:** Agreed
**Scope:** Frontend job/task UX overhaul

---

## Problem Statement

Current UX issues with job status and secondary tasks:

1. **Status invisibility** - Booster/iteration/producer status invisible without expanding job card
2. **No polling for secondary tasks** - Tasks don't auto-update after main job completes
3. **Confusing output location** - Users don't know where iteration/booster results appear
4. **Cluttered UI** - Everything crammed into one expandable card

---

## Agreed Solution: Job Detail Page + Dashboard Summary

### Architecture Overview

```
/dashboard                    /jobs/[id]
┌─────────────────────┐      ┌──────────────────────────────────────┐
│ Job Card (summary)  │      │ Job Detail Page                      │
│ ┌─────────────────┐ │      │ ┌──────────────────────────────────┐ │
│ │ Title + Status  │ │ ──→  │ │ Header: Title + Actions          │ │
│ │ 🔄 Booster 75%  │ │      │ └──────────────────────────────────┘ │
│ │ ✓ Doc 3 Ready   │ │      │ ┌──────────────────────────────────┐ │
│ └─────────────────┘ │      │ │ Progress Banner (if task active) │ │
│                     │      │ └──────────────────────────────────┘ │
│ Job Card 2...       │      │ ┌──────┐ ┌──────┐ ┌──────┐          │
│                     │      │ │Doc 0 │ │Doc 1 │ │Doc 2 │          │
└─────────────────────┘      │ └──────┘ └──────┘ └──────┘          │
                             │ ┌──────┐ ┌──────┐ ┌────────────────┐ │
                             │ │Booster│ │Doc 3 │ │ Iterations ▼  │ │
                             │ └──────┘ └──────┘ └────────────────┘ │
                             └──────────────────────────────────────┘
```

---

## Dashboard Changes

### Job Card (Simplified)

**Always visible:**
- Job title
- Overall status badge (queued/running/completed/failed)
- Created date (relative: "2 hours ago")

**Active task badges (mini chips):**
- `🔄 Booster 75%` - When booster running
- `✓ Deep Research` - When booster completed
- `🔄 Doc 3...` - When producer running
- `✓ Doc 3` - When producer completed
- `🔄 it_0002 45%` - When iteration running
- `✓ 2 iterations` - When iterations exist

**Click action:** Navigate to `/jobs/[id]`

### Polling Changes

**Current:** Only polls queued/running jobs
**New:** Also poll completed jobs with active secondary tasks:
```typescript
const shouldPoll = (job) =>
  job.status === 'queued' ||
  job.status === 'running' ||
  job.booster_status === 'running' ||
  job.booster_status === 'queued' ||
  job.iteration_status === 'running' ||
  job.iteration_status === 'queued' ||
  job.producer_status === 'running' ||
  job.producer_status === 'queued';
```

---

## Job Detail Page (`/jobs/[id]`)

### Layout Sections

#### 1. Header
```
┌─────────────────────────────────────────────────────────┐
│ ← Back to Dashboard                                     │
│                                                         │
│ [Title from job]                              [Archive] │
│ Status: Completed • Created 2 hours ago       [Delete]  │
└─────────────────────────────────────────────────────────┘
```

#### 2. Active Task Banner (conditional)
When booster/iteration/producer is running:
```
┌─────────────────────────────────────────────────────────┐
│ 🔄 Deep Research in progress... 75%          [Cancel]   │
│ ████████████████████░░░░░                               │
└─────────────────────────────────────────────────────────┘
```

#### 3. Artifact Cards Grid
```
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Doc 0   │ │  Doc 1   │ │  Doc 2   │
│  Source  │ │  Jump    │ │ Semantic │
│  Ledger  │ │  Start   │ │  Brief   │
│    ✓     │ │    ✓     │ │    ✓     │
└──────────┘ └──────────┘ └──────────┘

┌──────────┐ ┌──────────┐ ┌────────────────────┐
│  Booster │ │  Doc 3   │ │    Iterations      │
│   Deep   │ │ Producer │ │ ┌────────────────┐ │
│ Research │ │  Packet  │ │ │ Baseline ▼     │ │
│ [Start]  │ │ [Start]  │ │ │ it_0001        │ │
└──────────┘ └──────────┘ │ │ it_0002        │ │
                          │ └────────────────┘ │
                          │ [+ Run New Pass]   │
                          └────────────────────┘
```

### Card States

Each card has one of these states:

| State | Visual | Actions |
|-------|--------|---------|
| Not available | Grayed out, dashed border | None |
| Ready to trigger | Solid border, CTA button | [Start]/[Generate] |
| Queued | Pulsing border, spinner | [Cancel] |
| Running | Progress bar, percentage | [Cancel] |
| Completed | Green checkmark | [View] |
| Failed | Red X, error preview | [Retry] |

### Iteration Version Selector

The Iterations card has a dropdown to switch between versions:
```
┌────────────────────────────────────┐
│ Iterations                      ▼  │
│ ┌────────────────────────────────┐ │
│ │ ● Baseline (original)          │ │
│ │   it_0001 - More sources       │ │
│ │   it_0002 - Different angle    │ │
│ └────────────────────────────────┘ │
│                                    │
│ Currently viewing: Baseline        │
│ [View Documents] [+ New Iteration] │
└────────────────────────────────────┘
```

Selecting an iteration version updates which doc_0/doc_1/doc_2 the core document cards display.

---

## Technical Implementation

### New Files

```
frontend/
├── pages/
│   └── jobs/
│       └── [id].tsx          # Job detail page
├── components/
│   └── job-detail/
│       ├── JobDetailHeader.tsx
│       ├── ActiveTaskBanner.tsx
│       ├── ArtifactCard.tsx
│       ├── ArtifactCardGrid.tsx
│       ├── IterationSelector.tsx
│       └── index.ts
```

### Modified Files

```
frontend/
├── pages/
│   └── dashboard.tsx         # Simplify, add navigation
├── components/
│   └── job-card/
│       └── JobCard.tsx       # Add active task badges
├── store/
│   └── jobs.ts               # Update polling logic
```

### Store Changes

```typescript
// Add to jobs store
interface JobsState {
  // ... existing

  // For job detail page
  selectedJobId: string | null;
  selectedIterationVersion: string | null; // 'baseline' | 'it_0001' | ...

  // Actions
  selectJob: (jobId: string) => void;
  selectIterationVersion: (version: string) => void;
}
```

### Route Structure

```
/dashboard              → Job list with summary cards
/jobs/[id]              → Job detail page
/jobs/[id]/documents    → (optional) Full document viewer
```

---

## Migration Strategy

### Phase 1: Add Job Detail Page
1. Create `/jobs/[id]` route
2. Move document viewing logic from JobResults to new page
3. Dashboard cards link to detail page

### Phase 2: Simplify Dashboard
1. Remove full expansion from dashboard cards
2. Add active task badges
3. Update polling to include secondary tasks

### Phase 3: Enhance Detail Page
1. Add iteration version selector
2. Add activity timeline (optional)
3. Polish card states and transitions

---

## Success Metrics

1. **Discoverability** - User can see all task statuses from dashboard
2. **Progress visibility** - Running tasks show real-time progress
3. **Result clarity** - User knows exactly where outputs appear
4. **Scalability** - Pattern works for future features (more iteration types, etc.)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| More navigation clicks | Add "View Latest" quick action on dashboard |
| Polling load increase | Debounce + batch requests, only poll active jobs |
| Route complexity | Use Next.js dynamic routes, keep flat structure |
| Mobile responsiveness | Design mobile-first, stack cards vertically |

---

## Open Questions

1. **Should deep research be renamed?** Current "Booster" label is internal jargon
2. **Bulk actions on dashboard?** Select multiple jobs for archive/delete?
3. **Job comparison view?** Compare iterations side-by-side?

---

## Next Steps

1. Create detailed implementation plan with `/plan`
2. Design mockups for new layout (optional)
3. Implement Phase 1: Job Detail Page
4. Test with real jobs
5. Implement Phase 2-3

---

## Appendix: Component Hierarchy

```
JobDetailPage
├── JobDetailHeader
│   ├── BackButton
│   ├── JobTitle
│   ├── StatusBadge
│   └── ActionButtons (Archive, Delete)
├── ActiveTaskBanner (conditional)
│   ├── TaskIcon
│   ├── TaskLabel
│   ├── ProgressBar
│   └── CancelButton
├── ArtifactCardGrid
│   ├── ArtifactCard (Doc 0)
│   ├── ArtifactCard (Doc 1)
│   ├── ArtifactCard (Doc 2)
│   ├── ArtifactCard (Booster)
│   ├── ArtifactCard (Producer/Doc 3)
│   └── IterationCard
│       ├── IterationSelector
│       └── ActionButtons
└── DocumentViewerModal (existing, reused)
```
