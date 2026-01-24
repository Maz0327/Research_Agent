# Test Audit: Consolidation Candidates

**Date:** 2026-01-23
**Total Tests:** 1054 across 42 files
**Ratio:** ~25 tests/module (high)

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| Low-value existence checks | ~31 | **Consolidate** |
| Hasattr assertions | 52 | Review - some valid |
| Not-None assertions | 58 | Review - some valid |
| Enum value tests | ~50 | **Consolidate** |
| Pydantic model field tests | ~100+ | Keep (regression protection) |
| Behavior tests | ~700+ | Keep |

---

## High Priority Consolidation Targets

### 1. Existence Check Tests (~31 tests)
**Files:** `test_phase3_pipeline.py`, `test_prompt_templates.py`, `test_hallucination_prevention.py`

**Pattern:**
```python
def test_max_videos_constant_exists(self):
    assert MAX_VIDEOS_PER_JOB is not None

def test_api_timeout_constant_exists(self):
    assert API_TIMEOUT_SECONDS is not None
```

**Problem:** If the import succeeds, the constant exists. These add no value.

**Fix:** Delete. Import failure = test failure already.

---

### 2. Enum Value Tests (~50 tests)
**Files:** `test_semantic_models.py`, `test_mode_selector.py`

**Pattern:**
```python
def test_confidence_level_values(self):
    assert ConfidenceLevel.HIGH.value == "high"
    assert ConfidenceLevel.MEDIUM.value == "medium"
    assert ConfidenceLevel.LOW.value == "low"

def test_all_six_analysis_modes_exist(self):
    assert len(AnalysisMode) == 6
```

**Problem:** Enums are defined in code. These tests duplicate the definition.

**Fix:** Consolidate to 1 test per enum that verifies expected count. Delete value tests (they're the definition).

---

### 3. Mode Selector Constant Tests (~20 tests)
**File:** `test_mode_selector.py`

**Pattern:**
```python
def test_transcript_grounded_in_quotes_allowed(self):
    assert AnalysisMode.TRANSCRIPT_GROUNDED in QUOTES_ALLOWED

def test_caption_grounded_in_quotes_allowed(self):
    assert AnalysisMode.CAPTION_GROUNDED in QUOTES_ALLOWED
```

**Fix:** Consolidate to 1 parametrized test.

---

## Medium Priority Review

### 4. Pydantic Model Creation Tests (~100 tests)
**Files:** `test_semantic_models.py`, `test_document_outputs.py`, `test_producer_models.py`

**Pattern:**
```python
def test_quote_creation_minimal(self):
    quote = Quote(quote_id="QT_1", text="Test", source_id="SRC_1")
    assert quote.quote_id == "QT_1"

def test_quote_creation_full(self):
    quote = Quote(quote_id="QT_2", text="Full", source_id="SRC_2", timestamp="05:30")
    assert quote.timestamp == "05:30"
```

**Assessment:** These ARE valuable - they catch Pydantic schema changes.

**Fix:** Keep, but consolidate "minimal" and "full" into parametrized tests.

---

## Estimated Reduction

| Action | Tests Removed | New Count |
|--------|---------------|-----------|
| Delete existence checks | -31 | 1023 |
| Consolidate enum tests | -40 | 983 |
| Consolidate mode selectors | -15 | 968 |
| Parametrize model tests | -30 | 938 |
| **Total** | **-116** | **~940** |

---

## Recommendation

**Phase 1 (Safe, 30 min):**
1. Delete pure existence checks for constants/functions
2. Parametrize enum value tests

**Phase 2 (Medium risk, 1 hr):**
1. Consolidate mode selector constant membership tests
2. Parametrize Pydantic model field tests

**Skip:**
- Behavior tests (keep all)
- Prompt guardrail tests (keep - spec compliance)
- Integration tests (keep all)

---

## Questions

1. Should we reduce to ~600 tests by removing more schema tests?
2. Priority: test count reduction vs fixing production issues?
