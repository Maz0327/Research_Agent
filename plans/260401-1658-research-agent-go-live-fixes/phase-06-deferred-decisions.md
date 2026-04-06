# Phase 6: Deferred Decisions

## Context Links
- [plan.md](plan.md)
- CURRENT_PLAN: `plans/CURRENT_PLAN.md` (phases 2-5)
- Voice profiles store: `frontend/store/voice-profiles.ts`
- Script models: `backend/models/script_models.py`

## Overview
- **Priority:** LOW
- **Status:** Pending
- **Effort:** 1-2h (decision-making, minimal code)
- **Description:** Triage CURRENT_PLAN phases 2-5, decide on missing dialog components, voice profile UI wiring

## Key Insights

### CURRENT_PLAN Phases 2-5 Assessment

| Phase | Title | Go-Live Required? | Rationale |
|-------|-------|-------------------|-----------|
| 2 | Validate competitive analysis | **NO** | Analysis doc is internal strategy; doesn't affect product function |
| 3 | Creator Brief (Doc 3) | **NO** | Major new feature, not a blocker. Current 4-doc output works. Implement post-launch. |
| 4 | Close enforcement gaps | **PARTIAL** | Some gaps are code-quality (defer). Source ID enforcement (4.1) is important but existing validation catches most issues. |
| 5 | Iterate consolidation + naming | **NO** | Rename "Booster" → "Deep Dive" is cosmetic. Iterate system works as-is. |

**Recommendation:** Defer ALL of CURRENT_PLAN phases 2-5 to post-launch. The current pipeline produces valid output. Creator Brief (Phase 3) is the next major feature after go-live.

### Missing UI Dialogs

`ScriptOptionsDialog.tsx` and `SocialKitOptionsDialog.tsx` don't exist. The store triggers these endpoints with defaults:
- Script: uses `GenerateScriptRequest` defaults (conversational tone, medium length)
- Social kit: no options, fires directly

**Recommendation:** Defer dialogs. Current defaults work. Add options UI when user feedback requests customization.

### Voice Profile UI Wiring

- `frontend/store/voice-profiles.ts` exists (CRUD operations)
- Script trigger UI doesn't offer voice profile selection
- Voice profile CRUD pages may not be built yet

**Recommendation:** Defer. Voice mimicry is explicitly v2 in CURRENT_PLAN. The migration (Phase 1) and basic CRUD (Phase 4 smoke test) are enough foundation.

## Requirements

### Decisions Needed (from project owner)
1. Confirm CURRENT_PLAN phases 2-5 deferred to post-launch
2. Confirm script/social-kit run with defaults (no options dialogs) at launch
3. Confirm voice profile UI deferred to v2
4. Decide version number: `v0.1.0` (beta) or `v1.0.0` (production)

## Implementation Steps

### 6.1 — Document Deferral Decisions

Add to `DECISIONS.md`:

```markdown
## 2026-04-01: Go-Live Scope

**Decision:** Launch with current feature set. Defer CURRENT_PLAN phases 2-5.

**Deferred to post-launch:**
- Creator Brief (Doc 3) — major feature, separate release
- Competitive analysis validation — internal, no user impact
- Enforcement gap closures (4 of 6) — existing validation sufficient
- Iterate naming consolidation — cosmetic, current naming works
- ScriptOptionsDialog / SocialKitOptionsDialog — defaults sufficient
- Voice profile UI wiring — v2 feature

**Rationale:** Ship working product. Gather user feedback before building Creator Brief and voice mimicry. Current output (Doc 0-2 + optional Producer Packet) delivers core value.
```

### 6.2 — Update CURRENT_PLAN.md Status

Mark phases with launch deferral notes:

```markdown
## Phase 2: Read & Validate sandcastles-analysis.md
**Status:** Deferred (post-launch, non-blocking)

## Phase 3: Creator Brief
**Status:** Deferred (post-launch, next major feature)

## Phase 4: Close Enforcement Gaps
**Status:** Deferred (post-launch, code quality)

## Phase 5: Iterate System Consolidation
**Status:** Deferred (post-launch, cosmetic)
```

### 6.3 — Create Post-Launch Roadmap Issue (optional)

If using GitHub Issues for tracking:
```bash
gh issue create --title "Post-launch: Creator Brief (Doc 3) implementation" \
  --body "Implement CURRENT_PLAN Phase 3. See plans/CURRENT_PLAN.md for full spec." \
  --label "enhancement,post-launch"
```

## Todo Checklist

- [ ] 6.1 Get owner confirmation on deferral decisions
- [ ] 6.1 Add deferral decisions to DECISIONS.md
- [ ] 6.2 Update CURRENT_PLAN.md phase statuses
- [ ] 6.3 (Optional) Create GitHub Issues for deferred items

## Success Criteria
- Clear written decisions on what ships vs what's deferred
- DECISIONS.md and CURRENT_PLAN.md updated
- No ambiguity about go-live scope

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users expect Creator Brief at launch | MED | Clear messaging in release notes: "Coming soon" |
| Script defaults produce poor output | LOW | Monitor first 10 script generations; add options dialog in fast-follow |
| Voice mimicry table unused (wasted migration) | NONE | Table is small, RLS'd, no harm in having it ready |

## Security Considerations
- None — this phase is decision-making and documentation only
