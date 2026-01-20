# Research Agent — Implementation Mega Prompt

**For: Claude Code**
**From: Project Owner**
**Date: 2026-01-13**

---

# CRITICAL INSTRUCTIONS

## How to Work

1. **DO NOT START CODING IMMEDIATELY.** Read this entire document first.

2. **PLAN BEFORE BUILDING.** For each phase, output a PLAN REPORT before writing any code. Wait for my approval before proceeding.

3. **CHECKPOINT AFTER EACH PHASE.** After completing each phase, output a COMPLETION REPORT summarizing what was built, what files were created/modified, and what can be tested.

4. **ASK QUESTIONS if anything is ambiguous.** Do not guess. Do not assume. Ask me.

5. **PRESERVE DECISIONS.** The architectural decisions in this document are final unless I explicitly tell you to change them. Do not optimize, refactor, or "improve" without asking.

6. **ONE PHASE AT A TIME.** Complete Phase 1, report, get approval. Then Phase 2. Do not skip ahead.

---

# ORCHESTRATION SPECIFICATIONS

For job lifecycle, API contract, and task orchestration, refer to:
- `Job_State_Machine.md` — 11 job statuses, transition rules, failure handling
- `API_Endpoint_Spec.md` — 22 REST endpoints, request/response shapes
- `Celery_Task_Flow.md` — 9 Celery tasks, retry logic, queue configuration

These specs are authoritative for orchestration behavior.

---

# PROJECT OVERVIEW

## What We're Building

A **Research Agent** that analyzes video and text sources to produce structured research documents for YouTube documentary creators.

**Core Value Proposition:** 
- Takes YouTube videos, articles, text, screenshots as input
- Extracts structured information with provenance tracking
- Produces research documents that trace every claim back to source
- Prevents hallucination through grounding, validation, and confidence ceilings

## User Workflow

```
User submits sources (URLs, text, screenshots)
           ↓
System ingests and extracts each source (isolated)
           ↓
System synthesizes across sources
           ↓
System outputs Doc 0, Doc 1, Doc 2
           ↓
User optionally adds more sources (evolving job)
           ↓
User optionally triggers Booster (research directions)
           ↓
User optionally triggers Producer Packet (creative planning)
```

---

# TECHNICAL STACK

## Required Technologies

| Component | Technology | Version | Why |
|-----------|------------|---------|-----|
| **Backend Framework** | FastAPI | 0.100+ | Async API, Pydantic integration |
| **Task Queue** | Celery | 5.3+ | Background job processing |
| **Message Broker** | Redis | 7.0+ | Celery broker + result backend |
| **Database** | Supabase (PostgreSQL) | N/A | Managed, realtime capabilities |
| **LLM** | Google Gemini 2.5 Pro | API | Primary extraction/synthesis model |
| **Transcript Service** | Supadata | API | YouTube transcript extraction |
| **Python** | 3.11+ | N/A | Required for modern type hints |

## Key Dependencies

```
fastapi>=0.100.0
celery[redis]>=5.3.0
redis>=5.0.0
pydantic>=2.0.0
supabase>=2.0.0
google-generativeai>=0.3.0
httpx>=0.25.0
python-multipart>=0.0.6
python-dotenv>=1.0.0
```

---

# ARCHITECTURE DECISIONS (FINAL)

## Pipeline Stages

```
ACQUIRING_SOURCES → EXTRACTION → VALIDATION → SYNTHESIS → ASSEMBLY
                         ↑             ↑
                  (per source)   (per source)
```

### Acquiring Sources (per Job_State_Machine.md)
- Detects source type (YouTube, article, text, screenshot)
- Fetches metadata and content
- Assigns source_id (SRC_1, SRC_2, etc.)
- Determines analysis mode
- Records TranscriptProvenance

### Extraction (Per Source, Isolated)
- Each source extracted in SEPARATE LLM call
- Sources never see each other during extraction
- Mode-specific prompts and schemas
- Layered extraction: Facts → Patterns → Implications

### Validation (Per Source)
- Schema validation (Pydantic)
- Source ID consistency
- Confidence ceiling enforcement
- Quote verification (string matching for transcript_grounded)
- Timestamp sanity checks
- Retry once on failure, then degrade gracefully

### Synthesis (Cross-Source)
- Combines all validated extractions
- Identifies themes across sources
- Surfaces tensions/contradictions
- Identifies gaps
- Single LLM call with all extractions as input

### Assembly (No LLM)
- Code-driven document generation
- Populates markdown templates with synthesis output
- Produces Doc 0, Doc 1, Doc 2

---

## Analysis Modes

| Mode | When Used | Confidence Ceiling | Quotes Allowed |
|------|-----------|-------------------|----------------|
| `transcript_grounded` | YouTube with transcript | HIGH | Yes (verbatim) |
| `caption_grounded` | YouTube with captions only | MEDIUM | Yes (approximate) |
| `video_only` | YouTube, no text available | LOW | No |
| `text_provided` | User-pasted content | MEDIUM | No |
| `ocr_extracted` | Screenshot input | MEDIUM | No |
| `article_fetched` | Article URL | HIGH | Yes |

---

## Output Documents

### Doc 0 — Source Ledger
What was analyzed. Metadata, provenance, analysis mode for each source.

### Doc 1 — Jump-Start Research Directions
Where to go next. Scope lock, what we know, identified gaps, next steps.

### Doc 2 — Semantic Research Brief
What the sources reveal. Themes, key points with provenance, tensions, observations.

### Doc 3 — Producer Packet (Optional)
Creative interpretation. Story structure, hooks, titles, risk prep. User-triggered.

---

## LLM Configuration

| Stage | Model | Temperature | Response Format |
|-------|-------|-------------|-----------------|
| Extraction | gemini-2.5-pro | 0.1 | JSON (schema enforced) |
| Validation | N/A (code) | N/A | N/A |
| Synthesis | gemini-2.5-pro | 0.2 | JSON (schema enforced) |
| Booster | gemini-2.5-pro | 0.4 | JSON (schema enforced) |
| Producer Packet | gemini-2.5-pro | 0.3-0.5 | JSON (schema enforced) |

All LLM calls use `response_mime_type: "application/json"` and `response_schema`.

---

# IMPLEMENTATION PHASES

## Phase 1: Project Foundation

**Goal:** Project structure, configuration, database schema, all Pydantic models.

**Deliverables:**
1. Project folder structure
2. `requirements.txt` with all dependencies
3. `.env.example` with all environment variables
4. `app/core/config.py` — configuration management
5. `app/models/` — ALL Pydantic models for entire system
6. `database/schema.sql` — Supabase table definitions
7. `docker-compose.yml` — local development setup (Redis, etc.)

**CHECKPOINT:** Output list of all files created, all Pydantic models defined, database schema. I will review before Phase 2.

---

## Phase 2: Database & External Services

**Goal:** Database client, external service wrappers.

**Deliverables:**
1. `app/db/client.py` — Supabase client wrapper
2. `app/db/repositories/` — Data access layer (jobs, sources, extractions)
3. `app/services/gemini.py` — Gemini client wrapper with schema enforcement
4. `app/services/supadata.py` — Supadata client for transcripts
5. `app/services/youtube.py` — YouTube metadata fetcher
6. `app/services/article.py` — Article scraper

**CHECKPOINT:** Output service interfaces (method signatures), database operations available. I will review before Phase 3.

---

## Phase 3: Core Pipeline — Ingestion

**Goal:** Source ingestion that handles all input types.

**Deliverables:**
1. `app/pipeline/ingestion.py` — Main ingestion logic
2. `app/pipeline/source_detector.py` — Detect source type from input
3. `app/pipeline/mode_selector.py` — Determine analysis mode
4. Source type handlers:
   - `app/pipeline/handlers/youtube.py`
   - `app/pipeline/handlers/article.py`
   - `app/pipeline/handlers/text.py`
   - `app/pipeline/handlers/screenshot.py`

**CHECKPOINT:** Output how each source type is handled, what metadata is extracted, how mode is selected. I will review before Phase 4.

---

## Phase 4: Core Pipeline — Extraction

**Goal:** Per-source extraction with mode-specific prompts.

**Deliverables:**
1. `app/pipeline/extraction.py` — Main extraction orchestrator
2. `app/prompts/extraction/` — Prompt templates per mode:
   - `transcript_grounded.txt`
   - `caption_grounded.txt`
   - `video_only.txt`
   - `text_provided.txt`
   - `ocr_extracted.txt`
   - `article_fetched.txt`
3. `app/pipeline/extraction_builder.py` — Builds prompts from templates + source data

**CHECKPOINT:** Output one complete prompt example for `transcript_grounded` mode. Show the full prompt text that would be sent to Gemini. I will review before Phase 5.

---

## Phase 5: Core Pipeline — Validation

**Goal:** Validate extraction outputs, enforce rules.

**Deliverables:**
1. `app/pipeline/validation.py` — Main validation orchestrator
2. `app/pipeline/validators/` — Individual validators:
   - `schema_validator.py` — Pydantic validation
   - `source_id_validator.py` — Check all IDs match
   - `confidence_validator.py` — Enforce ceilings
   - `quote_validator.py` — String match quotes in transcript
   - `timestamp_validator.py` — Check timestamps within duration
3. `app/pipeline/validation_result.py` — Validation result handling

**CHECKPOINT:** Output all validation rules implemented, what happens on failure (retry vs degrade). I will review before Phase 6.

---

## Phase 6: Core Pipeline — Synthesis

**Goal:** Cross-source synthesis to identify themes, tensions, gaps.

**Deliverables:**
1. `app/pipeline/synthesis.py` — Main synthesis logic
2. `app/prompts/synthesis.txt` — Synthesis prompt template
3. `app/pipeline/synthesis_builder.py` — Builds synthesis prompt from extractions

**CHECKPOINT:** Output the synthesis prompt template. Show example input (multiple extractions) and expected output shape. I will review before Phase 7.

---

## Phase 7: Document Assembly

**Goal:** Generate final markdown documents from synthesis output.

**Deliverables:**
1. `app/assembly/assembler.py` — Main assembly orchestrator
2. `app/assembly/templates/` — Markdown templates:
   - `doc0_source_ledger.md`
   - `doc1_jumpstart.md`
   - `doc2_semantic_brief.md`
3. `app/assembly/renderers/` — Per-document renderers

**CHECKPOINT:** Output example Doc 0, Doc 1, Doc 2 from a hypothetical job. I will review before Phase 8.

---

## Phase 8: Celery Tasks & Job Orchestration

**Goal:** Background task execution, job state management.

**Deliverables:**
1. `app/tasks/celery_app.py` — Celery configuration
2. `app/tasks/pipeline_tasks.py` — Task definitions:
   - `task_ingest_source`
   - `task_extract_source`
   - `task_validate_extraction`
   - `task_synthesize_job`
   - `task_assemble_documents`
3. `app/tasks/orchestrator.py` — Job orchestration, task chaining
4. `app/models/job_state.py` — State machine for jobs

**Job States (per Job_State_Machine.md):**
```
pending → acquiring_sources → extracting → validating → synthesizing → assembling
                                                                          ↓
                                                            ┌─────────────┴─────────────┐
                                                            ↓                           ↓
                                                      completed           completed_with_warnings
                                                            ↓                           ↓
                                                   running_booster / running_producer (optional)

On infrastructure failure → failed (terminal)
```

**CHECKPOINT:** Output task signatures, job state transitions, what triggers each transition. I will review before Phase 9.

---

## Phase 9: API Endpoints

**Goal:** FastAPI routes for job management.

**Deliverables:**
1. `app/api/routes/jobs.py` — Job CRUD and triggers
2. `app/api/routes/sources.py` — Source management
3. `app/api/routes/documents.py` — Document retrieval
4. `app/api/schemas/` — Request/response schemas
5. `app/api/dependencies.py` — Shared dependencies
6. `app/main.py` — FastAPI app entry point

**Endpoints:**
```
POST   /jobs                    — Create new job
GET    /jobs/{job_id}           — Get job status and documents
POST   /jobs/{job_id}/sources   — Add sources to existing job
POST   /jobs/{job_id}/booster   — Trigger booster (Phase 11)
POST   /jobs/{job_id}/producer  — Trigger producer packet (Phase 12)
GET    /jobs/{job_id}/documents — Get all documents for job
```

**CHECKPOINT:** Output OpenAPI spec or equivalent for all endpoints. I will review before Phase 10.

---

## Phase 10: Evolving Jobs

**Goal:** Handle adding sources to existing jobs.

**Deliverables:**
1. `app/pipeline/evolving.py` — Evolving job logic
2. `app/pipeline/cross_reference.py` — Cross-reference new sources against existing
3. `app/prompts/cross_reference.txt` — Cross-reference prompt
4. `app/assembly/templates/addendum.md` — Addendum template

**Logic:**
- New sources extracted and validated normally
- Cross-reference pass compares new extractions to existing synthesis
- Addendum appended to existing documents
- Original analysis preserved, clearly marked

**CHECKPOINT:** Output cross-reference prompt, addendum template example. I will review before Phase 11.

---

## Phase 11: Booster Pipeline

**Goal:** Optional deep research directions generator.

**Deliverables:**
1. `app/pipeline/booster/` — Booster pipeline:
   - `stage1_gap_analysis.py`
   - `stage2_directions.py`
   - `stage3_queries.py`
   - `stage4_context_bundle.py`
2. `app/prompts/booster/` — Stage prompts:
   - `gap_analysis.txt`
   - `directions.txt`
   - `queries.txt`
   - `context_bundle.txt`
3. `app/tasks/booster_tasks.py` — Celery tasks for booster

**CHECKPOINT:** Output booster stage prompts, example output from each stage. I will review before Phase 12.

---

## Phase 12: Producer Packet Pipeline

**Goal:** Optional creative interpretation document.

**Deliverables:**
1. `app/pipeline/producer/` — Producer pipeline:
   - `stage1_story_core.py`
   - `stage2_structure.py`
   - `stage3_creative.py`
   - `stage4_risk_context.py`
2. `app/prompts/producer/` — Stage prompts
3. `app/assembly/templates/doc3_producer_packet.md`
4. `app/tasks/producer_tasks.py` — Celery tasks

**Gating:** Producer packet only available if:
- 4+ sources
- At least 1 high-confidence source
- At least 1 theme identified

**CHECKPOINT:** Output producer stage prompts, gating logic, example producer packet. I will review.

---

## Phase 13: Testing & Verification

**Goal:** Test suite for critical paths.

**Deliverables:**
1. `tests/fixtures/` — Test data:
   - Sample transcripts
   - Sample extractions
   - Expected outputs
2. `tests/test_extraction.py` — Extraction tests
3. `tests/test_validation.py` — Validation tests
4. `tests/test_synthesis.py` — Synthesis tests
5. `tests/test_assembly.py` — Assembly tests
6. `tests/mocks/` — Gemini mock responses

**CHECKPOINT:** Output test coverage report, what's tested, what's mocked.

---

# PYDANTIC MODELS (REFERENCE)

Define these in Phase 1. All subsequent phases reference these models.

## Source Models

```python
class SourceType(str, Enum):
    YOUTUBE = "youtube"
    ARTICLE = "article"
    TEXT = "text"
    SCREENSHOT = "screenshot"

class AnalysisMode(str, Enum):
    TRANSCRIPT_GROUNDED = "transcript_grounded"
    CAPTION_GROUNDED = "caption_grounded"
    VIDEO_ONLY = "video_only"
    TEXT_PROVIDED = "text_provided"
    OCR_EXTRACTED = "ocr_extracted"
    ARTICLE_FETCHED = "article_fetched"

class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SourceMetadata(BaseModel):
    source_id: str                           # SRC_1, SRC_2, etc.
    source_type: SourceType
    analysis_mode: AnalysisMode
    confidence_ceiling: ConfidenceLevel
    title: str
    url: Optional[str] = None
    duration_seconds: Optional[int] = None   # For video
    word_count: Optional[int] = None         # For text
    creator: Optional[str] = None
    platform: Optional[str] = None
    provenance_note: Optional[str] = None    # "User-provided", "System-fetched", etc.
    ingested_at: datetime
```

## Extraction Models

```python
class SupportingQuote(BaseModel):
    quote_id: str                            # QT_1, QT_2, etc.
    text: str
    source_id: str
    timestamp: Optional[str] = None          # "14:32" for video
    speaker: Optional[str] = None
    context: Optional[str] = None

class Claim(BaseModel):
    claim_id: str                            # CLM_1, CLM_2, etc.
    statement: str
    source_id: str
    confidence: ConfidenceLevel
    supporting_quotes: List[str] = []        # Quote IDs
    claim_type: Optional[str] = None         # "factual", "opinion", "prediction"

class KeyPoint(BaseModel):
    key_point_id: str                        # KP_1, KP_2, etc.
    statement: str
    source_ids: List[str]                    # Which sources support this
    confidence: ConfidenceLevel
    supporting_claims: List[str] = []        # Claim IDs
    supporting_quotes: List[str] = []        # Quote IDs

class Observation(BaseModel):
    """For video_only and screenshot modes where quotes aren't available."""
    observation_id: str                      # OBS_1, OBS_2, etc.
    description: str
    source_id: str
    timestamp_range: Optional[str] = None    # "12:00-15:00"
    confidence: ConfidenceLevel
    observation_type: str                    # "visual", "behavioral", "contextual"

class ExtractionOutput(BaseModel):
    source_id: str
    analysis_mode: AnalysisMode
    key_points: List[KeyPoint] = []
    claims: List[Claim] = []
    supporting_quotes: List[SupportingQuote] = []
    observations: List[Observation] = []
    entities_mentioned: List[str] = []
    topics: List[str] = []
    extraction_metadata: dict = {}           # Token counts, etc.
```

## Synthesis Models

```python
class Theme(BaseModel):
    theme_id: str                            # THEME_1, THEME_2, etc.
    name: str
    description: str
    related_key_points: List[str]            # KP IDs
    source_ids: List[str]                    # Which sources contribute
    confidence: ConfidenceLevel

class Tension(BaseModel):
    tension_id: str                          # TEN_1, TEN_2, etc.
    description: str
    side_a: str
    side_a_sources: List[str]
    side_b: str
    side_b_sources: List[str]
    status: str                              # "unresolved", "resolved", "unclear"

class Gap(BaseModel):
    gap_id: str                              # GAP_1, GAP_2, etc.
    description: str
    gap_type: str                            # "missing_source", "missing_perspective", etc.
    why_it_matters: str
    potential_sources: List[str] = []

class SynthesisOutput(BaseModel):
    job_id: str
    themes: List[Theme] = []
    tensions: List[Tension] = []
    gaps: List[Gap] = []
    key_points_consolidated: List[KeyPoint] = []
    scope_in: List[str] = []
    scope_out: List[str] = []
    confidence_summary: dict = {}
```

## Job Models

```python
class JobStatus(str, Enum):
    """Job lifecycle states. See Job_State_Machine.md for transition rules."""
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

class Job(BaseModel):
    job_id: str
    status: JobStatus  # Renamed from 'state' for consistency with Job_State_Machine.md
    sources: List[SourceMetadata] = []
    warnings: List[dict] = []  # Degradation tracking per Job_State_Machine.md
    warning_count: int = 0
    extractions: List[ExtractionOutput] = []
    synthesis: Optional[SynthesisOutput] = None
    documents: dict = {}                     # {"doc0": "...", "doc1": "...", "doc2": "..."}
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None
```

## Validation Models

```python
class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"

class ValidationIssue(BaseModel):
    severity: ValidationSeverity
    code: str                                # "QUOTE_NOT_FOUND", "CONFIDENCE_EXCEEDED", etc.
    message: str
    field: Optional[str] = None
    source_id: Optional[str] = None

class ValidationResult(BaseModel):
    valid: bool
    issues: List[ValidationIssue] = []
    corrected_extraction: Optional[ExtractionOutput] = None
```

---

# PROMPT GUIDELINES

All prompts must include:

## 1. Source Identity Lock

```
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  source_id: {source_id}                                  ║
║  title: {title}                                          ║
║  analysis_mode: {mode}                                   ║
║  confidence_ceiling: {ceiling}                           ║
╚══════════════════════════════════════════════════════════╝
```

## 2. Confidence Ceiling Declaration

```
CONFIDENCE CEILING: {ceiling}
Your maximum allowed confidence is: {ceiling}
Any output with higher confidence will be rejected.
```

## 3. Empty Output Permission

```
EMPTY OUTPUT PERMISSION
It is acceptable to return empty arrays if:
- No clear themes emerge
- No tensions exist
- No relevant content found
DO NOT invent content to fill arrays.
```

## 4. Layered Extraction (for extraction prompts)

```
EXTRACTION LAYERS — Process in order.

LAYER 1 — EXPLICIT CONTENT
What does the source explicitly state?
DO NOT interpret. DO NOT infer.

LAYER 2 — PATTERNS
What patterns exist in Layer 1 content?
Every pattern must reference Layer 1 items.

LAYER 3 — STRUCTURAL ELEMENTS
What themes, tensions, gaps emerge?
Must derive from Layer 2 only.
```

## 5. Output Schema

Always specify exact JSON structure expected.

---

# CONSTRAINTS & RULES

## DO

- Use Pydantic `response_schema` for all Gemini calls
- Validate ALL extractions before synthesis
- Log token usage for cost tracking
- Preserve original documents when adding sources (addendum pattern)
- Use explicit type hints everywhere
- Handle errors gracefully with clear messages

## DO NOT

- Let sources see each other during extraction
- Allow confidence to exceed mode ceiling
- Store full transcripts in database (too large)
- Use async for Celery tasks (compatibility issues)
- Assume previous session context exists
- "Improve" or "optimize" architecture without asking

---

# VERIFICATION PROTOCOL

After each phase, output a report in this format:

```
## PHASE {N} COMPLETION REPORT

### Files Created
- path/to/file1.py — Description
- path/to/file2.py — Description

### Files Modified
- path/to/existing.py — What changed

### Key Decisions Made
- Decision 1: Why
- Decision 2: Why

### Models/Schemas Defined
- ModelName: Purpose

### What Can Be Tested
- How to verify this phase works

### Open Questions
- Any ambiguities encountered

### Ready for Phase {N+1}?
Yes/No — If no, what's blocking
```

Wait for my "APPROVED — PROCEED TO PHASE {N+1}" before continuing.

---

# START HERE

Begin with **Phase 1: Project Foundation**.

Output a **PLAN REPORT** first:
- What files you will create
- What models you will define
- Any questions before starting

DO NOT write code until I approve the plan.

---

**END OF MEGA PROMPT**
