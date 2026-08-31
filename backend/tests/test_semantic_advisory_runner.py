"""End-to-end tests for the semantic advisory runner with fake model seats.

A miniature Read (three sentences: a supported fact, pure analysis, and a
negative corpus claim) flows through every stage — decomposition, retrieval,
relevance, full-source localization, dedup, referees, directional corpus
check, report — with injected fakes and zero network access.
"""

import pytest

from backend.pipeline.semantic_advisory import source_sentence_units
from backend.pipeline.semantic_advisory_runner import (
    SemanticAdvisoryRunner,
    actor_mask,
    positive_proposition,
)

SOURCE_TEXT = (
    "The dig started in 2008. The team found a stone wall under the sand. "
    "Nothing here mentions lost continents. The report was published later."
)


class FakeEmbedder:
    """Deterministic vectors: similar texts share tokens, so cosine tracks overlap."""

    VOCAB = ["dig", "2008", "team", "stone", "wall", "sand", "continents", "report", "published"]

    def embed(self, texts):
        vectors = []
        for text in texts:
            tokens = set(text.lower().replace(".", "").split())
            vectors.append([1.0 if word in tokens else 0.0 for word in self.VOCAB])
        return vectors


class FakeModel:
    """Stage-keyed canned responses; records every stage it was asked for."""

    def __init__(self):
        self.stages_called = []

    def generate(self, stage, prompt, schema):
        self.stages_called.append(stage)
        if stage == "stage_1_decomposition":
            if "S1" in prompt:
                return {
                    "claims": [
                        {
                            "type": "DIRECT_SOURCE_CLAIM",
                            "text": "The team found a stone wall under the sand.",
                            "derived_from_indices": [],
                            "reason": "",
                        }
                    ]
                }
            if "S2" in prompt:
                return {
                    "claims": [
                        {
                            "type": "WRITER_ANALYSIS",
                            "text": "The find is striking.",
                            "derived_from_indices": [],
                            "reason": "",
                        }
                    ]
                }
            return {
                "claims": [
                    {
                        "type": "CORPUS_META",
                        "text": "No supplied source identifies a lost continent.",
                        "derived_from_indices": [],
                        "reason": "",
                    }
                ]
            }
        if stage == "stage_3_relevance":
            fact_ids = [
                line.split(": ")[0]
                for line in prompt.split("Candidates:\n")[1].splitlines()
                if ": " in line
            ]
            return {
                "judgments": [
                    {
                        "fact_id": fid,
                        "label": "DIRECTLY_RELEVANT" if fid.endswith("F_1") else "NOT_RELEVANT",
                        "reason": "",
                    }
                    for fid in fact_ids
                ]
            }
        if stage.startswith("stage_4_localization"):
            return {
                "status": "SPAN_FOUND",
                "start_sentence_index": 1,
                "end_sentence_index": 1,
                "reason": "second sentence states it",
            }
        if stage == "stage_6_direct_referee":
            evidence_ids = [
                part.split()[1]
                for part in prompt.split("\n")
                if part.startswith("Evidence E_")
            ]
            return {
                "status": "SUPPORTED",
                "mismatch_dimensions": [],
                "conflicting_evidence": False,
                "evidence_assessments": [
                    {"evidence_id": eid, "relation": "SUPPORTS", "reason": ""}
                    for eid in evidence_ids
                ],
                "reason": "matches",
            }
        if stage == "stage_7_corpus_relation":
            candidate_ids = [
                line.split()[0]
                for line in prompt.splitlines()
                if line.startswith("CW_")
            ]
            return {
                "candidate_assessments": [
                    {"candidate_id": cid, "relation": "SUPPORTS_CLAIM", "reason": ""}
                    for cid in candidate_ids
                ],
                "reason": "",
            }
        raise AssertionError(f"unexpected stage {stage}")


@pytest.fixture()
def report():
    runner = SemanticAdvisoryRunner(FakeModel(), FakeEmbedder(), top_per_route=2)
    return runner.run(
        "mini-read",
        [
            {"sentence_id": "S1", "sentence": "They found a stone wall."},
            {"sentence_id": "S2", "sentence": "The find is striking."},
            {"sentence_id": "S3", "sentence": "No supplied source identifies a lost continent."},
        ],
        [
            {"fact_id": "SRC_1:F_1", "source_id": "SRC_1", "text": "team found a stone wall"},
            {"fact_id": "SRC_1:F_2", "source_id": "SRC_1", "text": "report published later"},
        ],
        [{"source_id": "SRC_1", "full_text": SOURCE_TEXT}],
    )


class TestEndToEnd:
    def test_advisories_per_sentence(self, report):
        by_id = {s["sentence_id"]: s["advisory"]["deterministic_status"] for s in report["sentences"]}
        assert by_id == {
            "S1": "NO_SEMANTIC_ISSUE_FOUND",
            "S2": "NO_SOURCE_VERIFICATION_REQUIRED",
            "S3": "NOTHING_FOUND_AGAINST",
        }

    def test_evidence_span_is_exact_offsets(self, report):
        evidence = report["evidence_objects"]
        assert len(evidence) == 1
        span = evidence[0]
        assert span["exact_raw_text"] == "The team found a stone wall under the sand."
        assert SOURCE_TEXT[span["start_char"] : span["end_char"]] == span["exact_raw_text"]

    def test_corpus_confirming_never_conflicts(self, report):
        s3 = next(s for s in report["sentences"] if s["sentence_id"] == "S3")
        check = s3["claims"][0]["corpus_check"]
        assert check["conceptual_result"] == "NOTHING_FOUND"
        assert check["counterexamples"] == []
        assert len(check["confirming_passages"]) >= 1
        assert check["nothing_found_is_proof_of_absence"] is False

    def test_report_contract(self, report):
        assert report["doctrine"]["gates_output"] is False
        assert report["stats"]["unique_evidence_ids"] == 1
        assert report["advisory_counts"]["NOTHING_FOUND_AGAINST"] == 1

    def test_irrelevant_candidates_not_localized(self, report):
        s1 = next(s for s in report["sentences"] if s["sentence_id"] == "S1")
        candidates = s1["claims"][0]["retrieval"]["candidates"]
        irrelevant = [c for c in candidates if c["system_relevance"]["label"] == "NOT_RELEVANT"]
        assert irrelevant and all(c["evidence_proposal"] is None for c in irrelevant)


class TestLocalizationCache:
    """The same fact retrieved by several claims is located once.

    Where a fact lives in its source depends on the fact and the source; the
    claim goes into the prompt marked "context only". Localization is 85% of
    the calls this runner makes, so re-deriving it is the single most
    expensive thing it can do (2026-08-31).
    """

    def _runner(self):
        return SemanticAdvisoryRunner(FakeModel(), FakeEmbedder(), top_per_route=2)

    def _candidate(self, fact_id="SRC_1:F_1"):
        return {
            "fact_id": fact_id,
            "source_id": "SRC_1",
            "fact_text": "team found a stone wall",
            "system_relevance": {"label": "DIRECTLY_RELEVANT", "reason": ""},
            "evidence_proposal": None,
        }

    def test_a_repeated_fact_is_not_localized_twice(self):
        runner = self._runner()
        units = source_sentence_units(SOURCE_TEXT)
        vectors = runner._embed([u["text"] for u in units])
        claim = {"claim_id": "S1:C01", "text": "They found a wall."}

        first, second = self._candidate(), self._candidate()
        runner.localize(claim, first, SOURCE_TEXT, units, vectors)
        calls_after_first = runner.model.stages_called.count("stage_4_localization")
        runner.localize(claim, second, SOURCE_TEXT, units, vectors)

        assert runner.model.stages_called.count("stage_4_localization") == calls_after_first
        assert runner.localization_calls_saved == 1
        assert second["evidence_proposal"] == first["evidence_proposal"]

    def test_the_cached_copy_is_independent(self):
        """A later claim editing its own proposal must not reach back into the
        one already stored."""
        runner = self._runner()
        units = source_sentence_units(SOURCE_TEXT)
        vectors = runner._embed([u["text"] for u in units])
        claim = {"claim_id": "S1:C01", "text": "They found a wall."}

        first, second = self._candidate(), self._candidate()
        runner.localize(claim, first, SOURCE_TEXT, units, vectors)
        runner.localize(claim, second, SOURCE_TEXT, units, vectors)
        second["evidence_proposal"]["exact_raw_text"] = "TAMPERED"

        assert first["evidence_proposal"]["exact_raw_text"] != "TAMPERED"

    def test_a_different_fact_still_costs_a_call(self):
        runner = self._runner()
        units = source_sentence_units(SOURCE_TEXT)
        vectors = runner._embed([u["text"] for u in units])
        claim = {"claim_id": "S1:C01", "text": "They found a wall."}

        runner.localize(claim, self._candidate("SRC_1:F_1"), SOURCE_TEXT, units, vectors)
        before = runner.model.stages_called.count("stage_4_localization")
        runner.localize(claim, self._candidate("SRC_1:F_2"), SOURCE_TEXT, units, vectors)

        assert runner.model.stages_called.count("stage_4_localization") == before + 1
        assert runner.localization_calls_saved == 0


class TestHelpers:
    def test_actor_mask_masks_names(self):
        assert actor_mask("Louis De Cordier argued the point") == "[P] argued the point"

    def test_positive_proposition_patterns(self):
        assert (
            positive_proposition("No supplied source identifies a lost continent.")
            == "A supplied source identifies a lost continent."
        )
        assert positive_proposition("The pile contains no response from anyone.") is not None
        assert positive_proposition("A weirdly shaped claim about things.") is None


class TestFailureHandling:
    def test_invalid_boundaries_fall_back_to_no_span(self):
        class BadLocalizer(FakeModel):
            def generate(self, stage, prompt, schema):
                if stage.startswith("stage_4"):
                    return {
                        "status": "SPAN_FOUND",
                        "start_sentence_index": 0,
                        "end_sentence_index": 99,
                        "reason": "bad",
                    }
                return super().generate(stage, prompt, schema)

        runner = SemanticAdvisoryRunner(BadLocalizer(), FakeEmbedder(), top_per_route=2)
        result = runner.run(
            "mini",
            [{"sentence_id": "S1", "sentence": "They found a stone wall."}],
            [{"fact_id": "SRC_1:F_1", "source_id": "SRC_1", "text": "team found a stone wall"}],
            [{"source_id": "SRC_1", "full_text": SOURCE_TEXT}],
        )
        claim = result["sentences"][0]["claims"][0]
        proposals = [
            c["evidence_proposal"]
            for c in claim["retrieval"]["candidates"]
            if c["evidence_proposal"]
        ]
        assert proposals and all(p["status"] == "NO_SUPPORTING_SPAN_FOUND" for p in proposals)
        # no located evidence -> deterministic INSUFFICIENT_EVIDENCE, advisory UNVERIFIED
        assert claim["direct_referee"]["system_result"]["generation_mode"] == "deterministic_no_evidence"
        assert result["sentences"][0]["advisory"]["deterministic_status"] == "UNVERIFIED"
