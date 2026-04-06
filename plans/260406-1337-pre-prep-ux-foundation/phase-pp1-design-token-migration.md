# Phase PP-1: Design Token Migration

## Overview
- **Priority:** P0 — blocks PP-4, PP-5, PP-6
- **Status:** complete
- **Effort:** 3-5 days
- **Description:** Replace 998 hardcoded color references with semantic CSS variable tokens. Ensure dark mode contrast meets WCAG AA.

## Key Insights
- 998 instances of `text-zinc-*`, `bg-zinc-*`, `text-gray-*`, `bg-gray-*` bypass the CSS variable system
- The semantic token system EXISTS in `app/globals.css` (--background, --foreground, --card, --muted, --muted-foreground, etc.) but components don't use it
- Most violations are in `components/document-v2/` (renderers), `components/auth/`, `components/dashboard/StartInput.tsx`
- `text-zinc-500` on dark bg fails WCAG AA (3.8:1 ratio, needs 4.5:1)

## Requirements

### Functional
- All color references use Tailwind semantic classes: `text-foreground`, `text-muted-foreground`, `bg-card`, `bg-secondary`, `bg-muted`, `border-border`
- No raw zinc/gray/slate Tailwind classes in component files
- Dark mode contrast meets WCAG AA (4.5:1 for text, 3:1 for large text)

### Non-Functional
- Visual appearance should be nearly identical after migration (same dark theme, just using tokens)
- No functional behavior changes

## Architecture

### Token Mapping (from audit)

| Hardcoded | Semantic Token | Usage |
|-----------|---------------|-------|
| `text-zinc-100`, `text-white` | `text-foreground` | Primary text |
| `text-zinc-300`, `text-zinc-400` | `text-muted-foreground` | Secondary text, labels |
| `text-zinc-500`, `text-zinc-600` | `text-muted-foreground/70` or new `text-subtle` | Captions, meta text (MUST check contrast) |
| `bg-zinc-900`, `bg-zinc-950` | `bg-background` | Page backgrounds |
| `bg-zinc-800`, `bg-zinc-850` | `bg-card` | Card surfaces |
| `bg-zinc-800/30`, `bg-zinc-700/50` | `bg-secondary` or `bg-muted` | Subtle backgrounds |
| `border-zinc-700`, `border-zinc-600` | `border-border` | Borders |
| `text-blue-400`, `text-blue-500` | `text-primary` | Links, primary accent |
| `text-green-400` | `text-accent-green` | Success states |
| `text-red-400` | `text-destructive` | Error states |
| `text-amber-400`, `text-yellow-400` | `text-accent-amber` | Warnings |

### New Tokens to Add (if missing in globals.css)

```css
--subtle: /* slightly dimmer than muted-foreground, still WCAG AA */
--accent-green: /* success */
--accent-amber: /* warning */
--accent-orange: /* CTA — #F97316 */
```

## Related Code Files

### Highest Violation Count (tackle first)
| Directory/File | Est. Violations |
|---|---|
| `components/document-v2/**` | ~500 |
| `components/auth/login-form.tsx` | ~30 |
| `components/dashboard/StartInput.tsx` | ~40 |
| `components/dashboard/**` | ~100 |
| `components/job-detail-v2/**` | ~150 |
| `components/layout/**` | ~80 |
| `app/globals.css` | Token definitions (modify) |

## Implementation Steps

### Task PP-1.1: Audit and extend token palette
1. Read `app/globals.css` — catalog all existing CSS variables
2. Identify gaps: do we have tokens for all the mappings above?
3. Add missing tokens (--subtle, --accent-green, --accent-amber, --accent-orange)
4. Verify contrast ratios: `text-muted-foreground` on `bg-background` must be >= 4.5:1

### Task PP-1.2: Migrate document-v2 renderers (~500 violations)
1. For each file in `components/document-v2/`:
   - Replace `text-zinc-100/200/300` → `text-foreground`
   - Replace `text-zinc-400/500` → `text-muted-foreground`
   - Replace `bg-zinc-800/900` → `bg-card` or `bg-background`
   - Replace `border-zinc-*` → `border-border`
   - Replace status colors (`text-green-*`, `text-red-*`, `text-amber-*`) → accent tokens
2. Visual diff: check each renderer looks the same

### Task PP-1.3: Migrate dashboard + auth components (~170 violations)
1. `components/auth/login-form.tsx`
2. `components/dashboard/StartInput.tsx`
3. `components/dashboard/dashboard-stats.tsx`
4. `components/dashboard/DashboardJobCard.tsx`
5. `components/dashboard/recent-jobs-list.tsx`
6. Same mapping as PP-1.2

### Task PP-1.4: Migrate job-detail + layout components (~230 violations)
1. `components/job-detail-v2/**`
2. `components/layout/**`
3. Same mapping

### Task PP-1.5: Replace emoji icons with Lucide
1. Grep for emoji usage in components: `grep -rn '[🔍📄⚠️✅❌🎬📝]' components/`
2. Replace each with appropriate Lucide icon component
3. Ensure consistent `w-4 h-4` or `w-5 h-5` sizing

### Task PP-1.6: Verify and test
1. Run `npm run build` — no errors
2. Run `npm run lint` — no new warnings
3. Visual check: dark mode looks identical
4. Contrast check: no text below 4.5:1 ratio

## Todo Checklist
- [x] PP-1.1 Audit + extend token palette in globals.css (tokens already present: text-accent-green, text-accent-amber, text-accent-orange)
- [x] PP-1.2 Migrate document-v2 renderers (~500 violations → 0)
- [x] PP-1.3 Migrate dashboard + auth components (~170 violations → 0)
- [x] PP-1.4 Migrate job-detail + layout components (~230 violations → 0)
- [x] PP-1.5 Replace emoji icons with Lucide (source type icons, task type icons, arc labels, chart icon)
- [x] PP-1.6 Build passes (`✓ Compiled successfully`, TypeScript clean)

## Success Criteria
- `grep -rn "text-zinc\|bg-zinc\|text-gray\|bg-gray" components/` returns 0 results
- All text meets WCAG AA contrast (4.5:1)
- `npm run build` passes
- Visual appearance unchanged

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Token mapping changes appearance | MEDIUM | Keep hex values identical; just switch from hardcoded to variable |
| Missing token for edge case | LOW | Add new tokens as discovered |
| Regex find-replace breaks JSX | LOW | Manual review per file, not blind sed |
