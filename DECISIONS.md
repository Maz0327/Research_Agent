# Research Agent — Architectural Decision Records

**Purpose:** Document key architectural decisions and their rationale. These decisions are FINAL unless explicitly changed by the project owner.

---

## ADR-001: Replace Gemini 4-Pass with Semantic Pipeline

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
The existing video analysis pipeline uses a Gemini 4-pass approach:
- Pass 1: Extraction (clips/quotes)
- Pass 2: Structure Analysis (ContentBlueprint)
- Pass 3: Gap Analysis
- Pass 4: Research Starter

This doesn't align with RASS specification which requires:
- Source isolation during extraction
- Verification stage
- 3-document output model

### Decision
**Replace the Gemini 4-pass pipeline with the semantic pipeline.** Remove the old pipeline immediately without a transition period.

### Rationale
1. RASS requires source isolation — 4-pass doesn't enforce it
2. RASS requires verification stage — 4-pass doesn't have one
3. Semantic pipeline provides provenance tracking
4. Maintaining two pipelines is technical debt
5. 4-pass doesn't support multiple source types

### Consequences
- Existing output format changes
- Old `run_gemini_video_job` task removed
- No rollback without code restoration

---

## ADR-002: Six Analysis Modes

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Different source types have different content availability and verification capabilities.

### Decision
Implement **six analysis modes** with mode-specific extraction and confidence ceilings:

| Mode | Source Type | Confidence Ceiling | Quotes |
|------|-------------|-------------------|--------|
| `transcript_grounded` | YouTube with transcript | HIGH | Yes |
| `caption_grounded` | YouTube with captions | MEDIUM | Yes (approximate) |
| `video_only` | YouTube, no text | LOW | No |
| `text_provided` | User-pasted content | MEDIUM | No |
| `ocr_extracted` | Screenshot | MEDIUM | No |
| `article_fetched` | Article URL | HIGH | Yes |

### Rationale
1. Different sources warrant different confidence levels
2. Can't quote from sources without verifiable text
3. Explicit mode prevents wrong assumptions
4. Mode-specific prompts prevent hallucination

### Consequences
- Six prompt templates required
- Mode selector logic required
- Validation must check mode-specific rules

---

## ADR-003: Source Isolation During Extraction

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
When analyzing multiple sources, there's risk of cross-contamination if the LLM sees multiple sources at once.

### Decision
**Each source is extracted in a separate, isolated LLM call.** The model never sees other sources during extraction. Cross-source analysis only happens in synthesis.

### Rationale
1. Prevents cross-source hallucination
2. Guarantees provenance accuracy
3. Makes validation simpler
4. Required by RASS Section 4.3
5. Added to INDEX.md as non-negotiable rule

### Consequences
- More LLM calls (one per source)
- Slightly higher cost
- Cannot identify cross-source patterns during extraction (by design)

---

## ADR-004: Four-Document Output Model

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Users need different types of information: metadata, directions, analysis, and optionally creative interpretation.

### Decision
Produce **three core documents** plus one optional:

| Doc | Name | Purpose |
|-----|------|---------|
| Doc 0 | Source Ledger | What was analyzed, provenance |
| Doc 1 | Jump-Start | Gaps, next steps, search suggestions |
| Doc 2 | Semantic Brief | Themes, key points, tensions |
| Doc 3 | Producer Packet | Creative interpretation (optional) |

### Rationale
1. Separation of concerns
2. Doc 3 is creative layer that doesn't contaminate research
3. Added to INDEX.md and RASS.md

### Consequences
- Three document templates required (plus optional fourth)
- Assembly stage must produce all three
- Storage must accommodate all documents

---

## ADR-005: Producer Packet Gating

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Producer Packet (Doc 3) is creative interpretation and requires sufficient input.

### Decision
Producer Packet requires:
1. 4+ sources in job
2. At least 1 high-confidence source
3. Job status = complete
4. User explicitly requests it

### Rationale
1. Prevents low-quality creative output
2. Ensures sufficient input for meaningful interpretation
3. User opt-in for creative layer

### Consequences
- Gating logic required
- Separate API endpoint
- Cannot auto-generate

---

## ADR-006: Deep Research Booster as Optional Add-On

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
After initial analysis, users may want deeper research directions.

### Decision
Booster is:
1. Optional — user explicitly triggers
2. 4-stage pipeline
3. Appends to Doc 1 only
4. Does not modify Docs 0/2

### Rationale
1. Not everyone needs deep research
2. Separate from core analysis
3. RASS Section 4.7 defines this

### Consequences
- Separate API endpoint
- Separate Celery task
- Results append to existing Doc 1

---

## ADR-007: Evolving Jobs (Addendum Pattern)

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Users may discover new sources after initial analysis.

### Decision
Use **addendum pattern**:
- Original analysis preserved
- New sources extracted normally
- Cross-reference compares new to existing
- Addendum appended with clear marking

### Rationale
1. Original analysis preserved
2. Clear what's new vs original
3. Lower risk than full re-synthesis

### Consequences
- Cross-reference stage required
- Addendum template required
- Docs grow over time

---

## ADR-008: Validation with Quote Verification

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
LLMs can hallucinate quotes that don't exist in source material.

### Decision
For `transcript_grounded` and `article_fetched` modes, **verify extracted quotes exist in source text**.

### Rationale
1. Catches hallucinated quotes
2. No additional LLM call needed
3. High value for research accuracy
4. RASS Section 4.4 requires this

### Consequences
- Must have transcript text available
- Fuzzy matching needed
- Warning (not error) if quote not found

---

## ADR-009: Archive Dead Code, Don't Delete

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Audit found unused integration clients and deprecated code.

### Decision
**Archive to `backend/archive/`** rather than delete.

### Rationale
1. May need reference for future features
2. Git history isn't enough
3. Clear separation from active code

### Consequences
- Archive directory in codebase
- Must not import from archive

---

## ADR-010: Gemini 2.5 Pro as Primary LLM

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Multiple LLM options available.

### Decision
**Gemini 2.5 Pro** is the primary LLM for all pipeline stages.

Configuration:
- Extraction: temperature 0.1
- Synthesis: temperature 0.2
- Booster: temperature 0.4
- Producer: temperature 0.3-0.5

Use JSON mode with response_schema.

### Rationale
1. Already integrated
2. Native JSON mode
3. Good price/performance
4. Direct YouTube video analysis

### Consequences
- All prompts optimized for Gemini
- Must use response_mime_type: application/json

---

## ADR-011: Prompt Requirements (Five Components)

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Prompts need guardrails to prevent hallucination and ensure consistency.

### Decision
All semantic extraction prompts MUST include:
1. Source Identity Lock Block
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction Instructions
5. Output Schema

### Rationale
1. Prevents model from guessing identity
2. Enforces confidence limits
3. Allows sparse but accurate output
4. Structures extraction logically
5. Ensures valid JSON output

### Consequences
- All prompts must be audited
- Added to INDEX.md as non-negotiable
- Added to RASS.md Section 6.3

---

## ADR-012: Spec Documents Updated

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Analysis found INDEX.md and RASS.md were missing critical rules.

### Decision
Update both documents:

**INDEX.md additions:**
- Source Isolation Rule
- Six Analysis Modes table
- Doc 3 definition
- Prompt Requirements section

**RASS.md additions:**
- Source Isolation in Section 4.3
- All 6 modes in Section 4.2
- Prompt requirements in Section 6.3
- Doc 3 in Section 3

### Rationale
1. Constitution must be complete
2. Spec must match implementation requirements
3. Prevents future drift

### Consequences
- New spec documents deployed in Phase 0
- All code must align with updated specs

---

## Decision Index

| ADR | Title | Status |
|-----|-------|--------|
| 001 | Replace 4-Pass with Semantic Pipeline | Accepted |
| 002 | Six Analysis Modes | Accepted |
| 003 | Source Isolation During Extraction | Accepted |
| 004 | Four-Document Output Model | Accepted |
| 005 | Producer Packet Gating | Accepted |
| 006 | Deep Research Booster as Optional | Accepted |
| 007 | Evolving Jobs (Addendum Pattern) | Accepted |
| 008 | Validation with Quote Verification | Accepted |
| 009 | Archive Dead Code, Don't Delete | Accepted |
| 010 | Gemini 2.5 Pro as Primary LLM | Accepted |
| 011 | Prompt Requirements (Five Components) | Accepted |
| 012 | Spec Documents Updated | Accepted |

---

**All decisions are FINAL unless explicitly changed by project owner.**
