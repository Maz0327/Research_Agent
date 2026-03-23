# Frontend UI/UX Accessibility & Quality Fixes

**Created:** 2026-03-23
**Branch:** feature/kimi-visual-analysis-and-optimizations
**Estimated Effort:** 4-5h total (3 phases, parallelizable)
**Risk:** Low — all changes are visual/a11y, no business logic

## Context

Full UI/UX audit identified ~80-100 issues across 20+ files. Issues grouped into 3 phases by severity and dependency.

## Phases

| Phase | File | Effort | Status |
|-------|------|--------|--------|
| 1 | [phase-01-critical-a11y.md](phase-01-critical-a11y.md) | 2h | Complete |
| 2 | [phase-02-design-tokens.md](phase-02-design-tokens.md) | 1.5h | Partial — gaps in admin-v2 + queue tokens |
| 3 | [phase-03-ux-polish.md](phase-03-ux-polish.md) | 1h | Complete (stubs noted) |

## Phase Summary

### Phase 1: Critical Accessibility (HIGH) — 2h
- Add `prefers-reduced-motion` support via Tailwind `motion-safe:` prefix
- Fix missing focus rings on 5+ interactive elements
- Add `aria-label` to 30+ placeholder-only inputs
- Wrap 2 tables in `overflow-x-auto`

### Phase 2: Design Token Migration (MEDIUM) — 1.5h
- Replace 50+ hardcoded hex colors with Tailwind theme tokens
- Map: `text-[#f5f5f5]` → `text-foreground`, `text-[#71717a]` → `text-muted-foreground`, etc.
- Add missing accent color tokens to `tailwind.config.ts`

### Phase 3: UX Polish (MEDIUM-LOW) — 1h
- Add error handling UI to dashboard/queue/admin (4 components)
- Polish admin empty states with icons + CTAs (4 tables)
- Add loading/disabled states to 3 async buttons
- Add skeleton loaders to admin tables

## Parallelization

Phases 1 + 2 can run in parallel (no file overlap). Phase 3 runs after Phase 2 (uses design tokens).

## Next Steps (from code review — 2026-03-23)

1. **[HIGH]** `tailwind.config.js` — add `surface-1/2/3` and `accent-red` tokens, OR replace in `queue-content.tsx`, `queue-worker-card.tsx`, `queue-table-row.tsx` with `bg-card`/`bg-secondary`/`bg-muted`/`text-destructive`
2. **[HIGH]** Complete Phase 2 in `job-management-table.tsx`, `user-management-table.tsx`, `error-log-table.tsx` — swap palette names (`zinc-700`, `blue-400`, `red-400`, `green-400`, etc.) for semantic tokens
3. **[MEDIUM]** `queue-table-row.tsx` — add `aria-label` + `focus-visible:ring` + `aria-hidden` to Stop/Cancel icon buttons
4. **[MEDIUM]** `DashboardJobCard` + `QueueTableRow` — add `role="button"` + `tabIndex={0}` + `onKeyDown` for keyboard nav, or convert to `<Link>`
5. **[MEDIUM]** `error-log-table.tsx` — clarify Dismiss vs Retry (currently same handler); extract `ErrorCard` to separate file
6. **[MEDIUM]** Extract `JobRow` to `job-row.tsx` to bring `job-management-table.tsx` under 200 lines
7. **[LOW]** Fix no-op hover on "View all" link in `recent-jobs-list.tsx`
8. **[LOW]** Replace `focus:border-blue-500` with `focus:border-primary` in `job-management-table.tsx`

See full report: [reports/code-reviewer-260323-1747-ux-a11y-review.md](reports/code-reviewer-260323-1747-ux-a11y-review.md)

## Success Criteria

- `npx tsc --noEmit` passes (zero errors)
- All inputs have labels or aria-labels
- All animations respect `prefers-reduced-motion`
- Zero hardcoded hex colors in component files
- All tables scroll horizontally on mobile
- All data-fetching components have error + empty states

## Token Color Migration Map

| Hardcoded | Design Token | Usage |
|-----------|-------------|-------|
| `text-[#f5f5f5]` | `text-foreground` | Primary text |
| `text-[#a1a1aa]` | `text-muted-foreground` | Secondary text |
| `text-[#71717a]` | `text-muted-foreground` | Muted text |
| `text-[#52525b]` | `text-muted-foreground/60` | Disabled text |
| `bg-[#12121a]` | `bg-card` | Card backgrounds |
| `bg-[#1a1a25]` | `bg-secondary` | Input backgrounds |
| `bg-[#222230]` | `bg-muted` | Disabled backgrounds |
| `border-[#27272a]` | `border-border` | Borders |
| `border-[#3f3f46]` | `border-border` | Hover borders |
| `text-[#3b82f6]` | `text-primary` | Blue accent |
| `bg-[#3b82f6]` | `bg-primary` | Blue backgrounds |
| `text-[#22c55e]` | `text-green-500` | Success/running |
| `text-[#ef4444]` | `text-destructive` | Error/failed |
| `text-[#f97316]` | `text-orange-500` | Warning |
| `text-[#8b5cf6]` | `text-purple-500` | AI/iterate |
| `text-[#f59e0b]` | `text-amber-500` | Hooks/creator brief |
