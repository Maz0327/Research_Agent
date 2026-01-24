# Producer Pack & Booster Expansion Document Bug

**Date:** 2026-01-24
**Debugger ID:** aba42dd
**Priority:** HIGH — User-facing feature broken

---

## Executive Summary

**Issue:** Producer Pack (Doc 3) and Booster expansion markdown are not displaying in frontend despite successful generation and storage in backend.

**Root Cause:** Document retrieval endpoint `/jobs/{job_id}/documents/{doc_type}` does NOT support inline markdown fields (`producer_packet_md`, `booster_expansion_md`). It only handles:
1. Storage paths (new jobs)
2. Inline data with `{data, markdown}` structure (legacy jobs)

**Impact:**
- Users cannot view Producer Pack content
- Booster expansion content is invisible
- Both tasks complete successfully but output is inaccessible

---

## Technical Analysis

### 1. Document Generation ✅ WORKING

**Booster Task** (`backend/worker.py:1351-1450`):
```python
# Line 1378: Booster expansion markdown is generated
expansion_md = build_booster_expansion_markdown(booster_output)

# Line 1378: Stored in artifacts
updated_artifacts["booster_expansion_md"] = expansion_md
```

**Producer Task** (`backend/worker.py:1584-1610`):
```python
# Line 1586: Producer markdown is generated
artifacts_dict["producer_packet_md"] = packet.to_markdown()

# Line 1608-1610: Stored in artifacts using partial_artifacts
partial_artifacts={
    "producer_packet": artifacts_dict.get("producer_packet"),
    "producer_packet_md": artifacts_dict.get("producer_packet_md"),
}
```

**Verdict:** ✅ Generation and storage work correctly.

---

### 2. Database Schema ✅ CORRECT

**Artifacts Model** (`backend/models/job_record.py:100-106`):
```python
# Booster (Doc 1 expansion)
booster_output: Optional[dict[str, Any]] = Field(None, description="Booster output for Doc 1 expansion")
booster_expansion_md: Optional[str] = Field(None, description="Booster markdown for Doc 1")

# Producer Packet (Doc 3)
producer_packet: Optional[dict[str, Any]] = Field(None, description="Doc 3 - Producer Packet (inline)")
producer_packet_md: Optional[str] = Field(None, description="Doc 3 markdown output")
```

**Verdict:** ✅ Schema supports both fields.

---

### 3. Document Retrieval Endpoint ❌ BUG FOUND

**Endpoint:** `GET /jobs/{job_id}/documents/{doc_type}` (`backend/app/routes/jobs_routes.py:944-1046`)

**Current Logic:**
```python
# Line 1007-1012: Mapping for doc types
doc_mapping = {
    "doc_0": {"path_field": "doc_0_path", "inline_field": "source_ledger"},
    "doc_1": {"path_field": "doc_1_path", "inline_field": "jump_start"},
    "doc_2": {"path_field": "doc_2_path", "inline_field": "semantic_brief"},
    "doc_3": {"path_field": "doc_3_path", "inline_field": "producer_packet"},  # ❌ WRONG
}

# Line 1036-1044: Returns inline data
if inline_data:
    if isinstance(inline_data, dict):
        return {
            "data": inline_data.get("data", inline_data),
            "markdown": inline_data.get("markdown"),  # ❌ WRONG for doc_3
        }
```

**Problems:**

1. **Doc 3 mapping is wrong:**
   - Maps to `producer_packet` (dict with structured data)
   - Should check `producer_packet_md` (string with markdown)
   - Current code looks for `producer_packet.markdown` (doesn't exist)

2. **No booster support:**
   - Endpoint doesn't recognize `doc_type="booster"`
   - Frontend calls `/documents/booster` but endpoint rejects it
   - Valid types only: `{"doc_0", "doc_1", "doc_2", "doc_3"}` (line 966)

3. **Inline markdown not accessed:**
   - For producer: `producer_packet` is a dict, not `{data, markdown}` structure
   - Markdown is in separate field: `producer_packet_md`
   - For booster: `booster_expansion_md` is a flat string, not nested

---

### 4. Frontend Fetching ✅ CORRECT INTENT

**DocumentCardGrid.tsx** (`frontend/components/job-card/DocumentCardGrid.tsx:278-304`):
```typescript
// Line 278: Fetch function calls backend
const fetchDocument = useCallback(async (docKey: string): Promise<string | null> => {
    const response = await authFetch(`/jobs/${jobId}/documents/${docKey}`, token);
    const result = await parseJsonResponse<DocumentApiResponse>(response);

    // Line 292: Expects markdown in response
    return result.markdown || null;
}, [jobId]);

// Line 312-320: Booster handling (inline only)
if (config.key === 'booster') {
    const content = boosterMarkdown || artifacts?.booster_expansion_md;
    if (content) {
        setDocContent({ markdown: content, data: {} });
        setModalOpen(true);
    }
    return;
}
```

**Problems:**

1. **Booster fails API call:**
   - Frontend tries `/documents/booster`
   - Backend rejects with 400 (invalid doc_type)
   - Frontend fallback works (uses inline `booster_expansion_md`)
   - **BUT** inline data not always passed down from JobCard

2. **Doc 3 gets empty markdown:**
   - Frontend calls `/documents/doc_3`
   - Backend returns `producer_packet` dict
   - Frontend extracts `result.markdown` → `null`
   - Modal opens with empty content

---

## Root Causes Summary

| Component | Issue | Severity |
|-----------|-------|----------|
| **Document Endpoint** | `doc_3` mapped to wrong field (`producer_packet` instead of `producer_packet_md`) | **CRITICAL** |
| **Document Endpoint** | No support for `booster` doc_type | **HIGH** |
| **Document Endpoint** | Doesn't handle flat markdown fields (`*_md`) | **HIGH** |
| **Frontend Props** | `boosterMarkdown` not always passed from JobCard | **MEDIUM** |

---

## Affected Files

### Backend
1. **`backend/app/routes/jobs_routes.py`** (lines 944-1046)
   - Document retrieval endpoint
   - Missing booster support
   - Wrong mapping for doc_3
   - Doesn't access `*_md` fields

### Frontend
2. **`frontend/components/job-card/DocumentCardGrid.tsx`** (lines 278-364)
   - Fetches from broken endpoint
   - Has fallback for booster (works if prop passed)
   - No fallback for doc_3

3. **`frontend/components/JobCard.tsx`**
   - May not pass `boosterMarkdown` prop consistently

---

## Recommended Fixes

### Fix 1: Update Document Endpoint Mapping (CRITICAL)

**File:** `backend/app/routes/jobs_routes.py`
**Lines:** 1007-1012, 1036-1046

**Current:**
```python
doc_mapping = {
    "doc_0": {"path_field": "doc_0_path", "inline_field": "source_ledger"},
    "doc_1": {"path_field": "doc_1_path", "inline_field": "jump_start"},
    "doc_2": {"path_field": "doc_2_path", "inline_field": "semantic_brief"},
    "doc_3": {"path_field": "doc_3_path", "inline_field": "producer_packet"},
}
```

**Fix:**
```python
doc_mapping = {
    "doc_0": {
        "path_field": "doc_0_path",
        "inline_field": "source_ledger",
        "markdown_field": None  # Has markdown nested
    },
    "doc_1": {
        "path_field": "doc_1_path",
        "inline_field": "jump_start",
        "markdown_field": None  # Has markdown nested
    },
    "doc_2": {
        "path_field": "doc_2_path",
        "inline_field": "semantic_brief",
        "markdown_field": None  # Has markdown nested
    },
    "doc_3": {
        "path_field": "doc_3_path",
        "inline_field": "producer_packet",
        "markdown_field": "producer_packet_md"  # Flat markdown field
    },
    "booster": {
        "path_field": None,
        "inline_field": "booster_output",
        "markdown_field": "booster_expansion_md"  # Flat markdown field
    },
}

# Update fallback logic (line 1036)
if inline_data:
    # Check for flat markdown field first
    if mapping.get("markdown_field"):
        flat_markdown = artifacts_dict.get(mapping["markdown_field"])
        if flat_markdown:
            return {"data": inline_data, "markdown": flat_markdown}

    # Fallback to nested markdown
    if isinstance(inline_data, dict):
        return {
            "data": inline_data.get("data", inline_data),
            "markdown": inline_data.get("markdown"),
        }
```

**Expected Behavior:**
- `GET /documents/doc_3` → returns `producer_packet_md` markdown
- `GET /documents/booster` → returns `booster_expansion_md` markdown
- Backward compatible with existing doc_0/1/2 logic

---

### Fix 2: Update Valid Doc Types (HIGH)

**File:** `backend/app/routes/jobs_routes.py`
**Line:** 966

**Current:**
```python
valid_doc_types = {"doc_0", "doc_1", "doc_2", "doc_3"}
```

**Fix:**
```python
valid_doc_types = {"doc_0", "doc_1", "doc_2", "doc_3", "booster"}
```

---

### Fix 3: Verify Frontend Props (MEDIUM)

**File:** `frontend/components/JobCard.tsx`

**Verify:**
- `boosterMarkdown` prop is passed to DocumentCardGrid
- Prop value is `job.artifacts?.booster_expansion_md`

**If missing, add:**
```typescript
<DocumentCardGrid
  // ... other props
  boosterMarkdown={job.artifacts?.booster_expansion_md}
/>
```

---

## Verification Steps

1. **Test Producer Pack:**
   - Trigger producer packet on completed job
   - Wait for `producer_status: "completed"`
   - Click "Producer Packet" card
   - Verify markdown renders in modal

2. **Test Booster:**
   - Trigger booster on completed job
   - Wait for `booster_status: "completed"`
   - Click "Deep Research" card
   - Verify expansion markdown renders in modal

3. **Test API Directly:**
   ```bash
   # Get job with producer/booster completed
   curl -H "Authorization: Bearer $TOKEN" \
     https://api.example.com/jobs/{job_id}

   # Test doc_3 endpoint
   curl -H "Authorization: Bearer $TOKEN" \
     https://api.example.com/jobs/{job_id}/documents/doc_3
   # Should return: {"data": {...}, "markdown": "# Producer Packet\n..."}

   # Test booster endpoint
   curl -H "Authorization: Bearer $TOKEN" \
     https://api.example.com/jobs/{job_id}/documents/booster
   # Should return: {"data": {...}, "markdown": "## Deep Research Expansion\n..."}
   ```

---

## Evidence

### Backend Storage (Confirmed Working)
- Booster: `worker.py:1378` stores `booster_expansion_md`
- Producer: `worker.py:1610` stores `producer_packet_md` via `partial_artifacts`

### Database Schema (Confirmed Correct)
- `job_record.py:102` defines `booster_expansion_md: Optional[str]`
- `job_record.py:106` defines `producer_packet_md: Optional[str]`

### Endpoint Mapping (Confirmed Broken)
- `jobs_routes.py:1011` maps `doc_3` to `producer_packet` (dict, not markdown)
- `jobs_routes.py:966` excludes `booster` from valid types
- `jobs_routes.py:1042` returns `inline_data.get("markdown")` → `None` for both

### Frontend Fetch (Confirmed Affected)
- `DocumentCardGrid.tsx:280` calls `/documents/{docKey}`
- `DocumentCardGrid.tsx:293` expects `result.markdown`
- Gets `null` for both producer and booster (when using API)

---

## Unresolved Questions

1. **Drive Upload Removal:**
   - Line 1620 comment: "Drive upload removed (2026-01-19 - Doc 3 stored in artifacts)"
   - Was `doc_3_path` supposed to be used? Or always inline?
   - If always inline, why have `doc_3_path` in schema?

2. **Booster Storage Path:**
   - No `booster_path` field in artifacts
   - Booster always stored inline
   - Should it use storage for large expansions?

3. **Legacy Jobs:**
   - Do any existing jobs have `doc_3_path` set?
   - If yes, endpoint must handle both paths

---

## Recommended Action

**Immediate:** Apply Fix 1 + Fix 2 to backend endpoint
**Priority:** HIGH
**Effort:** 30 minutes
**Risk:** LOW (backward compatible)
**Testing:** Manual verification on staging with completed jobs

**Next:** Verify Fix 3 for frontend props
**Priority:** MEDIUM
**Effort:** 10 minutes
