"""Tests for the Players/Places split and the Places section.

Cover for the Packer failure: the 2+-section ranking cannot tell a place from
a player, so five of fourteen "players" on that job were places - "Los Piños
Indian Agency", "Gunnison River", "Lake Fork", "Jefferson County", and the
truncated duplicate "Los Pi" - each handed a biography. The fix is a
three-kind classification before any card is written, a Places section of its
own, and alias folding that catches truncated variants.
"""
from unittest.mock import MagicMock, patch

from backend.models.briefing import Briefing
from backend.pipeline.briefing_passes import (
    classify_name_kinds,
    classify_people,
    run_places_pass,
)
from backend.pipeline.briefing_routing import (
    MAX_PLACE_CARDS,
    merge_aliases,
    split_cast,
)
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.briefing_stage import build_briefing


def _client(payload, cost=0.01):
    """A structured-output client that always returns one payload."""
    client = MagicMock()
    client.generate_structured.return_value = (payload, {"cost": cost})
    return client


class TestNameKindClassification:
    """One classifier, three kinds, and a safe direction on every failure."""

    def test_names_are_sorted_into_three_kinds(self):
        client = _client(
            {
                "names": [
                    {"name": "Polly Pry", "kind": "person"},
                    {"name": "Denver Post", "kind": "organisation"},
                    {"name": "Gunnison River", "kind": "place"},
                ]
            }
        )
        kinds = classify_name_kinds(
            ["Polly Pry", "Denver Post", "Gunnison River"], client
        )
        assert kinds == {
            "Polly Pry": "person",
            "Denver Post": "organisation",
            "Gunnison River": "place",
        }

    def test_answers_outside_the_vocabulary_read_as_no_answer(self):
        """An invented kind or an invented name must not move anyone."""
        client = _client(
            {
                "names": [
                    {"name": "Polly Pry", "kind": "reporter"},
                    {"name": "Alferd Packer", "kind": "place"},
                ]
            }
        )
        kinds = classify_name_kinds(["Polly Pry"], client)
        assert kinds == {}

    def test_model_failure_returns_none_so_callers_keep_every_name(self):
        client = MagicMock()
        client.generate_structured.side_effect = RuntimeError("api down")
        assert classify_name_kinds(["Polly Pry"], client) is None

    def test_no_names_no_call(self):
        client = MagicMock()
        assert classify_name_kinds([], client) == {}
        client.generate_structured.assert_not_called()

    def test_classify_people_is_the_person_bucket(self):
        client = _client(
            {
                "names": [
                    {"name": "Polly Pry", "kind": "person"},
                    {"name": "Denver Post", "kind": "organisation"},
                    {"name": "Lake Fork", "kind": "place"},
                ]
            }
        )
        people = classify_people(["Polly Pry", "Denver Post", "Lake Fork"], client)
        assert people == {"Polly Pry"}

    def test_classify_people_keeps_every_name_on_failure(self):
        """The pre-split failure behaviour, preserved through the rewrite."""
        client = MagicMock()
        client.generate_structured.side_effect = RuntimeError("api down")
        assert classify_people(["Polly Pry", "Lake Fork"], client) == {
            "Polly Pry",
            "Lake Fork",
        }


class TestSplitCast:
    """Players keeps people AND organisations; Places gets geography only."""

    def test_places_are_split_out_of_the_players(self):
        names = ["Polly Pry", "Gunnison River", "Denver Post", "Lake Fork"]
        kinds = {
            "Polly Pry": "person",
            "Gunnison River": "place",
            "Denver Post": "organisation",
            "Lake Fork": "place",
        }
        players, places = split_cast(names, kinds)
        assert players == ["Polly Pry", "Denver Post"]
        assert places == ["Gunnison River", "Lake Fork"]

    def test_an_unanswered_name_stays_a_player(self):
        """Absence from the classification must never drop a card."""
        players, places = split_cast(["Polly Pry", "Chief Ouray"], {"Polly Pry": "person"})
        assert players == ["Polly Pry", "Chief Ouray"]
        assert places == []

    def test_classification_failure_keeps_the_old_behaviour(self):
        players, places = split_cast(["Polly Pry", "Lake Fork"], None)
        assert players == ["Polly Pry", "Lake Fork"]
        assert places == []

    def test_the_places_section_is_capped(self):
        names = [f"Gulch Number{i}" for i in range(MAX_PLACE_CARDS + 4)]
        kinds = dict.fromkeys(names, "place")
        _, places = split_cast(names, kinds)
        assert len(places) == MAX_PLACE_CARDS


class TestTruncatedVariantFolding:
    """"Los Pi" and "Los Piños Indian Agency" are one card, the fullest one."""

    def test_a_mid_word_truncation_folds_into_the_full_form(self):
        merged = merge_aliases(
            {
                "Los Piños Indian Agency": {"read", "files"},
                "Los Pi": {"record"},
            }
        )
        assert list(merged) == ["Los Piños Indian Agency"]
        assert merged["Los Piños Indian Agency"]["sections"] == {
            "read",
            "files",
            "record",
        }
        assert "Los Pi" in merged["Los Piños Indian Agency"]["aliases"]

    def test_the_fullest_form_wins_even_at_equal_token_count(self):
        merged = merge_aliases(
            {"Denver Po": {"read"}, "Denver Post": {"files"}}
        )
        assert list(merged) == ["Denver Post"]

    def test_unrelated_names_do_not_fold(self):
        merged = merge_aliases(
            {"Lake Fork": {"read", "files"}, "Lake City": {"read", "record"}}
        )
        assert sorted(merged) == ["Lake City", "Lake Fork"]


class TestPlacesPass:
    """The model writes the cards; selection of backdrops is its half."""

    def test_only_requested_names_get_cards_and_backdrops_may_be_skipped(self):
        client = _client(
            {
                "places": [
                    {
                        "name": "Los Piños Indian Agency",
                        "line": "remote Ute agency on the Gunnison",
                        "body": "The party's intended destination.",
                    },
                    {
                        "name": "Colorado",
                        "line": "a state",
                        "body": "Invented card for a name never asked about.",
                    },
                ]
            }
        )
        places = run_places_pass(
            client,
            ["Los Piños Indian Agency", "Jefferson County"],
            {"Los Piños Indian Agency": ["The party set out for the agency."]},
        )
        # One card kept for a requested name; the unasked "Colorado" card is
        # discarded, and "Jefferson County" was skipped by the model - allowed.
        assert [p.name for p in places] == ["Los Piños Indian Agency"]
        assert places[0].line == "remote Ute agency on the Gunnison"

    def test_no_names_no_call(self):
        client = MagicMock()
        assert run_places_pass(client, [], {}) == []
        client.generate_structured.assert_not_called()


class TestModelCompatibility:
    """Old stored Briefings predate the section and must still validate."""

    def test_places_defaults_to_an_empty_list(self):
        briefing = Briefing.model_validate(
            {
                "job_id": "job-1",
                "topic": "Alferd Packer",
                "meta": {
                    "source_count": 1,
                    "independent_source_count": 1,
                    "raw_words": 10,
                },
                "read": {"lede": "Read it.", "paragraphs": [{"text": "One."}]},
            }
        )
        assert briefing.places == []

    def test_place_citations_must_resolve_like_any_others(self):
        data = {
            "job_id": "job-1",
            "topic": "Alferd Packer",
            "meta": {"source_count": 1, "independent_source_count": 1, "raw_words": 10},
            "read": {"lede": "Read it.", "paragraphs": [{"text": "One."}]},
            "places": [
                {"name": "Lake Fork", "line": "a river fork", "body": "Bodies found.",
                 "source_ids": ["SRC_9"]}
            ],
            "source_trail": [{"source_id": "SRC_1", "title": "A record"}],
        }
        try:
            Briefing.model_validate(data)
            raise AssertionError("SRC_9 should not have resolved")
        except ValueError as exc:
            assert "SRC_9" in str(exc)


# Both names must pass `acts_somewhere`, so both are followed by action verbs:
# the river "claimed" three men, which is exactly the shape that fooled the
# old two-way path into carding places.
PROSE = (
    "Alferd Packer led the party and the Gunnison River claimed three men in 1874."
)


def _scripted_client():
    """Answers every pass; the split is what is under test, not the wording."""
    client = MagicMock()

    def answer(prompt, schema, system, max_tokens=8000, model=None):
        keys = set(schema.get("properties", {}))
        if keys == {"lede", "paragraphs"}:
            data = {"lede": "Read it.", "paragraphs": [{"label": "", "text": PROSE}]}
        elif keys == {"subjects", "anecdote_fact_ids"}:
            data = {
                "subjects": [{"title": "The journey", "fact_ids": ["SRC_1:F_1"]}],
                "anecdote_fact_ids": [],
            }
        elif keys == {"title", "body"}:
            data = {"title": "The journey", "body": PROSE}
        elif keys == {"blurbs"}:
            data = {"blurbs": []}
        elif keys == {"names"}:
            data = {
                "names": [
                    {"name": "Alferd Packer", "kind": "person"},
                    {"name": "Gunnison River", "kind": "place"},
                ]
            }
        elif keys == {"players"}:
            data = {
                "players": [
                    {"name": "Alferd Packer", "role": "led the party",
                     "body": "Alferd Packer led the party."}
                ]
            }
        elif keys == {"places"}:
            data = {
                "places": [
                    {"name": "Gunnison River", "line": "the river the party followed",
                     "body": "The Gunnison River froze."}
                ]
            }
        elif keys == {"contributions"}:
            data = {"contributions": []}
        elif keys == {"introductions"}:
            data = {"introductions": []}
        else:
            data = {
                "for_heading": "For", "for_text": "x",
                "against_heading": "Against", "against_text": "y",
            }
        return data, {"cost": 0.0}

    client.generate_structured.side_effect = answer
    return client


class TestStageSplit:
    """End to end: a place never reaches the players pass or its section."""

    def _build(self):
        ctx = PipelineContext(job_id="job-1", topic="Alferd Packer")
        ctx.harvest_inventory = [
            {"fact_id": "SRC_1:F_1", "source_id": "SRC_1", "text": PROSE},
        ]
        sources = [
            {"source_id": "SRC_1", "title": "A record", "full_text": PROSE},
            {"source_id": "SRC_2", "title": "A retelling", "full_text": PROSE},
        ]
        with patch("backend.pipeline.stages.briefing_stage.update_job"):
            briefing, _report = build_briefing(ctx, _scripted_client(), sources)
        return briefing

    def test_places_are_excluded_from_the_players_section(self):
        briefing = self._build()
        assert [p.name for p in briefing.players] == ["Alferd Packer"]
        assert [p.name for p in briefing.places] == ["Gunnison River"]

    def test_both_renders_carry_places_after_players(self):
        from backend.pipeline.formatters.briefing_renderer import (
            render_briefing_html,
            render_briefing_markdown,
        )

        briefing = self._build()
        markdown = render_briefing_markdown(briefing)
        assert "## 3. The Places" in markdown
        assert (
            markdown.index("## 2. The Players")
            < markdown.index("## 3. The Places")
            < markdown.index("## 4. The Record")
        )

        html = render_briefing_html(briefing)
        assert html.index("The Players") < html.index("The Places")
        assert "Gunnison River" in html.split("The Places", 1)[1]
