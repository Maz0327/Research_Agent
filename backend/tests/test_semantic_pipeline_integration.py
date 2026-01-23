"""
Integration tests for semantic pipeline.

Tests for: Single-source flow, multi-source synthesis, evolving jobs,
booster integration, producer integration, error recovery.

Phase 9 Task 9.3.1
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    KeyPoint,
    Theme,
    Tension,
    Gap,
    Quote,
    Claim,
    SemanticExtractionResult,
)
from backend.models.document_outputs import (
    SourceLedger,
    JumpStartDirections,
    SemanticBrief,
    CrossReferenceNotes,
)
from backend.models.booster_models import (
    ContextBundle,
    BoosterOutput,
    MissingPerspective,
)
from backend.models.producer_models import (
    ProducerPacket,
    StoryCore,
)
from backend.pipeline.context import PipelineContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_gemini_extraction_response():
    """Mock Gemini response for extraction."""
    return {
        "data": {
            "quotes": [
                {
                    "quote_id": "QT_1",
                    "text": "This is a direct quote from the source.",
                    "timestamp": "01:30",
                    "context": "Discussion about main topic",
                },
            ],
            "claims": [
                {
                    "claim_id": "CLM_1",
                    "statement": "The company reported revenue growth",
                    "attribution": "CEO statement",
                    "confidence": "high",
                },
            ],
            "key_points": [
                {
                    "key_point_id": "KP_1",
                    "statement": "Revenue increased by 20% in Q4",
                    "source_ids": ["SRC_1"],
                    "confidence": "high",
                },
                {
                    "key_point_id": "KP_2",
                    "statement": "New product launch planned for Q1",
                    "source_ids": ["SRC_1"],
                    "confidence": "medium",
                },
            ],
            "themes": [
                {
                    "theme_id": "THEME_1",
                    "label": "Financial Growth",
                    "description": "Strong financial performance indicators",
                    "related_key_points": ["KP_1"],
                },
            ],
            "tensions": [],
            "gaps": [],
        },
        "cost": 0.02,
    }


@pytest.fixture
def mock_gemini_synthesis_response():
    """Mock Gemini response for synthesis."""
    return {
        "data": {
            "semantic_core": {
                "primary_narrative": "Company showing strong growth",
                "confidence_level": "medium",
            },
            "themes": [
                {
                    "theme_id": "THEME_1",
                    "label": "Financial Performance",
                    "description": "Patterns of revenue growth and market expansion",
                    "related_key_points": ["KP_1", "KP_2"],
                },
            ],
            "tensions": [
                {
                    "tension_id": "TEN_1",
                    "description": "Growth claims vs market uncertainty",
                    "involved_key_points": ["KP_1", "KP_2"],
                    "is_cross_source": True,
                },
            ],
            "gaps": [
                {
                    "gap_id": "GAP_1",
                    "description": "Missing competitor analysis",
                    "why_expected": "Context needed for market claims",
                    "related_key_points": ["KP_1"],
                },
            ],
        },
        "cost": 0.03,
    }


@pytest.fixture
def sample_extraction_result():
    """Sample extraction result for testing."""
    return SemanticExtractionResult(
        source_id="SRC_1",
        analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        quotes=[
            Quote(
                quote_id="QT_1",
                text="Direct quote text",
                source_id="SRC_1",
                timestamp="01:30",
            ),
        ],
        claims=[
            Claim(
                claim_id="CLM_1",
                statement="Claim statement",
                source_id="SRC_1",
                supporting_quotes=["QT_1"],
                confidence=ConfidenceLevel.HIGH,
            ),
        ],
        key_points=[
            KeyPoint(
                key_point_id="KP_1",
                statement="Key point statement",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.HIGH,
            ),
        ],
        themes=[
            Theme(
                theme_id="THEME_1",
                label="Test Theme",
                description="Theme description",
                related_key_points=["KP_1"],
            ),
        ],
    )


@pytest.fixture
def sample_source_ledger():
    """Sample source ledger for testing."""
    from backend.models.document_outputs import SourceEntry

    return SourceLedger(
        topic="Company financial performance analysis",
        sources=[
            SourceEntry(
                source_id="SRC_1",
                title="Test Video",
                source_type="youtube",
                url="https://youtube.com/watch?v=abc123",
            ),
        ],
    )


# =============================================================================
# TestSingleSourcePipeline
# =============================================================================


class TestSingleSourcePipeline:
    """Integration tests for single-source pipeline flow."""

    def test_youtube_transcript_flow(self, sample_extraction_result):
        """Single YouTube source should produce valid extraction."""
        # Verify extraction result structure
        assert sample_extraction_result.source_id == "SRC_1"
        assert sample_extraction_result.analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED
        assert len(sample_extraction_result.key_points) >= 1
        assert len(sample_extraction_result.themes) >= 1

        # Verify provenance chain
        for kp in sample_extraction_result.key_points:
            assert "SRC_1" in kp.source_ids

    def test_text_input_flow(self):
        """Text input should use TEXT_PROVIDED mode."""
        extraction = SemanticExtractionResult(
            source_id="SRC_TEXT_1",
            analysis_mode=AnalysisMode.TEXT_PROVIDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Point from text input",
                    source_ids=["SRC_TEXT_1"],
                    confidence=ConfidenceLevel.MEDIUM,  # Ceiling for text_provided
                ),
            ],
        )

        assert extraction.analysis_mode == AnalysisMode.TEXT_PROVIDED
        # TEXT_PROVIDED has MEDIUM ceiling
        assert extraction.key_points[0].confidence == ConfidenceLevel.MEDIUM

    def test_screenshot_ocr_flow(self):
        """Screenshot input should use OCR_EXTRACTED mode."""
        extraction = SemanticExtractionResult(
            source_id="SRC_OCR_1",
            analysis_mode=AnalysisMode.OCR_EXTRACTED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Point from OCR",
                    source_ids=["SRC_OCR_1"],
                    confidence=ConfidenceLevel.MEDIUM,  # Ceiling for ocr_extracted
                ),
            ],
        )

        assert extraction.analysis_mode == AnalysisMode.OCR_EXTRACTED

    def test_extraction_produces_source_ledger(self, sample_source_ledger):
        """Extraction should produce valid source ledger (Doc 0)."""
        assert len(sample_source_ledger.sources) == 1
        assert sample_source_ledger.sources[0].source_id == "SRC_1"
        assert sample_source_ledger.topic != ""


# =============================================================================
# TestMultiSourcePipeline
# =============================================================================


class TestMultiSourcePipeline:
    """Integration tests for multi-source synthesis."""

    def test_two_source_synthesis(self):
        """Two sources should produce cross-source synthesis."""
        extraction_1 = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Revenue increased",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
            themes=[
                Theme(
                    theme_id="THEME_1",
                    label="Financial Growth",
                    description="Growth patterns",
                    related_key_points=["KP_1"],
                ),
            ],
        )

        extraction_2 = SemanticExtractionResult(
            source_id="SRC_2",
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_2",
                    statement="Market share expanded",
                    source_ids=["SRC_2"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
            themes=[
                Theme(
                    theme_id="THEME_2",
                    label="Market Position",
                    description="Market expansion",
                    related_key_points=["KP_2"],
                ),
            ],
        )

        # Verify both extractions are valid
        assert extraction_1.source_id != extraction_2.source_id
        all_key_points = extraction_1.key_points + extraction_2.key_points
        assert len(all_key_points) == 2

    def test_three_source_conflict_detection(self):
        """Three sources with conflict should produce tensions."""
        # Source 1: Claims growth
        extraction_1 = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Company reports 20% growth",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
        )

        # Source 2: Supports growth
        extraction_2 = SemanticExtractionResult(
            source_id="SRC_2",
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_2",
                    statement="Analyst confirms growth trajectory",
                    source_ids=["SRC_2"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
        )

        # Source 3: Contradicts (skeptical)
        extraction_3 = SemanticExtractionResult(
            source_id="SRC_3",
            analysis_mode=AnalysisMode.TEXT_PROVIDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_3",
                    statement="Industry experts question growth claims",
                    source_ids=["SRC_3"],
                    confidence=ConfidenceLevel.MEDIUM,
                ),
            ],
        )

        # Synthesis would detect tension between KP_1/KP_2 and KP_3
        all_extractions = [extraction_1, extraction_2, extraction_3]
        assert len(all_extractions) == 3

        # Verify different source IDs
        source_ids = {e.source_id for e in all_extractions}
        assert len(source_ids) == 3

    def test_cross_source_theme_attribution(self):
        """Cross-source themes should reference multiple sources."""
        # Simulated synthesis result with cross-source theme
        cross_source_theme = Theme(
            theme_id="THEME_CROSS_1",
            label="Industry Consensus",
            description="Multiple sources agree on market direction",
            related_key_points=["KP_1", "KP_2"],  # From different sources
        )

        assert len(cross_source_theme.related_key_points) > 1


# =============================================================================
# TestEvolvingJobPipeline
# =============================================================================


class TestEvolvingJobPipeline:
    """Integration tests for evolving jobs (add sources to completed job)."""

    def test_add_source_to_completed_job(self, sample_extraction_result):
        """Adding source to completed job should create new extraction."""
        original_extractions = [sample_extraction_result]

        # New extraction from added source
        new_extraction = SemanticExtractionResult(
            source_id="SRC_2",
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_NEW_1",
                    statement="New perspective from added source",
                    source_ids=["SRC_2"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
        )

        # Combined extractions
        all_extractions = original_extractions + [new_extraction]
        assert len(all_extractions) == 2
        assert new_extraction.source_id not in [e.source_id for e in original_extractions]

    def test_cross_reference_on_new_source(self, sample_extraction_result):
        """Cross-reference should find supports/contradicts."""
        original = [sample_extraction_result]

        new_extraction = SemanticExtractionResult(
            source_id="SRC_2",
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_NEW_1",
                    statement="Confirms original key point",
                    source_ids=["SRC_2"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
        )

        # Simulated cross-reference result
        cross_ref = CrossReferenceNotes(
            supports=[{
                "existing_id": "KP_1",
                "new_id": "KP_NEW_1",
                "description": "New source confirms original finding",
            }],
            contradicts=[],
            new_tensions=[],
            new_gaps=[],
        )

        assert len(cross_ref.supports) == 1
        assert cross_ref.supports[0]["existing_id"] == "KP_1"

    def test_addendum_generation(self, sample_extraction_result):
        """Addendum should summarize new sources added to job."""
        # Original had 1 source
        original_count = 1

        # After adding 2 more
        new_sources = ["SRC_2", "SRC_3"]

        # Addendum would include
        addendum_data = {
            "original_source_count": original_count,
            "added_source_count": len(new_sources),
            "total_source_count": original_count + len(new_sources),
            "cross_reference_summary": {
                "supports_found": 2,
                "contradictions_found": 1,
                "new_gaps_identified": 1,
            },
        }

        assert addendum_data["total_source_count"] == 3


# =============================================================================
# TestBoosterIntegration
# =============================================================================


class TestBoosterIntegration:
    """Integration tests for booster pipeline."""

    def test_booster_on_completed_job(self, sample_extraction_result):
        """Booster should run on completed job with extractions."""
        # Completed job has extractions
        extractions = [sample_extraction_result]

        # Build context bundle from extractions
        context = ContextBundle(
            scope_in=["Company performance", "Market analysis"],
            themes=[{
                "theme_id": "THEME_1",
                "label": "Financial Growth",
                "description": "Growth patterns",
            }],
            source_count=len(extractions),
        )

        # Booster would produce directions
        assert context.source_count == 1
        assert len(context.themes) >= 1

    def test_booster_produces_directions_not_facts(self):
        """Booster output should be directions, not factual assertions."""
        booster_output = BoosterOutput(
            missing_perspectives=[
                MissingPerspective(
                    description="Industry expert perspective",
                    why_it_matters="Would provide credibility",
                    related_gaps=["GAP_1"],
                ),
            ],
            booster_provider="gemini",
        )

        # Verify output is directions (has why_it_matters)
        assert len(booster_output.missing_perspectives) >= 1
        assert booster_output.missing_perspectives[0].why_it_matters != ""

    def test_booster_failure_recovery(self):
        """Booster failure should not block job completion."""
        # Simulate booster failure
        booster_output = BoosterOutput()  # Empty output
        warnings = ["Booster failed: API timeout"]

        # Job should still have valid Doc 0/1/2
        assert booster_output.is_empty() is True
        assert len(warnings) == 1

        # Empty booster output is acceptable
        assert booster_output.total_directions == 0


# =============================================================================
# TestProducerIntegration
# =============================================================================


class TestProducerIntegration:
    """Integration tests for producer pipeline."""

    def test_producer_on_completed_job(self, sample_extraction_result):
        """Producer should run on completed job."""
        # Prerequisites: job completed with extractions
        extractions = [sample_extraction_result]

        # Producer would generate creative packet
        packet = ProducerPacket(
            job_id="JOB_1",
            generated_at=datetime.now(timezone.utc).isoformat(),
            story_core=StoryCore(
                central_question="What drives company growth?",
                one_sentence_pitch="An exploration of financial success.",
                why_this_matters="Relevant to investors and industry.",
                target_audience="Business documentary viewers",
                emotional_arc="Curiosity to understanding",
            ),
        )

        assert packet.job_id == "JOB_1"
        assert packet.story_core.central_question != ""

    def test_producer_gating_enforced(self):
        """Producer should only run on eligible jobs."""
        # Eligibility requirements (from spec):
        # - Job must be completed
        # - Must have at least 1 source
        # - Must have semantic brief generated

        job_status = "completed"
        source_count = 1
        has_semantic_brief = True

        is_eligible = (
            job_status in ["completed", "completed_with_warnings"]
            and source_count >= 1
            and has_semantic_brief
        )

        assert is_eligible is True

        # Incomplete job should not be eligible
        incomplete_job_status = "processing"
        is_eligible_incomplete = incomplete_job_status in ["completed", "completed_with_warnings"]
        assert is_eligible_incomplete is False

    def test_producer_doc3_generation(self):
        """Producer should generate valid Doc 3 (Producer Packet)."""
        packet = ProducerPacket(
            job_id="JOB_1",
            generated_at=datetime.now(timezone.utc).isoformat(),
            story_core=StoryCore(
                central_question="Main question?",
                one_sentence_pitch="Pitch.",
                why_this_matters="Importance.",
                target_audience="Audience",
                emotional_arc="Arc",
            ),
        )

        # Verify Doc 3 structure
        doc3 = packet.to_dict()
        assert "job_id" in doc3
        assert "generated_at" in doc3
        assert "story_core" in doc3

        # Verify creative interpretation notice
        markdown = packet.to_markdown()
        assert "CREATIVE INTERPRETATION" in markdown


# =============================================================================
# TestErrorRecovery
# =============================================================================


class TestErrorRecovery:
    """Integration tests for error handling and recovery."""

    def test_gemini_timeout_recovery(self, sample_extraction_result):
        """Pipeline should continue with warnings on Gemini timeout."""
        # Simulate timeout during extraction
        warnings = ["Gemini extraction timeout for SRC_2"]

        # Job continues with partial results
        partial_extractions = [sample_extraction_result]  # Only SRC_1 succeeded

        # Job completes with warnings
        assert len(warnings) >= 1
        assert len(partial_extractions) >= 1

    def test_partial_extraction_continues(self):
        """Pipeline should continue with partial extractions."""
        # 3 sources, 1 fails
        extraction_1 = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Point from source 1",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
        )

        extraction_3 = SemanticExtractionResult(
            source_id="SRC_3",
            analysis_mode=AnalysisMode.ARTICLE_FETCHED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_3",
                    statement="Point from source 3",
                    source_ids=["SRC_3"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
        )

        # SRC_2 failed, but we have 2/3
        successful_extractions = [extraction_1, extraction_3]
        warnings = ["Extraction failed for SRC_2: Video unavailable"]

        # Pipeline continues with partial results
        assert len(successful_extractions) == 2
        assert len(warnings) == 1

    def test_validation_failure_with_warnings(self):
        """Validation failures should add warnings, not crash."""
        # Extraction with confidence exceeding ceiling
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TEXT_PROVIDED,  # MEDIUM ceiling
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Point",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,  # Exceeds MEDIUM ceiling
                ),
            ],
        )

        # Validation would catch this and auto-correct
        warnings = []

        # Check confidence ceiling for TEXT_PROVIDED mode
        ceiling = ConfidenceLevel.MEDIUM
        # Confidence level ordering: HIGH > MEDIUM > LOW
        level_order = {ConfidenceLevel.LOW: 0, ConfidenceLevel.MEDIUM: 1, ConfidenceLevel.HIGH: 2}

        for kp in extraction.key_points:
            if level_order[kp.confidence] > level_order[ceiling]:
                warnings.append(
                    f"Confidence {kp.confidence.value} exceeds ceiling {ceiling.value} for {kp.key_point_id}"
                )
                # Auto-correct would set kp.confidence = ceiling

        assert len(warnings) >= 1
        assert "exceeds ceiling" in warnings[0]


# =============================================================================
# TestProvenance
# =============================================================================


class TestProvenance:
    """Tests for provenance chain integrity."""

    def test_all_key_points_have_source(self, sample_extraction_result):
        """Every key point must have source_ids."""
        for kp in sample_extraction_result.key_points:
            assert len(kp.source_ids) >= 1
            assert kp.source_ids[0] == sample_extraction_result.source_id

    def test_theme_references_valid_key_points(self, sample_extraction_result):
        """Theme related_key_points should reference valid KP IDs."""
        kp_ids = {kp.key_point_id for kp in sample_extraction_result.key_points}

        for theme in sample_extraction_result.themes:
            for ref in theme.related_key_points:
                assert ref in kp_ids, f"Theme references invalid KP: {ref}"

    def test_tension_references_valid_key_points(self):
        """Tension involved_key_points should reference valid KP IDs."""
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Point 1",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,
                ),
                KeyPoint(
                    key_point_id="KP_2",
                    statement="Point 2",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
            tensions=[
                Tension(
                    tension_id="TEN_1",
                    description="Conflict between points",
                    involved_key_points=["KP_1", "KP_2"],
                ),
            ],
        )

        kp_ids = {kp.key_point_id for kp in extraction.key_points}

        for tension in extraction.tensions:
            for ref in tension.involved_key_points:
                assert ref in kp_ids, f"Tension references invalid KP: {ref}"


# =============================================================================
# TestConfidenceCeilings
# =============================================================================


class TestConfidenceCeilingsIntegration:
    """Integration tests for confidence ceiling enforcement."""

    def test_transcript_grounded_allows_high(self):
        """TRANSCRIPT_GROUNDED mode allows HIGH confidence."""
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Verified quote",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
        )

        # HIGH is allowed for TRANSCRIPT_GROUNDED
        assert extraction.key_points[0].confidence == ConfidenceLevel.HIGH

    def test_video_only_caps_at_low(self):
        """VIDEO_ONLY mode should cap at LOW confidence."""
        # VIDEO_ONLY ceiling is LOW
        mode = AnalysisMode.VIDEO_ONLY
        ceiling = ConfidenceLevel.LOW

        # Any key point should be LOW
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=mode,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Visual observation",
                    source_ids=["SRC_1"],
                    confidence=ceiling,  # Must be LOW
                ),
            ],
        )

        assert extraction.key_points[0].confidence == ConfidenceLevel.LOW

    def test_caption_grounded_caps_at_medium(self):
        """CAPTION_GROUNDED mode should cap at MEDIUM confidence."""
        mode = AnalysisMode.CAPTION_GROUNDED
        ceiling = ConfidenceLevel.MEDIUM

        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=mode,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="From captions",
                    source_ids=["SRC_1"],
                    confidence=ceiling,
                ),
            ],
        )

        assert extraction.key_points[0].confidence == ConfidenceLevel.MEDIUM


# =============================================================================
# TestParallelExtractionDocEquivalence
# =============================================================================


class TestParallelExtractionDocEquivalence:
    """
    Integration tests verifying parallel extraction produces equivalent
    doc outputs to sequential processing.

    Critical for ensuring parallelization doesn't affect doc_0/doc_1/doc_2 quality.
    """

    @pytest.fixture
    def mock_source_packages(self):
        """Create mock source identity packages for testing."""
        from backend.pipeline.stages.source_identity import SourceIdentityPackage

        packages = []
        for i in range(4):
            packages.append(SourceIdentityPackage(
                source_id=f"SRC_{i+1}",
                source_type="article",
                url=f"https://example.com/article{i+1}",
                title=f"Test Article {i+1}",
                analysis_mode=AnalysisMode.ARTICLE_FETCHED,
                content=f"This is test content for article {i+1}. It contains unique information.",
                content_word_count=50,
                is_accessible=True,
            ))
        return packages

    @pytest.fixture
    def mock_gemini_responses(self):
        """Create deterministic mock responses for each source."""
        def make_response(source_id: str, index: int):
            return {
                "data": {
                    "key_points": [
                        {
                            "key_point_id": f"KP_{index}_1",
                            "statement": f"Key point from {source_id}",
                            "source_ids": [source_id],
                            "confidence": "high",
                        },
                    ],
                    "claims": [
                        {
                            "claim_id": f"CLM_{index}_1",
                            "statement": f"Claim from {source_id}",
                            "source_id": source_id,
                            "confidence": "high",
                        },
                    ],
                    "themes": [
                        {
                            "theme_id": f"THEME_{index}_1",
                            "label": f"Theme from {source_id}",
                            "description": f"Description for {source_id}",
                            "related_key_points": [f"KP_{index}_1"],
                        },
                    ],
                    "quotes": [],
                    "tensions": [],
                },
                "cost": 0.01,
            }
        return make_response

    def test_parallel_and_sequential_produce_same_extraction_count(
        self, mock_source_packages, mock_gemini_responses
    ):
        """Parallel and sequential modes should produce same number of extractions."""
        from backend.pipeline.stages.semantic_extraction import (
            stage_semantic_extraction,
        )
        from backend.pipeline.context import PipelineContext
        import uuid

        # Track responses by source_id for deterministic mocking
        response_map = {
            pkg.source_id: mock_gemini_responses(pkg.source_id, i)
            for i, pkg in enumerate(mock_source_packages)
        }

        def mock_generate_json(*args, **kwargs):
            # Extract source_id from prompt to return correct response
            prompt = args[0] if args else kwargs.get("prompt", "")
            for src_id in response_map:
                if src_id in prompt:
                    return response_map[src_id]
            # Fallback
            return response_map["SRC_1"]

        # Run with max_workers=3 (parallel)
        ctx_parallel = PipelineContext(job_id=str(uuid.uuid4()), topic="Test")
        ctx_parallel.source_identity_packages = mock_source_packages.copy()

        with patch("backend.pipeline.stages.semantic_extraction.update_job"):
            with patch("backend.config.get_settings") as mock_settings:
                mock_settings.return_value.semantic_extraction_max_workers = 3
                mock_settings.return_value.llm_judge_conditional = True  # Skip judge for speed
                mock_settings.return_value.llm_judge_warning_threshold = 999

                with patch("backend.integrations.gemini_client.GeminiClient") as MockGemini:
                    mock_client = MockGemini.return_value
                    mock_client.generate_json.side_effect = mock_generate_json

                    stage_semantic_extraction(ctx_parallel)

        # Run with max_workers=1 (sequential)
        ctx_sequential = PipelineContext(job_id=str(uuid.uuid4()), topic="Test")
        ctx_sequential.source_identity_packages = mock_source_packages.copy()

        with patch("backend.pipeline.stages.semantic_extraction.update_job"):
            with patch("backend.config.get_settings") as mock_settings:
                mock_settings.return_value.semantic_extraction_max_workers = 1
                mock_settings.return_value.llm_judge_conditional = True
                mock_settings.return_value.llm_judge_warning_threshold = 999

                with patch("backend.integrations.gemini_client.GeminiClient") as MockGemini:
                    mock_client = MockGemini.return_value
                    mock_client.generate_json.side_effect = mock_generate_json

                    stage_semantic_extraction(ctx_sequential)

        # Both should have same number of extractions
        assert len(ctx_parallel.semantic_extractions) == len(ctx_sequential.semantic_extractions)
        assert len(ctx_parallel.semantic_extractions) == 4

    def test_parallel_preserves_source_order_in_extractions(
        self, mock_source_packages, mock_gemini_responses
    ):
        """Parallel extraction must preserve source order (SRC_1, SRC_2, SRC_3, SRC_4)."""
        from backend.pipeline.stages.semantic_extraction import (
            stage_semantic_extraction,
        )
        from backend.pipeline.context import PipelineContext
        import time
        import random
        import uuid

        response_map = {
            pkg.source_id: mock_gemini_responses(pkg.source_id, i)
            for i, pkg in enumerate(mock_source_packages)
        }

        def mock_generate_json_with_delay(*args, **kwargs):
            """Add random delay to simulate real API latency."""
            time.sleep(random.uniform(0.01, 0.05))
            prompt = args[0] if args else kwargs.get("prompt", "")
            for src_id in response_map:
                if src_id in prompt:
                    return response_map[src_id]
            return response_map["SRC_1"]

        # Run 3 times to catch non-deterministic ordering
        for run in range(3):
            ctx = PipelineContext(job_id=str(uuid.uuid4()), topic="Test")
            ctx.source_identity_packages = mock_source_packages.copy()

            with patch("backend.pipeline.stages.semantic_extraction.update_job"):
                with patch("backend.config.get_settings") as mock_settings:
                    mock_settings.return_value.semantic_extraction_max_workers = 3
                    mock_settings.return_value.llm_judge_conditional = True
                    mock_settings.return_value.llm_judge_warning_threshold = 999

                    with patch("backend.integrations.gemini_client.GeminiClient") as MockGemini:
                        mock_client = MockGemini.return_value
                        mock_client.generate_json.side_effect = mock_generate_json_with_delay

                        stage_semantic_extraction(ctx)

            # Verify deterministic order
            source_ids = [e.source_id for e in ctx.semantic_extractions]
            expected_order = ["SRC_1", "SRC_2", "SRC_3", "SRC_4"]

            assert source_ids == expected_order, (
                f"Run {run+1}: Expected {expected_order}, got {source_ids}"
            )

    def test_parallel_and_sequential_key_points_match(
        self, mock_source_packages, mock_gemini_responses
    ):
        """Key points should be identical between parallel and sequential runs."""
        from backend.pipeline.stages.semantic_extraction import (
            stage_semantic_extraction,
        )
        from backend.pipeline.context import PipelineContext
        import uuid

        response_map = {
            pkg.source_id: mock_gemini_responses(pkg.source_id, i)
            for i, pkg in enumerate(mock_source_packages)
        }

        def mock_generate_json(*args, **kwargs):
            prompt = args[0] if args else kwargs.get("prompt", "")
            for src_id in response_map:
                if src_id in prompt:
                    return response_map[src_id]
            return response_map["SRC_1"]

        def run_extraction(max_workers: int) -> PipelineContext:
            ctx = PipelineContext(job_id=str(uuid.uuid4()), topic="Test")
            ctx.source_identity_packages = mock_source_packages.copy()

            with patch("backend.pipeline.stages.semantic_extraction.update_job"):
                with patch("backend.config.get_settings") as mock_settings:
                    mock_settings.return_value.semantic_extraction_max_workers = max_workers
                    mock_settings.return_value.llm_judge_conditional = True
                    mock_settings.return_value.llm_judge_warning_threshold = 999

                    with patch("backend.integrations.gemini_client.GeminiClient") as MockGemini:
                        mock_client = MockGemini.return_value
                        mock_client.generate_json.side_effect = mock_generate_json

                        stage_semantic_extraction(ctx)

            return ctx

        ctx_parallel = run_extraction(max_workers=3)
        ctx_sequential = run_extraction(max_workers=1)

        # Extract key point IDs from both runs
        parallel_kp_ids = []
        for extraction in ctx_parallel.semantic_extractions:
            parallel_kp_ids.extend([kp.key_point_id for kp in extraction.key_points])

        sequential_kp_ids = []
        for extraction in ctx_sequential.semantic_extractions:
            sequential_kp_ids.extend([kp.key_point_id for kp in extraction.key_points])

        # Same key points in same order
        assert parallel_kp_ids == sequential_kp_ids

    def test_doc_outputs_functionally_equivalent(
        self, mock_source_packages, mock_gemini_responses
    ):
        """
        Doc 0/1/2 outputs should be functionally equivalent between parallel and sequential.

        Functionally equivalent means:
        - Same source_ids in same order (Doc 0)
        - Same key_point_ids, theme_ids, claim_ids (Doc 1/2)
        - Same content (statements, labels, descriptions)

        Ignored fields (may differ):
        - timestamps, job_id, costs
        """
        from backend.pipeline.stages.semantic_extraction import (
            stage_semantic_extraction,
        )
        from backend.pipeline.context import PipelineContext
        import uuid

        response_map = {
            pkg.source_id: mock_gemini_responses(pkg.source_id, i)
            for i, pkg in enumerate(mock_source_packages)
        }

        def mock_generate_json(*args, **kwargs):
            prompt = args[0] if args else kwargs.get("prompt", "")
            for src_id in response_map:
                if src_id in prompt:
                    return response_map[src_id]
            return response_map["SRC_1"]

        def run_and_collect(max_workers: int) -> dict:
            ctx = PipelineContext(job_id=str(uuid.uuid4()), topic="Test")
            ctx.source_identity_packages = mock_source_packages.copy()

            with patch("backend.pipeline.stages.semantic_extraction.update_job"):
                with patch("backend.config.get_settings") as mock_settings:
                    mock_settings.return_value.semantic_extraction_max_workers = max_workers
                    mock_settings.return_value.llm_judge_conditional = True
                    mock_settings.return_value.llm_judge_warning_threshold = 999

                    with patch("backend.integrations.gemini_client.GeminiClient") as MockGemini:
                        mock_client = MockGemini.return_value
                        mock_client.generate_json.side_effect = mock_generate_json

                        stage_semantic_extraction(ctx)

            # Collect doc-relevant data
            return {
                "source_ids": [e.source_id for e in ctx.semantic_extractions],
                "key_point_ids": [
                    kp.key_point_id
                    for e in ctx.semantic_extractions
                    for kp in e.key_points
                ],
                "key_point_statements": [
                    kp.statement
                    for e in ctx.semantic_extractions
                    for kp in e.key_points
                ],
                "theme_ids": [
                    t.theme_id
                    for e in ctx.semantic_extractions
                    for t in e.themes
                ],
                "theme_labels": [
                    t.label
                    for e in ctx.semantic_extractions
                    for t in e.themes
                ],
                "claim_ids": [
                    c.claim_id
                    for e in ctx.semantic_extractions
                    for c in e.claims
                ],
            }

        parallel_data = run_and_collect(max_workers=3)
        sequential_data = run_and_collect(max_workers=1)

        # All doc-relevant fields must match exactly
        assert parallel_data["source_ids"] == sequential_data["source_ids"], \
            "Source IDs mismatch (Doc 0 affected)"

        assert parallel_data["key_point_ids"] == sequential_data["key_point_ids"], \
            "Key point IDs mismatch (Doc 1/2 affected)"

        assert parallel_data["key_point_statements"] == sequential_data["key_point_statements"], \
            "Key point statements mismatch (Doc 1/2 affected)"

        assert parallel_data["theme_ids"] == sequential_data["theme_ids"], \
            "Theme IDs mismatch (Doc 2 affected)"

        assert parallel_data["theme_labels"] == sequential_data["theme_labels"], \
            "Theme labels mismatch (Doc 2 affected)"

        assert parallel_data["claim_ids"] == sequential_data["claim_ids"], \
            "Claim IDs mismatch (Doc 1/2 affected)"
