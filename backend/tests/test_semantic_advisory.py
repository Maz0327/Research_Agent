"""Tests for the post-Read semantic advisory deterministic spine.

Covers the exact defect classes the 2026-08-30 owner test exposed: the S09
corpus polarity bug (confirming evidence escalated as conflict), the S11
nothing-found tier, and the aggregation ladder ordering.
"""

import pytest

from backend.pipeline.semantic_advisory import (
    assemble_advisory_report,
    deduplicate_evidence,
    deterministic_advisory,
    evidence_identity,
    full_source_candidate_regions,
    route_corpus_relations,
    source_sentence_units,
)


def direct(claim_id: str, status: str) -> dict:
    return {
        "claim_id": claim_id,
        "type": "DIRECT_SOURCE_CLAIM",
        "direct_referee": {"system_result": {"status": status}},
        "retrieval": {"candidates": []},
    }


def inference(claim_id: str, status: str) -> dict:
    return {
        "claim_id": claim_id,
        "type": "SOURCE_GROUNDED_INFERENCE",
        "inference_referee": {"system_result": {"status": status}},
    }


def corpus(claim_id: str, conceptual: str) -> dict:
    return {
        "claim_id": claim_id,
        "type": "CORPUS_META",
        "corpus_check": {"conceptual_result": conceptual},
    }


def analysis(claim_id: str) -> dict:
    return {"claim_id": claim_id, "type": "WRITER_ANALYSIS"}


class TestSourceSentenceUnits:
    def test_offsets_slice_exactly(self):
        text = "First sentence. Second one! And a third?  \n\nNew paragraph here."
        units = source_sentence_units(text)
        assert [u["text"] for u in units] == [
            "First sentence.",
            "Second one!",
            "And a third?",
            "New paragraph here.",
        ]
        for unit in units:
            assert text[unit["start_char"] : unit["end_char"]] == unit["text"]

    def test_transcript_chunking_for_punctuation_free_text(self):
        text = " ".join(f"word{i}" for i in range(150))
        units = source_sentence_units(text)
        assert all(u["unit_kind"] == "bounded_transcript_unit" for u in units)
        assert sum(len(u["text"].split()) for u in units) == 150

    def test_closing_quote_absorbed(self):
        text = 'He said "stop." Then left.'
        units = source_sentence_units(text)
        assert units[0]["text"] == 'He said "stop."'


class TestFullSourceRegions:
    def test_semantic_anchor_wins_rank_one(self):
        units = source_sentence_units("Alpha beta. Gamma delta. Target sentence here.")
        vectors = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]
        regions = full_source_candidate_regions(
            {"target"}, [0.0, 1.0], units, vectors, radius=0
        )
        assert regions[0]["start_sentence_index"] == 2
        assert regions[0]["semantic_anchor_ranks"][0] == 1

    def test_mismatched_vectors_rejected(self):
        units = source_sentence_units("One. Two.")
        with pytest.raises(ValueError):
            full_source_candidate_regions(set(), [1.0], units, [[1.0]])


class TestEvidenceDedup:
    def make_claim(self, claim_id, spans):
        return {
            "claim_id": claim_id,
            "retrieval": {
                "candidates": [
                    {
                        "fact_id": fact_id,
                        "fact_text": fact_text,
                        "evidence_proposal": {
                            "status": "SPAN_FOUND",
                            "source_id": source_id,
                            "start_char": start,
                            "end_char": end,
                            "exact_raw_text": text,
                        },
                    }
                    for (fact_id, fact_text, source_id, start, end, text) in spans
                ]
            },
        }

    def test_same_span_same_source_collapses(self):
        claim = self.make_claim(
            "C1",
            [
                ("SRC_1:F_1", "fact a", "SRC_1", 10, 50, "the exact span"),
                ("SRC_1:F_2", "fact b", "SRC_1", 10, 50, "the exact  span"),
            ],
        )
        evidence, stats = deduplicate_evidence([claim])
        assert stats["unique_evidence_ids"] == 1
        assert stats["duplicates_eliminated"] == 1
        assert evidence[0]["supporting_fact_ids"] == ["SRC_1:F_1", "SRC_1:F_2"]

    def test_different_sources_never_merge(self):
        claim = self.make_claim(
            "C1",
            [
                ("SRC_1:F_1", "fact a", "SRC_1", 10, 50, "identical wording"),
                ("SRC_2:F_9", "fact a", "SRC_2", 10, 50, "identical wording"),
            ],
        )
        _, stats = deduplicate_evidence([claim])
        assert stats["unique_evidence_ids"] == 2
        assert stats["duplicates_eliminated"] == 0

    def test_identity_is_stable(self):
        proposal = {
            "source_id": "SRC_1",
            "start_char": 5,
            "end_char": 9,
            "exact_raw_text": "a  b",
        }
        same = dict(proposal, exact_raw_text="a b")
        assert evidence_identity(proposal) == evidence_identity(same)


class TestCorpusPolarity:
    WINDOWS = [
        {"candidate_id": "CW_01", "source_id": "SRC_9"},
        {"candidate_id": "CW_02", "source_id": "SRC_3"},
    ]

    def test_supporting_passage_is_never_a_counterexample(self):
        # The S09 bug: evidence FOR a negative claim must not escalate.
        result = route_corpus_relations(
            self.WINDOWS, {"CW_01": "SUPPORTS_CLAIM", "CW_02": "UNRELATED"}
        )
        assert result["conceptual_result"] == "NOTHING_FOUND"
        assert result["counterexamples"] == []
        assert len(result["confirming_passages"]) == 1
        assert result["nothing_found_is_proof_of_absence"] is False

    def test_contradicting_passage_is_a_counterexample(self):
        result = route_corpus_relations(
            self.WINDOWS, {"CW_01": "CONTRADICTS_CLAIM", "CW_02": "SUPPORTS_CLAIM"}
        )
        assert result["conceptual_result"] == "POSSIBLE_COUNTEREXAMPLE_FOUND"
        assert [w["candidate_id"] for w in result["counterexamples"]] == ["CW_01"]

    def test_invalid_relation_rejected(self):
        with pytest.raises(ValueError):
            route_corpus_relations(self.WINDOWS, {"CW_01": "MAYBE", "CW_02": "UNRELATED"})


class TestAdvisoryLadder:
    def test_conflict_outranks_everything(self):
        result = deterministic_advisory(
            [direct("C1", "CONFLICT"), direct("C2", "PARTIALLY_SUPPORTED"), corpus("C3", "NOTHING_FOUND")]
        )
        assert result["deterministic_status"] == "SEMANTIC_CONFLICT"
        assert result["triggering_claim_ids"] == ["C1"]

    def test_does_not_follow_is_a_conflict(self):
        result = deterministic_advisory([direct("C1", "SUPPORTED"), inference("C2", "DOES_NOT_FOLLOW")])
        assert result["deterministic_status"] == "SEMANTIC_CONFLICT"

    def test_corpus_counterexample_is_a_conflict(self):
        result = deterministic_advisory([corpus("C1", "POSSIBLE_COUNTEREXAMPLE_FOUND")])
        assert result["deterministic_status"] == "SEMANTIC_CONFLICT"

    def test_partial_before_unverified(self):
        result = deterministic_advisory(
            [direct("C1", "PARTIALLY_SUPPORTED"), direct("C2", "INSUFFICIENT_EVIDENCE")]
        )
        assert result["deterministic_status"] == "PARTIAL_WARNING"

    def test_check_incomplete_is_unverified(self):
        result = deterministic_advisory([corpus("C1", "CHECK_INCOMPLETE")])
        assert result["deterministic_status"] == "UNVERIFIED"

    def test_nothing_found_gets_its_own_tier(self):
        # The S11 fix: a clean negative-claim search is not "unverified".
        result = deterministic_advisory([direct("C1", "SUPPORTED"), corpus("C2", "NOTHING_FOUND")])
        assert result["deterministic_status"] == "NOTHING_FOUND_AGAINST"
        assert result["triggering_claim_ids"] == ["C2"]

    def test_all_clean_is_no_issue(self):
        result = deterministic_advisory([direct("C1", "SUPPORTED"), inference("C2", "REASONABLE_INFERENCE")])
        assert result["deterministic_status"] == "NO_SEMANTIC_ISSUE_FOUND"

    def test_pure_analysis_needs_no_verification(self):
        result = deterministic_advisory([analysis("C1"), analysis("C2")])
        assert result["deterministic_status"] == "NO_SOURCE_VERIFICATION_REQUIRED"
        assert result["triggering_claim_ids"] == ["C1", "C2"]


class TestReportAssembly:
    def test_report_never_gates_and_counts_advisories(self):
        sentences = [
            {"sentence_id": "S1", "sentence": "A fact.", "claims": [direct("S1:C1", "SUPPORTED")]},
            {"sentence_id": "S2", "sentence": "Opinion.", "claims": [analysis("S2:C1")]},
            {"sentence_id": "S3", "sentence": "Negative.", "claims": [corpus("S3:C1", "NOTHING_FOUND")]},
        ]
        report = assemble_advisory_report("test-read", sentences)
        assert report["doctrine"]["gates_output"] is False
        assert report["doctrine"]["modifies_writer_inputs"] is False
        assert report["doctrine"]["modifies_read"] is False
        assert "noisy" in report["doctrine"]["referee_noise_caveat"]
        assert report["advisory_counts"] == {
            "NOTHING_FOUND_AGAINST": 1,
            "NO_SEMANTIC_ISSUE_FOUND": 1,
            "NO_SOURCE_VERIFICATION_REQUIRED": 1,
        }
