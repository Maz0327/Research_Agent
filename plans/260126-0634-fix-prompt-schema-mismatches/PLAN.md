# Implementation Plan: Fix Prompt vs Schema Mismatches

**Date:** 2026-01-26
**Branch:** claude/fix-transcript-name-extraction-E75jf
**Audit Report:** `plans/reports/audit-260126-0627-prompt-schema-mismatches.md`

---

## Objective

Align schemas, dataclasses, and parsers with prompt requirements so extracted data is captured and stored.

---

## Phase 1: Quote Fields (HIGH Priority)

**Goal:** Capture `speaker` and `context` from all quote modes

### Task 1.1: Update QuoteSchema
**File:** `backend/models/semantic_extraction_schema.py`
**Lines:** 22-28

```python
class QuoteSchema(BaseModel):
    quote_id: str
    text: str
    source_id: str
    timestamp: str
    approximate: bool
    speaker: str           # ADD
    context: str           # ADD (optional per mode)
```

### Task 1.2: Update Quote Dataclass
**File:** `backend/models/semantic_units.py`
**Lines:** 45-88

Add fields:
```python
speaker: Optional[str] = None
context: Optional[str] = None
```

Update `to_dict()` to include new fields.

### Task 1.3: Update Parser
**File:** `backend/pipeline/stages/semantic_extraction.py`
**Function:** `parse_extraction_response()` (~lines 288-296)

Capture:
```python
speaker=quote_data.get("speaker"),
context=quote_data.get("context"),
```

### Task 1.4: Test Quote Extraction
- Run existing tests
- Verify speaker/context captured in output

**Checkpoint:** Quotes have speaker and context fields populated

---

## Phase 2: Claim/KeyPoint Fields (MEDIUM Priority)

**Goal:** Store `confidence_rationale` extracted by Gemini

### Task 2.1: Update Claim Dataclass
**File:** `backend/models/semantic_units.py`
**Lines:** 94-133

Add field:
```python
confidence_rationale: Optional[str] = None
```

Update `to_dict()`.

### Task 2.2: Update KeyPoint Dataclass
**File:** `backend/models/semantic_units.py`
**Lines:** 140-171

Add field:
```python
confidence_rationale: Optional[str] = None
```

Update `to_dict()`.

### Task 2.3: Update Parser for Claims/KeyPoints
**File:** `backend/pipeline/stages/semantic_extraction.py`

Capture `confidence_rationale` for both claim and key_point parsing.

### Task 2.4: Test Claim/KeyPoint Extraction
- Verify rationale captured
- Check output documents include rationale

**Checkpoint:** Claims and KeyPoints have confidence_rationale populated

---

## Phase 3: Mode-Specific Fields (LOW Priority)

### Task 3.1: caption_grounded - Add caption_source
**Files:**
- `semantic_extraction_schema.py` - Add `caption_source: str` to QuoteSchema (conditional)
- `semantic_units.py` - Add `caption_source: Optional[str] = None` to Quote
- Parser - Capture field

### Task 3.2: article_fetched - Add location
**Files:**
- `semantic_extraction_schema.py` - Add `location: str` to QuoteSchema (conditional)
- `semantic_units.py` - Add `location: Optional[str] = None` to Quote
- Parser - Capture field

### Task 3.3: ocr_extracted - Add ocr_confidence
**Files:**
- `semantic_extraction_schema.py` - Add `ocr_confidence: str` to QuoteSchema (conditional)
- `semantic_units.py` - Add `ocr_confidence: Optional[str] = None` to Quote
- Parser - Capture field

### Task 3.4: text_provided/ocr_extracted - Add _accuracy_unverified
**Files:**
- `semantic_units.py` - Add `_accuracy_unverified: Optional[bool] = None` to Quote
- Parser - Capture field

**Checkpoint:** Mode-specific fields captured when applicable

---

## Phase 4: ApproximateObservation Schema (LOW Priority)

### Task 4.1: Update ApproximateObservationSchema
**File:** `backend/models/semantic_extraction_schema.py`
**Lines:** 66-71

Add fields to match dataclass:
```python
approximate: bool  # Always True
type: str          # Always "observation"
confidence: str    # Always "low"
```

**Checkpoint:** video_only schema matches prompt requirements

---

## Phase 5: Verification & Documentation

### Task 5.1: Run Full Test Suite
```bash
pytest backend/tests/ -v
```

### Task 5.2: Manual Integration Test
- Create test job with transcript
- Verify speaker names extracted
- Check all documents contain new fields

### Task 5.3: Update PROGRESS.md
- Document changes
- List modified files

---

## File Change Summary

| File | Changes |
|------|---------|
| `backend/models/semantic_extraction_schema.py` | Add speaker, context to QuoteSchema; update ApproximateObservationSchema |
| `backend/models/semantic_units.py` | Add speaker, context to Quote; add confidence_rationale to Claim/KeyPoint |
| `backend/pipeline/stages/semantic_extraction.py` | Update parser to capture new fields |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Schema change breaks Gemini validation | Test with small prompt first |
| Existing data migration | New fields are Optional, backward compatible |
| Parser regression | Run existing tests after each change |

---

## Estimated Effort

| Phase | Tasks | Complexity |
|-------|-------|------------|
| Phase 1 | 4 | Medium |
| Phase 2 | 4 | Low |
| Phase 3 | 4 | Low |
| Phase 4 | 1 | Low |
| Phase 5 | 3 | Low |

---

## Success Criteria

1. ✅ All prompts' requested fields are captured in models
2. ✅ Existing tests pass
3. ✅ New integration test verifies speaker extraction
4. ✅ Output documents show speaker names from transcripts
