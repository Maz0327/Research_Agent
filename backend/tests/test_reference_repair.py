"""Tests for deterministic claim-reference repair.

Cover for P3 work-order item C11. On job c5d32615 both the primary and the
escalation model returned `thesis.based_on: ["SRC_2", "SRC_5"]`. The thesis
rests on claims, not sources, so validation rejected the graph twice and the
job burned an Opus call on an error with a mechanical answer: the claims that
cite that source are the claims the thesis rests on.
"""
from backend.models.claim_graph import repair_references


def _payload(**overrides) -> dict:
    """A graph payload with two claims citing two sources."""
    payload = {
        "claims": [
            {"id": "CLM_1", "evidence": [{"source_id": "SRC_2"}]},
            {"id": "CLM_2", "evidence": [{"source_id": "SRC_2"}, {"source_id": "SRC_5"}]},
            {"id": "CLM_3", "evidence": [{"source_id": "SRC_9"}]},
        ],
        "thesis": {"text": "A verdict.", "based_on": ["CLM_1"]},
        "story_goods": [],
        "holes": [],
    }
    payload.update(overrides)
    return payload


class TestThesisRepair:
    """The measured failure, repaired without a model call."""

    def test_source_ref_becomes_the_claims_citing_it(self):
        """SRC_2 resolves to every claim whose evidence cites SRC_2."""
        payload = _payload(thesis={"text": "A verdict.", "based_on": ["SRC_2"]})

        repaired, repairs = repair_references(payload)

        assert repaired["thesis"]["based_on"] == ["CLM_1", "CLM_2"]
        assert "thesis.based_on" in repairs[0]

    def test_mixed_refs_keep_the_valid_ones(self):
        """Claim IDs already present survive the repair untouched."""
        payload = _payload(thesis={"text": "A verdict.", "based_on": ["CLM_3", "SRC_5"]})

        repaired, _ = repair_references(payload)

        assert repaired["thesis"]["based_on"] == ["CLM_3", "CLM_2"]

    def test_duplicates_are_collapsed(self):
        """Two sources sharing a claim do not list it twice."""
        payload = _payload(thesis={"text": "A verdict.", "based_on": ["SRC_2", "SRC_5"]})

        repaired, _ = repair_references(payload)

        assert repaired["thesis"]["based_on"] == ["CLM_1", "CLM_2"]

    def test_unresolvable_refs_are_left_to_fail(self):
        """Nothing is invented: a dangling ref still fails validation later."""
        payload = _payload(thesis={"text": "A verdict.", "based_on": ["SRC_99"]})

        repaired, repairs = repair_references(payload)

        assert repaired["thesis"]["based_on"] == ["SRC_99"]
        assert repairs == []

    def test_clean_payload_is_unchanged(self):
        """A correct graph produces no repairs at all."""
        repaired, repairs = repair_references(_payload())

        assert repaired["thesis"]["based_on"] == ["CLM_1"]
        assert repairs == []


class TestOtherReferenceSites:
    """The same error class appears wherever a claim ID is expected."""

    def test_story_good_claim_ids(self):
        """Story goods point at claims, not sources."""
        payload = _payload(
            story_goods=[{"id": "STG_1", "claim_ids": ["SRC_5"]}]
        )

        repaired, repairs = repair_references(payload)

        assert repaired["story_goods"][0]["claim_ids"] == ["CLM_2"]
        assert any("STG_1.claim_ids" in r for r in repairs)

    def test_hole_attachment(self):
        """A hole attaches to one claim, so the first citing claim wins."""
        payload = _payload(holes=[{"id": "HOLE_1", "attached_to": "SRC_2"}])

        repaired, repairs = repair_references(payload)

        assert repaired["holes"][0]["attached_to"] == "CLM_1"
        assert any("HOLE_1.attached_to" in r for r in repairs)

    def test_hole_attached_to_thesis_is_untouched(self):
        """"thesis" is a legitimate attachment, not a bad reference."""
        payload = _payload(holes=[{"id": "HOLE_1", "attached_to": "thesis"}])

        repaired, _ = repair_references(payload)

        assert repaired["holes"][0]["attached_to"] == "thesis"

    def test_grounds(self):
        """Weakest and strongest ground both name a claim."""
        payload = _payload(
            weakest_ground={"claim_id": "SRC_5", "why": "thin"},
            strongest_ground={"claim_id": "CLM_1", "why": "solid"},
        )

        repaired, _ = repair_references(payload)

        assert repaired["weakest_ground"]["claim_id"] == "CLM_2"
        assert repaired["strongest_ground"]["claim_id"] == "CLM_1"

    def test_market_context(self):
        """The optional market layer cites claims too."""
        payload = _payload(
            market_context={"who_else_serves_this": "x", "based_on": ["SRC_9"]}
        )

        repaired, _ = repair_references(payload)

        assert repaired["market_context"]["based_on"] == ["CLM_3"]


class TestMalformedInput:
    """Repair never raises on shapes it does not understand."""

    def test_non_dict_payload(self):
        """A list or a string passes through untouched."""
        assert repair_references(["not", "a", "graph"]) == (["not", "a", "graph"], [])

    def test_missing_claims(self):
        """With no claims there is nothing to resolve against."""
        payload = {"thesis": {"based_on": ["SRC_1"]}}

        repaired, repairs = repair_references(payload)

        assert repaired == payload
        assert repairs == []
