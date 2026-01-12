# Operational Definitions

**Research Agent System Specification — Addendum**

This document defines the **exact meaning** of core concepts used throughout the Research Agent.
If a term appears in code, prompts, validation logic, or UX, **it must conform to this document**.

---

## 1. SOURCE

### Definition

A **Source** is any discrete unit of external information provided to or ingested by the system.

### Examples

* One YouTube video
* One article
* One forum thread
* One uploaded text document

### Rules

* Each source is assigned a stable `source_id`
* A source has exactly **one canonical full-text representation**
* Partial excerpts are not sources

---

## 2. SOURCE DATA (CANONICAL)

### Definition

**Source Data** is the full, verbatim content of a source.

### Includes

* Full transcript of a video
* Full article text
* Full thread/comment text

### Rules

* Source Data is immutable after ingestion
* All downstream artifacts must trace back to Source Data
* No interpretation, summarization, or filtering occurs at this layer

---

## 3. QUOTE

### Definition

A **Quote** is verbatim text taken directly from Source Data.

### Properties

* Exact text match (or near-exact with punctuation tolerance)
* Associated with:

  * `source_id`
  * location anchor (timestamp, paragraph index, or offset)

### Rules

* Quotes do **not** imply truth
* Quotes do **not** imply importance
* Quotes exist only to support higher-level units

---

## 4. CLAIM

### Definition

A **Claim** is a declarative statement **made by a source** that asserts something about reality.

### Examples

* “The event happened in 2019.”
* “We never received funding.”
* “The study showed a 30% increase.”

### What a Claim is NOT

* Opinions (“I think this is bad”)
* Interpretations (“This suggests corruption”)
* General descriptions (“The video discusses funding issues”)

### Rules

* Claims must originate from a source
* Claims may be false, disputed, or unverifiable
* Claims must reference at least one supporting Quote

**Exception for video_only mode:**

When `analysis_mode = video_only`, Claims are not required to have supporting Quotes. Instead:
- Claims must reference approximate timestamp ranges
- Claims must be marked `confidence: low`
- Claims must include `source_mode: video_only` metadata

---

## 5. KEY POINT

### Definition

A **Key Point** is a **semantically meaningful assertion** that a human researcher would reasonably extract after reviewing the corpus.

### Properties

* Derived from one or more Claims and/or Quotes
* Expressed in neutral language
* Represents *what is being said*, not *what it means*

### Examples

* “Multiple sources state that funding was delayed.”
* “The subject gives differing accounts of the timeline.”

### What a Key Point is NOT

* A summary of the entire source
* A quote
* A conclusion
* A narrative beat

### Rules

* Each Key Point must reference:

  * one or more `source_id`s
* Key Points may conflict with one another
* Key Points may be incomplete

---

## 6. THEME

### Definition

A **Theme** is a recurring **conceptual pattern** that spans multiple Key Points.

### Properties

* Abstracted one level above Key Points
* Describes *what ideas recur*, not what is concluded

### Examples

* “Inconsistent timelines”
* “Financial opacity”
* “Shifting public narratives”

### Rules

* A Theme must:

  * contain ≥2 Key Points
* Themes must not:

  * assert causality
  * resolve ambiguity
* Themes may overlap

---

## 7. TENSION / CONTRADICTION

### Definition

A **Tension** exists when two or more Key Points cannot simultaneously be true **without explanation**.

### Examples

* Two sources give conflicting dates
* A subject contradicts earlier statements
* Data conflicts with testimony

### Rules

* Tensions must cite all involved Key Points
* The system must not resolve tensions unless evidence exists
* Tensions are surfaced, not adjudicated

---

## 8. GAP

### Definition

A **Gap** is information that a competent human researcher would reasonably expect to find **but is missing** from the current corpus.

### Examples

* Missing response from a key party
* No primary documentation for a major claim
* No coverage of consequences or outcomes

### Rules

* Gaps are contextual, not absolute
* Gaps must explain *why* the information is expected
* Gaps drive the Jump-Start document

---

## 9. SEMANTIC INTERPRETATION

### Definition

**Semantic Interpretation** is the act of identifying patterns, relationships, or implications **across** Key Points.

### Properties

* Requires multiple sources or points
* Must remain descriptive, not narrative

### Examples

* “Accounts of the event diverge after 2020.”
* “Discussion shifts from facts to personal attacks.”

### Rules

* Must cite supporting Key Points
* Must be clearly labeled as interpretation
* Must not introduce new facts

---

## 10. SPECULATION

### Definition

**Speculation** is any inference that goes beyond what the source data directly supports.

### Examples

* “This may indicate an attempt to obscure responsibility.”
* “One possible motive is financial pressure.”

### Rules

* Must be explicitly labeled as speculative
* Must never appear in Doc 0
* Optional in Doc 2
* Never presented as truth

---

## 11. THIN OUTPUT

### Definition

Output is considered **thin** when it fails to provide sufficient structure for understanding **relative to corpus size**.

### Indicators

* Very few Key Points given large source material
* Themes lack diversity
* Major claims have no supporting structure

### Rules

* Thin output does **not** fail the job
* Thin output triggers:

  * confidence downgrade
  * emphasis on gaps
  * stronger Jump-Start guidance

---

## 12. CONFIDENCE LEVELS

### High

* Multiple sources
* Verified quotes
* Consistent Key Points

### Medium

* Limited sources
* Partial verification
* Some ambiguity

### Low

* Single perspective
* Unverified claims
* Thin extraction

Confidence is descriptive, not evaluative.

---

## 13. CONTEXT BUNDLE

### Definition

A **Context Bundle** is a constrained input set used to guide downstream research or expansion.

### Includes

* Scope lock
* Key Points
* Themes
* Gaps

### Rules

* Context Bundles replace free-text topic prompts
* Used for Deep Research Booster
* Must not introduce new facts into canonical layers

---

## 14. TRANSCRIPT PROVENANCE

### Definition

**Transcript Provenance** is metadata describing how transcript text was acquired for a video source.

### Transcript Acquisition Order (LOCKED)

1. Supadata (primary) → `transcript_grounded`
2. Whisper (if Supadata fails) → `transcript_grounded`
3. YouTube captions (if Whisper fails) → `caption_grounded`
4. None (if all fail) → `video_only`

### Includes

* Transcript source (supadata, whisper, youtube_captions, or none)
* Acquisition status (success or failed)
* Analysis mode (transcript_grounded, caption_grounded, video_only)
* Verification capabilities (quote verification, timestamp grounding, semantic precision)

### Enables

* Confidence calibration based on source quality
* Appropriate flagging of unverified quotes
* Transparency about degradation

### Restricts

* Claims from degraded sources cannot be marked high-confidence
* Verbatim quotes require `transcript_grounded` mode

### Rules

* Every video source MUST have transcript provenance metadata
* Provenance propagates to all downstream documents
* Missing provenance is a validation error

---

## 15. DEGRADED SOURCE

### Definition

A **Degraded Source** is a source where the ideal transcript (Supadata or Whisper) was unavailable, requiring fallback to YouTube captions or video-only analysis.

### Indicators

* `transcript_source` = `youtube_captions` or `none`
* `gemini_analysis_mode` ≠ `transcript_grounded`

### Enables

* Partial analysis to proceed
* User awareness of limitations
* Job completion despite transcript failure

### Restricts

* Quote verification capabilities
* Timestamp precision claims
* Confidence level maximums:
  - `caption_grounded`: confidence ceiling = `medium`
  - `video_only`: confidence ceiling = `low`

### Rules

* Degraded sources do NOT fail jobs
* Degradation MUST be visible in DOC 0 and DOC 2
* Quotes from `caption_grounded` sources MUST be flagged as approximate
* `video_only` sources produce `approximate_observations`, not quotes

---

## 16. GEMINI VIDEO-ONLY ANALYSIS

### Definition

**Gemini Video-Only Analysis** is an analysis mode where Gemini processes video content without access to transcript text.

### Enables

* Visual/audio-based theme extraction
* `approximate_observations` — semantic descriptions of what was said (NOT quotes)
* Topic identification from non-text signals
* Job completion when transcript acquisition fails entirely

### Restricts

* **Quotes prohibited** — use `approximate_observations` instead
* Timestamp precision — cannot claim precise timestamps
* Confidence ceiling is `low` (categorical, not numeric)
* Quote verification — not available in this mode

### Terminology

In `video_only` mode, use **`approximate_observations`** consistently.
- These are semantic descriptions, NOT verbatim text
- All must be marked `approximate: true` and `type: observation`
- Do NOT call them "quotes" or "approximate quotes"

### Rules

* Video-only mode is triggered when Supadata, Whisper, AND YouTube captions all fail
* Analysis MUST still run (Gemini can process video directly)
* All outputs MUST include `analysis_limitations` field
* DOC 2 must visibly indicate degraded source quality

---

## End of Operational Definitions (Draft v1)

---
