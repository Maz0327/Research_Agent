# Claude Code Build Instructions

**Research Agent — Semantic Research Assistant**

---

## 0. GLOBAL RULES FOR CLAUDE (READ FIRST)

* Do **not** invent features or documents not specified
* Do **not** collapse Doc 0 / 1 / 2 into a single artifact
* Do **not** add creative writing outside Doc 2 (and only where allowed)
* Do **not** add summaries, scripts, or conclusions
* Prefer honest thin output over padded output
* Every non-verbatim statement must be traceable to Doc 0

---

## 0.1 DOCS-ONLY SAFETY RULE: Legacy Output Preservation

During this documentation phase, we preserve existing outputs as a safety measure:
- producer_packet
- clips
- quotes
- content_blueprint

New semantic docs (Doc 0/1/2) are ADDITIVE during this phase.

**NOTE:** This is a docs-phase safety rule, not a permanent product decision.
Future deprecation may occur after semantic pipeline is validated.

---

## 1. FILE / MODULE STRUCTURE (EXPECTED)

Claude should implement or modify the following logical areas:

```
backend/
  pipeline/
    ingest.py
    semantic_extraction.py
    gap_identification.py
    semantic_synthesis.py
    booster.py
    assembly.py
    validation.py

  prompts/
    gemini_semantic_extraction.md
    gemini_gap_identification.md
    gemini_semantic_synthesis.md
    deep_research_booster.md

  models/
    job.py
    source.py
    semantic_units.py

  storage/
    blob_store.py

  worker.py              # Main Celery worker (not in workers/ subdirectory)
  pipeline/
    stages.py            # Pipeline stage implementations
```

Claude may adapt names to the existing repo **but must preserve separation of concerns**.

---

## 2. DATA MODEL REQUIREMENTS

### 2.1 Source Model

Each source must store:

* `source_id`
* `job_id`
* `type` (youtube, article, thread, text)
* `title`
* `creator_or_author`
* `url`
* `duration_or_length`
* `blob_key` (Supabase Storage path)
* `ingest_status`
* `error_message` (nullable)

### 2.2 Semantic Units

Create tables / structures for:

* Key Points (`KP_x`)
* Claims (`CLM_x`)
* Themes (`THEME_x`)
* Tensions (`TEN_x`)
* Gaps (`GAP_x`)

Each must reference:

* `job_id`
* one or more `source_id`s

---

## 3. STORAGE REQUIREMENTS

### 3.1 Supabase Storage

* Create bucket: `media`
* Store full source text only
* Never overwrite blobs
* Serve blobs via signed URLs

### 3.2 Database

* Postgres stores:

  * metadata
  * semantic units
  * doc assembly outputs
* Blobs are **canonical**, DB entries are **derived**

---

## 4. PIPELINE IMPLEMENTATION (STRICT ORDER)

Claude must implement pipeline stages in this exact order:

### Stage A — Ingest

* Accept user-provided sources
* Fetch transcript/text
* Store full text in blob storage
* Create `Source` records

### Stage B — Semantic Extraction

* Call Gemini with **Semantic Extraction Prompt**
* Produce:

  * Key Points
  * Claims
  * Themes
  * Tensions
* No synthesis here

### Stage C — Validation

* Enforce:

  * schema validity
  * grounding rules
* Retry once on failure
* Mark soft vs hard failures

### Stage D — Gap Identification

* Call Gemini with **Gap Identification Prompt**
* Input = Context Bundle only
* Output = GAP objects only

### Stage E — Semantic Synthesis

* Call Gemini with **Semantic Synthesis Prompt**
* Input = Key Points, Themes, Tensions, Gaps
* Output = Doc 2 content only

### Stage F — Optional Booster

* Call Deep Research Booster (provider-agnostic)
* Augment Doc 1 only
* Never touch Doc 0 or Doc 2

---

## 5. DOCUMENT ASSEMBLY (MANDATORY)

Claude must assemble **three separate outputs**:

### Doc 0 — Source Ledger

* Includes:

  * source manifest
  * skim summaries
  * extracted indexes
  * FULL source text via blob reference
* No interpretation

### Doc 1 — Jump-Start

* Includes:

  * scope lock
  * what we know
  * gaps
  * research directions
  * top 3 next steps

### Doc 2 — Semantic Research Brief

* Includes:

  * semantic core
  * themes
  * key points
  * tensions
  * gaps
  * confidence assessment
  * optional speculation (labeled)

---

## 6. PROMPT WIRING (NON-NEGOTIABLE)

Claude must:

* Store prompts in `/prompts`
* Load prompts by role
* Never inline prompts in code
* Never mix prompt responsibilities

Each prompt corresponds to exactly **one cognitive role**.

---

## 7. VALIDATION & RETRY LOGIC

Claude must implement:

* Hard failures:

  * invalid JSON
  * missing grounding
* Soft failures:

  * thin output
  * low diversity
* Retry **once per stage**
* Downgrade confidence instead of failing whenever possible

---

## 8. JOB STATES

Claude must support:

* `pending`
* `processing`
* `completed`
* `completed_with_warnings`
* `failed`

Warnings must be human-readable.

---

## 9. ACCEPTANCE TESTS (REQUIRED)

Claude must include tests that verify:

* Docs are distinct
* Doc 0 contains full source text
* Doc 1 contains gaps + next steps
* Doc 2 contains synthesis but no new facts
* Thin output does not fail job
* Booster failure does not block core docs

---

## 10. EXPLICIT NON-GOALS (DO NOT IMPLEMENT)

Claude must NOT:

* Build UI
* Build clip generation
* Write scripts
* Discover topics automatically
* Add chat interfaces
* Add collaboration features

---

## FINAL INSTRUCTION TO CLAUDE

> Implement exactly this system.
> If a requirement is unclear, **do not guess** — surface the ambiguity instead.
> Preserve document boundaries at all costs.

---
