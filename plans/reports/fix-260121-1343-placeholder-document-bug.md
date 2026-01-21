# Fix Report: Placeholder Document Display Bug

**Date:** 2026-01-21 13:43
**Issue:** UI/PDFs show placeholder text instead of real document content from storage

---

## Root Cause

**Two-part problem:**

### 1. Backend wrote placeholder markdown to inline fields (lines 287-306)
```python
# backend/pipeline/stages/initialization.py
inline_stub_md = "# Document Available via Cloud Storage..."
artifacts_dict["source_ledger"] = {"data": {}, "markdown": inline_stub_md}
```

### 2. Frontend used inline data without checking if it's a placeholder
```typescript
// frontend/components/job-card/DocumentAccordion.tsx:93,146
const [markdown, setMarkdown] = useState(inlineMarkdown ?? null);
if (markdown) return;  // Never fetched from storage!
```

**Flow:**
1. Worker uploads docs to Supabase Storage → stores `doc_0_path`, `doc_1_path`, `doc_2_path`
2. Completion stage ALSO writes placeholder markdown to `source_ledger.markdown`, etc.
3. Frontend receives job with both storage paths AND placeholder inline content
4. DocumentAccordion initializes with placeholder markdown, thinks it has real content
5. On expand, `if (markdown) return` skips API fetch → user sees placeholder
6. PDF export exports the placeholder text

---

## Fixes Applied

### A. Frontend: `DocumentAccordion.tsx`

**File:** `frontend/components/job-card/DocumentAccordion.tsx`

| Line | Change |
|------|--------|
| 15-24 | Added `hasStoragePath` prop to interface |
| 84-99 | Added `isPlaceholderContent()` helper function |
| 100-117 | Component now checks placeholder detection and storage path |
| 137-160 | `handleToggle()` forces fetch when storage path exists |
| 162-177 | `handleDownloadPdf()` blocks export of placeholder content |
| 192-202 | PDF button only shows for exportable (non-placeholder) content |

**Key logic:**
```typescript
function isPlaceholderContent(content: string | null | undefined): boolean {
  if (!content) return true;
  return (
    content.includes('Document Available via Cloud Storage') ||
    content.includes('inline JSON omitted')
  );
}

// Only use inline markdown if: (1) no storage path AND (2) not a placeholder
const initialMarkdown = (!hasStoragePath && !inlineIsPlaceholder) ? (inlineMarkdown ?? null) : null;
```

### B. Frontend: `JobResults.tsx`

**File:** `frontend/components/job-card/JobResults.tsx`

| Line | Change |
|------|--------|
| 189-191 | Added `hasStoragePath={!!artifacts?.doc_0_path}` to Doc 0 |
| 201-203 | Added `hasStoragePath={!!artifacts?.doc_1_path}` to Doc 1 |
| 213-215 | Added `hasStoragePath={!!artifacts?.doc_2_path}` to Doc 2 |
| 223-225 | Added `hasStoragePath={!!artifacts?.doc_3_path}` to Doc 3 |

### C. Backend: `initialization.py`

**File:** `backend/pipeline/stages/initialization.py`

| Line | Change |
|------|--------|
| 281-291 | Removed placeholder markdown generation; storage paths only |

**Before:**
```python
if storage_paths:
    artifacts_dict = dict(storage_paths)
    inline_stub_md = "# Document Available via Cloud Storage..."
    artifacts_dict["source_ledger"] = {"data": {}, "markdown": inline_stub_md}
    # ... same for jump_start, semantic_brief
```

**After:**
```python
if storage_paths:
    # Only store paths. NO placeholder markdown.
    artifacts_dict = dict(storage_paths)
```

---

## Tests Added

**File:** `backend/tests/test_pipeline_stages.py`

Added `test_completion_no_placeholder_markdown_when_storage_exists()`:
- Verifies `doc_0_path`, `doc_1_path`, `doc_2_path` are present
- Verifies NO "Document Available via Cloud Storage" in any inline field
- Verifies NO "inline JSON omitted" in any inline field

---

## Validation

```bash
# Backend tests (all 13 pass)
pytest backend/tests/test_pipeline_stages.py -v
# ✓ test_completion_no_placeholder_markdown_when_storage_exists PASSED

# Frontend lint
npm run lint
# ✓ No ESLint warnings or errors

# Frontend build
npm run build
# ✓ Build successful
```

---

## Prevention

1. **Backend rule:** When storage upload succeeds, do NOT populate inline markdown fields
2. **Frontend rule:** When `doc_X_path` exists, ALWAYS fetch from API, ignore inline
3. **Frontend safety:** Detect placeholder patterns and refuse to export as PDF

---

## Files Changed

| File | Lines Changed |
|------|---------------|
| `frontend/components/job-card/DocumentAccordion.tsx` | +40, -10 |
| `frontend/components/job-card/JobResults.tsx` | +4 |
| `backend/pipeline/stages/initialization.py` | -16 |
| `backend/tests/test_pipeline_stages.py` | +50 |

---

## Deploy Instructions

1. Push changes to trigger CI
2. Verify Railway API redeploys
3. Verify Vercel frontend redeploys
4. Test with existing job that has `doc_X_path` set in DB
