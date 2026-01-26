# Investigation: ETA & Loading State Accuracy

**Date:** 2026-01-26
**Branch:** `claude/fix-metadata-supadata-ABW4P`

---

## Current State Analysis

### 1. Progress Tracking Infrastructure

| Component | Location | Purpose |
|-----------|----------|---------|
| `useETA` hook | `frontend/hooks/useETA.ts` | Calculates ETA from stage + elapsed time |
| `STAGE_LABELS` | `frontend/lib/constants.ts:96` | Human-readable stage descriptions |
| `STAGE_DURATIONS` | `frontend/hooks/useETA.ts:70-195` | Static time estimates per stage |
| `update_job()` | `backend/state/__init__.py:74` | Updates progress_percent, stage, pass_detail |

### 2. Backend Progress Updates

**Main Pipeline (mixed_input)** - `worker.py:339-358`
```python
update_job(job_id, stage="semantic_extraction", progress_percent=20)
update_job(job_id, stage="semantic_validation", progress_percent=35)
update_job(job_id, stage="gap_analysis", progress_percent=50)
update_job(job_id, stage="semantic_synthesis", progress_percent=65)
update_job(job_id, stage="document_assembly", progress_percent=80)
update_job(job_id, stage="completion", progress_percent=95)
```

**Issues:**
- Progress jumps are fixed (20→35→50→65→80→95)
- No per-source granularity within stages
- No `pass_detail` explaining current action

**Iteration Modes** - `backend/pipeline/iteration/modes/*.py`
```python
# Better granularity example (more_sources.py:135)
pass_detail=f"Analyzing: {title[:40]}...",
```

**Video Pipeline** - `worker.py:640-666`
```python
# Best example - uses progress_callback with pass_detail
pass_detail=f"Pass {pass_num}/{total_passes}: {detail}"
```

### 3. Frontend ETA Calculation

**Current Method** (`useETA.ts:288-343`):
1. Look up stage in predefined order
2. Use static duration estimates per stage
3. Subtract elapsed time in current stage
4. Sum remaining stages

**Problems:**
- Static estimates don't account for source count
- No dynamic adjustment based on actual performance
- Semantic extraction takes ~90s estimate regardless of source count

---

## Gap Analysis

| Gap | Impact | Location |
|-----|--------|----------|
| No per-source progress in extraction | ETA inaccurate for multi-source jobs | `semantic_extraction.py:836` |
| Fixed progress jumps | Progress bar jumps, not smooth | `worker.py:339-358` |
| Static stage durations | ETA wrong for varying source counts | `useETA.ts:186-194` |
| Missing pass_detail in main pipeline | User sees generic "Extracting..." | `worker.py:339-358` |
| No historical data usage | Can't learn actual durations | N/A (not implemented) |

---

## Recommendations

### Priority 1: Add Per-Source Progress (High Impact)

**Location:** `backend/pipeline/stages/semantic_extraction.py`

```python
# Current - no progress updates within stage
def stage_semantic_extraction(ctx: PipelineContext) -> None:
    for source in sources:
        extract_source(source)  # No progress update

# Proposed - add progress callback
def stage_semantic_extraction(ctx: PipelineContext, progress_callback=None) -> None:
    total = len(sources)
    for i, source in enumerate(sources):
        if progress_callback:
            progress_callback(
                percent=int(20 + (i / total) * 15),  # 20-35% range
                detail=f"Extracting: {source.title[:40]}... ({i+1}/{total})"
            )
        extract_source(source)
```

**Worker Update:**
```python
# worker.py - pass callback to stage
def source_progress(percent, detail):
    update_job(job_id, progress_percent=percent, pass_detail=detail)

run_stage_with_recovery(
    lambda ctx: stage_semantic_extraction(ctx, progress_callback=source_progress),
    ctx, "semantic_extraction"
)
```

### Priority 2: Dynamic Duration Estimates (Medium Impact)

**Location:** `frontend/hooks/useETA.ts`

```typescript
// Current - static estimate
semantic_extraction: 90,  // Always 90s regardless of source count

// Proposed - scale by source count
function getSemanticDurations(sourceCount: number): Record<string, number> {
  return {
    source_identity: 10 + sourceCount * 2,        // ~2s per source
    semantic_extraction: 30 + sourceCount * 20,   // ~20s per source
    semantic_validation: 15 + sourceCount * 5,    // ~5s per source
    gap_analysis: 30,                             // Fixed
    semantic_synthesis: 30 + sourceCount * 10,    // ~10s per source
    document_assembly: 30 + sourceCount * 5,      // ~5s per source
    completion: 15,                               // Fixed
  };
}
```

**Requires:** Backend sends source count in job config or early stage.

### Priority 3: Better Stage Descriptions (Low Effort)

**Location:** `frontend/lib/constants.ts`

```typescript
// Current
semantic_extraction: {
  label: 'Extracting Insights',
  description: 'Pulling key points and claims from sources'
},

// Proposed - more specific with action verbs
semantic_extraction: {
  label: 'Analyzing Sources',
  description: 'Reading each source and extracting key points, claims, and quotes'
},
```

### Priority 4: Use pass_detail in Main Pipeline (Medium Effort)

**Location:** `backend/worker.py`

Add `pass_detail` to every `update_job()` call:

```python
# Before
update_job(job_id, stage="semantic_extraction", progress_percent=20)

# After
update_job(
    job_id,
    stage="semantic_extraction",
    progress_percent=20,
    pass_detail="Starting semantic extraction..."
)
```

### Priority 5: Historical Duration Tracking (Future)

Store actual stage durations per job, use for ML-based ETA:

```python
# On stage completion
stage_end = datetime.now()
stage_duration = (stage_end - stage_start).total_seconds()
store_stage_metric(job_id, stage, source_count, stage_duration)

# For ETA calculation
avg_duration = get_avg_duration(stage, source_count_bucket)
```

---

## Implementation Plan

| Phase | Task | Effort | Impact |
|-------|------|--------|--------|
| 1 | Add pass_detail to main pipeline stages | 1h | Medium |
| 2 | Add per-source progress to extraction stage | 2h | High |
| 3 | Update frontend stage descriptions | 30m | Low |
| 4 | Dynamic duration scaling by source count | 2h | Medium |
| 5 | Historical duration tracking (future) | 8h | High |

---

## Quick Wins (Can Implement Now)

1. **Add pass_detail to worker.py** - Trivial change
2. **Update STAGE_LABELS descriptions** - Already has infrastructure
3. **Frontend shows pass_detail** - Already supported via `stageDescription` in useETA

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/worker.py` | Add pass_detail to update_job calls |
| `backend/pipeline/stages/semantic_extraction.py` | Add progress callback |
| `frontend/lib/constants.ts` | Improve stage descriptions |
| `frontend/hooks/useETA.ts` | Dynamic duration estimates |
| `frontend/store/jobs.ts` | Pass source_count to ETA hook |

---

## Questions

1. Should ETA show "calculating..." if elapsed < 30s?
2. Should we hide ETA when progress > 90% (near completion)?
3. Should we show source count in UI? ("Analyzing 5 sources...")
4. Historical tracking scope - per-user or global averages?
