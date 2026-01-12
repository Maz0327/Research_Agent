# Authoritative Spec Index (Repo Constitution)

**READ THIS FIRST.**
This file is the single, repo-level pointer for what is **authoritative** vs **legacy** for the Research Agent.

If you are a human, Claude Code, Cursor, or any other agent: **do not implement anything until you have read the authoritative docs and canonical examples listed below.**

---

## Precedence Rules (Non-Negotiable)

When there is any ambiguity or conflict:

1. **Example artifacts override prose**
2. **Prose overrides inferred behavior**
3. **If still unclear, ASK before proceeding**

**Implementation rule:**
If an implementation decision conflicts with a canonical example, **the example wins**.
Update/replace the example *before* changing behavior.

---

## Vocabulary Authority (Non-Negotiable)

`Operational_Definitions.md` is the **authoritative vocabulary source** for this system.

**Rules:**
1. If any prompt, spec, or example uses a term, check `Operational_Definitions.md` first
2. If undefined there, defer to that document's closest semantic match
3. If still ambiguous, flag for definition addition before proceeding

**Prohibition:**
Terms MUST NOT be redefined in individual prompts or specs.
All documents inherit vocabulary from `Operational_Definitions.md`.

---

## System Non-Goals (Authoritative)

This system is NOT:

- a general-purpose research engine
- an autonomous truth-finder or adjudicator
- optimized for breadth, coverage, or completeness
- designed to resolve contradictions or decide who is correct
- intended to output publish-ready scripts or final narratives

This system IS:

- an externalized cognition and memory system
- a semantic sense-making assistant for humans
- designed to reduce activation energy (ADHD-first)
- built to preserve receipts, provenance, and uncertainty
- meant to prepare a human to think, not replace thinking

---

## Brevity vs Depth (Authoritative)

**Brevity is a UI constraint, not a depth constraint.**

All artifacts must be:

- **skimmable by default**
- **expandable** via:
  - full source text (Doc 0)
  - provenance metadata
  - explicit gaps
  - next-step research prompts

Short outputs must **never** be interpreted as complete understanding.

---

## Definition of "Semantic" (Locked)

"Semantic understanding" in this system means:

- identifying key points
- identifying themes
- surfacing tensions and contradictions
- noting assumptions and gaps

It does NOT mean:

- sentiment analysis
- psychological profiling
- motive inference beyond source material
- interpretation or judgment not supported by receipts

---

## Canonical 3-Document Model (Non-Negotiable)

The Research Agent produces **three distinct documents** with strict boundaries:

### Doc 0 — Source Ledger (Canonical Data Layer)
- Preserves **100% of full context** and raw extracted structure
- Includes full source text (or explicit placeholder if unavailable)
- Includes provenance, transcript status, and degradation flags
- **No interpretation, no synthesis, no opinions**

### Doc 1 — Jump-Start Research Brief (Research Direction Layer)
- "What do I have, what's missing, where do I go next?"
- Gaps, research directions, and top next steps
- **No narrative conclusions**
- **No new facts**

### Doc 2 — Semantic Research Brief (80% Finished Output)
- Themes, key points, tensions, assumptions, gaps
- Confidence calibration and explicitly labeled speculation
- **No new facts beyond Doc 0**
- All reasoning must trace back to Doc 0

**Hard boundary rule:**
Docs 1 and 2 must not introduce facts not present in Doc 0.

---

## Transcript Provenance (Authoritative)

Every video source must record transcript provenance and analysis mode.

**Transcript Acquisition Order (LOCKED):**
1. Supadata (primary — includes title, date, description) → `transcript_grounded`
2. Whisper (if Supadata fails) → `transcript_grounded`
3. YouTube captions (if Whisper fails) → `caption_grounded`
4. If all fail → `video_only` mode

**Analysis Mode Rules:**
- Gemini always runs (receives content regardless of transcript status)
- Transcript failure must **never** fail a job
- Degradation must be visible in outputs
- Confidence ceiling depends on mode (see below)

**Confidence Ceilings (Categorical):**
| Analysis Mode | Max Confidence |
|---------------|----------------|
| transcript_grounded | high |
| caption_grounded | medium |
| video_only | low |

**Video-Only Mode: `approximate_observations`**
- Input to Gemini has empty quotes array
- Gemini generates `approximate_observations` (NOT quotes)
- All observations marked `approximate: true`, `type: observation`
- These are semantic descriptions, NOT verbatim text
- TERMINOLOGY: Use "approximate_observations" consistently, never "approximate quotes"

---

## Authoritative Documents (Must Exist in Repo)

Location: `docs/authoritative/`

### Context
- `context/Context_Handoff.md`

### System Specification
- `spec/RASS.md`
- `spec/Operational_Definitions.md`
- `spec/Document_Output_Format.md`
- `spec/Validation_and_Retry_Rules.md`

### Prompt Contracts (Never Inline)
- `prompts/Gemini_Semantic_Extraction.md`
- `prompts/Gap_Identification.md`
- `prompts/Semantic_Synthesis.md`
- `prompts/Deep_Research_Booster.md`

### Meta / Build Instructions
- `meta/Claude_Code_Build_Instructions.md`
- `meta/Missing_Examples_Tracker.md`
- `meta/Corrections_260111.md`

### Reviews
- `reviews/Spec_Review_2026-01-08.md`

---

## Canonical Example Artifacts (Example-Wins)

Location: `docs/authoritative/examples/`

### Core Outputs
- `Example_Producer_Packet.md`
- `Example_Content_Blueprint.md`

### Trust & Failure Modes
- `Example_Degraded_Output.md`
- `Example_Thin_But_Acceptable.md`
- `Example_Conflicting_Sources.md`

### System & UX Anchors
- `Example_Artifact_Index_Confidence_Summary.md`
- `Example_Minimal_API_Response.md`

**Rule:**
If code behavior conflicts with an example, treat it as a bug in code
(or update the example first, explicitly).

---

## Legacy / Superseded Documentation

Files describing older or competing system behavior are **LEGACY** and must not be implemented from.

They must either:
- contain a LEGACY banner pointing here, or
- be moved under `docs/legacy/` with a stub pointer

**Authoritative reference:**
`docs/authoritative/INDEX.md`

---

## Change Policy (Drift Prevention)

1. Update **canonical examples first**
2. Then update prose specs
3. Then update code

This order is mandatory.

---

**END OF REPO CONSTITUTION**
