# Phase 3: Core Pages — Dashboard + Queue + Job Creation

## Context
- Plan: [plan.md](plan.md)
- Depends on: [Phase 2](phase-02-layout-system-sidebar-columns.md) (AppShell layout)
- Current: `pages/dashboard.tsx` (945 lines), `pages/queue.tsx` (581 lines)
- Target: `app/(app)/dashboard/page.tsx`, `app/(app)/queue/page.tsx`

## Overview
| Field | Value |
|-------|-------|
| Date | 2026-03-18 |
| Priority | P1 |
| Status | pending |
| Effort | 8h |
| Description | Migrate dashboard (wizard job creation) + queue pages, integrate TanStack Query, adapt Zustand for UI-only state |

## Key Insights
- `dashboard.tsx` (945 lines) is the second largest page; contains job creation form, job list, preview/disambiguation flow
- `queue.tsx` (581 lines) has tabbed view (all/running/completed/failed)
- Zustand stores MUST have `'use client'` at top of file — they use browser APIs
- Server components can fetch initial data, pass to client components as props
- Job creation flow: redesigned as multi-step wizard (topic → sources → mode → preview → create)
- `jobs.ts` store (1926 lines) — data fetching moves to TanStack Query hooks; store keeps UI state only
- TanStack Query replaces manual polling (refetchInterval for active jobs)

## Requirements
1. Dashboard page in App Router with multi-step job creation wizard
2. Queue page with tabbed job list (shadcn/ui Tabs)
3. TanStack Query hooks for data fetching (useJobs, useJobDetail, useCreateJob, etc.)
4. Zustand stores slimmed to UI-only state (selectedTab, sortOrder, chatSheetOpen, etc.)
5. Auth-protected routes via middleware stub (full impl in Phase 7)
6. Job card component rebuilt with shadcn/ui Card + Badge
7. Auto-refetch via TanStack Query refetchInterval for active jobs

## Architecture

### Dashboard Page Decomposition
Current 945-line monolith splits into:
```
app/(app)/dashboard/page.tsx          # Server component, layout only
components/dashboard/
├── DashboardContent.tsx              # 'use client' — orchestrates all dashboard UI
├── JobCreationWizard.tsx             # Multi-step wizard container
├── WizardStepTopic.tsx              # Step 1: Topic input
├── WizardStepSources.tsx            # Step 2: Source URLs + types
├── WizardStepMode.tsx               # Step 3: Pipeline mode + niche selection
├── WizardStepPreview.tsx            # Step 4: Preview + disambiguation + confirm
├── RecentJobsList.tsx                # Recent jobs grid/list
└── DashboardStats.tsx                # Quick stats (total jobs, active, credits)
```

### TanStack Query Hooks
```
hooks/
├── use-jobs.ts                      # useJobs() — list with auto-refetch
├── use-job-detail.ts                # useJobDetail(id) — single job + polling
├── use-create-job.ts                # useCreateJob() — mutation
├── use-iterate-job.ts               # useIterateJob() — mutation
├── use-preview-job.ts               # usePreviewJob() — mutation
└── use-settings.ts                  # useSettings() — user settings query
```

### Queue Page Decomposition
```
app/(app)/queue/page.tsx              # Server component
components/queue/
├── QueueContent.tsx                  # 'use client' — tab container
├── QueueTabs.tsx                     # shadcn Tabs: All/Running/Completed/Failed
└── JobListItem.tsx                   # Compact job row for queue view
```

### Job Card Redesign
```
components/job/
├── JobCard.tsx                       # Card with status badge, title, source count, date
├── JobCardGrid.tsx                   # Grid layout for job cards
├── StatusBadge.tsx                   # shadcn Badge variants: running/completed/failed/queued
├── SourceTypeTags.tsx                # Tag badges for source types
└── JobActions.tsx                    # Quick actions dropdown (view, iterate, delete)
```

### Zustand Store Adaptation
Zustand keeps UI-only state; data fetching moves to TanStack Query:
```typescript
'use client';
import { create } from 'zustand';

// UI state only — no fetch logic
export const useJobsUIStore = create((set) => ({
  sortOrder: 'newest' as const,
  searchQuery: '',
  selectedTab: 'all' as const,
  chatSheetOpen: false,
  setSortOrder: (order) => set({ sortOrder: order }),
  // ... UI toggles only
}));
```

## Related Code Files
| File | Action | Notes |
|------|--------|-------|
| `pages/dashboard.tsx` | Reference → decompose | 945 lines, split into 5 components |
| `pages/queue.tsx` | Reference → decompose | 581 lines, split into 3 components |
| `store/jobs.ts` | Modify | Add 'use client', 1926 lines |
| `store/settings.ts` | Modify | Add 'use client' |
| `store/admin.ts` | Modify | Add 'use client' |
| `store/style-guides.ts` | Modify | Add 'use client' |
| `store/voice-profiles.ts` | Modify | Add 'use client' |
| `store/ui-preferences.ts` | Modify | Add 'use client' |
| `components/job-card/*` | Reference | 20 files — extract reusable parts |
| `components/unified-input/*` | Reference | Source input forms |
| `components/dashboard/*` | Reference | Existing dashboard components |
| `lib/api-client.ts` | Preserve | apiFetch/authFetch unchanged |
| `lib/constants.ts` | Preserve | Stage labels, API_URL |

## Implementation Steps

### 3.1 Add 'use client' to all Zustand stores
- `store/jobs.ts`
- `store/settings.ts`
- `store/admin.ts`
- `store/style-guides.ts`
- `store/voice-profiles.ts`
- `store/ui-preferences.ts`

### 3.2 Create middleware.ts stub
```typescript
// frontend/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Phase 7: full auth check with Supabase
  // For now: pass through
  return NextResponse.next();
}

export const config = {
  matcher: ['/(app)/:path*', '/(admin)/:path*'],
};
```

### 3.3 Build JobCard component
- shadcn/ui Card as base
- StatusBadge: Badge variants (destructive=failed, default=running, secondary=queued, outline=completed)
- Title, topic, source count, created date, analysis mode badge
- SourceTypeTags: small Badge components per source type
- Click navigates to `/jobs/[id]`

### 3.4 Build JobCardGrid component
- CSS grid: 1 col mobile, 2 cols tablet, 3 cols desktop
- Empty state with illustration
- Loading state with Skeleton cards

### 3.5 Build JobCreationWizard (multi-step)
- Step indicator component (Step 1/4, Step 2/4, etc.) using shadcn Progress
- Navigation: Next/Back buttons, step validation before advancing
- State managed locally (wizard state, not global store)

### 3.5a WizardStepTopic — Step 1
- shadcn Input for research topic
- Validation: required, max 2000 chars
- Optional: quick-start templates

### 3.5b WizardStepSources — Step 2
- Dynamic source URL list (add/remove)
- YouTube URL detection + transcript toggle
- Text paste input option
- File upload option

### 3.5c WizardStepMode — Step 3
- shadcn Select for pipeline mode (quick/full/breaking_news/investigation/profile/controversy)
- Niche selector
- Style guide selector (if guides exist)

### 3.5d WizardStepPreview — Step 4
- Preview card with interpreted topic, mode, sources
- Disambiguation flow: if `is_ambiguous`, show interpretation cards with "Select"
- Confirm button triggers useCreateJob mutation
- Loading state during creation

### 3.6 Build TanStack Query hooks
- `use-jobs.ts`: useQuery with refetchInterval for active jobs (replaces manual polling)
- `use-job-detail.ts`: useQuery(jobId) with conditional refetchInterval when status=running
- `use-create-job.ts`: useMutation, invalidates jobs query on success
- `use-preview-job.ts`: useMutation for preview/disambiguation

### 3.7 Build DashboardContent
- Combines: DashboardStats + JobCreationForm + JobPreviewCard + RecentJobsList
- Uses useJobsStore() for state
- Polls for active jobs using existing polling mechanism

### 3.8 Create app/(app)/dashboard/page.tsx
- Server component wrapper
- Renders DashboardContent (client)

### 3.9 Build QueueTabs + QueueContent
- shadcn/ui Tabs: All, Running, Completed, Failed
- Each tab filters jobs from store
- JobListItem: compact row with status, title, date, progress
- Sort by date descending

### 3.10 Create app/(app)/queue/page.tsx
- Server component wrapper
- Renders QueueContent (client)

### 3.11 TanStack Query polling replaces manual polling
- refetchInterval from `lib/constants.ts` POLLING_INTERVALS
- Auto-enabled when any job has status=running
- Pauses when all jobs complete (enabled: hasActiveJobs)
- No manual cleanup needed — React Query handles unmount

### 3.12 Test dashboard and queue
- Job creation flow end-to-end
- Disambiguation flow
- Queue tab filtering
- Polling updates
- Empty states
- Error states

## Todo
- [ ] 3.1 Add 'use client' to all stores
- [ ] 3.2 Create middleware.ts stub
- [ ] 3.3 Build JobCard component
- [ ] 3.4 Build JobCardGrid component
- [ ] 3.5 Build JobCreationForm
- [ ] 3.6 Build JobPreviewCard
- [ ] 3.7 Build DashboardContent
- [ ] 3.8 Create dashboard page.tsx
- [ ] 3.9 Build QueueTabs + QueueContent
- [ ] 3.10 Create queue page.tsx
- [ ] 3.11 Wire up polling
- [ ] 3.12 Integration test

## Success Criteria
- Dashboard renders with job creation form and recent jobs list
- Job creation flow works: topic > preview > disambiguate > create
- Queue page shows tabbed job list with correct filtering
- Polling updates job status in real time
- All shadcn/ui components styled correctly in dark theme
- `npm run build` passes

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Dashboard decomposition loses functionality | Medium | High | Systematic extraction, test each piece |
| Store hydration mismatch | Medium | Medium | All stores are client-only, no SSR state |
| Polling memory leaks | Low | Medium | Cleanup useEffect, same pattern as current |
| Job creation form validation loss | Low | High | Preserve all validation from current dashboard.tsx |

## Security Considerations
- Auth tokens must be included in all API calls (authFetch from api-client.ts)
- Middleware stub allows access now; full protection in Phase 7
- No user input rendered as HTML without sanitization

## Next Steps
Phase 4: Migrate the job detail hero page into the 3-column layout with all panels.
