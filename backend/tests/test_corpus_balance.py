"""Tests for the corpus balance header block (work order I.24).

The block exists to make skew visible, so what these tests pin hardest is that
it *reports* rather than judges: a lopsided corpus produces a note, never a
failure, and a stance call that dies produces an empty tally rather than an
exception that takes the Briefing with it.
"""
from unittest.mock import MagicMock

from backend.pipeline.corpus_balance import (
    build_corpus_balance,
    date_spread,
    domain_of,
    domain_spread,
    network_note,
    shared_bylines,
    stance_counts,
)


def _source(sid, url="", creator=None, published=None, title="A source"):
    """Build a ledger entry with only the fields this block reads."""
    return {
        "source_id": sid,
        "url": url,
        "creator": creator,
        "published": published,
        "title": title,
    }


class TestDomains:
    """Hosts are compared, not URLs."""

    def test_www_and_scheme_do_not_split_a_host(self):
        """Two spellings of one outlet must not read as two outlets."""
        assert domain_of("https://www.bbc.co.uk/news/1") == "bbc.co.uk"
        assert domain_of("http://bbc.co.uk/other") == "bbc.co.uk"

    def test_one_property_spelled_two_ways_is_one_host(self):
        """The Hawara corpus split five YouTube sources into two outlets."""
        assert domain_of("https://youtu.be/2NEef3qaISI") == "youtube.com"
        assert domain_of("https://www.youtube.com/watch?v=x") == "youtube.com"
        assert domain_of("https://m.youtube.com/watch?v=x") == "youtube.com"

    def test_unparseable_urls_are_empty_not_errors(self):
        """A missing or junk URL is common in a ledger and is not a defect."""
        assert domain_of("") == ""
        assert domain_of(None) == ""
        assert domain_of("not a url") == ""

    def test_spread_counts_per_host_and_drops_the_unknowns(self):
        """A source with no URL contributes to no host."""
        spread = domain_spread([
            _source("SRC_1", "https://www.bbc.co.uk/a"),
            _source("SRC_2", "https://bbc.co.uk/b"),
            _source("SRC_3", "https://youtube.com/watch?v=1"),
            _source("SRC_4"),
        ])
        assert spread == {"bbc.co.uk": 2, "youtube.com": 1}


class TestDates:
    """The date window is stated in one phrase, undated sources included."""

    def test_range_and_undated_count(self):
        """A reader needs both the span and how much of the corpus lacks one."""
        assert date_spread([
            _source("SRC_1", published="2019-04-02T00:00:00Z"),
            _source("SRC_2", published="2025-09-03T00:00:00.000Z"),
            _source("SRC_3"),
        ]) == "2019-2025, 1 undated"

    def test_single_year_is_not_rendered_as_a_range(self):
        """"2021-2021" reads as a mistake."""
        assert date_spread([
            _source("SRC_1", published="2021-01-01"),
            _source("SRC_2", published="2021-12-31"),
        ]) == "2021"

    def test_no_dates_at_all_says_so(self):
        """Silence here would read as "recent"; it must read as "unknown"."""
        assert date_spread([_source("SRC_1"), _source("SRC_2")]) == "none dated (2 sources)"

    def test_junk_dates_do_not_become_years(self):
        """A parse artifact must not widen the corpus's apparent span."""
        assert date_spread([
            _source("SRC_1", published="0001-01-01"),
            _source("SRC_2", published="2024-05-05"),
        ]) == "2024, 1 undated"


class TestNetworkOverlap:
    """The 'one crew' catch, mechanized."""

    def test_one_host_carrying_half_the_corpus_is_named(self):
        """Sixteen sources that are really one outlet must not read as sixteen."""
        sources = [_source(f"SRC_{i}", "https://onesite.com/a") for i in range(3)]
        sources.append(_source("SRC_9", "https://elsewhere.org/b"))
        note = network_note(sources)
        assert "3 of 4" in note and "onesite.com" in note

    def test_shared_bylines_are_named_with_counts(self):
        """One author writing several sources is a concentration, not a coincidence."""
        note = network_note([
            _source("SRC_1", "https://a.com/1", creator="Ashley Cowie"),
            _source("SRC_2", "https://b.com/2", creator="Ashley Cowie"),
            _source("SRC_3", "https://c.com/3", creator="Someone Else"),
        ])
        assert "Ashley Cowie (2)" in note
        assert "Someone Else" not in note

    def test_the_string_none_is_not_a_byline(self):
        """Ledger entries store an absent creator as the text "None"."""
        assert shared_bylines([
            _source("SRC_1", creator="None"),
            _source("SRC_2", creator="none"),
            _source("SRC_3", creator=""),
        ]) == {}

    def test_republished_copies_are_counted_from_the_duplicate_groups(self):
        """Syndication already detected upstream belongs in this note."""
        note = network_note(
            [_source(f"SRC_{i}", f"https://site{i}.com/x") for i in range(4)],
            duplicate_groups=[["SRC_0", "SRC_1", "SRC_2"]],
        )
        assert "2 republished copies" in note

    def test_a_spread_corpus_produces_no_note(self):
        """Saying nothing is the correct output for a balanced corpus."""
        assert network_note([
            _source("SRC_1", "https://a.com/1", creator="One Writer"),
            _source("SRC_2", "https://b.com/2", creator="Two Writer"),
            _source("SRC_3", "https://c.com/3", creator="Three Writer"),
        ]) is None

    def test_an_empty_corpus_is_not_an_error(self):
        assert network_note([]) is None


class TestStances:
    """The one LLM judgement in the block, and its failure behaviour."""

    def test_counts_are_tallied_in_vocabulary_order(self):
        counts = stance_counts([
            {"stance": "believer"},
            {"stance": "skeptic"},
            {"stance": "believer"},
        ])
        assert counts == {"believer": 2, "skeptic": 1}
        assert list(counts) == ["believer", "skeptic"]

    def test_labels_outside_the_vocabulary_are_dropped(self):
        """A model that invents a label must not invent a category."""
        assert stance_counts([{"stance": "enthusiast"}, {"stance": "neutral"}]) == {
            "neutral": 1
        }

    def test_a_failed_stance_call_leaves_the_block_standing(self):
        """This is advisory: it degrades, it never takes the Briefing down."""
        client = MagicMock()
        client.generate_structured.side_effect = RuntimeError("provider down")
        balance = build_corpus_balance(
            [_source("SRC_1", "https://a.com/1", published="2024-01-01")],
            client=client,
            topic="A topic",
        )
        assert balance is not None
        assert balance.stance_counts == {}
        assert balance.domains == {"a.com": 1}

    def test_stances_for_unknown_source_ids_are_discarded(self):
        """A hallucinated source_id must not become a corpus statistic."""
        client = MagicMock()
        client.generate_structured.return_value = (
            {"stances": [
                {"source_id": "SRC_1", "stance": "skeptic"},
                {"source_id": "SRC_99", "stance": "believer"},
            ]},
            {},
        )
        balance = build_corpus_balance([_source("SRC_1")], client=client)
        assert balance.stance_counts == {"skeptic": 1}


class TestAssembly:
    """What the header block is, end to end."""

    def test_no_sources_means_no_block(self):
        assert build_corpus_balance([], client=MagicMock()) is None

    def test_without_a_client_the_code_half_still_reports(self):
        """The spreads are counting problems and never need a model."""
        balance = build_corpus_balance([
            _source("SRC_1", "https://a.com/1", published="2020-01-01"),
            _source("SRC_2", "https://a.com/2", published="2024-01-01"),
        ])
        assert balance.domains == {"a.com": 2}
        assert balance.date_range == "2020-2024"
        assert "2 of 2" in balance.network_note
        assert balance.stance_counts == {}
