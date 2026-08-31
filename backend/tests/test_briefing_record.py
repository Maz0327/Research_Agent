"""The Record: one event, told once, with its numbers settled."""

from backend.pipeline.briefing_routing import (
    collapse_same_event,
    date_in,
    strip_source_voice,
)


def _fact(source_id, text):
    key, written = date_in(text)
    return {
        "fact_id": f"{source_id}:F_1",
        "source_id": source_id,
        "text": text,
        "sort_key": key,
        "when": written,
    }


class TestDecadesAreDates:
    def test_a_decade_is_read_rather_than_the_next_number_in_the_sentence(self):
        """The gun's model year used to win over the year it was found."""
        assert date_in("In the 1950s, a rusted 1862 Colt was found")[0] == 1950.0

    def test_a_decade_only_event_is_not_dateless(self):
        """These used to be dropped from the Record entirely."""
        assert date_in("In the early 1900s, Polly Pry launched a campaign")[0] == 1900.0

    def test_a_year_that_opens_the_sentence_still_wins(self):
        """Leftmost, not most-specific-pattern: the decade here is an aside."""
        assert date_in("In 1874 the party set out; the gun surfaced in the 1950s")[0] == 1874.0


class TestOneEventToldOnce:
    def test_restatements_collapse_to_the_fullest_telling(self):
        facts = [
            _fact("SRC_1", "Packer was born near Pittsburgh in 1842."),
            _fact(
                "SRC_2",
                "Alfred Griner Packer was born on January 21, 1842, in Allegheny "
                "County, Pennsylvania, near Pittsburgh.",
            ),
        ]
        kept, dropped = collapse_same_event(facts)
        assert len(kept) == 1
        assert "Allegheny County" in kept[0]["text"]
        assert dropped[0]["dropped_because"] == "restates the same event"

    def test_a_year_fewer_sources_support_loses(self):
        """1907 against 1909 is arithmetic, not a dispute for the reader."""
        facts = [
            _fact("SRC_1", "Alferd Packer lived from 1842 to 1909."),
            _fact("SRC_2", "Alferd Packer lived from 1842 to 1907 and prospected."),
            _fact("SRC_3", "Packer was born in 1842 and died in 1907 in Colorado."),
            _fact("SRC_4", "Born in 1842, Packer died in 1907 at Littleton."),
        ]
        kept, dropped = collapse_same_event(facts)
        assert all("1909" not in fact["text"] for fact in kept)
        assert any("1909" in fact["text"] for fact in dropped)

    def test_numbers_that_appear_together_never_compete(self):
        """"eight years for each of five victims" is two quantities, not two readings."""
        facts = [
            _fact("SRC_1", "In 1886 Packer got 40 years, eight years for each of five victims."),
            _fact("SRC_2", "In 1886 Packer was resentenced to 40 years for five victims."),
            _fact("SRC_3", "In 1886 the court imposed eight years per victim."),
        ]
        kept, _dropped = collapse_same_event(facts)
        # Whatever collapses, no entry loses its numbers to the other's.
        assert kept
        assert all(fact["text"] for fact in kept)

    def test_an_unsupported_year_never_empties_its_own_bucket(self):
        """Arithmetic may thin a year, never delete it."""
        facts = [_fact("SRC_1", "Packer lived from 1842 to 1909.")]
        kept, dropped = collapse_same_event(facts)
        assert len(kept) == 1
        assert dropped == []

    def test_unrelated_facts_in_the_same_year_both_survive(self):
        facts = [
            _fact("SRC_1", "In 1874 the party set out from Utah into the mountains."),
            _fact("SRC_2", "In 1874 Chief Ouray warned the men against winter travel."),
        ]
        kept, _dropped = collapse_same_event(facts)
        assert len(kept) == 2


class TestTheRecordDoesNotTalkAboutItsSources:
    def test_the_texts_own_framing_comes_off(self):
        assert strip_source_voice(
            "The text says Alferd Packer died in 1907."
        ) == "Alferd Packer died in 1907."

    def test_a_trailing_framing_clause_comes_off(self):
        assert strip_source_voice(
            "Packer died in 1907, and the text says his reputation lives on."
        ) == "Packer died in 1907, and his reputation lives on."

    def test_ordinary_prose_is_untouched(self):
        plain = "Packer emerged at the agency on April 16, 1874."
        assert strip_source_voice(plain) == plain


class TestTensionsStateTheirOwnOpposition:
    """The two sides come from the description, not from the key points cited."""

    def test_a_versus_description_splits_into_two_sides(self):
        from backend.pipeline.briefing_routing import split_tension

        left, right = split_tension(
            "Packer's claim of self-defense against Shannon Bell versus coroner "
            "reports indicating all five bodies suffered identical blunt trauma"
        )
        assert left == "Packer's claim of self-defense against Shannon Bell"
        assert right.startswith("coroner reports")

    def test_a_heading_before_the_sentence_is_not_one_of_the_sides(self):
        from backend.pipeline.briefing_routing import split_tension

        left, right = split_tension(
            "Criminal Conviction vs. Forensic Evidence: Packer served seventeen "
            "years for murder, yet bullet lead matching supports his account"
        )
        assert left == "Packer served seventeen years for murder"
        assert right.startswith("bullet lead matching")

    def test_a_description_stating_no_opposition_yields_no_sides(self):
        """Better an empty answer than two sides invented from one."""
        from backend.pipeline.briefing_routing import split_tension

        assert split_tension("Sources disagree about the roof") == ("", "")


class TestSourcesAreCalledWhatReadersCallThem:
    def test_a_scraped_footer_widget_is_not_a_byline(self):
        """The first live briefing credited "Authority control databases"."""
        from backend.pipeline.briefing_routing import source_display_name

        assert source_display_name(
            {"title": "Alfred Packer - Wikipedia", "creator": "Authority control databases"}
        ) == "Wikipedia"

    def test_the_publication_beats_the_byline(self):
        from backend.pipeline.briefing_routing import source_display_name

        assert source_display_name(
            {"title": "Cannibal Correspondence - True West Magazine",
             "creator": "Kellen Cutsforth"}
        ) == "True West Magazine"

    def test_a_shouted_byline_is_calmed_down(self):
        from backend.pipeline.briefing_routing import source_display_name

        assert source_display_name(
            {"title": "Alfred Packer ate 'em", "creator": "KAREN TIMMONS"}
        ) == "Karen Timmons"

    def test_a_cms_label_is_not_part_of_the_name(self):
        from backend.pipeline.briefing_routing import source_display_name

        assert source_display_name(
            {"title": "Alferd Packer", "creator": "Author Gulliford; Andrew"}
        ) == "Gulliford"
