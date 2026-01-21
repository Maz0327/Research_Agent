# docs/authoritative/spec/API_Contract.md

**Purpose:** Define the ONLY endpoints the frontend may call, and the endpoints that MUST be unreachable.

**Non‑negotiable:** The frontend must have ONE user entrypoint: **Add source** → 4 source types.

---

## 1) Frontend Allowed Endpoints

### 1.1 Create job (implicit on first source)
- **POST** `/jobs/mixed-input`

**Frontend rule:** The UI MUST NOT expose a separate “Create Job” action.
The first time the user adds a source, the frontend creates a job implicitly using this endpoint.

### 1.2 Add source (single entrypoint)
- **POST** `/jobs/{job_id}/sources`
- **POST** `/jobs/{job_id}/process-pending` *(name may differ in code; if so, alias this behavior to the existing endpoint)*

**Frontend rule:** After the first source, all additional sources MUST go through `/jobs/{job_id}/sources`.

### 1.3 Read job + docs
- **GET** `/jobs/{job_id}`
- **GET** `/jobs/{job_id}/manifest`
- **GET** `/jobs/{job_id}/doc/{doc_id}`
- **GET** `/jobs/{job_id}/attachments`
- **GET** `/jobs/{job_id}/attachments/{filename}`
- **GET** `/jobs/{job_id}/download.pdf`

### 1.4 Optional boosters
- **POST** `/jobs/{job_id}/booster`
- **POST** `/jobs/{job_id}/producer-packet`

### 1.5 User actions
- **POST** `/jobs/{job_id}/cancel`
- **POST** `/jobs/{job_id}/archive`
- **DELETE** `/jobs/{job_id}`

---

## 2) Deprecated Endpoints (MUST return 410 Gone)

These MUST remain unreachable and MUST NOT be called by the frontend:

- **POST** `/jobs`
- **POST** `/jobs/preview`
- **POST** `/jobs/{job_id}/select-interpretation`
- **POST** `/jobs/video-analysis`
- **POST** `/export/google-docs`
- Any Slack endpoints
- Any Google Drive OAuth endpoints

---

## 3) Internal Maintenance Endpoints (NOT for frontend)

### 3.1 Retention cleanup cron
- **POST** `/maintenance/retention/cleanup`

**Auth:** requires header:
- `X-Maintenance-Token: <secret>`

**Server behavior:**
- If token missing/invalid → return `401`.
- If valid → enqueue cleanup task and return `{ queued: true }`.

---

## 4) Reachability Invariant (semantic-only)

There MUST be exactly one reachable pipeline path:
- semantic pipeline triggered by `/jobs/mixed-input` and expanded by `/jobs/{job_id}/sources`.

No reachable endpoint may trigger any legacy pipeline.

---

## 5) Example frontend flow (authoritative)

### 5.1 User adds first source
1) User clicks Add Source
2) User selects one of:
   - YouTube URL
   - URL
   - Paste text
   - Upload screenshot
3) Frontend calls `POST /jobs/mixed-input` with only that source in the payload
4) Frontend receives `job_id`

### 5.2 User adds second source
1) Frontend calls `POST /jobs/{job_id}/sources` to append it
2) Frontend calls `POST /jobs/{job_id}/process-pending` to process new sources

---

**END**

