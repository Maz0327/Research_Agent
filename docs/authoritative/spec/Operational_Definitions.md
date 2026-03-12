# docs/authoritative/spec/Operational_Definitions.md

**Purpose:** Authoritative vocabulary and operational rules. Any ambiguity must be resolved here first.

**Non‑negotiable:**
- *Examples > prose > inferred behavior.*
- Terms MUST NOT be redefined elsewhere.

---

## 1) Core Objects

### Job
A long-running unit of work that ingests one or more sources and produces Docs 0–2 (and optional Doc 3 / boosters). A Job is the only durable container for artifacts.

### Source
A discrete unit of input content. Each source is processed in an isolated extraction call.

A job contains **N sources**. Each source has:
- a stable `source_id`
- exactly one `source_type`
- exactly one `analysis_mode`
- its own provenance

**Source types (canonical):**
- `youtube_video` (user provides a YouTube URL)
- `article_url` (user provides a URL to a page/article)
- `text_paste` (user pastes text)
- `screenshot` (user uploads an image)

### Source Isolation (critical)
**Rule:** Each source MUST be extracted in a separate isolated LLM call. No cross-source reasoning during extraction.

Cross-source reasoning is permitted only in Synthesis.

---

## 2) IDs and Reference Integrity

### ID formats
| Entity | Format | Example |
|--------|--------|---------|
| Source | `SRC_N` | `SRC_1` |
| Quote | `QT_N` | `QT_14` |
| Observation | `OBS_N` | `OBS_9` |
| Claim | `CLM_N` | `CLM_2` |
| Key Point | `KP_N` | `KP_6` |
| Theme | `THEME_N` | `THEME_3` |
| Tension | `TEN_N` | `TEN_1` |
| Gap | `GAP_N` | `GAP_5` |

### Referential integrity invariant
Any field that references another object MUST reference a valid ID that exists in the same job artifacts.

---

## 3) Analysis Modes (canonical)

### analysis_mode
Defines how the source was obtained and what extraction can safely do.

| Mode | Meaning |
|------|---------|
| `transcript_grounded` | Video transcript obtained via Supadata or Whisper |
| `caption_grounded` | Video transcript obtained from YouTube captions only |
| `video_only` | No transcript/captions available; video could not be converted into text |
| `article_fetched` | Full article text fetched from URL |
| `text_provided` | User pasted text |
| `ocr_extracted` | Screenshot converted to text via OCR |

### Confidence ceiling
Maximum confidence allowed for any extracted item from that source.

| Mode | confidence_ceiling |
|------|-------------------|
| `transcript_grounded` | `high` |
| `caption_grounded` | `medium` |
| `video_only` | `low` |
| `article_fetched` | `high` |
| `text_provided` | `medium` |
| `ocr_extracted` | `medium` |

**Ceiling rule:** any extracted item’s confidence MUST NOT exceed the source’s ceiling.

---

## 4) Provenance (how text was obtained)

### transcript_provenance
Stored for video sources.

Fields:
- `method`: `supadata | whisper | youtube_captions | none`
- `quality`: `high | medium | low | unavailable`
- `timestamp_reliability`: `precise | approximate | unavailable`
- `acquired_at`: ISO-8601 datetime

**Transcript chain (locked order):**
1) Supadata
2) Whisper
3) YouTube captions
4) None → `video_only`

### ocr_provenance
Stored for screenshot sources.

Fields:
- `method`: `gemini_ocr | tesseract | other`
- `ocr_quality`: `high | medium | low`
- `acquired_at`: ISO-8601 datetime

---

## 5) Quotes vs Observations (critical)

### Quote
A quote is **verbatim wording** as captured by the system.

**Important:** A quote does **not** mean the claim is true. Quotes are about *wording fidelity*, not factual verification.

Quote fields (canonical):
- `quote_id` (QT_N)
- `text`
- `source_id` (single)
- `speaker` (nullable)
- `timestamp` (nullable human form)
- `timestamp_seconds` (nullable integer)
- `accuracy_unverified` (boolean)
- `verbatim_confidence` (`high|medium|low`)
- `provenance` (`user_provided|fetched|derived`)
- `approximate` (boolean)

### Observation
An observation is a **non-verbatim description** of content.

Observation fields (canonical):
- `observation_id` (OBS_N)
- `description`
- `source_id` (single)
- `timestamp` (nullable)
- `approximate` (must be `true`)
- `type` (must be `observation`)

### Mode-based quote rules (authoritative)

| Mode | Quotes allowed? | Rules |
|------|-----------------|------|
| `transcript_grounded` | YES | verbatim, `accuracy_unverified=false`, `verbatim_confidence=high`, `provenance=fetched` |
| `article_fetched` | YES | verbatim, `accuracy_unverified=false`, `verbatim_confidence=high`, `provenance=fetched` |
| `caption_grounded` | YES (approx) | `approximate=true`, `verbatim_confidence=medium`, `provenance=fetched` |
| `text_provided` | YES (unverified) | `accuracy_unverified=true`, `verbatim_confidence=high`, `provenance=user_provided` |
| `ocr_extracted` | YES (unverified) | `accuracy_unverified=true`, `provenance=user_provided`; verbatim_confidence depends on OCR quality |
| `video_only` | **NO (HARD FAIL)** | Any quote present is a hard validation failure |

### Messy OCR demotion rule (authoritative)
If `analysis_mode==ocr_extracted` AND `ocr_quality==low`:
- quotes MUST NOT be emitted
- quote-like lines MUST be converted into observations
- warning MUST be added: `OCR messy: treated quote-like lines as observations; wording is not reliable.`

---

## 6) “No new facts” rule (Docs 1 & 2)

### New fact
Any factual claim, numeric detail, timeline detail, or named entity relationship that is not supported by Doc 0.

**Rule:** Doc 1 and Doc 2 MUST NOT introduce new facts beyond Doc 0.

Allowed in Doc 1 and Doc 2:
- synthesis and interpretation based on Doc 0 items
- calling out gaps
- suggesting next steps

Not allowed:
- adding details not present in Doc 0

---

## 7) Retention and deletion terms

### expires_at
A timestamptz stored on a job after completion.

**Rule:** On completion, set `expires_at = completed_at + 30 days`.

### retention warnings
UI warnings at {7, 3, 1} days remaining.

### hard delete
Delete all job-linked storage objects, then delete the job row.

---

## 8) Document set

- **Doc 0**: Source Ledger (canonical data, no synthesis)
- **Doc 1**: Jump Start (gaps + next steps, no new facts)
- **Doc 2**: Semantic Brief (themes/tensions, no new facts)
- **Doc 3**: Creator Brief (auto-generated core document; the hero — production-ready creative brief)
- **Doc 4**: Producer Packet (optional creative layer; user-triggered; must not modify Doc 0/1/2/3)

---

## 9) Creator Brief

### creator_brief
Doc 3. The hero document automatically generated at the end of every successful pipeline run.

**Purpose:** Distill all research into a creator-ready production brief. The bridge between raw research and content creation.

**Key sections (canonical):**
- `hook_options` — 2 hook options, each referencing a `claim_id` from Doc 2
- `setup` — core theme/thesis derived from synthesis
- `twist` — contradiction or disputed claim from Doc 2 framing
- `core_facts` — 3–5 high-significance claims with plain-English phrasing ("say it like")
- `analogy` — accessible explanation of the core concept
- `personal_stakes` — why this matters to the viewer
- `cliffhanger` — open question or speculative claim
- `description_sources` — formatted for description box copy-paste
- `disputed_claims` — explicit flag for speculative/disputed content

**Provenance requirement:** Every claim_id must exist in Doc 2. Every source_id must exist in Doc 0.

---

## 10) Iterate System

### iterate
The unified system for iterating on a completed job. Replaces: Booster, Addendum, more_sources.

All iterations go through `POST /jobs/{job_id}/iterate` with a `mode` field.

**Iterate modes (canonical):**

| Mode | Description | Formerly |
|------|-------------|---------|
| `deep_dive` | Gap analysis + search directions for current corpus | Booster |
| `expand_sources` | Add new sources and re-run full pipeline | Addendum / more_sources |
| `deeper` | Re-extract existing sources with more depth | (new) |
| `different_angle` | Re-synthesize existing data from a different perspective | (new) |
| `custom` | User-defined freeform instructions | (new) |

**Document versioning:** Each iteration creates new versions of affected documents. Rolling 4-version window per document.

---

## 11) Document Versioning

### document_version (in storage context)
The version number of a document artifact (distinct from `document_version` schema field).

**Format:** Integer, starting at 1. Increments on each iteration that produces a new version of that document.

**Rolling window:** Maximum 4 versions stored per document (latest + 3 previous). On 5th version creation, oldest is deleted.

**Version metadata fields (canonical):**
- `version`: integer
- `created_at`: ISO-8601 datetime
- `trigger`: `initial_run | deep_dive | expand_sources | deeper | different_angle | custom`
- `source_count`: integer
- `claim_count`: integer
- `diff_summary`: human-readable change description (e.g., "+3 sources, +12 claims")

---

**END**

