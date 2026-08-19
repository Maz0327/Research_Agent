"""Tests for judge counting and flag reconciliation.

Cover for P3 work-order item B9. The extraction stage logged the whole
`items_reviewed` list where a count belonged, and reported every id the judge
put in `hallucination_flags` as a hallucination even when the same response
marked those items VALID. A clean extraction could be downgraded to LOW
confidence across the board on the strength of a self-contradictory response.
"""
from backend.pipeline.llm_judge import (
    ItemReview,
    JudgeResult,
    JudgeVerdict,
    apply_judge_verdicts,
)


def _review(item_id: str, verdict: JudgeVerdict) -> ItemReview:
    """One reviewed item with the given verdict."""
    return ItemReview(
        item_id=item_id,
        item_type="key_point",
        verdict=verdict,
        grounding="grounded",
    )


class TestFlagReconciliation:
    """A flag only counts when the judge's own verdict supports it."""

    def test_flags_on_valid_items_are_contradictory(self):
        """The observed bug: everything VALID, everything flagged."""
        result = JudgeResult(
            items_reviewed=[
                _review("SRC_1:KP_1", JudgeVerdict.VALID),
                _review("SRC_1:KP_2", JudgeVerdict.VALID),
            ],
            hallucination_flags=["SRC_1:KP_1", "SRC_1:KP_2"],
        )

        assert result.confirmed_hallucination_flags == []
        assert result.contradictory_hallucination_flags == ["SRC_1:KP_1", "SRC_1:KP_2"]

    def test_flags_on_invalid_items_are_confirmed(self):
        """A flag that agrees with its verdict is acted on."""
        result = JudgeResult(
            items_reviewed=[
                _review("SRC_1:KP_1", JudgeVerdict.INVALID),
                _review("SRC_1:KP_2", JudgeVerdict.QUESTIONABLE),
            ],
            hallucination_flags=["SRC_1:KP_1", "SRC_1:KP_2"],
        )

        assert result.confirmed_hallucination_flags == ["SRC_1:KP_1", "SRC_1:KP_2"]
        assert result.contradictory_hallucination_flags == []

    def test_flags_for_unreviewed_items_are_kept(self):
        """With no verdict to contradict it, a flag stands."""
        result = JudgeResult(
            items_reviewed=[_review("SRC_1:KP_1", JudgeVerdict.VALID)],
            hallucination_flags=["SRC_1:KP_9"],
        )

        assert result.confirmed_hallucination_flags == ["SRC_1:KP_9"]

    def test_stats_report_both_numbers(self):
        """The serialized stats carry the item count and both flag counts."""
        result = JudgeResult(
            items_reviewed=[
                _review("SRC_1:KP_1", JudgeVerdict.VALID),
                _review("SRC_1:KP_2", JudgeVerdict.INVALID),
            ],
            hallucination_flags=["SRC_1:KP_1", "SRC_1:KP_2"],
        )

        stats = result.to_dict()["stats"]

        assert stats["items_reviewed"] == 2
        assert stats["valid"] == 1
        assert stats["invalid"] == 1
        assert stats["hallucination_flags"] == 1
        assert stats["contradictory_flags"] == 1


class TestApplyJudgeVerdicts:
    """Confidence is not destroyed by a self-contradictory response."""

    def _extraction(self):
        return {
            "key_points": [
                {"key_point_id": "SRC_1:KP_1", "confidence": "high", "statement": "A point"},
            ],
            "claims": [],
            "quotes": [],
        }

    def test_valid_item_keeps_its_confidence(self):
        """A VALID item flagged as fabricated is not downgraded."""
        result = JudgeResult(
            items_reviewed=[_review("SRC_1:KP_1", JudgeVerdict.VALID)],
            hallucination_flags=["SRC_1:KP_1"],
        )

        updated, warnings = apply_judge_verdicts(self._extraction(), result)

        assert updated["key_points"][0]["confidence"] == "high"
        assert updated["key_points"][0].get("_hallucination_flag") is None
        assert any("the verdict wins" in w for w in warnings)

    def test_invalid_item_is_downgraded(self):
        """A flag the judge's verdict supports still does its job."""
        result = JudgeResult(
            items_reviewed=[_review("SRC_1:KP_1", JudgeVerdict.INVALID)],
            hallucination_flags=["SRC_1:KP_1"],
        )

        updated, warnings = apply_judge_verdicts(self._extraction(), result)

        assert updated["key_points"][0]["confidence"] == "low"
        assert updated["key_points"][0].get("_hallucination_flag") is True
        assert any("HALLUCINATION FLAG" in w for w in warnings)
