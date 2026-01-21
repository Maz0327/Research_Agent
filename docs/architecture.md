# Architecture (Convenience Summary)

> **Authoritative spec lives at `docs/authoritative/INDEX.md`.**
> This document is a **non-authoritative convenience summary**. If anything conflicts with the authoritative spec, **the authoritative spec wins**.

---

## 1) High-level system overview

This repo contains a semantic-only research system with:
- **FastAPI API service** (request handling, job state, read endpoints)
- **Celery worker** (long-running pipeline execution)
- **Supabase Postgres** (job records, config, artifacts)
- **Supabase Storage** (uploads and generated exports)

There is exactly one reachable pipeline: **semantic pipeline**.

---

## 2) Data model (jobs)

A `job` is the unit of work.

### Job inputs
Jobs are **mixed-input** only (even for one source):
- YouTube URLs
- Article URLs
- Pasted text
- Uploaded screenshots

The canonical shape lives in:
- `docs/authoritative/spec/Job_Config_Schema.md`

### Job outputs
Docs:
- Doc 0: Source Ledger
- Doc 1: Jump Start
- Doc 2: Semantic Brief
- Doc 3: Producer Packet (optional)

Canonical output shapes live in:
- `docs/authoritative/spec/Document_Output_Format.md`

---

## 3) Pipeline stages (semantic-only)

> Stage definitions and failure semantics are authoritative in:
> - `docs/authoritative/spec/RASS.md`
> - `docs/authoritative/spec/Validation_and_Retry_Rules.md`

### Canonical stage intent (summary)
1) **Source identity**: normalize source metadata and determine provenance
2) **Per-source semantic extraction**: isolated extraction call per source
3) **Semantic validation**: enforce quote policy, JSON validity, confidence ceilings
4) **Gap analysis**: identify what the corpus does not cover
5) **Semantic synthesis**: derive themes and tensions without adding new facts
6) **Document assembly**: generate Doc 0/1/2
7) **Completion**: persist artifacts and finalize manifest

### Source isolation
Extraction is **per-source** and **isolated**. Cross-source reasoning occurs only in synthesis.

---

## 4) Transcript acquisition (YouTube)

Canonical order (locked):
1) Supadata
2) Whisper
3) YouTube captions
4) None → `video_only`

Mode mapping:
- Supadata/Whisper → `transcript_grounded`
- YouTube captions → `caption_grounded`
- None → `video_only`

Mode definitions live in:
- `docs/authoritative/spec/modes/INDEX.md`

---

## 5) Quote vs observation enforcement

Canonical rule summary:
- `video_only` → **NO quotes** (hard fail)
- `caption_grounded` → quotes allowed but **approximate**
- `text_provided` and `ocr_extracted` → quotes allowed but **accuracy_unverified=true**
- `ocr_extracted` with `ocr_quality=low` → demote quote-like strings to observations

See:
- `docs/authoritative/spec/Operational_Definitions.md`
- `docs/authoritative/spec/OCR_Quality_and_Quote_Demotion.md`

---

## 6) Storage strategy (Option B)

### Canonical storage
- Core doc content is stored in the DB in `job.artifacts` JSON.
- Supabase Storage is used for:
  - screenshot uploads
  - generated exports (PDF/zip) and any large blobs referenced by manifest

### Lazy loading
The frontend loads docs via:
- `GET /jobs/{job_id}/manifest`
- `GET /jobs/{job_id}/doc/{doc_id}`

PDF is generated on-demand:
- `GET /jobs/{job_id}/download.pdf`

Details live in:
- `docs/authoritative/spec/API_Contract.md`

---

## 7) API surface

This repo intentionally limits API surface. The canonical list is:
- `docs/authoritative/spec/API_Contract.md`

**Deprecated endpoints must return 410 Gone** and must not be used by the frontend.

---

## 8) Retention and deletion

Retention is a hard requirement:
- 30 days from completion
- UI warnings at {7, 3, 1} days remaining
- hard delete removes storage objects then DB row

Canonical spec:
- `docs/authoritative/spec/Retention_and_Deletion.md`

---

## 9) What is explicitly NOT part of this architecture

- No Slack triggers
- No Google Drive exports
- No separate “video analysis job” pipeline
- No multi-pipeline selection UI

If you see docs or code suggesting these exist, treat it as drift.

---

**END**

