# Research Agent System Specification (RASS)

**Draft v1 — Sections 1–8**

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

The system’s primary value is **cognitive offloading**, not automation of thinking or creativity.

---

### 1.2 Definition of “80% of a Human Research Assistant”

“80% finished” means:

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
* “average out” disagreements
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

The Research Agent produces **three distinct documents**, each with strict boundaries.

These documents are **not interchangeable**.

---

## DOC 0 — SOURCE LEDGER (Canonical Data Layer)

### Purpose

* Preserve **100% of full context**
* Act as the **single source of truth**
* Enable verification, recall, and re-orientation

### Allowed Content

* Full transcripts (verbatim)
* Full article text
* Full thread/comment text
* Source metadata
* Lightweight skim summaries
* Indexes (quotes, timestamps, entities, claims)

### Forbidden Content

* Interpretation
* Synthesis
* Narrative framing
* Opinions
* Recommendations

### Guarantees

* No information appears elsewhere unless it exists here
* All other documents must reference this document

---

## DOC 1 — JUMP-START (Research Direction Layer)

### Purpose

* Reduce activation energy
* Answer: *“What do I have, what’s missing, where do I go next?”*

### Allowed Content

* Scope lock (what this research is / is not)
* Coverage summary of current corpus
* Explicit gaps
* Open questions
* Research directions
* Suggested search queries
* Verification checklist
* “Top 3 next steps”

### Forbidden Content

* Narrative conclusions
* Creative framing
* Claims of completeness

### Guarantees

* Always produced, even if thin
* Useful without any external APIs
* May be augmented by Deep Research Booster

---

## DOC 2 — SEMANTIC RESEARCH BRIEF (80% Output)

### Purpose

* Deliver deep understanding
* Externalize thinking
* Spark human insight, not replace it

### Allowed Content

* Semantic core of the topic
* Themes and sub-themes
* Key points (grounded)
* Competing interpretations
* Tensions and contradictions
* Gaps and weaknesses
* Confidence calibration
* Clearly labeled speculation (optional)

### Forbidden Content

* Scripts
* Final narratives
* Definitive conclusions
* Authoritative judgments

### Guarantees

* Every section cites source identifiers
* Confidence and uncertainty are visible
* Skimmable before detailed

---

## 4. PIPELINE BEHAVIOR & STAGES

This section defines **how the system behaves end-to-end**, independent of code or vendor.

---

### 4.1 High-Level Pipeline Order (Non-Negotiable)

The Research Agent pipeline executes in the following order:

1. **Ingest**
2. **Semantic Extraction**
3. **Verification**
4. **Assembly**
5. **Optional Deep Research Booster**

Stages may **degrade gracefully**, but **may not be skipped**.

---

### 4.2 Stage A — Ingest

**Purpose**

* Acquire full context
* Preserve raw data
* Normalize sources into a common internal representation

**Inputs**

* User-provided sources (primary):

  * YouTube URLs
  * Articles
  * Threads
  * Plain text (later phase)

**Behavior**

* For each source:

  * Fetch metadata
  * Fetch full content
  * Store full content as a blob
  * Generate a stable `source_id`
* Transcript acquisition priority (LOCKED ORDER — see Section 8.1):

  1. Supadata (primary) → `transcript_grounded`
  2. Whisper (if Supadata fails) → `transcript_grounded`
  3. YouTube captions (if Whisper fails) → `caption_grounded`
  4. If all fail → `video_only` mode

**Failure Rules**

* If a single source fails → continue job with warning
* If all sources fail → job fails with actionable error

---

### 4.3 Stage B — Semantic Extraction

**Purpose**

* Extract meaning, not summaries
* Convert raw data into structured understanding units

**Primary Model**

* Gemini (semantic-first prompt)

**Extracted Units**

* Themes
* Key points
* Entities
* Claims (descriptive only)
* Tensions / contradictions (if present)

**Rules**

* Extraction must reference `source_id`
* No narrative synthesis
* No conclusions
* No creative framing

**Failure Rules**

* If extraction is thin:

  * Retry once with constrained prompt
* If still thin:

  * Proceed with downgraded confidence
  * Emphasize gaps in downstream docs

---

### 4.4 Stage C — Verification

**Purpose**

* Preserve epistemic integrity
* Prevent hallucinated grounding

**Verification Actions**

* Match quotes to source text
* Validate timestamps (if present)
* Mark:

  * verified
  * partially verified
  * unverifiable

**Rules**

* Unverifiable items are not removed
* They are explicitly marked
* Verification status propagates downstream

---

### 4.5 Stage D — Assembly

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

### 4.6 Stage E — Optional Deep Research Booster

**Purpose**

* Expand research directions beyond the current corpus
* Never contaminate canonical data

**Trigger**

* Runs post-job by default
* User-initiated or automatic if gaps are detected

**Inputs**

* Context Bundle (derived from DOC 0 + DOC 1)

**Outputs**

* Augments DOC 1 only
* Adds:

  * new leads
  * missing perspectives
  * primary source directions

**Fallback Behavior**

* If booster fails:

  * DOC 1 remains valid
  * Job status = completed_with_warnings

---

## 5. STORAGE & DATA OWNERSHIP MODEL

This section defines **where data lives and why**.

---

### 5.1 Canonical vs Derived Data

**Canonical**

* Full source text
* Source metadata

**Derived**

* Indexes
* Semantic units
* Documents 1 & 2

Canonical data **must never be overwritten**.

---

### 5.2 Storage Split

**Supabase Storage**

* Full transcripts
* Full article text
* Full thread dumps

**Supabase Postgres**

* Jobs
* Sources
* Index records
* Semantic units
* Document metadata

---

### 5.3 Blob Ownership Rules

* Blobs are immutable after write
* Each blob tied to:

  * `job_id`
  * `source_id`
* Deletion cascades only on job deletion

---

### 5.4 Migration Strategy

**Phase 1 (MVP)**

* Store transcripts inline + blob pointer

**Phase 2**

* Blob-only
* Inline removed

**Rule**

* Document contracts must not change between phases

---

## 6. LLM CONTRACTS (PROMPT + VALIDATION)

This section defines **how models are allowed to behave**.

---

### 6.1 Model Roles

* **Gemini**

  * Semantic extraction only
* **OpenAI / Perplexity / Exa**

  * Research expansion only
* No model performs both roles in the same stage

---

### 6.2 Semantic Extraction Contract (Gemini)

**Gemini MUST**

* Identify themes
* Extract key points
* Surface tensions
* Cite sources

**Gemini MUST NOT**

* Summarize the topic
* Write narratives
* Draw conclusions
* Fill gaps with assumptions

---

### 6.3 Output Validation Rules

Validation occurs **after model output**.

**Hard Fail**

* Invalid JSON
* Missing source references
* Empty DOC 0

**Soft Fail**

* Thin extraction
* Low diversity
* Low verification rate

**Soft Fail Handling**

* Retry once
* Downgrade confidence
* Emphasize gaps

---

### 6.4 Cardinality Rules

* Item counts are **targets**, not absolutes
* Minimums trigger warnings, not failure
* Multiple retries are forbidden

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

  * “What’s missing”
  * “What to do next”

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

## End of Draft v1 (Sections 1–7)

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

This mode is stored in **Transcript Provenance** metadata and propagates to all downstream documents.

---

### 8.3 Degradation Rules

**Core Principle:** Transcript failure MUST NOT fail the job.

| Rule | Requirement |
|------|-------------|
| Job completion | Job MUST complete even with zero transcripts |
| Disclosure | Degradation MUST be disclosed in DOC 0 and DOC 2 |
| Quote flagging | Quotes from degraded sources MUST be flagged `unverified` |
| Confidence ceiling | Video-only sources cannot produce `high_confidence` claims |

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
| Supadata fetch | 1 | Try YouTube captions |
| Captions fetch | 1 | Continue with video_only |
| Gemini stage | 1 | Fail stage, not job |

**CRITICAL:** Never fail job due to transcript absence alone.

---

