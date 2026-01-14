# Research Agent — Targeted Implementation Plan

**Based on:** Project Audit Report (2026-01-13)
**Updated:** 2026-01-13 (Added spec alignment tasks)
**Purpose:** Preserve what works, fix what's broken, build what's missing, archive what's dead

---

# EXECUTIVE SUMMARY

## The Core Finding

**You have code that's 80% built but disconnected from the spec.**

### Working Systems
- **Video Analysis Pipeline:** Gemini 4-pass — working but being replaced
- **External Integrations:** 18 working API clients
- **Authentication:** JWT via Supabase
- **Export System:** 8 formats

### Disconnected Code
- **Semantic Pipeline Stages:** Exist but not exported, not called
- **Semantic Models:** Exist but not integrated
- **Prompts:** Exist but missing required components

### Spec-Code Misalignment
- RASS says 5 stages; code has 4-pass or 11-stage
- RASS says source isolation; code doesn't enforce it
- RASS says verification stage; code doesn't have one
- INDEX.md missing critical rules (source isolation, 6 modes, Doc 3)

---

# DECISION SUMMARY

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Replace vs Augment | **Replace** | Clean architecture, provenance tracking |
| Migration Period | **Remove immediately** | Pipeline can evolve, no legacy burden |
| Phase Order | **As specified** | Logical dependency chain |

---

## Phase 0: Commit & Stabilize (Day 1 Morning)

**Goal:** Get untracked code into version control, archive dead code.

### 0.1 Commit Untracked Semantic Code

```bash
git add backend/models/semantic_units.py
git add backend/models/document_outputs.py
git add backend/pipeline/stages/source_identity.py
git add backend/pipeline/stages/semantic_extraction.py
git add backend/pipeline/stages/document_assembly.py
git add backend/pipeline/transcript_acquisition.py
git add backend/pipeline/prompts/semantic_extraction_prompt.py
git add backend/pipeline/prompts/semantic_synthesis_prompt.py
git add backend/pipeline/semantic_validation.py
git commit -m "Phase 0.1: Commit untracked semantic pipeline code"
```

### 0.2 Archive Dead Code

Create `backend/archive/` and move:
```
backend/integrations/brave_search_client.py → archive/
backend/integrations/claimbuster_client.py → archive/
backend/integrations/gdelt_client.py → archive/
backend/integrations/google_factcheck_client.py → archive/
backend/integrations/semantic_scholar_client.py → archive/
backend/pipeline/_stages_deprecated.py → archive/
backend/legacy/ → archive/
```

```bash
git add backend/archive/
git rm backend/pipeline/_stages_deprecated.py
git rm -r backend/legacy/
git commit -m "Phase 0.2: Archive unused integrations and deprecated code"
```

### 0.3 Create .env.example

```env
# Required
REDIS_URL=redis://localhost:6379
GOOGLE_API_KEY=your-gemini-api-key
SUPADATA_API_KEY=your-supadata-key

# Supabase (required for production)
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Optional integrations
OPENAI_API_KEY=optional
PERPLEXITY_API_KEY=optional
YOUTUBE_API_KEY=optional
EXA_API_KEY=optional
SERPER_API_KEY=optional
```

### 0.4 Deploy Setup Documents

Copy all setup documents to project:
- `CLAUDE.md` → Project root (replace existing)
- `PROGRESS.md` → Project root
- `DECISIONS.md` → Project root
- `IMPLEMENTATION_PLAN.md` → Project root
- `SPEC_MANIFEST.md` → Project root
- `docs/authoritative/INDEX.md` → Replace existing
- `docs/authoritative/spec/RASS.md` → Replace existing
- `docs/operational-reference.md` → New file
- `.claude/rules/` → Replace or add files
- `.claude/commands/` → Replace or add files
- `.claude/workflows/` → Replace or add files

```bash
git add -A
git commit -m "Phase 0.4: Deploy setup documents and updated specs"
```

### 0.5 Verify Project Runs

```bash
pytest backend/tests/ -v
uvicorn backend.app.main:app --reload  # Should start without errors
```

### Checkpoint 0
- [ ] All semantic code committed
- [ ] Dead code archived
- [ ] .env.example created
- [ ] Setup documents deployed
- [ ] INDEX.md and RASS.md updated
- [ ] Project runs without errors
- [ ] Tests pass

---

## Phase 0.5: Review Existing Semantic Code (Day 1 Afternoon)

**Goal:** Verify existing semantic code matches updated specifications before wiring.

### 0.5.1 Review semantic_units.py

Use `/review-file backend/models/semantic_units.py`

Compare against RASS Section 4.3 and Operational Definitions:
- ConfidenceLevel enum
- AnalysisMode enum (now 6 modes)
- Quote, Claim, KeyPoint, Theme, Tension, Gap dataclasses
- ApproximateObservation for video_only
- SemanticExtractionResult with confidence_ceiling

**Expected Outcome:** Mostly correct, may need to add `text_provided`, `ocr_extracted`, `article_fetched` modes.

### 0.5.2 Review document_outputs.py

Use `/review-file backend/models/document_outputs.py`

Compare against RASS Section 3:
- SourceLedger (Doc 0)
- JumpStartDirections (Doc 1)
- SemanticBrief (Doc 2)
- **Missing:** ProducerPacket (Doc 3) — needs to be added

**Expected Outcome:** Doc 0/1/2 mostly correct, need to add Doc 3 model.

### 0.5.3 Review source_identity.py

Use `/review-file backend/pipeline/stages/source_identity.py`

Compare against RASS Section 4.2:
- Mode selection logic for all 6 modes
- Metadata resolution before LLM
- SourceIdentityPackage output

**Expected Outcome:** May need updates for new modes.

### 0.5.4 Review semantic_extraction.py

Use `/review-file backend/pipeline/stages/semantic_extraction.py`

Compare against RASS Section 4.3:
- Source isolation (separate LLM call per source)
- Mode-specific behavior
- Confidence ceiling enforcement
- Calls to GeminiClient

**Expected Outcome:** Needs fixes — calls non-existent generate_json(), may not enforce isolation properly.

### 0.5.5 Review document_assembly.py

Use `/review-file backend/pipeline/stages/document_assembly.py`

Compare against RASS Section 4.6:
- Produces Doc 0, Doc 1, Doc 2
- Correct markdown format
- Handles degraded sources

**Expected Outcome:** Review for completeness.

### 0.5.6 Review Prompt Files

Use `/review-file` on:
- `backend/pipeline/prompts/semantic_extraction_prompt.py`
- `backend/pipeline/prompts/semantic_synthesis_prompt.py`

Check for 5 required components (per INDEX.md):
1. Source Identity Lock Block
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction Instructions
5. Output Schema

**Expected Outcome:** Likely missing some components, need updates.

### 0.5.7 Generate Code Review Report

Output comprehensive report documenting:
- What matches spec
- What needs modification
- What needs rewrite
- Recommended order of changes

### Checkpoint 0.5
- [ ] All files reviewed
- [ ] Code Review Report generated
- [ ] Owner approved modifications
- [ ] Plan adjusted if rewrites needed

---

## Phase 1: Fix Blocking Issues (Day 2)

**Goal:** Make semantic stages callable.

### 1.1 Export Semantic Stages

**File:** `backend/pipeline/stages/__init__.py`

Add:
```python
from .source_identity import stage_source_identity
from .semantic_extraction import stage_semantic_extraction
from .document_assembly import stage_document_assembly

__all__ = [
    # ... existing exports ...
    'stage_source_identity',
    'stage_semantic_extraction', 
    'stage_document_assembly',
]
```

### 1.2 Add JobStatus Enum

**Spec:** `Job_State_Machine.md` Section 7

**File:** `backend/models/job.py` (or appropriate location)

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    ACQUIRING_SOURCES = "acquiring_sources"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    SYNTHESIZING = "synthesizing"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    RUNNING_BOOSTER = "running_booster"
    RUNNING_PRODUCER = "running_producer"
```

### 1.3 Add Missing PipelineContext Fields

**File:** `backend/pipeline/context.py`

Add to PipelineContext dataclass:
```python
# Semantic pipeline fields
source_identity_packages: list = field(default_factory=list)
semantic_extractions: list = field(default_factory=list)
source_ledger: Optional[dict] = None
jump_start: Optional[dict] = None
semantic_brief: Optional[dict] = None

# Analysis mode per source
analysis_modes: dict = field(default_factory=dict)  # source_id → mode
```

### 1.3 Add generate_json() to GeminiClient

**File:** `backend/integrations/gemini_client.py`

Add method:
```python
@with_rate_limit("gemini")
def generate_json(
    self,
    prompt: str,
    system_message: Optional[str] = None,
    model: str = "gemini-2.5-pro",
    temperature: float = 0.1,
) -> dict[str, Any]:
    """Generate structured JSON output with schema enforcement.
    
    Args:
        prompt: The prompt including JSON schema
        system_message: Optional system instruction
        model: Model to use
        temperature: Sampling temperature (low for extraction)
        
    Returns:
        Dict with 'data' (parsed JSON), 'cost', and optionally 'error'
    """
    try:
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_message,
            response_mime_type="application/json",
        )
        
        response = self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        
        data = parse_json_from_llm_response(response.text)
        
        # Estimate cost
        input_tokens = len(prompt.split()) * 1.3
        output_tokens = len(response.text.split()) * 1.3
        cost = self._estimate_cost(model, input_tokens, output_tokens)
        
        return {
            "data": data,
            "cost": cost,
            "model": model,
        }
        
    except GeminiParseError as e:
        logger.error(f"JSON parse failed: {e}")
        return {
            "data": {},
            "cost": 0,
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Gemini generate_json failed: {e}")
        return {
            "data": {},
            "cost": 0,
            "error": sanitize_error_message(e),
        }
```

### 1.4 Add 3-Doc Fields to Artifacts Model

**File:** `backend/models/job_record.py`

Update Artifacts class:
```python
class Artifacts(BaseModel):
    # ... existing fields ...
    
    # Semantic pipeline outputs (Doc 0/1/2/3)
    source_ledger: Optional[dict[str, Any]] = Field(
        None, description="Doc 0: Source Ledger"
    )
    jump_start: Optional[dict[str, Any]] = Field(
        None, description="Doc 1: Jump-Start Directions"
    )
    semantic_brief: Optional[dict[str, Any]] = Field(
        None, description="Doc 2: Semantic Research Brief"
    )
    producer_packet_v2: Optional[dict[str, Any]] = Field(
        None, description="Doc 3: Producer Packet (optional)"
    )
```

### 1.5 Export New Models

**File:** `backend/models/__init__.py`

Add:
```python
from .semantic_units import (
    ConfidenceLevel,
    AnalysisMode,
    Quote,
    Claim,
    KeyPoint,
    Theme,
    Tension,
    Gap,
    ApproximateObservation,
    SpeculativeObservation,
    SemanticExtractionResult,
)
from .document_outputs import (
    SourceStatus,
    TriageLevel,
    TranscriptProvenance,
    SourceEntry,
    SourceLedger,
    ResearchDirection,
    VerificationItem,
    JumpStartDirections,
    ConfidenceAssessment,
    SemanticBrief,
)
```

### 1.6 Add Missing Analysis Modes

**File:** `backend/models/semantic_units.py`

Update AnalysisMode enum:
```python
class AnalysisMode(str, Enum):
    """How the source was analyzed based on type and content availability."""
    TRANSCRIPT_GROUNDED = "transcript_grounded"  # YouTube with Supadata/Whisper
    CAPTION_GROUNDED = "caption_grounded"        # YouTube with captions only
    VIDEO_ONLY = "video_only"                    # YouTube, no text
    TEXT_PROVIDED = "text_provided"              # User-pasted content
    OCR_EXTRACTED = "ocr_extracted"              # Screenshot
    ARTICLE_FETCHED = "article_fetched"          # Article URL
```

### 1.7 Verify All Imports Resolve

```bash
python -c "from backend.pipeline.stages import stage_semantic_extraction"
python -c "from backend.models import SemanticExtractionResult"
python -c "from backend.integrations.gemini_client import GeminiClient; gc = GeminiClient()"
```

### Checkpoint 1
- [ ] `from backend.pipeline.stages import stage_semantic_extraction` works
- [ ] PipelineContext has new fields
- [ ] GeminiClient.generate_json() exists and works
- [ ] Artifacts model has 3-doc fields
- [ ] AnalysisMode has all 6 modes
- [ ] All imports resolve
- [ ] Tests pass

---

## Phase 2: Wire Semantic Pipeline to Video Analysis (Day 3)

**Goal:** Replace 4-pass with semantic stages for video jobs.

**Specs:**
- `Celery_Task_Flow.md` — Task definitions, signatures, orchestration
- `Job_State_Machine.md` — Status transitions during pipeline execution

### 2.1 Create Semantic Video Pipeline Task

**File:** `backend/worker.py`

Add new task:
```python
@celery.task(bind=True, max_retries=3)
def run_semantic_video_job(self, job_id: str, video_url: str, user_id: str):
    """Video analysis using semantic pipeline."""
    
    from backend.pipeline.stages import (
        stage_source_identity,
        stage_semantic_extraction,
        stage_document_assembly,
    )
    from backend.pipeline.validation import validate_extraction_stage
    from backend.pipeline.synthesis import stage_synthesis
    
    # Initialize context
    ctx = PipelineContext(
        job_id=job_id,
        user_id=user_id,
        topic=f"Video analysis: {video_url}",
    )
    ctx.sources = [video_url]
    
    try:
        update_job(job_id, status="running", stage="source_identity")
        
        # Stage 1: Source Identity (per source, pre-LLM)
        for source_url in ctx.sources:
            ctx = stage_source_identity(ctx, source_url)
        
        update_job(job_id, stage="semantic_extraction", progress_percent=20)
        
        # Stage 2: Semantic Extraction (per source, isolated)
        for package in ctx.source_identity_packages:
            ctx = stage_semantic_extraction(ctx, package)
        
        update_job(job_id, stage="validation", progress_percent=40)
        
        # Stage 3: Validation (per extraction)
        for extraction in ctx.semantic_extractions:
            ctx = validate_extraction_stage(ctx, extraction)
        
        update_job(job_id, stage="synthesis", progress_percent=60)
        
        # Stage 4: Synthesis (cross-source)
        ctx = stage_synthesis(ctx)
        
        update_job(job_id, stage="assembly", progress_percent=80)
        
        # Stage 5: Document Assembly
        ctx = stage_document_assembly(ctx)
        
        # Store results
        update_job(
            job_id,
            status="completed",
            stage="complete",
            progress_percent=100,
            artifacts={
                'source_ledger': ctx.source_ledger,
                'jump_start': ctx.jump_start,
                'semantic_brief': ctx.semantic_brief,
            },
            warnings=ctx.warnings,
        )
        
        return {'status': 'complete', 'job_id': job_id}
        
    except Exception as e:
        logger.error(f"Semantic pipeline failed for {job_id}: {e}")
        update_job(
            job_id,
            status="failed",
            error=str(e),
            warnings=ctx.warnings,
        )
        raise
```

### 2.2 Remove Old Pipeline Task

**File:** `backend/worker.py`

Add deprecation notice to `run_gemini_video_job`:
```python
@celery.task(bind=True, max_retries=3)
def run_gemini_video_job(self, job_id: str, video_url: str, user_id: str):
    """
    DEPRECATED: Use run_semantic_video_job instead.
    This task is being removed.
    """
    # Redirect to new pipeline
    return run_semantic_video_job(job_id, video_url, user_id)
```

### 2.3 Update API Route

**File:** `backend/app/routes/jobs_routes.py`

Modify `create_video_analysis_job`:
```python
@router.post("/jobs/video-analysis")
async def create_video_analysis_job(
    request: VideoAnalysisRequest,
    user: AuthUser = Depends(get_current_user),
):
    """Create a video analysis job using semantic pipeline."""
    job_id = str(uuid.uuid4())
    
    # Create job record
    create_job(
        job_id=job_id,
        user_id=user.id,
        pipeline="semantic",
        status="pending",
    )
    
    # Queue semantic pipeline task
    run_semantic_video_job.delay(job_id, request.video_url, user.id)
    
    return {"job_id": job_id, "status": "pending"}
```

### 2.4 Test End-to-End

```bash
# Start worker
celery -A backend.worker worker --loglevel=INFO

# Start API
uvicorn backend.app.main:app --reload

# Create test job
curl -X POST http://localhost:8000/jobs/video-analysis \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://youtube.com/watch?v=TEST"}'
```

### Checkpoint 2
- [ ] New task processes video
- [ ] Produces Doc 0/1/2
- [ ] Old task redirects to new
- [ ] API works
- [ ] Tests pass

---

## Phase 3: Add Analysis Modes (Day 4)

**Goal:** Mode-specific extraction based on source type and content availability.

### 3.1 Create Mode Selector

**File:** `backend/pipeline/mode_selector.py`

```python
from backend.models.semantic_units import AnalysisMode, ConfidenceLevel

CONFIDENCE_CEILINGS = {
    AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,
    AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,
    AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,
    AnalysisMode.TEXT_PROVIDED: ConfidenceLevel.MEDIUM,
    AnalysisMode.OCR_EXTRACTED: ConfidenceLevel.MEDIUM,
    AnalysisMode.ARTICLE_FETCHED: ConfidenceLevel.HIGH,
}

QUOTES_ALLOWED = {
    AnalysisMode.TRANSCRIPT_GROUNDED: True,
    AnalysisMode.CAPTION_GROUNDED: True,
    AnalysisMode.VIDEO_ONLY: False,
    AnalysisMode.TEXT_PROVIDED: False,
    AnalysisMode.OCR_EXTRACTED: False,
    AnalysisMode.ARTICLE_FETCHED: True,
}

def select_analysis_mode(source_type: str, content_available: dict) -> AnalysisMode:
    """Determine analysis mode based on source type and content."""
    
    if source_type == "youtube":
        if content_available.get("supadata_transcript"):
            return AnalysisMode.TRANSCRIPT_GROUNDED
        elif content_available.get("whisper_transcript"):
            return AnalysisMode.TRANSCRIPT_GROUNDED
        elif content_available.get("youtube_captions"):
            return AnalysisMode.CAPTION_GROUNDED
        else:
            return AnalysisMode.VIDEO_ONLY
    
    elif source_type == "article":
        return AnalysisMode.ARTICLE_FETCHED
    
    elif source_type == "text":
        return AnalysisMode.TEXT_PROVIDED
    
    elif source_type == "screenshot":
        return AnalysisMode.OCR_EXTRACTED
    
    raise ValueError(f"Unknown source type: {source_type}")
```

### 3.2 Create Mode-Specific Prompts

**Directory:** `backend/pipeline/prompts/modes/`

Create 6 prompt files, each with all 5 required components:
- `transcript_grounded.py`
- `caption_grounded.py`
- `video_only.py`
- `text_provided.py`
- `ocr_extracted.py`
- `article_fetched.py`

Each prompt includes:
1. Source Identity Lock block
2. Confidence ceiling for that mode
3. Empty output permission
4. Layered extraction instructions
5. Mode-specific output schema (no quotes for certain modes)

### 3.3 Update Semantic Extraction Stage

Modify `stage_semantic_extraction` to use mode-specific prompts and enforce confidence ceiling.

### Checkpoint 3
- [ ] Mode selector correctly identifies source types
- [ ] Each mode has dedicated prompt with all 5 components
- [ ] Confidence ceiling enforced per mode
- [ ] video_only mode produces observations, not quotes
- [ ] Tests pass

---

## Phase 4: Add Validation Stage (Day 5)

**Goal:** Validate extractions before synthesis.

### 4.1 Create Validation Module

**File:** `backend/pipeline/validation.py`

Implement:
- Quote verification (check quotes exist in transcript)
- Confidence ceiling enforcement
- Timestamp validation
- Source ID consistency check

### 4.2 Integrate Validation into Pipeline

Update `run_semantic_video_job` to call validation after each extraction.

### Checkpoint 4
- [ ] Quote verification catches hallucinated quotes
- [ ] Confidence ceiling enforced
- [ ] Validation warnings stored in job
- [ ] Pipeline continues with warnings, stops on errors
- [ ] Tests pass

---

## Phase 5: Multi-Source Support (Day 6)

**Goal:** Handle multiple sources in one job.

### 5.1 Update Job Creation API

Add endpoint for multi-source jobs.

### 5.2 Create Multi-Source Task

Handle array of sources, extract each in isolation, synthesize across all.

### 5.3 Create Synthesis Stage

Identify cross-source themes, tensions, gaps.

### Checkpoint 5
- [ ] Multi-source job creation works
- [ ] Each source extracted in isolation
- [ ] Synthesis identifies cross-source themes
- [ ] Tensions correctly attribute to sources
- [ ] Tests pass

---

## Phase 6: Evolving Jobs (Day 7)

**Goal:** Support adding sources to existing jobs.

### 6.1 Create Addendum Logic
### 6.2 Create Cross-Reference Stage
### 6.3 Add API Endpoint

### Checkpoint 6
- [ ] Sources can be added to completed jobs
- [ ] New sources extracted normally
- [ ] Cross-reference identifies supports/contradicts
- [ ] Addendum appended to existing documents

---

## Phase 7: Booster Pipeline (Day 8)

**Goal:** Optional deep research directions generator.

### 7.1 Create Booster Task (4 stages)
### 7.2 Add Booster Endpoint

### Checkpoint 7
- [ ] Booster endpoint exists
- [ ] 4-stage pipeline runs
- [ ] Results appended to Doc 1
- [ ] Booster only available for completed jobs

---

## Phase 8: Producer Packet Pipeline (Day 9)

**Goal:** Optional creative interpretation document (Doc 3).

### 8.1 Add ProducerPacket Model

**File:** `backend/models/document_outputs.py`

Add Doc 3 model.

### 8.2 Create Producer Packet Task (4 stages)
### 8.3 Add Producer Packet Endpoint
### 8.4 Implement Gating Logic

### Checkpoint 8
- [ ] ProducerPacket model exists
- [ ] Endpoint exists
- [ ] Gating enforced (4+ sources, 1 high-confidence)
- [ ] 4-stage pipeline runs
- [ ] Results stored as Doc 3

---

## Phase 9: Update Tests (Day 10)

**Goal:** Test coverage for new semantic pipeline.

### 9.1 Add Semantic Model Tests
### 9.2 Add Pipeline Stage Tests
### 9.3 Add Integration Tests
### 9.4 Achieve >80% Coverage

### Checkpoint 9
- [ ] Model tests pass
- [ ] Stage tests pass
- [ ] Integration tests pass
- [ ] Coverage >80% for new code

---

## Phase 10: Documentation & Cleanup (Day 11)

**Goal:** Update all documentation.

### 10.1 Final CLAUDE.md Review
### 10.2 Update Architecture Docs
### 10.3 Remove Deprecated Code

### Checkpoint 10
- [ ] All docs updated
- [ ] No outdated references
- [ ] Deprecated code removed

---

# SUMMARY

## Implementation Order

| Phase | Focus | Duration |
|-------|-------|----------|
| 0 | Commit & Stabilize | 0.5 day |
| 0.5 | Review Existing Code | 0.5 day |
| 1 | Fix Blocking Issues | 1 day |
| 2 | Wire Semantic Pipeline | 1 day |
| 3 | Add Analysis Modes | 1 day |
| 4 | Add Validation | 1 day |
| 5 | Add Multi-Source | 1 day |
| 6 | Add Evolving Jobs | 1 day |
| 7 | Add Booster | 1 day |
| 8 | Add Producer Packet | 1 day |
| 9 | Update Tests | 1 day |
| 10 | Documentation | 0.5 day |

**Total: ~11 days**

## What's Preserved
- All working integrations (18 clients)
- Authentication system
- Export formats
- API structure
- Database schema (extended, not replaced)
- State management
- 142 existing tests

## What's Fixed
- Semantic stages now exported and connected
- PipelineContext has required fields
- GeminiClient has generate_json()
- Artifacts model has Doc 0/1/2/3 fields
- INDEX.md has source isolation, 6 modes, Doc 3
- RASS.md has prompt requirements, validation rules

## What's Built
- Mode-specific extraction (6 modes)
- Validation stage with quote verification
- Multi-source support
- Evolving jobs with addendum
- Deep Research Booster (4 stages)
- Producer Packet (4 stages)

## What's Archived
- 5 unused integration clients
- Deprecated stage implementations
- Legacy extraction code

---

**END OF IMPLEMENTATION PLAN**
