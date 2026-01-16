# CLAUDE.md — Research Agent

**Last Updated:** 2026-01-15
**Version:** 2.1 (Phase 2 Complete)

---

## CRITICAL: READ FIRST EVERY SESSION

1. **Read `PROGRESS.md`** — Know where we are
2. **Run `/phase-status`** — Confirm current task
3. **Do NOT skip phases** — Sequential execution only
4. **Checkpoint after each task** — Run `/checkpoint`
5. **Do NOT optimize without approval** — Build what's specified

---

## SESSION START CHECKLIST

Every session, you must:

```
[ ] Read PROGRESS.md
[ ] Identify current phase and task
[ ] Check for blockers
[ ] State what you will do this session
[ ] Get approval before starting code changes
```

## SESSION END CHECKLIST

Every session, you must:

```
[ ] Run /checkpoint
[ ] Update PROGRESS.md with completed tasks
[ ] List all files modified
[ ] Note any blockers discovered
[ ] Commit with message: "Phase X.Y: [description]"
[ ] State what next session should do
```

---

## PROJECT OVERVIEW

### What This System Does

Research Agent analyzes video and text sources to produce structured research documents for YouTube documentary creators.

**Core Value:**
- Takes YouTube videos, articles, text, screenshots as input
- Extracts structured information with provenance tracking
- Every claim traces back to source with timestamp/quote
- Prevents hallucination through validation and confidence ceilings

### Current State (2026-01-15)

- **Phase 2:** ✅ COMPLETE — Semantic pipeline orchestration + extended inputs
- **Semantic Pipeline:** Fully wired (5 stages in worker.py)
- **Extended Inputs:** Text + Screenshot endpoints implemented
- **Next:** Phase 3 — Add Analysis Modes OR E2E testing

### Key Documents

| Document | Location | Purpose |
|----------|----------|---------|
| RASS.md | docs/authoritative/spec/ | System specification |
| INDEX.md | docs/authoritative/ | Repo constitution |
| PROGRESS.md | Project root | Current implementation status |
| DECISIONS.md | Project root | Architectural decisions |
| IMPLEMENTATION_PLAN.md | Project root | Phase-by-phase build plan |
| SPEC_MANIFEST.md | Project root | Maps specs to phases |
| operational-reference.md | docs/ | Commands, costs, stack |
| Job_State_Machine.md | Project root | Job lifecycle, status transitions |
| API_Endpoint_Spec.md | Project root | REST API contract |
| Celery_Task_Flow.md | Project root | Task orchestration, retry logic |

---

## ARCHITECTURE (DO NOT CHANGE WITHOUT APPROVAL)

### Pipeline Flow

```
SOURCE IDENTITY → EXTRACTION → VALIDATION → SYNTHESIS → ASSEMBLY
       ↑              ↑             ↑
  (pre-LLM)     (per source)  (per source)
```

### Critical Rules

1. **Source Isolation:** Each source extracted in SEPARATE LLM call. Sources never see each other during extraction.

2. **Pre-LLM Identity Resolution:** Source metadata resolved BEFORE any LLM call. Model cannot guess or infer identity.

3. **Confidence Ceilings:** Enforced per analysis mode:
   - `transcript_grounded`: HIGH
   - `caption_grounded`: MEDIUM
   - `video_only`: LOW (NO quotes allowed)
   - `text_provided`: MEDIUM
   - `ocr_extracted`: MEDIUM
   - `article_fetched`: HIGH

4. **Provenance:** Every key point, claim, quote must reference source_id. Broken chain = validation failure.

5. **Output Documents:**
   - Doc 0: Source Ledger (what was analyzed)
   - Doc 1: Jump-Start Directions (where to go next)
   - Doc 2: Semantic Brief (what sources reveal)
   - Doc 3: Producer Packet (creative interpretation, optional)

### LLM Configuration

| Stage | Model | Temperature | Format |
|-------|-------|-------------|--------|
| Extraction | gemini-2.5-pro | 0.1 | JSON (schema enforced) |
| Synthesis | gemini-2.5-pro | 0.2 | JSON (schema enforced) |
| Booster | gemini-2.5-pro | 0.4 | JSON (schema enforced) |
| Producer | gemini-2.5-pro | 0.3-0.5 | JSON (schema enforced) |

---

## PROMPT REQUIREMENTS

All LLM prompts MUST include these 5 components:

### 1. Source Identity Lock

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

### 2. Confidence Ceiling Declaration

```
CONFIDENCE CEILING: {ceiling}
Your maximum allowed confidence is: {ceiling}
Any output with higher confidence will be rejected.
```

### 3. Empty Output Permission

```
EMPTY OUTPUT PERMISSION
It is acceptable to return empty arrays if:
- No clear themes emerge
- No tensions exist
- No relevant content found
DO NOT invent content to fill arrays.
```

### 4. Layered Extraction (for extraction prompts)

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

### 5. Output Schema

Always specify exact JSON structure with Pydantic model reference.

---

## FILE LOCATIONS

```
backend/
├── app/                      # FastAPI routes
│   ├── main.py              # Entry point
│   └── routes/              # API endpoints
├── models/                   # Pydantic models
│   ├── semantic_units.py    # Extraction models
│   └── document_outputs.py  # Doc 0/1/2/3 models
├── pipeline/                 # Pipeline implementation
│   ├── stages/              # Stage implementations
│   ├── prompts/             # LLM prompts
│   │   └── modes/           # Mode-specific prompts
│   ├── validation.py        # Validation logic
│   └── context.py           # Pipeline context
├── integrations/            # External API clients
├── state/                   # Job persistence
└── worker.py               # Celery tasks

docs/
├── authoritative/           # Canonical specs
│   ├── INDEX.md            # Repo constitution
│   ├── spec/               # Specifications
│   │   └── RASS.md         # System spec
│   ├── prompts/            # Prompt contracts
│   └── examples/           # Canonical examples
└── operational-reference.md # Commands, costs, stack

.claude/
├── rules/                   # Project rules
├── commands/               # Slash commands
└── workflows/              # Session workflows
```

---

## IMPLEMENTATION PHASES

See `IMPLEMENTATION_PLAN.md` for full details.
See `SPEC_MANIFEST.md` for which specs apply to which phase.

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Commit & Stabilize | Pending |
| 0.5 | Review Existing Code | Pending |
| 1 | Fix Blocking Issues | Pending |
| 2 | Wire Semantic Pipeline | Pending |
| 3 | Add Analysis Modes | Pending |
| 4 | Add Validation | Pending |
| 5 | Multi-Source Support | Pending |
| 6 | Evolving Jobs | Pending |
| 7 | Booster Pipeline | Pending |
| 8 | Producer Packet | Pending |
| 9 | Tests | Pending |
| 10 | Documentation | Pending |

**Current Phase:** See PROGRESS.md

---

## CODE STANDARDS

### Type Hints Required
```python
def extract_source(ctx: PipelineContext, source_id: str) -> PipelineContext:
```

### Docstrings Required
```python
def extract_source(ctx: PipelineContext, source_id: str) -> PipelineContext:
    """Extract semantic content from a single source.
    
    Args:
        ctx: Pipeline context with source data
        source_id: ID of source to extract
        
    Returns:
        Updated context with extraction results
    """
```

### Error Handling Required
```python
try:
    result = gemini_client.generate_json(prompt, schema)
except GeminiError as e:
    logger.error(f"Extraction failed for {source_id}: {e}")
    ctx.warnings.append(f"Extraction failed: {e}")
    return ctx  # Continue with degraded output
```

### Commit Message Format
```
Phase X.Y: [description]
```

Examples:
- `Phase 0: Archive unused integration clients`
- `Phase 1.3: Add generate_json() to GeminiClient`
- `Phase 4: Add quote verification validation`

---

## TESTING REQUIREMENTS

### Before Completing Any Phase

1. Run existing tests: `pytest backend/tests/ -v`
2. Verify no regressions
3. Add tests for new code
4. All tests must pass

### Test File Locations

- `backend/tests/test_semantic_models.py` — Model tests
- `backend/tests/test_semantic_pipeline.py` — Pipeline tests
- `backend/tests/test_validation.py` — Validation tests

---

## DEVELOPMENT COMMANDS

### Backend
```bash
source venv/bin/activate
uvicorn backend.app.main:app --reload        # API server
celery -A backend.worker worker --loglevel=INFO  # Worker
pytest backend/tests/ -v                     # Tests
```

### Frontend
```bash
cd frontend && npm run dev                   # Dev server
npm run build && npm run lint               # Build + lint
```

See `docs/operational-reference.md` for full command reference and API costs.

---

## DO NOT

- Skip phases or tasks
- Modify architecture without approval
- Remove working code without archiving
- "Optimize" without asking
- Add features not in the plan
- Ignore validation failures
- Allow confidence to exceed ceiling
- Let sources see each other during extraction
- Guess source identity in LLM prompts

---

## REFERENCE DOCUMENTS

| Document | Purpose |
|----------|---------|
| `PROGRESS.md` | Current status, task tracking |
| `DECISIONS.md` | Architectural decisions |
| `IMPLEMENTATION_PLAN.md` | Full phase details |
| `SPEC_MANIFEST.md` | Maps specs to phases |
| `docs/authoritative/INDEX.md` | Repo constitution |
| `docs/authoritative/spec/RASS.md` | System specification |
| `docs/operational-reference.md` | Commands, costs, stack |

---

## GETTING HELP

If you encounter:

- **Ambiguity:** Ask before assuming
- **Blockers:** Document in PROGRESS.md, ask for guidance
- **Architecture questions:** Check DECISIONS.md first
- **Spec questions:** Check RASS.md and INDEX.md
- **Operational questions:** Check operational-reference.md

Never guess. Always ask.

---

**START EVERY SESSION BY READING PROGRESS.md**
