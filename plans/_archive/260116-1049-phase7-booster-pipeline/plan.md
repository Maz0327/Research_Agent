# Phase 7 Implementation Plan: Deep Research Booster

**Date:** 2026-01-16
**Phase:** 7
**Branch:** feature/vision-alignment-v1
**Prerequisite:** Phase 6 Complete (Evolving Jobs)
**Spec Reference:** `docs/authoritative/spec/GAPS_AND_BOOSTER_SPEC.md` Part 2

---

## Executive Summary

Phase 7 implements the **Deep Research Booster** — an optional, user-triggered component that expands Doc 1 (Jump-Start Research Directions) with additional research directions, search queries, and perspectives.

**Critical Principle:** The booster produces **DIRECTIONS**, not **FACTS**. It tells you WHERE to look, not WHAT you'll find.

**Key Characteristics:**
- User-triggered (not automatic)
- Runs AFTER initial job completion
- Input: Context Bundle (auto-generated, user provides nothing)
- Output: Appends to Doc 1 as visually distinct "Deep Research Expansion" section
- Failure does NOT affect existing documents

---

## Current State Analysis

### Already Working (Phases 0-6)
- Full semantic pipeline: extract → validate → synthesize → assemble
- Doc 0/1/2 generation with proper structure
- JumpStartDirections model with research_directions, gaps, next_steps
- Evolving jobs with addendum pattern
- Cross-reference stage

### Missing for Phase 7
- ContextBundle model (input to booster)
- BoosterOutput model (structured output)
- Booster prompt with hallucination protection
- Context bundle generator function
- Booster pipeline stage
- API endpoint for triggering booster
- Doc 1 integration for booster expansion section
- Booster Celery task

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     BOOSTER FLOW                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User clicks "Deep Research" on completed job                   │
│                  │                                              │
│                  ▼                                              │
│  ┌──────────────────────────┐                                   │
│  │ POST /jobs/{id}/booster  │                                   │
│  └──────────────────────────┘                                   │
│                  │                                              │
│                  ▼                                              │
│  ┌──────────────────────────┐                                   │
│  │ Generate Context Bundle  │ ← From existing job output       │
│  │ (themes, gaps, tensions) │                                   │
│  └──────────────────────────┘                                   │
│                  │                                              │
│                  ▼                                              │
│  ┌──────────────────────────┐                                   │
│  │ Booster Stage (Gemini)   │ ← Temperature: 0.4-0.5           │
│  │ • Missing perspectives   │                                   │
│  │ • Primary source dirs    │                                   │
│  │ • Search queries         │                                   │
│  │ • Research questions     │                                   │
│  └──────────────────────────┘                                   │
│                  │                                              │
│                  ▼                                              │
│  ┌──────────────────────────┐                                   │
│  │ Validate Booster Output  │ ← Grounding check, entity check  │
│  └──────────────────────────┘                                   │
│                  │                                              │
│                  ▼                                              │
│  ┌──────────────────────────┐                                   │
│  │ Append to Doc 1          │ → "Deep Research Expansion"      │
│  │ (visually distinct)      │                                   │
│  └──────────────────────────┘                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Task Breakdown

### Task 7.1: Create Booster Models

**File:** `backend/models/booster_models.py` (NEW)

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class PrimarySourceType(str, Enum):
    """Types of primary sources to search for."""
    COURT_FILING = "court_filing"
    SEC_FILING = "sec_filing"
    GOVERNMENT_RECORD = "government_record"
    ACADEMIC_PAPER = "academic_paper"
    NEWS_ARTICLE = "news_article"
    PRESS_RELEASE = "press_release"
    SOCIAL_MEDIA_ARCHIVE = "social_media_archive"
    INTERVIEW_TRANSCRIPT = "interview_transcript"
    INTERNAL_DOCUMENT = "internal_document"
    DATASET = "dataset"
    FINANCIAL_REPORT = "financial_report"
    OTHER = "other"

class PlatformSuggestion(str, Enum):
    """Platforms to search."""
    GOOGLE = "google"
    REDDIT = "reddit"
    TWITTER = "twitter"
    NEWS = "news"
    YOUTUBE = "youtube"
    ARCHIVE = "archive"  # Wayback Machine, etc.

@dataclass
class ThemeSummary:
    """Lightweight theme for context bundle."""
    theme_id: str
    label: str
    description: str

@dataclass
class TensionSummary:
    """Lightweight tension for context bundle."""
    tension_id: str
    description: str

@dataclass
class GapSummary:
    """Lightweight gap for context bundle."""
    gap_id: str
    description: str

@dataclass
class ContextBundle:
    """
    Constrained input for Deep Research Booster.
    Auto-generated from job output. User provides nothing.
    """
    # Scope (from Doc 1)
    scope_in: list[str] = field(default_factory=list)
    scope_out: list[str] = field(default_factory=list)

    # Semantic content (from extraction)
    themes: list[ThemeSummary] = field(default_factory=list)
    key_point_summaries: list[str] = field(default_factory=list)  # Statements only
    tensions: list[TensionSummary] = field(default_factory=list)
    gaps: list[GapSummary] = field(default_factory=list)

    # Metadata
    source_count: int = 0
    source_types: list[str] = field(default_factory=list)
    confidence_level: str = "medium"  # Overall job confidence

    # Job reference
    job_id: str = ""
    generated_at: str = ""

@dataclass
class MissingPerspective:
    """A viewpoint or voice not represented in current sources."""
    description: str
    why_it_matters: str
    related_gaps: list[str] = field(default_factory=list)

@dataclass
class PrimarySourceDirection:
    """A type of primary source that might exist and should be sought."""
    source_type: PrimarySourceType
    description: str
    search_suggestion: str
    related_gap: Optional[str] = None

@dataclass
class SearchQuery:
    """A specific search query to find relevant sources."""
    query: str
    purpose: str
    platform_suggestion: PlatformSuggestion
    related_gap: Optional[str] = None
    related_theme: Optional[str] = None

@dataclass
class ResearchQuestion:
    """A question that would advance understanding if answered."""
    question: str
    why_it_matters: str
    related_theme: str

@dataclass
class BoosterOutput:
    """
    Output that augments Doc 1. DIRECTIONS ONLY, no facts.
    """
    missing_perspectives: list[MissingPerspective] = field(default_factory=list)
    primary_source_directions: list[PrimarySourceDirection] = field(default_factory=list)
    suggested_search_queries: list[SearchQuery] = field(default_factory=list)
    research_questions: list[ResearchQuestion] = field(default_factory=list)

    # Metadata
    booster_provider: str = "gemini"
    booster_timestamp: str = ""
    context_bundle_hash: str = ""  # SHA256 for verification
```

---

### Task 7.2: Create Booster Prompt

**File:** `backend/pipeline/prompts/booster_prompt.py` (NEW)

```python
BOOSTER_ROLE = """You are a research direction generator.

Your job is to suggest WHERE to look for information, not to provide information itself.

You will receive a Context Bundle describing completed research: themes, key points, tensions, and gaps.

Your task is to suggest:
1. Missing perspectives that should be sought
2. Types of primary sources that might exist
3. Specific search queries to find relevant sources
4. Research questions that would advance understanding"""

BOOSTER_CONTEXT_LOCK = """
╔══════════════════════════════════════════════════════════════╗
║  BOOSTER CONTEXT LOCK — DIRECTIONS ONLY                      ║
╠══════════════════════════════════════════════════════════════╣
║  Job ID: {job_id}                                            ║
║  Source Count: {source_count}                                ║
║  Confidence: {confidence_level}                              ║
║  Task: Generate research DIRECTIONS, NOT facts               ║
╚══════════════════════════════════════════════════════════════╝

RULE: You suggest WHERE to look. You do NOT provide WHAT will be found.
"""

BOOSTER_PROMPT = """## ABSOLUTE RULES (VIOLATION = INVALID OUTPUT)

1. **NO FACTS**: Do not state anything as true. Do not provide dates, numbers, names, or events not in the Context Bundle.

2. **NO RESOLUTION**: Do not resolve tensions or pick sides in contradictions.

3. **NO NEW ENTITIES**: Do not introduce people, companies, or events not mentioned in the Context Bundle.

4. **DIRECTIONS ONLY**: Every output must be a suggestion of where to look, not what will be found.

5. **GROUNDED**: Every suggestion must connect to a gap_id or theme_id from the Context Bundle.

❌ WRONG: "SEC filings from 2019 show the company had $2M in debt"
✅ RIGHT: "Look for SEC filings to verify financial claims"

❌ WRONG: "The March date is probably correct"
✅ RIGHT: "Search for contemporaneous sources to verify the disputed timeline"

---

## CONTEXT BUNDLE

### Scope
IN: {scope_in}
OUT: {scope_out}

### Themes
{themes}

### Key Point Summaries
{key_points}

### Tensions
{tensions}

### Identified Gaps
{gaps}

### Metadata
- Sources: {source_count}
- Source Types: {source_types}
- Confidence: {confidence_level}

---

## OUTPUT FORMAT (JSON ONLY)

{{
    "missing_perspectives": [
        {{
            "description": "What voice/viewpoint is missing",
            "why_it_matters": "Why this perspective would help",
            "related_gaps": ["GAP_1"]
        }}
    ],
    "primary_source_directions": [
        {{
            "source_type": "court_filing | news_article | social_media_archive | ...",
            "description": "What type of source to look for",
            "search_suggestion": "How to search for it",
            "related_gap": "GAP_1"
        }}
    ],
    "suggested_search_queries": [
        {{
            "query": "Specific search query",
            "purpose": "What this query aims to find",
            "platform_suggestion": "google | reddit | twitter | news | archive",
            "related_gap": "GAP_1 or null",
            "related_theme": "THEME_1 or null"
        }}
    ],
    "research_questions": [
        {{
            "question": "A question to investigate",
            "why_it_matters": "How answering it advances understanding",
            "related_theme": "THEME_1"
        }}
    ]
}}

---

## REMEMBER

You are generating a research TODO list, not conducting research.
"Look for X" is correct. "X shows that Y" is forbidden.

Empty arrays are acceptable if no relevant directions exist.
DO NOT invent directions to fill output.
"""
```

---

### Task 7.3: Create Context Bundle Generator

**File:** `backend/pipeline/booster/context_bundle_generator.py` (NEW)

```python
from datetime import datetime, timezone
import hashlib
import json

from backend.models.booster_models import (
    ContextBundle,
    ThemeSummary,
    TensionSummary,
    GapSummary,
)

def generate_context_bundle(
    job_id: str,
    jump_start: dict,
    semantic_brief: dict,
    extractions: list[dict],
) -> ContextBundle:
    """
    Generate Context Bundle from completed job output.

    Args:
        job_id: Job identifier
        jump_start: Doc 1 data
        semantic_brief: Doc 2 data
        extractions: List of extraction results

    Returns:
        ContextBundle for booster input
    """
    # Extract scope from jump_start
    scope_lock = jump_start.get("scope_lock", {})
    scope_in = scope_lock.get("in", [])
    scope_out = scope_lock.get("out", [])

    # Extract themes from semantic_brief
    themes = []
    for theme_data in semantic_brief.get("themes", []):
        themes.append(ThemeSummary(
            theme_id=theme_data.get("theme_id", ""),
            label=theme_data.get("label", ""),
            description=theme_data.get("description", ""),
        ))

    # Extract key point summaries (statements only)
    key_point_summaries = []
    for kp in semantic_brief.get("key_points", []):
        key_point_summaries.append(kp.get("statement", ""))

    # Extract tensions
    tensions = []
    for tension_data in semantic_brief.get("tensions", []):
        tensions.append(TensionSummary(
            tension_id=tension_data.get("tension_id", ""),
            description=tension_data.get("description", ""),
        ))

    # Extract gaps from jump_start
    gaps = []
    for gap_data in jump_start.get("gaps", []):
        gaps.append(GapSummary(
            gap_id=gap_data.get("gap_id", ""),
            description=gap_data.get("description", ""),
        ))

    # Metadata
    corpus = jump_start.get("current_corpus", {})
    source_count = corpus.get("source_count", len(extractions))
    source_types = corpus.get("perspectives_represented", [])
    confidence = semantic_brief.get("confidence", {}).get("overall", "medium")

    return ContextBundle(
        scope_in=scope_in,
        scope_out=scope_out,
        themes=themes,
        key_point_summaries=key_point_summaries,
        tensions=tensions,
        gaps=gaps,
        source_count=source_count,
        source_types=source_types,
        confidence_level=confidence,
        job_id=job_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

def compute_bundle_hash(bundle: ContextBundle) -> str:
    """Compute SHA256 hash of context bundle for verification."""
    bundle_dict = {
        "job_id": bundle.job_id,
        "scope_in": bundle.scope_in,
        "themes": [t.theme_id for t in bundle.themes],
        "gaps": [g.gap_id for g in bundle.gaps],
        "source_count": bundle.source_count,
    }
    json_str = json.dumps(bundle_dict, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]
```

---

### Task 7.4: Create Booster Stage

**File:** `backend/pipeline/stages/booster_stage.py` (NEW)

```python
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.booster_models import (
    BoosterOutput,
    ContextBundle,
    MissingPerspective,
    PrimarySourceDirection,
    PrimarySourceType,
    PlatformSuggestion,
    ResearchQuestion,
    SearchQuery,
)
from backend.pipeline.booster.context_bundle_generator import compute_bundle_hash
from backend.pipeline.prompts.booster_prompt import (
    BOOSTER_CONTEXT_LOCK,
    BOOSTER_PROMPT,
    BOOSTER_ROLE,
)

def build_booster_prompt(bundle: ContextBundle) -> str:
    """Build complete booster prompt from context bundle."""
    # Format themes
    themes_str = "\n".join([
        f"- {t.theme_id}: {t.label} — {t.description}"
        for t in bundle.themes
    ]) or "(No themes identified)"

    # Format key points
    key_points_str = "\n".join([
        f"- {kp}" for kp in bundle.key_point_summaries[:15]
    ]) or "(No key points)"

    # Format tensions
    tensions_str = "\n".join([
        f"- {t.tension_id}: {t.description}"
        for t in bundle.tensions
    ]) or "(No tensions identified)"

    # Format gaps
    gaps_str = "\n".join([
        f"- {g.gap_id}: {g.description}"
        for g in bundle.gaps
    ]) or "(No gaps identified)"

    context_lock = BOOSTER_CONTEXT_LOCK.format(
        job_id=bundle.job_id,
        source_count=bundle.source_count,
        confidence_level=bundle.confidence_level,
    )

    prompt = context_lock + "\n\n" + BOOSTER_PROMPT.format(
        scope_in=", ".join(bundle.scope_in) or "(Not specified)",
        scope_out=", ".join(bundle.scope_out) or "(Not specified)",
        themes=themes_str,
        key_points=key_points_str,
        tensions=tensions_str,
        gaps=gaps_str,
        source_count=bundle.source_count,
        source_types=", ".join(bundle.source_types) or "(Unknown)",
        confidence_level=bundle.confidence_level,
    )

    return prompt

def parse_booster_response(data: dict[str, Any], bundle: ContextBundle) -> BoosterOutput:
    """Parse Gemini response into BoosterOutput."""
    # Parse missing perspectives
    missing_perspectives = []
    for mp in data.get("missing_perspectives", []):
        missing_perspectives.append(MissingPerspective(
            description=mp.get("description", ""),
            why_it_matters=mp.get("why_it_matters", ""),
            related_gaps=mp.get("related_gaps", []),
        ))

    # Parse primary source directions
    primary_source_directions = []
    for psd in data.get("primary_source_directions", []):
        source_type_str = psd.get("source_type", "other")
        try:
            source_type = PrimarySourceType(source_type_str)
        except ValueError:
            source_type = PrimarySourceType.OTHER

        primary_source_directions.append(PrimarySourceDirection(
            source_type=source_type,
            description=psd.get("description", ""),
            search_suggestion=psd.get("search_suggestion", ""),
            related_gap=psd.get("related_gap"),
        ))

    # Parse search queries
    search_queries = []
    for sq in data.get("suggested_search_queries", []):
        platform_str = sq.get("platform_suggestion", "google")
        try:
            platform = PlatformSuggestion(platform_str)
        except ValueError:
            platform = PlatformSuggestion.GOOGLE

        search_queries.append(SearchQuery(
            query=sq.get("query", ""),
            purpose=sq.get("purpose", ""),
            platform_suggestion=platform,
            related_gap=sq.get("related_gap"),
            related_theme=sq.get("related_theme"),
        ))

    # Parse research questions
    research_questions = []
    for rq in data.get("research_questions", []):
        research_questions.append(ResearchQuestion(
            question=rq.get("question", ""),
            why_it_matters=rq.get("why_it_matters", ""),
            related_theme=rq.get("related_theme", ""),
        ))

    return BoosterOutput(
        missing_perspectives=missing_perspectives,
        primary_source_directions=primary_source_directions,
        suggested_search_queries=search_queries,
        research_questions=research_questions,
        booster_provider="gemini",
        booster_timestamp=datetime.now(timezone.utc).isoformat(),
        context_bundle_hash=compute_bundle_hash(bundle),
    )

def validate_booster_output(output: BoosterOutput, bundle: ContextBundle) -> list[str]:
    """
    Validate booster output for grounding and hallucination.

    Returns list of warnings. Empty = valid.
    """
    warnings = []
    valid_gap_ids = {g.gap_id for g in bundle.gaps}
    valid_theme_ids = {t.theme_id for t in bundle.themes}

    # Check that related_gaps reference valid gap IDs
    for mp in output.missing_perspectives:
        for gap_id in mp.related_gaps:
            if gap_id not in valid_gap_ids:
                warnings.append(f"Invalid gap reference: {gap_id}")

    # Check primary source directions
    for psd in output.primary_source_directions:
        if psd.related_gap and psd.related_gap not in valid_gap_ids:
            warnings.append(f"Invalid gap reference: {psd.related_gap}")

    # Check search queries
    for sq in output.search_queries:
        if sq.related_gap and sq.related_gap not in valid_gap_ids:
            warnings.append(f"Invalid gap reference: {sq.related_gap}")
        if sq.related_theme and sq.related_theme not in valid_theme_ids:
            warnings.append(f"Invalid theme reference: {sq.related_theme}")

    # Check research questions
    for rq in output.research_questions:
        if rq.related_theme and rq.related_theme not in valid_theme_ids:
            warnings.append(f"Invalid theme reference: {rq.related_theme}")

    return warnings

def run_booster(bundle: ContextBundle) -> tuple[BoosterOutput, float, list[str]]:
    """
    Run the Deep Research Booster.

    Args:
        bundle: Context bundle from job output

    Returns:
        Tuple of (BoosterOutput, cost, warnings)
    """
    logger.info(f"Running booster for job {bundle.job_id}")

    # Build prompt
    prompt = build_booster_prompt(bundle)

    # Call Gemini with higher temperature for variety
    client = GeminiClient()
    response = client.generate_json(
        prompt=prompt,
        system_message=BOOSTER_ROLE,
        temperature=0.45,  # Higher for creative directions
    )

    if "error" in response:
        raise RuntimeError(f"Booster generation failed: {response['error']}")

    cost = response.get("cost", 0)
    data = response.get("data", {})

    # Parse response
    output = parse_booster_response(data, bundle)

    # Validate
    warnings = validate_booster_output(output, bundle)

    logger.info(
        f"Booster complete: {len(output.missing_perspectives)} perspectives, "
        f"{len(output.suggested_search_queries)} queries, "
        f"{len(warnings)} warnings, cost=${cost:.4f}"
    )

    return output, cost, warnings
```

---

### Task 7.5: Add Booster Celery Task

**File:** `backend/worker.py` (add to existing)

```python
@celery_app.task(name="backend.worker.run_booster")
def run_booster_task(job_id: str, user_id: str) -> dict:
    """
    Run Deep Research Booster for a completed job.

    Prerequisites:
    - Job must be in 'completed' status
    - Doc 0, Doc 1, Doc 2 must exist

    Output:
    - Booster expansion appended to Doc 1
    - Job artifacts updated with booster output
    """
    from backend.pipeline.booster.context_bundle_generator import generate_context_bundle
    from backend.pipeline.stages.booster_stage import run_booster
    from backend.models.booster_models import BoosterOutput

    logger.info(f"[{job_id}] Starting booster")

    try:
        # Get job
        job = get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Verify job is completed
        if job.get("status") not in ("completed", "completed_with_warnings"):
            raise ValueError(f"Job must be completed to run booster. Current: {job.get('status')}")

        # Verify docs exist
        artifacts = job.get("artifacts", {})
        jump_start = artifacts.get("jump_start")
        semantic_brief = artifacts.get("semantic_brief")
        extractions = artifacts.get("semantic_extractions", [])

        if not jump_start or not semantic_brief:
            raise ValueError("Doc 1 and Doc 2 must exist to run booster")

        # Update status
        update_job(job_id, status="running_booster", stage="booster")

        # Generate context bundle
        bundle = generate_context_bundle(
            job_id=job_id,
            jump_start=jump_start,
            semantic_brief=semantic_brief,
            extractions=extractions,
        )

        # Run booster
        booster_output, cost, warnings = run_booster(bundle)

        # Build booster expansion markdown
        expansion_md = _build_booster_expansion_markdown(booster_output)

        # Update Doc 1 with booster expansion
        updated_jump_start = _append_booster_to_jump_start(jump_start, booster_output)

        # Update job artifacts
        update_job(
            job_id,
            status="completed",  # Return to completed
            stage="complete",
            artifacts={
                **artifacts,
                "jump_start": updated_jump_start,
                "booster_output": _booster_output_to_dict(booster_output),
                "booster_expansion_md": expansion_md,
            },
            partial_outputs={
                "booster_summary": {
                    "perspectives_count": len(booster_output.missing_perspectives),
                    "queries_count": len(booster_output.suggested_search_queries),
                    "directions_count": len(booster_output.primary_source_directions),
                    "questions_count": len(booster_output.research_questions),
                    "cost": cost,
                    "warnings": warnings,
                }
            },
        )

        logger.info(f"[{job_id}] Booster complete")

        return {
            "status": "success",
            "job_id": job_id,
            "cost": cost,
            "warnings": warnings,
        }

    except Exception as e:
        logger.error(f"[{job_id}] Booster failed: {e}")
        # Restore job to completed status (booster failure doesn't affect core docs)
        update_job(job_id, status="completed", stage="complete")
        return {
            "status": "error",
            "job_id": job_id,
            "error": str(e),
        }
```

---

### Task 7.6: Add Booster API Endpoint

**File:** `backend/app/routes/jobs_routes.py` (add to existing)

```python
class BoosterRequest(BaseModel):
    """Request to run Deep Research Booster."""
    pass  # No user input needed

class BoosterResponse(BaseModel):
    """Response after triggering booster."""
    job_id: str
    status: str  # "running_booster" or "error"
    message: str

@router.post("/jobs/{job_id}/booster", response_model=BoosterResponse)
async def run_job_booster(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Trigger Deep Research Booster for a completed job.

    Prerequisites:
    - Job must be in 'completed' status
    - Doc 0, Doc 1, Doc 2 must exist

    The booster expands Doc 1 with additional research directions,
    search queries, and perspectives to investigate.

    Booster failure does NOT affect existing documents.
    """
    # Get job
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if job.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify job status
    status = job.get("status")
    if status == "running_booster":
        raise HTTPException(status_code=409, detail="Booster already running")

    if status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Job must be completed to run booster. Current: {status}"
        )

    # Verify docs exist
    artifacts = job.get("artifacts", {})
    if not artifacts.get("jump_start") or not artifacts.get("semantic_brief"):
        raise HTTPException(
            status_code=400,
            detail="Doc 1 and Doc 2 must exist to run booster"
        )

    # Check if booster already ran (warn but allow)
    if artifacts.get("booster_output"):
        # Could add logic here to prevent repeated runs, or allow with warning
        pass

    # Queue booster task
    from backend.worker import run_booster_task
    run_booster_task.delay(job_id, user.id)

    # Update status
    update_job(job_id, status="running_booster")

    return BoosterResponse(
        job_id=job_id,
        status="running_booster",
        message="Deep Research Booster started. Results will append to Doc 1.",
    )
```

---

### Task 7.7: Create Booster Expansion Markdown Builder

**File:** `backend/pipeline/booster/expansion_builder.py` (NEW)

```python
from backend.models.booster_models import BoosterOutput

def build_booster_expansion_markdown(output: BoosterOutput) -> str:
    """
    Build visually distinct booster expansion section for Doc 1.

    This section is appended to Jump-Start directions after a divider.
    """
    lines = [
        "",
        "---",
        "",
        "## 🔍 Deep Research Expansion",
        f"*Generated by Deep Research Booster on {output.booster_timestamp[:10]}*",
        "",
    ]

    # Missing Perspectives
    if output.missing_perspectives:
        lines.append("### Missing Perspectives to Seek")
        for mp in output.missing_perspectives:
            lines.append(f"- **{mp.description}**")
            lines.append(f"  - Why it matters: {mp.why_it_matters}")
            if mp.related_gaps:
                lines.append(f"  - Related gaps: {', '.join(mp.related_gaps)}")
        lines.append("")

    # Primary Sources
    if output.primary_source_directions:
        lines.append("### Primary Sources to Find")
        lines.append("| Type | Description | Search Approach |")
        lines.append("|------|-------------|-----------------|")
        for psd in output.primary_source_directions:
            lines.append(
                f"| {psd.source_type.value.replace('_', ' ').title()} | "
                f"{psd.description} | {psd.search_suggestion} |"
            )
        lines.append("")

    # Search Queries
    if output.suggested_search_queries:
        lines.append("### Suggested Search Queries")
        for i, sq in enumerate(output.suggested_search_queries, 1):
            lines.append(f"{i}. `{sq.query}`")
            lines.append(f"   - Purpose: {sq.purpose}")
            lines.append(f"   - Platform: {sq.platform_suggestion.value.title()}")
        lines.append("")

    # Research Questions
    if output.research_questions:
        lines.append("### Research Questions to Pursue")
        for rq in output.research_questions:
            lines.append(f"- {rq.question}")
            lines.append(f"  - Why: {rq.why_it_matters}")
        lines.append("")

    # Footer
    lines.extend([
        "---",
        "*Deep Research Expansion complete. These are DIRECTIONS to explore, not facts.*",
        "*Original source analysis above. Expansion suggestions below the divider.*",
    ])

    return "\n".join(lines)
```

---

### Task 7.8: Update JumpStartDirections Model

**File:** `backend/models/document_outputs.py` (modify)

Add booster expansion field:

```python
@dataclass
class JumpStartDirections:
    # ... existing fields ...

    # Booster Expansion (Phase 7)
    booster_expansion: Optional[dict] = None  # BoosterOutput as dict
    booster_expansion_md: Optional[str] = None  # Markdown format
```

---

### Task 7.9: Update Exports

**File:** `backend/pipeline/stages/__init__.py` (modify)

```python
# Booster Stage (Phase 7)
from .booster_stage import run_booster
```

**File:** `backend/models/__init__.py` (modify)

```python
from .booster_models import (
    ContextBundle,
    BoosterOutput,
    MissingPerspective,
    PrimarySourceDirection,
    SearchQuery,
    ResearchQuestion,
)
```

---

### Task 7.10: Verify and Test

```bash
# Syntax verification
python3 -m py_compile backend/models/booster_models.py
python3 -m py_compile backend/pipeline/prompts/booster_prompt.py
python3 -m py_compile backend/pipeline/booster/context_bundle_generator.py
python3 -m py_compile backend/pipeline/stages/booster_stage.py
python3 -m py_compile backend/pipeline/booster/expansion_builder.py

# Run tests
pytest backend/tests/ -v
```

---

## Files to Create

| File | Description | Lines (est) |
|------|-------------|-------------|
| `backend/models/booster_models.py` | Booster data models | ~150 |
| `backend/pipeline/prompts/booster_prompt.py` | LLM prompt | ~120 |
| `backend/pipeline/booster/__init__.py` | Package init | ~10 |
| `backend/pipeline/booster/context_bundle_generator.py` | Context bundle creation | ~100 |
| `backend/pipeline/stages/booster_stage.py` | Booster pipeline stage | ~200 |
| `backend/pipeline/booster/expansion_builder.py` | Markdown builder | ~80 |

## Files to Modify

| File | Changes |
|------|---------|
| `backend/worker.py` | Add run_booster_task |
| `backend/app/routes/jobs_routes.py` | Add /jobs/{job_id}/booster endpoint |
| `backend/models/document_outputs.py` | Add booster fields to JumpStartDirections |
| `backend/pipeline/stages/__init__.py` | Export booster stage |
| `backend/models/__init__.py` | Export booster models |

---

## API Contract

### POST /jobs/{job_id}/booster

**Prerequisites:**
- Job status: `completed` or `completed_with_warnings`
- Doc 1 and Doc 2 must exist

**Request:**
```json
{}  // No user input needed
```

**Response (Success):**
```json
{
    "job_id": "uuid",
    "status": "running_booster",
    "message": "Deep Research Booster started. Results will append to Doc 1."
}
```

**Response (Error):**
```json
{
    "detail": "Job must be completed to run booster. Current: running"
}
```

---

## Hallucination Protection Checklist

The booster prompt includes these protections:

- [x] NO FACTS rule
- [x] NO RESOLUTION rule (don't pick sides in tensions)
- [x] NO NEW ENTITIES rule
- [x] DIRECTIONS ONLY rule
- [x] GROUNDED rule (must reference bundle items)
- [x] Validation checks gap_id and theme_id references
- [x] Context bundle excludes full text and quotes
- [x] Higher temperature (0.45) for creative variety

---

## Doc 1 Integration Example

### Before Booster
```markdown
# JUMP-START RESEARCH DIRECTIONS

## SCOPE LOCK
[Original scope content...]

## GAPS
- GAP_1: No statement from other party
- GAP_2: No primary documentation

## TOP 3 NEXT STEPS
[Original next steps...]
```

### After Booster
```markdown
# JUMP-START RESEARCH DIRECTIONS

## SCOPE LOCK
[Original scope content...]

## GAPS
- GAP_1: No statement from other party
- GAP_2: No primary documentation

## TOP 3 NEXT STEPS
[Original next steps...]

---

## 🔍 Deep Research Expansion
*Generated by Deep Research Booster on 2026-01-16*

### Missing Perspectives to Seek
- **No response from other involved party**
  - Why it matters: One-sided narrative cannot be verified
  - Related gaps: GAP_1

### Primary Sources to Find
| Type | Description | Search Approach |
|------|-------------|-----------------|
| News Article | Contemporary coverage | Date-filtered search |

### Suggested Search Queries
1. `Creator X statement March 2024`
   - Purpose: Find earliest public statement
   - Platform: Google

### Research Questions to Pursue
- What was their position BEFORE the controversy?
  - Why: Establishes baseline for measuring shift

---
*These are DIRECTIONS to explore, not facts.*
```

---

## Verification Checklist

- [ ] Booster models created with all required fields
- [ ] Booster prompt includes all hallucination protection rules
- [ ] Context bundle excludes sensitive data (no full text, no quotes)
- [ ] Booster stage validates output references
- [ ] API endpoint enforces prerequisites
- [ ] Doc 1 updated with visually distinct expansion section
- [ ] Booster failure does NOT affect existing documents
- [ ] All syntax checks pass

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Booster hallucinates facts | Strict prompt rules + validation |
| Invalid gap/theme references | Post-generation validation |
| Large context bundle | Exclude full text, use summaries |
| Repeated booster runs | Track previous runs, warn user |
| Booster failure | Restore job to completed status |

---

## Post-Implementation

1. Run `/checkpoint`
2. Update PROGRESS.md
3. Commit: `Phase 7: Add Deep Research Booster pipeline`
4. Consider E2E test before Phase 8

---

## Dependencies

**Phase 7 depends on:**
- Phase 2: Semantic pipeline (Doc 0/1/2 generation)
- Phase 4: Validation patterns

**Phase 8 depends on Phase 7:**
- Producer Packet may use booster output

---

**END OF PLAN**
