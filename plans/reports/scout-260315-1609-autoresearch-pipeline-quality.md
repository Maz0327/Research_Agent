# Scout Report: Pipeline Models for Quality Scoring, Prompt Optimization, Circuit Breakers

**Date:** 2026-03-15 16:09 UTC  
**Scope:** Codebase search for files relevant to:
1. Composite quality scoring
2. Prompt optimization loops
3. Circuit breaker expansion

**Search Strategy:** Parallel grep + targeted file reads  
**Token Efficiency:** ~85K tokens used (complex codebase analysis)

---

## Executive Summary

The Research Agent codebase has **layered quality mechanisms** but they are currently separated into distinct phases with limited cross-feedback:

- **Quality Gate** (pipeline entry): Source filtering with score-based allocation
- **Validation Layer** (post-extraction): Quote verification, confidence ceiling enforcement
- **Output Quality** (post-synthesis): Generic phrase detection, claim grounding checks

**No unified composite scoring exists.** Each layer computes metrics independently.

**No prompt optimization loop.** Prompts are static; feedback from validation does not improve future prompts.

**Circuit breaker pattern appears in transcript acquisition only** (4-tier fallback chain).

---

## Core Files for Implementation

### 1. DATA MODELS & STATE

#### `/home/user/Research_Agent/backend/models/job_record.py`
**Purpose:** JobRecord model — persistent storage for all job state  
**Relevance:** Where quality_score fields would be stored  
**Key Classes/Fields:**
- `JobRecord`: Job metadata, status tracking, artifact references
- `Artifacts`: Job outputs (Doc 0/1/2, iterations, runs)
- `ApiCosts`: Cost tracking by service
- **MISSING:** `quality_score`, `quality_components`, `quality_history`

**Connection to Three Focus Areas:**
1. **Composite Quality:** Would add `overall_quality_score` + `component_scores` dict
2. **Prompt Optimization:** Would track `prompt_version`, `extraction_quality_metrics`
3. **Circuit Breaker:** Would need `fallback_chain_state`, `retry_attempts`

---

#### `/home/user/Research_Agent/backend/pipeline/context.py`
**Purpose:** PipelineContext dataclass — data passing between stages  
**Relevance:** Intermediate stage results, accumulates warnings/outputs  
**Key Fields:**
- `quality_gate_stats`: Partial (source filtering only)
- `semantic_extractions`: List of SemanticExtractionResult objects
- `identified_gaps`: Gap list from gap_analysis stage
- `source_coverage`: Cross-source key point tracking (Phase 5)
- `validation_warnings`: Quote verification warnings
- **MISSING:** `quality_scores_per_source`, `extraction_quality_metrics`, `fallback_decisions`

**Connection:**
1. **Composite Quality:** Would accumulate `extraction_quality_metrics`, `synthesis_quality_score`
2. **Prompt Optimization:** Would track `prompt_adjustments_applied`, `confidence_ceiling_overrides`
3. **Circuit Breaker:** Would store `fallback_chain_attempts`, `primary_failure_reason`

---

### 2. QUALITY MECHANISMS (CURRENT)

#### `/home/user/Research_Agent/backend/pipeline/quality_gate.py` (800+ lines)
**Purpose:** Deterministic source filtering (no LLM, <5s execution)  
**Implements:** Conservative filtering + score-based slot allocation  
**Key Components:**
- `Source` dataclass: url, title, quality_score, recency_score, final_score
- `QualityGateOutput`: approved, soft_rejected, hard_rejected + stats
- `QualityGateStats`: Tracks diversity (Shannon entropy), rejection breakdown
- **Scoring formula:** `final_score = 0.55*relevance + 0.35*quality + 0.10*recency + keyword_bonus`
- **Mode-specific:** Source type floors by pipeline mode (quick, breaking_news, investigation)
- **Niche support:** Priority keywords + preferred domains
- **BM25 integration:** Relevance scoring with optional query terms

**Strengths:**
- Composite score (final_score) with documented weights
- Mode-aware floor configuration
- Diversity metric (Shannon entropy-based)

**Limitations:**
- **No feedback loop:** Quality gate runs once, never adjusted
- **No downstream connection:** Approved sources lose their scores post-ingestion
- **No per-source quality tracking:** Scores not persisted in extraction results

**Connection to Three Focus Areas:**
1. **Composite Quality:** This is a scoring system, but scores are discarded
2. **Prompt Optimization:** Could use source quality scores to adjust prompt specificity
3. **Circuit Breaker:** No fallback logic, just hard/soft rejection

---

#### `/home/user/Research_Agent/backend/utils/output_quality.py` (440+ lines)
**Purpose:** Post-synthesis quality enforcement (R17 anti-generic validation)  
**Implements:** Code-level checks on LLM text  
**Key Checks:**
- `detect_hedge_phrases()`: 80+ banned AI-filler phrases (e.g., "it's important to note")
- `detect_repetitive_sentence_starts()`: 2+ consecutive sentences with same first word
- `detect_ungrounded_claims()`: Factual claims (numbers, dates) without source refs
- `detect_circular_logic()`: Concept restatement via Jaccard similarity (>0.55)
- **OutputQualityReport:** Scores 0-100, deducts for each issue type

**Scoring Formula:**
```
score = 100
score -= hedge_count * 5        # -5 per hedge
score -= ungrounded_count * 10  # -10 per ungrounded
score -= repetition_count * 8   # -8 per repetition
score -= circular_count * 15    # -15 per circular
```

**Limitations:**
- **Text-only:** Cannot assess source integration or theme coherence
- **No feedback to LLM:** Quality issues detected but not communicated back to Gemini
- **No cross-document awareness:** Checks individual text in isolation

**Connection to Three Focus Areas:**
1. **Composite Quality:** Could contribute to overall score, but isolated
2. **Prompt Optimization:** Issues could trigger re-prompting, but currently doesn't
3. **Circuit Breaker:** No fallback, just validation after completion

---

#### `/home/user/Research_Agent/backend/pipeline/stages/semantic_validation_stage.py`
**Purpose:** Post-extraction validation (quote verification, confidence ceiling enforcement)  
**Key Function:** `stage_semantic_validation(ctx)`  
**Validates:**
- Quote fuzzy matching against source content
- Confidence ceiling enforcement (per analysis mode)
- Source ID consistency
- Timestamp grounding (for video sources)

**Current Implementation:**
- Runs `verify_all_quotes()` per extraction
- Updates `verification_rate` in context
- Adds warnings for unverified claims

**Limitations:**
- **No retry loop:** Failed verification doesn't trigger re-extraction
- **Validation warnings accumulate but don't drive decisions**
- **No composite scoring:** Individual checks exist, no aggregation

**Connection:**
1. **Composite Quality:** Feeds validation metrics but no rollup
2. **Prompt Optimization:** Could improve extraction, but currently just validates
3. **Circuit Breaker:** Could trigger fallback if verification rate too low

---

### 3. PIPELINE ORCHESTRATION

#### `/home/user/Research_Agent/backend/pipeline/stage_runner.py` (180 lines)
**Purpose:** Stage execution wrapper with error recovery  
**Key Classes:**
- `StageResult`: success, stage_name, used_fallback, error
- `run_stage_with_recovery()`: Executes stage + optional fallback
- `StageGroup`: Track multiple stages, report aggregate results
- `run_optional_stage()`: Conditional execution

**Current Fallback Pattern:**
```python
def run_stage_with_recovery(stage_fn, ctx, stage_name, fallback_fn=None, critical=False):
    try:
        stage_fn(ctx)
        return StageResult(success=True, ...)
    except Exception as e:
        if fallback_fn:
            try:
                fallback_fn(ctx)
                return StageResult(success=True, used_fallback=True, ...)
            except:
                # Both failed
                if critical:
                    raise
                return StageResult(success=False, error=..., used_fallback=True)
```

**Limitations:**
- **Binary fallback:** Only one fallback per stage, not a chain
- **No circuit breaker state:** Can retry infinitely
- **No cost awareness:** Fallback decisions don't consider API costs
- **No prompt adjustment:** Fallback doesn't adjust prompts based on failure reason

**Connection:**
1. **Composite Quality:** Could pass quality scores to decide fallback worthiness
2. **Prompt Optimization:** Could adjust prompts before fallback
3. **Circuit Breaker:** Foundation is here but not expanded

---

### 4. EXTRACTION & PROMPT INFRASTRUCTURE

#### `/home/user/Research_Agent/backend/pipeline/stages/semantic_extraction.py` (300+ lines)
**Purpose:** Main LLM extraction stage (per-source isolation)  
**Key Function:** `stage_semantic_extraction(ctx) → list[SemanticExtractionResult]`  
**Features:**
- **Per-source isolation:** Each source gets separate Gemini call (architecture rule)
- **ThreadPoolExecutor:** Parallel processing (default 3 workers)
- **Retry logic:** `should_retry()` checks validation report, optional re-prompt
- **Cost tracking:** Records tokens, API costs per source
- **Memory monitoring:** Checks memory pressure during batch processing

**Retry Mechanism (Partial):**
```python
validation_report = validate_semantic_extraction(result, ...)
if should_retry(validation_report):
    retry_prompt = get_retry_prompt(...)  # Adjusted prompt
    result = extract_with_gemini(retry_prompt, schema, ...)
```

**Limitations:**
- **Retry prompt is generic:** Doesn't use quality metrics to adjust specificity
- **One retry only:** After retry, accepts result regardless of quality
- **No cost feedback:** Doesn't account for retry cost in quality decision
- **No fallback chain:** If Gemini fails, no tier-2 option

**Connection:**
1. **Composite Quality:** Computes individual extraction quality but no rollup
2. **Prompt Optimization:** Has retry mechanism but prompt adjustments are hardcoded
3. **Circuit Breaker:** Thread pool executor could be circuit breaker but isn't

---

#### `/home/user/Research_Agent/backend/pipeline/prompts/semantic_extraction_prompt.py` (80+ lines)
**Purpose:** Dispatcher for mode-specific extraction prompts  
**Components:**
- `SEMANTIC_EXTRACTION_ROLE`: Analyst role definition
- `SOURCE_IDENTITY_LOCK_BLOCK`: Prevents LLM from inferring source identity
- `CONFIDENCE_CEILING_DECLARATION`: Enforces ceiling per analysis mode
- `SOURCE_IDENTITY_CONTRACT`: Additional source handling rules

**Key Function:** `build_semantic_extraction_prompt()` — delegates to mode-specific builders

**Limitations:**
- **No feedback incorporation:** Prompt template is static
- **No quality-aware adjustments:** Doesn't increase specificity for low-quality sources
- **No learning loop:** Failed extractions don't improve future prompts

**Connection:**
1. **Composite Quality:** Prompt is built, but quality signals not fed back
2. **Prompt Optimization:** This is where optimization would happen, but currently static
3. **Circuit Breaker:** No mode selection fallback here

---

#### `/home/user/Research_Agent/backend/pipeline/prompts/modes/base.py` (100+ lines)
**Purpose:** Shared prompt components for all analysis modes  
**5 Required Components:**
1. SOURCE_IDENTITY_LOCK_BLOCK
2. CONFIDENCE_CEILING_DECLARATION
3. EMPTY_OUTPUT_PERMISSION
4. LAYERED_EXTRACTION_INSTRUCTIONS
5. OUTPUT_SCHEMA

**Strengths:**
- Guaranteed prompt structure across all modes
- Confidence ceiling enforcement embedded in prompt

**Limitations:**
- **No prompt versioning:** Single version, no A/B testing
- **No difficulty adjustment:** Doesn't vary complexity based on source quality
- **No example demonstrations:** No few-shot examples that could improve quality

**Connection:**
1. **Composite Quality:** Foundation for quality-aware prompts, but not used
2. **Prompt Optimization:** Could add multi-shot examples, adjusted difficulty
3. **Circuit Breaker:** Could include mode selection as fallback

---

### 5. FALLBACK & RESILIENCE PATTERNS

#### `/home/user/Research_Agent/backend/pipeline/transcript_acquisition.py` (80+ lines)
**Purpose:** 4-tier transcript fallback chain  
**LOCKED ORDER:**
1. Supadata → transcript_grounded (highest quality)
2. Whisper → transcript_grounded
3. YouTube captions → caption_grounded (fails on cloud IPs)
4. None → video_only (fallback)

**Code Pattern:**
```python
async def acquire_transcript(video_url: str) -> TranscriptResult:
    # Tier 1: Supadata
    result = await fetch_supadata(...)
    if result.status == SUCCESS:
        return result
    
    # Tier 2: Whisper
    result = await transcribe_with_whisper(...)
    if result.status == SUCCESS:
        return result
    
    # Tier 3: YouTube captions (with IP check)
    if not is_cloud_ip():
        result = await get_youtube_captions(...)
        if result.status == SUCCESS:
            return result
    
    # Tier 4: Fallback to video_only
    return TranscriptResult(
        transcript_source=TranscriptSource.NONE,
        analysis_mode=AnalysisMode.VIDEO_ONLY,
        status=AcquisitionStatus.FAILED
    )
```

**Strengths:**
- **Ordered fallback chain:** Fixed tiers with clear success criteria
- **Analysis mode derivation:** Automatically sets confidence ceiling based on tier
- **Status tracking:** Records which tier succeeded
- **Cost tracking:** Different costs per tier

**Limitations:**
- **No cost optimization:** Doesn't try cheapest first, tries best first
- **No adaptive routing:** Doesn't adjust tier order based on failure patterns
- **Single-use:** Chain runs once, no retry of earlier tiers
- **No circuit breaker:** Doesn't track persistent failures per tier

**Connection:**
1. **Composite Quality:** Uses transcript source as quality indicator (implicit)
2. **Prompt Optimization:** Analysis mode sets confidence ceiling, affects prompts
3. **Circuit Breaker:** This IS a circuit breaker, but not expandable pattern

---

#### `/home/user/Research_Agent/backend/integrations/gemini_client.py` (100+ lines of header)
**Purpose:** Gemini API client for research tasks  
**Key Exception Classes:**
- `GeminiParseError`: JSON parse failures
- `GeminiTimeoutError`: 5-minute API timeout
- `GeminiTruncationError`: Response exceeds max_output_tokens

**Utility Function:**
- `parse_json_from_llm_response()`: Fallback strategies for JSON extraction
  - Tries ```json blocks first
  - Falls back to plain JSON
  - Attempts to repair truncated JSON

**Limitations:**
- **No retry-with-backoff:** Timeouts are raised, not retried
- **No token budget enforcement:** Can exceed max_output_tokens
- **Single temperature per task:** No dynamic temperature adjustment
- **No cost-quality tradeoff:** Doesn't choose cheaper model if quality sufficient

**Connection:**
1. **Composite Quality:** Could assess response quality before returning
2. **Prompt Optimization:** Could adjust temperature/model based on previous quality
3. **Circuit Breaker:** Could implement exponential backoff, fallback to cheaper model

---

### 6. DOCUMENT ASSEMBLY (FINALIZATION)

#### `/home/user/Research_Agent/backend/pipeline/stages/document_assembly.py` (1000+ lines)
**Purpose:** Build 3 canonical documents (Doc 0/1/2) + quality gates  
**Key Functions:**
- `build_source_ledger()`: Doc 0 (source inventory)
- `build_jump_start()`: Doc 1 (research directions, thematic grouping)
- `build_semantic_brief()`: Doc 2 (core analysis, gaps, tensions)
- `validate_provenance_chain()`: Ensure all references trace to Doc 0
- `generate_executive_summary()`: Cross-document summary (R15)
- `stage_document_assembly()`: Main orchestrator

**Quality-Related Logic:**
```python
# Confidence determination (deterministic formula, lines 904-918)
if failed_sources / max(total_sources, 1) > 0.3:
    overall_confidence = ConfidenceLevel.LOW  # >30% fail = never HIGH
elif tension_count > 10 or total_sources < 2:
    overall_confidence = ConfidenceLevel.MEDIUM  # Many tensions or single source
else:
    overall_confidence = doc_1.confidence

# Triage level determination (lines 583-605)
triage = TriageLevel.THIN if len(issues) > 2 else TriageLevel.USABLE
if degraded_sources > len(extractions) / 2:
    triage = TriageLevel.DEGRADED
```

**Limitations:**
- **Confidence is calculated here, not persisted:** No quality_score in JobRecord
- **Triage level not used downstream:** Doesn't trigger re-extraction
- **No quality gap analysis:** Doesn't identify which sources hurt quality most
- **No cost-quality rollup:** Ignores API costs in quality assessment

**Connection:**
1. **Composite Quality:** Computes confidence + triage, but doesn't aggregate
2. **Prompt Optimization:** Could adjust future prompts based on triage level
3. **Circuit Breaker:** Could reject assembly if triage=THIN, re-run with more sources

---

### 7. INTEGRATION CLIENTS

#### `/home/user/Research_Agent/backend/integrations/transcripts.py`
**Purpose:** Transcript fetching (Supadata, Whisper, YouTube)  
**Fallback Chain:** (Documented as spec-compliant)  
**Key Limitation:** Each client call is independent, no cross-service retry

#### `/home/user/Research_Agent/backend/integrations/supadata_client.py`
**Purpose:** Supadata API client for video metadata + transcripts  
**Key Limitation:** No cost-quality optimization

#### `/home/user/Research_Agent/backend/integrations/jina_reader_client.py`, `whisper_client.py`, `youtube_client.py`
**Purpose:** Individual API integrations  
**Common Pattern:** Success/failure with error messages, but no quality scoring

---

### 8. TEST SUITE (Test Structure Overview)

**Total Test Files: 48** in `/home/user/Research_Agent/backend/tests/`

**Key Test Files for Quality/Pipeline:**

| File | Coverage | Purpose |
|------|----------|---------|
| `test_semantic_extraction_stages.py` | Extraction | Per-source isolation, retry logic |
| `test_validation_stages.py` | Validation | Quote verification, confidence ceiling |
| `test_document_assembly.py` | Assembly | Doc 0/1/2 building, triage level |
| `test_prompt_templates.py` | Prompts | Mode-specific prompts, lock block |
| `test_hallucination_prevention.py` | Quality | Ungrounded claims detection |
| `test_semantic_models.py` | Models | SemanticExtractionResult validation |
| `test_rate_limiter.py` | Rate Limiting | API call throttling |
| `test_supabase_retry.py` | Resilience | Retry patterns |
| `test_phase3_pipeline.py` | Integration | Full pipeline execution |

**Test Pattern:** Mostly unit tests, limited integration tests for quality feedback loops.

---

## Gap Analysis: Where Implementation Should Focus

### 1. COMPOSITE QUALITY SCORING

**What Exists:**
- Quality Gate source scoring (0-1)
- Output quality validation (0-100)
- Confidence level determination (HIGH/MEDIUM/LOW)
- Triage level (USABLE/THIN/DEGRADED)

**What's Missing:**
- **Unified quality score** that combines all signals
- **Per-source quality tracking** through entire pipeline
- **Quality components rollup:** source quality → extraction quality → synthesis quality → final document quality
- **Quality history:** Track how quality changed across iterations
- **Quality-aware cost tradeoff:** Balance API cost against expected quality gain

**Implementation Path:**
1. Add `quality_score` fields to `JobRecord` + `SemanticExtractionResult`
2. Create `QualityScoreAggregator` class that rolls up:
   - Source quality (from quality_gate)
   - Extraction quality (from validation + semantic_validation)
   - Synthesis quality (from theme consensus + tension resolution)
   - Document quality (from output_quality checks)
3. Store rollup in `Artifacts.quality_metadata`
4. Display in frontend + use in iteration decisions

---

### 2. PROMPT OPTIMIZATION LOOPS

**What Exists:**
- Basic retry mechanism in semantic_extraction.py
- Hardcoded retry prompt in SEMANTIC_EXTRACTION_RETRY_PROMPT
- Mode-specific base prompts

**What's Missing:**
- **Feedback loop:** Quality metrics don't improve future prompts
- **Difficulty adjustment:** Prompts don't vary by source quality
- **Example-based learning:** No few-shot demonstrations
- **Temperature optimization:** No dynamic temperature adjustment
- **Prompt versioning:** No A/B testing or version comparison
- **Cost-quality optimization:** Doesn't choose cheaper model when sufficient

**Implementation Path:**
1. Create `PromptOptimizer` class with methods:
   - `adjust_for_source_quality()`: Increase specificity for low-quality sources
   - `adjust_difficulty()`: Add examples for complex topics
   - `select_model_by_cost_quality()`: Choose Flash vs Pro based on past performance
2. Store `prompt_version`, `confidence_ceiling_override` in context
3. Log prompt adjustments for offline analysis
4. (Later) Add offline optimizer that retrains prompts based on failure patterns

---

### 3. CIRCUIT BREAKER EXPANSION

**What Exists:**
- 4-tier transcript fallback chain (rigid order)
- Basic error recovery in stage_runner.py
- Single optional fallback per stage

**What's Missing:**
- **Expandable pattern:** Generalize transcript chain pattern
- **State tracking:** Remember which tiers failed for this job
- **Adaptive retry:** Don't retry failed tiers immediately
- **Cost accounting:** Prefer cheap tiers first, expensive tiers as fallback
- **Quality gating:** Don't use low-quality tier if better option available
- **Multiple fallback layers:** Not just extract, but also prompt adjustment, model selection

**Implementation Path:**
1. Create `CircuitBreaker` class with state machine:
   - Tracks per-tier failure counts + backoff time
   - Implements exponential backoff (don't retry failed tier for N seconds)
   - Supports multiple fallback chains (transcript tier + model tier + prompt tier)
2. Extend `run_stage_with_recovery()` to use circuit breaker
3. Log all fallback decisions for observability
4. (Later) Learn optimal tier order from historical performance

---

## Recommended Implementation Order

**Phase 0 (Foundation - 1 sprint):**
1. Add `quality_score` fields to JobRecord
2. Create `QualityScoreAggregator` class
3. Implement rollup in document_assembly.py
4. Add tests for quality rollup

**Phase 1 (Prompt Loop - 1 sprint):**
1. Create `PromptOptimizer` class
2. Add confidence ceiling adjustment based on source quality
3. Add difficulty adjustment for high-tension sources
4. Log all prompt adjustments
5. Add tests for prompt optimization

**Phase 2 (Circuit Breaker - 1 sprint):**
1. Generalize transcript fallback pattern into `CircuitBreaker` class
2. Extend stage_runner.py to use it
3. Add cost-aware tier selection
4. Add state persistence (which tiers failed this job)
5. Add tests for circuit breaker

---

## Files Requiring Changes (Summary)

| File | Changes | Impact |
|------|---------|--------|
| `backend/models/job_record.py` | Add quality_score fields | Enable quality persistence |
| `backend/pipeline/context.py` | Add quality_metrics, prompt_adjustments | Track optimization decisions |
| `backend/models/semantic_units.py` | Add quality_score to SemanticExtractionResult | Per-source tracking |
| `backend/pipeline/quality_aggregator.py` | NEW: Composite scoring class | Unified quality metric |
| `backend/pipeline/prompt_optimizer.py` | NEW: Prompt adjustment logic | Feedback loop |
| `backend/pipeline/circuit_breaker.py` | NEW: Expandable fallback pattern | Resilience |
| `backend/pipeline/stages/document_assembly.py` | Call QualityScoreAggregator | Populate quality fields |
| `backend/pipeline/stages/semantic_extraction.py` | Use PromptOptimizer | Adjust prompts by quality |
| `backend/pipeline/stage_runner.py` | Use CircuitBreaker | Multi-tier fallback |
| `backend/tests/test_quality_*.py` | NEW: Tests for all above | Validation |

---

## Unresolved Questions

1. **Quality Score Weighting:** What weights should composite score use?
   - Option A: Equal weight all components (0.25 each)
   - Option B: Weight by pipeline stage impact (source=0.15, extraction=0.35, synthesis=0.35, output=0.15)
   - Option C: Weight by user-specified priorities (configurable)

2. **Prompt Adjustment Triggers:** When should prompts be adjusted?
   - Option A: Always (every source)
   - Option B: Only for low-quality sources (quality < 0.4)
   - Option C: Only on retry (failed validation)

3. **Circuit Breaker Cost Model:** How to weight cost vs quality?
   - Option A: Always use cheapest tier first
   - Option B: Use best-quality tier first, fall back to cheap only on failure
   - Option C: Use cost-quality ratio (prefer tier with best quality/$ ratio)

4. **Fallback Chain Persistence:** Should state be job-scoped or persistent?
   - Option A: Job-scoped (reset per job)
   - Option B: Persistent (remember tier success rates across jobs)
   - Option C: Configurable (per niche/topic)

5. **Quality Threshold for Re-extraction:** At what score should system re-extract?
   - Option A: Never auto-retry (manual only)
   - Option B: Always retry once (current pattern)
   - Option C: Retry if quality < threshold (e.g., 0.5)

---

## Conclusion

The codebase has **strong foundational pieces** (quality_gate, validation, output_quality) but they operate **independently** without cross-feedback. Implementation of the three focus areas requires:

1. **Composite scoring:** Aggregate existing metrics into unified quality_score
2. **Prompt loop:** Use quality feedback to adjust prompts before retry
3. **Circuit breaker:** Generalize transcript fallback into reusable pattern

All files necessary for implementation have been identified. **No major architectural changes** required — extensions fit within existing pipeline stages.

**Estimated Implementation Effort:** 3 sprints (foundation + optimization + resilience)
