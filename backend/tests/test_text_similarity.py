"""Tests for the deterministic text-similarity primitives.

These decide identity for three pipeline questions: is this the same
syndicated article (shingles), do two sources say the same thing (statement
containment), and is this theme a restatement of that one. Thresholds are
calibrated on the films corpus, so the tests pin the calibration.
"""
from backend.pipeline.text_similarity import (
    content_tokens,
    group_matching,
    numbers_in,
    says_the_same_thing,
    shingle_overlap,
    shingles,
    statement_similarity,
    tokenize,
)

WIRE_STORY = (
    "Jurassic Park changed film making forever by putting computer generated "
    "dinosaurs on screen beside animatronic ones, and the industry never went "
    "back. Steven Spielberg had planned to shoot the dinosaurs in stop motion "
    "until Industrial Light and Magic showed him a test that changed his mind."
)

SYNDICATED_COPY = (
    "Jurassic Park changed film making forever by putting computer generated "
    "dinosaurs on screen beside animatronic ones, and the industry never went "
    "back. The film went on to earn a billion dollars worldwide."
)

UNRELATED = (
    "The Hawara labyrinth has been described by ancient writers for two "
    "thousand years, and every surviving account disagrees with the next about "
    "what was actually buried under the sand at the site."
)


class TestTokenizing:
    """Tokenizing drops punctuation and stopwords, keeps numbers."""

    def test_tokenize(self):
        """Punctuation is stripped, case folded."""
        assert tokenize("The Film, in 1993!") == ["the", "film", "in", "1993"]

    def test_content_tokens_drop_stopwords(self):
        """Stopwords and single characters are removed."""
        assert content_tokens("The film in 1993") == {"film", "1993"}

    def test_numbers_are_normalized(self):
        """Commas and trailing dots are stripped so figures compare."""
        assert numbers_in("1,200 chambers and 12 rooms.") == {"1200", "12"}


class TestShingles:
    """Shingles catch verbatim reuse, the syndication signal."""

    def test_short_text_has_no_shingles(self):
        """Below one shingle's width there is nothing to compare."""
        assert shingles("too short to shingle") == set()

    def test_syndicated_copy_scores_high(self):
        """A republished story shares long verbatim runs."""
        assert shingle_overlap(WIRE_STORY, SYNDICATED_COPY) >= 0.6

    def test_unrelated_texts_score_zero(self):
        """Different articles share no eight-word runs."""
        assert shingle_overlap(WIRE_STORY, UNRELATED) == 0.0

    def test_identical_text_scores_one(self):
        """A text fully contains itself."""
        assert shingle_overlap(WIRE_STORY, WIRE_STORY) == 1.0


class TestStatementSimilarity:
    """Containment handles the length asymmetry Jaccard punishes."""

    def test_paraphrase_scores_high(self):
        """The same point said at different lengths still matches."""
        score = statement_similarity(
            "Jurassic Park changed visual effects forever",
            "Jurassic Park changed the visual effects industry forever, and "
            "every studio followed",
        )
        assert score > 0.6

    def test_different_points_score_low(self):
        """Unrelated statements stay far apart."""
        assert statement_similarity(WIRE_STORY, UNRELATED) < 0.2

    def test_empty_scores_zero(self):
        """No content words means no similarity."""
        assert statement_similarity("", "anything at all") == 0.0


class TestSaysTheSameThing:
    """The corroboration decision, deliberately conservative."""

    def test_paraphrase_is_the_same_thing(self):
        """Wording differs, assertion does not."""
        assert says_the_same_thing(
            "Jurassic Park changed visual effects forever",
            "Jurassic Park changed the visual effects industry forever",
        )

    def test_conflicting_numbers_are_not(self):
        """Same sentence, different figure, is a disagreement."""
        assert not says_the_same_thing(
            "The dig uncovered 1,200 chambers beneath the site",
            "The dig uncovered 12,000 chambers beneath the site",
        )

    def test_one_figure_one_not_is_not(self):
        """A cited figure is part of the claim; its absence changes the claim."""
        assert not says_the_same_thing(
            "The dig uncovered 1,200 chambers beneath the site",
            "The dig uncovered many chambers beneath the site",
        )

    def test_very_short_statements_never_match(self):
        """Two-word fragments would match everything, so they match nothing."""
        assert not says_the_same_thing("the dig", "the dig")

    def test_unrelated_statements_are_not(self):
        """Different subjects do not corroborate."""
        assert not says_the_same_thing(WIRE_STORY, UNRELATED)


class TestGroupMatching:
    """Grouping is single-link and stable."""

    def test_matching_statements_share_a_group(self):
        """Two ways of saying one thing land in one group."""
        groups = group_matching(
            [
                ("A", "Jurassic Park changed visual effects forever"),
                ("B", "Jurassic Park changed the visual effects industry forever"),
                ("C", "The Hawara labyrinth was described by ancient writers"),
            ]
        )

        assert groups["A"] == groups["B"]
        assert groups["C"] != groups["A"]

    def test_group_ids_come_from_the_first_member(self):
        """Grouping is stable for a given input order."""
        groups = group_matching(
            [
                ("A", "Jurassic Park changed visual effects forever"),
                ("B", "Jurassic Park changed the visual effects industry forever"),
            ]
        )

        assert groups["A"] == "A"
        assert groups["B"] == "A"

    def test_empty_input(self):
        """No items, no groups."""
        assert group_matching([]) == {}
