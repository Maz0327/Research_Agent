"""
Unit tests for document output models.

Tests for: SourceStatus, TriageLevel, TranscriptProvenance, SourceEntry,
SourceLedger, JumpStartDirections, SemanticBrief, ProducerPacket,
CrossReferenceNotes, AddendumSection.

Phase 9 Task 9.1.2
"""
import pytest
from datetime import datetime, timezone

from backend.models.document_outputs import (
    AddendumSection,
    ConfidenceAssessment,
    CrossReferenceNotes,
    JumpStartDirections,
    NarrativeAngle,
    ProducerPacket,
    ResearchDirection,
    SemanticBrief,
    SourceEntry,
    SourceLedger,
    SourceStatus,
    StructureOption,
    TranscriptProvenance,
    TriageLevel,
    VerificationItem,
)
from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    Gap,
    KeyPoint,
    SpeculativeObservation,
    Tension,
    Theme,
)


# =============================================================================
# TestSourceStatus
# =============================================================================


class TestSourceStatus:
    """Tests for SourceStatus enum."""

    def test_source_status_values(self):
        """SourceStatus should have correct string values."""
        assert SourceStatus.INGESTED.value == "ingested"
        assert SourceStatus.FAILED.value == "failed"
        assert SourceStatus.PARTIAL.value == "partial"

    def test_all_statuses_exist(self):
        """All expected statuses should be defined."""
        statuses = [SourceStatus.INGESTED, SourceStatus.FAILED, SourceStatus.PARTIAL]
        assert len(statuses) == 3


# =============================================================================
# TestTriageLevel
# =============================================================================


class TestTriageLevel:
    """Tests for TriageLevel enum."""

    def test_triage_level_values(self):
        """TriageLevel should have correct string values."""
        assert TriageLevel.READY.value == "ready"
        assert TriageLevel.USABLE.value == "usable"
        assert TriageLevel.THIN.value == "thin"
        assert TriageLevel.DEGRADED.value == "degraded"
        assert TriageLevel.FAILED.value == "failed"

    def test_all_triage_levels_exist(self):
        """All triage levels should be defined."""
        levels = [
            TriageLevel.READY,
            TriageLevel.USABLE,
            TriageLevel.THIN,
            TriageLevel.DEGRADED,
            TriageLevel.FAILED,
        ]
        assert len(levels) == 5


# =============================================================================
# TestTranscriptProvenance
# =============================================================================


class TestTranscriptProvenance:
    """Tests for TranscriptProvenance dataclass."""

    def test_transcript_provenance_creation(self):
        """TranscriptProvenance should create correctly."""
        provenance = TranscriptProvenance(
            transcript_source="supadata",
            transcript_status="success",
            captions_status="success",
            gemini_analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            quote_verification=True,
            timestamp_grounding=True,
            semantic_precision=ConfidenceLevel.HIGH,
        )
        assert provenance.transcript_source == "supadata"
        assert provenance.transcript_status == "success"
        assert provenance.gemini_analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED
        assert provenance.quote_verification is True
        assert provenance.semantic_precision == ConfidenceLevel.HIGH

    def test_transcript_provenance_with_notes(self):
        """TranscriptProvenance should support optional notes."""
        provenance = TranscriptProvenance(
            transcript_source="whisper",
            transcript_status="success",
            captions_status="missing",
            gemini_analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            quote_verification=True,
            timestamp_grounding=True,
            semantic_precision=ConfidenceLevel.HIGH,
            notes="Whisper fallback used due to Supadata timeout",
        )
        assert provenance.notes == "Whisper fallback used due to Supadata timeout"

    def test_transcript_provenance_to_dict(self):
        """to_dict should return correctly structured dict."""
        provenance = TranscriptProvenance(
            transcript_source="youtube_captions",
            transcript_status="failed",
            captions_status="success",
            gemini_analysis_mode=AnalysisMode.CAPTION_GROUNDED,
            quote_verification=False,
            timestamp_grounding=False,
            semantic_precision=ConfidenceLevel.MEDIUM,
        )
        result = provenance.to_dict()

        assert result["transcript_source"] == "youtube_captions"
        assert result["gemini_analysis_mode"] == "caption_grounded"
        assert result["verification_capabilities"]["quote_verification"] is False
        assert result["verification_capabilities"]["semantic_precision"] == "medium"


# =============================================================================
# TestSourceEntry
# =============================================================================


class TestSourceEntry:
    """Tests for SourceEntry dataclass."""

    def test_source_entry_creation_minimal(self):
        """SourceEntry should create with minimal fields."""
        entry = SourceEntry(
            source_id="SRC_1",
            source_type="youtube",
            title="Test Video",
            url="https://youtube.com/watch?v=test",
        )
        assert entry.source_id == "SRC_1"
        assert entry.source_type == "youtube"
        assert entry.title == "Test Video"
        assert entry.status == SourceStatus.INGESTED

    def test_source_entry_creation_full(self):
        """SourceEntry should create with all fields."""
        provenance = TranscriptProvenance(
            transcript_source="supadata",
            transcript_status="success",
            captions_status="success",
            gemini_analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            quote_verification=True,
            timestamp_grounding=True,
            semantic_precision=ConfidenceLevel.HIGH,
        )
        entry = SourceEntry(
            source_id="SRC_2",
            source_type="youtube",
            title="Full Test Video",
            url="https://youtube.com/watch?v=full",
            status=SourceStatus.INGESTED,
            creator="Test Channel",
            published="2024-01-15",
            duration="15:30",
            skim_summary=["Point 1", "Point 2", "Point 3"],
            claim_ids=["CLM_1", "CLM_2"],
            entity_names=["Entity A", "Entity B"],
            theme_ids=["THEME_1"],
            full_text="Full transcript text here...",
            transcript_provenance=provenance,
        )
        assert entry.creator == "Test Channel"
        assert entry.duration == "15:30"
        assert len(entry.skim_summary) == 3
        assert entry.full_text == "Full transcript text here..."
        assert entry.transcript_provenance is not None

    def test_source_entry_with_failure(self):
        """SourceEntry should track failure info."""
        entry = SourceEntry(
            source_id="SRC_3",
            source_type="article",
            title="Failed Article",
            url="https://example.com/article",
            status=SourceStatus.FAILED,
            failure_reason="URL returned 404",
        )
        assert entry.status == SourceStatus.FAILED
        assert entry.failure_reason == "URL returned 404"

    def test_source_entry_to_dict(self):
        """to_dict should return correctly structured dict."""
        entry = SourceEntry(
            source_id="SRC_1",
            source_type="youtube",
            title="Test Video",
            url="https://youtube.com/watch?v=test",
            skim_summary=["Summary point"],
            claim_ids=["CLM_1"],
            entity_names=["Entity"],
            theme_ids=["THEME_1"],
        )
        result = entry.to_dict()

        assert result["source_id"] == "SRC_1"
        assert result["status"] == "ingested"
        assert result["extracted_index"]["claim_ids"] == ["CLM_1"]
        assert result["extracted_index"]["entity_names"] == ["Entity"]

    def test_source_entry_to_markdown(self):
        """to_markdown should render valid markdown."""
        entry = SourceEntry(
            source_id="SRC_1",
            source_type="youtube",
            title="Test Video",
            url="https://youtube.com/watch?v=test",
            creator="Test Creator",
            skim_summary=["Point one", "Point two"],
            full_text="Full transcript here",
        )
        md = entry.to_markdown()

        assert "### SRC_1:" in md  # New format: "### SRC_1: Title"
        assert "YOUTUBE" in md  # Type shown as badge
        assert "**Creator:** Test Creator" in md  # Bolded metadata
        assert "#### Quick Summary" in md  # Section heading
        assert "Point one" in md
        assert "Full Source Text" in md  # In collapsible details
        assert "Full transcript here" in md


# =============================================================================
# TestSourceLedger
# =============================================================================


class TestSourceLedger:
    """Tests for SourceLedger dataclass (Doc 0)."""

    def test_source_ledger_creation(self):
        """SourceLedger should create correctly."""
        ledger = SourceLedger(
            topic="Investigation into corporate fraud allegations",
        )
        assert ledger.topic == "Investigation into corporate fraud allegations"
        assert ledger.sources == []
        assert ledger.created_at is not None

    def test_source_ledger_with_sources(self):
        """SourceLedger should hold multiple sources."""
        sources = [
            SourceEntry(
                source_id="SRC_1",
                source_type="youtube",
                title="Video 1",
                url="https://youtube.com/1",
            ),
            SourceEntry(
                source_id="SRC_2",
                source_type="article",
                title="Article 1",
                url="https://example.com/article",
            ),
        ]
        ledger = SourceLedger(
            topic="Test topic",
            sources=sources,
        )
        assert len(ledger.sources) == 2

    def test_source_ledger_ingested_count(self):
        """ingested_count should count INGESTED sources."""
        sources = [
            SourceEntry(source_id="SRC_1", source_type="youtube", title="V1", url="url1"),
            SourceEntry(source_id="SRC_2", source_type="youtube", title="V2", url="url2", status=SourceStatus.FAILED),
            SourceEntry(source_id="SRC_3", source_type="youtube", title="V3", url="url3"),
        ]
        ledger = SourceLedger(topic="Test", sources=sources)

        assert ledger.ingested_count == 2
        assert ledger.failed_count == 1

    def test_source_ledger_to_dict(self):
        """to_dict should include source manifest."""
        entry = SourceEntry(
            source_id="SRC_1",
            source_type="youtube",
            title="Test Video",
            url="https://youtube.com/test",
        )
        ledger = SourceLedger(topic="Test topic", sources=[entry])
        result = ledger.to_dict()

        assert result["document_type"] == "source_ledger"
        assert result["topic"] == "Test topic"
        assert len(result["source_manifest"]) == 1
        assert result["source_manifest"][0]["source_id"] == "SRC_1"

    def test_source_ledger_to_markdown(self):
        """to_markdown should render valid markdown."""
        entry = SourceEntry(
            source_id="SRC_1",
            source_type="youtube",
            title="Test Video Title Here",
            url="https://youtube.com/test",
        )
        ledger = SourceLedger(topic="Test topic", sources=[entry])
        md = ledger.to_markdown()

        assert "# SOURCE LEDGER" in md
        assert "**Research Topic:** Test topic" in md  # New format
        assert "## Source Manifest" in md  # Title case
        assert "SRC_1" in md
        assert "## Overview" in md  # New overview section
        assert "Total Sources | 1" in md  # Stats table


# =============================================================================
# TestResearchDirection
# =============================================================================


class TestResearchDirection:
    """Tests for ResearchDirection dataclass."""

    def test_research_direction_creation(self):
        """ResearchDirection should create correctly."""
        direction = ResearchDirection(
            priority=1,
            what_to_look_for="Financial documents from 2019-2020",
            example_queries=["company 10-K filings", "SEC investigations"],
            why_it_matters="Key to verifying financial claims",
        )
        assert direction.priority == 1
        assert direction.what_to_look_for == "Financial documents from 2019-2020"
        assert len(direction.example_queries) == 2
        assert direction.why_it_matters == "Key to verifying financial claims"

    def test_research_direction_to_dict(self):
        """to_dict should return correctly structured dict."""
        direction = ResearchDirection(
            priority=2,
            what_to_look_for="Expert interviews",
            example_queries=["industry expert opinion"],
        )
        result = direction.to_dict()

        assert result["priority"] == 2
        assert "Expert interviews" in result["what_to_look_for"]


# =============================================================================
# TestVerificationItem
# =============================================================================


class TestVerificationItem:
    """Tests for VerificationItem dataclass."""

    def test_verification_item_creation(self):
        """VerificationItem should create correctly."""
        item = VerificationItem(
            item_id="VER_1",
            description="Verify claim about Q3 revenue",
            status="pending",
        )
        assert item.item_id == "VER_1"
        assert item.status == "pending"

    def test_verification_item_with_notes(self):
        """VerificationItem should support notes."""
        item = VerificationItem(
            item_id="VER_2",
            description="Cross-check timeline",
            status="verified",
            notes="Confirmed via court records",
        )
        assert item.notes == "Confirmed via court records"


# =============================================================================
# TestJumpStartDirections
# =============================================================================


class TestJumpStartDirections:
    """Tests for JumpStartDirections dataclass (Doc 1)."""

    def test_jump_start_creation_minimal(self):
        """JumpStartDirections should create with minimal fields."""
        jump_start = JumpStartDirections()
        assert jump_start.scope_in == []
        assert jump_start.scope_out == []
        assert jump_start.source_count == 0
        assert jump_start.next_steps == []

    def test_jump_start_creation_full(self):
        """JumpStartDirections should create with all fields."""
        kp = KeyPoint(
            key_point_id="KP_1",
            statement="Key point statement",
            source_ids=["SRC_1"],
        )
        gap = Gap(
            gap_id="GAP_1",
            description="Missing information",
            why_expected="Standard practice",
        )
        direction = ResearchDirection(
            priority=1,
            what_to_look_for="Additional sources",
        )
        jump_start = JumpStartDirections(
            scope_in=["Company financials", "Executive actions"],
            scope_out=["Personal lives", "Unrelated acquisitions"],
            source_count=5,
            perspectives_represented=["Management", "Employees", "Regulators"],
            time_span_covered="2018-2023",
            key_points=[kp],
            gaps=[gap],
            research_directions=[direction],
            next_steps=["Step 1", "Step 2", "Step 3"],
        )
        assert len(jump_start.scope_in) == 2
        assert len(jump_start.scope_out) == 2
        assert len(jump_start.perspectives_represented) == 3
        assert len(jump_start.next_steps) == 3

    def test_jump_start_with_booster_expansion(self):
        """JumpStartDirections should support booster expansion."""
        jump_start = JumpStartDirections(
            source_count=5,
            booster_expansion={"missing_perspectives": [], "search_queries": []},
            booster_expansion_md="## Deep Research Booster\nExpanded content here",
        )
        assert jump_start.booster_expansion is not None
        assert "Deep Research Booster" in jump_start.booster_expansion_md

    def test_jump_start_to_dict(self):
        """to_dict should return correctly structured dict."""
        jump_start = JumpStartDirections(
            scope_in=["Topic A"],
            scope_out=["Topic B"],
            source_count=3,
            next_steps=["Do this"],
        )
        result = jump_start.to_dict()

        assert result["document_type"] == "jump_start"
        assert result["scope_lock"]["in"] == ["Topic A"]
        assert result["scope_lock"]["out"] == ["Topic B"]
        assert result["current_corpus"]["source_count"] == 3

    def test_jump_start_to_dict_with_booster(self):
        """to_dict should include booster expansion when present."""
        jump_start = JumpStartDirections(
            source_count=5,
            booster_expansion={"test": "data"},
            booster_expansion_md="## Booster",
        )
        result = jump_start.to_dict()

        assert "booster_expansion" in result
        assert "booster_expansion_md" in result

    def test_jump_start_to_markdown(self):
        """to_markdown should render valid markdown."""
        jump_start = JumpStartDirections(
            scope_in=["Topic A"],
            scope_out=["Topic B"],
            source_count=3,
            perspectives_represented=["Perspective 1"],
            next_steps=["First step", "Second step", "Third step"],
        )
        md = jump_start.to_markdown()

        assert "# JUMP-START RESEARCH BRIEF" in md
        assert "## SCOPE LOCK" in md
        assert "IN: Topic A" in md
        assert "OUT: Topic B" in md
        assert "## TOP 3 NEXT STEPS (MANDATORY)" in md


# =============================================================================
# TestConfidenceAssessment
# =============================================================================


class TestConfidenceAssessment:
    """Tests for ConfidenceAssessment dataclass."""

    def test_confidence_assessment_creation(self):
        """ConfidenceAssessment should create correctly."""
        assessment = ConfidenceAssessment(
            level=ConfidenceLevel.HIGH,
            reasoning=["Multiple sources agree", "Primary documents available"],
        )
        assert assessment.level == ConfidenceLevel.HIGH
        assert len(assessment.reasoning) == 2

    def test_confidence_assessment_to_dict(self):
        """to_dict should return correctly structured dict."""
        assessment = ConfidenceAssessment(
            level=ConfidenceLevel.MEDIUM,
            reasoning=["Some uncertainty remains"],
        )
        result = assessment.to_dict()

        assert result["level"] == "medium"
        assert "Some uncertainty remains" in result["reasoning"]


# =============================================================================
# TestSemanticBrief
# =============================================================================


class TestSemanticBrief:
    """Tests for SemanticBrief dataclass (Doc 2)."""

    def test_semantic_brief_creation_minimal(self):
        """SemanticBrief should create with minimal fields."""
        brief = SemanticBrief(
            semantic_core="This investigation centers on alleged financial misconduct.",
        )
        assert "financial misconduct" in brief.semantic_core
        assert brief.themes == []
        assert brief.triage == TriageLevel.USABLE

    def test_semantic_brief_creation_full(self):
        """SemanticBrief should create with all fields."""
        theme = Theme(
            theme_id="THEME_1",
            label="Financial Opacity",
            description="Repeated patterns of non-disclosure",
            related_key_points=["KP_1", "KP_2"],
        )
        kp = KeyPoint(
            key_point_id="KP_1",
            statement="Key finding",
            source_ids=["SRC_1"],
        )
        tension = Tension(
            tension_id="TEN_1",
            description="Conflicting accounts",
            involved_key_points=["KP_1", "KP_2"],
        )
        gap = Gap(
            gap_id="GAP_1",
            description="Missing perspective",
            why_expected="Standard practice",
        )
        spec_obs = SpeculativeObservation(
            text="This may indicate intentional obfuscation",
            based_on=["KP_1"],
        )
        brief = SemanticBrief(
            semantic_core="Core issue description",
            semantic_core_based_on=["KP_1", "KP_2"],
            themes=[theme],
            key_points=[kp],
            tensions=[tension],
            gaps=[gap],
            speculative_observations=[spec_obs],
            confidence=ConfidenceAssessment(
                level=ConfidenceLevel.HIGH,
                reasoning=["Strong evidence"],
            ),
        )
        assert len(brief.themes) == 1
        assert len(brief.speculative_observations) == 1

    def test_semantic_brief_passes_minimum_depth_pass(self):
        """passes_minimum_depth should return True when requirements met."""
        # Create enough content to pass
        key_points = [
            KeyPoint(key_point_id=f"KP_{i}", statement=f"Point {i}", source_ids=["SRC_1"])
            for i in range(8)
        ]
        themes = [
            Theme(
                theme_id=f"THEME_{i}",
                label=f"Theme {i}",
                description=f"Description {i}",
                related_key_points=["KP_1", "KP_2"],  # Meets 2+ requirement
            )
            for i in range(4)
        ]
        gaps = [
            Gap(gap_id=f"GAP_{i}", description=f"Gap {i}", why_expected=f"Why {i}")
            for i in range(5)
        ]
        brief = SemanticBrief(
            semantic_core="Core",
            key_points=key_points,
            themes=themes,
            gaps=gaps,
        )
        passes, issues = brief.passes_minimum_depth()

        assert passes is True
        assert len(issues) == 0

    def test_semantic_brief_passes_minimum_depth_fail(self):
        """passes_minimum_depth should return False with issues when requirements not met."""
        brief = SemanticBrief(
            semantic_core="Core",
            key_points=[KeyPoint(key_point_id="KP_1", statement="One", source_ids=["SRC_1"])],
            themes=[Theme(theme_id="THEME_1", label="T", description="D", related_key_points=["KP_1"])],
            gaps=[Gap(gap_id="GAP_1", description="G", why_expected="W")],
        )
        passes, issues = brief.passes_minimum_depth()

        assert passes is False
        assert len(issues) >= 3  # At least 3 issues (key_points, themes, gaps)
        assert any("key points" in issue for issue in issues)
        assert any("themes" in issue for issue in issues)
        assert any("gaps" in issue for issue in issues)

    def test_semantic_brief_to_dict(self):
        """to_dict should return correctly structured dict."""
        brief = SemanticBrief(
            semantic_core="Core issue",
            semantic_core_based_on=["KP_1"],
            triage=TriageLevel.READY,
        )
        result = brief.to_dict()

        assert result["document_type"] == "semantic_brief"
        assert result["semantic_core"]["text"] == "Core issue"
        assert result["triage"] == "ready"

    def test_semantic_brief_to_markdown(self):
        """to_markdown should render valid markdown."""
        theme = Theme(
            theme_id="THEME_1",
            label="Test Theme",
            description="Theme description",
            related_key_points=["KP_1"],
        )
        brief = SemanticBrief(
            semantic_core="This is the core issue",
            themes=[theme],
            confidence=ConfidenceAssessment(
                level=ConfidenceLevel.MEDIUM,
                reasoning=["Reason 1"],
            ),
        )
        md = brief.to_markdown()

        assert "# SEMANTIC RESEARCH BRIEF" in md
        assert "## SEMANTIC CORE" in md
        assert "This is the core issue" in md
        assert "## KEY THEMES" in md
        assert "THEME_1: Test Theme" in md

    def test_semantic_brief_markdown_warning_banner(self):
        """to_markdown should show warning for degraded briefs."""
        brief = SemanticBrief(
            semantic_core="Thin content",
            triage=TriageLevel.THIN,
        )
        md = brief.to_markdown()

        assert "Warning" in md
        assert "limited or one-sided sources" in md


# =============================================================================
# TestNarrativeAngle
# =============================================================================


class TestNarrativeAngle:
    """Tests for NarrativeAngle dataclass."""

    def test_narrative_angle_creation(self):
        """NarrativeAngle should create correctly."""
        angle = NarrativeAngle(
            angle_id="ANGLE_1",
            description="Whistleblower's journey",
            hook="What happens when you speak truth to power?",
            based_on=["THEME_1", "KP_3"],
            confidence=ConfidenceLevel.HIGH,
        )
        assert angle.angle_id == "ANGLE_1"
        assert angle.hook == "What happens when you speak truth to power?"
        assert len(angle.based_on) == 2

    def test_narrative_angle_to_dict(self):
        """to_dict should return correctly structured dict."""
        angle = NarrativeAngle(
            angle_id="ANGLE_1",
            description="Test angle",
            hook="Test hook",
        )
        result = angle.to_dict()

        assert result["angle_id"] == "ANGLE_1"
        assert result["confidence"] == "medium"  # Default


# =============================================================================
# TestStructureOption
# =============================================================================


class TestStructureOption:
    """Tests for StructureOption dataclass."""

    def test_structure_option_creation(self):
        """StructureOption should create correctly."""
        structure = StructureOption(
            structure_type="chronological",
            description="Timeline-based narrative",
            act_breakdown=["Act 1: Setup", "Act 2: Escalation", "Act 3: Resolution"],
            why_it_works="Natural progression helps audience follow complex events",
        )
        assert structure.structure_type == "chronological"
        assert len(structure.act_breakdown) == 3

    def test_structure_option_types(self):
        """StructureOption should support various structure types."""
        types = ["chronological", "thematic", "mystery", "villain_origin"]
        for t in types:
            structure = StructureOption(
                structure_type=t,
                description=f"{t} structure",
            )
            assert structure.structure_type == t


# =============================================================================
# TestProducerPacket
# =============================================================================


class TestProducerPacket:
    """Tests for ProducerPacket dataclass (Doc 3)."""

    def test_producer_packet_creation_minimal(self):
        """ProducerPacket should create with minimal fields."""
        packet = ProducerPacket(
            job_id="job_123",
            story_core="The untold story of corporate deception.",
        )
        assert packet.job_id == "job_123"
        assert "corporate deception" in packet.story_core
        assert packet.triage == TriageLevel.USABLE

    def test_producer_packet_creation_full(self):
        """ProducerPacket should create with all fields."""
        angle = NarrativeAngle(
            angle_id="ANGLE_1",
            description="Main narrative",
            hook="Opening question",
        )
        structure = StructureOption(
            structure_type="mystery",
            description="Mystery-driven",
            act_breakdown=["Setup", "Investigation", "Reveal"],
        )
        packet = ProducerPacket(
            job_id="job_456",
            story_core="Core narrative",
            story_core_based_on=["KP_1", "KP_2"],
            narrative_angles=[angle],
            structure_options=[structure],
            opening_hooks=["Hook 1", "Hook 2"],
            title_concepts=["Title 1", "Title 2"],
            thumbnail_concepts=["Thumbnail 1"],
            call_to_action=["Subscribe for more"],
            sensitivity_notes=["Involves minors"],
            risk_assessment="Medium risk",
            legal_considerations=["Defamation concerns"],
            source_count=5,
            high_confidence_sources=3,
            verification_rate=0.85,
        )
        assert len(packet.narrative_angles) == 1
        assert len(packet.structure_options) == 1
        assert packet.verification_rate == 0.85

    def test_producer_packet_meets_gating_pass(self):
        """meets_gating_requirements should pass with sufficient sources."""
        packet = ProducerPacket(
            job_id="job_123",
            story_core="Core",
            source_count=5,
            high_confidence_sources=2,
        )
        passes, failed = packet.meets_gating_requirements()

        assert passes is True
        assert len(failed) == 0

    def test_producer_packet_meets_gating_fail_sources(self):
        """meets_gating_requirements should fail with insufficient sources."""
        packet = ProducerPacket(
            job_id="job_123",
            story_core="Core",
            source_count=3,  # Below minimum 4
            high_confidence_sources=1,
        )
        passes, failed = packet.meets_gating_requirements()

        assert passes is False
        assert any("sources" in f.lower() for f in failed)

    def test_producer_packet_meets_gating_fail_high_confidence(self):
        """meets_gating_requirements should fail without high-confidence sources."""
        packet = ProducerPacket(
            job_id="job_123",
            story_core="Core",
            source_count=5,
            high_confidence_sources=0,  # No high-confidence sources
        )
        passes, failed = packet.meets_gating_requirements()

        assert passes is False
        assert any("high-confidence" in f.lower() for f in failed)

    def test_producer_packet_to_dict(self):
        """to_dict should return correctly structured dict."""
        packet = ProducerPacket(
            job_id="job_123",
            story_core="Story",
            story_core_based_on=["KP_1"],
            opening_hooks=["Hook"],
            source_count=4,
            high_confidence_sources=2,
            verification_rate=0.75,
        )
        result = packet.to_dict()

        assert result["document_type"] == "producer_packet"
        assert result["job_id"] == "job_123"
        assert result["story_core"]["text"] == "Story"
        assert result["creative_elements"]["opening_hooks"] == ["Hook"]
        assert result["source_quality"]["verification_rate"] == 0.75

    def test_producer_packet_to_markdown(self):
        """to_markdown should render valid markdown."""
        angle = NarrativeAngle(
            angle_id="ANGLE_1",
            description="Test angle",
            hook="Test hook",
        )
        packet = ProducerPacket(
            job_id="job_123",
            story_core="The story core here",
            narrative_angles=[angle],
            opening_hooks=["Opening hook"],
            title_concepts=["Title concept"],
            source_count=5,
            high_confidence_sources=3,
            verification_rate=0.8,
        )
        md = packet.to_markdown()

        assert "# PRODUCER PACKET" in md
        assert "## STORY CORE" in md
        assert "The story core here" in md
        assert "## NARRATIVE ANGLES" in md
        assert "ANGLE_1" in md

    def test_producer_packet_markdown_caution_banner(self):
        """to_markdown should show caution for thin packets."""
        packet = ProducerPacket(
            job_id="job_123",
            story_core="Thin content",
            triage=TriageLevel.DEGRADED,
        )
        md = packet.to_markdown()

        assert "Caution" in md
        assert "limited sources" in md


# =============================================================================
# TestCrossReferenceNotes
# =============================================================================


class TestCrossReferenceNotes:
    """Tests for CrossReferenceNotes dataclass."""

    def test_cross_ref_creation_empty(self):
        """CrossReferenceNotes should create with empty lists."""
        notes = CrossReferenceNotes()
        assert notes.supports == []
        assert notes.contradicts == []
        assert notes.new_tensions == []
        assert notes.new_gaps == []

    def test_cross_ref_supports(self):
        """CrossReferenceNotes should track supporting evidence."""
        notes = CrossReferenceNotes(
            supports=[
                {"new_id": "KP_5", "supports_id": "THEME_1", "reason": "Confirms pattern"},
                {"new_id": "KP_6", "supports_id": "KP_2", "reason": "Additional evidence"},
            ],
        )
        assert len(notes.supports) == 2
        assert notes.supports[0]["reason"] == "Confirms pattern"

    def test_cross_ref_contradicts(self):
        """CrossReferenceNotes should track contradictions."""
        notes = CrossReferenceNotes(
            contradicts=[
                {"new_id": "KP_7", "contradicts_id": "KP_1", "reason": "Different timeline"},
            ],
        )
        assert len(notes.contradicts) == 1
        assert notes.contradicts[0]["contradicts_id"] == "KP_1"

    def test_cross_ref_new_tensions(self):
        """CrossReferenceNotes should track new tensions."""
        tension = Tension(
            tension_id="TEN_NEW_1",
            description="New source contradicts original",
            involved_key_points=["KP_1", "KP_5"],
            is_cross_source=True,
        )
        notes = CrossReferenceNotes(new_tensions=[tension])
        assert len(notes.new_tensions) == 1
        assert notes.new_tensions[0].is_cross_source is True

    def test_cross_ref_to_dict(self):
        """to_dict should return correctly structured dict."""
        notes = CrossReferenceNotes(
            supports=[{"new_id": "KP_5", "supports_id": "THEME_1"}],
            contradicts=[{"new_id": "KP_6", "contradicts_id": "KP_1"}],
        )
        result = notes.to_dict()

        assert len(result["supports"]) == 1
        assert len(result["contradicts"]) == 1

    def test_cross_ref_to_markdown(self):
        """to_markdown should render valid markdown."""
        notes = CrossReferenceNotes(
            supports=[{"new_id": "KP_5", "supports_id": "THEME_1", "reason": "Test reason"}],
            contradicts=[{"new_id": "KP_6", "contradicts_id": "KP_1", "reason": "Conflict"}],
        )
        md = notes.to_markdown()

        assert "## Cross-Reference Notes" in md
        assert "### Supports Existing" in md
        assert "KP_5 **supports** THEME_1" in md
        assert "### Contradictions" in md
        assert "KP_6 **contradicts** KP_1" in md


# =============================================================================
# TestAddendumSection
# =============================================================================


class TestAddendumSection:
    """Tests for AddendumSection dataclass."""

    def test_addendum_creation_empty(self):
        """AddendumSection should create with defaults."""
        addendum = AddendumSection()
        assert addendum.source_ids == []
        assert addendum.new_sources == []
        assert addendum.added_at is not None

    def test_addendum_creation_full(self):
        """AddendumSection should create with all fields."""
        new_source = SourceEntry(
            source_id="SRC_5",
            source_type="youtube",
            title="New Video",
            url="https://youtube.com/new",
        )
        new_kp = KeyPoint(
            key_point_id="KP_10",
            statement="New key point from added source",
            source_ids=["SRC_5"],
        )
        cross_ref = CrossReferenceNotes(
            supports=[{"new_id": "KP_10", "supports_id": "THEME_1"}],
        )
        addendum = AddendumSection(
            source_ids=["SRC_5"],
            new_sources=[new_source],
            new_key_points=[new_kp],
            cross_reference=cross_ref,
        )
        assert len(addendum.new_sources) == 1
        assert len(addendum.new_key_points) == 1
        assert addendum.cross_reference is not None

    def test_addendum_with_cross_reference(self):
        """AddendumSection should properly link cross references."""
        addendum = AddendumSection(
            source_ids=["SRC_5"],
            cross_reference=CrossReferenceNotes(
                supports=[{"new_id": "KP_5", "supports_id": "THEME_1"}],
                new_tensions=[
                    Tension(
                        tension_id="TEN_NEW_1",
                        description="Cross-source tension",
                        involved_key_points=["KP_1", "KP_5"],
                    )
                ],
            ),
        )
        assert len(addendum.cross_reference.supports) == 1
        assert len(addendum.cross_reference.new_tensions) == 1

    def test_addendum_to_dict(self):
        """to_dict should return correctly structured dict."""
        addendum = AddendumSection(
            source_ids=["SRC_5"],
            new_key_points=[
                KeyPoint(key_point_id="KP_10", statement="New", source_ids=["SRC_5"])
            ],
        )
        result = addendum.to_dict()

        assert result["source_ids"] == ["SRC_5"]
        assert len(result["new_key_points"]) == 1

    def test_addendum_to_markdown(self):
        """to_markdown should render valid markdown."""
        addendum = AddendumSection(
            source_ids=["SRC_5", "SRC_6"],
            new_key_points=[
                KeyPoint(key_point_id="KP_10", statement="New finding", source_ids=["SRC_5"])
            ],
            new_themes=[
                Theme(
                    theme_id="THEME_NEW_1",
                    label="New Theme",
                    description="Description",
                    related_key_points=["KP_10"],
                )
            ],
        )
        md = addendum.to_markdown()

        assert "## Addendum" in md
        assert "SRC_5, SRC_6" in md
        assert "### New Key Points" in md
        assert "KP_10: New finding" in md
        assert "### New Themes" in md
        assert "THEME_NEW_1: New Theme" in md
