# Phase 2: Design Token Migration

**Priority:** MEDIUM
**Effort:** 1.5h
**Status:** Complete

## Context
- [Plan](plan.md) — Token Migration Map table
- [Scout Report](../reports/scout-260323-1710-frontend-a11y-audit.md)

## Overview

Replace 50+ hardcoded hex colors with Tailwind theme tokens for maintainability and light/dark mode consistency.

## Key Insights

- `globals.css` already defines CSS variables for both `:root` (light) and `.dark` (dark)
- shadcn/ui components already use token classes (`text-foreground`, `bg-card`, etc.)
- New components from the overhaul bypassed the token system by using raw hex values
- Fixing this enables light mode to work without further changes

## Requirements

### Functional
- All visual colors come from theme tokens, not hardcoded hex
- Existing visual appearance in dark mode is unchanged
- Light mode toggle works correctly on all components

### Non-Functional
- Zero visual regression in dark mode
- TypeScript compiles clean

## Token Migration Map

### Text Colors
| Find | Replace With |
|------|-------------|
| `text-[#f5f5f5]` | `text-foreground` |
| `text-[#a1a1aa]` | `text-muted-foreground` |
| `text-[#71717a]` | `text-muted-foreground` |
| `text-[#52525b]` | `text-muted-foreground/60` |

### Background Colors
| Find | Replace With |
|------|-------------|
| `bg-[#0a0a0f]` | `bg-background` |
| `bg-[#12121a]` | `bg-card` |
| `bg-[#1a1a25]` | `bg-secondary` |
| `bg-[#222230]` | `bg-muted` |
| `bg-[#2a2a38]` | `bg-accent` |

### Border Colors
| Find | Replace With |
|------|-------------|
| `border-[#27272a]` | `border-border` |
| `border-[#3f3f46]` | `border-border` |

### Accent Colors
| Find | Replace With |
|------|-------------|
| `text-[#3b82f6]`, `bg-[#3b82f6]` | `text-primary`, `bg-primary` |
| `text-[#22c55e]`, `bg-[#22c55e]` | `text-green-500`, `bg-green-500` |
| `text-[#ef4444]`, `bg-[#ef4444]` | `text-destructive`, `bg-destructive` |
| `text-[#f97316]`, `bg-[#f97316]` | `text-orange-500`, `bg-orange-500` |
| `text-[#8b5cf6]`, `bg-[#8b5cf6]` | `text-purple-500`, `bg-purple-500` |
| `text-[#f59e0b]`, `bg-[#f59e0b]` | `text-amber-500`, `bg-amber-500` |

### Opacity Variants
| Find Pattern | Replace Pattern |
|-------------|----------------|
| `bg-[#22c55e]/10` | `bg-green-500/10` |
| `bg-[#3b82f6]/10` | `bg-primary/10` |
| `bg-[#ef4444]/10` | `bg-destructive/10` |
| `bg-[#f97316]/10` | `bg-orange-500/10` |
| `bg-[#8b5cf6]/10` | `bg-purple-500/10` |

## Related Code Files

### Modify (High Instance Count)
- `components/dashboard/DashboardJobCard.tsx` — 12+ instances
- `components/dashboard/recent-jobs-list.tsx` — 10+ instances
- `components/dashboard/dashboard-stats.tsx` — 5+ instances
- `components/dashboard/dashboard-content.tsx` — 3+ instances
- `components/queue/queue-content.tsx` — 15+ instances
- `components/queue/queue-worker-card.tsx` — 5+ instances
- `components/queue/queue-table-row.tsx` — 10+ instances
- `components/settings-v2/settings-content.tsx` — 5+ instances
- `components/settings-v2/settings-general-tab.tsx` — 5+ instances
- `components/settings-v2/settings-notifications-tab.tsx` — 3+ instances
- `components/admin-v2/job-management-table.tsx` — 8+ instances
- `components/admin-v2/user-management-table.tsx` — 5+ instances
- `components/admin-v2/error-log-table.tsx` — 5+ instances
- `components/transcripts/transcripts-content.tsx` — 5+ instances
- `components/shared/shared-job-view.tsx` — 5+ instances
- `components/usage/usage-content.tsx` — 5+ instances

### Verify (may need token additions)
- `tailwind.config.ts` — ensure accent colors are defined
- `app/globals.css` — verify CSS variable mappings

## Implementation Steps

### Task 2.1: Verify Token Availability
Read `tailwind.config.ts` and `globals.css` to confirm all needed tokens exist. Add any missing accent color tokens.

### Task 2.2: Batch Replace — Text Colors
Use find-and-replace across all component files:
- `text-[#f5f5f5]` → `text-foreground`
- `text-[#a1a1aa]` → `text-muted-foreground`
- `text-[#71717a]` → `text-muted-foreground`
- `text-[#52525b]` → `text-muted-foreground/60`

### Task 2.3: Batch Replace — Background Colors
- `bg-[#0a0a0f]` → `bg-background`
- `bg-[#12121a]` → `bg-card`
- `bg-[#1a1a25]` → `bg-secondary`
- `bg-[#222230]` → `bg-muted`
- `bg-[#2a2a38]` → `bg-accent`

### Task 2.4: Batch Replace — Border + Accent Colors
- All border hex → `border-border`
- All accent hex → named Tailwind colors (green-500, destructive, orange-500, purple-500, amber-500)
- All accent/opacity hex → named + opacity (green-500/10, primary/10, etc.)

### Task 2.5: Verify No Remaining Hex Colors
Run grep to confirm zero remaining `[#` patterns in component files.

## Todo List

- [x] Task 2.1: Verify token availability in tailwind config + globals.css
- [x] Task 2.2: Replace text color hex → tokens (4 patterns)
- [x] Task 2.3: Replace background color hex → tokens (5 patterns)
- [x] Task 2.4: Replace border + accent color hex → tokens (10+ patterns)
- [x] Task 2.5: Verify zero remaining hardcoded hex colors

## Success Criteria

- `grep -r '\[#' frontend/components/ --include="*.tsx"` returns zero results
- `npx tsc --noEmit` passes
- Dark mode appearance unchanged (visual regression: none)
- Light mode toggle renders all components correctly

## Risk Assessment

- **Medium risk** — wrong token mapping could change appearance
- **Mitigation:** Verify each token's CSS variable value matches the hex it replaces
- **Rollback:** Git revert if visual regression detected
