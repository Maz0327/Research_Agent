# E2E Verification: Document Accordion UI Flow

**Date:** 2026-01-21
**Scope:** Verify job completion → UI shows Doc0/1/2 → expand loads content → PDF works

---

## Contract Table

### A. Job Payload: Artifacts Doc Paths

| Layer | Key Names | Evidence |
|-------|-----------|----------|
| **Backend Model** | `doc_0_path`, `doc_1_path`, `doc_2_path`, `doc_3_path` | `backend/models/job_record.py:23-26` |
| **Backend List** | `artifacts_dict = job.artifacts.model_dump(exclude_none=True)` | `jobs_routes.py:1332` |
| **Backend Detail** | Same as list - uses `get_job()` → JobRecord | `jobs_routes.py:1388` |
| **Frontend Store** | `doc_0_path`, `doc_1_path`, `doc_2_path`, `doc_3_path` | `frontend/store/jobs.ts:129-136` |
| **Frontend UI** | `artifacts?.doc_0_path \|\| artifacts?.doc_1_path \|\| artifacts?.doc_2_path` | `JobResults.tsx:124` |

**Verdict:** ✅ MATCHES — All layers use same field names.

---

### B. Document Fetch Endpoint

| Aspect | Backend | Frontend |
|--------|---------|----------|
| **Route** | `GET /jobs/{job_id}/documents/{doc_type}` | `authFetch(\`/jobs/${jobId}/documents/${docKey}\`)` |
| **Valid Keys** | `{"doc_0", "doc_1", "doc_2", "doc_3"}` | `type DocKey = 'doc_0' \| 'doc_1' \| 'doc_2' \| 'doc_3'` |
| **Response (storage)** | `{"url": "signed_url", "expires_in": 3600}` | Expects `result.url` |
| **Response (inline)** | `{"data": {...}, "markdown": "..."}` | Falls back to `result.markdown` |
| **Evidence** | `jobs_routes.py:944-1046` | `DocumentAccordion.tsx:104-129` |

**Verdict:** ✅ MATCHES — Endpoint route, docKey values, and response shapes align.

---

### C. Document Storage Format

| Aspect | Value | Evidence |
|--------|-------|----------|
| **Storage Path** | `{job_id}/doc_{n}.json` | `supabase_storage.py:177` |
| **Content Structure** | `{"data": {...}, "markdown": "..."}` | `initialization.py:39-41, 47-49, 55-57, 63-65` |
| **Frontend Extraction** | `content.markdown` from fetched JSON | `DocumentAccordion.tsx:117-118` |

**Verdict:** ✅ MATCHES — Stored format has `markdown` field that frontend expects.

---

### D. UI Detection Logic

| Check | Code | Evidence |
|-------|------|----------|
| **Has storage docs** | `artifacts?.doc_0_path \|\| artifacts?.doc_1_path \|\| artifacts?.doc_2_path` | `JobResults.tsx:124` |
| **Has inline docs** | `artifacts?.source_ledger \|\| artifacts?.jump_start \|\| artifacts?.semantic_brief` | `JobResults.tsx:123` |
| **Combined check** | `hasDocuments = hasInlineDocuments \|\| hasStorageDocuments` | `JobResults.tsx:125` |
| **Render condition** | `isCompleted && hasDocuments` | `JobResults.tsx:133` |

**Verdict:** ✅ CORRECT — Checks both storage paths and inline data for backward compatibility.

---

### E. PDF Export

| Aspect | Value | Evidence |
|--------|-------|----------|
| **Utility** | `exportToPdf(markdown, filename)` | `frontend/lib/pdf-export.ts:12` |
| **Trigger** | `handleDownloadPdf` in accordion | `DocumentAccordion.tsx:162-171` |
| **Content source** | Uses loaded `markdown` state | `DocumentAccordion.tsx:164` |
| **Enabled when** | Only when `markdown` is loaded | `DocumentAccordion.tsx:192` |

**Verdict:** ✅ CORRECT — PDF export uses loaded markdown content.

---

## Full Data Flow

```
1. Pipeline completes
   └─ initialization.py uploads docs to Supabase Storage
   └─ Sets artifacts.doc_0_path, doc_1_path, doc_2_path
   └─ Stores: {data: {...}, markdown: "..."}

2. Frontend fetches jobs
   └─ GET /jobs → returns artifacts with doc_X_path fields
   └─ JobResults checks: hasStorageDocuments = doc_0_path || doc_1_path || doc_2_path

3. User expands accordion
   └─ DocumentAccordion calls GET /jobs/{id}/documents/doc_0
   └─ Backend returns {url: "signed_url"}
   └─ Frontend fetches signed URL → gets JSON → extracts .markdown

4. User clicks PDF
   └─ exportToPdf(markdown, filename)
   └─ Uses html2pdf.js to generate and download
```

---

## Evidence Summary

| File | Lines | What it proves |
|------|-------|----------------|
| `backend/models/job_record.py` | 23-26 | Artifacts model has doc_X_path fields |
| `backend/app/routes/jobs_routes.py` | 1332 | List endpoint returns artifacts via model_dump |
| `backend/app/routes/jobs_routes.py` | 944-1046 | Document endpoint accepts doc_0/1/2/3, returns URL or inline |
| `backend/pipeline/stages/initialization.py` | 39-67 | Documents uploaded with {data, markdown} structure |
| `frontend/store/jobs.ts` | 129-136 | JobArtifacts interface has doc_X_path fields |
| `frontend/components/job-card/JobResults.tsx` | 123-125 | Detection checks both storage paths and inline |
| `frontend/components/job-card/DocumentAccordion.tsx` | 104-118 | Fetches from /documents/{docKey}, extracts .markdown |
| `frontend/lib/pdf-export.ts` | 12-57 | exportToPdf converts markdown to PDF |

---

## Verdict

**✅ End-to-end document display flow is CORRECT.**

All contracts align:
1. Backend returns `doc_0_path`, `doc_1_path`, `doc_2_path` in artifacts
2. Frontend checks these fields to show accordions
3. Document endpoint accepts `doc_0`, `doc_1`, `doc_2`, `doc_3`
4. Stored JSON has `markdown` field that frontend extracts
5. PDF export uses the loaded markdown

**No fixes needed.**

---

## Potential Edge Cases (Not Bugs)

1. **Empty markdown**: If `ctx.outputs.get("source_ledger_md")` is None, stored document will have `"markdown": null`. Frontend handles this: `content.markdown || null` → shows "No content available".

2. **Legacy inline jobs**: Old jobs without storage paths fall back to inline data (`source_ledger`, `jump_start`, etc.). Frontend handles both paths correctly.

3. **Storage failure**: If signed URL fetch fails, error is shown in accordion. No silent failure.

---

*Report generated: 2026-01-21*
