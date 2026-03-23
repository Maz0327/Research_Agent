# Phase 1: Critical Accessibility Fixes

**Priority:** HIGH
**Effort:** 2h
**Status:** Complete

## Context
- [Scout Report](../reports/scout-260323-1710-frontend-a11y-audit.md)
- [Plan](plan.md)

## Overview

Fix WCAG violations: reduced-motion, focus visibility, input labels, table overflow.

## Key Insights

- `globals.css` already has `@media (prefers-reduced-motion: reduce)` but components bypass it with inline Tailwind animation classes
- Tailwind's `motion-safe:` and `motion-reduce:` prefixes are the cleanest fix
- Most shadcn/ui components already have proper focus rings via `focus-visible:ring`

## Requirements

### Functional
- All animations pause when user prefers reduced motion
- All interactive elements have visible focus indicators
- All inputs have accessible labels
- All tables scroll horizontally on mobile

### Non-Functional
- Zero new dependencies
- TypeScript compiles clean

## Related Code Files

### Modify
- `components/dashboard/DashboardJobCard.tsx` — pulse animation + hardcoded colors
- `components/dashboard/recent-jobs-list.tsx` — search input label, focus ring
- `components/queue/queue-content.tsx` — table overflow, button focus rings
- `components/queue/queue-worker-card.tsx` — pulse animation
- `components/queue/queue-table-row.tsx` — pulse animation
- `components/transcripts/transcripts-content.tsx` — search/URL input labels, focus ring
- `components/admin-v2/error-log-table.tsx` — button focus rings
- `components/admin-v2/job-management-table.tsx` — search input label, focus ring
- `components/admin-v2/user-management-table.tsx` — table overflow wrapper
- `components/settings/StyleGuideSection.tsx` — focus ring upgrade (border → ring)
- `components/settings-v2/settings-general-tab.tsx` — input labels
- `app/globals.css` — ensure reduced-motion utility classes work

## Implementation Steps

### Task 1.1: Reduced Motion Support
For every component using `animate-pulse`, `animate-spin`, `animate-bounce`:
- Replace `animate-pulse` → `motion-safe:animate-pulse`
- Replace `animate-spin` → `motion-safe:animate-spin`
- Replace `animate-bounce` → `motion-safe:animate-bounce`

**Files:** DashboardJobCard.tsx, queue-worker-card.tsx, queue-table-row.tsx, and any skeleton loaders.

### Task 1.2: Focus Ring Fixes
For every element with `focus:outline-none` but no `focus:ring`:
- Add `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`
- Pattern: `focus:outline-none focus-visible:ring-2 focus-visible:ring-ring`

**Files:**
- `admin-v2/error-log-table.tsx` (line ~143)
- `admin-v2/job-management-table.tsx` (lines ~118, ~123)
- `dashboard/recent-jobs-list.tsx` (lines ~86, ~92)
- `queue/queue-content.tsx` (lines ~65, ~68)
- `settings/StyleGuideSection.tsx` (line ~136)
- `transcripts/transcripts-content.tsx` (line ~86)

### Task 1.3: Input Label Accessibility
For every input with only `placeholder=`:
- Add `aria-label="description"` attribute
- OR add visible `<label>` element

**Priority inputs:**
- Dashboard search: `aria-label="Search jobs"`
- Admin search: `aria-label="Search jobs"`
- Admin filter: `aria-label="Filter by status"`
- Transcripts search: `aria-label="Search transcripts"`
- Transcripts URL: `aria-label="YouTube video URLs"`

### Task 1.4: Table Overflow Wrappers
Wrap bare `<table>` elements in `<div className="overflow-x-auto">`:

**Files:**
- `queue/queue-content.tsx` (line ~98)
- `admin-v2/user-management-table.tsx` (line ~107)

## Todo List

- [x] Task 1.1: Add `motion-safe:` prefix to all animation classes
- [x] Task 1.2: Add `focus-visible:ring` to 6+ elements missing focus rings
- [x] Task 1.3: Add `aria-label` to 5+ placeholder-only inputs
- [x] Task 1.4: Wrap 2 tables in `overflow-x-auto` div

## Success Criteria

- `npx tsc --noEmit` passes
- `prefers-reduced-motion: reduce` stops all animations
- Tab key shows visible focus ring on every interactive element
- Screen reader announces input purposes
- Tables scroll horizontally at 375px width

## Risk Assessment

- **Low risk** — all changes are additive CSS classes, no logic changes
- **Regression risk:** None — focus rings and aria-labels can't break functionality
