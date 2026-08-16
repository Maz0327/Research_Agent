---
phase: E-6
title: "Workers + Lazy Doc 3"
status: pending
effort: 30min
risk: low
---

# E-6: Bump Workers + Lazy Doc 3

**What:** Increase parallel extraction workers from 3 to 5. Make Creator Brief (Doc 3) on-demand only instead of always-generated.
**Why:** More workers = fewer rounds for many sources (10 sources: 4 rounds → 2). Doc 3 adds ~10s per job and most users don't need it until they're producing.

## Changes

### 1. `.env.example` — update default
```
SEMANTIC_EXTRACTION_MAX_WORKERS=5
```

### 2. `backend/worker.py` — make Doc 3 on-demand
Comment out or gate the Creator Brief stage:

```python
# Current (line ~474-475):
# Stage F: Creator Brief assembly (Doc 3) — non-fatal
run_stage_with_recovery(run_creator_brief_stage, ctx, "creator_brief")

# New:
# Stage F: Creator Brief assembly (Doc 3) — ON-DEMAND only
# Triggered via POST /jobs/{id}/creator-brief endpoint
# run_stage_with_recovery(run_creator_brief_stage, ctx, "creator_brief")
```

### 3. Ensure Creator Brief can be triggered later
Verify that `run_creator_brief_stage` can run independently when called from an API endpoint (it should already work since it reads from ctx/DB).

## Tests
- Existing tests should pass (Doc 3 tests may need `skipIf` or mock)
- Verify worker count change with env var

## Success Criteria
- Workers configurable, default 5
- Doc 3 not generated on every job
- Doc 3 still available on-demand
