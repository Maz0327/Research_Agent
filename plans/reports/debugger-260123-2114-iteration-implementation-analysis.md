# Iteration Feature Implementation Analysis

**Date:** 2026-01-23
**Job ID:** debugger-260123-2114
**Status:** Complete

---

## Executive Summary

Iteration feature scaffolding complete. Infrastructure present for 4 modes (more_sources, deeper, different_angle, custom). API endpoint functional, models defined, worker task skeleton exists. Implementation blocked at line 1760-1810 in `backend/worker.py` with "coming soon" placeholder.

**Key Finding:** All supporting infrastructure exists. Implementation requires mode-specific pipeline orchestration calling existing extraction/synthesis stages.

---

## Infrastructure Inventory

### 1. Data Models (Complete)

**Location:** `backend/models/job_record.py`

```python
# Core iteration models (lines 12-73)
- IterationRequest: mode, user_prompt, target, max_new_sources, angle, constraints
- IterationInputs: baseline doc paths, source hashes, URLs added/used
- IterationOutputs: iteration-specific doc_0/1/2 paths + inline fallback
- IterationMetrics: llm_calls, tokens, wall_time
- IterationError: message + stack trace
- Iteration: Full bundle (id, index, timestamps, status, request, inputs, outputs, metrics)

# Artifact storage (lines 113)
- Artifacts.iterations: list[Iteration] (append-only)
```

**Key Features:**
- Append-only design (baseline never modified)
- Separate tracking fields: `iteration_status`, `iteration_id`, `iteration_progress_percent`
- Captures baseline state before iteration starts

### 2. API Endpoint (Complete)

**Location:** `backend/app/routes/jobs_routes.py` (lines 1406-1612)

**Endpoint:** `POST /{job_id}/iterate`

**Validation:**
- Job must be completed
- No concurrent iteration running (TOCTOU race protection via unique constraint)
- Baseline docs (Doc 0/1/2) must exist (storage path OR inline data)

**Request Model:**
```python
class IterateJobRequest:
    mode: "more_sources" | "deeper" | "different_angle" | "custom"
    user_prompt: str (max 2000 chars)
    max_new_sources: int (0-10, default 4)
    angle: Optional[str]
```

**Flow:**
1. Creates `Iteration` object with queued status
2. Appends to `artifacts.iterations[]`
3. Enqueues `run_iteration_task` with task_id=`{job_id}_{iteration_id}`
4. Returns `IterateJobResponse` with iteration_id

### 3. Worker Task (Scaffolded)

**Location:** `backend/worker.py` (lines 1679-1807)

**Task:** `run_iteration_task(job_id, iteration_id, user_id)`

**Current State:**
- Loads job + artifacts ✅
- Finds iteration in artifacts array ✅
- Extracts request parameters (mode, user_prompt, max_new_sources, angle) ✅
- Updates iteration status to "running" ✅
- **BLOCKS at line 1762:** Placeholder "not implemented" error
- Marks iteration failed with clear message ✅

**Missing:** Actual pipeline logic (lines 1762-1774)

### 4. Pipeline Context Support

**Location:** `backend/pipeline/context.py`

**Relevant Fields:**
```python
# Extraction stage outputs (line 79)
semantic_extractions: list[SemanticExtractionResult]

# Source identity (line 77)
source_identity_packages: list[SourceIdentityPackage]

# Gap analysis (line 81)
identified_gaps: list[Gap]

# Synthesis outputs (lines 91-96)
semantic_core: str
synthesized_themes: list[Theme]
speculative_observations: list
confidence_reasoning: list
overall_confidence: str

# Document assembly (lines 86-88)
source_ledger: dict
jump_start: dict
semantic_brief: dict
```

**Note:** Context designed for single pipeline run. Iteration will need fresh context initialized from baseline data.

---

## Available Data from Completed Jobs

### Stored in Artifacts

**Inline Data:**
- `artifacts.source_ledger` (Doc 0 data)
- `artifacts.jump_start` (Doc 1 data)
- `artifacts.semantic_brief` (Doc 2 data)
- `artifacts.semantic_extractions` (per-source extraction results)

**Storage Paths:**
- `artifacts.doc_0_path` → Supabase Storage path
- `artifacts.doc_1_path`
- `artifacts.doc_2_path`

**Extraction Data Structure:**
```python
# Each item in semantic_extractions contains:
{
  "source_id": "SRC_1",
  "analysis_mode": "transcript_grounded",
  "quotes": [...],
  "claims": [...],
  "key_points": [...],
  "themes": [...],
  "tensions": [...],
  "approximate_observations": [...],  # video_only mode
  "transcript_source": "supadata",
  "parse_error": false
}
```

### Available in Job Config

**Location:** `job.config_json`

```python
{
  "topic": "Research topic",
  "input_mode": "mixed",
  "video_urls": [...],
  "article_urls": [...],
  "text_inputs": [...],
  "screenshots": [...],
  "source_count": N,
  "user_email": "...",
  "user_id": "..."
}
```

---

## Reusable Pipeline Stages

### Source Identity Builder

**File:** `backend/pipeline/stages/source_identity.py`

**Functions:**
```python
build_source_identity_from_video(url, source_id) → SourceIdentityPackage
build_source_identity_from_article(url, source_id) → SourceIdentityPackage
build_source_identity_from_text(text, source_id, title) → SourceIdentityPackage
build_source_identity_from_screenshot(img_data, source_id) → SourceIdentityPackage
```

**Output:** Deterministic identity resolution before LLM (source_id, analysis_mode, transcript_source, content, provenance)

### Semantic Extraction

**File:** `backend/pipeline/stages/semantic_extraction.py`

**Key Functions:**
```python
# Main stage
stage_semantic_extraction(ctx: PipelineContext) → None
  - Processes ctx.source_identity_packages
  - Outputs to ctx.semantic_extractions

# Core extraction
extract_semantic_structure(gemini_client, source_id, content, analysis_mode, title)
  → (SemanticExtractionResult, ValidationReport, cost)

# Parallel processing (line 19)
Uses ThreadPoolExecutor for parallel source processing
Configurable via SEMANTIC_EXTRACTION_MAX_WORKERS (default: 3)
```

**Features:**
- Isolated per-source extraction (no cross-contamination)
- Confidence ceiling enforcement
- Quote verification (transcript-grounded modes)
- Retry logic for validation failures

### Gap Analysis

**File:** `backend/pipeline/stages/gap_analysis.py`

**Purpose:** Identify missing coverage in semantic extractions

**Output:** `ctx.identified_gaps` (list of Gap objects)

### Semantic Synthesis

**File:** `backend/pipeline/stages/semantic_synthesis.py`

**Function:** `stage_semantic_synthesis(ctx: PipelineContext) → None`

**Process:**
1. Aggregates all semantic units from `ctx.semantic_extractions`
2. Includes gaps from `ctx.identified_gaps`
3. Calls Gemini for cross-source synthesis
4. Outputs to `ctx.semantic_core`, `ctx.synthesized_themes`, `ctx.speculative_observations`

**Input Requirements:**
- `ctx.semantic_extractions` (from extraction stage)
- `ctx.identified_gaps` (from gap analysis)
- `ctx.topic` (scope lock)

### Document Assembly

**File:** `backend/pipeline/stages/document_assembly.py`

**Function:** `stage_document_assembly(ctx: PipelineContext) → None`

**Process:**
1. Builds Doc 0 (Source Ledger) from sources + extractions
2. Builds Doc 1 (Jump-Start) from synthesis + gaps
3. Builds Doc 2 (Semantic Brief) from themes + key points + tensions
4. Stores in `ctx.outputs`

**Functions:**
```python
build_source_ledger(topic, sources, extractions) → SourceLedger
build_jump_start(topic, semantic_core, themes, gaps, quality) → JumpStartDirections
build_semantic_brief(topic, semantic_core, themes, kps, tensions, gaps, confidence) → SemanticBrief
```

### Completion Stage

**File:** `backend/pipeline/stages/initialization.py`

**Function:** `stage_10_completion(ctx: PipelineContext) → None`

**Process:**
1. Uploads docs to Supabase Storage (if available)
2. Builds artifact manifest
3. Updates job with final artifacts
4. Marks job completed

---

## Implementation Plan by Mode

### Mode 1: `more_sources`

**Goal:** Find and analyze additional sources, produce updated docs

**Pipeline Flow:**
1. **Load Baseline**
   - Fetch baseline Doc 0/1/2 from storage or inline
   - Load existing `semantic_extractions` from artifacts

2. **Source Discovery** (NEW CODE NEEDED)
   - Extract research focus from baseline Doc 1 (jump_start.research_directions)
   - Use Tavily/Perplexity to find `max_new_sources` additional URLs
   - Filter against baseline sources (deduplicate)

3. **Source Identity** (REUSE)
   - Call `build_source_identity_from_*()` for each new URL
   - Create `SourceIdentityPackage` objects

4. **Extraction** (REUSE)
   - Initialize fresh `PipelineContext`
   - Set `ctx.source_identity_packages` = new sources only
   - Run `stage_semantic_extraction(ctx)`
   - Merge new extractions with baseline extractions

5. **Gap Analysis** (REUSE)
   - Set `ctx.semantic_extractions` = baseline + new
   - Run `stage_gap_analysis(ctx)`

6. **Synthesis** (REUSE)
   - Set `ctx.semantic_extractions` = baseline + new
   - Run `stage_semantic_synthesis(ctx)`

7. **Document Assembly** (REUSE)
   - Run `stage_document_assembly(ctx)`
   - Produces iteration-specific doc_0/doc_1/doc_2

8. **Storage**
   - Upload iteration docs to storage under `{job_id}/iterations/{iteration_id}/`
   - Update `iteration.outputs` with paths
   - Mark iteration completed

**New Code Required:**
- Source discovery function (Tavily/Perplexity integration)
- URL deduplication against baseline
- Baseline data loader

### Mode 2: `deeper`

**Goal:** Re-analyze existing sources with deeper prompts

**Pipeline Flow:**
1. **Load Baseline**
   - Fetch baseline Doc 0 for source list
   - DO NOT load semantic_extractions (we're re-extracting)

2. **Source Reconstruction** (NEW CODE NEEDED)
   - Parse Doc 0 source entries
   - Reconstruct `SourceIdentityPackage` for each source
   - Fetch original transcripts/content (cached or re-fetch)

3. **Modified Extraction** (MODIFY EXISTING)
   - Create custom prompt modifier for "deeper analysis"
   - Adjust extraction prompts to request:
     - More granular key points
     - Additional themes from implicit patterns
     - Confidence-based speculation (labeled)
   - Run `stage_semantic_extraction(ctx)` with modified prompts

4. **Gap Analysis → Synthesis → Assembly** (REUSE)
   - Same as mode 1, steps 5-8

**New Code Required:**
- Source reconstruction from Doc 0
- Prompt modifier for deeper analysis
- Content re-fetcher (with caching)

**Alternative (Cheaper):**
- Re-use baseline extractions
- Run synthesis-only with modified synthesis prompt (ask for deeper themes)
- Skip re-extraction entirely

### Mode 3: `different_angle`

**Goal:** Explore different perspective on same sources

**Pipeline Flow:**
1. **Load Baseline**
   - Load semantic_extractions from artifacts (no re-extraction)

2. **Angle Definition** (NEW CODE NEEDED)
   - Parse `angle` parameter (e.g., "financial impact", "technical feasibility")
   - OR use user_prompt to derive angle via LLM

3. **Angle-Filtered Synthesis** (MODIFY EXISTING)
   - Modify synthesis prompt with angle focus
   - Request themes/tensions relevant to angle
   - Filter key points by angle relevance (optional)
   - Run `stage_semantic_synthesis(ctx)` with angle-specific prompt

4. **Document Assembly** (REUSE)
   - Standard assembly with synthesized outputs

5. **Storage** (REUSE)
   - Same as mode 1, step 8

**New Code Required:**
- Angle extraction from user_prompt
- Synthesis prompt modifier with angle focus

**Cost:** Lowest (synthesis-only, no extraction)

### Mode 4: `custom`

**Goal:** User-defined iteration via prompt

**Pipeline Flow:**
1. **Parse User Prompt** (NEW CODE NEEDED)
   - Detect intent: find sources, re-analyze, re-synthesize, or hybrid
   - Extract parameters (e.g., "find 3 more academic sources")

2. **Dynamic Router** (NEW CODE NEEDED)
   - Route to mode 1/2/3 flow based on intent
   - OR execute custom LLM-driven pipeline

3. **Execution**
   - Delegate to appropriate mode implementation

4. **Storage** (REUSE)
   - Same as mode 1, step 8

**New Code Required:**
- Intent parser (LLM-based)
- Dynamic router
- Custom pipeline executor (fallback)

---

## Shared Infrastructure Needed

### 1. Baseline Data Loader

**Function:** `load_baseline_artifacts(job_id, artifacts_dict) → BaselineData`

```python
@dataclass
class BaselineData:
    doc_0: SourceLedger
    doc_1: JumpStartDirections
    doc_2: SemanticBrief
    semantic_extractions: list[SemanticExtractionResult]
    source_identity_packages: list[SourceIdentityPackage]
```

**Logic:**
- Try storage paths first (`doc_0_path`, etc.)
- Fallback to inline data (`source_ledger`, etc.)
- Parse JSON → Pydantic models
- Reconstruct source identity from Doc 0

### 2. Context Initializer

**Function:** `init_iteration_context(job_id, topic, baseline_data) → PipelineContext`

**Logic:**
- Create fresh `PipelineContext`
- Pre-populate with baseline extractions
- Set up cost tracker
- Configure for iteration mode

### 3. Iteration Storage Manager

**Function:** `store_iteration_results(job_id, iteration_id, ctx) → IterationOutputs`

**Logic:**
- Upload doc_0/1/2 to Supabase Storage under `{job_id}/iterations/{iteration_id}/`
- Build IterationOutputs with paths
- Include inline fallback if storage fails
- Return IterationOutputs object

### 4. Metrics Tracker

**Function:** `track_iteration_metrics(ctx, start_time) → IterationMetrics`

**Logic:**
- Collect LLM call count
- Sum input/output tokens
- Calculate wall time
- Return IterationMetrics object

---

## Implementation Priority

### Phase 1: Core Infrastructure (1-2 days)
- [ ] Baseline data loader
- [ ] Context initializer
- [ ] Iteration storage manager
- [ ] Metrics tracker

### Phase 2: Mode 1 - more_sources (2-3 days)
- [ ] Source discovery integration (Tavily/Perplexity)
- [ ] URL deduplication
- [ ] End-to-end pipeline for new sources
- [ ] Testing with 2-4 new sources

### Phase 3: Mode 3 - different_angle (1-2 days)
- [ ] Angle extraction from user_prompt
- [ ] Synthesis prompt modifier
- [ ] Testing with various angles

### Phase 4: Mode 2 - deeper (2-3 days)
- [ ] Source reconstruction from Doc 0
- [ ] Content re-fetcher with caching
- [ ] Prompt modifier for deeper analysis
- [ ] Testing with re-extraction

### Phase 5: Mode 4 - custom (2-3 days)
- [ ] Intent parser
- [ ] Dynamic router
- [ ] Custom pipeline executor
- [ ] Testing with diverse prompts

---

## Cost Estimates

### Mode 1 (more_sources)
- **Source Discovery:** $0.01-0.02 per query (Tavily/Perplexity)
- **Extraction:** $0.05-0.15 per source (Gemini + transcript)
- **Synthesis:** $0.02-0.05 (Gemini)
- **Total (4 sources):** ~$0.30-0.70 per iteration

### Mode 2 (deeper)
- **Re-extraction:** $0.05-0.15 per source × N sources
- **Synthesis:** $0.02-0.05
- **Total (5 sources):** ~$0.30-0.80 per iteration
- **Alternative (synthesis-only):** ~$0.05-0.10 per iteration

### Mode 3 (different_angle)
- **Synthesis only:** $0.02-0.05 per iteration
- **Total:** ~$0.05 per iteration (cheapest)

### Mode 4 (custom)
- **Intent parsing:** $0.01
- **Execution:** Depends on routed mode
- **Total:** $0.05-0.70+ per iteration

---

## Risk Assessment

### Technical Risks

1. **Baseline Data Availability**
   - **Risk:** Storage paths broken, inline data incomplete
   - **Mitigation:** Dual-path loading (storage → inline fallback)

2. **Context State Pollution**
   - **Risk:** Baseline extractions mixed with new extractions incorrectly
   - **Mitigation:** Clear separation in context (baseline vs new lists)

3. **Storage Upload Failures**
   - **Risk:** Iteration docs fail to upload
   - **Mitigation:** Inline fallback in IterationOutputs

4. **Concurrent Iterations**
   - **Risk:** Two iterations triggered simultaneously
   - **Mitigation:** Already handled (unique constraint on iteration_status)

### Data Quality Risks

1. **Source Discovery Quality**
   - **Risk:** New sources low-quality or duplicate baseline
   - **Mitigation:** Quality gate filtering, URL canonicalization

2. **Re-extraction Consistency**
   - **Risk:** Deeper mode produces inconsistent extractions
   - **Mitigation:** Validation stage, confidence ceilings enforced

3. **Angle Drift**
   - **Risk:** Different_angle loses original topic focus
   - **Mitigation:** Scope lock in synthesis prompt

---

## Recommended Implementation Approach

### Start with Mode 3 (different_angle)

**Rationale:**
1. **Simplest:** Reuses baseline extractions, synthesis-only
2. **Lowest cost:** ~$0.05 per iteration
3. **Fastest to implement:** 1-2 days
4. **High value:** Users can explore angles without re-extraction
5. **Validates infrastructure:** Tests baseline loader, storage manager, metrics

### Then Mode 1 (more_sources)

**Rationale:**
1. **Highest user value:** Expands research coverage
2. **Tests full pipeline:** Source discovery → extraction → synthesis
3. **Builds on Mode 3:** Reuses synthesis logic

### Then Mode 2 (deeper) or Mode 4 (custom)

**Rationale:**
1. Mode 2 requires content re-fetcher (more complex)
2. Mode 4 requires intent parser (LLM-based, variable)
3. Both build on Mode 1/3 infrastructure

---

## Unresolved Questions

1. **Source Discovery API:** Tavily vs Perplexity vs Exa for more_sources?
2. **Caching Strategy:** Where to cache original transcripts/content for deeper mode?
3. **Prompt Versioning:** How to track prompt modifications across iterations?
4. **Iteration Limits:** Max iterations per job (billing concern)?
5. **Baseline Invalidation:** When baseline changes (addendum), how to handle queued iterations?
6. **UI Polling:** How often should frontend poll for iteration completion?
7. **Storage Quota:** Iteration docs consume storage - retention policy?

---

## Code Locations Reference

| Component | File | Line Range |
|-----------|------|------------|
| Data Models | `backend/models/job_record.py` | 12-73, 113 |
| API Endpoint | `backend/app/routes/jobs_routes.py` | 1406-1612 |
| Worker Task | `backend/worker.py` | 1679-1807 |
| Placeholder Block | `backend/worker.py` | 1762-1774 |
| Source Identity | `backend/pipeline/stages/source_identity.py` | 0-100 |
| Extraction Stage | `backend/pipeline/stages/semantic_extraction.py` | 416-940 |
| Synthesis Stage | `backend/pipeline/stages/semantic_synthesis.py` | 253-360 |
| Document Assembly | `backend/pipeline/stages/document_assembly.py` | 50-355 |
| Context Definition | `backend/pipeline/context.py` | 12-151 |
| Completion Stage | `backend/pipeline/stages/initialization.py` | 23-174 |

---

## Next Steps

1. **Get approval** on implementation order (Mode 3 → 1 → 2/4)
2. **Implement shared infrastructure** (baseline loader, storage manager)
3. **Build Mode 3** (different_angle) as proof-of-concept
4. **Test** with real completed jobs
5. **Iterate** based on findings
6. **Expand** to Mode 1, then Mode 2/4

---

**End of Report**
