# Phase 9 Implementation Plan: Comprehensive Test Suite

**Date:** 2026-01-16
**Phase:** 9
**Branch:** feature/vision-alignment-v1
**Prerequisite:** Phases 1-8 Complete
**Focus:** Tests only (Media Inventory deferred to Phase 11)

---

## Executive Summary

Phase 9 adds comprehensive test coverage for Phases 2-8 semantic pipeline code.

**Current State:**
- 142 tests pass (1,929 lines)
- 0% coverage for new semantic pipeline stages
- 0% coverage for V1-V10 validation rules

**Target State:**
- 280+ tests (5,500+ lines)
- >80% coverage for backend/pipeline/stages
- >85% coverage for backend/models
- All V1-V10 validation rules tested

**Scope Decision:** Media Inventory deferred to Phase 11 (per Phase 8 plan).

---

## Task Breakdown

### Phase 9.1: Model Tests (~1,300 lines, 5 files)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| 9.1.1 | test_semantic_models.py | ~400 | HIGH |
| 9.1.2 | test_document_outputs.py | ~300 | HIGH |
| 9.1.3 | test_booster_models.py | ~200 | MEDIUM |
| 9.1.4 | test_producer_models.py | ~250 | MEDIUM |
| 9.1.5 | test_job_extended_models.py | ~150 | LOW |

---

### Phase 9.2: Pipeline Stage Tests (~2,000 lines, 7 files)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| 9.2.1 | test_semantic_extraction_stages.py | ~400 | HIGH |
| 9.2.2 | test_document_assembly.py | ~300 | HIGH |
| 9.2.3 | test_validation_stages.py | ~350 | HIGH |
| 9.2.4 | test_cross_reference.py | ~250 | MEDIUM |
| 9.2.5 | test_booster_stage.py | ~250 | MEDIUM |
| 9.2.6 | test_producer_stage.py | ~300 | MEDIUM |
| 9.2.7 | test_mode_selector.py | ~150 | HIGH |

---

### Phase 9.3: Integration Tests (~500 lines, 1 file)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| 9.3.1 | test_semantic_pipeline_integration.py | ~500 | HIGH |

---

### Phase 9.4: Validation Rule Tests (V1-V10)

Embedded in Phase 9.2.3 (test_validation_stages.py)

| Rule | Test Scenarios |
|------|----------------|
| V1 | JSON schema compliance |
| V2 | Source ID consistency |
| V3 | Confidence ceiling enforcement |
| V4 | Quote verification (fuzzy matching) |
| V5 | Quote permission by mode |
| V6 | Timestamp validation |
| V7 | Empty output permission |
| V8 | Provenance chain validation |
| V9 | Cardinality validation |
| V10 | Doc 3 gating requirements |

---

## Detailed Task Specifications

### Task 9.1.1: test_semantic_models.py

**File:** `backend/tests/test_semantic_models.py`

**Test Classes:**
```python
class TestQuote:
    def test_quote_creation()
    def test_quote_with_verification_status()
    def test_quote_to_dict()

class TestClaim:
    def test_claim_creation()
    def test_claim_confidence_levels()
    def test_claim_to_dict()

class TestKeyPoint:
    def test_key_point_requires_source_ids()
    def test_key_point_with_multiple_sources()

class TestTheme:
    def test_theme_creation()
    def test_theme_with_cross_source_consensus()
    def test_theme_supporting_key_points()

class TestTension:
    def test_tension_creation()
    def test_tension_with_cross_source_flag()

class TestGap:
    def test_gap_creation()
    def test_gap_with_related_themes()

class TestSemanticExtractionResult:
    def test_extraction_result_creation()
    def test_enforce_confidence_ceiling_high()
    def test_enforce_confidence_ceiling_medium()
    def test_enforce_confidence_ceiling_low()
    def test_mode_specific_quote_warnings()
```

---

### Task 9.1.2: test_document_outputs.py

**File:** `backend/tests/test_document_outputs.py`

**Test Classes:**
```python
class TestSourceEntry:
    def test_source_entry_creation()
    def test_source_entry_with_transcript()
    def test_source_entry_to_dict()

class TestSourceLedger:
    def test_source_ledger_creation()
    def test_source_ledger_to_markdown()

class TestJumpStartDirections:
    def test_jump_start_creation()
    def test_jump_start_with_booster_expansion()
    def test_jump_start_to_markdown()

class TestSemanticBrief:
    def test_semantic_brief_creation()
    def test_semantic_brief_with_tensions()
    def test_semantic_brief_to_markdown()

class TestAddendumSection:
    def test_addendum_creation()
    def test_addendum_with_cross_reference()
    def test_addendum_to_markdown()

class TestCrossReferenceNotes:
    def test_cross_ref_supports()
    def test_cross_ref_contradicts()
    def test_cross_ref_new_tensions()
```

---

### Task 9.1.3: test_booster_models.py

**File:** `backend/tests/test_booster_models.py`

**Test Classes:**
```python
class TestContextBundle:
    def test_context_bundle_creation()
    def test_context_bundle_excludes_full_text()

class TestBoosterOutput:
    def test_booster_output_creation()
    def test_booster_with_missing_perspectives()
    def test_booster_with_primary_directions()
    def test_booster_with_search_queries()

class TestMissingPerspective:
    def test_perspective_creation()
    def test_perspective_to_dict()

class TestPrimarySourceDirection:
    def test_direction_creation()
    def test_direction_source_types()

class TestSearchQuery:
    def test_search_query_creation()
    def test_platform_suggestions()
```

---

### Task 9.1.4: test_producer_models.py

**File:** `backend/tests/test_producer_models.py`

**Test Classes:**
```python
class TestStoryCore:
    def test_story_core_creation()
    def test_story_core_to_dict()

class TestNarrativeAngle:
    def test_angle_creation()
    def test_angle_with_key_sources()

class TestOpeningHook:
    def test_hook_types()
    def test_hook_creation()

class TestStructureOption:
    def test_structure_types()
    def test_structure_with_sections()

class TestRiskAssessment:
    def test_sensitivity_levels()
    def test_risk_with_legal_considerations()

class TestProducerPacket:
    def test_packet_creation()
    def test_packet_to_dict()
    def test_packet_to_markdown()
    def test_creative_interpretation_notice()
```

---

### Task 9.1.5: test_job_extended_models.py

**File:** `backend/tests/test_job_extended_models.py`

**Test Classes:**
```python
class TestSourceStateEnum:
    def test_state_values()

class TestJobSource:
    def test_job_source_creation()
    def test_job_source_status_tracking()

class TestAddSourcesRequest:
    def test_request_validation()
    def test_max_sources_limit()

class TestAddSourcesResponse:
    def test_response_creation()
```

---

### Task 9.2.1: test_semantic_extraction_stages.py

**File:** `backend/tests/test_semantic_extraction_stages.py`

**Test Classes:**
```python
class TestGapAnalysisStage:
    def test_stage_with_complete_extractions()
    def test_stage_with_single_source()
    def test_stage_returns_valid_gaps()
    def test_stage_handles_empty_input()

class TestSemanticSynthesisStage:
    def test_synthesis_with_multiple_sources()
    def test_synthesis_creates_cross_source_themes()
    def test_synthesis_detects_conflicts()
    def test_synthesis_handles_single_source()
    def test_confidence_calibration()
```

**Mocking:**
```python
# Mock Gemini responses for deterministic testing
@pytest.fixture
def mock_gemini_synthesis_response():
    return {
        "semantic_core": {...},
        "themes": [...],
        "tensions": [...],
    }
```

---

### Task 9.2.2: test_document_assembly.py

**File:** `backend/tests/test_document_assembly.py`

**Test Classes:**
```python
class TestDocZeroAssembly:
    def test_doc0_includes_all_sources()
    def test_doc0_transcript_provenance()
    def test_doc0_to_markdown()

class TestDocOneAssembly:
    def test_doc1_scope_in_out()
    def test_doc1_key_points()
    def test_doc1_gaps()
    def test_doc1_next_steps()

class TestDocTwoAssembly:
    def test_doc2_semantic_core()
    def test_doc2_themes()
    def test_doc2_tensions()
    def test_doc2_to_markdown()

class TestProvenanceChainValidation:
    def test_valid_provenance_chain()
    def test_broken_theme_to_keypoint()
    def test_broken_keypoint_to_source()
    def test_orphan_references_detected()
```

---

### Task 9.2.3: test_validation_stages.py

**File:** `backend/tests/test_validation_stages.py`

**Test Classes (V1-V10):**
```python
class TestV1JsonSchema:
    def test_valid_json_passes()
    def test_invalid_json_fails()
    def test_retry_on_failure()

class TestV2SourceIdConsistency:
    def test_valid_source_ids()
    def test_invalid_source_reference()

class TestV3ConfidenceCeiling:
    def test_transcript_grounded_allows_high()
    def test_caption_grounded_caps_at_medium()
    def test_video_only_caps_at_low()
    def test_auto_downgrade_with_warning()

class TestV4QuoteVerification:
    def test_exact_match_verified()
    def test_95_percent_match_verified()
    def test_80_94_percent_partial()
    def test_below_80_unverified()
    def test_whitespace_normalization()
    def test_case_insensitive()

class TestV5QuotePermission:
    def test_transcript_grounded_allows_quotes()
    def test_video_only_forbids_quotes()
    def test_text_provided_allows_with_warning()

class TestV6TimestampValidation:
    def test_valid_timestamp_format()
    def test_invalid_timestamp_rejected()
    def test_timestamp_range_validation()

class TestV7EmptyOutput:
    def test_empty_arrays_permitted()
    def test_sparse_output_accepted()
    def test_no_forced_content()

class TestV8ProvenanceChain:
    def test_complete_chain_passes()
    def test_theme_missing_keypoint_fails()
    def test_keypoint_missing_source_fails()

class TestV9Cardinality:
    def test_min_themes_enforced()
    def test_max_hooks_enforced()
    def test_narrative_angles_range()

class TestV10DocThreeGating:
    def test_requires_4_plus_sources()
    def test_requires_high_confidence_source()
    def test_requires_completed_job()
    def test_gating_failure_message()
```

---

### Task 9.2.4: test_cross_reference.py

**File:** `backend/tests/test_cross_reference.py`

**Test Classes:**
```python
class TestCrossReferenceStage:
    def test_identifies_supporting_evidence()
    def test_identifies_contradictions()
    def test_creates_new_tensions()
    def test_handles_empty_new_extractions()

class TestAddendumAssembly:
    def test_addendum_preserves_original()
    def test_addendum_appends_new_content()
    def test_cross_ref_notes_included()
```

---

### Task 9.2.5: test_booster_stage.py

**File:** `backend/tests/test_booster_stage.py`

**Test Classes:**
```python
class TestContextBundleGeneration:
    def test_bundle_excludes_full_text()
    def test_bundle_includes_themes()
    def test_bundle_includes_gaps()
    def test_bundle_metadata()

class TestBoosterStage:
    def test_booster_with_valid_context()
    def test_booster_hallucination_protection()
    def test_booster_safe_failure()
    def test_booster_temperature_setting()

class TestBoosterExpansion:
    def test_expansion_markdown_generation()
    def test_expansion_appends_to_doc1()
```

---

### Task 9.2.6: test_producer_stage.py

**File:** `backend/tests/test_producer_stage.py`

**Test Classes:**
```python
class TestProducerPipeline:
    def test_4_stage_sequence()
    def test_stage1_story_core()
    def test_stage2_structure()
    def test_stage3_creative()
    def test_stage4_risk()

class TestProducerTemperature:
    def test_core_temp_04()
    def test_structure_temp_04()
    def test_creative_temp_05()
    def test_risk_temp_03()

class TestCardinalityValidation:
    def test_min_narrative_angles()
    def test_max_narrative_angles()
    def test_min_hooks()
    def test_max_structure_options()

class TestCreativeInterpretationNotice:
    def test_notice_in_output()
    def test_not_factual_disclaimer()
```

---

### Task 9.2.7: test_mode_selector.py

**File:** `backend/tests/test_mode_selector.py`

**Test Classes:**
```python
class TestModeSelection:
    def test_selects_transcript_grounded()
    def test_selects_caption_grounded()
    def test_selects_video_only()
    def test_selects_text_provided()
    def test_selects_ocr_extracted()
    def test_selects_article_fetched()

class TestConfidenceCeilings:
    def test_get_confidence_ceiling()
    def test_all_modes_have_ceiling()

class TestQuotePermissions:
    def test_are_quotes_allowed()
    def test_degraded_quote_modes()
    def test_no_quote_modes()
```

---

### Task 9.3.1: test_semantic_pipeline_integration.py

**File:** `backend/tests/test_semantic_pipeline_integration.py`

**Test Classes:**
```python
class TestSingleSourcePipeline:
    def test_youtube_transcript_flow()
    def test_text_input_flow()
    def test_screenshot_ocr_flow()

class TestMultiSourcePipeline:
    def test_two_source_synthesis()
    def test_three_source_conflict_detection()
    def test_cross_source_theme_attribution()

class TestEvolvingJobPipeline:
    def test_add_source_to_completed_job()
    def test_cross_reference_on_new_source()
    def test_addendum_generation()

class TestBoosterIntegration:
    def test_booster_on_completed_job()
    def test_booster_appends_to_doc1()
    def test_booster_failure_recovery()

class TestProducerIntegration:
    def test_producer_on_completed_job()
    def test_producer_gating_enforced()
    def test_producer_doc3_generation()

class TestErrorRecovery:
    def test_gemini_timeout_recovery()
    def test_partial_extraction_continues()
    def test_validation_failure_with_warnings()
```

---

## Test Utilities

### fixtures.py

```python
# backend/tests/fixtures.py

@pytest.fixture
def sample_key_point():
    return KeyPoint(
        key_point_id="KP_1",
        statement="Test statement",
        source_ids=["SRC_1"],
        confidence=ConfidenceLevel.HIGH,
    )

@pytest.fixture
def sample_extraction_result():
    return SemanticExtractionResult(
        source_id="SRC_1",
        analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        confidence_ceiling=ConfidenceLevel.HIGH,
        quotes=[...],
        claims=[...],
        key_points=[...],
    )

@pytest.fixture
def mock_gemini_client():
    """Mock GeminiClient for deterministic tests."""
    with patch('backend.integrations.gemini_client.GeminiClient') as mock:
        mock.return_value.generate_json.return_value = {...}
        yield mock
```

---

## Verification Commands

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Run specific phase
pytest backend/tests/test_semantic_*.py -v

# Run validation tests only
pytest backend/tests/test_validation_stages.py -v

# Check coverage threshold
pytest --cov=backend/pipeline/stages --cov-fail-under=80
```

---

## Success Criteria

| Metric | Target | Current |
|--------|--------|---------|
| Total tests | 280+ | 142 |
| Test lines | 5,500+ | 1,929 |
| Stage coverage | >80% | 0% |
| Model coverage | >85% | ~60% |
| V1-V10 tested | 100% | 0% |
| Test runtime | <60s | ~12s |

---

## Files to Create (13 total)

| # | File | Lines |
|---|------|-------|
| 1 | backend/tests/test_semantic_models.py | ~400 |
| 2 | backend/tests/test_document_outputs.py | ~300 |
| 3 | backend/tests/test_booster_models.py | ~200 |
| 4 | backend/tests/test_producer_models.py | ~250 |
| 5 | backend/tests/test_job_extended_models.py | ~150 |
| 6 | backend/tests/test_semantic_extraction_stages.py | ~400 |
| 7 | backend/tests/test_document_assembly.py | ~300 |
| 8 | backend/tests/test_validation_stages.py | ~350 |
| 9 | backend/tests/test_cross_reference.py | ~250 |
| 10 | backend/tests/test_booster_stage.py | ~250 |
| 11 | backend/tests/test_producer_stage.py | ~300 |
| 12 | backend/tests/test_mode_selector.py | ~150 |
| 13 | backend/tests/test_semantic_pipeline_integration.py | ~500 |

**Total:** ~3,800 lines of new test code

---

## Task Order (Dependencies)

```
9.1.1 → 9.2.1 (models before stages)
9.1.2 → 9.2.2 (document models before assembly)
9.2.7 → 9.2.3 (mode_selector before validation)
9.2.1-9.2.6 → 9.3.1 (all stages before integration)
```

**Recommended execution order:**
1. 9.1.1 (semantic_models)
2. 9.1.2 (document_outputs)
3. 9.2.7 (mode_selector) — foundational
4. 9.2.3 (validation_stages) — V1-V10
5. 9.2.1 (extraction_stages)
6. 9.2.2 (document_assembly)
7. 9.1.3 (booster_models)
8. 9.2.5 (booster_stage)
9. 9.1.4 (producer_models)
10. 9.2.6 (producer_stage)
11. 9.2.4 (cross_reference)
12. 9.1.5 (job_extended_models)
13. 9.3.1 (integration)

---

## Post-Phase 9

After completion:
1. Run `/checkpoint`
2. Update PROGRESS.md
3. Commit: `Phase 9: Add comprehensive test suite`
4. Generate coverage report
5. Archive coverage report to plans/reports/

**Next Phase:** Phase 10 (Documentation) or Phase 11 (Media Inventory)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Gemini API costs in tests | Use mocked responses |
| Test runtime bloat | Parallel execution, fixtures |
| Coverage gaps | Coverage enforcement in CI |
| Flaky tests | Deterministic mocks, no network |
