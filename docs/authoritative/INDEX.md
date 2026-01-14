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

## Source Isolation Rule (Non-Negotiable)

**Each source MUST be extracted in a SEPARATE, ISOLATED LLM call.**

Rules:
- The model must NEVER see content from other sources during extraction
- Cross-source analysis (themes, tensions) happens ONLY in synthesis stage
- Source identity must be resolved BEFORE LLM call, not inferred by LLM

Rationale:
- Prevents cross-contamination of source attribution
- Guarantees provenance accuracy
- Enables parallel processing
- Makes validation simpler (check one source at a time)

**Violation of this rule is a critical bug.**

---

## Six Analysis Modes (Authoritative)

Every source is assigned ONE analysis mode based on source type and content availability.

| Mode | Source Type | Confidence Ceiling | Quotes Allowed |
|------|-------------|-------------------|----------------|
| `transcript_grounded` | YouTube with Supadata/Whisper transcript | HIGH | Yes (verbatim) |
| `caption_grounded` | YouTube with captions only | MEDIUM | Yes (approximate) |
| `video_only` | YouTube, no text available | LOW | **No** (observations only) |
| `text_provided` | User-pasted content | MEDIUM | **No** |
| `ocr_extracted` | Screenshot with OCR | MEDIUM | **No** |
| `article_fetched` | Article URL with full text | HIGH | Yes |

**Rules:**
- Mode is determined BEFORE extraction, not during
- Mode determines confidence ceiling — extraction cannot exceed it
- Modes without quote permission use `approximate_observations` instead
- Mode is recorded in TranscriptProvenance and propagates to all outputs

---

## Canonical Document Model (Non-Negotiable)

The Research Agent produces **three core documents** plus one optional:

### Doc 0 — Source Ledger (Canonical Data Layer)
- Preserves **100% of full context** and raw extracted structure
- Includes full source text (or explicit placeholder if unavailable)
- Includes provenance, transcript status, and degradation flags
- **No interpretation, no synthesis, no opinions**

### Doc 1 — Jump-Start Research Brief (Research Direction Layer)
- "What do I have, what's missing, where do I go next?"
- Gaps, research directions, and top next steps
- **No narrative conclusions**
- **No new facts beyond Doc 0**

### Doc 2 — Semantic Research Brief (80% Finished Output)
- Themes, key points, tensions, assumptions, gaps
- Confidence calibration and explicitly labeled speculation
- **No new facts beyond Doc 0**
- All reasoning must trace back to Doc 0

### Doc 3 — Producer Packet (Optional Creative Layer)
- Story angles, hooks, structure options, creative elements
- **GATED:** Requires 4+ sources AND 1+ high-confidence source
- Explicitly labeled as creative interpretation
- Does NOT affect Docs 0/1/2
- User must explicitly request this document

**Hard boundary rules:**
- Docs 1 and 2 must not introduce facts not present in Doc 0
- Doc 3 is isolated from canonical documents

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
- Confidence ceiling depends on mode (see above)

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

## Prompt Requirements (Non-Negotiable)

All LLM prompts for semantic extraction MUST include these 5 components:

### 1. Source Identity Lock Block
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
Explicit statement of maximum allowed confidence. Output exceeding ceiling is rejected.

### 3. Empty Output Permission
Explicit permission to return empty arrays if no relevant content found. Prevents hallucination.

### 4. Layered Extraction Instructions (extraction prompts only)
- Layer 1: Explicit content only (what source says)
- Layer 2: Patterns from Layer 1
- Layer 3: Themes from Layer 2

### 5. Output Schema
JSON structure specification with Pydantic model reference.

**Prompts missing any component are invalid.**

---

## Authoritative Documents (Must Exist in Repo)

Location: `docs/authoritative/`

### System Specification
- `spec/RASS.md` — Research Agent System Specification
- `spec/Operational_Definitions.md` — Vocabulary authority
- `spec/Document_Output_Format.md` — Doc 0/1/2/3 schemas
- `spec/Validation_and_Retry_Rules.md` — Failure handling

### Prompt Contracts (Never Inline)
- `prompts/Gemini_Semantic_Extraction.md`
- `prompts/Gap_Identification.md`
- `prompts/Semantic_Synthesis.md`
- `prompts/Deep_Research_Booster.md`

### Orchestration Specifications
- `Job_State_Machine.md` — Job lifecycle, status transitions, failure handling
- `API_Endpoint_Spec.md` — REST API contract, request/response shapes
- `Celery_Task_Flow.md` — Task orchestration, retry logic, queue configuration

### Canonical Examples
- `examples/Example_Producer_Packet.md`
- `examples/Example_Content_Blueprint.md`
- `examples/Example_Degraded_Output.md`
- `examples/Example_Thin_But_Acceptable.md`
- `examples/Example_Conflicting_Sources.md`

### Meta / Build Instructions
- `meta/Claude_Code_Build_Instructions.md`

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
