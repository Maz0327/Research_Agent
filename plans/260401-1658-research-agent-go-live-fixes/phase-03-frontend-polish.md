# Phase 3: Frontend Polish

## Context Links
- [plan.md](plan.md)
- Prior plan: `plans/260323-1710-frontend-ux-fixes/plan.md` (8 open items listed under "Next Steps")
- Code review: `plans/260323-1710-frontend-ux-fixes/reports/code-reviewer-260323-1747-ux-a11y-review.md`
- A11y audit: `plans/reports/scout-260323-1710-frontend-a11y-audit.md`

## Overview
- **Priority:** HIGH / MEDIUM
- **Status:** Pending
- **Effort:** 3-4h
- **Description:** Complete residual UX fixes from 260323 plan: admin table tokens, keyboard nav, focus colors, JobRow extraction, no-op hover

## Key Insights
- 3 admin tables still use hardcoded Tailwind colors: `job-management-table.tsx`, `user-management-table.tsx`, `error-log-table.tsx`
- 30+ components use `focus:border-blue-500` / `focus:ring-blue-500` instead of `focus:border-primary` / `focus:ring-ring`
- DashboardJobCard already has `onKeyDown` + `focus-visible:ring-2` — mostly compliant
- QueueTableRow has `aria-label` but icon buttons inside lack individual labels
- `recent-jobs-list.tsx` "View all" link (line 148) has hover style but navigates correctly — not truly no-op, just missing visual affordance
- `job-management-table.tsx` is likely >200 lines — extracting `JobRow` needed per code standards

## Requirements

### Functional
- All admin tables use semantic design tokens (no hardcoded `zinc-*`, `blue-400`, etc.)
- Interactive elements have keyboard support + ARIA labels
- Focus indicators use design system tokens
- `job-management-table.tsx` under 200 lines after JobRow extraction

### Non-Functional
- `npx tsc --noEmit` passes
- `npm run build` passes
- No visual regressions (colors should look identical)

## Related Code Files

| File | Action | Issue |
|------|--------|-------|
| `frontend/components/admin-v2/job-management-table.tsx` | Modify — tokens + extract JobRow | #6, #18.6 |
| `frontend/components/admin-v2/user-management-table.tsx` | Modify — tokens | #6 |
| `frontend/components/admin-v2/error-log-table.tsx` | Modify — tokens + clarify handlers | #6, #18.5 |
| `frontend/components/admin-v2/job-row.tsx` | Create — extracted from job-management-table | #18.6 |
| `frontend/components/queue/queue-table-row.tsx` | Modify — aria-label on icon buttons | #7, #18.3 |
| `frontend/components/dashboard/recent-jobs-list.tsx` | Modify — fix hover affordance | #13, #18.7 |
| `frontend/components/settings-v2/preferences-section.tsx` | Modify — focus tokens | #14 |
| `frontend/components/auth/login-form.tsx` | Modify — focus tokens | #14 |
| `frontend/components/settings-v2/profile-section.tsx` | Modify — focus tokens | #14 |
| `frontend/components/settings-v2/style-guides-section.tsx` | Modify — focus tokens | #14 |
| `frontend/components/brainstorm/BrainstormPanel.tsx` | Modify — focus tokens | #14 |
| `frontend/components/iterate/RefinePanel.tsx` | Modify — focus tokens | #14 |
| `frontend/components/unified-input/*.tsx` | Modify — focus tokens | #14 |
| `frontend/components/settings/*.tsx` | Modify — focus tokens | #14 |
| `frontend/components/job-card/ShareButton.tsx` | Modify — focus tokens | #14 |
| `frontend/components/job-card/DocumentViewerModal.tsx` | Modify — focus tokens | #14 |
| `frontend/components/dashboard/JobTable.tsx` | Modify — focus tokens | #14 |
| `frontend/components/JobCard.tsx` | Modify — focus tokens | #14 |
| `frontend/components/ui/AnimatedButton.tsx` | Modify — focus tokens | #14 |
| `frontend/components/document-v2/shared/editable-section.tsx` | Modify — focus tokens | #14 |
| `frontend/components/SkipLink.tsx` | Modify — focus tokens | #14 |

## Implementation Steps

### 3.1 — Admin Table Design Token Migration (HIGH)

For each of the 3 admin tables, apply the token mapping from the 260323 plan:

**Color replacement map:**
| Hardcoded | Token |
|-----------|-------|
| `text-zinc-*` / `text-gray-*` text | `text-foreground` or `text-muted-foreground` |
| `bg-zinc-*` / `bg-gray-*` backgrounds | `bg-card` / `bg-secondary` / `bg-muted` |
| `border-zinc-*` / `border-gray-*` | `border-border` |
| `text-blue-400` / `text-blue-500` | `text-primary` |
| `text-red-400` / `text-red-500` | `text-destructive` |
| `text-green-400` / `text-green-500` | `text-green-500` (status — keep semantic) |
| `text-orange-*` / `text-amber-*` | `text-orange-500` / `text-amber-500` (keep semantic) |
| `bg-blue-500/10` hover backgrounds | `bg-primary/10` |

**Process per file:**
1. Read entire file
2. Find all hardcoded color classes
3. Replace with nearest token per map
4. Verify visual output unchanged (same effective colors in dark mode)

### 3.2 — Extract JobRow Component (MEDIUM)

1. Read `job-management-table.tsx`, identify the row rendering logic
2. Extract to `frontend/components/admin-v2/job-row.tsx`
3. Props: job data, action handlers (view, delete, etc.)
4. Import back into table component
5. Verify parent file is under 200 lines

### 3.3 — Keyboard Navigation & ARIA (HIGH)

**queue-table-row.tsx:**
1. Add `aria-label` to Stop and Cancel icon buttons (e.g., `aria-label="Stop job"`, `aria-label="Cancel job"`)
2. Add `focus-visible:ring-2 focus-visible:ring-ring` to icon buttons
3. Optionally add `aria-hidden="true"` to decorative icons inside labeled buttons

**error-log-table.tsx:**
1. Clarify Dismiss vs Retry handlers — if same handler, differentiate or remove one
2. Add `aria-label` to action buttons

**DashboardJobCard:** Already compliant (has onKeyDown + focus-visible). No changes needed.

### 3.4 — Focus Color Token Migration (LOW — bulk find-replace)

Replace across all 20+ component files:
```
focus:border-blue-500  →  focus:border-primary
focus:ring-blue-500    →  focus:ring-ring
focus:ring-1 focus:ring-blue-500  →  focus:ring-1 focus:ring-ring
focus:ring-2 focus:ring-blue-500  →  focus:ring-2 focus:ring-ring
text-blue-500 (in checkboxes)  →  text-primary
bg-blue-600 (in SkipLink)  →  bg-primary
focus:ring-blue-400  →  focus:ring-ring
focus:bg-blue-600  →  focus:bg-primary
```

**Approach:** Use IDE global find-replace or a script. Files affected (from grep):
- `preferences-section.tsx` (3 instances)
- `login-form.tsx` (4 instances)
- `profile-section.tsx` (2 instances)
- `style-guides-section.tsx` (1 instance)
- `BrainstormPanel.tsx` (2 instances)
- `RefinePanel.tsx` (1 instance)
- `ArticleSourceForm.tsx` (2 instances)
- `ScreenshotSourceForm.tsx` (2 instances)
- `AddSourceModal.tsx` (2 instances)
- `UnifiedInputPanel.tsx` (2 instances)
- `ShareButton.tsx` (2 instances)
- `DocumentViewerModal.tsx` (1 instance)
- `JobTable.tsx` (1 instance)
- `JobCard.tsx` (2 instances)
- `AnimatedButton.tsx` (1 instance)
- `editable-section.tsx` (2 instances)
- `SkipLink.tsx` (3 instances)
- `DisplaySection.tsx` (4 instances)
- `NotificationsSection.tsx` (3 instances)
- `PipelineSection.tsx` (3 instances)
- `AccountSection.tsx` (2 instances)

**Do NOT touch files in `frontend/archive/`** — those are dead code.

### 3.5 — Fix "View All" Hover in recent-jobs-list.tsx (LOW)

Line 148: `className="text-xs text-muted-foreground hover:text-primary transition-colors"`

The link works (navigates to queue). The issue is it looks like a label, not a link. Fix:
1. Add `underline-offset-4 hover:underline` to make it clearly clickable
2. Optionally add `cursor-pointer` if not already on a `<Link>` element

### 3.6 — Tailwind Config Token Check (HIGH)

Verify `tailwind.config.ts` has these tokens defined:
- `primary` — should map to blue-500 equivalent
- `ring` — should map to blue-500 or primary
- `destructive` — should map to red-500 equivalent
- `card`, `secondary`, `muted`, `border` — standard shadcn tokens

If `surface-1/2/3` or `accent-red` tokens referenced in queue components are missing, replace with `bg-card`/`bg-secondary`/`bg-muted`/`text-destructive` instead of adding new tokens (YAGNI).

## Todo Checklist

- [ ] 3.1 Migrate `job-management-table.tsx` to design tokens
- [ ] 3.1 Migrate `user-management-table.tsx` to design tokens
- [ ] 3.1 Migrate `error-log-table.tsx` to design tokens
- [ ] 3.2 Extract `job-row.tsx` from `job-management-table.tsx`
- [ ] 3.2 Verify parent file under 200 lines
- [ ] 3.3 Add aria-labels to queue-table-row.tsx icon buttons
- [ ] 3.3 Clarify Dismiss vs Retry in error-log-table.tsx
- [ ] 3.4 Bulk replace `focus:border-blue-500` → `focus:border-primary` (21 files)
- [ ] 3.4 Bulk replace `focus:ring-blue-*` → `focus:ring-ring` (21 files)
- [ ] 3.5 Add underline hover to "View all" in recent-jobs-list.tsx
- [ ] 3.6 Verify tailwind.config.ts has all referenced tokens
- [ ] Run `npx tsc --noEmit` — zero errors
- [ ] Run `npm run build` — passes

## Success Criteria
- Zero hardcoded palette colors in admin-v2 components
- All interactive elements have ARIA labels
- All focus indicators use `primary` / `ring` tokens
- `job-management-table.tsx` < 200 lines
- Build passes with zero TS errors

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token replacement changes visual appearance | MED | Compare before/after screenshots; tokens should resolve to same hex values |
| Missing token in tailwind.config causes invisible focus rings | HIGH | Verify tokens exist before replacing |
| JobRow extraction breaks table layout | LOW | Test in browser after extraction |

## Security Considerations
- No security implications — purely visual/a11y changes
