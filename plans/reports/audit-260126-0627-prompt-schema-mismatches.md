# Audit Report: Prompt vs Schema Mismatches

**Date:** 2026-01-26
**Branch:** claude/fix-transcript-name-extraction-E75jf
**Scope:** All extraction modes, synthesis prompts, output documents

---

## Executive Summary

Found **12 field mismatches** where prompts request data that schemas/models don't capture. The most critical is **speaker name extraction** which affects all quote-capable modes.

---

## Critical Issues

### 1. QUOTE SPEAKER FIELD (All Quote Modes) ⚠️ HIGH

**Prompts request but schema doesn't capture:**

| Mode | Prompt Location | Requests `speaker` |
|------|-----------------|-------------------|
| transcript_grounded | `prompts/modes/transcript_grounded.py:41` | ✅ Yes |
| caption_grounded | `prompts/modes/caption_grounded.py:42` | ✅ Yes |
| article_fetched | `prompts/modes/article_fetched.py:47` | ✅ Yes |
| text_provided | `prompts/modes/text_provided.py:45` | ✅ Yes |
| ocr_extracted | `prompts/modes/ocr_extracted.py:52` | ✅ Yes |

**Schema/Model:** `semantic_extraction_schema.py:22-28`
```python
class QuoteSchema(BaseModel):
    quote_id: str
    text: str
    source_id: str
    timestamp: str
    approximate: bool
    # NO speaker field!
```

**Dataclass:** `semantic_units.py:45-88`
```python
@dataclass
class Quote:
    quote_id: str
    text: str
    source_id: str
    timestamp: Optional[str] = None
    paragraph_index: Optional[int] = None
    approximate: bool = False
    # NO speaker field!
```

**Parser:** `semantic_extraction.py:289-296` - doesn't capture speaker

**Impact:** Speaker names extracted by Gemini are discarded

---

### 2. QUOTE CONTEXT FIELD (All Quote Modes) ⚠️ MEDIUM

**All prompts request `context` field for quotes:**
- transcript_grounded:42 - `"context": "Brief context around the quote"`
- caption_grounded:44 - `"context": "Brief context"`
- article_fetched:48 - `"context": "Section or paragraph context"`
- text_provided:46 - `"context": "Brief context"`
- ocr_extracted:53 - `"context": "Brief context"`

**Not in QuoteSchema or Quote dataclass**

---

### 3. CAPTION_SOURCE FIELD (caption_grounded only) ⚠️ LOW

**Prompt:** `caption_grounded.py:46`
```json
"caption_source": "auto-generated | user-uploaded | unknown"
```

**Not in schema or model**

---

### 4. ARTICLE STRUCTURE (article_fetched only) ⚠️ LOW

**Prompt:** `article_fetched.py:56-60`
```json
"article_structure": {
  "sections": ["Introduction", "Main Argument", ...],
  "author": "Author name",
  "publication_date": "YYYY-MM-DD if available"
}
```

**Not in schema - entire structure missing**

---

### 5. QUOTE LOCATION FIELD (article_fetched only) ⚠️ LOW

**Prompt:** `article_fetched.py:49`
```json
"location": "Section heading or paragraph description"
```

**Not in schema or model**

---

### 6. VERIFICATION FLAGS (text_provided, ocr_extracted) ⚠️ MEDIUM

**Prompts request:**
```json
"_accuracy_unverified": true,
"_verification_warning": "User-provided source; accuracy unconfirmed"
```

**Model has `_verification_warning` but not `_accuracy_unverified`**

---

### 7. OCR_CONFIDENCE FIELD (ocr_extracted only) ⚠️ LOW

**Prompt:** `ocr_extracted.py:56`
```json
"ocr_confidence": "high | medium | low"
```

**Not in schema**

---

### 8. OCR_ISSUES_DETECTED ARRAY (ocr_extracted only) ⚠️ LOW

**Prompt:** `ocr_extracted.py:72-75`
```json
"ocr_issues_detected": [
  "Possible character confusion at 'rnatter' (likely 'matter')"
]
```

**Not in schema - entire array missing**

---

### 9. APPROXIMATE OBSERVATION FIELDS (video_only) ⚠️ LOW

**Prompt requests but schema lacks:**
- `approximate: true` (always true)
- `type: "observation"`
- `confidence: "low"` (always low)

**ApproximateObservationSchema:** `semantic_extraction_schema.py:66-71`
```python
class ApproximateObservationSchema(BaseModel):
    observation_id: str
    observation: str
    source_id: str
    timestamp_range: str
    # Missing: approximate, type, confidence
```

**Note:** The dataclass `ApproximateObservation` in `semantic_units.py:307-337` DOES have these fields with defaults.

---

### 10. CONFIDENCE_RATIONALE (Claims, KeyPoints) ⚠️ MEDIUM

**Schema HAS the field:** `semantic_extraction_schema.py:38,48`
```python
class ClaimSchema(BaseModel):
    ...
    confidence_rationale: str  # Required

class KeyPointSchema(BaseModel):
    ...
    confidence_rationale: str  # Required
```

**Dataclass MISSING the field:** `semantic_units.py:94-133` (Claim) and `semantic_units.py:140-171` (KeyPoint)

**Impact:** Rationale extracted but not stored

---

## Synthesis/Output Issues

### 11. SYNTHESIS THEMES MISSING PHASE 5 FIELDS

**Prompt requests (synthesis_prompt.py:67-75):**
```json
{
    "theme_id": "THEME_1",
    "sources_supporting": ["SRC_1", "SRC_2"],
    "is_consensus": true
}
```

**Theme dataclass HAS these fields** (`semantic_units.py:201-203`) ✅

---

### 12. SYNTHESIS TENSIONS MISSING PHASE 5 FIELDS

**Prompt requests (synthesis_prompt.py:79-86):**
```json
{
    "tension_id": "TEN_1",
    "is_cross_source": true,
    "sources_position_a": ["SRC_1"],
    "sources_position_b": ["SRC_2"]
}
```

**Tension dataclass HAS these fields** (`semantic_units.py:244-246`) ✅

---

## Summary by Priority

| Priority | Issue | Affected Modes |
|----------|-------|----------------|
| **HIGH** | Missing `speaker` field | All quote modes (5) |
| **MEDIUM** | Missing `context` field | All quote modes (5) |
| **MEDIUM** | Missing `confidence_rationale` in dataclass | All modes |
| **MEDIUM** | Missing `_accuracy_unverified` | text_provided, ocr_extracted |
| **LOW** | Missing `caption_source` | caption_grounded |
| **LOW** | Missing `article_structure` | article_fetched |
| **LOW** | Missing `location` | article_fetched |
| **LOW** | Missing `ocr_confidence` | ocr_extracted |
| **LOW** | Missing `ocr_issues_detected` | ocr_extracted |
| **LOW** | Missing observation fields in schema | video_only |

---

## Fix Locations

### For Quote Fields (speaker, context)

1. **Schema:** `backend/models/semantic_extraction_schema.py:22-28`
   - Add `speaker: str`
   - Add `context: str`

2. **Dataclass:** `backend/models/semantic_units.py:45-88`
   - Add `speaker: Optional[str] = None`
   - Add `context: Optional[str] = None`

3. **Parser:** `backend/pipeline/stages/semantic_extraction.py:289-296`
   - Capture `quote_data.get("speaker")` and `quote_data.get("context")`

4. **to_dict():** Update in Quote class

### For Claim/KeyPoint confidence_rationale

1. **Dataclass:** `backend/models/semantic_units.py`
   - Add `confidence_rationale: Optional[str] = None` to Claim (line 120)
   - Add `confidence_rationale: Optional[str] = None` to KeyPoint (line 162)

2. **Parser:** `backend/pipeline/stages/semantic_extraction.py`
   - Capture `confidence_rationale` for claims and key_points

3. **to_dict():** Update in Claim and KeyPoint classes

---

## Unresolved Questions

1. Should `context` be added to Quote or remain prompt-only guidance?
2. Are mode-specific fields (caption_source, ocr_confidence) needed in common schema?
3. Should article_structure be a separate model or embedded in Quote?
