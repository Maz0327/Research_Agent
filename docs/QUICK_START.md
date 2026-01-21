# QUICK START (Convenience Summary)

> **Authoritative spec lives at `docs/authoritative/INDEX.md`.** This document is a **non-authoritative convenience summary**. If anything conflicts with the authoritative spec, **the authoritative spec wins**.

---

## What this repo is

This system is a **semantic-only research pipeline** that:

- accepts user-provided sources (YouTube URL, URL, pasted text, screenshots)
- extracts per-source information in **isolated calls**
- produces **Doc 0 / Doc 1 / Doc 2** (and optional **Doc 3**)
- stores docs in **job artifacts** and optionally in **Supabase Storage** for lazy loading / downloads

There are **no Slack endpoints** and **no Google Drive exports**.

---

## The only user flow (UI)

The UI has exactly one entry point:

1. Click **Add Source**
2. Pick one:
   - **YouTube URL**
   - **URL**
   - **Paste Text**
   - **Upload Screenshot**
3. The system creates (or updates) a job and processes sources.

**Important:** Users should not see separate “pipelines” or a “video analysis job.”

---

## API: the endpoints you should use

> Exact endpoint contract is defined in `docs/authoritative/spec/API_Contract.md`.

### Create job (implicit creation on first source)

- `POST /jobs/mixed-input`

This is the single job creation endpoint. Even if you only submit one source, the payload shape is mixed-input.

### Add more sources to an existing job

- `POST /jobs/{job_id}/sources`

Then process newly added sources using the system’s evolving-job mechanism:

- `POST /jobs/{job_id}/process-pending` *(or the repo’s current equivalent endpoint if named differently)*

### Read job state + outputs

- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/manifest`
- `GET /jobs/{job_id}/doc/{doc_id}`  (lazy-load doc content)
- `GET /jobs/{job_id}/attachments`
- `GET /jobs/{job_id}/attachments/{filename}`
- `GET /jobs/{job_id}/download.pdf` (on-demand PDF generation)

### Optional boosters

- `POST /jobs/{job_id}/booster` (Deep Research Booster)
- `POST /jobs/{job_id}/producer-packet` (Doc 3)

### User actions

- `POST /jobs/{job_id}/cancel`
- `POST /jobs/{job_id}/archive`
- `DELETE /jobs/{job_id}`

---

## Endpoints that MUST be gone (410)

These endpoints are deprecated and must return **410 Gone**:

- `POST /jobs`
- `POST /jobs/preview`
- `POST /jobs/{job_id}/select-interpretation`
- `POST /jobs/video-analysis`

Also deprecated:

- any Slack endpoints
- any Google Drive export endpoints

---

## What the system outputs

### Doc 0 — Source Ledger (canonical)

- Per-source identity + provenance
- Quotes / observations / claims
- No synthesis

### Doc 1 — Jump Start

- Gaps + next steps
- No new facts beyond Doc 0

### Doc 2 — Semantic Brief

- Themes + tensions + key points
- No new facts beyond Doc 0

### Doc 3 — Producer Packet (optional)

- Creative layer / narrative angles
- Must not modify Docs 0–2

Doc definitions and required JSON shapes live in:

- `docs/authoritative/spec/Document_Output_Format.md`

---

## Storage model (Option B)

- Canonical doc content is stored in `job.artifacts` JSON.
- Exports/attachments (PDF/zip) may be stored in Supabase Storage.
- The frontend **lazy-loads** docs via the `/doc/{doc_id}` endpoint.
- PDF generation is on-demand via `GET /jobs/{job_id}/download.pdf`.

Details:

- `docs/authoritative/spec/RASS.md`
- `docs/authoritative/spec/Retention_and_Deletion.md`

---

## Running locally (developer)

### Requirements

- Python 3.11+ recommended
- Redis for Celery (local) or a hosted Redis provider

### Environment

Copy `.env.example` → `.env` and set required variables.

Minimum typical variables:

- `DATABASE_URL` or Supabase connection vars
- `REDIS_URL`
- model provider keys (Gemini/OpenAI) used by your configured clients
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (for storage)

### Start API

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Start worker

```bash
celery -A backend.worker worker --loglevel=INFO
```

---

## Guardrails you should know

- **Source isolation:** each source extracted in its own call
- **Transcript chain order:** Supadata → Whisper → YouTube captions → video\_only
- **video\_only:** quotes are forbidden (hard fail)
- **text\_provided & ocr\_extracted:** quotes allowed but must be marked `accuracy_unverified=true`
- **messy OCR:** demote quote-like text to observations

See:

- `docs/authoritative/spec/Operational_Definitions.md`
- `docs/authoritative/spec/OCR_Quality_and_Quote_Demotion.md`
- `docs/authoritative/spec/Validation_and_Retry_Rules.md`

---

## If something seems off

Stop and consult `docs/authoritative/INDEX.md`.

**END**

