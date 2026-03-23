# Code Review Summary

## Scope
- **Files reviewed:** 10 components (dashboard-content, recent-jobs-list, DashboardJobCard, queue-content, queue-worker-card, queue-table-row, job-management-table, user-management-table, error-log-table, transcripts-content)
- **Lines analyzed:** ~1,615 LOC
- **Review focus:** Phase 1 (A11Y), Phase 2 (design tokens), Phase 3 (UX polish) — as described in `plans/260323-1710-frontend-ux-fixes/`
- **Build:** PASS (`npm run build` clean, zero TS errors, `npx tsc --noEmit` clean)
- **Updated plans:** `plans/260323-1710-frontend-ux-fixes/plan.md` (status updated)

---

## Overall Assessment

All three phases are functionally complete and the build passes. The A11Y and UX polish work is solid — motion-safe prefixes, focus rings, aria-labels, and error/empty/skeleton states are consistently applied across the reviewed files. However, **Phase 2 (design token migration) is incomplete**: multiple files in the reviewed scope still use undeclared custom tokens (`surface-1`, `surface-2`, `surface-3`, `accent-red`, `accent-purple`) and hardcoded Tailwind palette colors (`red-400`, `blue-600`, `green-400`, `zinc-700`, etc.) that will render as `undefined` at runtime or are not theme-aware.

---

## Critical Issues

None. Build passes, no runtime-breaking TS errors.

---

## High Priority Findings

### H1: Undeclared custom tokens will silently produce no-op CSS
**Files:** `queue-content.tsx`, `queue-worker-card.tsx`, `queue-table-row.tsx`, `transcripts/transcript-types.ts`

The following tokens are used but **not defined in `tailwind.config.js`**:
- `bg-surface-1`, `bg-surface-2`, `hover:bg-surface-3`, `bg-surface-3` — used in queue-content (lines 107, 118, 153), queue-worker-card (lines 15, 32), queue-table-row (line 66)
- `text-accent-red`, `hover:text-accent-red` — used in queue-table-row (lines 96, 160, 165)
- `text-accent-purple`, `bg-accent-purple/10` — used in `transcript-types.ts` (line 49)

Tailwind config defines `accent.blue`, `accent.green`, `accent.purple` — but the class-name convention is `accent-blue` (flat), not `accent.blue` (nested). Flat names like `bg-accent-blue` only work because Tailwind flattens nested color keys with a `-` separator (`accent.blue.DEFAULT` → `accent-blue`). However `surface-*` and `accent-red` have **no entry** at all. These classes produce empty CSS rules — elements using them get no background/color applied.

**Fix:** Either add these to `tailwind.config.js`:
```js
surface: {
  '1': 'hsl(var(--card))',        // equivalent to bg-card
  '2': 'hsl(var(--secondary))',   // equivalent to bg-secondary
  '3': 'hsl(var(--muted))',       // equivalent to bg-muted
},
```
Or replace them with the equivalent tokens already defined: `bg-card`, `bg-secondary`, `bg-muted`, `text-destructive`.

### H2: Phase 2 token migration incomplete — hardcoded palette colors remain in admin files
**Files:** `job-management-table.tsx`, `user-management-table.tsx`, `error-log-table.tsx`

Status in plan says "Complete" but these files still use raw Tailwind palette names (not theme tokens), which breaks light mode:

| File | Remaining instances |
|------|---------------------|
| `job-management-table.tsx` | `bg-zinc-700/40 text-zinc-300`, `text-zinc-400`, `bg-green-500/10 text-green-400`, `bg-blue-500/10 text-blue-400`, `bg-red-500/10 text-red-400`, `hover:text-red-400`, `focus:border-blue-500` |
| `user-management-table.tsx` | `bg-blue-500/20 text-blue-400`, `bg-green-500/20 text-green-400`, `bg-orange-500/20 text-orange-400`, `bg-red-500/10 text-red-400`, `text-green-400 hover:text-green-300`, `hover:text-red-400`, `bg-blue-600 hover:bg-blue-500` |
| `error-log-table.tsx` | `border-red-500/20`, `bg-red-500/10`, `border-orange-500/20`, `bg-orange-500/10`, `text-red-400`, `text-orange-400`, `text-green-400` |

These are not theme-aware — they will appear the same in light mode when they should adapt.

---

## Medium Priority Improvements

### M1: Icon-only action buttons missing aria-labels
**File:** `queue-table-row.tsx` (lines 159–168)

The Stop (`Square`) and Cancel (`X`) buttons have no `aria-label`. Screen readers will announce them as "button" with no context.

```tsx
// Current (lines 160, 165)
<button className="text-muted-foreground/60 hover:text-accent-red transition-colors">
  <Square className="w-4 h-4" />
</button>

// Fix
<button aria-label="Stop job" className="...">
  <Square className="w-4 h-4" aria-hidden="true" />
</button>
<button aria-label="Remove job from queue" className="...">
  <X className="w-4 h-4" aria-hidden="true" />
</button>
```

Also missing `focus-visible:ring-2 focus-visible:ring-ring` on these same buttons.

### M2: `DashboardJobCard` and `QueueTableRow` — clickable `<div>`/`<tr>` are not keyboard accessible
**Files:** `DashboardJobCard.tsx` (line 42), `queue-table-row.tsx` (line 115)

Both use `onClick` on a `div`/`tr` without `role="button"`, `tabIndex={0}`, or keyboard handler (`onKeyDown`). Tab navigation will skip them entirely.

```tsx
// DashboardJobCard.tsx — current
<div onClick={() => router.push(`/jobs/${job.id}`)} className="... cursor-pointer">

// Fix — add keyboard accessibility
<div
  role="button"
  tabIndex={0}
  onClick={() => router.push(`/jobs/${job.id}`)}
  onKeyDown={(e) => e.key === 'Enter' && router.push(`/jobs/${job.id}`)}
  className="... cursor-pointer focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
>
```

Or convert to `<Link>` which is semantically correct and accessible out-of-the-box.

### M3: `ErrorCard` — "Dismiss" and "Retry Job" are both wired to `handleResolve`
**File:** `error-log-table.tsx` (lines 86–111)

Both buttons call the same handler — "Dismiss" should be a separate dismiss action. Currently clicking "Dismiss" resolves the error (same as "Retry Job"). If the API has distinct endpoints, this is a bug. If intentional, the UI is misleading.

### M4: File size violations — 3 files exceed 200-line limit
Per dev rules (`docs/development-rules.md`):

| File | Lines |
|------|-------|
| `job-management-table.tsx` | 234 |
| `user-management-table.tsx` | 203 |
| `error-log-table.tsx` | 232 |

`job-management-table.tsx` and `error-log-table.tsx` meaningfully exceed the 200-line limit. `JobRow` and `ErrorCard` sub-components could be extracted to separate files.

### M5: `handlePause` / `handleClearCompleted` are placeholder stubs
**File:** `queue-content.tsx` (lines 59–77)

Both handlers contain `// Pause queue action — placeholder for API call` and `await new Promise(resolve => setTimeout(resolve, 500))`. This means the buttons show a loading state but do nothing functional. Acceptable only if tracked as known debt — if this was supposed to be wired up in Phase 3, it's incomplete.

### M6: `View all` link has no visible hover change
**File:** `recent-jobs-list.tsx` (lines 147–151)

```tsx
className="text-xs text-muted-foreground hover:text-muted-foreground transition-colors"
```

`hover:text-muted-foreground` is identical to the default — no visual feedback on hover. Should be `hover:text-foreground` or `hover:underline`.

---

## Low Priority Suggestions

### L1: `admin-dashboard.tsx` — animation missing `motion-safe:` prefix
**File:** `components/admin-v2/admin-dashboard.tsx` (line 127)

```tsx
<div className="rounded-lg border border-gray-700 bg-gray-800 p-6 animate-pulse">
```

Also uses hardcoded `gray-700` / `gray-800` — both a token and motion-safe issue in a file not in the reviewed scope.

### L2: `job-management-table.tsx` search input uses `focus:border-blue-500` (hardcoded color + not a token)
Line 146. Should be `focus:border-primary` to match the rest.

### L3: Duplicate `modeLabel` columns in `queue-table-row.tsx`
Lines 129–135 and 138–140 both render `modeLabel` — once in the job title sub-text, once in a dedicated "Mode" column. The subtitle in the title cell is redundant. Minor UX clutter.

### L4: Inline `confirm()` in `job-management-table.tsx` (line 33)
`confirm('Delete this job?')` is a browser-native dialog — breaks in some embedded environments, not styleable. Low priority but worth noting for future polish.

---

## Positive Observations

- `motion-safe:animate-pulse` and `motion-safe:animate-spin` consistently applied across all pulse/spinner animations in the reviewed files. Phase 1 goal met.
- `focus-visible:ring-2 focus-visible:ring-ring` correctly applied to all form inputs and select elements across all reviewed files.
- `aria-label` correctly added to all search inputs, sort selects, and the textarea in transcripts.
- Error UI pattern (AlertCircle + message + retry button) is consistent across all 4 target components.
- Empty state pattern (icon + title + subtitle) is consistent across all 4 target tables.
- Skeleton loaders use `motion-safe:animate-pulse` correctly.
- `overflow-x-auto` wrappers present on all tables.
- Build clean, zero TypeScript errors, zero `[#` hardcoded hex remaining in reviewed files.

---

## Recommended Actions

1. **[HIGH]** Add `surface-1/2/3` and `accent-red` to `tailwind.config.js` or replace with existing tokens (`bg-card`, `bg-secondary`, `bg-muted`, `text-destructive`) — affects queue components that are currently broken in these colors.
2. **[HIGH]** Complete Phase 2 token migration for `job-management-table.tsx`, `user-management-table.tsx`, `error-log-table.tsx` — replace palette names with semantic tokens.
3. **[MEDIUM]** Add `aria-label`, `focus-visible:ring`, and keyboard handlers to icon-only action buttons in `queue-table-row.tsx` (Stop/Cancel buttons).
4. **[MEDIUM]** Make `DashboardJobCard` and `QueueTableRow` keyboard-accessible (tabIndex + onKeyDown or convert to Link/button).
5. **[MEDIUM]** Clarify or separate "Dismiss" vs "Retry Job" in `error-log-table.tsx` — currently both call same handler.
6. **[MEDIUM]** Extract `JobRow` → `job-row.tsx` and `ErrorCard` → `error-card.tsx` to get `job-management-table.tsx` and `error-log-table.tsx` under 200 lines.
7. **[LOW]** Fix `hover:text-muted-foreground` no-op in `recent-jobs-list.tsx` "View all" link.
8. **[LOW]** Replace `focus:border-blue-500` with `focus:border-primary` in `job-management-table.tsx`.

---

## Metrics

- **TypeScript:** 0 errors
- **Build:** PASS
- **Hardcoded `[#` hex:** 0 (in reviewed files)
- **Undeclared token usage:** 3 files (surface-*, accent-red, accent-purple)
- **Files over 200 lines:** 3 (`job-management-table.tsx` 234, `error-log-table.tsx` 232, `user-management-table.tsx` 203)
- **Linting issues:** 1 warning (`<img>` in MarkdownRenderer — pre-existing, unrelated)
- **motion-safe coverage:** Complete on all reviewed files
- **aria-label coverage:** Complete on inputs; gaps on icon-only buttons

---

## Unresolved Questions

1. Are `handlePause` and `handleClearCompleted` in `queue-content.tsx` intentionally stubbed (known backlog) or were they supposed to be wired in Phase 3?
2. Is the "Dismiss" button in `error-log-table.tsx` intentionally mapped to the same API call as "Retry Job", or is this a missing endpoint?
3. Should `surface-1/2/3` tokens be added to Tailwind config to preserve the visual distinction from `bg-card`/`bg-secondary`/`bg-muted`, or are they semantically identical and should just be replaced?
