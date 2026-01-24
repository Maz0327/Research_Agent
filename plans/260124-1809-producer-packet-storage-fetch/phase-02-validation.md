# Phase 2: Validation

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-add-storage-fetch.md)

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-24 |
| Priority | P1 |
| Status | Pending |
| Effort | 10m |

## Validation Steps

### Step 1: Run existing tests

```bash
pytest backend/tests/test_producer_stage.py -v
pytest backend/tests/test_worker_semantic_tasks.py -v
```

### Step 2: Test with affected job

Trigger producer packet on job `0085a89e-7987-4ffc-93d7-2a52ae37db5a`:
- Via API: `POST /api/v1/jobs/{job_id}/producer`
- Check response for populated story_core

### Step 3: Verify output cardinality

Expected minimums per spec:
- narrative_angles: 2+
- opening_hooks: 2+
- structure_options: 2+
- title_options: 2+
- key_moments: 3+

## Todo

- [ ] Run unit tests
- [ ] Trigger producer on test job
- [ ] Verify Story Core populated
- [ ] Check cardinality minimums met
- [ ] Verify no warnings about missing content

## Success Criteria

1. All existing tests pass
2. Story Core has populated fields (not None)
3. All cardinality minimums met
4. No "cannot assess without context" in risk assessment

## Unresolved Questions

None.
