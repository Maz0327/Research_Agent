# Phase 1: Composite Pipeline Quality Score

## Context Links

- [Plan Overview](plan.md)
- [Phase 2: Prompt Optimization](phase-02-prompt-optimization-loop.md) (depends on this)
- [Phase 3: Circuit Breakers](phase-03-circuit-breaker-expansion.md) (independent)

## Overview

Roll up 4 existing pipeline signals into a single numerical quality score per job. This score becomes the objective function for Phase 2's prompt optimization loop and provides observability into pipeline output quality over time.

No new LLM calls. Pure computation from data already produced by the pipeline.

## Key Insights

- All 4 signals already exist in the pipeline; we only need to aggregate them
- `validate_provenance_chain()` returns a warnings list -- completeness = 1 - (broken / total)
- `semantic_validation.py` enforces confidence ceilings; violations are already counted in ValidationReport
- LLM Judge `validation_rate` is 0.0-1.0 (valid_count / total items reviewed)
- Quality Gate `diversity_score` is Shannon entropy normalized to 0-1
- `quality_cost_ratio` = composite_score / total_cost gives cost-efficiency signal

## Requirements

1. **PipelineQualityScore** dataclass with 4 component signals + composite + quality_cost_ratio
2. Composite formula: weighted average with configurable weights, default `[0.35, 0.20, 0.25, 0.20]`
3. Store score in JobRecord as `quality_score: Optional[dict]`
4. Compute after provenance validation in `stage_document_assembly()`
5. Persist via `update_job()` alongside existing cost summary
6. Add `quality_score: Optional[dict]` to PipelineContext for downstream access

## Architecture

```
stage_document_assembly(ctx)
  |
  +-- validate_provenance_chain(ctx)  -->  provenance_completeness
  |
  +-- ctx.verification_rate           -->  validation_rate (from LLM Judge)
  |
  +-- ctx.quality_gate_stats          -->  diversity_score
  |
  +-- ctx.validation_warnings         -->  ceiling_compliance
  |
  +-- compute_quality_score(signals)  -->  PipelineQualityScore
  |
  +-- update_job(quality_score=score.to_dict())
```

### PipelineQualityScore Dataclass

```python
@dataclass
class PipelineQualityScore:
    validation_rate: float          # 0.0-1.0, from LLM Judge
    diversity_score: float          # 0.0-1.0, from Quality Gate
    provenance_completeness: float  # 0.0-1.0, 1 - (broken_refs / total_refs)
    ceiling_compliance: float       # 0.0-1.0, 1 - (violations / total_items)
    composite_score: float          # weighted average of above
    quality_cost_ratio: float       # composite_score / total_cost (0 if no cost)
    weights: dict[str, float]       # weight config used

    def to_dict(self) -> dict: ...
```

### Composite Formula

```python
DEFAULT_WEIGHTS = {
    "validation_rate": 0.35,
    "diversity_score": 0.20,
    "provenance_completeness": 0.25,
    "ceiling_compliance": 0.20,
}

composite = sum(signal * weight for signal, weight in zip(signals, weights))
```

Weights rationale:
- `validation_rate` highest -- LLM Judge catches hallucinations/grounding errors
- `provenance_completeness` second -- broken chains = broken documents
- `diversity_score` and `ceiling_compliance` equal -- both are hygiene signals

## Related Code Files

| File | Role |
|------|------|
| `backend/pipeline/quality_score.py` | NEW: PipelineQualityScore + compute function |
| `backend/models/job_record.py` | Add `quality_score` field to JobRecord |
| `backend/pipeline/context.py` | Add `quality_score` field |
| `backend/pipeline/stages/document_assembly.py` | Compute + persist score |
| `backend/pipeline/llm_judge.py` | Source of `validation_rate` (read-only) |
| `backend/pipeline/quality_gate.py` | Source of `diversity_score` (read-only) |
| `backend/pipeline/semantic_validation.py` | Source of ceiling violations (read-only) |

## Implementation Steps

### 1.1: Create `quality_score.py` module
- Define `PipelineQualityScore` dataclass
- Define `DEFAULT_WEIGHTS` dict
- Implement `compute_quality_score(validation_rate, diversity_score, provenance_completeness, ceiling_compliance, total_cost, weights=None) -> PipelineQualityScore`
- Add `to_dict()` method
- Full type hints, docstrings, loguru logging

### 1.2: Add `quality_score` field to models
- `backend/models/job_record.py`: Add `quality_score: Optional[dict[str, Any]] = Field(None, description="Pipeline quality score")`
- `backend/pipeline/context.py`: Add `quality_score: Optional[dict] = None`

### 1.3: Integrate into `stage_document_assembly()`
- After provenance validation and doc builds, collect signals:
  - `validation_rate` from `ctx.verification_rate` (already set by validation stage)
  - `diversity_score` from `ctx.quality_gate_stats.get("diversity_score", 0.0)`
  - `provenance_completeness` from provenance_warnings count vs total references
  - `ceiling_compliance` from `ctx.validation_warnings` count vs total items
- Call `compute_quality_score()`
- Store on `ctx.quality_score`
- Include in `update_job()` call

### 1.4: Write tests
- Unit tests for `compute_quality_score()` with known inputs
- Test edge cases: zero cost, all signals 1.0, all signals 0.0, empty pipeline
- Test `to_dict()` serialization
- Integration test: verify score appears in job record after assembly

### 1.5: Verify existing tests pass
- Run `pytest backend/tests/ -v`
- Ensure no regressions

## Todo List

- [ ] 1.1: Create `backend/pipeline/quality_score.py`
- [ ] 1.2: Add `quality_score` field to JobRecord and PipelineContext
- [ ] 1.3: Integrate computation into `stage_document_assembly()`
- [ ] 1.4: Write unit + integration tests
- [ ] 1.5: Run full test suite, fix any regressions

## Success Criteria

- `compute_quality_score()` returns valid score for any combination of inputs
- Quality score stored in JobRecord after every pipeline run
- All existing tests pass without modification
- New tests cover edge cases (zero cost, perfect score, empty pipeline)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| `verification_rate` not set (LLM Judge skipped/failed) | Score inaccurate | Default to 0.5 when LLM Judge unavailable |
| `quality_gate_stats` is None (stage skipped) | KeyError | Guard with `.get()` and default 0.0 |
| Division by zero in provenance completeness | Crash | Guard: if total_refs == 0, completeness = 1.0 |
| Weights don't sum to 1.0 | Misleading score | Assert/normalize in compute function |

## Security Considerations

- No external API calls; pure computation
- No user input in score computation
- Score stored as dict, not executable

## Next Steps

After Phase 1 completes:
- Phase 2 uses `composite_score` as the objective function for prompt optimization
- Future: dashboard visualization of quality scores over time
- Future: quality score thresholds for alerting on degraded jobs
