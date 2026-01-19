"""
Tests for hallucination prevention features.

Tests cover:
- Chain-of-thought prompting components
- RAG grounding verification
- Confidence penalty weights
- LLM judge parsing
- HallucinationConfig feature flags
- Error-specific retry prompts
"""

import pytest
import json

from backend.models.job_config import HallucinationConfig, JobConfig, ResearchMode
from backend.models.semantic_extraction_schema import (
    SemanticExtractionSchema,
    KeyPointSchema,
    ClaimSchema,
)
from backend.pipeline.prompts.modes.base import (
    CHAIN_OF_THOUGHT_SECTION,
    ANTI_HALLUCINATION_EXAMPLES,
    LAYERED_EXTRACTION_INSTRUCTIONS,
    build_base_prompt,
)
from backend.pipeline.prompts.semantic_extraction_prompt import (
    get_retry_prompt,
    SCHEMA_RETRY_PROMPT,
    HALLUCINATION_RETRY_PROMPT,
    GROUNDING_RETRY_PROMPT,
)
from backend.pipeline.rag_grounding import (
    GroundingStrength,
    GroundingResult,
    verify_claim_grounding,
    verify_claims_grounding,
    apply_grounding_adjustments,
    assess_grounding_strength,
    suggest_confidence_for_grounding,
)
from backend.pipeline.semantic_validation import (
    CONFIDENCE_PENALTY_WEIGHTS,
    calculate_weighted_error_score,
    should_downgrade_source_confidence,
    get_confidence_penalty_summary,
    ValidationResult,
    ValidationLevel,
)
from backend.pipeline.llm_judge import (
    JudgeVerdict,
    OverallQuality,
    ItemReview,
    QuoteReview,
    ConfidenceOverride,
    JudgeResult,
    parse_judge_response,
    apply_judge_verdicts,
)
from backend.models.semantic_units import ConfidenceLevel


# =============================================================================
# Chain-of-Thought Prompting Tests
# =============================================================================

class TestChainOfThought:
    """Tests for chain-of-thought prompting components."""

    def test_cot_section_exists(self):
        """Chain-of-thought section is defined."""
        assert CHAIN_OF_THOUGHT_SECTION is not None
        assert len(CHAIN_OF_THOUGHT_SECTION) > 100

    def test_cot_section_has_steps(self):
        """CoT section contains required reasoning steps."""
        assert "Step 1" in CHAIN_OF_THOUGHT_SECTION
        assert "Step 2" in CHAIN_OF_THOUGHT_SECTION
        assert "Step 3" in CHAIN_OF_THOUGHT_SECTION
        assert "Content Inventory" in CHAIN_OF_THOUGHT_SECTION
        assert "Evidence Assessment" in CHAIN_OF_THOUGHT_SECTION
        assert "Gap" in CHAIN_OF_THOUGHT_SECTION or "Hallucination" in CHAIN_OF_THOUGHT_SECTION

    def test_cot_mentions_reasoning_trace(self):
        """CoT section mentions reasoning_trace field."""
        assert "reasoning_trace" in CHAIN_OF_THOUGHT_SECTION

    def test_anti_hallucination_examples_exist(self):
        """Anti-hallucination examples section is defined."""
        assert ANTI_HALLUCINATION_EXAMPLES is not None
        assert len(ANTI_HALLUCINATION_EXAMPLES) > 100

    def test_anti_hallucination_has_bad_examples(self):
        """Section contains BAD examples."""
        assert "BAD" in ANTI_HALLUCINATION_EXAMPLES
        assert "DO NOT" in ANTI_HALLUCINATION_EXAMPLES

    def test_anti_hallucination_has_good_examples(self):
        """Section contains GOOD examples."""
        assert "GOOD" in ANTI_HALLUCINATION_EXAMPLES

    def test_layer_checkpoints_exist(self):
        """Layer checkpoints are present in extraction instructions."""
        assert "CHECKPOINT 1" in LAYERED_EXTRACTION_INSTRUCTIONS
        assert "CHECKPOINT 2" in LAYERED_EXTRACTION_INSTRUCTIONS
        assert "CHECKPOINT 3" in LAYERED_EXTRACTION_INSTRUCTIONS

    def test_build_base_prompt_includes_cot(self):
        """build_base_prompt includes CoT by default."""
        prompt = build_base_prompt(
            source_id="SRC_1",
            source_content="Test content",
            title="Test",
            analysis_mode="transcript_grounded",
            confidence_ceiling="HIGH",
            mode_specific_instructions="",
        )
        assert "REASONING PROCESS" in prompt or "reasoning_trace" in prompt

    def test_build_base_prompt_can_exclude_cot(self):
        """build_base_prompt can exclude CoT."""
        prompt = build_base_prompt(
            source_id="SRC_1",
            source_content="Test content",
            title="Test",
            analysis_mode="transcript_grounded",
            confidence_ceiling="HIGH",
            mode_specific_instructions="",
            include_chain_of_thought=False,
        )
        # Should not contain the full CoT section when disabled
        assert "Content Inventory" not in prompt


# =============================================================================
# RAG Grounding Tests
# =============================================================================

class TestRagGrounding:
    """Tests for RAG grounding verification."""

    def test_grounding_strength_enum(self):
        """GroundingStrength enum has expected values."""
        assert GroundingStrength.STRONG.value == "strong"
        assert GroundingStrength.PARTIAL.value == "partial"
        assert GroundingStrength.WEAK.value == "weak"
        assert GroundingStrength.NONE.value == "none"

    def test_assess_grounding_strong(self):
        """High match scores return STRONG grounding."""
        assert assess_grounding_strength(0.95) == GroundingStrength.STRONG
        assert assess_grounding_strength(0.90) == GroundingStrength.STRONG
        assert assess_grounding_strength(1.0) == GroundingStrength.STRONG

    def test_assess_grounding_partial(self):
        """Medium match scores return PARTIAL grounding."""
        assert assess_grounding_strength(0.85) == GroundingStrength.PARTIAL
        assert assess_grounding_strength(0.70) == GroundingStrength.PARTIAL

    def test_assess_grounding_weak(self):
        """Low match scores return WEAK grounding."""
        assert assess_grounding_strength(0.60) == GroundingStrength.WEAK
        assert assess_grounding_strength(0.50) == GroundingStrength.WEAK

    def test_assess_grounding_none(self):
        """Very low match scores return NONE grounding."""
        assert assess_grounding_strength(0.40) == GroundingStrength.NONE
        assert assess_grounding_strength(0.0) == GroundingStrength.NONE

    def test_suggest_confidence_strong_grounding(self):
        """Strong grounding doesn't suggest changes."""
        suggested, note = suggest_confidence_for_grounding("high", GroundingStrength.STRONG)
        assert suggested is None
        assert note is None

    def test_suggest_confidence_partial_grounding_high(self):
        """Partial grounding suggests medium for high confidence."""
        suggested, note = suggest_confidence_for_grounding("high", GroundingStrength.PARTIAL)
        assert suggested == "medium"
        assert note is not None

    def test_suggest_confidence_weak_grounding(self):
        """Weak grounding suggests low confidence."""
        suggested, note = suggest_confidence_for_grounding("high", GroundingStrength.WEAK)
        assert suggested == "low"

        suggested, note = suggest_confidence_for_grounding("medium", GroundingStrength.WEAK)
        assert suggested == "low"

    def test_suggest_confidence_no_grounding(self):
        """No grounding suggests low or removal."""
        suggested, note = suggest_confidence_for_grounding("high", GroundingStrength.NONE)
        assert suggested == "low"

    def test_verify_claim_grounding_exact_match(self):
        """Exact text match returns strong grounding."""
        source = "The company raised $50 million in funding."
        claim = "The company raised $50 million in funding"
        result = verify_claim_grounding("CLM_1", claim, source, "high")

        assert result.grounding_strength == GroundingStrength.STRONG
        assert result.match_score >= 0.90

    def test_verify_claim_grounding_no_match(self):
        """Unrelated text returns no grounding."""
        source = "The weather was nice today."
        claim = "The company raised $50 million in funding"
        result = verify_claim_grounding("CLM_1", claim, source, "high")

        assert result.grounding_strength == GroundingStrength.NONE
        assert result.match_score < 0.50

    def test_verify_claim_grounding_empty_inputs(self):
        """Empty inputs return no grounding."""
        result = verify_claim_grounding("CLM_1", "", "source text", "high")
        assert result.grounding_strength == GroundingStrength.NONE

        result = verify_claim_grounding("CLM_1", "claim text", "", "high")
        assert result.grounding_strength == GroundingStrength.NONE

    def test_verify_claims_grounding_filters_by_threshold(self):
        """Claims below threshold are not verified."""
        claims = [
            {"claim_id": "CLM_1", "statement": "Test claim 1", "confidence": "high"},
            {"claim_id": "CLM_2", "statement": "Test claim 2", "confidence": "low"},
        ]
        source_text = "Test claim 1 is in the source."

        results, summary = verify_claims_grounding(
            claims, source_text, "SRC_1",
            confidence_threshold="high",
        )

        # Only high confidence claim should be verified
        assert len(results) == 1
        assert results[0].claim_id == "CLM_1"

    def test_apply_grounding_adjustments(self):
        """Grounding adjustments are applied correctly."""
        claims = [
            {"claim_id": "CLM_1", "statement": "Test", "confidence": "high"},
        ]
        grounding_results = [
            GroundingResult(
                claim_id="CLM_1",
                claim_text="Test",
                original_confidence="high",
                grounding_strength=GroundingStrength.WEAK,
                match_score=0.55,
                suggested_confidence="low",
                grounding_note="Weak grounding",
            )
        ]

        adjusted, warnings = apply_grounding_adjustments(claims, grounding_results)

        assert adjusted[0]["confidence"] == "low"
        assert adjusted[0].get("_grounding_adjusted") is True
        assert len(warnings) == 1


# =============================================================================
# Confidence Penalty Weights Tests
# =============================================================================

class TestConfidencePenalties:
    """Tests for confidence penalty weights in validation."""

    def test_penalty_weights_defined(self):
        """Penalty weights are defined for all confidence levels."""
        assert ConfidenceLevel.HIGH in CONFIDENCE_PENALTY_WEIGHTS
        assert ConfidenceLevel.MEDIUM in CONFIDENCE_PENALTY_WEIGHTS
        assert ConfidenceLevel.LOW in CONFIDENCE_PENALTY_WEIGHTS

    def test_penalty_weights_ordering(self):
        """HIGH confidence has highest penalty."""
        assert CONFIDENCE_PENALTY_WEIGHTS[ConfidenceLevel.HIGH] > CONFIDENCE_PENALTY_WEIGHTS[ConfidenceLevel.MEDIUM]
        assert CONFIDENCE_PENALTY_WEIGHTS[ConfidenceLevel.MEDIUM] > CONFIDENCE_PENALTY_WEIGHTS[ConfidenceLevel.LOW]

    def test_calculate_weighted_error_score_empty(self):
        """Empty results return zero score."""
        score = calculate_weighted_error_score([], {})
        assert score == 0.0

    def test_calculate_weighted_error_score_hard_fail(self):
        """Hard failures contribute to score."""
        results = [
            ValidationResult(
                level=ValidationLevel.HARD_FAIL,
                message="Test error",
                field="test",
            )
        ]
        score = calculate_weighted_error_score(results, {})
        assert score > 0

    def test_should_downgrade_below_threshold(self):
        """Scores below threshold don't trigger downgrade."""
        assert not should_downgrade_source_confidence(3.0)
        assert not should_downgrade_source_confidence(4.9)

    def test_should_downgrade_above_threshold(self):
        """Scores above threshold trigger downgrade."""
        assert should_downgrade_source_confidence(5.0)
        assert should_downgrade_source_confidence(10.0)

    def test_get_confidence_penalty_summary(self):
        """Summary includes all expected fields."""
        results = [
            ValidationResult(
                level=ValidationLevel.SOFT_FAIL,
                message="Test",
                field="test",
            )
        ]
        summary = get_confidence_penalty_summary(results, {})

        assert "weighted_error_score" in summary
        assert "should_downgrade_source" in summary
        assert "threshold" in summary


# =============================================================================
# LLM Judge Tests
# =============================================================================

class TestLlmJudge:
    """Tests for LLM judge parsing and application."""

    def test_judge_verdict_enum(self):
        """JudgeVerdict enum has expected values."""
        assert JudgeVerdict.VALID.value == "valid"
        assert JudgeVerdict.QUESTIONABLE.value == "questionable"
        assert JudgeVerdict.INVALID.value == "invalid"

    def test_overall_quality_enum(self):
        """OverallQuality enum has expected values."""
        assert OverallQuality.HIGH.value == "high"
        assert OverallQuality.MEDIUM.value == "medium"
        assert OverallQuality.LOW.value == "low"

    def test_item_review_to_dict(self):
        """ItemReview serializes correctly."""
        item = ItemReview(
            item_id="KP_1",
            item_type="key_point",
            verdict=JudgeVerdict.VALID,
            grounding="grounded",
        )
        d = item.to_dict()
        assert d["item_id"] == "KP_1"
        assert d["verdict"] == "valid"

    def test_judge_result_validation_rate(self):
        """JudgeResult calculates validation rate correctly."""
        result = JudgeResult(
            items_reviewed=[
                ItemReview("KP_1", "key_point", JudgeVerdict.VALID, "grounded"),
                ItemReview("KP_2", "key_point", JudgeVerdict.INVALID, "ungrounded"),
            ]
        )
        assert result.valid_count == 1
        assert result.invalid_count == 1
        assert result.validation_rate == 0.5

    def test_parse_judge_response_valid(self):
        """Valid judge response parses correctly."""
        response_data = {
            "items_reviewed": [
                {
                    "item_id": "KP_1",
                    "item_type": "key_point",
                    "verdict": "valid",
                    "grounding": "grounded",
                    "issues": [],
                }
            ],
            "quotes_reviewed": [],
            "overall_quality": "high",
            "hallucination_flags": [],
            "confidence_overrides": [],
            "summary": "Good extraction",
        }

        result = parse_judge_response(response_data)

        assert len(result.items_reviewed) == 1
        assert result.items_reviewed[0].verdict == JudgeVerdict.VALID
        assert result.overall_quality == OverallQuality.HIGH
        assert result.summary == "Good extraction"

    def test_parse_judge_response_with_hallucinations(self):
        """Hallucination flags are parsed correctly."""
        response_data = {
            "items_reviewed": [],
            "quotes_reviewed": [],
            "overall_quality": "low",
            "hallucination_flags": ["KP_1", "CLM_2"],
            "confidence_overrides": [],
            "summary": "Multiple hallucinations detected",
        }

        result = parse_judge_response(response_data)

        assert result.hallucination_flags == ["KP_1", "CLM_2"]
        assert result.overall_quality == OverallQuality.LOW

    def test_parse_judge_response_with_overrides(self):
        """Confidence overrides are parsed correctly."""
        response_data = {
            "items_reviewed": [],
            "quotes_reviewed": [],
            "overall_quality": "medium",
            "hallucination_flags": [],
            "confidence_overrides": [
                {
                    "item_id": "KP_1",
                    "original": "high",
                    "suggested": "medium",
                    "reason": "Circumstantial evidence",
                }
            ],
            "summary": "",
        }

        result = parse_judge_response(response_data)

        assert len(result.confidence_overrides) == 1
        assert result.confidence_overrides[0].item_id == "KP_1"
        assert result.confidence_overrides[0].suggested == "medium"

    def test_apply_judge_verdicts_confidence_override(self):
        """Confidence overrides are applied to extraction."""
        extraction = {
            "key_points": [
                {"key_point_id": "KP_1", "confidence": "high", "statement": "Test"},
            ],
            "claims": [],
            "quotes": [],
        }

        judge_result = JudgeResult(
            confidence_overrides=[
                ConfidenceOverride("KP_1", "high", "medium", "Weak evidence"),
            ]
        )

        updated, warnings = apply_judge_verdicts(extraction, judge_result)

        assert updated["key_points"][0]["confidence"] == "medium"
        assert updated["key_points"][0].get("_judge_override") is True
        assert len(warnings) == 1

    def test_apply_judge_verdicts_hallucination_flags(self):
        """Hallucination flags mark items and set low confidence."""
        extraction = {
            "key_points": [
                {"key_point_id": "KP_1", "confidence": "high", "statement": "Test"},
            ],
            "claims": [],
            "quotes": [],
        }

        judge_result = JudgeResult(
            hallucination_flags=["KP_1"]
        )

        updated, warnings = apply_judge_verdicts(extraction, judge_result)

        assert updated["key_points"][0]["confidence"] == "low"
        assert updated["key_points"][0].get("_hallucination_flag") is True
        assert len(warnings) == 1
        assert "HALLUCINATION FLAG" in warnings[0]


# =============================================================================
# Error-Specific Retry Prompts Tests
# =============================================================================

class TestRetryPrompts:
    """Tests for error-specific retry prompts."""

    def test_get_retry_prompt_schema(self):
        """Schema error type returns schema retry prompt."""
        prompt = get_retry_prompt("schema", ["Missing key_point_id"])
        assert "schema" in prompt.lower() or "required" in prompt.lower()
        assert "Missing key_point_id" in prompt

    def test_get_retry_prompt_hallucination(self):
        """Hallucination error type returns hallucination retry prompt."""
        prompt = get_retry_prompt("hallucination", ["Quote not found"])
        assert "hallucin" in prompt.lower() or "fabricat" in prompt.lower()
        assert "Quote not found" in prompt

    def test_get_retry_prompt_grounding(self):
        """Grounding error type returns grounding retry prompt."""
        prompt = get_retry_prompt("grounding", ["No source references"])
        assert "grounding" in prompt.lower() or "source" in prompt.lower()
        assert "No source references" in prompt

    def test_get_retry_prompt_thin(self):
        """Thin output returns default retry prompt."""
        prompt = get_retry_prompt("thin", ["Too few key points"])
        assert "specific" in prompt.lower() or "more" in prompt.lower()


# =============================================================================
# HallucinationConfig Tests
# =============================================================================

class TestHallucinationConfig:
    """Tests for HallucinationConfig feature flags."""

    def test_default_config(self):
        """Default config has expected values."""
        config = HallucinationConfig()

        # LLM judge on by default
        assert config.enable_llm_judge is True
        assert config.llm_judge_model == "gpt-4o"

        # RAG grounding on by default
        assert config.enable_rag_grounding is True

        # Semantic entropy off by default
        assert config.enable_semantic_entropy is False

    def test_rag_grounding_config(self):
        """RAG grounding config fields work correctly."""
        config = HallucinationConfig(
            enable_rag_grounding=True,
            rag_confidence_threshold="medium",
            max_claims_to_rag_verify=20,
        )

        assert config.enable_rag_grounding is True
        assert config.rag_confidence_threshold == "medium"
        assert config.max_claims_to_rag_verify == 20

    def test_job_config_should_enable_llm_judge(self):
        """JobConfig correctly determines LLM judge enablement."""
        config = JobConfig(topic="Test")
        assert config.should_enable_llm_judge() is True

        config.hallucination.enable_llm_judge = False
        assert config.should_enable_llm_judge() is False

    def test_job_config_should_enable_rag_grounding(self):
        """JobConfig correctly determines RAG grounding enablement."""
        config = JobConfig(topic="Test")
        assert config.should_enable_rag_grounding() is True  # Default ON

        config.hallucination.enable_rag_grounding = False
        assert config.should_enable_rag_grounding() is False

    def test_job_config_should_enable_semantic_entropy(self):
        """JobConfig correctly determines semantic entropy enablement."""
        config = JobConfig(topic="Test", mode=ResearchMode.CLAIMS_EVIDENCE)
        assert config.should_enable_semantic_entropy() is False

        # Auto-enable for investigation mode
        config = JobConfig(topic="Test", mode=ResearchMode.INVESTIGATION)
        assert config.should_enable_semantic_entropy() is True


# =============================================================================
# Schema Tests
# =============================================================================

class TestSemanticExtractionSchema:
    """Tests for updated semantic extraction schema."""

    def test_schema_has_reasoning_trace(self):
        """Schema includes reasoning_trace field."""
        # Check that the model has the field
        assert "reasoning_trace" in SemanticExtractionSchema.model_fields

    def test_schema_has_confidence_rationale(self):
        """KeyPoint and Claim schemas have confidence_rationale."""
        assert "confidence_rationale" in KeyPointSchema.model_fields
        assert "confidence_rationale" in ClaimSchema.model_fields

    def test_schema_validation_with_rationale(self):
        """Schema validates with confidence_rationale."""
        key_point = KeyPointSchema(
            key_point_id="KP_1",
            statement="Test statement",
            source_ids=["SRC_1"],
            supporting_claims=["CLM_1"],
            confidence="high",
            confidence_rationale="Verbatim quote present at 2:34",
        )

        assert key_point.confidence_rationale == "Verbatim quote present at 2:34"
