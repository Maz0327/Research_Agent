# Troubleshooting (Convenience Summary)

> **Authoritative spec lives at `docs/authoritative/INDEX.md`.**
> This document is a **non-authoritative convenience summary**. If anything conflicts with the authoritative spec, **the authoritative spec wins**.

This file intentionally focuses on common operational issues without redefining the system.

---

## 1) API won’t start

### Symptoms
- Uvicorn fails to start
- Import errors
- Missing environment variables

### Checks
1) Confirm you have a virtualenv and dependencies installed.
2) Confirm `.env` exists and contains required values.

Common missing vars:
- Redis: `REDIS_URL`
- Supabase: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- Model providers: e.g., Gemini/OpenAI keys as required by your configured clients

---

## 2) Worker won’t start

### Symptoms
- Celery worker exits
- Cannot connect to Redis

### Checks
- Verify Redis is reachable from worker:
  - local: `redis://localhost:6379/0`
  - cloud: verify URL and firewall rules
- Verify the Celery app import path is correct.

---

## 3) Jobs get stuck in running

### Typical causes
- Worker died mid-run
- Redis dropped connection
- Provider API request failed repeatedly

### What to do
- Check worker logs for the job_id.
- Verify retry/degradation rules are working (job should degrade rather than die if some sources fail).

See authoritative failure semantics:
- `docs/authoritative/spec/Validation_and_Retry_Rules.md`

---

## 4) “video_only mode forbids quotes” hard fail

### Meaning
A video source ended up in `video_only` mode (no transcript/captions available), but the extraction produced quotes.

### Fix
- Ensure transcript acquisition is working (Supadata/Whisper/captions).
- Ensure `video_only` extraction prompt disallows quotes and only allows observations.

Mode rules:
- `docs/authoritative/spec/modes/video_only.md`

---

## 5) Screenshot OCR looks wrong / garbled

### Meaning
The OCR quality may be `low`.

### Expected behavior
If OCR is messy (low quality):
- quote-like text must be treated as observations
- a warning must be attached

See:
- `docs/authoritative/spec/OCR_Quality_and_Quote_Demotion.md`

---

## 6) Frontend gets 410 Gone errors

### Meaning
Frontend is calling deprecated endpoints.

### Correct action
Update frontend to use only the allowed endpoints in:
- `docs/authoritative/spec/API_Contract.md`

Deprecated endpoints that must remain 410:
- `POST /jobs`
- `POST /jobs/preview`
- `POST /jobs/{id}/select-interpretation`
- `POST /jobs/video-analysis`

---

## 7) PDF download fails

### Symptoms
- `GET /jobs/{id}/download.pdf` returns 500

### Checks
- Verify the job has artifacts for Docs 0–2 (and Doc 3 if requested).
- Verify PDF generation dependencies are installed.
- Check storage permissions if PDF is stored as an attachment.

---

## 8) Supabase storage permission errors

### Symptoms
- cannot upload screenshots
- cannot download attachments

### Checks
- Ensure buckets exist:
  - `screenshots` (private)
  - `documents` (private)
- Ensure service role key is configured on the backend.

Note: the documents bucket may need MIME allowlist support for JSON, PDF, and zip if you store exports there.

---

## 9) Retention cleanup not running

### Expected behavior
- Jobs expire 30 days after completion.
- UI shows countdown and warnings at {7,3,1} days.
- Cleanup is triggered daily by a cron hitting the maintenance endpoint.

See:
- `docs/authoritative/spec/Retention_and_Deletion.md`

---

**END**

