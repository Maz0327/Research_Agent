# Plan: Hallucination Protection Spec Hardening & Implementation Prep

**Date**: 2026-01-11
**Branch**: feature/vision-alignment-v1
**Status**: Ready for approval

---

## Overview

This plan addresses spec drift and hallucination protection gaps identified in the 10 authoritative documents in `Active Docs/REVIEW THESE FILES/`. The goal is to harden specifications before any code implementation.

---

## Phase 1: File Organization

### 1.1 INDEX Files Strategy

| File | Action |
|------|--------|
| `/docs/authoritative/INDEX.md` | KEEP as authoritative constitution |
| `/Index.md` (root) | Convert to 1-screen pointer |

**Root Index.md becomes pointer only:**
```markdown
# Research Agent Index

See [`docs/authoritative/INDEX.md`](docs/authoritative/INDEX.md) for the Repo Constitution.

Quick links:
- [Specifications](docs/authoritative/spec/)
- [Prompts](docs/authoritative/prompts/)
- [Examples](docs/authoritative/examples/)
```

**docs/authoritative/INDEX.md updates:**
- Add Whisper as transcript fallback #2 (Supadata → Whisper → Captions → Video-only)
- Add approximate_observations terminology for video_only mode
- Add CORRECTIONS file as meta document
- Add "Definitions Authority" rule (Section 0.4)

### 1.2 Move Files to Target Locations

**Strategy**: Copy to target first, then move originals to `Archive Docs/` after verification.

| Source | Target |
|--------|--------|
| `Active Docs/REVIEW THESE FILES/Research Agent — Context Handoff Document.md` | `docs/authoritative/context/Context_Handoff.md` |
| `Active Docs/REVIEW THESE FILES/Research Agent System Specification (RASS).md` | `docs/authoritative/spec/RASS.md` |
| `Active Docs/REVIEW THESE FILES/Research Agent System Opirational Definitions.md` | `docs/authoritative/spec/Operational_Definitions.md` |
| `Active Docs/REVIEW THESE FILES/Document Output Format Specification.md` | `docs/authoritative/spec/Document_Output_Format.md` |
| `Active Docs/REVIEW THESE FILES/Validation & Retry Rules Specification.md` | `docs/authoritative/spec/Validation_and_Retry_Rules.md` |
| `Active Docs/REVIEW THESE FILES/Gemini Semantic Extraction Prompt Pack.md` | `docs/authoritative/prompts/Gemini_Semantic_Extraction.md` |
| `Active Docs/REVIEW THESE FILES/Gap Identification Prompt.md` | `docs/authoritative/prompts/Gap_Identification.md` |
| `Active Docs/REVIEW THESE FILES/Semantic Synthesis Prompt.md` | `docs/authoritative/prompts/Semantic_Synthesis.md` |
| `Active Docs/REVIEW THESE FILES/Deep Research Booster Prompt.md` | `docs/authoritative/prompts/Deep_Research_Booster.md` |
| `Active Docs/REVIEW THESE FILES/Claude Code Build Instructions.md` | `docs/authoritative/meta/Claude_Code_Build_Instructions.md` |
| `Active Docs/REVIEW THESE FILES/Missing Examples Tracker.md` | `docs/authoritative/meta/Missing_Examples_Tracker.md` |
| `Active Docs/REVIEW THESE FILES/ANALYSIS-REPORT-260108-semantic-spec-review.md` | `docs/authoritative/reviews/Spec_Review_2026-01-08.md` |
| `Active Docs/REVIEW THESE FILES/Degraded Output Example.md` | `docs/authoritative/examples/Example_Degraded_Output.md` |
| `Active Docs/REVIEW THESE FILES/Thin But Acceptable Output Example.md` | `docs/authoritative/examples/Example_Thin_But_Acceptable.md` |
| `Active Docs/REVIEW THESE FILES/Conflicting Sources Example.md` | `docs/authoritative/examples/Example_Conflicting_Sources.md` |
| `Active Docs/REVIEW THESE FILES/Minimal API Response Example.md` | `docs/authoritative/examples/Example_Minimal_API_Response.md` |
| `Active Docs/REVIEW THESE FILES/Producer Packet Example.md` | `docs/authoritative/examples/Example_Producer_Packet.md` |
| `Active Docs/REVIEW THESE FILES/Content Blueprint — Example Output.md` | `docs/authoritative/examples/Example_Content_Blueprint.md` |
| `Active Docs/REVIEW THESE FILES/AI Research Assistant Blueprint (1).md` | `docs/authoritative/examples/Example_Artifact_Index_Confidence_Summary.md` |
| `Active Docs/REVIEW THESE FILES/CORRECTIONS-260111-audit-review.md` | `docs/authoritative/meta/Corrections_260111.md` |

---

## Phase 2: Spec Hardening (10 Issues + Line-by-Line Fixes)

### 2.1 RASS.md Fixes

**Fix 1: Title formatting**
```markdown
BEFORE: Research Agent System Specification (RASS)
AFTER:  # Research Agent System Specification (RASS)
```

**Fix 2: Subtitle**
```markdown
BEFORE: **Draft v1 — Sections 1–7**
AFTER:  **Draft v1 — Sections 1–8**
```

**Fix 3: Transcript order (Section 4.2) — Apply EVERYWHERE**
```markdown
BEFORE:
* Transcript acquisition priority:
  1. YouTube captions
  2. Supadata
  3. Whisper (fallback)

AFTER:
* Transcript acquisition priority (LOCKED ORDER — apply to ALL docs):
  1. Supadata (primary) → transcript_grounded
  2. Whisper (if Supadata fails) → transcript_grounded
  3. YouTube captions (if Whisper fails) → caption_grounded
  4. If all fail → video_only mode (approximate_observations only)

NOTE: This order must be consistent in:
- RASS Section 4.2 and 8.1
- Operational_Definitions.md Section 16
- Document_Output_Format.md Transcript Provenance
- INDEX.md Transcript section
- Claude Code Build Instructions
```

**Fix 4: Add Identity Lock to Section 1.4**
```markdown
ADD after "invent facts to fill gaps":
* guess or substitute source identity — metadata must be resolved deterministically before any LLM call
```

### 2.2 Operational_Definitions.md Fixes

**Fix 0: Add "Definitions Authority" Rule to INDEX.md**
```markdown
ADD to docs/authoritative/INDEX.md Section 0.4:

## 0.4 Vocabulary Authority

Operational_Definitions.md is the AUTHORITATIVE vocabulary source.

If any prompt, spec, or example uses a term not defined there:
1. Check Operational_Definitions.md first
2. If undefined, defer to that document's closest match
3. If still ambiguous, flag for definition addition

Terms MUST NOT be redefined in individual prompts.
All prompts inherit vocabulary from Operational_Definitions.md.
```

**Fix 1: Filename**
```
RENAME: Research Agent System Opirational Definitions.md
TO:     Operational_Definitions.md
```

**Fix 2: Section 4 (Claim) - Add video_only exception**
```markdown
ADD after "Claims must reference at least one supporting Quote":

**Exception for video_only mode:**
When `analysis_mode = video_only`, Claims are not required to have supporting Quotes. Instead:
- Claims must reference approximate timestamp ranges
- Claims must be marked `confidence: low`
- Claims must include `source_mode: video_only` metadata
```

**Fix 3: Section 16 - Confidence ceiling**
```markdown
BEFORE: confidence ceiling is `medium`
AFTER:  confidence ceiling is `low`
```

### 2.3 Document_Output_Format.md Fixes

**Fix 1: Add FULL SOURCE TEXT placeholder rule**
```markdown
ADD after "#### FULL SOURCE TEXT (Canonical)":

If full source text is unavailable, use this standardized placeholder:

```
#### FULL SOURCE TEXT (Canonical)
⚠️ FULL SOURCE TEXT UNAVAILABLE

Reason: [Supadata failed / Captions unavailable / Access denied]
Analysis Mode: [video_only / caption_grounded]

This source was analyzed without verbatim transcript text.
All extracted quotes are approximate observations, not verbatim.
```

Never invent or reconstruct missing source text.
```

**Fix 2: Add extraction rules by mode (using approximate_observations)**
```markdown
ADD to Transcript Provenance section:

**Extraction Rules by Mode:**
| transcript_source | Output Type |
|-------------------|-------------|
| supadata | Verbatim quotes required |
| youtube_captions | Approximate quotes allowed, mark `approximate: true` |
| none (video_only) | `approximate_observations` only — NOT quotes |

TERMINOLOGY: In video_only mode, use "approximate_observations"
(not "approximate quotes") to avoid confusion.
```

**Fix 3: Terminology consistency**
```markdown
STANDARDIZE: Use "Skim Summary" consistently (not "Orientation Notes")
```

### 2.4 Validation_and_Retry_Rules.md Fixes

**Fix 1: Section 3 - Add video_only exception**
```markdown
ADD after "A Claim has no supporting Quote":

**Exception:** For sources with `analysis_mode = video_only`:
- Claims are not required to have supporting Quotes
- Claims must reference timestamp ranges (approximate)
- Claims must be marked `confidence: low`
- Validation passes if these conditions are met
```

**Fix 2: Section 2 - Reconcile with "jobs complete" policy**
```markdown
BEFORE: If retry fails → **Job = FAILED**

AFTER:  If retry fails → **Stage = failed_with_warnings**

        Job continues with degraded output:
        - Doc 0: Produced deterministically (always possible)
        - Doc 1: Produced from deterministic gap rules + available metadata
        - Doc 2: Marked "thin/degraded: semantic extraction unavailable"

        Job = FAILED only if:
        - ALL sources fail (nothing usable remains)
        - Infrastructure/system failure (pipeline crash, DB outage)
        - Contract violation (no sources provided at all)
```

**Fix 2b: Add malformed source handling**
```markdown
ADD new section:

### Malformed Source Handling

If a source is malformed (invalid URL, deleted/private video, access denied):
1. Mark source as `failed` with explicit reason
2. Exclude from semantic extraction (no Gemini call)
3. Record in Doc 0 with failure_reason
4. Propagate degradation to Doc 1/2

Job continues with remaining valid sources.
Job fails ONLY if no usable sources remain.
```

**Fix 3: Add confidence ceiling enforcement (CATEGORICAL, not numeric)**
```markdown
ADD new section 12.6:

### 12.6 Confidence Ceiling Enforcement (Machine-Checked)

Confidence uses CATEGORICAL values only: `low`, `medium`, `high`
Do NOT use numeric values (0.0-1.0) or percentages.

| Analysis Mode | Max Confidence | Auto-Downgrade |
|---------------|----------------|----------------|
| transcript_grounded | high | No |
| caption_grounded | medium | Yes, if high |
| video_only | low | Yes, if medium or high |

If output exceeds mode ceiling:
1. Auto-downgrade to ceiling value
2. Add warning: "Confidence auto-downgraded from {original} to {ceiling}"

RULE: All specs must use low/medium/high — never 0.3, 0.7, etc.
```

### 2.5 Gemini_Semantic_Extraction.md Fixes

**Fix 1: Section 8 video_only - Replace "quotes" with "approximate_observations"**
```markdown
BEFORE:
- Mark all quotes as `approximate: true` in the output
- Extract approximate quotes (paraphrased, not verbatim)

AFTER:
- You receive NO quotes in input (quotes array is empty before you process)
- You MAY generate `approximate_observations` — semantic descriptions of what was said
- All observations MUST include `approximate: true` and `type: observation`
- These are NOT quotes — use distinct terminology to prevent confusion
- Confidence ceiling is LOW (categorical, not numeric)

TERMINOLOGY RULE:
Use "approximate_observations" (not "approximate quotes") throughout all specs.
This eliminates ambiguity about what video_only mode produces.
```

**Fix 2: Add Source Identity Rule to Section 0**
```markdown
ADD after role definition:

## SOURCE IDENTITY CONTRACT (BEFORE REASONING)

The source_id and source metadata provided are CANONICAL.

You MUST NOT:
- Guess or infer which video/article this is
- Substitute or correct source metadata
- Assume information about the source not explicitly provided
- Reference external knowledge about this topic

If source identity seems wrong or incomplete:
- Proceed with provided data
- Note discrepancy in `analysis_limitations`
- Do NOT substitute a "likely" source
```

**Fix 3: Add Input Echo Requirement**
```markdown
ADD to Section 1 (Primary Prompt):

### Input Verification (Required First Step)

Before extracting any content, output:
```json
{
  "source_verification": {
    "source_id": "{provided_source_id}",
    "content_length": <word_count>,
    "first_line": "<first 50 chars>",
    "analysis_mode": "{mode}"
  }
}
```

This proves you are analyzing the correct content.
```

### 2.6 Gap_Identification.md Fixes

**Fix 1: Add Source Identity Rule**
```markdown
ADD to Section 0 (Role Definition):

You must NOT:
- Guess which video/article is being discussed
- Substitute a "likely" source
- Assume information not in the Context Bundle
```

**Fix 2: Add gap count guidance**
```markdown
ADD new section:

## GAP COUNT GUIDANCE

- Minimum: 0 (valid if corpus is comprehensive)
- Target: 3-7 gaps for typical research
- Maximum: 10 (prevent overwhelming user)

If fewer than 3 gaps identified for a multi-source corpus:
- This may indicate thin analysis
- Triggers soft fail review
```

### 2.7 Semantic_Synthesis.md Fixes

**Fix 1: Add Theme Minimum**
```markdown
ADD to Task 2 (Organize Themes):

**Theme Requirements:**
- Minimum total themes: 2
- Each theme must reference ≥2 Key Points
- If fewer than 2 themes emerge, this is valid but triggers confidence downgrade
```

**Fix 2: Emphasize No New Information Rule**
```markdown
ADD at top of Section 5 (Prohibitions):

⚠️ HIGHEST PRIORITY CONSTRAINT ⚠️

You have ONLY the JSON input provided. You have NO other knowledge.
Any fact, name, date, or claim NOT in this JSON is FABRICATION.
Before each sentence, ask: "Which source_id supports this?"
If no source_id supports it, DELETE the sentence.
```

### 2.8 Deep_Research_Booster.md Fixes

**Fix 1: Add merge strategy**
```markdown
ADD new section:

## MERGE STRATEGY (Doc 1 Integration)

Booster output is APPENDED to Doc 1, never replaces:

- `missing_perspectives` → append to "GAPS" section
- `primary_source_directions` → append to "RESEARCH DIRECTIONS"
- `research_questions` → append to "OPEN QUESTIONS"
- `suggested_search_queries` → append to "SUGGESTED QUERIES"

If booster fails, Doc 1 remains valid as-is.
```

**Fix 2: Ban factual assertions**
```markdown
ADD to Section 5 (Prohibitions):

**Explicit Factual Assertion Ban:**
Your output must NEVER contain:
- "X happened" / "Y occurred" / "Z discovered"
- "The evidence shows" / "This proves"
- Any statement that could be verified as true/false

You provide DIRECTIONS, not FINDINGS.
```

### 2.9 Claude_Code_Build_Instructions.md Fixes

**Fix 1: Correct file paths**
```markdown
BEFORE:
  workers/
    celery_tasks.py

AFTER:
  worker.py  # Main Celery worker (not in workers/ subdirectory)
  pipeline/
    stages.py  # Pipeline stage implementations
```

**Fix 2: Add legacy preservation as DOCS-ONLY safety rule**
```markdown
ADD to Section 0 (Global Rules):

## DOCS-ONLY SAFETY RULE: Legacy Output Preservation

During this documentation phase, we preserve existing outputs as a safety measure:
- producer_packet
- clips
- quotes
- content_blueprint

New semantic docs (Doc 0/1/2) are ADDITIVE during this phase.

NOTE: This is a docs-phase safety rule, not a permanent product decision.
Future deprecation may occur after semantic pipeline is validated.
```

### 2.10 Degraded_Output_Example.md Fix

**Fix: Add explicit prefix to observations**
```markdown
BEFORE:
**Key Points:**
- Creator X repeatedly reframes Event Y as unavoidable

AFTER:
**Key Points:**
- (Approximate observation, not verbatim quote) Creator X appears to reframe Event Y as unavoidable based on visual/audio cues
```

### 2.11 Missing_Examples_Tracker.md Fix

```markdown
UPDATE status:
- [x] Degraded Output Example ← NOW EXISTS
- [x] Thin-but-Acceptable Output Example ← NOW EXISTS
- [x] Conflicting Sources Example ← NOW EXISTS
- [x] Artifact Index / Confidence Summary ← NOW EXISTS
- [x] Minimal API Response Example ← NOW EXISTS
```

### 2.12 docs/authoritative/INDEX.md Updates

```markdown
ADD to Transcript Provenance section:

**Transcript Acquisition Order (Locked):**
1. Supadata (primary - includes title, date, description) → `transcript_grounded`
2. Whisper (if Supadata fails) → `transcript_grounded`
3. YouTube captions (if Whisper fails) → `caption_grounded`
4. If all fail → video_only mode

**Video-Only Mode: approximate_observations**
- Input to Gemini has empty quotes array
- Gemini generates `approximate_observations` (NOT quotes)
- All observations marked `approximate: true`, `type: observation`
- These are semantic descriptions, NOT verbatim text
- Confidence ceiling: LOW (categorical)

**Vocabulary Authority (Section 0.4):**
Operational_Definitions.md is the authoritative vocabulary source.
Prompts inherit definitions — they do not redefine terms.
```

### 2.13 Root /Index.md Conversion

Convert root `/Index.md` to a 1-screen pointer only:

```markdown
# Research Agent Index

See [`docs/authoritative/INDEX.md`](docs/authoritative/INDEX.md) for the Repo Constitution.

## Quick Links
- [Specifications](docs/authoritative/spec/)
- [Prompts](docs/authoritative/prompts/)
- [Examples](docs/authoritative/examples/)
- [Reviews](docs/authoritative/reviews/)
```

---

## Phase 3: Implementation Checklist

After specs are hardened, implementation follows this order:

### 3.1 New Models (backend/models/)
- [ ] `semantic_units.py` - KeyPoint, Theme, Tension, Gap, SemanticExtractionResult
- [ ] `document_outputs.py` - SourceLedger, JumpStartDirections, SemanticBrief

### 3.2 New Prompts (backend/pipeline/prompts/)
- [ ] `semantic_extraction_prompt.py` - Load from authoritative spec
- [ ] `semantic_synthesis_prompt.py` - Load from authoritative spec

### 3.3 New Validation (backend/pipeline/)
- [ ] `semantic_validation.py` - 4-level validation with mode-aware rules

### 3.4 New Pipeline Stages (backend/pipeline/stages/)
- [ ] `semantic_extraction.py` - New stage
- [ ] `document_assembly.py` - Generates Doc 0/1/2

### 3.5 Extend Existing (Additive Only)
- [ ] `gemini_client.py` - Add analysis_mode parameter, wire to prompts
- [ ] `job_record.py` - Add semantic artifact fields
- [ ] `extraction.py` - Set TranscriptProvenance, confidence_ceiling

### 3.6 DO NOT TOUCH
- `dual_output.py`
- `producer_packet` generation
- `clips`/`quotes` structures
- Existing validation logic

---

## Verification

After implementation:

1. **Unit Test**: Validate semantic_validation.py with mock outputs
2. **Integration Test**: Run with mock Gemini returning various quality outputs
3. **End-to-End Test**: Process real video (degraded source) to verify:
   - confidence_ceiling propagates correctly
   - video_only mode produces no verbatim quotes
   - approximate observations are marked
4. **Hallucination Test**: Feed Gemini a prompt that tempts speculation, verify rejection

---

## Summary

| Phase | Items | Scope |
|-------|-------|-------|
| 1: File Organization | INDEX strategy + file moves | Pointer + archive pattern |
| 2: Spec Hardening | 13 documents, ~28 edits | Documentation only |
| 3: Implementation | 9 files | Code changes (after spec approval) |

**Key Decisions Applied:**
1. `/Index.md` = pointer only → `docs/authoritative/INDEX.md` = constitution
2. Transcript order: Supadata → Whisper → Captions → Video-only (everywhere)
3. Terminology: `approximate_observations` (not "approximate quotes")
4. Confidence: categorical (`low`/`medium`/`high`) only
5. Legacy outputs: docs-phase safety rule (not permanent)
6. Vocabulary authority: Operational_Definitions.md is canonical

**Next Step**: Approve this plan, then execute Phase 1 + Phase 2 (docs only).
