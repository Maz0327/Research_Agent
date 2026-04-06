# Phase PP-5: Progress UX Polish

## Overview
- **Priority:** P1
- **Status:** pending
- **Effort:** 1-2 days
- **Depends on:** PP-1 (tokens)
- **Description:** Surface existing stage descriptions and ETA during pipeline. Add skeleton states for dashboard stats. Add wizard step transitions.

## Key Insights
- `STAGE_LABELS` in `lib/constants.ts` already has descriptions for every stage — they're just never rendered
- `PipelineStatusBar` has an `eta` prop — it's never passed
- Dashboard stats flicker from 0 to real values (no skeleton)
- Wizard steps swap instantly (no animation, Framer Motion is installed but unused in wizard)

## Related Code Files

| File | Change |
|------|--------|
| `components/layout/pipeline-status-bar.tsx` | Show description below label, wire ETA |
| `components/dashboard/DashboardJobCard.tsx` | Show stage description inline |
| `lib/constants.ts` | Already has descriptions — just verify they're good |
| `components/dashboard/dashboard-stats.tsx` | Add skeleton loading state |
| `components/dashboard/job-creation-wizard.tsx` | Add Framer Motion step transitions |

## Implementation Steps

### Task PP-5.1: Show stage descriptions in pipeline status
1. In `pipeline-status-bar.tsx`: render the `description` field from STAGE_LABELS below the stage label
2. Style: `text-caption text-muted-foreground` (using new tokens + type scale)
3. Add rough ETA per pipeline mode: Quick ~1min, Full ~3min, Investigation ~8min
4. Pass ETA to `PipelineStatusBar` from job detail page

### Task PP-5.2: Show stage description on dashboard job cards
1. In `DashboardJobCard.tsx`: when job is running, show stage description text below progress bar
2. Keep it concise — one line

### Task PP-5.3: Add skeleton for dashboard stats
1. In `dashboard-stats.tsx`: while loading, show `Skeleton` components (from shadcn) instead of "0" values
2. 4 skeleton cards matching the stat card layout

### Task PP-5.4: Add wizard step transitions
1. In `job-creation-wizard.tsx`: wrap step content in `<AnimatePresence>` + `<motion.div>`
2. Slide/fade transition: `initial={{ opacity: 0, x: 20 }}` → `animate={{ opacity: 1, x: 0 }}` → `exit={{ opacity: 0, x: -20 }}`
3. Duration: 200ms

### Task PP-5.5: Verify
1. Pipeline status shows description + ETA
2. Dashboard cards show stage description while running
3. Stats show skeleton while loading, then populate
4. Wizard steps animate between steps
5. `npm run build` passes

## Todo Checklist
- [ ] PP-5.1 Show stage descriptions + ETA in pipeline status bar
- [ ] PP-5.2 Show stage description on dashboard job cards
- [ ] PP-5.3 Add skeleton loading for dashboard stats
- [ ] PP-5.4 Add Framer Motion wizard step transitions
- [ ] PP-5.5 Verify all changes + build

## Success Criteria
- Stage descriptions visible during pipeline run
- ETA shown (even rough estimate)
- No stat flicker (skeleton → real values)
- Wizard steps animate smoothly
- Build passes
