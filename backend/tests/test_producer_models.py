"""
Unit tests for producer models (Doc 3).

Tests for: HookType, StructureType, TitleTone, SensitivityLevel,
StoryCore, NarrativeAngle, OpeningHook, StructureOption, KeyMoment,
TitleOption, ThumbnailConcept, RiskAssessment, InterviewCandidate,
InterviewSuggestions, BRollSuggestion, ProducerPacket.

Phase 9 Task 9.1.4
"""
import pytest
import json

from backend.models.producer_models import (
    BRollSuggestion,
    HookType,
    InterviewCandidate,
    InterviewSuggestions,
    KeyMoment,
    NarrativeAngle,
    OpeningHook,
    ProducerPacket,
    RiskAssessment,
    SensitivityLevel,
    StoryCore,
    StructureOption,
    StructureType,
    ThumbnailConcept,
    TitleOption,
    TitleTone,
    CREATIVE_INTERPRETATION_NOTICE,
)


# =============================================================================
# TestEnums
# =============================================================================


class TestHookType:
    """Tests for HookType enum."""

    def test_hook_type_values(self):
        """HookType should have correct string values."""
        assert HookType.COLD_OPEN.value == "cold_open"
        assert HookType.PROVOCATIVE_QUESTION.value == "provocative_question"
        assert HookType.SURPRISING_FACT.value == "surprising_fact"
        assert HookType.PERSONAL_STORY.value == "personal_story"
        assert HookType.SCENE_SETTING.value == "scene_setting"

    def test_all_hook_types_exist(self):
        """All expected hook types should be defined."""
        assert len(HookType) == 5


class TestStructureType:
    """Tests for StructureType enum."""

    def test_structure_type_values(self):
        """StructureType should have correct string values."""
        assert StructureType.CHRONOLOGICAL.value == "chronological"
        assert StructureType.THEMATIC.value == "thematic"
        assert StructureType.MYSTERY_REVEAL.value == "mystery_reveal"
        assert StructureType.COMPARE_CONTRAST.value == "compare_contrast"
        assert StructureType.PROBLEM_SOLUTION.value == "problem_solution"

    def test_all_structure_types_exist(self):
        """All expected structure types should be defined."""
        assert len(StructureType) == 5


class TestTitleTone:
    """Tests for TitleTone enum."""

    def test_title_tone_values(self):
        """TitleTone should have correct string values."""
        assert TitleTone.SERIOUS.value == "serious"
        assert TitleTone.PROVOCATIVE.value == "provocative"
        assert TitleTone.CURIOUS.value == "curious"
        assert TitleTone.URGENT.value == "urgent"

    def test_all_title_tones_exist(self):
        """All expected title tones should be defined."""
        assert len(TitleTone) == 4


class TestSensitivityLevel:
    """Tests for SensitivityLevel enum."""

    def test_sensitivity_level_values(self):
        """SensitivityLevel should have correct string values."""
        assert SensitivityLevel.LOW.value == "low"
        assert SensitivityLevel.MEDIUM.value == "medium"
        assert SensitivityLevel.HIGH.value == "high"

    def test_all_sensitivity_levels_exist(self):
        """All expected sensitivity levels should be defined."""
        assert len(SensitivityLevel) == 3


# =============================================================================
# TestStoryCore
# =============================================================================


class TestStoryCore:
    """Tests for StoryCore dataclass."""

    def test_story_core_creation(self):
        """StoryCore should create with all required fields."""
        core = StoryCore(
            central_question="Why did the company fail?",
            one_sentence_pitch="A deep dive into corporate fraud that shook Wall Street.",
            why_this_matters="Affects millions of investors",
            target_audience="Documentary enthusiasts interested in finance",
            emotional_arc="Curiosity → Shock → Understanding",
        )

        assert core.central_question == "Why did the company fail?"
        assert "Wall Street" in core.one_sentence_pitch
        assert core.emotional_arc == "Curiosity → Shock → Understanding"

    def test_story_core_to_dict(self):
        """to_dict should return all fields."""
        core = StoryCore(
            central_question="Question",
            one_sentence_pitch="Pitch",
            why_this_matters="Importance",
            target_audience="Audience",
            emotional_arc="Arc",
        )
        result = core.to_dict()

        assert result["central_question"] == "Question"
        assert result["one_sentence_pitch"] == "Pitch"
        assert result["why_this_matters"] == "Importance"
        assert result["target_audience"] == "Audience"
        assert result["emotional_arc"] == "Arc"


# =============================================================================
# TestNarrativeAngle
# =============================================================================


class TestNarrativeAngle:
    """Tests for NarrativeAngle dataclass."""

    def test_narrative_angle_creation_minimal(self):
        """NarrativeAngle should create with minimal fields."""
        angle = NarrativeAngle(
            angle_id="ANGLE_1",
            title="The Whistleblower's Journey",
            description="Follow the insider who exposed it all",
        )

        assert angle.angle_id == "ANGLE_1"
        assert angle.strengths == []
        assert angle.weaknesses == []

    def test_narrative_angle_creation_full(self):
        """NarrativeAngle should create with all fields."""
        angle = NarrativeAngle(
            angle_id="ANGLE_1",
            title="The Whistleblower's Journey",
            description="Follow the insider who exposed it all",
            strengths=["Personal", "Emotional"],
            weaknesses=["Limited scope"],
            best_for="Character-driven stories",
            key_sources=["SRC_1", "SRC_3"],
        )

        assert len(angle.strengths) == 2
        assert angle.best_for == "Character-driven stories"
        assert "SRC_1" in angle.key_sources

    def test_narrative_angle_to_dict(self):
        """to_dict should return all fields."""
        angle = NarrativeAngle(
            angle_id="ANGLE_1",
            title="Test",
            description="Test description",
            strengths=["Strength 1"],
            key_sources=["SRC_1"],
        )
        result = angle.to_dict()

        assert result["angle_id"] == "ANGLE_1"
        assert result["strengths"] == ["Strength 1"]
        assert result["key_sources"] == ["SRC_1"]


# =============================================================================
# TestOpeningHook
# =============================================================================


class TestOpeningHook:
    """Tests for OpeningHook dataclass."""

    def test_opening_hook_creation(self):
        """OpeningHook should create correctly."""
        hook = OpeningHook(
            hook_type=HookType.COLD_OPEN,
            content="The phone rang at 3am. It was the call that would change everything.",
            tone="suspenseful",
            source_basis=["SRC_1"],
        )

        assert hook.hook_type == HookType.COLD_OPEN
        assert "3am" in hook.content
        assert hook.tone == "suspenseful"

    def test_opening_hook_to_dict(self):
        """to_dict should serialize enum as string value."""
        hook = OpeningHook(
            hook_type=HookType.PROVOCATIVE_QUESTION,
            content="What if everything you knew was wrong?",
            tone="curious",
        )
        result = hook.to_dict()

        assert result["hook_type"] == "provocative_question"
        assert result["tone"] == "curious"

    def test_all_hook_types_work(self):
        """All hook types should work in OpeningHook."""
        for hook_type in HookType:
            hook = OpeningHook(
                hook_type=hook_type,
                content="Test content",
                tone="test",
            )
            assert hook.hook_type == hook_type


# =============================================================================
# TestStructureOption
# =============================================================================


class TestStructureOption:
    """Tests for StructureOption dataclass."""

    def test_structure_option_creation(self):
        """StructureOption should create correctly."""
        option = StructureOption(
            structure_type=StructureType.CHRONOLOGICAL,
            description="Tell the story in order of events",
            section_breakdown=["Early years", "The crisis", "Aftermath"],
            pros=["Easy to follow"],
            cons=["May feel predictable"],
        )

        assert option.structure_type == StructureType.CHRONOLOGICAL
        assert len(option.section_breakdown) == 3
        assert "Easy to follow" in option.pros

    def test_structure_option_to_dict(self):
        """to_dict should serialize enum as string value."""
        option = StructureOption(
            structure_type=StructureType.MYSTERY_REVEAL,
            description="Build to a reveal",
        )
        result = option.to_dict()

        assert result["structure_type"] == "mystery_reveal"

    def test_all_structure_types_work(self):
        """All structure types should work in StructureOption."""
        for struct_type in StructureType:
            option = StructureOption(
                structure_type=struct_type,
                description="Test",
            )
            assert option.structure_type == struct_type


# =============================================================================
# TestKeyMoment
# =============================================================================


class TestKeyMoment:
    """Tests for KeyMoment dataclass."""

    def test_key_moment_creation_minimal(self):
        """KeyMoment should create with minimal fields."""
        moment = KeyMoment(
            moment="The CEO's resignation announcement",
            source_id="SRC_1",
        )

        assert moment.moment == "The CEO's resignation announcement"
        assert moment.timestamp is None

    def test_key_moment_creation_full(self):
        """KeyMoment should create with all fields."""
        moment = KeyMoment(
            moment="The CEO's resignation announcement",
            source_id="SRC_1",
            timestamp="5:32",
            why_compelling="Emotional turning point",
            potential_use="Opening scene",
        )

        assert moment.timestamp == "5:32"
        assert moment.potential_use == "Opening scene"

    def test_key_moment_to_dict(self):
        """to_dict should return all fields."""
        moment = KeyMoment(
            moment="Test moment",
            source_id="SRC_1",
            timestamp="1:00",
        )
        result = moment.to_dict()

        assert result["moment"] == "Test moment"
        assert result["source_id"] == "SRC_1"
        assert result["timestamp"] == "1:00"


# =============================================================================
# TestTitleOption
# =============================================================================


class TestTitleOption:
    """Tests for TitleOption dataclass."""

    def test_title_option_creation_minimal(self):
        """TitleOption should create with minimal fields."""
        title = TitleOption(title="The Fall of Giants")

        assert title.title == "The Fall of Giants"
        assert title.subtitle is None
        assert title.tone == TitleTone.SERIOUS  # Default

    def test_title_option_creation_full(self):
        """TitleOption should create with all fields."""
        title = TitleOption(
            title="The Fall of Giants",
            subtitle="How corruption brought down an empire",
            tone=TitleTone.PROVOCATIVE,
            seo_considerations="Include 'scandal' for search",
        )

        assert title.subtitle == "How corruption brought down an empire"
        assert title.tone == TitleTone.PROVOCATIVE
        assert "scandal" in title.seo_considerations

    def test_title_option_to_dict(self):
        """to_dict should serialize tone as string value."""
        title = TitleOption(
            title="Test",
            tone=TitleTone.URGENT,
        )
        result = title.to_dict()

        assert result["tone"] == "urgent"


# =============================================================================
# TestThumbnailConcept
# =============================================================================


class TestThumbnailConcept:
    """Tests for ThumbnailConcept dataclass."""

    def test_thumbnail_concept_creation(self):
        """ThumbnailConcept should create correctly."""
        concept = ThumbnailConcept(
            concept="Split image showing before/after",
            visual_elements=["CEO portrait", "Empty building"],
            text_overlay="THE TRUTH",
            emotional_appeal="Contrast creates intrigue",
        )

        assert "before/after" in concept.concept
        assert len(concept.visual_elements) == 2
        assert concept.text_overlay == "THE TRUTH"

    def test_thumbnail_concept_to_dict(self):
        """to_dict should return all fields."""
        concept = ThumbnailConcept(
            concept="Test concept",
            visual_elements=["Element 1"],
        )
        result = concept.to_dict()

        assert result["concept"] == "Test concept"
        assert result["visual_elements"] == ["Element 1"]


# =============================================================================
# TestRiskAssessment
# =============================================================================


class TestRiskAssessment:
    """Tests for RiskAssessment dataclass."""

    def test_risk_assessment_creation(self):
        """RiskAssessment should create correctly."""
        risk = RiskAssessment(
            sensitivity_level=SensitivityLevel.HIGH,
            potential_issues=["Defamation risk", "Privacy concerns"],
            mitigation_suggestions=["Get legal review", "Anonymize sources"],
            legal_considerations=["Check fair use"],
            ethical_considerations=["Protect whistleblower identity"],
        )

        assert risk.sensitivity_level == SensitivityLevel.HIGH
        assert "Defamation risk" in risk.potential_issues
        assert len(risk.mitigation_suggestions) == 2

    def test_risk_assessment_to_dict(self):
        """to_dict should serialize sensitivity_level as string."""
        risk = RiskAssessment(
            sensitivity_level=SensitivityLevel.MEDIUM,
            potential_issues=["Issue 1"],
        )
        result = risk.to_dict()

        assert result["sensitivity_level"] == "medium"


# =============================================================================
# TestInterviewCandidate
# =============================================================================


class TestInterviewCandidate:
    """Tests for InterviewCandidate dataclass."""

    def test_interview_candidate_creation(self):
        """InterviewCandidate should create correctly."""
        candidate = InterviewCandidate(
            name="John Smith",
            role="Former CFO",
            why_relevant="Was present during key events",
            potential_questions=[
                "When did you first notice irregularities?",
                "Who was involved in the cover-up?",
            ],
        )

        assert candidate.name == "John Smith"
        assert candidate.role == "Former CFO"
        assert len(candidate.potential_questions) == 2

    def test_interview_candidate_to_dict(self):
        """to_dict should return all fields."""
        candidate = InterviewCandidate(
            name="Jane Doe",
            role="Expert",
            why_relevant="Expertise",
        )
        result = candidate.to_dict()

        assert result["name"] == "Jane Doe"
        assert result["role"] == "Expert"


# =============================================================================
# TestInterviewSuggestions
# =============================================================================


class TestInterviewSuggestions:
    """Tests for InterviewSuggestions dataclass."""

    def test_interview_suggestions_creation(self):
        """InterviewSuggestions should create correctly."""
        suggestions = InterviewSuggestions(
            people_to_contact=[
                InterviewCandidate("Person 1", "Role 1", "Relevant"),
                InterviewCandidate("Person 2", "Role 2", "Also relevant"),
            ],
            expert_perspectives_needed=[
                "Financial fraud expert",
                "Corporate governance specialist",
            ],
        )

        assert len(suggestions.people_to_contact) == 2
        assert len(suggestions.expert_perspectives_needed) == 2

    def test_interview_suggestions_to_dict(self):
        """to_dict should serialize nested candidates."""
        suggestions = InterviewSuggestions(
            people_to_contact=[
                InterviewCandidate("Person", "Role", "Why"),
            ],
        )
        result = suggestions.to_dict()

        assert len(result["people_to_contact"]) == 1
        assert result["people_to_contact"][0]["name"] == "Person"


# =============================================================================
# TestBRollSuggestion
# =============================================================================


class TestBRollSuggestion:
    """Tests for BRollSuggestion dataclass."""

    def test_b_roll_suggestion_creation(self):
        """BRollSuggestion should create correctly."""
        b_roll = BRollSuggestion(
            description="Empty corporate lobby",
            purpose="Establish sense of abandonment",
            source_options=["Stock footage", "Original shoot"],
        )

        assert b_roll.description == "Empty corporate lobby"
        assert b_roll.purpose == "Establish sense of abandonment"
        assert len(b_roll.source_options) == 2

    def test_b_roll_suggestion_to_dict(self):
        """to_dict should return all fields."""
        b_roll = BRollSuggestion(
            description="Test",
            purpose="Test purpose",
        )
        result = b_roll.to_dict()

        assert result["description"] == "Test"
        assert result["purpose"] == "Test purpose"


# =============================================================================
# TestProducerPacket
# =============================================================================


class TestProducerPacket:
    """Tests for ProducerPacket dataclass."""

    def create_minimal_story_core(self) -> StoryCore:
        """Create a minimal StoryCore for testing."""
        return StoryCore(
            central_question="Question?",
            one_sentence_pitch="Pitch",
            why_this_matters="Importance",
            target_audience="Audience",
            emotional_arc="Arc",
        )

    def test_producer_packet_creation_minimal(self):
        """ProducerPacket should create with minimal fields."""
        packet = ProducerPacket(
            job_id="job_123",
            generated_at="2024-01-15T10:00:00Z",
            story_core=self.create_minimal_story_core(),
        )

        assert packet.job_id == "job_123"
        assert packet.narrative_angles == []
        assert packet.risk_assessment is None

    def test_producer_packet_creation_full(self):
        """ProducerPacket should create with all fields."""
        packet = ProducerPacket(
            job_id="job_123",
            generated_at="2024-01-15T10:00:00Z",
            story_core=self.create_minimal_story_core(),
            narrative_angles=[
                NarrativeAngle("ANGLE_1", "Title", "Description"),
            ],
            opening_hooks=[
                OpeningHook(HookType.COLD_OPEN, "Content", "Tone"),
            ],
            structure_options=[
                StructureOption(StructureType.CHRONOLOGICAL, "Description"),
            ],
            key_moments=[
                KeyMoment("Moment", "SRC_1"),
            ],
            title_options=[
                TitleOption("Title"),
            ],
            thumbnail_concepts=[
                ThumbnailConcept("Concept"),
            ],
            risk_assessment=RiskAssessment(SensitivityLevel.MEDIUM),
            interview_suggestions=InterviewSuggestions(),
            b_roll_suggestions=[
                BRollSuggestion("Description", "Purpose"),
            ],
        )

        assert len(packet.narrative_angles) == 1
        assert len(packet.opening_hooks) == 1
        assert packet.risk_assessment is not None

    def test_producer_packet_to_dict(self):
        """to_dict should return all fields with document metadata."""
        packet = ProducerPacket(
            job_id="job_123",
            generated_at="2024-01-15T10:00:00Z",
            story_core=self.create_minimal_story_core(),
            narrative_angles=[
                NarrativeAngle("ANGLE_1", "Title", "Description"),
            ],
        )
        result = packet.to_dict()

        assert result["document_type"] == "producer_packet"
        assert result["document_version"] == "2.0"
        assert result["job_id"] == "job_123"
        assert "creative_interpretation_notice" in result
        assert len(result["narrative_angles"]) == 1

    def test_producer_packet_to_dict_json_serializable(self):
        """to_dict output should be JSON-serializable."""
        packet = ProducerPacket(
            job_id="job_123",
            generated_at="2024-01-15T10:00:00Z",
            story_core=self.create_minimal_story_core(),
            opening_hooks=[
                OpeningHook(HookType.COLD_OPEN, "Content", "Tone"),
            ],
            risk_assessment=RiskAssessment(SensitivityLevel.HIGH),
        )
        result = packet.to_dict()

        # Should not raise
        json.dumps(result)

    def test_producer_packet_to_markdown(self):
        """to_markdown should produce readable output."""
        packet = ProducerPacket(
            job_id="job_123",
            generated_at="2024-01-15T10:00:00Z",
            story_core=StoryCore(
                central_question="Why did it happen?",
                one_sentence_pitch="A story about...",
                why_this_matters="It matters because...",
                target_audience="Viewers",
                emotional_arc="Beginning → End",
            ),
            title_options=[
                TitleOption("The Truth", subtitle="Revealed", tone=TitleTone.SERIOUS),
            ],
        )
        markdown = packet.to_markdown()

        assert "Producer Packet" in markdown  # Header may have emoji prefix
        assert "job_123" in markdown
        assert "Creative Interpretation" in markdown  # Notice text updated in R1-R17
        assert "Why did it happen?" in markdown
        assert "The Truth" in markdown

    def test_producer_packet_markdown_all_sections(self):
        """to_markdown should include all populated sections."""
        packet = ProducerPacket(
            job_id="job_123",
            generated_at="2024-01-15T10:00:00Z",
            story_core=self.create_minimal_story_core(),
            narrative_angles=[
                NarrativeAngle("ANGLE_1", "Angle Title", "Description", strengths=["Strong"]),
            ],
            opening_hooks=[
                OpeningHook(HookType.COLD_OPEN, "Hook content", "suspense"),
            ],
            structure_options=[
                StructureOption(StructureType.THEMATIC, "Theme-based"),
            ],
            key_moments=[
                KeyMoment("Big moment", "SRC_1", timestamp="5:00"),
            ],
            risk_assessment=RiskAssessment(SensitivityLevel.HIGH, potential_issues=["Issue"]),
            interview_suggestions=InterviewSuggestions(
                people_to_contact=[InterviewCandidate("Name", "Role", "Why")],
            ),
            b_roll_suggestions=[
                BRollSuggestion("B-roll desc", "Purpose"),
            ],
        )
        markdown = packet.to_markdown()

        assert "Narrative Angles" in markdown  # Section headers may have emoji prefixes
        assert "Opening Hooks" in markdown or "Hooks" in markdown
        assert "Structure Options" in markdown
        assert "Key Moments" in markdown or "Moments" in markdown
        assert "Risk Assessment" in markdown
        assert "Interview Suggestions" in markdown
        assert "B-Roll Suggestions" in markdown


# =============================================================================
# TestCreativeInterpretationNotice
# =============================================================================


class TestCreativeInterpretationNotice:
    """Tests for the creative interpretation notice."""

    def test_notice_exists(self):
        """CREATIVE_INTERPRETATION_NOTICE should exist."""
        assert CREATIVE_INTERPRETATION_NOTICE is not None
        assert len(CREATIVE_INTERPRETATION_NOTICE) > 0

    def test_notice_mentions_creative(self):
        """Notice should mention creative interpretation."""
        assert "creative interpretation" in CREATIVE_INTERPRETATION_NOTICE.lower()

    def test_notice_mentions_verification(self):
        """Notice should mention need for verification."""
        assert "verify" in CREATIVE_INTERPRETATION_NOTICE.lower() or "verified" in CREATIVE_INTERPRETATION_NOTICE.lower()

    def test_notice_included_in_packet_dict(self):
        """Notice should be included in packet to_dict output."""
        packet = ProducerPacket(
            job_id="test",
            generated_at="2024-01-15T10:00:00Z",
            story_core=StoryCore(
                central_question="Q",
                one_sentence_pitch="P",
                why_this_matters="W",
                target_audience="A",
                emotional_arc="E",
            ),
        )
        result = packet.to_dict()

        assert result["creative_interpretation_notice"] == CREATIVE_INTERPRETATION_NOTICE

    def test_notice_included_in_packet_markdown(self):
        """Notice should be included in packet to_markdown output."""
        packet = ProducerPacket(
            job_id="test",
            generated_at="2024-01-15T10:00:00Z",
            story_core=StoryCore(
                central_question="Q",
                one_sentence_pitch="P",
                why_this_matters="W",
                target_audience="A",
                emotional_arc="E",
            ),
        )
        markdown = packet.to_markdown()

        # R1-R17 updated the notice format — check for key phrase instead of exact match
        assert "creative interpretation" in markdown.lower()
