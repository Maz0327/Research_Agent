# Phase 4: Low Priority Issues Implementation

**Priority:** Backlog
**Total Effort:** ~2h
**Issues:** L1-L7

---

## L1: Add Missing Type Hints

**Files:** Multiple extraction files
**Effort:** 30m

### Implementation

Find functions missing return type annotations:
```bash
grep -rn "def " backend/pipeline/ --include="*.py" | grep -v " -> "
```

Add type hints:
```python
# Before
def _extract_quotes(text):
    pass

# After
def _extract_quotes(text: str) -> list[dict[str, Any]]:
    pass
```

---

## L2: Centralize Jina Timeout

**File:** `backend/integrations/jina_reader_client.py`
**Lines:** ~28

### Current Code
```python
timeout = 30  # hardcoded
```

### Implementation
```python
from backend.config import settings

timeout = settings.timeout_api_default  # Use centralized config
```

---

## L3: Split Perplexity Timeouts

**File:** `backend/integrations/perplexity_client.py`
**Lines:** ~18

### Implementation
```python
# Add to config.py
PERPLEXITY_SEARCH_TIMEOUT: int = 30  # Faster for search
PERPLEXITY_EXTRACT_TIMEOUT: int = 120  # Longer for extraction

# Use in client
def search_perplexity(...):
    timeout = settings.PERPLEXITY_SEARCH_TIMEOUT
    ...

def extract_perplexity(...):
    timeout = settings.PERPLEXITY_EXTRACT_TIMEOUT
    ...
```

---

## L4: CSP unsafe-inline

**File:** `frontend/next.config.js`
**Lines:** ~23
**Status:** DEFERRED

### Reason
- Required by Next.js for hydration
- Mitigated by:
  - DOMPurify on all user content
  - Strict CSP on API responses
  - No inline scripts in custom code

### Future Option
When Next.js supports it, migrate to nonces:
```javascript
// Future implementation with nonces
const nonce = generateNonce();
contentSecurityPolicy: `script-src 'nonce-${nonce}'`
```

---

## L5: Add Magic Bytes Validation

**File:** `frontend/components/ScreenshotSourceForm.tsx`
**Effort:** 30m

### Client-Side Implementation
```typescript
const VALID_IMAGE_SIGNATURES: Record<string, number[]> = {
  'image/png': [0x89, 0x50, 0x4e, 0x47],
  'image/jpeg': [0xff, 0xd8, 0xff],
  'image/gif': [0x47, 0x49, 0x46],
  'image/webp': [0x52, 0x49, 0x46, 0x46],
};

async function validateImageMagicBytes(file: File): Promise<boolean> {
  const buffer = await file.slice(0, 4).arrayBuffer();
  const bytes = new Uint8Array(buffer);

  for (const [mimeType, signature] of Object.entries(VALID_IMAGE_SIGNATURES)) {
    if (signature.every((byte, i) => bytes[i] === byte)) {
      return true;
    }
  }
  return false;
}

// In file handler
const handleFileSelect = async (file: File) => {
  if (!await validateImageMagicBytes(file)) {
    setError('Invalid image file');
    return;
  }
  // Process file...
};
```

### Backend Implementation (if needed)
```python
import magic

def validate_image_upload(file_bytes: bytes) -> bool:
    """Validate uploaded file is actually an image."""
    mime = magic.from_buffer(file_bytes, mime=True)
    return mime in ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
```

---

## L6: Whitelist Google Docs URL

**File:** `frontend/components/ExportButton.tsx`
**Lines:** ~61

### Implementation
```typescript
const ALLOWED_EXPORT_DOMAINS = [
  'docs.google.com',
  'drive.google.com',
];

function isAllowedExportUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ALLOWED_EXPORT_DOMAINS.includes(parsed.hostname);
  } catch {
    return false;
  }
}

// Before opening external URL
const handleExport = (url: string) => {
  if (!isAllowedExportUrl(url)) {
    console.error(`Blocked export to unauthorized domain: ${url}`);
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
};
```

---

## L7: Refactor CONFIDENCE_CEILINGS

**File:** `backend/models/semantic_units.py`
**Lines:** ~426
**Effort:** 30m

### Issue
Duplicate `CONFIDENCE_CEILINGS` dict exists to avoid circular import.

### Implementation

1. Create dedicated constants file:
   ```python
   # backend/models/constants.py
   from enum import Enum

   class ConfidenceLevel(str, Enum):
       HIGH = "HIGH"
       MEDIUM = "MEDIUM"
       LOW = "LOW"

   class AnalysisMode(str, Enum):
       TRANSCRIPT_GROUNDED = "transcript_grounded"
       CAPTION_GROUNDED = "caption_grounded"
       VIDEO_ONLY = "video_only"
       TEXT_PROVIDED = "text_provided"
       OCR_EXTRACTED = "ocr_extracted"
       ARTICLE_FETCHED = "article_fetched"

   CONFIDENCE_CEILINGS: dict[AnalysisMode, ConfidenceLevel] = {
       AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,
       AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,
       AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,
       AnalysisMode.TEXT_PROVIDED: ConfidenceLevel.MEDIUM,
       AnalysisMode.OCR_EXTRACTED: ConfidenceLevel.MEDIUM,
       AnalysisMode.ARTICLE_FETCHED: ConfidenceLevel.HIGH,
   }
   ```

2. Update imports in all files:
   ```python
   from backend.models.constants import CONFIDENCE_CEILINGS, ConfidenceLevel, AnalysisMode
   ```

3. Remove duplicates from `semantic_units.py` and other files.

---

## Verification Checklist

After completing Phase 4:
- [ ] `pytest backend/tests/ -v` passes
- [ ] `cd frontend && npm run build && npm run lint` passes
- [ ] No duplicate constants
- [ ] All public functions have type hints
- [ ] Commit: `chore: Code quality improvements (L1-L7)`

---

## Summary

| Issue | Status | Notes |
|-------|--------|-------|
| L1 | TODO | Type hints on helpers |
| L2 | TODO | Centralize Jina timeout |
| L3 | TODO | Split Perplexity timeouts |
| L4 | DEFERRED | Next.js requirement |
| L5 | TODO | Magic bytes validation |
| L6 | TODO | Google Docs URL whitelist |
| L7 | TODO | Refactor CONFIDENCE_CEILINGS |
