"""Tests for the Briefing's canonical JSON model.

Cover for P3 work-order item 12. The Briefing (D-025) is the reading surface;
this model is the artifact everything else derives from, so its invariants are
the document's guarantees: Section 1 exists, every citation resolves, chips
come from the locked vocabulary, and the pass schemas stay inside the measured
structured-outputs grammar ceiling.
"""
import pytest

from backend.models.briefing import (
    BLURBS_SCHEMA,
    CONTRIBUTIONS_SCHEMA,
    DISPUTE_SCHEMA,
    FILE_SCHEMA,
    PLAYERS_SCHEMA,
    READ_SCHEMA,
    SUBJECT_MAP_SCHEMA,
    Anecdote,
    Briefing,
    BriefingMeta,
    Chip,
    Dispute,
    DisputeSide,
    File,
    Player,
    Read,
    ReadParagraph,
    RecordEntry,
    SourceTrailEntry,
    chip,
)


def _briefing(**overrides) -> dict:
    """A minimal valid Briefing payload."""
    payload = {
        "job_id": "job-1",
        "topic": "The lost labyrinth",
        "meta": BriefingMeta(
            source_count=2, independent_source_count=2, raw_words=4000
        ),
        "read": Read(
            lede="Read all two.",
            paragraphs=[ReadParagraph(label="What you've got", text="Two sources.")],
        ),
        "source_trail": [
            SourceTrailEntry(source_id="SRC_1", title="A video"),
            SourceTrailEntry(source_id="SRC_2", title="An article"),
        ],
    }
    payload.update(overrides)
    return payload


class TestChips:
    """Chip labels are locked; tone follows the label, never a caller."""

    def test_vocabulary_labels_resolve_their_tone(self):
        """Each locked label carries the colour the mockup gives it."""
        assert chip("established").tone == "solid"
        assert chip("contested").tone == "contested"
        assert chip("single source").tone == "network"
        assert chip("belief migration").tone == "network"

    def test_unknown_label_is_rejected(self):
        """A model cannot invent a status by inventing a chip."""
        with pytest.raises(ValueError, match="outside the D-025 vocabulary"):
            Chip(label="probably true")

    def test_tone_cannot_be_overridden(self):
        """Passing the wrong tone does not change what the reader sees."""
        assert Chip(label="single source", tone="solid").tone == "network"


class TestBriefingInvariants:
    """The document's guarantees, enforced at the model."""

    def test_minimal_briefing_validates(self):
        """The smallest honest document is valid."""
        briefing = Briefing(**_briefing())

        assert briefing.briefing_version == "1"
        assert briefing.read.lede.startswith("Read all")

    def test_empty_read_is_rejected(self):
        """A Briefing without Section 1 is a failed build, not a thin one."""
        with pytest.raises(ValueError, match="no Section 1"):
            Briefing(**_briefing(read=Read(lede="", paragraphs=[])))

    def test_unknown_citation_is_rejected(self):
        """Every cited source must exist in the trail."""
        with pytest.raises(ValueError, match="not in the trail"):
            Briefing(
                **_briefing(
                    players=[
                        Player(
                            name="Louis De Cordier",
                            role="expedition lead",
                            body="Funded the scans.",
                            source_ids=["SRC_9"],
                        )
                    ]
                )
            )

    def test_citations_across_every_section_are_checked(self):
        """Files, record entries, disputes, and anecdotes all resolve."""
        briefing = Briefing(
            **_briefing(
                files=[File(title="The Water", body="A canal.", source_ids=["SRC_1"])],
                record=[RecordEntry(when="1888", what="Petrie digs.", source_ids=["SRC_2"])],
                anecdotes=[Anecdote(text="A match saved him.", source_ids=["SRC_1"])],
                disputes=[
                    Dispute(
                        claim="The labyrinth survives.",
                        holders="For: the scan network. Against: Petrie.",
                        chip=chip("contested"),
                        case_for=DisputeSide(
                            heading="The case for", text="Three authors.", source_ids=["SRC_1"]
                        ),
                        case_against=DisputeSide(
                            heading="The case against", text="Chip stratum.", source_ids=["SRC_2"]
                        ),
                    )
                ],
            )
        )

        assert briefing.disputes[0].chip.tone == "contested"
        assert briefing.files[0].source_ids == ["SRC_1"]

    def test_duplicate_pointer_must_resolve(self):
        """A republication names a source that is actually in the trail."""
        with pytest.raises(ValueError, match="not in the trail"):
            Briefing(
                **_briefing(
                    source_trail=[
                        SourceTrailEntry(
                            source_id="SRC_1", title="A video", duplicate_of="SRC_7"
                        )
                    ]
                )
            )

    def test_unknown_fields_are_rejected(self):
        """Drift surfaces as a failure rather than a silently ignored key."""
        with pytest.raises(ValueError):
            Briefing(**_briefing(section_9={"text": "surprise"}))


class TestPassSchemas:
    """What reaches the API stays inside the measured grammar ceiling."""

    ALL = [
        READ_SCHEMA,
        SUBJECT_MAP_SCHEMA,
        FILE_SCHEMA,
        DISPUTE_SCHEMA,
        BLURBS_SCHEMA,
        PLAYERS_SCHEMA,
        CONTRIBUTIONS_SCHEMA,
    ]

    def _walk(self, node):
        if isinstance(node, dict):
            yield node
            for value in node.values():
                yield from self._walk(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._walk(value)

    def test_no_nullable_branches(self):
        """Zero nullable branches: the measured ceiling, not a style choice."""
        for schema in self.ALL:
            for node in self._walk(schema):
                assert "anyOf" not in node
                assert node.get("type") != "null"

    def test_objects_are_closed_and_fully_required(self):
        """Optional properties multiply the compiled grammar; none are allowed."""
        for schema in self.ALL:
            for node in self._walk(schema):
                if node.get("type") == "object":
                    assert node["additionalProperties"] is False
                    assert sorted(node["required"]) == sorted(node["properties"])

    def test_each_pass_asks_for_content_fields_only(self):
        """No pass is handed the document's structure to assemble."""
        assert set(READ_SCHEMA["properties"]) == {"lede", "paragraphs"}
        assert set(FILE_SCHEMA["properties"]) == {"title", "body"}
        assert set(DISPUTE_SCHEMA["properties"]) == {
            "for_heading",
            "for_text",
            "against_heading",
            "against_text",
        }
