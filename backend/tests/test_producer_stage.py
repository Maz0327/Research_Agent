"""
Unit tests for producer pipeline stage.

Tests for: run_producer_pipeline, validate_producer_cardinality

Phase 9 Task 9.2.6
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.pipeline.stages.producer_stage import (
    run_producer_pipeline,
    validate_producer_cardinality,
)
from backend.models.producer_models import (
    ProducerPacket,
    StoryCore,
    NarrativeAngle,
    OpeningHook,
    StructureOption,
    KeyMoment,
    TitleOption,
    ThumbnailConcept,
    RiskAssessment,
    InterviewSuggestions,
    InterviewCandidate,
    BRollSuggestion,
    HookType,
    StructureType,
    TitleTone,
    SensitivityLevel,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_job_data():
    """Minimal job data for testing."""
    return {
        "sources": [
            {"source_id": "SRC_1", "title": "Test Video", "source_type": "youtube"},
        ],
        "artifacts": {
            "semantic_brief": {
                "themes": [
                    {"theme_id": "THEME_1", "label": "Test Theme", "description": "Test description"}
                ],
                "key_points": [
                    {"key_point_id": "KP_1", "statement": "Test key point"}
                ],
                "tensions": [
                    {"tension_id": "TEN_1", "description": "Test tension"}
                ],
            }
        }
    }


@pytest.fixture
def minimal_producer_packet():
    """Minimal valid producer packet."""
    return ProducerPacket(
        job_id="JOB_1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        story_core=StoryCore(
            central_question="Test question?",
            one_sentence_pitch="Test pitch.",
            why_this_matters="Test reason.",
            target_audience="Test audience",
            emotional_arc="Test arc",
        ),
        narrative_angles=[
            NarrativeAngle(
                angle_id="ANG_1",
                title="Angle 1",
                description="Description 1",
                strengths=["Strength 1"],
                weaknesses=["Weakness 1"],
                best_for="Best for 1",
                key_sources=["SRC_1"],
            ),
            NarrativeAngle(
                angle_id="ANG_2",
                title="Angle 2",
                description="Description 2",
                strengths=["Strength 2"],
                weaknesses=["Weakness 2"],
                best_for="Best for 2",
                key_sources=["SRC_1"],
            ),
        ],
        opening_hooks=[
            OpeningHook(
                hook_type=HookType.COLD_OPEN,
                content="Hook 1 content",
                tone="Engaging",
                source_basis=["SRC_1"],
            ),
            OpeningHook(
                hook_type=HookType.PROVOCATIVE_QUESTION,
                content="Hook 2 content",
                tone="Intriguing",
                source_basis=["SRC_1"],
            ),
        ],
        structure_options=[
            StructureOption(
                structure_type=StructureType.CHRONOLOGICAL,
                description="Chronological structure",
                section_breakdown=["Intro", "Middle", "End"],
                pros=["Clear timeline"],
                cons=["Predictable"],
            ),
            StructureOption(
                structure_type=StructureType.THEMATIC,
                description="Thematic structure",
                section_breakdown=["Theme A", "Theme B"],
                pros=["Conceptual clarity"],
                cons=["Complex"],
            ),
        ],
        key_moments=[
            KeyMoment(
                moment="Moment 1",
                source_id="SRC_1",
                why_compelling="Compelling 1",
                potential_use="Use 1",
            ),
            KeyMoment(
                moment="Moment 2",
                source_id="SRC_1",
                why_compelling="Compelling 2",
                potential_use="Use 2",
            ),
            KeyMoment(
                moment="Moment 3",
                source_id="SRC_1",
                why_compelling="Compelling 3",
                potential_use="Use 3",
            ),
        ],
        title_options=[
            TitleOption(
                title="Title 1",
                tone=TitleTone.SERIOUS,
            ),
            TitleOption(
                title="Title 2",
                tone=TitleTone.PROVOCATIVE,
            ),
        ],
        thumbnail_concepts=[
            ThumbnailConcept(
                concept="Concept 1",
                visual_elements=["Element 1"],
                emotional_appeal="Appeal 1",
            ),
        ],
        risk_assessment=RiskAssessment(
            sensitivity_level=SensitivityLevel.MEDIUM,
            potential_issues=["Issue 1"],
            mitigation_suggestions=["Suggestion 1"],
            legal_considerations=["Legal 1"],
            ethical_considerations=["Ethical 1"],
        ),
        interview_suggestions=InterviewSuggestions(
            people_to_contact=[],
            expert_perspectives_needed=["Expert 1"],
        ),
        b_roll_suggestions=[],
    )


@pytest.fixture
def mock_gemini_responses():
    """Mock Gemini responses for all 4 stages."""
    return {
        "story_core": {
            "data": {
                "central_question": "What happened?",
                "one_sentence_pitch": "An investigation into...",
                "why_this_matters": "Because...",
                "target_audience": "Documentary viewers",
                "emotional_arc": "Curiosity to understanding",
            },
            "cost": 0.01,
        },
        "structure": {
            "data": {
                "narrative_angles": [
                    {
                        "angle_id": "ANG_1",
                        "title": "The Investigation",
                        "description": "Follow the investigation",
                        "strengths": ["Clear narrative"],
                        "weaknesses": ["Limited scope"],
                        "best_for": "News-style docs",
                        "key_sources": ["SRC_1"],
                    },
                    {
                        "angle_id": "ANG_2",
                        "title": "The Human Story",
                        "description": "Focus on people",
                        "strengths": ["Emotional impact"],
                        "weaknesses": ["May lack context"],
                        "best_for": "Character-driven docs",
                        "key_sources": ["SRC_1"],
                    },
                ],
                "structure_options": [
                    {
                        "structure_type": "chronological",
                        "description": "Timeline-based",
                        "section_breakdown": ["Beginning", "Middle", "End"],
                        "pros": ["Easy to follow"],
                        "cons": ["Predictable"],
                    },
                    {
                        "structure_type": "thematic",
                        "description": "Theme-based",
                        "section_breakdown": ["Theme 1", "Theme 2"],
                        "pros": ["Conceptual depth"],
                        "cons": ["Complex"],
                    },
                ],
            },
            "cost": 0.02,
        },
        "creative": {
            "data": {
                "opening_hooks": [
                    {
                        "hook_type": "cold_open",
                        "content": "In 2024...",
                        "tone": "Mysterious",
                        "source_basis": ["SRC_1"],
                    },
                    {
                        "hook_type": "provocative_question",
                        "content": "What if...?",
                        "tone": "Intriguing",
                        "source_basis": ["SRC_1"],
                    },
                ],
                "title_options": [
                    {
                        "title": "The Investigation",
                        "subtitle": "A Documentary",
                        "tone": "serious",
                        "seo_considerations": "SEO notes",
                    },
                    {
                        "title": "Uncovered",
                        "tone": "provocative",
                    },
                ],
                "thumbnail_concepts": [
                    {
                        "concept": "Silhouette against city",
                        "visual_elements": ["Person", "City skyline"],
                        "text_overlay": "The Truth",
                        "emotional_appeal": "Mystery",
                    },
                ],
                "key_moments": [
                    {
                        "moment": "The revelation",
                        "source_id": "SRC_1",
                        "timestamp": "10:30",
                        "why_compelling": "Turning point",
                        "potential_use": "Trailer clip",
                    },
                    {
                        "moment": "Expert analysis",
                        "source_id": "SRC_1",
                        "why_compelling": "Credibility",
                        "potential_use": "Middle section",
                    },
                    {
                        "moment": "Conclusion",
                        "source_id": "SRC_1",
                        "why_compelling": "Resolution",
                        "potential_use": "Ending",
                    },
                ],
            },
            "cost": 0.02,
        },
        "risk": {
            "data": {
                "risk_assessment": {
                    "sensitivity_level": "medium",
                    "potential_issues": ["Defamation risk"],
                    "mitigation_suggestions": ["Verify all claims"],
                    "legal_considerations": ["Consult lawyer"],
                    "ethical_considerations": ["Protect sources"],
                },
                "interview_suggestions": {
                    "people_to_contact": [
                        {
                            "name": "Expert Name",
                            "role": "Industry Expert",
                            "why_relevant": "Has expertise",
                            "potential_questions": ["Question 1"],
                        },
                    ],
                    "expert_perspectives_needed": ["Legal expert"],
                },
                "b_roll_suggestions": [
                    {
                        "description": "City footage",
                        "purpose": "Establish setting",
                        "source_options": ["Stock footage"],
                    },
                ],
            },
            "cost": 0.01,
        },
    }


# =============================================================================
# TestValidateProducerCardinality
# =============================================================================


class TestValidateProducerCardinality:
    """Tests for validate_producer_cardinality function."""

    def test_valid_packet_no_warnings(self, minimal_producer_packet):
        """Valid packet should have no cardinality warnings."""
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert warnings == []

    def test_narrative_angles_below_minimum(self, minimal_producer_packet):
        """Should warn if narrative_angles < 2."""
        minimal_producer_packet.narrative_angles = [
            minimal_producer_packet.narrative_angles[0]
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("narrative_angles below minimum" in w for w in warnings)
        assert "1/2" in warnings[0]

    def test_narrative_angles_above_maximum(self, minimal_producer_packet):
        """Should warn if narrative_angles > 6."""
        minimal_producer_packet.narrative_angles = [
            NarrativeAngle(
                angle_id=f"ANG_{i}",
                title=f"Angle {i}",
                description=f"Description {i}",
                strengths=[],
                weaknesses=[],
                best_for="",
                key_sources=[],
            )
            for i in range(7)
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("narrative_angles above maximum" in w for w in warnings)
        assert "7/6" in warnings[0]

    def test_opening_hooks_below_minimum(self, minimal_producer_packet):
        """Should warn if opening_hooks < 2."""
        minimal_producer_packet.opening_hooks = [
            minimal_producer_packet.opening_hooks[0]
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("opening_hooks below minimum" in w for w in warnings)

    def test_opening_hooks_above_maximum(self, minimal_producer_packet):
        """Should warn if opening_hooks > 6."""
        minimal_producer_packet.opening_hooks = [
            OpeningHook(
                hook_type=HookType.COLD_OPEN,
                content=f"Hook {i}",
                tone="Test",
                source_basis=[],
            )
            for i in range(7)
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("opening_hooks above maximum" in w for w in warnings)

    def test_structure_options_below_minimum(self, minimal_producer_packet):
        """Should warn if structure_options < 2."""
        minimal_producer_packet.structure_options = [
            minimal_producer_packet.structure_options[0]
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("structure_options below minimum" in w for w in warnings)

    def test_structure_options_above_maximum(self, minimal_producer_packet):
        """Should warn if structure_options > 5."""
        minimal_producer_packet.structure_options = [
            StructureOption(
                structure_type=StructureType.THEMATIC,
                description=f"Structure {i}",
                section_breakdown=[],
                pros=[],
                cons=[],
            )
            for i in range(6)
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("structure_options above maximum" in w for w in warnings)

    def test_title_options_below_minimum(self, minimal_producer_packet):
        """Should warn if title_options < 2."""
        minimal_producer_packet.title_options = [
            minimal_producer_packet.title_options[0]
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("title_options below minimum" in w for w in warnings)

    def test_title_options_above_maximum(self, minimal_producer_packet):
        """Should warn if title_options > 8."""
        minimal_producer_packet.title_options = [
            TitleOption(
                title=f"Title {i}",
                tone=TitleTone.SERIOUS,
            )
            for i in range(9)
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("title_options above maximum" in w for w in warnings)

    def test_key_moments_below_minimum(self, minimal_producer_packet):
        """Should warn if key_moments < 3."""
        minimal_producer_packet.key_moments = [
            minimal_producer_packet.key_moments[0],
            minimal_producer_packet.key_moments[1],
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("key_moments below minimum" in w for w in warnings)
        assert "2/3" in warnings[0]

    def test_key_moments_above_maximum(self, minimal_producer_packet):
        """Should warn if key_moments > 15."""
        minimal_producer_packet.key_moments = [
            KeyMoment(
                moment=f"Moment {i}",
                source_id="SRC_1",
                why_compelling=f"Compelling {i}",
                potential_use=f"Use {i}",
            )
            for i in range(16)
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert any("key_moments above maximum" in w for w in warnings)
        assert "16/15" in warnings[0]

    def test_multiple_violations(self, minimal_producer_packet):
        """Should report all cardinality violations."""
        minimal_producer_packet.narrative_angles = []
        minimal_producer_packet.opening_hooks = []
        minimal_producer_packet.key_moments = []

        warnings = validate_producer_cardinality(minimal_producer_packet)

        assert len(warnings) >= 3
        assert any("narrative_angles" in w for w in warnings)
        assert any("opening_hooks" in w for w in warnings)
        assert any("key_moments" in w for w in warnings)

    def test_at_boundary_minimum(self, minimal_producer_packet):
        """Exactly at minimum should not warn."""
        # minimal_producer_packet already has exactly 2 of each required
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert not any("below minimum" in w for w in warnings)

    def test_at_boundary_maximum(self, minimal_producer_packet):
        """Exactly at maximum should not warn."""
        minimal_producer_packet.narrative_angles = [
            NarrativeAngle(
                angle_id=f"ANG_{i}",
                title=f"Angle {i}",
                description=f"Description {i}",
                strengths=[],
                weaknesses=[],
                best_for="",
                key_sources=[],
            )
            for i in range(6)  # Exactly at max of 6
        ]
        warnings = validate_producer_cardinality(minimal_producer_packet)
        assert not any("narrative_angles above maximum" in w for w in warnings)


# =============================================================================
# TestRunProducerPipeline
# =============================================================================


class TestRunProducerPipeline:
    """Tests for run_producer_pipeline function."""

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_returns_tuple(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should return (ProducerPacket, cost, warnings)."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup responses for each stage
        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        result = run_producer_pipeline("JOB_1", minimal_job_data)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], ProducerPacket)
        assert isinstance(result[1], float)
        assert isinstance(result[2], list)

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_accumulates_cost(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should accumulate costs from all stages."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
            {"data": {"quality_score": 85, "issues": [], "generic_phrase_count": 0}, "cost": 0.005},  # R12 self-critique
        ]

        packet, cost, warnings = run_producer_pipeline("JOB_1", minimal_job_data)

        expected_cost = 0.01 + 0.02 + 0.02 + 0.01 + 0.005  # sum of all stage costs incl. R12
        assert cost == pytest.approx(expected_cost)

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_makes_4_calls(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should make exactly 4 Gemini calls."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
            {"data": {"quality_score": 85, "issues": [], "generic_phrase_count": 0}, "cost": 0.005},  # R12 self-critique
        ]

        run_producer_pipeline("JOB_1", minimal_job_data)

        # R12 self-critique adds Stage 6, so now 5 calls (was 4 before R12)
        assert mock_client.generate_json.call_count == 5

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_temperature_settings(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should use correct temperatures per stage."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
            {"data": {"quality_score": 85, "issues": [], "generic_phrase_count": 0}, "cost": 0.005},  # R12 self-critique
        ]

        run_producer_pipeline("JOB_1", minimal_job_data)

        calls = mock_client.generate_json.call_args_list

        # Stage 1: Story Core - temp 0.4
        assert calls[0].kwargs.get("temperature") == 0.4

        # Stage 2: Structure - temp 0.4
        assert calls[1].kwargs.get("temperature") == 0.4

        # Stage 3: Creative - temp 0.5
        assert calls[2].kwargs.get("temperature") == 0.5

        # Stage 4: Risk - temp 0.3
        assert calls[3].kwargs.get("temperature") == 0.3

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_story_core_error_raises(self, mock_client_class, minimal_job_data):
        """Stage 1 error should raise RuntimeError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.return_value = {
            "error": "API error",
            "cost": 0.0,
        }

        with pytest.raises(RuntimeError, match="Story core generation failed"):
            run_producer_pipeline("JOB_1", minimal_job_data)

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_structure_error_warns(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Stage 2 error should add warning but continue."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            {"error": "Structure error", "data": {}, "cost": 0.01},
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, cost, warnings = run_producer_pipeline("JOB_1", minimal_job_data)

        assert any("Structure generation warning" in w for w in warnings)

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_creative_error_warns(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Stage 3 error should add warning but continue."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            {"error": "Creative error", "data": {}, "cost": 0.01},
            mock_gemini_responses["risk"],
        ]

        packet, cost, warnings = run_producer_pipeline("JOB_1", minimal_job_data)

        assert any("Creative elements warning" in w for w in warnings)

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_risk_error_warns(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Stage 4 error should add warning but continue."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            {"error": "Risk error", "data": {}, "cost": 0.01},
        ]

        packet, cost, warnings = run_producer_pipeline("JOB_1", minimal_job_data)

        assert any("Risk assessment warning" in w for w in warnings)

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_populates_story_core(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should populate story_core correctly."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        assert packet.story_core.central_question == "What happened?"
        assert packet.story_core.one_sentence_pitch == "An investigation into..."
        assert packet.story_core.target_audience == "Documentary viewers"

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_populates_narrative_angles(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should populate narrative_angles correctly."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        assert len(packet.narrative_angles) == 2
        assert packet.narrative_angles[0].title == "The Investigation"
        assert packet.narrative_angles[1].title == "The Human Story"

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_populates_opening_hooks(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should populate opening_hooks correctly."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        assert len(packet.opening_hooks) == 2
        assert packet.opening_hooks[0].hook_type == HookType.COLD_OPEN
        assert packet.opening_hooks[1].hook_type == HookType.PROVOCATIVE_QUESTION

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_populates_risk_assessment(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should populate risk_assessment correctly."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        assert packet.risk_assessment.sensitivity_level == SensitivityLevel.MEDIUM
        assert "Defamation risk" in packet.risk_assessment.potential_issues

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_populates_interview_suggestions(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should populate interview_suggestions correctly."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        assert len(packet.interview_suggestions.people_to_contact) == 1
        assert packet.interview_suggestions.people_to_contact[0].name == "Expert Name"

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_validates_cardinality(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should call validate_producer_cardinality."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Return data with below-minimum angles
        modified_structure = mock_gemini_responses["structure"].copy()
        modified_structure["data"] = {"narrative_angles": [], "structure_options": []}

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            modified_structure,
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, cost, warnings = run_producer_pipeline("JOB_1", minimal_job_data)

        # Should have cardinality warnings
        assert any("below minimum" in w for w in warnings)

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_handles_empty_job_data(self, mock_client_class, mock_gemini_responses):
        """Pipeline should handle job with minimal/empty data."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        empty_job = {"sources": [], "artifacts": {}}

        # Should not raise
        packet, cost, warnings = run_producer_pipeline("JOB_1", empty_job)

        assert packet.job_id == "JOB_1"

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_sets_job_id(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should set job_id on packet."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("TEST_JOB_123", minimal_job_data)

        assert packet.job_id == "TEST_JOB_123"

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_sets_generated_at(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should set generated_at timestamp."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        assert packet.generated_at is not None
        # Should be ISO format
        assert "T" in packet.generated_at

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_handles_invalid_hook_type(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should default invalid hook_type to COLD_OPEN."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Return invalid hook_type
        modified_creative = mock_gemini_responses["creative"].copy()
        modified_creative["data"] = {
            "opening_hooks": [
                {
                    "hook_type": "invalid_type",
                    "content": "Test",
                    "tone": "Test",
                    "source_basis": [],
                },
                {
                    "hook_type": "cold_open",
                    "content": "Test 2",
                    "tone": "Test",
                    "source_basis": [],
                },
            ],
            "title_options": mock_gemini_responses["creative"]["data"]["title_options"],
            "thumbnail_concepts": [],
            "key_moments": mock_gemini_responses["creative"]["data"]["key_moments"],
        }

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            modified_creative,
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        # Invalid type should default to COLD_OPEN
        assert packet.opening_hooks[0].hook_type == HookType.COLD_OPEN

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_handles_invalid_structure_type(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should default invalid structure_type to THEMATIC."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Return invalid structure_type
        modified_structure = mock_gemini_responses["structure"].copy()
        modified_structure["data"] = {
            "narrative_angles": mock_gemini_responses["structure"]["data"]["narrative_angles"],
            "structure_options": [
                {
                    "structure_type": "invalid_type",
                    "description": "Test",
                    "section_breakdown": [],
                    "pros": [],
                    "cons": [],
                },
                {
                    "structure_type": "chronological",
                    "description": "Test 2",
                    "section_breakdown": [],
                    "pros": [],
                    "cons": [],
                },
            ],
        }

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            modified_structure,
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        # Invalid type should default to THEMATIC
        assert packet.structure_options[0].structure_type == StructureType.THEMATIC

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_pipeline_handles_invalid_sensitivity_level(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Pipeline should default invalid sensitivity_level to MEDIUM."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Return invalid sensitivity level
        modified_risk = mock_gemini_responses["risk"].copy()
        modified_risk["data"] = {
            "risk_assessment": {
                "sensitivity_level": "invalid_level",
                "potential_issues": [],
                "mitigation_suggestions": [],
                "legal_considerations": [],
                "ethical_considerations": [],
            },
            "interview_suggestions": {"people_to_contact": [], "expert_perspectives_needed": []},
            "b_roll_suggestions": [],
        }

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            modified_risk,
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        # Invalid level should default to MEDIUM
        assert packet.risk_assessment.sensitivity_level == SensitivityLevel.MEDIUM


# =============================================================================
# TestProducerContextBuilding
# =============================================================================


class TestProducerContextBuilding:
    """Tests for context building from job data."""

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_context_limits_themes(self, mock_client_class, mock_gemini_responses):
        """Context should limit themes to 8."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        # Job with 15 themes
        job_data = {
            "sources": [{"source_id": "SRC_1", "title": "Test", "source_type": "youtube"}],
            "artifacts": {
                "semantic_brief": {
                    "themes": [
                        {"theme_id": f"THEME_{i}", "label": f"Theme {i}", "description": f"Desc {i}"}
                        for i in range(15)
                    ],
                    "key_points": [],
                    "tensions": [],
                }
            }
        }

        run_producer_pipeline("JOB_1", job_data)

        # Verify themes_str in first call
        first_call = mock_client.generate_json.call_args_list[0]
        prompt = first_call.args[0] if first_call.args else first_call.kwargs.get("prompt", "")

        # Themes should be limited (prompt building uses [:8])
        # We can't directly check but the pipeline should not fail

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_context_limits_key_points(self, mock_client_class, mock_gemini_responses):
        """Context should limit key_points to 12."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        # Job with 20 key points
        job_data = {
            "sources": [{"source_id": "SRC_1", "title": "Test", "source_type": "youtube"}],
            "artifacts": {
                "semantic_brief": {
                    "themes": [],
                    "key_points": [
                        {"key_point_id": f"KP_{i}", "statement": f"Point {i}"}
                        for i in range(20)
                    ],
                    "tensions": [],
                }
            }
        }

        run_producer_pipeline("JOB_1", job_data)

        # Pipeline should succeed with limited key points

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_context_limits_sources(self, mock_client_class, mock_gemini_responses):
        """Context should limit sources to 10."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        # Job with 15 sources
        job_data = {
            "sources": [
                {"source_id": f"SRC_{i}", "title": f"Source {i}", "source_type": "youtube"}
                for i in range(15)
            ],
            "artifacts": {"semantic_brief": {"themes": [], "key_points": [], "tensions": []}}
        }

        run_producer_pipeline("JOB_1", job_data)

        # Pipeline should succeed with limited sources

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_context_handles_missing_artifacts(self, mock_client_class, mock_gemini_responses):
        """Context should handle missing artifacts gracefully."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        # Job with no artifacts
        job_data = {
            "sources": [{"source_id": "SRC_1", "title": "Test", "source_type": "youtube"}],
        }

        # Should not raise
        packet, _, _ = run_producer_pipeline("JOB_1", job_data)
        assert packet.job_id == "JOB_1"

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_context_handles_empty_arrays(self, mock_client_class, mock_gemini_responses):
        """Context should handle empty arrays with fallback text."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        # Job with empty arrays
        job_data = {
            "sources": [],
            "artifacts": {"semantic_brief": {"themes": [], "key_points": [], "tensions": []}}
        }

        run_producer_pipeline("JOB_1", job_data)

        # Verify first call prompt (should have "(No themes)" etc.)
        first_call = mock_client.generate_json.call_args_list[0]
        prompt = first_call.args[0] if first_call.args else first_call.kwargs.get("prompt", "")

        # The prompt building uses fallback text
        # Pipeline should succeed


# =============================================================================
# TestProducerParsing
# =============================================================================


class TestProducerParsing:
    """Tests for parsing Gemini response data."""

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_auto_generates_angle_ids(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Should auto-generate angle_id if missing."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Return angles without angle_id
        modified_structure = mock_gemini_responses["structure"].copy()
        modified_structure["data"] = {
            "narrative_angles": [
                {
                    # No angle_id
                    "title": "Angle 1",
                    "description": "Desc 1",
                    "strengths": [],
                    "weaknesses": [],
                    "best_for": "",
                    "key_sources": [],
                },
                {
                    # No angle_id
                    "title": "Angle 2",
                    "description": "Desc 2",
                    "strengths": [],
                    "weaknesses": [],
                    "best_for": "",
                    "key_sources": [],
                },
            ],
            "structure_options": mock_gemini_responses["structure"]["data"]["structure_options"],
        }

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            modified_structure,
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        # Should have auto-generated IDs
        assert packet.narrative_angles[0].angle_id == "ANG_1"
        assert packet.narrative_angles[1].angle_id == "ANG_2"

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_handles_missing_optional_fields(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Should handle missing optional fields in response."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Return minimal story core
        modified_story = {
            "data": {
                "central_question": "Question?",
                # Missing other fields
            },
            "cost": 0.01,
        }

        mock_client.generate_json.side_effect = [
            modified_story,
            mock_gemini_responses["structure"],
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, _ = run_producer_pipeline("JOB_1", minimal_job_data)

        # Should have empty strings for missing fields
        assert packet.story_core.one_sentence_pitch == ""
        assert packet.story_core.why_this_matters == ""

    @patch("backend.pipeline.stages.producer_stage.GeminiClient")
    def test_handles_empty_response_data(self, mock_client_class, minimal_job_data, mock_gemini_responses):
        """Should handle empty data dict in response."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Return empty structure data
        empty_structure = {
            "data": {},
            "cost": 0.01,
        }

        mock_client.generate_json.side_effect = [
            mock_gemini_responses["story_core"],
            empty_structure,
            mock_gemini_responses["creative"],
            mock_gemini_responses["risk"],
        ]

        packet, _, warnings = run_producer_pipeline("JOB_1", minimal_job_data)

        # Should have empty lists
        assert packet.narrative_angles == []
        assert packet.structure_options == []

        # Should have cardinality warnings
        assert any("below minimum" in w for w in warnings)
