# Research Agent System Specification (RASS)

**Version 2.0 — Complete Specification**
**Last Updated:** 2026-01-13

---

## 1. SYSTEM INTENT & NON-GOALS

### 1.1 System Intent (What this exists to do)

The Research Agent exists to act as a **semantic research assistant** for a **solo creator with ADHD**, by:

* Performing the **heavy cognitive lifting** of:
  * ingesting long-form sources
  * preserving full context
  * extracting structured meaning
  * organizing information for recall

* Producing **research artifacts** that allow the human user to:
  * understand a topic deeply (not shallow summaries)
  * re-orient quickly when memory fails
  * resume work without re-reading everything

* Delivering outputs that are:
  * skimmable first
  * expandable to full context
  * honest about uncertainty
  * explicitly grounded in source material

The system's primary value is **cognitive offloading**, not automation of thinking or creativity.

---

### 1.2 Definition of "80% of a Human Research Assistant"

"80% finished" means:

* The system delivers **most of the factual grounding, organization, and orientation** a skilled human researcher would provide **given the current corpus**
* The remaining 20% is intentionally left for:
  * human judgment
  * narrative construction
  * ethical interpretation
  * creative synthesis

The system **does not promise**:

* completeness independent of source quality
* correctness beyond available evidence
* resolution of ambiguity

Instead, it promises:

* clarity about what is known
* clarity about what is missing
* clarity about what is uncertain

---

### 1.3 Target User

* Single user (solo creator)
* ADHD, executive dysfunction–prone
* High curiosity, low tolerance for:
  * cognitive overload
  * vague outputs
  * re-reading long material
* Wants to:
  * learn deeply
  * think creatively
  * build narratives manually
* Does **not** want:
  * AI-written scripts
  * authoritative conclusions
  * black-box reasoning

---

### 1.4 System Non-Goals (Explicitly Out of Scope)

The Research Agent is **not**:

* A source discovery engine that autonomously defines topics
* A clip generator or editing tool
* A script writer
* A fact-checking authority
* A real-time conversational assistant
* A collaborative/team research platform
* A replacement for human judgment or curiosity

The system **must not**:

* invent facts to fill gaps
* guess or substitute source identity — metadata must be resolved deterministically before any LLM call
* collapse data and interpretation into a single layer
* present speculation as truth
* hide uncertainty for the sake of fluency
* allow sources to see each other during extraction

---

## 2. EPISTEMIC CONTRACT (Truth & Meaning Rules)

This section defines **how the system thinks**, not how it is implemented.

All downstream behavior is constrained by this contract.

---

### 2.1 Epistemic Categories (Mandatory Distinctions)

All extracted or produced information must fall into **one of the following categories**:

1. **Source Data**
   * Verbatim text from a source
   * Full transcripts, full articles, full threads
   * No interpretation
   * Canonical

2. **Descriptive Extraction**
   * What the source *explicitly says*
   * Quotes, paraphrased statements, claims made by speakers/authors
   * Still grounded entirely in the source
   * No added reasoning

3. **Semantic Interpretation**
   * Patterns, themes, tensions inferred *across* source data
   * May combine multiple sources
   * Must be explicitly labeled as interpretation
   * Must cite supporting source data

4. **Speculation / Creative Inference**
   * Hypotheses, implications, possible narratives
   * Explicitly marked as speculative
   * Never presented as fact
   * Optional and non-authoritative

---

### 2.2 Grounding Rules

* Every non-verbatim statement must reference:
  * one or more source identifiers
* If no supporting source exists:
  * the statement must be omitted **or**
  * explicitly marked as speculation

The system must prefer **absence** over fabrication.

---

### 2.3 Uncertainty Representation

Uncertainty is not an error state.

The system must surface uncertainty via:

* explicit gaps
* conflicting interpretations
* confidence calibration

The system must never:

* smooth over contradictions
* "average out" disagreements
* pick a side without evidence

---

### 2.4 Failure Philosophy

If the system cannot produce high-confidence output, it must:

* still return usable artifacts
* downgrade confidence
* emphasize gaps and next steps
* avoid over-synthesis

A thin but honest output is **preferred** to a fluent but misleading one.

---

## 3. CANONICAL DOCUMENT MODEL

The Research Agent produces **three core documents** plus one optional, each with strict boundaries.

These documents are **not interchangeable**.

---

### DOC 0 — SOURCE LEDGER (Canonical Data Layer)

**Purpose**

* Preserve **100% of full context**
* Act as the **single source of truth**
* Enable verification, recall, and re-orientation

**Allowed Content**

* Full transcripts (verbatim)
* Full article text
* Full thread/comment text
* Source metadata
* Lightweight skim summaries
* Indexes (quotes, timestamps, entities, claims)
* Transcript provenance metadata

**Forbidden Content**

* Interpretation
* Synthesis
* Narrative framing
* Opinions
* Recommendations

**Guarantees**

* No information appears elsewhere unless it exists here
* All other documents must reference this document

---

### DOC 1 — JUMP-START (Research Direction Layer)

**Purpose**

* Reduce activation energy
* Answer: *"What do I have, what's missing, where do I go next?"*

**Allowed Content**

* Scope lock (what this research is / is not)
* Coverage summary of current corpus
* Explicit gaps
* Open questions
* Research directions
* Suggested search queries
* Verification checklist
* "Top 3 next steps"

**Forbidden Content**

* Narrative conclusions
* Creative framing
* Claims of completeness
* New facts not in Doc 0

**Guarantees**

* Always produced, even if thin
* Useful without any external APIs
* May be augmented by Iterate: deep_dive mode

---

### DOC 2 — SEMANTIC RESEARCH BRIEF (80% Output)

**Purpose**

* Deliver deep understanding
* Externalize thinking
* Spark human insight, not replace it

**Allowed Content**

* Semantic core of the topic
* Themes and sub-themes
* Key points (grounded)
* Competing interpretations
* Tensions and contradictions
* Gaps and weaknesses
* Confidence calibration
* Clearly labeled speculation (optional)

**Forbidden Content**

* Scripts
* Final narratives
* Definitive conclusions
* Authoritative judgments
* New facts not in Doc 0

**Guarantees**

* Every section cites source identifiers
* Confidence and uncertainty are visible
* Skimmable before detailed

---

### DOC 3 — CREATOR BRIEF (Core — Auto-Generated)

**Purpose**

* Distill all research into a production-ready creative brief for the creator
* The hero document — what the creator actually uses to make content
* Bridge between raw research (Doc 2) and creative execution

**Gating Requirements**

* Automatically generated after Stage E (Assembly) completes
* No user trigger required — always produced if pipeline succeeds

**Allowed Content**

* Hook options (2, each referencing a claim_id from Doc 2)
* Setup: core theme/thesis from synthesis
* Twist: contradiction or reversal from `framing: contradicts` claims
* Core facts: 3–5 high-significance claims with plain-English phrasing and source links
* Analogy: explanation of core concept for general audience
* Personal stakes: why this matters to the viewer
* Cliffhanger: open questions or `framing: speculative` claims
* Sources for description box (formatted for copy-paste)
* Disputed/speculative claims section (explicit flagging)

**Forbidden Content**

* Scripts or full narration
* Presentation of speculative claims as confirmed
* New facts not traceable to Doc 0
* Modification of Docs 0/1/2

**Guarantees**

* Every hook_option references valid `claim_id` from Doc 2
* Every core_fact references valid `claim_id` (Doc 2) and `source_id` (Doc 0)
* Disputed claims match actual `framing` field from claim enrichments
* Temperature: 0.3 (creative but grounded)

---

### DOC 4 — PRODUCER PACKET (Optional Creative Layer)

**Purpose**

* Provide creative interpretation and story angles for long-form narrative construction
* Reduce activation energy for scripting
* Serve as a "co-producer" collaborator

**Gating Requirements (ALL must be met)**

* 4+ sources in the job
* At least 1 source with HIGH confidence ceiling
* Job status is "complete"
* User explicitly requests Doc 4

**Allowed Content**

* Story core and narrative angles
* Opening hooks and cold open options
* Structure options (chronological, thematic, etc.)
* Title and thumbnail concepts
* Risk assessment and sensitivity notes

**Forbidden Content**

* Presentation as fact
* Claims without explicit speculation label
* Modification of Docs 0/1/2/3

**Guarantees**

* Explicitly labeled as creative interpretation
* Does not contaminate canonical documents
* Higher temperature LLM calls permitted (0.3-0.5)

---

## 4. PIPELINE BEHAVIOR & STAGES

This section defines **how the system behaves end-to-end**, independent of code or vendor.

---

### 4.1 High-Level Pipeline Order (Non-Negotiable)

The Research Agent pipeline executes in the following order:

1. **Source Identity** — Resolve metadata before LLM
2. **Semantic Extraction** — Extract per source, isolated
3. **Validation** — Verify quotes, enforce ceilings
4. **Synthesis** — Cross-source analysis
5. **Assembly** — Build Doc 0/1/2 (Source Ledger, Jump-Start, Semantic Brief)
6. **Creator Brief** — Auto-generate Doc 3 from Doc 2 + Doc 0 data
7. **Optional: Iterate (deep_dive)** — Deep research directions (formerly Booster)
8. **Optional: Producer Packet** — Creative interpretation (Doc 4)

Stages may **degrade gracefully**, but **may not be skipped**.

---

### 4.2 Stage A — Source Identity (Pre-LLM)

**Purpose**

* Resolve all source metadata BEFORE any LLM call
* Determine analysis mode based on content availability
* Prevent LLM from guessing or inferring identity

**Inputs**

* User-provided sources:
  * YouTube URLs
  * Article URLs
  * Plain text (copy-paste)
  * Screenshots

**Behavior**

For each source:
1. Fetch metadata (title, creator, date, duration)
2. Attempt transcript acquisition (for video)
3. Determine analysis mode
4. Generate stable `source_id`
5. Package identity for downstream stages

**Analysis Mode Selection**

| Source Type | Content Available | Mode |
|-------------|-------------------|------|
| YouTube | Supadata/Whisper transcript | `transcript_grounded` |
| YouTube | YouTube captions only | `caption_grounded` |
| YouTube | No text | `video_only` |
| Article | Full text fetched | `article_fetched` |
| Text | User-provided | `text_provided` |
| Screenshot | OCR extracted | `ocr_extracted` |

**Transcript Acquisition Order (LOCKED)**

1. Supadata (primary) → `transcript_grounded`
2. Whisper (if Supadata fails) → `transcript_grounded`
3. YouTube captions (if Whisper fails) → `caption_grounded`
4. If all fail → `video_only` mode

**Failure Rules**

* If a single source fails → continue job with warning
* If all sources fail → job fails with actionable error
* Transcript failure MUST NOT fail the job

---

### 4.3 Stage B — Semantic Extraction

**Purpose**

* Extract meaning, not summaries
* Convert raw data into structured understanding units

**Primary Model**

* Gemini 2.5 Pro (semantic-first prompt)

**CRITICAL: Source Isolation Rule**

Each source MUST be extracted in a SEPARATE, ISOLATED LLM call.

* The model MUST NOT see content from other sources
* Cross-source analysis happens ONLY in synthesis stage
* This prevents cross-contamination of provenance

**Extracted Units**

* Key Points
* Claims (descriptive only)
* Themes (per-source)
* Tensions (per-source, if present)
* Quotes (if mode allows) OR Approximate Observations

**Mode-Specific Behavior**

| Mode | Quotes | Confidence Ceiling | Special Rules |
|------|--------|-------------------|---------------|
| `transcript_grounded` | Required (verbatim) | HIGH | Full quote verification |
| `caption_grounded` | Allowed (approximate) | MEDIUM | Approximate timestamps |
| `video_only` | FORBIDDEN | LOW | Use `approximate_observations` |
| `text_provided` | FORBIDDEN | MEDIUM | No source verification |
| `ocr_extracted` | FORBIDDEN | MEDIUM | OCR quality warning |
| `article_fetched` | Allowed | HIGH | Full quote verification |

**Prompt Requirements**

All extraction prompts MUST include:

1. **Source Identity Lock Block** — Immutable metadata
2. **Confidence Ceiling Declaration** — Max allowed confidence
3. **Empty Output Permission** — Permission to return sparse results
4. **Layered Extraction Instructions** — Layer 1 → 2 → 3
5. **Output Schema** — JSON structure with Pydantic reference

**Rules**

* Extraction must reference `source_id`
* No narrative synthesis
* No conclusions
* No creative framing
* Confidence cannot exceed mode ceiling

**Failure Rules**

* If extraction is thin:
  * Retry once with constrained prompt
* If still thin:
  * Proceed with downgraded confidence
  * Emphasize gaps in downstream docs

---

### 4.4 Stage C — Validation

**Purpose**

* Preserve epistemic integrity
* Prevent hallucinated grounding
* Enforce confidence ceilings

**Validation Actions**

1. **Quote Verification** (transcript_grounded, article_fetched only)
   * Match extracted quotes to source text
   * Mark: verified / partially verified / unverifiable

2. **Confidence Ceiling Enforcement**
   * Check all confidence levels against mode ceiling
   * Auto-downgrade if exceeded
   * Log warning for each downgrade

3. **Timestamp Validation** (video sources)
   * Verify timestamps within source duration
   * Flag out-of-range timestamps

4. **Source ID Consistency**
   * All extracted items reference valid source_id
   * Broken references are errors

**Rules**

* Unverifiable items are not removed
* They are explicitly marked
* Verification status propagates downstream

---

### 4.5 Stage D — Synthesis

**Purpose**

* Analyze patterns ACROSS sources
* Identify themes, tensions, gaps
* This is the ONLY stage that sees multiple sources

**Inputs**

* All validated extraction results

**Outputs**

* Cross-source themes
* Cross-source tensions
* Overall gaps
* Confidence assessment

**Rules**

* Must cite source_ids for all assertions
* Cannot introduce new facts
* Cannot resolve tensions — only surface them

---

### 4.6 Stage E — Assembly

**Purpose**

* Construct the three canonical documents
* Enforce document boundaries

**Assembly Order**

1. DOC 0 — Source Ledger
2. DOC 1 — Jump-Start
3. DOC 2 — Semantic Research Brief

**Rules**

* DOC 1 and DOC 2 may not introduce new data
* All references must trace to DOC 0
* If DOC 0 is thin → DOC 1 and DOC 2 must reflect this explicitly

---

### 4.7 Stage F — Creator Brief Assembly (Core — Auto-Runs After Stage E)

**Purpose**

* Generate Doc 3 (Creator Brief) automatically after Assembly completes
* Distill Doc 2 claims and Doc 0 sources into a creator-ready production brief

**Trigger**

* Automatic — runs after every successful Stage E
* No user initiation required

**Inputs**

* Doc 2 — all claims with enrichments (framing, speaker, significance, source_ids)
* Doc 0 — source metadata for citation formatting

**Pipeline**

1. **Claim Ranking** — Sort claims by significance, flag disputed/speculative
2. **Hook Generation** — Select 2 highest-impact claims as hook options
3. **Brief Assembly** — Build setup, twist, core facts, analogy, stakes, cliffhanger
4. **Provenance Validation** — Every claim_id and source_id verified against Doc 2/Doc 0
5. **Output Serialization** — Store as CreatorBriefDocument + render markdown

**Outputs**

* DOC 3 — Creator Brief
* Stored as `doc_3_path` in job artifacts

**Rules**

* Temperature: 0.3 (creative but grounded)
* Every hook_option must reference a valid claim_id
* Every core_fact must reference valid claim_id + source_id
* If Creator Brief generation fails: pipeline completes with warning, Doc 3 absent

---

### 4.8 Stage G — Iterate System (User-Triggered, Post-Completion)

**Purpose**

* Enable iterative improvement of research after initial pipeline completes
* Create new document versions without destroying existing versions

**Trigger**

* User-initiated after job completion via `POST /jobs/{job_id}/iterate`

**Five Iteration Modes**

| Mode | What It Does | Docs Affected |
|------|-------------|---------------|
| `deep_dive` | Gap analysis, search directions (formerly Booster) | Doc 1 only |
| `expand_sources` | Add new sources, re-run full pipeline (formerly Addendum/more_sources) | Doc 0/1/2/3 |
| `deeper` | Re-extract all sources with more detail | Doc 0/1/2/3 |
| `different_angle` | Re-synthesize with different framing | Doc 2/3 |
| `custom` | User-defined instructions | Specified docs |

**Versioning**

* Each iteration creates a new version of affected documents
* Rolling 4-version window (latest + 3 previous)
* Iteration history stored at `jobs/{job_id}/iterations/{iteration_id}/`

**Fallback Behavior**

* If iteration fails: previous versions remain valid
* Job status = completed_with_warnings (iteration failure does not break job)

---

### 4.9 Stage H — Optional Producer Packet (Doc 4)

**Purpose**

* Provide creative interpretation for narrative construction
* Reduce activation energy for scripting

**Gating Requirements**

* 4+ sources in job
* At least 1 high-confidence source
* Job status = complete
* User explicitly requests

**4-Stage Producer Pipeline**

1. **Story Core** — Central narrative and angles
2. **Structure Options** — Organization approaches
3. **Creative Elements** — Hooks, titles, thumbnails
4. **Risk & Context** — Sensitivity assessment

**Outputs**

* DOC 4 — Producer Packet
* Stored separately from canonical documents

**Rules**

* Higher temperature permitted (0.3-0.5)
* Explicitly labeled as creative interpretation
* Does not modify Docs 0/1/2/3

---

## 5. STORAGE & DATA OWNERSHIP MODEL

This section defines **where data lives and why**.

---

### 5.1 Canonical vs Derived Data

**Canonical**

* Full source text
* Source metadata
* Transcript provenance

**Derived**

* Indexes
* Semantic units
* Documents 1, 2, 3

Canonical data **must never be overwritten**.

---

### 5.2 Storage Split

**Supabase Storage (Blobs)**

* Full transcripts
* Full article text
* Full thread dumps

**Supabase Postgres**

* Jobs
* Sources
* Index records
* Semantic units
* Document metadata

**Note:** Phase 1 may store transcripts inline. Migration to blob-only in Phase 2.

---

### 5.3 Blob Ownership Rules

* Blobs are immutable after write
* Each blob tied to:
  * `job_id`
  * `source_id`
* Deletion cascades only on job deletion

---

## 6. LLM CONTRACTS (PROMPT + VALIDATION)

This section defines **how models are allowed to behave**.

---

### 6.1 Model Roles

* **Gemini 2.5 Pro**
  * Semantic extraction (per-source, isolated)
  * Synthesis (cross-source)
  * Creator Brief assembly (Doc 3)
  * Iterate: deep_dive pipeline
  * Producer Packet (Doc 4)

* **OpenAI / Perplexity / Exa**
  * Research expansion (Iterate: expand_sources and deep_dive only)
  * NOT used for extraction

No model performs extraction and synthesis in the same call.

---

### 6.2 Semantic Extraction Contract (Gemini)

**Gemini MUST**

* Identify themes (per-source)
* Extract key points
* Surface tensions
* Cite source_id
* Respect confidence ceiling
* Return empty arrays if no content found

**Gemini MUST NOT**

* Summarize the topic
* Write narratives
* Draw conclusions
* Fill gaps with assumptions
* Exceed confidence ceiling
* See other sources during extraction

---

### 6.3 Prompt Component Requirements

All semantic extraction prompts MUST include:

**1. Source Identity Lock Block**
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

**2. Confidence Ceiling Declaration**
```
CONFIDENCE CEILING: {ceiling}
Your maximum allowed confidence for any output is: {ceiling}
Output with higher confidence will be rejected by validation.
```

**3. Empty Output Permission**
```
EMPTY OUTPUT PERMISSION
It is acceptable — and preferred — to return empty arrays if:
- No clear key points emerge
- No tensions exist
- No relevant content found

DO NOT invent content to fill arrays.
Sparse, accurate output > dense, hallucinated output.
```

**4. Layered Extraction Instructions**
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

**5. Output Schema**
```
OUTPUT SCHEMA
Return valid JSON matching this structure:
{schema}

Use Pydantic model: {model_name}
```

---

### 6.4 Output Validation Rules

Validation occurs **after model output**.

**Hard Fail (Retry Once)**

* Invalid JSON
* Missing source_id references
* Confidence exceeds ceiling (after auto-downgrade fails)
* Empty DOC 0

**Soft Fail (Continue with Warning)**

* Thin extraction (below minimums)
* Low diversity
* Low verification rate
* Quote not found in source

**Soft Fail Handling**

* Retry once with constrained prompt
* If still failing: downgrade confidence, emphasize gaps

---

### 6.5 Cardinality Rules

* Item counts are **targets**, not absolutes
* Minimums trigger warnings, not failure
* Multiple retries are forbidden (max 1 retry)

**Minimum Targets (Warning if not met)**

| Document | Minimum | On Failure |
|----------|---------|------------|
| Doc 0 | 1+ source with content | Job fails |
| Doc 1 | 5+ gaps, 3+ next steps | Warning |
| Doc 2 | 8+ key points, 4+ themes | Warning |
| Doc 3 | 2 hook_options, 3+ core_facts | Warning (Doc 3 absent, not job failure) |

---

## 7. UX BEHAVIOR RULES (NOT UI)

This section defines **how information is experienced**.

---

### 7.1 Reading Order (Mandatory)

1. Jump-Start Summary
2. Semantic Research Brief (collapsed)
3. Source Ledger Index
4. Full Source Text (on demand)

---

### 7.2 Default Visibility

* Summaries visible by default
* Full text collapsed
* Speculation visually separated
* Confidence indicators always visible

---

### 7.3 Cognitive Load Rules

* Never present more than:
  * 7–9 bullets at once
* Always include:
  * "What's missing"
  * "What to do next"

---

### 7.4 Failure Communication

* Never hide failure
* Use:
  * warnings
  * downgraded confidence
  * explicit notes

---

### 7.5 User Agency Preservation

The system must never:

* Decide the narrative
* Resolve ambiguity for the user
* Present speculative output as authoritative

The system must:

* Provide triggers
* Preserve memory
* Enable human insight

---

## 8. TRANSCRIPT ACQUISITION & ANALYSIS POLICY

This section defines **how transcripts are acquired** and **how analysis adapts** based on transcript availability.

---

### 8.1 Transcript Acquisition Order (LOCKED)

For each video source, transcripts are acquired in priority order:

1. **Supadata** (primary) — Full transcript with high accuracy → `transcript_grounded`
2. **Whisper** (if Supadata fails) — Audio transcription → `transcript_grounded`
3. **YouTube captions** (fallback) — Auto-generated or uploaded captions → `caption_grounded`
4. **None** (degraded mode) — Video-only analysis proceeds → `video_only`

The system must attempt the next fallback if the higher-priority source fails.

---

### 8.2 Analysis Mode Recording

Gemini analysis **ALWAYS runs**, regardless of transcript availability.

The analysis mode must be recorded for each source as one of:

| Mode | Description |
|------|-------------|
| `transcript_grounded` | Full transcript available |
| `caption_grounded` | YouTube captions used |
| `video_only` | No text available |
| `text_provided` | User-provided text |
| `ocr_extracted` | Screenshot with OCR |
| `article_fetched` | Article full text |

This mode is stored in **Transcript Provenance** metadata and propagates to all downstream documents.

---

### 8.3 Degradation Rules

**Core Principle:** Transcript failure MUST NOT fail the job.

| Rule | Requirement |
|------|-------------|
| Job completion | Job MUST complete even with zero transcripts |
| Disclosure | Degradation MUST be disclosed in DOC 0 and DOC 2 |
| Quote flagging | Quotes from degraded sources MUST be flagged `unverified` |
| Confidence ceiling | Video-only sources cannot produce `high` confidence claims |

---

### 8.4 Capability Restrictions by Mode

| Capability | `transcript_grounded` | `caption_grounded` | `video_only` |
|------------|----------------------|-------------------|--------------|
| Quote verification | ✅ Full | ⚠️ Partial | ❌ None |
| Timestamp grounding | ✅ Precise | ⚠️ Approximate (±5s) | ❌ Unavailable |
| Semantic precision | High | Medium | Low |
| Max confidence level | High | Medium | Low |
| Verbatim quotes | ✅ Required | ⚠️ Approximate | ❌ `approximate_observations` only |

**Terminology:** In `video_only` mode, use `approximate_observations` (not "quotes") to describe what was observed.

---

### 8.5 Retry Rules for Transcript Acquisition

| Stage | Max Retries | On Failure |
|-------|-------------|------------|
| Supadata fetch | 1 | Try Whisper |
| Whisper | 1 | Try YouTube captions |
| Captions fetch | 1 | Continue with video_only |
| Gemini extraction | 1 | Fail stage with warning, continue job |

**CRITICAL:** Never fail job due to transcript absence alone.

---

## END OF SPECIFICATION

**Version:** 2.0
**Status:** Authoritative
**Supersedes:** All previous RASS versions
