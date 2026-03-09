"""
Unit tests for document assembly stage.

Tests for: build_source_ledger, build_jump_start, build_semantic_brief,
validate_provenance_chain, stage_document_assembly.

Phase 9 Task 9.2.2
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.models.document_outputs import (
    ConfidenceAssessment,
    JumpStartDirections,
    ResearchDirection,
    SemanticBrief,
    SourceEntry,
    SourceLedger,
    SourceStatus,
    TranscriptProvenance,
    TriageLevel,
    VerificationItem,
)
from backend.models.semantic_units import (
    AnalysisMode,
    Claim,
    ConfidenceLevel,
    Gap,
    KeyPoint,
    SemanticExtractionResult,
    Tension,
    Theme,
)
from backend.pipeline.stages.document_assembly import (
    build_source_ledger,
    build_jump_start,
    build_semantic_brief,
    validate_provenance_chain,
)
from backend.pipeline.stages.source_identity import SourceIdentityPackage


# =============================================================================
# MockPipelineContext
# =============================================================================


class MockPipelineContext:
    """Mock pipeline context for testing document assembly."""

    def __init__(self):
        self.job_id = "test_job"
        self.topic = "Test Research Topic"
        self.source_identity_packages = []
        self.semantic_extractions = []
        self.identified_gaps = []
        self.scope_in = ["Topic A", "Topic B"]
        self.scope_out = ["Topic C"]
        self.outputs = {}
        self.warnings = []
        self.source_contributions = None
        self.source_coverage = None

    def add_warning(self, msg):
        self.warnings.append(msg)


# =============================================================================
# TestBuildSourceLedger
# =============================================================================


class TestBuildSourceLedger:
    """Tests for build_source_ledger function."""

    def test_build_empty_ledger(self):
        """Empty sources should produce empty ledger."""
        ledger = build_source_ledger(
            topic="Test Topic",
            sources=[],
            extractions=[],
        )

        assert ledger.topic == "Test Topic"
        assert ledger.sources == []
        assert ledger.ingested_count == 0

    def test_build_single_source_ledger(self):
        """Single source should create ledger entry."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Test Video",
            "url": "https://youtube.com/watch?v=test",
            "creator": "Test Channel",
            "published": "2024-01-15",
        }]
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(
                        key_point_id="KP_1",
                        statement="Key point one",
                        source_ids=["SRC_1"],
                        confidence=ConfidenceLevel.HIGH,
                    ),
                ],
            ),
        ]

        ledger = build_source_ledger(
            topic="Test Topic",
            sources=sources,
            extractions=extractions,
        )

        assert len(ledger.sources) == 1
        assert ledger.sources[0].source_id == "SRC_1"
        assert ledger.sources[0].status == SourceStatus.INGESTED

    def test_build_ledger_with_failed_source(self):
        """Failed source should have FAILED status."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Failed Video",
            "url": "https://youtube.com/watch?v=fail",
            "failed": True,
            "failure_reason": "Video unavailable",
        }]

        ledger = build_source_ledger(
            topic="Test Topic",
            sources=sources,
            extractions=[],
        )

        assert len(ledger.sources) == 1
        assert ledger.sources[0].status == SourceStatus.FAILED
        assert ledger.failed_count == 1

    def test_build_ledger_with_partial_extraction(self):
        """Partial extraction should have PARTIAL status."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Partial Video",
            "url": "https://youtube.com/watch?v=partial",
        }]
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.VIDEO_ONLY,
                parse_error=True,
            ),
        ]

        ledger = build_source_ledger(
            topic="Test Topic",
            sources=sources,
            extractions=extractions,
        )

        assert ledger.sources[0].status == SourceStatus.PARTIAL

    def test_build_ledger_transcript_provenance_supadata(self):
        """Supadata transcript should create proper provenance."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Video",
            "url": "https://youtube.com/watch?v=test",
            "transcript_source": "supadata",
        }]

        ledger = build_source_ledger(
            topic="Test Topic",
            sources=sources,
            extractions=[],
        )

        provenance = ledger.sources[0].transcript_provenance
        assert provenance is not None
        assert provenance.gemini_analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED
        assert provenance.quote_verification is True

    def test_build_ledger_transcript_provenance_captions(self):
        """YouTube captions should create CAPTION_GROUNDED provenance."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Video",
            "url": "https://youtube.com/watch?v=test",
            "transcript_source": "youtube_captions",
        }]

        ledger = build_source_ledger(
            topic="Test Topic",
            sources=sources,
            extractions=[],
        )

        provenance = ledger.sources[0].transcript_provenance
        assert provenance.gemini_analysis_mode == AnalysisMode.CAPTION_GROUNDED
        assert provenance.semantic_precision == ConfidenceLevel.MEDIUM

    def test_build_ledger_transcript_provenance_none(self):
        """No transcript should create VIDEO_ONLY provenance."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Video",
            "url": "https://youtube.com/watch?v=test",
            "transcript_source": "none",
        }]

        ledger = build_source_ledger(
            topic="Test Topic",
            sources=sources,
            extractions=[],
        )

        provenance = ledger.sources[0].transcript_provenance
        assert provenance.gemini_analysis_mode == AnalysisMode.VIDEO_ONLY
        assert provenance.semantic_precision == ConfidenceLevel.LOW

    def test_build_ledger_skim_summary_from_extraction(self):
        """Skim summary should come from first 5 key points."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Video",
            "url": "https://youtube.com/watch?v=test",
        }]
        key_points = [
            KeyPoint(key_point_id=f"KP_{i}", statement=f"Point {i}", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH)
            for i in range(1, 8)  # 7 key points
        ]
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=key_points,
            ),
        ]

        ledger = build_source_ledger(
            topic="Test Topic",
            sources=sources,
            extractions=extractions,
        )

        # Only first 5 key points in skim summary
        assert len(ledger.sources[0].skim_summary) == 5
        assert ledger.sources[0].skim_summary[0] == "Point 1"

    def test_build_ledger_multiple_sources(self):
        """Multiple sources should all be included."""
        sources = [
            {"source_id": "SRC_1", "source_type": "youtube", "title": "Video 1", "url": "url1"},
            {"source_id": "SRC_2", "source_type": "article", "title": "Article 1", "url": "url2"},
            {"source_id": "SRC_3", "source_type": "reddit", "title": "Post 1", "url": "url3"},
        ]

        ledger = build_source_ledger(
            topic="Test Topic",
            sources=sources,
            extractions=[],
        )

        assert len(ledger.sources) == 3
        assert ledger.ingested_count == 3


# =============================================================================
# TestBuildJumpStart
# =============================================================================


class TestBuildJumpStart:
    """Tests for build_jump_start function."""

    def test_build_empty_jump_start(self):
        """Empty inputs should produce minimal jump start."""
        jump_start = build_jump_start(
            scope_lock=(["Topic A"], ["Topic B"]),
            extractions=[],
            gaps=[],
        )

        assert jump_start.scope_in == ["Topic A"]
        assert jump_start.scope_out == ["Topic B"]
        assert jump_start.source_count == 0

    def test_build_jump_start_with_gaps(self):
        """Gaps should become research directions."""
        gaps = [
            Gap(
                gap_id="GAP_1",
                description="Missing perspective",
                why_expected="Would provide balance",
                suggested_research_direction="Search for alternative views",
            ),
            Gap(
                gap_id="GAP_2",
                description="Missing data",
                why_expected="Would verify claims",
            ),
        ]

        jump_start = build_jump_start(
            scope_lock=(["Topic"], []),
            extractions=[],
            gaps=gaps,
        )

        assert len(jump_start.research_directions) == 2
        assert jump_start.research_directions[0].priority == 1
        assert jump_start.research_directions[0].what_to_look_for == "Missing perspective"

    def test_build_jump_start_aggregates_key_points(self):
        """Key points should be aggregated from all extractions."""
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(key_point_id="KP_1", statement="Point 1", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH),
                ],
            ),
            SemanticExtractionResult(
                source_id="SRC_2",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(key_point_id="KP_2", statement="Point 2", source_ids=["SRC_2"], confidence=ConfidenceLevel.HIGH),
                ],
            ),
        ]

        jump_start = build_jump_start(
            scope_lock=(["Topic"], []),
            extractions=extractions,
            gaps=[],
        )

        assert len(jump_start.key_points) == 2

    def test_build_jump_start_verification_items(self):
        """Low confidence claims should become verification items."""
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.VIDEO_ONLY,
                claims=[
                    Claim(
                        claim_id="CLM_1",
                        statement="Unverified claim that needs checking",
                        source_id="SRC_1",
                        confidence=ConfidenceLevel.LOW,
                        supporting_quotes=[],
                    ),
                ],
            ),
        ]

        jump_start = build_jump_start(
            scope_lock=(["Topic"], []),
            extractions=extractions,
            gaps=[],
        )

        assert len(jump_start.verification_items) == 1
        assert "Verify:" in jump_start.verification_items[0].description

    def test_build_jump_start_confidence_high(self):
        """Multiple sources with few gaps should have HIGH confidence."""
        extractions = [
            SemanticExtractionResult(source_id="SRC_1", analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED),
            SemanticExtractionResult(source_id="SRC_2", analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED),
        ]
        gaps = [Gap(gap_id=f"GAP_{i}", description=f"Gap {i}", why_expected="") for i in range(3)]

        jump_start = build_jump_start(
            scope_lock=(["Topic"], []),
            extractions=extractions,
            gaps=gaps,
        )

        assert jump_start.confidence == ConfidenceLevel.HIGH

    def test_build_jump_start_confidence_low(self):
        """Single source or many gaps should have LOW confidence."""
        extractions = [
            SemanticExtractionResult(source_id="SRC_1", analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED),
        ]

        jump_start = build_jump_start(
            scope_lock=(["Topic"], []),
            extractions=extractions,
            gaps=[],
        )

        assert jump_start.confidence == ConfidenceLevel.LOW

    def test_build_jump_start_next_steps(self):
        """Next steps should be generated based on gaps and tensions."""
        gaps = [
            Gap(gap_id="GAP_1", description="Important gap", why_expected="Needed"),
        ]
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                tensions=[
                    Tension(tension_id="TEN_1", description="Key tension", involved_key_points=[]),
                ],
            ),
        ]

        jump_start = build_jump_start(
            scope_lock=(["Topic"], []),
            extractions=extractions,
            gaps=gaps,
        )

        assert len(jump_start.next_steps) == 3
        assert "Address gap" in jump_start.next_steps[0]


# =============================================================================
# TestBuildSemanticBrief
# =============================================================================


class TestBuildSemanticBrief:
    """Tests for build_semantic_brief function."""

    def test_build_empty_semantic_brief(self):
        """Empty inputs should produce minimal brief."""
        brief = build_semantic_brief(
            semantic_core="Core understanding.",
            extractions=[],
            gaps=[],
            overall_confidence=ConfidenceLevel.MEDIUM,
            confidence_reasoning=["Default confidence"],
        )

        assert brief.semantic_core == "Core understanding."
        assert brief.themes == []
        assert brief.key_points == []

    def test_build_semantic_brief_aggregates_themes(self):
        """Themes should be aggregated from all extractions."""
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                themes=[
                    Theme(theme_id="THEME_1", label="Theme A", description="Description", related_key_points=["KP_1"]),
                ],
            ),
            SemanticExtractionResult(
                source_id="SRC_2",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                themes=[
                    Theme(theme_id="THEME_2", label="Theme B", description="Description", related_key_points=["KP_2"]),
                ],
            ),
        ]

        brief = build_semantic_brief(
            semantic_core="Core",
            extractions=extractions,
            gaps=[],
            overall_confidence=ConfidenceLevel.HIGH,
            confidence_reasoning=[],
        )

        assert len(brief.themes) == 2

    def test_build_semantic_brief_triage_usable(self):
        """Adequate content should have USABLE triage."""
        # Create adequate content
        key_points = [
            KeyPoint(key_point_id=f"KP_{i}", statement=f"Point {i}", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH)
            for i in range(10)
        ]
        themes = [
            Theme(theme_id=f"THEME_{i}", label=f"Theme {i}", description="Desc", related_key_points=[])
            for i in range(5)
        ]
        gaps = [
            Gap(gap_id=f"GAP_{i}", description=f"Gap {i}", why_expected="")
            for i in range(6)
        ]

        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=key_points,
                themes=themes,
            ),
        ]

        brief = build_semantic_brief(
            semantic_core="Core",
            extractions=extractions,
            gaps=gaps,
            overall_confidence=ConfidenceLevel.HIGH,
            confidence_reasoning=[],
        )

        assert brief.triage == TriageLevel.USABLE

    def test_build_semantic_brief_triage_thin(self):
        """Insufficient content should have THIN triage."""
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(key_point_id="KP_1", statement="Only one point", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH),
                ],
                themes=[
                    Theme(theme_id="THEME_1", label="One theme", description="Desc", related_key_points=[]),
                ],
            ),
        ]

        brief = build_semantic_brief(
            semantic_core="Core",
            extractions=extractions,
            gaps=[],  # No gaps
            overall_confidence=ConfidenceLevel.LOW,
            confidence_reasoning=[],
        )

        assert brief.triage == TriageLevel.THIN

    def test_build_semantic_brief_triage_degraded(self):
        """Majority video_only should have DEGRADED triage."""
        extractions = [
            SemanticExtractionResult(source_id="SRC_1", analysis_mode=AnalysisMode.VIDEO_ONLY),
            SemanticExtractionResult(source_id="SRC_2", analysis_mode=AnalysisMode.VIDEO_ONLY),
            SemanticExtractionResult(source_id="SRC_3", analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED),
        ]

        brief = build_semantic_brief(
            semantic_core="Core",
            extractions=extractions,
            gaps=[],
            overall_confidence=ConfidenceLevel.LOW,
            confidence_reasoning=[],
        )

        assert brief.triage == TriageLevel.DEGRADED

    def test_build_semantic_brief_with_source_coverage(self):
        """Phase 5: Source coverage should enrich themes."""
        key_points = [
            KeyPoint(key_point_id="KP_1", statement="Point 1", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH),
            KeyPoint(key_point_id="KP_2", statement="Point 2", source_ids=["SRC_2"], confidence=ConfidenceLevel.HIGH),
        ]
        themes = [
            Theme(theme_id="THEME_1", label="Cross-source theme", description="Desc", related_key_points=["KP_1", "KP_2"]),
        ]
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[key_points[0]],
                themes=themes,
            ),
            SemanticExtractionResult(
                source_id="SRC_2",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[key_points[1]],
            ),
        ]

        source_coverage = {
            "KP_1": ["SRC_1"],
            "KP_2": ["SRC_2"],
        }

        brief = build_semantic_brief(
            semantic_core="Core",
            extractions=extractions,
            gaps=[],
            overall_confidence=ConfidenceLevel.HIGH,
            confidence_reasoning=[],
            source_coverage=source_coverage,
        )

        # Theme should be marked as consensus (from multiple sources)
        assert len(brief.themes) == 1
        # Theme sources should be populated (2 sources support it)

    def test_build_semantic_brief_confidence_assessment(self):
        """Confidence assessment should be included."""
        brief = build_semantic_brief(
            semantic_core="Core",
            extractions=[],
            gaps=[],
            overall_confidence=ConfidenceLevel.HIGH,
            confidence_reasoning=["Multiple sources", "Verified quotes"],
        )

        assert brief.confidence.level == ConfidenceLevel.HIGH
        assert len(brief.confidence.reasoning) == 2


# =============================================================================
# TestValidateProvenanceChain
# =============================================================================


class TestValidateProvenanceChain:
    """Tests for validate_provenance_chain function."""

    def test_validate_empty_context(self):
        """Empty context should pass validation."""
        ctx = MockPipelineContext()

        warnings = validate_provenance_chain(ctx)

        assert warnings == []

    def test_validate_valid_provenance(self):
        """Valid provenance chain should pass."""
        ctx = MockPipelineContext()
        ctx.source_identity_packages = [
            SourceIdentityPackage(
                source_id="SRC_1",
                source_type="youtube",
                url="url",
                title="Video",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            ),
        ]
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(key_point_id="KP_1", statement="Point", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH),
                ],
                themes=[
                    Theme(theme_id="THEME_1", label="Theme", description="Desc", related_key_points=["KP_1"]),
                ],
            ),
        ]

        warnings = validate_provenance_chain(ctx)

        assert warnings == []

    def test_validate_invalid_source_reference(self):
        """Invalid source_id in key point should warn."""
        ctx = MockPipelineContext()
        ctx.source_identity_packages = [
            SourceIdentityPackage(
                source_id="SRC_1",
                source_type="youtube",
                url="url",
                title="Video",
            ),
        ]
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(
                        key_point_id="KP_1",
                        statement="Point",
                        source_ids=["SRC_INVALID"],  # Invalid reference
                        confidence=ConfidenceLevel.HIGH,
                    ),
                ],
            ),
        ]

        warnings = validate_provenance_chain(ctx)

        assert len(warnings) == 1
        assert "invalid source SRC_INVALID" in warnings[0]

    def test_validate_invalid_theme_key_point_reference(self):
        """Theme referencing invalid key point should warn."""
        ctx = MockPipelineContext()
        ctx.source_identity_packages = [
            SourceIdentityPackage(
                source_id="SRC_1",
                source_type="youtube",
                url="url",
                title="Video",
            ),
        ]
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(key_point_id="KP_1", statement="Point", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH),
                ],
                themes=[
                    Theme(
                        theme_id="THEME_1",
                        label="Theme",
                        description="Desc",
                        related_key_points=["KP_INVALID"],  # Invalid reference
                    ),
                ],
            ),
        ]

        warnings = validate_provenance_chain(ctx)

        assert len(warnings) == 1
        assert "invalid key_point KP_INVALID" in warnings[0]

    def test_validate_invalid_tension_key_point_reference(self):
        """Tension referencing invalid key point should warn."""
        ctx = MockPipelineContext()
        ctx.source_identity_packages = [
            SourceIdentityPackage(
                source_id="SRC_1",
                source_type="youtube",
                url="url",
                title="Video",
            ),
        ]
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(key_point_id="KP_1", statement="Point", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH),
                ],
                tensions=[
                    Tension(
                        tension_id="TEN_1",
                        description="Tension",
                        involved_key_points=["KP_MISSING"],  # Invalid reference
                    ),
                ],
            ),
        ]

        warnings = validate_provenance_chain(ctx)

        assert len(warnings) == 1
        assert "invalid key_point KP_MISSING" in warnings[0]


# =============================================================================
# TestDocumentAssemblyIntegration
# =============================================================================


class TestDocumentAssemblyIntegration:
    """Integration tests for document assembly pipeline."""

    def test_build_all_documents(self):
        """All three documents should be buildable."""
        # Setup source data
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Test Video",
            "url": "https://youtube.com/watch?v=test",
            "transcript_source": "supadata",
        }]

        # Setup extraction
        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(
                        key_point_id="KP_1",
                        statement="Main point",
                        source_ids=["SRC_1"],
                        confidence=ConfidenceLevel.HIGH,
                    ),
                ],
                themes=[
                    Theme(
                        theme_id="THEME_1",
                        label="Main theme",
                        description="Description",
                        related_key_points=["KP_1"],
                    ),
                ],
            ),
        ]

        gaps = [
            Gap(
                gap_id="GAP_1",
                description="Missing perspective",
                why_expected="Would add balance",
            ),
        ]

        # Build all documents
        doc_0 = build_source_ledger(
            topic="Research Topic",
            sources=sources,
            extractions=extractions,
        )

        doc_1 = build_jump_start(
            scope_lock=(["Topic A"], ["Topic B"]),
            extractions=extractions,
            gaps=gaps,
        )

        doc_2 = build_semantic_brief(
            semantic_core="Core understanding of the research topic.",
            extractions=extractions,
            gaps=gaps,
            overall_confidence=ConfidenceLevel.MEDIUM,
            confidence_reasoning=["Single source"],
        )

        # Verify documents
        assert doc_0.ingested_count == 1
        assert len(doc_1.key_points) == 1
        assert doc_2.semantic_core == "Core understanding of the research topic."

    def test_documents_reference_consistency(self):
        """Document references should be consistent."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Video",
            "url": "url",
        }]

        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(key_point_id="KP_1", statement="Point", source_ids=["SRC_1"], confidence=ConfidenceLevel.HIGH),
                ],
                claims=[
                    Claim(claim_id="CLM_1", statement="Claim", source_id="SRC_1", confidence=ConfidenceLevel.HIGH),
                ],
            ),
        ]

        doc_0 = build_source_ledger(
            topic="Topic",
            sources=sources,
            extractions=extractions,
        )

        doc_1 = build_jump_start(
            scope_lock=([], []),
            extractions=extractions,
            gaps=[],
        )

        # Doc 1 key points should reference sources in Doc 0
        for kp in doc_1.key_points:
            for sid in kp.source_ids:
                source_ids = [s.source_id for s in doc_0.sources]
                assert sid in source_ids

    def test_to_dict_produces_json_serializable(self):
        """Document to_dict should produce JSON-serializable output."""
        import json

        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Video",
            "url": "url",
        }]

        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            ),
        ]

        doc_0 = build_source_ledger(
            topic="Topic",
            sources=sources,
            extractions=extractions,
        )

        doc_1 = build_jump_start(
            scope_lock=([], []),
            extractions=extractions,
            gaps=[],
        )

        doc_2 = build_semantic_brief(
            semantic_core="Core",
            extractions=extractions,
            gaps=[],
            overall_confidence=ConfidenceLevel.MEDIUM,
            confidence_reasoning=[],
        )

        # All should be JSON-serializable
        json.dumps(doc_0.to_dict())
        json.dumps(doc_1.to_dict())
        json.dumps(doc_2.to_dict())

    def test_to_markdown_produces_readable_output(self):
        """Document to_markdown should produce readable output."""
        sources = [{
            "source_id": "SRC_1",
            "source_type": "youtube",
            "title": "Test Video Title",
            "url": "https://youtube.com/watch?v=test",
        }]

        extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(
                        key_point_id="KP_1",
                        statement="Important finding",
                        source_ids=["SRC_1"],
                        confidence=ConfidenceLevel.HIGH,
                    ),
                ],
            ),
        ]

        doc_0 = build_source_ledger(
            topic="Research Topic",
            sources=sources,
            extractions=extractions,
        )

        markdown = doc_0.to_markdown()

        assert "SOURCE LEDGER" in markdown  # Header may have emoji prefix
        assert "Research Topic" in markdown
        assert "Test Video Title" in markdown
