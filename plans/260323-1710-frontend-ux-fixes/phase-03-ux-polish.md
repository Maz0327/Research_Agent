# Phase 3: UX Polish

**Priority:** MEDIUM-LOW
**Effort:** 1h
**Status:** Complete
**Depends on:** Phase 2 (uses design tokens)

## Context
- [Plan](plan.md)
- [Scout Report](../reports/scout-260323-1710-frontend-a11y-audit.md)

## Overview

Add error handling UI, polished empty states, async button states, and skeleton loaders to components missing them.

## Key Insights

- `job-detail-v2/job-detail-content.tsx` has the best error/loading pattern to copy
- Dashboard and queue already have skeletons — admin pages don't
- Empty states should have icon + message + optional CTA (pattern from recent-jobs-list.tsx)

## Requirements

### Functional
- All data-fetching components show error state on failure
- All lists show polished empty state when no data
- All async action buttons show loading + disabled state
- All admin tables show skeleton loaders while fetching

### Non-Functional
- Consistent patterns across all components
- Use design tokens (from Phase 2)
- Files stay under 200 lines

## Related Code Files

### Modify
- `components/dashboard/dashboard-content.tsx` — add error state
- `components/dashboard/recent-jobs-list.tsx` — add error state
- `components/queue/queue-content.tsx` — add error state, polish empty state
- `components/admin-v2/job-management-table.tsx` — error, empty, skeleton
- `components/admin-v2/user-management-table.tsx` — error, empty, skeleton
- `components/admin-v2/error-log-table.tsx` — empty state polish

### Reference (copy patterns from)
- `components/job-detail-v2/job-detail-content.tsx` — error + skeleton pattern

## Implementation Steps

### Task 3.1: Error Handling UI (4 components)

Add error state check before rendering data. Pattern:

```tsx
if (error) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <AlertCircle className="h-8 w-8 text-destructive mb-3" />
      <p className="text-sm font-medium text-foreground">Failed to load data</p>
      <p className="text-xs text-muted-foreground mt-1">{error.message}</p>
      <button onClick={refetch} className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm">
        Try Again
      </button>
    </div>
  );
}
```

**Files:** dashboard-content.tsx, recent-jobs-list.tsx, queue-content.tsx, admin tables

### Task 3.2: Polish Empty States (4 tables)

Replace plain "No data" text with icon + message + CTA. Pattern:

```tsx
<div className="flex flex-col items-center justify-center py-12 text-center">
  <FileText className="h-8 w-8 text-muted-foreground/40 mb-3" />
  <p className="text-sm text-muted-foreground">No jobs found</p>
  <p className="text-xs text-muted-foreground/60 mt-1">Jobs will appear here when created</p>
</div>
```

**Files:** job-management-table.tsx, user-management-table.tsx, error-log-table.tsx, queue-content.tsx

### Task 3.3: Async Button Loading States (3 buttons)

Add `disabled` + spinner for buttons that trigger async actions:

```tsx
<button
  disabled={isLoading}
  className="... disabled:opacity-50 disabled:cursor-not-allowed"
>
  {isLoading ? (
    <><Loader2 className="h-4 w-4 motion-safe:animate-spin mr-1.5" /> Processing...</>
  ) : (
    'Action'
  )}
</button>
```

**Files:**
- queue-content.tsx — "Pause Queue" + "Clear Completed" buttons
- dashboard-content.tsx — "New Research" button (if it triggers navigation, just disable during route change)

### Task 3.4: Admin Table Skeleton Loaders (3 tables)

Add skeleton grid matching table layout while data loads. Pattern:

```tsx
if (isLoading) {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-10 rounded-lg bg-muted motion-safe:animate-pulse" />
      ))}
    </div>
  );
}
```

**Files:** job-management-table.tsx, user-management-table.tsx, error-log-table.tsx

## Todo List

- [x] Task 3.1: Add error handling UI to 4 components
- [x] Task 3.2: Polish empty states in 4 admin tables
- [x] Task 3.3: Add loading/disabled states to 3 async buttons
- [x] Task 3.4: Add skeleton loaders to 3 admin tables

## Success Criteria

- API failure → user sees error message + retry button
- Empty data → user sees icon + helpful message
- Async actions → button shows spinner + disabled state
- `npx tsc --noEmit` passes

## Risk Assessment

- **Low risk** — additive UI changes, no logic modifications
- **Regression risk:** Minimal — error/empty states only show on edge cases
