---
title: "Iteration Feature Implementation"
description: "Implement 4 iteration modes in run_iteration_task with shared utilities"
status: pending
priority: P1
effort: 6h
branch: feature/vision-alignment-v1
tags: [iteration, pipeline, backend]
created: 2026-01-23
---

# Iteration Feature Implementation Plan

## Executive Summary

Implement the iteration loop feature that allows users to refine research results through 4 modes:
- **more_sources**: Add new sources via web search, re-synthesize
- **deeper**: Re-extract existing sources with deeper prompts
- **different_angle**: Re-synthesize with angle-specific focus
- **custom**: Apply user prompt to synthesis

All iterations are APPEND-ONLY: baseline docs are NEVER modified. Each iteration produces new Doc 0/1/2 stored under `artifacts.iterations[]`.

---

## 1. Current State Analysis

### What Exists (Scaffolding Complete)

**Models** (`backend/models/job_record.py`):
- `IterationRequest` - Mode, user_prompt, max_new_sources, angle, constraints
- `IterationInputs` - Baseline doc paths, sources hash, URLs
- `IterationOutputs` - doc_0/1/2 paths and inline data
- `IterationMetrics` - llm_calls, tokens_in/out, wall_time_ms
- `IterationError` - message, stack
- `Iteration` - Full iteration bundle with status lifecycle

**Job Record**:
- `Artifacts.iterations: list[Iteration]` - Append-only iteration array
- Job-level tracking: `iteration_status`, `iteration_id`, `iteration_progress_percent`

**API** (`backend/app/routes/jobs_routes.py`):
- `POST /jobs/{job_id}/iterate` - Creates iteration, queues Celery task

**Worker** (`backend/worker.py`):
- `run_iteration_task` - Skeleton with error handling, but returns "not implemented"

### Reusable Pipeline Stages

| Stage | Location | Reuse Strategy |
|-------|----------|----------------|
| Source Identity | `stages/source_identity.py` | Direct reuse for new sources |
| Semantic Extraction | `stages/semantic_extraction.py` | Reuse with prompt variant parameter |
| Gap Analysis | `stages/gap_analysis.py` | Direct reuse |
| Semantic Synthesis | `stages/semantic_synthesis.py` | Reuse with angle/mode parameter |
| Document Assembly | `stages/document_assembly.py` | Direct reuse |

### Baseline Data Access

- `artifacts.doc_0_path` / `artifacts.doc_1_path` / `artifacts.doc_2_path` - Storage paths
- `artifacts.semantic_extractions` - Per-source extraction results
- `artifacts.source_ledger` / `jump_start` / `semantic_brief` - Inline data (fallback)
- `config_json.topic` - Original research topic

---

## 2. File Structure

```
backend/pipeline/iteration/
    __init__.py                  # Package exports
    baseline_loader.py           # Load baseline docs and extractions
    context_initializer.py       # Initialize IterationContext
    storage_manager.py           # Store iteration outputs to GCS
    metrics_tracker.py           # Track LLM calls, tokens, wall time
    modes/
        __init__.py              # Mode dispatcher
        more_sources.py          # Mode: more_sources
        deeper.py                # Mode: deeper
        different_angle.py       # Mode: different_angle
        custom.py                # Mode: custom
    prompts/
        deeper_extraction.py     # Deeper extraction prompt variant
        angle_synthesis.py       # Angle-specific synthesis prompt
```

---

## 3. Shared Infrastructure

### 3.1 baseline_loader.py

```python
"""Load baseline documents and extractions for iteration."""

from typing import Optional, TypedDict
from backend.integrations.supabase_storage import get_storage_client
from backend.models.semantic_units import SemanticExtractionResult

class BaselineData(TypedDict):
    """Baseline data loaded from completed job."""
    doc_0: dict               # Source Ledger
    doc_1: dict               # Jump-Start
    doc_2: dict               # Semantic Brief
    extractions: list[SemanticExtractionResult]
    topic: str
    source_urls: list[str]    # All URLs from baseline

def load_baseline(job_id: str, artifacts: dict) -> BaselineData:
    """
    Load baseline documents from storage or inline artifacts.

    Priority: Storage paths > Inline data

    Args:
        job_id: Job ID for logging
        artifacts: Job artifacts dict

    Returns:
        BaselineData with all documents and extractions

    Raises:
        ValueError: If required baseline data missing
    """
    ...

def extract_source_urls(doc_0: dict) -> list[str]:
    """Extract all URLs from Source Ledger."""
    ...
```

### 3.2 context_initializer.py

```python
"""Initialize PipelineContext for iteration modes."""

from backend.pipeline.context import PipelineContext
from backend.pipeline.cost_tracker import CostTracker
from .baseline_loader import BaselineData
from .metrics_tracker import MetricsTracker

def create_iteration_context(
    job_id: str,
    iteration_id: str,
    baseline: BaselineData,
    mode: str,
) -> tuple[PipelineContext, MetricsTracker]:
    """
    Create PipelineContext pre-populated with baseline data.

    Args:
        job_id: Parent job ID
        iteration_id: Iteration identifier
        baseline: Loaded baseline data
        mode: Iteration mode

    Returns:
        Tuple of (PipelineContext, MetricsTracker)
    """
    ...
```

### 3.3 storage_manager.py

```python
"""Store iteration outputs to GCS."""

from backend.integrations.supabase_storage import get_storage_client
from backend.models.job_record import IterationOutputs

def store_iteration_docs(
    job_id: str,
    iteration_id: str,
    doc_0: dict,
    doc_1: dict,
    doc_2: dict,
) -> IterationOutputs:
    """
    Store iteration documents to GCS under iterations/{iteration_id}/.

    Storage paths:
    - jobs/{job_id}/iterations/{iteration_id}/doc_0.json
    - jobs/{job_id}/iterations/{iteration_id}/doc_1.json
    - jobs/{job_id}/iterations/{iteration_id}/doc_2.json

    Returns:
        IterationOutputs with storage paths
    """
    ...
```

### 3.4 metrics_tracker.py

```python
"""Track iteration metrics (LLM calls, tokens, wall time)."""

from dataclasses import dataclass, field
from datetime import datetime
from backend.models.job_record import IterationMetrics

@dataclass
class MetricsTracker:
    """Accumulate metrics during iteration execution."""

    start_time: datetime = field(default_factory=datetime.utcnow)
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    def record_llm_call(self, tokens_in: int, tokens_out: int) -> None:
        """Record an LLM call with token counts."""
        ...

    def finalize(self) -> IterationMetrics:
        """Finalize metrics with wall time."""
        ...
```

---

## 4. Mode Implementations

### 4.1 Mode: more_sources

**Purpose**: Find new sources and expand research coverage

**Flow**:
1. Load baseline (topic, existing URLs)
2. Run source discovery (web search) excluding existing URLs
3. Build source identity for new sources
4. Extract semantics from new sources only
5. Merge baseline extractions + new extractions
6. Re-synthesize combined corpus
7. Re-assemble documents
8. Store iteration outputs

**Implementation** (`modes/more_sources.py`):

```python
async def run_more_sources(
    ctx: PipelineContext,
    baseline: BaselineData,
    max_new_sources: int,
    metrics: MetricsTracker,
) -> tuple[dict, dict, dict]:
    """
    Add more sources to research.

    Args:
        ctx: Pipeline context
        baseline: Baseline data
        max_new_sources: Maximum sources to add (1-10)
        metrics: Metrics tracker

    Returns:
        Tuple of (doc_0, doc_1, doc_2) dicts
    """
    # 1. Get existing URLs to exclude
    existing_urls = set(baseline["source_urls"])

    # 2. Run web search for new sources
    from backend.integrations.web_capture import search_web_sources
    new_source_candidates = search_web_sources(
        query=baseline["topic"],
        max_results=max_new_sources * 2,  # Over-fetch for filtering
        exclude_urls=existing_urls,
    )

    # 3. Filter and limit
    new_sources = new_source_candidates[:max_new_sources]

    # 4. Build source identity for new sources
    from backend.pipeline.stages.source_identity import (
        build_source_identity_from_video,
        build_source_identity_from_article,
    )
    # ... build packages for new sources

    # 5. Extract from new sources only
    from backend.pipeline.stages.semantic_extraction import (
        process_single_source,
    )
    new_extractions = []
    for pkg in new_packages:
        result = process_single_source(pkg, index=len(existing_urls) + i)
        if result.extraction_result:
            new_extractions.append(result.extraction_result)
            metrics.record_llm_call(...)

    # 6. Merge extractions (baseline + new)
    ctx.semantic_extractions = baseline["extractions"] + new_extractions

    # 7. Re-run gap analysis and synthesis
    from backend.pipeline.stages.gap_analysis import stage_gap_analysis
    from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis
    stage_gap_analysis(ctx)
    stage_semantic_synthesis(ctx)

    # 8. Re-assemble documents
    from backend.pipeline.stages.document_assembly import stage_document_assembly
    result = stage_document_assembly(ctx)

    return (
        result["source_ledger"].to_dict(),
        result["jump_start"].to_dict(),
        result["semantic_brief"].to_dict(),
    )
```

**Source Discovery Strategy**:
- Use existing `_fetch_url_content` and `_extract_text_with_trafilatura` from `web_capture.py`
- For videos: Use YouTube search API or Gemini to suggest videos
- Filter: Exclude existing URLs via URL normalization
- Quality gate: Apply existing quality gate from `quality_gate.py`

### 4.2 Mode: deeper

**Purpose**: Re-extract existing sources with more granular prompts

**Flow**:
1. Load baseline source identity packages (reconstruct from Doc 0)
2. Re-extract each source with "deeper" prompt variant
3. Run synthesis on deeper extractions
4. Re-assemble documents
5. Store iteration outputs

**Implementation** (`modes/deeper.py`):

```python
async def run_deeper(
    ctx: PipelineContext,
    baseline: BaselineData,
    metrics: MetricsTracker,
) -> tuple[dict, dict, dict]:
    """
    Re-extract sources with deeper analysis prompts.
    """
    # 1. Reconstruct source packages from baseline
    packages = reconstruct_source_packages(baseline["doc_0"])
    ctx.source_identity_packages = packages

    # 2. Extract with deeper prompt
    from backend.pipeline.stages.semantic_extraction import (
        extract_semantic_structure,
    )
    from backend.pipeline.prompts.iteration.deeper_extraction import (
        build_deeper_extraction_prompt,
    )
    from backend.integrations.gemini_client import GeminiClient

    gemini = GeminiClient()
    ctx.semantic_extractions = []

    for pkg in packages:
        prompt = build_deeper_extraction_prompt(
            source_id=pkg.source_id,
            source_content=pkg.content,
            analysis_mode=pkg.analysis_mode.value,
            title=pkg.title,
            existing_key_points=get_kps_for_source(baseline, pkg.source_id),
        )

        result, validation, cost = extract_semantic_structure(
            gemini_client=gemini,
            source_id=pkg.source_id,
            source_content=pkg.content,
            analysis_mode=pkg.analysis_mode,
            title=pkg.title,
            prompt_override=prompt,  # Pass custom prompt
        )
        ctx.semantic_extractions.append(result)
        metrics.record_llm_call(...)

    # 3-5. Gap analysis, synthesis, document assembly
    stage_gap_analysis(ctx)
    stage_semantic_synthesis(ctx)
    result = stage_document_assembly(ctx)

    return (...)
```

**Deeper Extraction Prompt** (`prompts/deeper_extraction.py`):

```python
"""Deeper extraction prompt for iteration mode."""

DEEPER_EXTRACTION_INSTRUCTIONS = """
You are performing a DEEPER extraction pass. You have already extracted the following key points:

{existing_key_points}

Your task is to find ADDITIONAL granular details that were missed in the first pass:
1. Specific examples and case studies mentioned
2. Numerical data, statistics, percentages
3. Named entities (people, organizations, places)
4. Direct quotes with speaker attribution
5. Causal relationships and mechanisms
6. Counterarguments or limitations acknowledged

DO NOT simply repeat the existing key points.
Focus on extracting NEW, more specific information.
"""

def build_deeper_extraction_prompt(
    source_id: str,
    source_content: str,
    analysis_mode: str,
    title: str,
    existing_key_points: list[str],
) -> str:
    """Build prompt for deeper extraction."""
    ...
```

### 4.3 Mode: different_angle

**Purpose**: Re-synthesize with a specific angle or perspective

**Flow**:
1. Load baseline extractions (no re-extraction needed)
2. Re-run synthesis with angle-specific prompt
3. Re-assemble documents
4. Store iteration outputs

**Implementation** (`modes/different_angle.py`):

```python
async def run_different_angle(
    ctx: PipelineContext,
    baseline: BaselineData,
    angle: str,
    metrics: MetricsTracker,
) -> tuple[dict, dict, dict]:
    """
    Re-synthesize with a different angle.

    Args:
        angle: Specific angle (e.g., "economic impact", "historical context")
    """
    # 1. Use baseline extractions directly
    ctx.semantic_extractions = baseline["extractions"]
    ctx.topic = baseline["topic"]

    # 2. Re-run gap analysis (angle may reveal new gaps)
    stage_gap_analysis(ctx)

    # 3. Run angle-specific synthesis
    from backend.pipeline.stages.semantic_synthesis import (
        aggregate_for_synthesis,
        parse_synthesis_response,
    )
    from backend.pipeline.prompts.iteration.angle_synthesis import (
        build_angle_synthesis_prompt,
    )

    key_points, themes, tensions, gaps = aggregate_for_synthesis(ctx)

    prompt = build_angle_synthesis_prompt(
        angle=angle,
        key_points=key_points,
        themes=themes,
        tensions=tensions,
        gaps=gaps,
    )

    gemini = GeminiClient()
    response = gemini.generate_json(
        prompt=prompt,
        system_message=ANGLE_SYNTHESIS_ROLE,
    )
    metrics.record_llm_call(...)

    # Parse and store synthesis result
    synthesis = parse_synthesis_response(response["data"])
    ctx.semantic_core = synthesis["semantic_core"]
    ctx.synthesized_themes = synthesis["themes"]
    # ...

    # 4. Document assembly
    result = stage_document_assembly(ctx)
    return (...)
```

**Angle Synthesis Prompt** (`prompts/angle_synthesis.py`):

```python
"""Angle-specific synthesis prompt."""

ANGLE_SYNTHESIS_ROLE = """You are a research synthesizer focusing on a SPECIFIC ANGLE.
Your task is to re-analyze the research findings through the lens of: {angle}

Filter and prioritize findings that are most relevant to this angle.
Identify tensions and gaps specific to this perspective.
"""

def build_angle_synthesis_prompt(
    angle: str,
    key_points: list[dict],
    themes: list[dict],
    tensions: list[dict],
    gaps: list[dict],
) -> str:
    """Build angle-focused synthesis prompt."""
    ...
```

### 4.4 Mode: custom

**Purpose**: Apply user-provided custom instructions to synthesis

**Flow**:
1. Load baseline extractions
2. Run synthesis with user prompt as additional instruction
3. Re-assemble documents
4. Store iteration outputs

**Implementation** (`modes/custom.py`):

```python
async def run_custom(
    ctx: PipelineContext,
    baseline: BaselineData,
    user_prompt: str,
    metrics: MetricsTracker,
) -> tuple[dict, dict, dict]:
    """
    Apply custom user instructions to synthesis.

    Args:
        user_prompt: User-provided custom instruction
    """
    # 1. Use baseline extractions
    ctx.semantic_extractions = baseline["extractions"]
    ctx.topic = baseline["topic"]

    # 2. Gap analysis
    stage_gap_analysis(ctx)

    # 3. Custom synthesis with user prompt
    from backend.pipeline.prompts.semantic_synthesis_prompt import (
        build_semantic_synthesis_prompt,
        SEMANTIC_SYNTHESIS_ROLE,
    )

    key_points, themes, tensions, gaps = aggregate_for_synthesis(ctx)

    base_prompt = build_semantic_synthesis_prompt(
        scope_lock=f"Research topic: {ctx.topic}",
        key_points=key_points,
        themes=themes,
        tensions=tensions,
        gaps=gaps,
        verification_rate=calculate_verification_rate(ctx),
        source_diversity=len(ctx.semantic_extractions),
    )

    # Append user instructions
    custom_prompt = f"""
{base_prompt}

## CUSTOM USER INSTRUCTIONS

The user has requested the following specific focus:

{user_prompt}

Apply these instructions when synthesizing the research findings.
Prioritize insights that address the user's request.
"""

    gemini = GeminiClient()
    response = gemini.generate_json(
        prompt=custom_prompt,
        system_message=SEMANTIC_SYNTHESIS_ROLE,
    )
    metrics.record_llm_call(...)

    # ... rest of synthesis and document assembly
```

---

## 5. Worker Integration

Update `run_iteration_task` in `backend/worker.py`:

```python
@celery_app.task(
    bind=True,
    name="backend.worker.run_iteration_task",
    max_retries=1,
    soft_time_limit=900,
    time_limit=960,
)
def run_iteration_task(self, job_id: str, iteration_id: str, user_id: str) -> dict:
    """Run iteration on completed job."""
    from datetime import datetime, timezone
    from backend.models.job_record import Artifacts, IterationOutputs, IterationMetrics, IterationError
    from backend.pipeline.iteration import (
        load_baseline,
        create_iteration_context,
        store_iteration_docs,
        MetricsTracker,
    )
    from backend.pipeline.iteration.modes import run_iteration_mode

    job = get_job(job_id)
    # ... validation ...

    # Find iteration in artifacts
    artifacts_dict = job.artifacts.model_dump(exclude_none=True) if job.artifacts else {}
    iterations = artifacts_dict.get("iterations", [])
    iteration_data = next((it for it in iterations if it["iteration_id"] == iteration_id), None)

    if not iteration_data:
        return {"status": "failed", "error": f"Iteration {iteration_id} not found"}

    request = iteration_data["request"]
    mode = request["mode"]

    try:
        # Update status to running
        iteration_data["status"] = "running"
        iteration_data["started_at"] = datetime.now(timezone.utc).isoformat()
        # ... update job ...

        # Load baseline
        baseline = load_baseline(job_id, artifacts_dict)

        # Create context and metrics tracker
        ctx, metrics = create_iteration_context(job_id, iteration_id, baseline, mode)

        # Dispatch to mode handler
        doc_0, doc_1, doc_2 = run_iteration_mode(
            mode=mode,
            ctx=ctx,
            baseline=baseline,
            metrics=metrics,
            user_prompt=request.get("user_prompt", ""),
            max_new_sources=request.get("max_new_sources", 4),
            angle=request.get("angle"),
        )

        # Store iteration outputs
        outputs = store_iteration_docs(job_id, iteration_id, doc_0, doc_1, doc_2)

        # Finalize metrics
        final_metrics = metrics.finalize()

        # Update iteration with success
        iteration_data["status"] = "completed"
        iteration_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        iteration_data["outputs"] = outputs.model_dump()
        iteration_data["metrics"] = final_metrics.model_dump()

        # Update job artifacts
        update_job(
            job_id,
            iteration_status="completed",
            iteration_completed_at=datetime.now(timezone.utc),
            artifacts=Artifacts(**{**artifacts_dict, "iterations": iterations}),
        )

        return {
            "job_id": job_id,
            "iteration_id": iteration_id,
            "status": "completed",
            "outputs": outputs.model_dump(),
            "metrics": final_metrics.model_dump(),
        }

    except Exception as e:
        # ... error handling ...
```

---

## 6. Mode Dispatcher

`modes/__init__.py`:

```python
"""Iteration mode dispatcher."""

from backend.pipeline.context import PipelineContext
from .baseline_loader import BaselineData
from .metrics_tracker import MetricsTracker

def run_iteration_mode(
    mode: str,
    ctx: PipelineContext,
    baseline: BaselineData,
    metrics: MetricsTracker,
    user_prompt: str = "",
    max_new_sources: int = 4,
    angle: str | None = None,
) -> tuple[dict, dict, dict]:
    """
    Dispatch to appropriate mode handler.

    Returns:
        Tuple of (doc_0, doc_1, doc_2) dicts
    """
    if mode == "more_sources":
        from .more_sources import run_more_sources
        return run_more_sources(ctx, baseline, max_new_sources, metrics)

    elif mode == "deeper":
        from .deeper import run_deeper
        return run_deeper(ctx, baseline, metrics)

    elif mode == "different_angle":
        if not angle:
            raise ValueError("different_angle mode requires 'angle' parameter")
        from .different_angle import run_different_angle
        return run_different_angle(ctx, baseline, angle, metrics)

    elif mode == "custom":
        if not user_prompt:
            raise ValueError("custom mode requires 'user_prompt' parameter")
        from .custom import run_custom
        return run_custom(ctx, baseline, user_prompt, metrics)

    else:
        raise ValueError(f"Unknown iteration mode: {mode}")
```

---

## 7. Testing Strategy

### Unit Tests

1. **baseline_loader_test.py**
   - Load from storage paths
   - Fallback to inline data
   - Handle missing data gracefully

2. **metrics_tracker_test.py**
   - Record LLM calls
   - Calculate wall time
   - Finalize to IterationMetrics

3. **storage_manager_test.py**
   - Store docs to correct paths
   - Return IterationOutputs

4. **Mode tests** (per mode)
   - Correct stage sequence
   - Proper metrics tracking
   - Output document structure

### Integration Tests

1. **Full iteration flow**
   - Create job, complete it
   - Trigger iteration
   - Verify new docs created
   - Verify baseline unchanged

2. **Concurrent iterations**
   - Multiple iterations on same job
   - Verify TOCTOU protection works

---

## 8. Implementation Phases

### Phase 1: Infrastructure (2h)

1. Create `backend/pipeline/iteration/` package structure
2. Implement `baseline_loader.py`
3. Implement `context_initializer.py`
4. Implement `storage_manager.py`
5. Implement `metrics_tracker.py`
6. Add unit tests for infrastructure

### Phase 2: Mode Implementations (3h)

1. Implement `different_angle` mode (simplest - no re-extraction)
2. Implement `custom` mode (similar to different_angle)
3. Implement `deeper` mode (requires prompt variant)
4. Implement `more_sources` mode (requires source discovery)
5. Create mode-specific prompts

### Phase 3: Worker Integration (1h)

1. Update `run_iteration_task` with full implementation
2. Wire mode dispatcher
3. Add integration tests
4. End-to-end testing

---

## 9. Dependencies

### External
- Existing GeminiClient for LLM calls
- Existing Supabase Storage for doc storage
- Existing pipeline stages

### Internal (to create)
- `deeper_extraction.py` prompt
- `angle_synthesis.py` prompt
- Web search for `more_sources` mode (may need new integration)

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Baseline data missing | Validate on load, fail fast with clear error |
| LLM costs accumulate | Track via MetricsTracker, expose to user |
| Source discovery fails | Graceful degradation - return fewer sources |
| Long execution time | 15min timeout already set, chunked processing |
| Storage race condition | TOCTOU protection via iteration_claim column |

---

## 11. Success Criteria

1. All 4 modes implemented and tested
2. Baseline documents never modified
3. Iteration outputs stored in GCS under iterations/{iteration_id}/
4. Metrics tracked (llm_calls, tokens, wall_time)
5. Frontend can display iteration versions
6. 90%+ test coverage on new code

---

## 12. Unresolved Questions

1. **Source discovery for more_sources**: Should we use existing web capture or need dedicated search endpoint? Current web_capture fetches specific URLs, doesn't search.

2. **Token counting**: GeminiClient doesn't currently return token counts. Need to add or estimate?

3. **Reconstruction of source packages**: How to reconstruct SourceIdentityPackage from Doc 0? Need to store enough metadata in source_ledger.

4. **Prompt override in extraction**: Current `extract_semantic_structure` doesn't support prompt override. Need to add parameter or refactor?
