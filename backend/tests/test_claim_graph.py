"""Tests for the Claim Graph model and its structural invariants.

These guard the invariants EXECUTION-PLAN P1 names as the gate: claim count
bounds, evidence refs resolving to real sources, every hole attached, and no
orphan story goods.
"""

import pytest
from pydantic import ValidationError

from backend.models.claim_graph import (
    MAX_CLAIMS,
    MIN_CLAIMS,
    ClaimGraph,
    normalize_wire_payload,
    api_json_schema,
)
from backend.pipeline.stages.distillation_stage import (
    build_corpus,
    confidence_ceiling_grade,
)
from backend.models.semantic_units import ConfidenceLevel


def _claim(n: int, **overrides) -> dict:
    claim = {
        "id": f"CLM_{n}",
        "title": f"Claim number {n} says something a person would say.",
        "what_sources_say": "Two sources land here independently.",
        "pushback": None,
        "my_read": None,
        "say_it_like": f"Here is claim {n}, out loud.",
        "confidence": {"grade": 3, "reason": "Two sources, quotes unverified."},
        "evidence_status": "multi_source",
        "evidence": [{"source_id": "SRC_1", "quote_ref": None, "timestamp": None}],
        "story_goods": [],
        "spine_order": n,
        "tags": [],
    }
    claim.update(overrides)
    return claim


def _graph(claim_count: int = MIN_CLAIMS, **overrides) -> dict:
    graph = {
        "graph_version": "1",
        "job_id": "job-1",
        "topic": "why films look the way they do",
        "thesis": {
            "text": "The look changed because the money changed.",
            "confidence": "usable",
            "based_on": ["CLM_1"],
        },
        "claims": [_claim(i) for i in range(1, claim_count + 1)],
        "story_goods": [],
        "holes": [],
        "sources_ranked": [],
    }
    graph.update(overrides)
    return graph


class TestClaimCountBounds:
    def test_accepts_minimum(self):
        assert len(ClaimGraph.model_validate(_graph(MIN_CLAIMS)).claims) == MIN_CLAIMS

    def test_accepts_maximum(self):
        assert len(ClaimGraph.model_validate(_graph(MAX_CLAIMS)).claims) == MAX_CLAIMS

    def test_rejects_too_few(self):
        with pytest.raises(ValidationError, match="claim count"):
            ClaimGraph.model_validate(_graph(MIN_CLAIMS - 1))

    def test_rejects_too_many(self):
        with pytest.raises(ValidationError, match="claim count"):
            ClaimGraph.model_validate(_graph(MAX_CLAIMS + 1))


class TestIdentity:
    def test_rejects_duplicate_claim_ids(self):
        graph = _graph()
        graph["claims"][1]["id"] = graph["claims"][0]["id"]
        with pytest.raises(ValidationError, match="duplicate claim ids"):
            ClaimGraph.model_validate(graph)

    def test_rejects_wrong_id_prefix(self):
        graph = _graph()
        graph["claims"][0]["id"] = "CLAIM_1"
        with pytest.raises(ValidationError, match="must start with 'CLM_'"):
            ClaimGraph.model_validate(graph)

    def test_rejects_duplicate_spine_order(self):
        graph = _graph()
        graph["claims"][1]["spine_order"] = graph["claims"][0]["spine_order"]
        with pytest.raises(ValidationError, match="duplicate spine_order"):
            ClaimGraph.model_validate(graph)


class TestHolesAttach:
    def test_accepts_hole_on_claim(self):
        graph = _graph()
        graph["holes"] = [
            {
                "id": "HOLE_1",
                "attached_to": "CLM_1",
                "missing": "The studio's own numbers.",
                "hurts_because": "The claim rests on one outside estimate.",
                "severity": 4,
                "how_to_fill": "Annual report or an on-record producer.",
            }
        ]
        assert len(ClaimGraph.model_validate(graph).holes_for("CLM_1")) == 1

    def test_accepts_hole_on_thesis(self):
        graph = _graph()
        graph["holes"] = [
            {
                "id": "HOLE_1",
                "attached_to": "thesis",
                "missing": "Anything from the other side.",
                "hurts_because": "The whole argument is one-sided.",
                "severity": 5,
            }
        ]
        ClaimGraph.model_validate(graph)

    def test_rejects_unattached_hole(self):
        graph = _graph()
        graph["holes"] = [
            {
                "id": "HOLE_1",
                "attached_to": "CLM_99",
                "missing": "x",
                "hurts_because": "y",
                "severity": 3,
            }
        ]
        with pytest.raises(ValidationError, match="attached to unknown claim"):
            ClaimGraph.model_validate(graph)


class TestStoryGoods:
    def test_rejects_orphan_story_good(self):
        graph = _graph()
        graph["story_goods"] = [
            {
                "id": "STG_1",
                "type": "number",
                "text": "The budget tripled between the two films.",
                "source_id": "SRC_1",
                "claim_ids": [],
            }
        ]
        with pytest.raises(ValidationError, match="orphan story good"):
            ClaimGraph.model_validate(graph)

    def test_rejects_story_good_pointing_at_missing_claim(self):
        graph = _graph()
        graph["story_goods"] = [
            {
                "id": "STG_1",
                "type": "scene",
                "text": "They screened it twice in an empty theater.",
                "source_id": "SRC_1",
                "claim_ids": ["CLM_99"],
            }
        ]
        with pytest.raises(ValidationError, match="unknown claim"):
            ClaimGraph.model_validate(graph)

    def test_rejects_claim_pointing_at_missing_story_good(self):
        graph = _graph()
        graph["claims"][0]["story_goods"] = ["STG_404"]
        with pytest.raises(ValidationError, match="unknown story good"):
            ClaimGraph.model_validate(graph)


class TestLedgerValidation:
    def test_clean_graph_reports_no_problems(self):
        graph = ClaimGraph.model_validate(_graph())
        assert graph.validate_against_ledger({"SRC_1"}) == []

    def test_flags_evidence_citing_unknown_source(self):
        graph = ClaimGraph.model_validate(_graph())
        problems = graph.validate_against_ledger({"SRC_2"})
        assert problems
        assert "unknown source SRC_1" in problems[0]

    def test_flags_claim_with_no_evidence(self):
        graph = _graph()
        graph["claims"][0]["evidence"] = []
        problems = ClaimGraph.model_validate(graph).validate_against_ledger({"SRC_1"})
        assert any("has no evidence" in p for p in problems)


class TestThesisAndGround:
    def test_rejects_thesis_referencing_unknown_claim(self):
        graph = _graph()
        graph["thesis"]["based_on"] = ["CLM_99"]
        with pytest.raises(ValidationError, match="thesis based_on"):
            ClaimGraph.model_validate(graph)

    def test_rejects_ground_referencing_unknown_claim(self):
        graph = _graph()
        graph["weakest_ground"] = {"claim_id": "CLM_99", "why": "shaky"}
        with pytest.raises(ValidationError, match="weakest_ground"):
            ClaimGraph.model_validate(graph)


class TestSchemaFutureProofing:
    def test_market_context_ships_in_v1(self):
        """V2's Strategist Brief depends on this field existing from day one."""
        assert "market_context" in ClaimGraph.model_json_schema()["properties"]
        assert "market_context" in api_json_schema()["$defs"]["Claim"]["properties"]

    def test_market_context_is_optional(self):
        ClaimGraph.model_validate(_graph())  # omitted entirely

    def test_market_context_accepted_when_supplied(self):
        graph = _graph()
        graph["claims"][0]["market_context"] = {
            "who_else_serves_this": "Two long-form channels cover this ground.",
            "supply_vs_demand": "Steady search interest, little recent coverage.",
            "based_on": ["SRC_1"],
        }
        parsed = ClaimGraph.model_validate(graph)
        assert parsed.claims[0].market_context.based_on == ["SRC_1"]


class TestWireSchema:
    def test_strips_keywords_structured_outputs_reject(self):
        schema = api_json_schema()
        banned = {
            "minimum",
            "maximum",
            "minLength",
            "maxLength",
            "pattern",
            "format",
            "minItems",
            "default",
        }

        def walk(node, found):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in banned:
                        found.add(key)
                    walk(value, found)
            elif isinstance(node, list):
                for item in node:
                    walk(item, found)
            return found

        assert walk(schema, set()) == set()

    def test_forces_additional_properties_false(self):
        schema = api_json_schema()
        assert schema["additionalProperties"] is False
        for definition in schema["$defs"].values():
            if definition.get("type") == "object":
                assert definition["additionalProperties"] is False

    def test_confidence_grade_survives_as_enum(self):
        """Bounds are stripped, so the 1-5 domain must ride on an enum."""
        grade = api_json_schema()["$defs"]["Confidence"]["properties"]["grade"]
        assert grade["enum"] == [1, 2, 3, 4, 5]

    def test_no_nullable_branches_anywhere(self):
        """The compiled grammar only fits at zero nullable unions.

        Measured against the live API: the schema is rejected as "grammar too
        large" with any nullable branches and compiles at none. If a future
        change reintroduces Optional-as-nullable on the wire, every
        distillation call starts failing with a 400, so fail here instead.
        """
        schema = api_json_schema()

        def walk(node, found):
            if isinstance(node, dict):
                if node.get("type") == "null":
                    found.append(node)
                for value in node.values():
                    walk(value, found)
            elif isinstance(node, list):
                for item in node:
                    walk(item, found)
            return found

        assert walk(schema, []) == []

    def test_every_property_is_required(self):
        """Absence is encoded as emptiness, so no key may be omittable."""
        schema = api_json_schema()
        assert set(schema["required"]) == set(schema["properties"])
        for definition in schema["$defs"].values():
            if "properties" in definition:
                assert set(definition["required"]) == set(definition["properties"])


class TestWirePayloadNormalization:
    def test_empty_optional_strings_become_none(self):
        graph = _graph()
        graph["claims"][0]["pushback"] = ""
        graph["claims"][0]["my_read"] = "   "
        parsed = ClaimGraph.model_validate(normalize_wire_payload(graph))
        assert parsed.claims[0].pushback is None
        assert parsed.claims[0].my_read is None

    def test_real_content_is_left_alone(self):
        graph = _graph()
        graph["claims"][0]["pushback"] = "One source disagrees on the date."
        parsed = ClaimGraph.model_validate(normalize_wire_payload(graph))
        assert parsed.claims[0].pushback == "One source disagrees on the date."

    def test_blank_market_context_becomes_none(self):
        """Most corpora say nothing about the market; that must stay absent."""
        graph = _graph()
        graph["claims"][0]["market_context"] = {
            "who_else_serves_this": "",
            "supply_vs_demand": "",
            "based_on": [],
        }
        parsed = ClaimGraph.model_validate(normalize_wire_payload(graph))
        assert parsed.claims[0].market_context is None

    def test_populated_market_context_survives(self):
        graph = _graph()
        graph["claims"][0]["market_context"] = {
            "who_else_serves_this": "Two channels cover this ground.",
            "supply_vs_demand": "",
            "based_on": ["SRC_1"],
        }
        parsed = ClaimGraph.model_validate(normalize_wire_payload(graph))
        assert parsed.claims[0].market_context is not None
        assert parsed.claims[0].market_context.supply_vs_demand is None

    def test_empty_quote_locators_become_none(self):
        graph = _graph()
        graph["claims"][0]["evidence"] = [
            {"source_id": "SRC_1", "quote_ref": "", "timestamp": ""}
        ]
        parsed = ClaimGraph.model_validate(normalize_wire_payload(graph))
        assert parsed.claims[0].evidence[0].quote_ref is None
        assert parsed.claims[0].evidence[0].timestamp is None


class TestConfidenceCeiling:
    def test_high_ceiling_allows_top_grade(self):
        assert confidence_ceiling_grade([ConfidenceLevel.HIGH], 1.0) == 5

    def test_medium_ceiling_caps_at_four(self):
        assert confidence_ceiling_grade([ConfidenceLevel.MEDIUM], 1.0) == 4

    def test_low_only_corpus_caps_low(self):
        assert confidence_ceiling_grade([ConfidenceLevel.LOW], 1.0) == 2

    def test_best_source_sets_the_cap(self):
        ceilings = [ConfidenceLevel.LOW, ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
        assert confidence_ceiling_grade(ceilings, 1.0) == 5

    def test_unverified_corpus_drops_one_grade(self):
        assert confidence_ceiling_grade([ConfidenceLevel.HIGH], 0.0) == 4

    def test_never_below_one(self):
        assert confidence_ceiling_grade([ConfidenceLevel.LOW], 0.0) == 1

    def test_empty_corpus_is_conservative(self):
        assert confidence_ceiling_grade([], 1.0) == 2


class TestCorpusBuilding:
    def test_key_points_are_namespaced_by_source(self):
        """Key point IDs collide across sources; the corpus must disambiguate."""
        corpus = build_corpus(
            topic="t",
            sources=[{"source_id": "SRC_1"}, {"source_id": "SRC_2"}],
            key_points=[
                {"key_point_id": "KP_1", "statement": "a", "source_ids": ["SRC_1"]},
                {"key_point_id": "KP_1", "statement": "b", "source_ids": ["SRC_2"]},
            ],
            themes=[],
            tensions=[],
            gaps=[],
        )
        refs = [kp["ref"] for kp in corpus["key_points"]]
        assert refs == ["SRC_1:KP_1", "SRC_2:KP_1"]
        assert len(set(refs)) == 2

    def test_key_point_without_source_is_not_dropped(self):
        corpus = build_corpus(
            topic="t",
            sources=[],
            key_points=[{"key_point_id": "KP_1", "statement": "a", "source_ids": []}],
            themes=[],
            tensions=[],
            gaps=[],
        )
        assert corpus["key_points"][0]["ref"] == "UNKNOWN:KP_1"
