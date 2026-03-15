---
title: "Autoresearch Pipeline Quality"
description: "Apply Karpathy's autoresearch self-improving pattern to the Research Agent pipeline in 3 phases"
status: pending
priority: P2
effort: 12h
branch: claude/review-video-insights-de0aU
tags: [quality, observability, circuit-breaker, prompt-optimization]
created: 2026-03-15
---

# Autoresearch Pipeline Quality

Apply the autoresearch loop (modify -> verify -> keep/revert -> log -> repeat) to the Research Agent pipeline.

## Phases

| # | Phase | Effort | Depends On | Detail File |
|---|-------|--------|------------|-------------|
| 1 | Composite Pipeline Quality Score | 4h | None | [phase-01](phase-01-composite-quality-score.md) |
| 2 | Prompt Optimization Loop (dev tool) | 4h | Phase 1 | [phase-02](phase-02-prompt-optimization-loop.md) |
| 3 | Circuit Breaker Expansion | 4h | None (parallel w/ Phase 2) | [phase-03](phase-03-circuit-breaker-expansion.md) |

## Key Decisions

- Phase 1 rolls up 4 existing signals into one composite score; no new LLM calls
- Phase 2 is an offline dev script, not production code
- Phase 3 extracts the existing LLM Judge circuit breaker into a shared utility

## Constraints

- Must not break existing tests
- No new dependencies unless essential
- Commit format: `Phase X.Y: [description]`
- Follow architecture rules in `docs/authoritative/INDEX.md`

## Validation Summary

**Validated:** 2026-03-15
**Questions asked:** 7

### Confirmed Decisions
- **Quality score weights:** Accept defaults (validation=0.35, provenance=0.25, diversity=0.20, ceiling=0.20)
- **LLM Judge unavailable fallback:** Default validation_rate to 0.5 (neutral)
- **Gemini circuit breaker threshold:** 5 failures before trip
- **LLM Judge circuit breaker threshold:** Keep threshold=1 (matches current _PROVIDER_DISABLED behavior)

### Changes from Plan
- [ ] **Phase 1:** Move quality score computation to a new **post-assembly stage** instead of inside document_assembly — cleaner separation of concerns
- [ ] **Phase 2:** Add `--run` flag to trigger a pipeline run on a test topic (measure + trigger), not just measure existing jobs
- [ ] **Phase 3:** Add `threading.Lock` to CircuitBreaker's `record_failure()`/`record_success()` for thread safety in ThreadPoolExecutor

## Files Created

| File | Phase |
|------|-------|
| `backend/pipeline/quality_score.py` | 1 |
| `scripts/prompt_optimizer.py` | 2 |
| `backend/pipeline/circuit_breaker.py` | 3 |

## Files Modified

| File | Phase | Change |
|------|-------|--------|
| `backend/models/job_record.py` | 1 | Add `quality_score` field |
| `backend/pipeline/context.py` | 1 | Add `quality_score` field |
| `backend/pipeline/stages/quality_assessment.py` | 1 | NEW: post-assembly stage for quality score |
| `backend/pipeline/stage_runner.py` | 1 | Add quality_assessment after document_assembly |
| `backend/pipeline/transcript_acquisition.py` | 3 | Wrap fallback chain |
| `backend/pipeline/stages/semantic_extraction.py` | 3 | Add Gemini circuit breaker |
| `backend/pipeline/llm_judge.py` | 3 | Migrate to shared CircuitBreaker |
| `backend/pipeline/iteration/metrics_tracker.py` | 3 | Add failure tracking |
