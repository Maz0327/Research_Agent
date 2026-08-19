"""Tests for the Briefing generation passes and their orchestration.

Cover for P3 work-order item 14 and the approved pass layout (Section J). The
tests hold the division of labour to account: the model fills content fields,
and code decides what goes where, what qualifies, what a chip says, and what
gets checked. A scripted client stands in for the API so the structure is
what is under test, not a model's wording.
"""
from unittest.mock import MagicMock

from backend.models.briefing import File
from backend.pipeline.briefing_passes import (
    build_anecdotes,
    build_record_entries,
    repair_file_coverage,
    run_blurb_pass,
    run_contribution_pass,
    run_dispute_pass,
    run_file_pass,
    run_players_pass,
    run_read_pass,
    run_subject_map_pass,
)
from backend.pipeline.briefing_routing import (
    date_in,
    evidence_chip,
    paragraphs_for_fact,
    qualifying_players,
    route_facts,
    select_disputes,
)


def _client(payload, cost=0.01):
    """A structured-output client that always returns one payload."""
    client = MagicMock()
    client.generate_structured.return_value = (payload, {"cost": cost})
    return client


def _fact(fact_id, source_id, text):
    return {"fact_id": fact_id, "source_id": source_id, "text": text}


class TestReadPass:
    """Section 1 is written from raw text, and only from raw text."""

    def test_read_is_built_from_raw_sources(self):
        """The prompt carries the manifest and the source bodies."""
        client = _client(
            {
                "lede": "Read all two.",
                "paragraphs": [
                    {"label": "What you've got", "text": "Two videos and an article."},
                    {"label": "", "text": "The story, assembled."},
                ],
            }
        )
        sources = [
            {
                "source_id": "SRC_1",
                "title": "A video",
                "source_type": "youtube",
                "creator": "Johanna",
                "full_text": "The scans found a grid at eight metres.",
            },
            {"source_id": "SRC_2", "title": "An article", "full_text": "Petrie disagreed."},
        ]

        read = run_read_pass(client, "the labyrinth", sources)

        prompt = client.generate_structured.call_args.kwargs["prompt"]
        assert "SRC_1 · A video" in prompt
        assert "The scans found a grid at eight metres." in prompt
        assert "EXAMPLE ONE" in prompt and "EXAMPLE TWO" in prompt
        assert read.lede == "Read all two."
        assert read.paragraphs[1].label is None

    def test_sources_without_text_still_appear_in_the_manifest(self):
        """A failed fetch is part of what the pile is."""
        client = _client({"lede": "One source.", "paragraphs": [{"label": "", "text": "x"}]})

        run_read_pass(
            client,
            "topic",
            [{"source_id": "SRC_8", "title": "Herodotus", "full_text": ""}],
        )

        prompt = client.generate_structured.call_args.kwargs["prompt"]
        assert "[no text captured]" in prompt


class TestSubjectMapPass:
    """Grouping is the one semantic job code cannot do; no-orphan is code's."""

    def test_facts_are_grouped_and_anecdotes_split_out(self):
        """The model's grouping is respected when it uses real IDs."""
        client = _client(
            {
                "subjects": [
                    {"title": "The 2008 scans", "fact_ids": ["SRC_1:F_1", "SRC_1:F_2"]},
                ],
                "anecdote_fact_ids": ["SRC_2:F_1"],
            }
        )
        facts = [
            _fact("SRC_1:F_1", "SRC_1", "The scans found a grid."),
            _fact("SRC_1:F_2", "SRC_1", "The grid sits at 8 metres."),
            _fact("SRC_2:F_1", "SRC_2", "Petrie got stuck in a tunnel."),
        ]

        subjects, anecdotes = run_subject_map_pass(client, facts)

        assert subjects == [
            {"title": "The 2008 scans", "fact_ids": ["SRC_1:F_1", "SRC_1:F_2"]}
        ]
        assert anecdotes == ["SRC_2:F_1"]

    def test_unassigned_facts_are_never_dropped(self):
        """A fact the model forgot lands in a catch-all, not the bin."""
        client = _client({"subjects": [], "anecdote_fact_ids": []})
        facts = [_fact("SRC_1:F_1", "SRC_1", "A fact nobody grouped.")]

        subjects, anecdotes = run_subject_map_pass(client, facts)

        assert subjects == [{"title": "Everything else", "fact_ids": ["SRC_1:F_1"]}]
        assert anecdotes == []

    def test_invented_ids_are_discarded(self):
        """A model cannot add a fact by naming an ID that does not exist."""
        client = _client(
            {
                "subjects": [{"title": "Invented", "fact_ids": ["SRC_9:F_9"]}],
                "anecdote_fact_ids": [],
            }
        )
        facts = [_fact("SRC_1:F_1", "SRC_1", "A real fact.")]

        subjects, _ = run_subject_map_pass(client, facts)

        assert subjects == [{"title": "Everything else", "fact_ids": ["SRC_1:F_1"]}]

    def test_too_many_subjects_are_folded_together(self):
        """A map with twenty regions is not a map; the cap is code's call."""
        from backend.pipeline.briefing_passes import cap_subjects

        subjects = [
            {"title": f"Subject {i}", "fact_ids": [f"SRC_1:F_{i}_{j}" for j in range(10 - i)]}
            for i in range(11)
        ]
        before = sum(len(s["fact_ids"]) for s in subjects)

        capped = cap_subjects(subjects)

        assert len(capped) == 8
        assert sum(len(s["fact_ids"]) for s in capped) == before
        assert sum(len(s["fact_ids"]) for s in subjects) == before  # input untouched

    def test_a_small_map_is_left_alone(self):
        """Under the ceiling, nothing is merged."""
        from backend.pipeline.briefing_passes import cap_subjects

        subjects = [{"title": "One", "fact_ids": ["a"]}, {"title": "Two", "fact_ids": ["b"]}]

        assert cap_subjects(subjects) == subjects

    def test_no_facts_no_call(self):
        """Nothing to group means nothing is spent."""
        client = _client({"subjects": [], "anecdote_fact_ids": []})

        assert run_subject_map_pass(client, []) == ([], [])
        assert client.generate_structured.call_count == 0


class TestFilePass:
    """Files carry their assigned facts, and misses are repaired by appending."""

    def test_file_records_its_facts_and_sources(self):
        """Assignment is code's, so the file remembers what it owes."""
        client = _client({"title": "The 2008 scans", "body": "The scans found a grid."})
        facts = [
            _fact("SRC_1:F_1", "SRC_1", "The scans found a grid."),
            _fact("SRC_2:F_1", "SRC_2", "The grid sits at 8 metres."),
        ]

        file = run_file_pass(client, "The 2008 scans", facts, {"SRC_1": "raw text"})

        assert file.fact_ids == ["SRC_1:F_1", "SRC_2:F_1"]
        assert file.source_ids == ["SRC_1", "SRC_2"]

    def test_repair_appends_rather_than_rewrites(self):
        """Re-emitting a document to edit it drops content; appending does not."""
        client = _client({"title": "x", "body": "The grid sits at 8 metres."})
        file = File(title="The 2008 scans", body="The scans found a grid.", source_ids=["SRC_1"])

        repaired = repair_file_coverage(
            client, file, [_fact("SRC_2:F_1", "SRC_2", "The grid sits at 8 metres.")], {}
        )

        assert repaired.body.startswith("The scans found a grid.")
        assert "8 metres" in repaired.body

    def test_repair_with_nothing_missing_costs_nothing(self):
        """No misses, no call."""
        client = _client({"title": "x", "body": "y"})
        file = File(title="A file", body="Body.", source_ids=[])

        repair_file_coverage(client, file, [], {})

        assert client.generate_structured.call_count == 0


class TestDisputeAndBlurbPasses:
    """Code selects and places; the model only writes."""

    def test_dispute_sides_keep_their_assigned_sources(self):
        """Citations are code's, not the model's to reassign."""
        client = _client(
            {
                "for_heading": "The case for",
                "for_text": "Three authors describe a stone roof.",
                "against_heading": "The case against",
                "against_text": "Petrie found demolition debris.",
            }
        )

        case_for, case_against = run_dispute_pass(
            client,
            claim="The labyrinth survives.",
            holders="For: the scan network. Against: Petrie.",
            evidence_for=["Three authors describe a stone roof."],
            evidence_against=["Petrie found a chip stratum."],
            source_ids_for=["SRC_1"],
            source_ids_against=["SRC_2"],
        )

        assert case_for.source_ids == ["SRC_1"]
        assert case_against.source_ids == ["SRC_2"]

    def test_blurbs_are_addressed_by_index(self):
        """A model cannot move or invent an entry it can only number."""
        client = _client(
            {
                "blurbs": [
                    {"index": 0, "context": "Context for the first."},
                    {"index": 7, "context": "An entry that does not exist."},
                ]
            }
        )

        blurbs = run_blurb_pass(client, ["First entry.", "Second entry."])

        assert blurbs == {0: "Context for the first."}


class TestPlayersAndContributions:
    """Cards and trail lines are written only for what code asked about."""

    def test_only_requested_names_get_cards(self):
        """A model cannot add a player by writing one."""
        client = _client(
            {
                "players": [
                    {"name": "Flinders Petrie", "role": "excavator", "body": "Dug in 1888."},
                    {"name": "Someone Else", "role": "invented", "body": "Not asked for."},
                ]
            }
        )

        players = run_players_pass(
            client, ["Flinders Petrie"], {"Flinders Petrie": ["Dug at Hawara in 1888."]}
        )

        assert [p.name for p in players] == ["Flinders Petrie"]

    def test_contributions_are_keyed_to_real_sources(self):
        """Lines for sources that do not exist are dropped."""
        client = _client(
            {
                "contributions": [
                    {"source_id": "SRC_1", "contribution": "the only interview."},
                    {"source_id": "SRC_9", "contribution": "a source nobody has."},
                ]
            }
        )

        lines = run_contribution_pass(
            client, [{"source_id": "SRC_1", "title": "A video"}], {"SRC_1": ["A fact."]}
        )

        assert lines == {"SRC_1": "the only interview."}


class TestCodeHalves:
    """The parts no model touches at all."""

    def test_record_is_placed_and_sorted_by_code(self):
        """Dates are read, sorted, and placed mechanically."""
        routed = route_facts(
            [
                _fact("SRC_1:F_1", "SRC_1", "Petrie excavated Hawara in 1888."),
                _fact("SRC_1:F_2", "SRC_1", "Herodotus visited in c. 450 BC."),
                _fact("SRC_1:F_3", "SRC_1", "The water table is saline."),
            ]
        )

        entries = build_record_entries(routed["record"], {0: "Context."})

        assert [e.when for e in entries] == ["c. 450 BC", "1888"]
        assert entries[0].context == "Context."
        assert len(routed["remaining"]) == 1

    def test_anecdotes_carry_their_source(self):
        """Texture keeps its citation."""
        anecdotes = build_anecdotes([_fact("SRC_3:F_1", "SRC_3", "A match saved him.")])

        assert anecdotes[0].source_ids == ["SRC_3"]

    def test_players_threshold_is_two_sections(self):
        """The D-025 rule, applied by counting rather than by asking."""
        names = qualifying_players(
            {
                "read": "Flinders Petrie dug at Hawara. Eric Uphill wrote later.",
                "files": "Flinders Petrie found the stone bed.",
            }
        )

        assert "Flinders Petrie" in names
        assert "Eric Uphill" not in names

    def test_chips_are_provenance_arithmetic(self):
        """Syndication collapses before anything is counted."""
        assert evidence_chip(["SRC_1", "SRC_2"]).label == "established"
        assert evidence_chip(["SRC_1"]).label == "single source"
        assert (
            evidence_chip(["SRC_7", "SRC_8"], duplicate_of={"SRC_8": "SRC_7"}).label
            == "single source"
        )
        assert evidence_chip(["SRC_1", "SRC_2"], contested=True).label == "contested"
        assert evidence_chip(["SRC_1"], verifiable=False).label == "unverifiable"

    def test_paragraph_pull_narrows_the_input(self):
        """A writing pass sees the paragraphs its facts came from, not the corpus."""
        raw = (
            "An opening paragraph about something else entirely.\n\n"
            "The Mataha expedition scanned the site in 2008 and reported a grid "
            "at eight to twelve metres depth.\n\n"
            "A closing paragraph about the weather."
        )

        pulled = paragraphs_for_fact("The grid sits at 8 to 12 metres depth.", raw, window=1)

        assert len(pulled) == 1
        assert "Mataha" in pulled[0]

    def test_disputes_are_selected_by_code(self):
        """Restated tensions do not stage the same fight twice."""

        class _Tension:
            def __init__(self, description):
                self.description = description
                self.source_ids = ["SRC_1"]

        disputes = select_disputes(
            tensions=[
                _Tension("Sources disagree about whether the roof survives"),
                _Tension("Whether the roof survives is disputed among the sources"),
                _Tension("The dating of the canal is disputed"),
            ],
            inventory=[_fact("SRC_1:F_1", "SRC_1", "The roof survives under the sand.")],
        )

        assert len(disputes) == 2

    def test_date_reading_handles_how_sources_write_dates(self):
        """Years, months, ranges, centuries, and BC all sort correctly."""
        assert date_in("Petrie excavated in 1888")[0] == 1888
        assert date_in("On May 7 2026 the ministry confirmed")[1] == "May 7 2026"
        assert date_in("Herodotus wrote c. 450 BC")[0] == -450
        assert date_in("the 5th century BC")[0] == -450
        assert date_in("no dates here") is None
