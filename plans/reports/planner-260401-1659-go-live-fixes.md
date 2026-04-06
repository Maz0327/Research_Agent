# Planner Report: Research Agent Go-Live Fixes

**Date:** 2026-04-01
**Plan:** `plans/260401-1658-research-agent-go-live-fixes/`

## Summary

Created 6-phase implementation plan addressing all 18 blockers/issues for Research Agent go-live. Total estimated effort: 14-18h.

## Plan Structure

| Phase | Focus | Effort | Priority |
|-------|-------|--------|----------|
| 1 | Infrastructure & DevOps | 3h | CRITICAL |
| 2 | Type Safety & Code Quality | 2h | HIGH |
| 3 | Frontend Polish | 3-4h | HIGH/MED |
| 4 | Live Testing & Validation | 2-3h | CRITICAL |
| 5 | PR Strategy & Release | 2-3h | HIGH |
| 6 | Deferred Decisions | 1-2h | LOW |

## Key Decisions Made in Plan

1. **Do NOT split PR #19** — 294 tightly coupled files across backend+frontend. Splitting creates worse merge risk than reviewing as-is.
2. **Defer CURRENT_PLAN phases 2-5** — Creator Brief, enforcement gaps, iterate renaming are post-launch. Current pipeline produces valid output.
3. **Defer missing dialogs** — ScriptOptionsDialog/SocialKitOptionsDialog use defaults. Add when users request customization.
4. **os.getenv issue is smaller than reported** — only 1 non-script file (`llm_judge.py:376`). Scripts using os.getenv is acceptable.
5. **audit-H8 appears resolved** — `share_routes.py` uses atomic RPC via migration 026. Just needs TODO comment cleanup.
6. **Focus color migration is bulk work** — 30+ files with `focus:border-blue-500`. Straightforward find-replace but tedious.

## Dependency Chain

```
Phase 1 + 2 + 3 (parallel) → Phase 4 (needs migration + OpenAI) → Phase 5 (merge + release)
Phase 6 (independent — owner decisions)
```

## Files Created

- `plans/260401-1658-research-agent-go-live-fixes/plan.md`
- `plans/260401-1658-research-agent-go-live-fixes/phase-01-infrastructure-devops.md`
- `plans/260401-1658-research-agent-go-live-fixes/phase-02-type-safety-code-quality.md`
- `plans/260401-1658-research-agent-go-live-fixes/phase-03-frontend-polish.md`
- `plans/260401-1658-research-agent-go-live-fixes/phase-04-live-testing-validation.md`
- `plans/260401-1658-research-agent-go-live-fixes/phase-05-pr-strategy-release.md`
- `plans/260401-1658-research-agent-go-live-fixes/phase-06-deferred-decisions.md`
