"""Tests for the voice repair pass - pairs applied by code, never re-emission."""

from unittest.mock import patch

from backend.models.claim_graph import ClaimGraph
from backend.pipeline.voice_repair import _offending_sentences, repair_voice
from backend.tests.test_briefing_formatter import _graph_dict


class TestOffenderDetection:
    def test_source_opener_detected(self):
        found = _offending_sentences(
            "One source says the look changed. The cameras got better."
        )
        assert len(found) == 1
        assert "source reference" in found[0][1]

    def test_trailing_attribution_is_legal(self):
        found = _offending_sentences(
            "The look changed, and one of the essayists admits that outright."
        )
        assert found == []

    def test_register_word_detected(self):
        found = _offending_sentences(
            "The whole corpus critiques the modern look at length."
        )
        assert len(found) == 1

    def test_clean_prose_passes(self):
        assert _offending_sentences(
            "Budgets are tight and the image followed the money."
        ) == []


class TestPairApplication:
    def _run(self, graph, edits):
        with patch(
            "backend.integrations.structured_client.get_structured_client"
        ) as factory:
            factory.return_value.generate_structured.return_value = (
                {"edits": edits},
                {"cost": 0.01},
            )
            return repair_voice("test-job", graph)

    def test_pair_applied_in_place(self):
        data = _graph_dict()
        data["sections"][0]["body"] = (
            "One source says budgets are tight. The image followed the money."
        )
        graph = ClaimGraph.model_validate(data)
        graph, stats = self._run(
            graph,
            [
                {
                    "old": "One source says budgets are tight.",
                    "new": "Budgets are tight, one article points out.",
                }
            ],
        )
        assert stats["applied"] == 1
        assert "One source says" not in graph.sections[0].body
        assert "The image followed the money." in graph.sections[0].body

    def test_unfound_pair_skipped_never_fuzzy(self):
        data = _graph_dict()
        data["sections"][0]["body"] = "One source says budgets are tight."
        graph = ClaimGraph.model_validate(data)
        graph, stats = self._run(
            graph,
            [{"old": "One source says budgets are loose.", "new": "Whatever."}],
        )
        assert stats["applied"] == 0
        assert stats["skipped"] == 1
        assert graph.sections[0].body == "One source says budgets are tight."

    def test_rewrite_that_still_offends_is_rejected(self):
        data = _graph_dict()
        data["sections"][0]["body"] = "One source says budgets are tight."
        graph = ClaimGraph.model_validate(data)
        graph, stats = self._run(
            graph,
            [
                {
                    "old": "One source says budgets are tight.",
                    "new": "A separate article says budgets are tight.",
                }
            ],
        )
        assert stats["applied"] == 0
        assert stats["skipped"] == 1

    def test_clean_graph_makes_no_call(self):
        data = _graph_dict()
        graph = ClaimGraph.model_validate(data)
        with patch(
            "backend.integrations.structured_client.get_structured_client"
        ) as factory:
            graph, stats = repair_voice("test-job", graph)
            factory.assert_not_called()
        assert stats["offenders"] == 0
