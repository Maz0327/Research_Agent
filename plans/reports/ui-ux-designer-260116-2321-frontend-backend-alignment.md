# Frontend-Backend Alignment Audit

**Date:** 2026-01-16
**Auditor:** UI/UX Designer Agent
**Branch:** feature/vision-alignment-v1
**Backend Phase:** 10 Complete (948 tests passing)

---

## Executive Summary

The frontend has **partial alignment** with backend capabilities. Core input modes (video, text, screenshot) are implemented, but several Phase 6-8 features are **MISSING** from the UI. The semantic pipeline outputs (Doc 0/1/2/3) are not displayed in the frontend, which still uses the legacy video_analysis artifacts pattern.

### Overall Status

| Category | Status | Priority |
|----------|--------|----------|
| Input Types | Mostly Aligned | - |
| Job Management | Partial | MEDIUM |
| Output Documents | **NOT ALIGNED** | CRITICAL |
| Extended Features | **MISSING** | CRITICAL |
| Analysis Mode Display | **MISSING** | MEDIUM |

---

## 1. Input Types Verification

### 1.1 YouTube Video URL Input
- **Backend:** `POST /jobs/video-analysis`
- **Frontend:** Implemented in `dashboard.tsx` (lines 456-541)
- **Status:** ALIGNED
- **Notes:** Supports multiple URLs, model selection (flash/pro), project title

### 1.2 Text Input Mode
- **Backend:** `POST /jobs/text-input` (50k char limit)
- **Frontend:** Implemented in `dashboard.tsx` (lines 577-762)
- **Status:** ALIGNED
- **Notes:** All metadata fields present (source_label, source_url, author, pub_date, platform_hint, context_note)

### 1.3 Screenshot Upload
- **Backend:** `POST /jobs/screenshot-input` (10MB limit, PNG/JPG/WEBP)
- **Frontend:** Implemented in `dashboard.tsx` (lines 763-917)
- **Status:** ALIGNED
- **Notes:** File validation, platform hints, OCR warning displayed

### 1.4 Article URL Input
- **Backend:** Supported in `POST /jobs/mixed-input` via `article_urls`
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (LOW priority)
- **Recommendation:** Add article URL input as fourth content mode or integrate into mixed mode

### 1.5 Mixed Input (Multiple Source Types)
- **Backend:** `POST /jobs/mixed-input` (max 20 sources)
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (MEDIUM priority)
- **Recommendation:** Add "Mixed Sources" job creation mode with multi-type source builder

### 1.6 Platform Hints Dropdown
- **Backend:** Supports `reddit`, `twitter`, `forum`, `email`, `article`, `other`
- **Frontend:** Implemented in `lib/constants.ts` (PLATFORM_HINTS, SCREENSHOT_PLATFORM_HINTS)
- **Status:** ALIGNED

---

## 2. Job Management Verification

### 2.1 Create New Job
- **Status:** ALIGNED
- **Location:** `dashboard.tsx`, `store/jobs.ts`

### 2.2 View Job Status with Progress
- **Status:** ALIGNED
- **Location:** `JobCard.tsx`, `ProgressBar.tsx`, `StatusBadge.tsx`
- **Notes:** Shows stage, progress_percent, ETA calculation

### 2.3 Cancel Job
- **Status:** ALIGNED
- **Location:** `JobActions.tsx` (lines 100-123)

### 2.4 Delete Job
- **Status:** ALIGNED
- **Location:** `JobActions.tsx` (lines 151-162)

### 2.5 Add Sources to Completed Job (Evolving Jobs)
- **Backend:** `POST /jobs/{job_id}/sources`
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (CRITICAL)
- **Recommendation:** Add "Add Sources" button on completed job cards that opens a modal for adding new sources

### 2.6 Process Pending Sources Button
- **Backend:** `POST /jobs/{job_id}/process-pending`
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (CRITICAL)
- **Recommendation:** Show "Process Pending" button when job has `sources_pending` status

---

## 3. Output Documents Verification

### 3.1 View Doc 0 (Source Ledger)
- **Backend:** Generated in document_assembly.py, stored in artifacts
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (CRITICAL)
- **Current State:** Frontend shows clips/quotes/blueprints/gaps/research tabs only

### 3.2 View Doc 1 (Jump-Start Directions)
- **Backend:** Generated with gaps, research directions, next steps
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (CRITICAL)
- **Notes:** Frontend has `ResearchStarterView` but does not display Doc 1 structure

### 3.3 View Doc 2 (Semantic Brief)
- **Backend:** Generated with themes, key_points, claims, tensions
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (CRITICAL)
- **Notes:** This is the core semantic analysis output

### 3.4 View Doc 3 (Producer Packet)
- **Backend:** `POST /jobs/{job_id}/producer-packet`, gated (4+ sources, 1+ high-confidence)
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (CRITICAL)
- **Recommendation:** Add "Generate Producer Packet" button with gating message if requirements not met

### 3.5 Export Documents
- **Backend:** Multiple export endpoints exist:
  - `GET /jobs/{job_id}/export?format=json|bibtex|ris|chapters|clips|social|brief`
  - `GET /jobs/{job_id}/export/all`
  - `POST /jobs/{job_id}/export/google-docs`
  - `GET /jobs/{job_id}/export/markdown`
- **Frontend:** Partial implementation in `ExportButton.tsx`
  - Google Docs export
  - Markdown download
  - Copy to clipboard
- **Status:** PARTIAL
- **Missing:** JSON export, ZIP export, BibTeX, RIS formats

---

## 4. Extended Features Verification

### 4.1 Trigger Booster Button
- **Backend:** `POST /jobs/{job_id}/booster`
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (CRITICAL)
- **Recommendation:** Add "Run Deep Research Booster" button on completed jobs

### 4.2 Trigger Producer Packet Button
- **Backend:** `POST /jobs/{job_id}/producer-packet`
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (CRITICAL)
- **Recommendation:** Add button with V10 gating requirements shown (4+ sources, 1+ high-confidence)

### 4.3 View Warnings/Degradation Notices
- **Backend:** Job has `warnings` array, sources can have degraded modes
- **Frontend:** **PARTIAL**
- **Status:** PARTIAL
- **Current:** Shows warning count in status badge
- **Missing:** Detailed warnings list, per-source degradation indicators

---

## 5. Analysis Mode Display Verification

### 5.1 Show Analysis Mode per Source
- **Backend:** Each source has `analysis_mode` (transcript_grounded, video_only, text_provided, ocr_extracted, article_fetched, caption_grounded)
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (MEDIUM)
- **Recommendation:** Display mode badge next to each source

### 5.2 Show Confidence Ceiling per Source
- **Backend:** Each mode has confidence ceiling (HIGH/MEDIUM/LOW)
- **Frontend:** **NOT IMPLEMENTED**
- **Status:** MISSING (MEDIUM)
- **Recommendation:** Show confidence indicator with color coding

### 5.3 Show Quote Verification Status
- **Backend:** Quotes have `verification_status` (verified/partial/unverified) and `match_ratio`
- **Frontend:** Partial in `QuoteList.tsx`
- **Status:** PARTIAL
- **Current:** Shows `quote_verified` boolean
- **Missing:** verification_status enum, match_ratio percentage

---

## 6. Missing API Integrations

### Store (`store/jobs.ts`)

The following methods need to be added:

```typescript
// Evolving Jobs (Phase 6)
addSourcesToJob: (jobId: string, sources: AddSourcesRequest) => Promise<AddSourcesResponse>;
processPendingSources: (jobId: string) => Promise<ProcessPendingResponse>;

// Booster (Phase 7)
triggerBooster: (jobId: string) => Promise<BoosterResponse>;

// Producer Packet (Phase 8)
checkProducerEligibility: (jobId: string) => Promise<EligibilityResponse>;
triggerProducerPacket: (jobId: string) => Promise<ProducerResponse>;

// Documents
getJobDocuments: (jobId: string) => Promise<DocumentsResponse>;
getDocument: (jobId: string, docType: 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3') => Promise<Document>;
```

### Missing API Types

```typescript
interface AddSourcesRequest {
  video_urls?: string[];
  article_urls?: string[];
  text_inputs?: TextInput[];
  process_immediately?: boolean;
}

interface BoosterResponse {
  job_id: string;
  status: string;
  message: string;
}

interface ProducerEligibility {
  eligible: boolean;
  requirements: {
    min_sources: { required: number; actual: number; met: boolean };
    high_confidence_source: { required: number; actual: number; met: boolean };
  };
  message: string;
}
```

---

## 7. Recommended UI Changes

### 7.1 CRITICAL - Add Semantic Documents Viewer

Create new component `SemanticDocumentsView.tsx`:

```
/frontend/components/job-card/SemanticDocumentsView.tsx
```

Features:
- Tab navigation: Source Ledger | Jump-Start | Semantic Brief | Producer Packet
- Collapsible sections for each document part
- Copy/Export buttons per document
- Gating message for Doc 3 if not eligible

### 7.2 CRITICAL - Add Evolving Jobs UI

In `JobActions.tsx`, add:
- "Add Sources" button (visible for completed jobs)
- "Process Pending" button (visible when status = sources_pending)
- Source count badge showing original vs pending

### 7.3 CRITICAL - Add Booster/Producer Buttons

In `JobActions.tsx`, add:
- "Run Booster" button (visible for completed jobs)
- "Generate Producer Packet" button with eligibility check
- Status indicators for running_booster / running_producer

### 7.4 MEDIUM - Add Analysis Mode Indicators

In `JobResults.tsx` or new `SourcesView.tsx`:
- Mode badge per source (e.g., "Transcript" / "Video Only" / "Text")
- Confidence ceiling indicator (color-coded: green=HIGH, yellow=MEDIUM, red=LOW)
- Quote verification rate per source

### 7.5 LOW - Expand Export Options

In `ExportButton.tsx`:
- Add JSON export option
- Add ZIP export (all formats)
- Add BibTeX/RIS for academic use

---

## 8. Files Requiring Modification

| File | Priority | Changes Needed |
|------|----------|----------------|
| `store/jobs.ts` | CRITICAL | Add evolving jobs, booster, producer methods + types |
| `components/job-card/JobResults.tsx` | CRITICAL | Add semantic documents tabs |
| `components/job-card/JobActions.tsx` | CRITICAL | Add booster, producer, add-sources buttons |
| `lib/constants.ts` | MEDIUM | Add new status values, gating constants |
| `components/job-card/ExportButton.tsx` | LOW | Add JSON, ZIP, BibTeX exports |

### New Components Needed

| Component | Priority | Purpose |
|-----------|----------|---------|
| `SemanticDocumentsView.tsx` | CRITICAL | Display Doc 0/1/2/3 |
| `SourceLedgerView.tsx` | CRITICAL | Doc 0 display |
| `JumpStartView.tsx` | CRITICAL | Doc 1 display |
| `SemanticBriefView.tsx` | CRITICAL | Doc 2 display |
| `ProducerPacketView.tsx` | CRITICAL | Doc 3 display |
| `AddSourcesModal.tsx` | CRITICAL | Evolving jobs UI |
| `SourceModeIndicator.tsx` | MEDIUM | Show analysis mode/confidence |
| `WarningsPanel.tsx` | MEDIUM | Detailed warnings display |

---

## 9. Code Snippets

### 9.1 Missing Job Status Values

In `store/jobs.ts`, add to `Job.status`:

```typescript
status: 'queued' | 'running' | 'completed' | 'completed_with_warnings' | 'failed' | 'failed_insufficient' | 'cancelled' | 'disambiguating'
  | 'sources_pending' | 'processing' | 'running_booster' | 'running_producer';
```

### 9.2 Example Booster Trigger

```typescript
// In store/jobs.ts
triggerBooster: async (jobId: string) => {
  const token = await getAccessToken();
  const response = await fetch(`${API_URL}/jobs/${jobId}/booster`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!response.ok) throw new Error('Failed to trigger booster');
  const data = await response.json();
  // Update job status locally
  set((state) => ({
    jobs: state.jobs.map(j =>
      j.id === jobId ? { ...j, status: 'running_booster' } : j
    ),
  }));
  return data;
}
```

---

## 10. Unresolved Questions

1. **Document Storage:** Where are Doc 0/1/2/3 stored in job.artifacts? Need to verify field names.
2. **Booster Re-run:** Can booster be run multiple times? Backend allows with warning.
3. **Producer Re-run:** Same question for producer packet.
4. **Addendum Display:** How should addendum content be displayed when sources are added to completed job?
5. **Cross-Reference Notes:** Should these be shown in a separate tab or inline with sources?

---

## Summary Matrix

| Feature | Backend | Frontend | Gap |
|---------|---------|----------|-----|
| Video input | YES | YES | - |
| Text input | YES | YES | - |
| Screenshot input | YES | YES | - |
| Article URL input | YES | NO | LOW |
| Mixed input | YES | NO | MEDIUM |
| Job CRUD | YES | YES | - |
| Evolving jobs | YES | NO | CRITICAL |
| Doc 0 (Source Ledger) | YES | NO | CRITICAL |
| Doc 1 (Jump-Start) | YES | NO | CRITICAL |
| Doc 2 (Semantic Brief) | YES | NO | CRITICAL |
| Doc 3 (Producer Packet) | YES | NO | CRITICAL |
| Booster trigger | YES | NO | CRITICAL |
| Producer trigger | YES | NO | CRITICAL |
| Analysis mode display | YES | NO | MEDIUM |
| Quote verification | YES | PARTIAL | MEDIUM |
| Export (all formats) | YES | PARTIAL | LOW |

---

**Recommendation:** Prioritize implementing the semantic documents viewer (Doc 0/1/2/3) and the Booster/Producer triggers. These represent the core value of the Phase 7-8 backend work that is currently invisible to users.
