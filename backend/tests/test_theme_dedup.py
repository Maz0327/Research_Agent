"""Tests for mechanical theme deduplication.

Cover for P3 work-order item B8. The labyrinth run produced 39 themes
including both "Suppression of Information" and "Control and Suppression of
Archaeological Information". The merge is deliberately narrow: one label
wholly inside the other, or near-verbatim descriptions. Themes that restate
each other in different words are a semantic problem, handled by the
Briefing's subject-mapping pass.
"""
from backend.models.semantic_units import Theme
from backend.pipeline.theme_dedup import merge_similar_themes


def _theme(theme_id, label, description, key_points=None, sources=None) -> Theme:
    """A theme with the fields dedup reads."""
    return Theme(
        theme_id=theme_id,
        label=label,
        description=description,
        related_key_points=list(key_points or []),
        sources_supporting=list(sources or []),
    )


class TestMergeSimilarThemes:
    """Restatements collapse; distinct themes survive."""

    def test_subsumed_label_is_merged(self):
        """The labyrinth case: one label sits entirely inside another."""
        themes = [
            _theme("T1", "Control and Suppression of Archaeological Information",
                   "Authorities manage and release discoveries on their own terms."),
            _theme("T2", "Suppression of Information",
                   "Officials are portrayed as actively withholding findings."),
        ]

        merged, report = merge_similar_themes(themes)

        assert len(merged) == 1
        assert report[0]["merged"] == "T2"
        assert report[0]["into"] == "T1"

    def test_near_verbatim_descriptions_are_merged(self):
        """Different labels, the same paragraph, is one theme."""
        body = (
            "A recurring pattern where remote sensing technology is used to "
            "challenge the established archaeological account of the site."
        )
        themes = [
            _theme("T1", "Rediscovery through Technology", body),
            _theme("T2", "Technology and the Record", body + " Scans are cited."),
        ]

        merged, report = merge_similar_themes(themes)

        assert len(merged) == 1
        assert len(report) == 1

    def test_distinct_themes_survive(self):
        """Themes about different things are left alone."""
        themes = [
            _theme("T1", "Suppression of Information",
                   "Officials withhold findings from the public record."),
            _theme("T2", "Dating the Construction",
                   "Sources disagree about when the structure was built."),
        ]

        merged, report = merge_similar_themes(themes)

        assert len(merged) == 2
        assert report == []

    def test_one_word_labels_never_subsume(self):
        """A single shared word is not evidence of the same theme."""
        themes = [
            _theme("T1", "Suppression", "Officials withhold findings."),
            _theme("T2", "Suppression and Dating Disputes",
                   "Sources disagree about when the structure was built."),
        ]

        merged, _ = merge_similar_themes(themes)

        assert len(merged) == 2

    def test_references_are_unioned_not_dropped(self):
        """No key point loses its theme in a merge."""
        themes = [
            _theme("T1", "Control and Suppression of Archaeological Information",
                   "Authorities manage releases.", key_points=["SRC_1:KP_1"],
                   sources=["SRC_1"]),
            _theme("T2", "Suppression of Information",
                   "Officials withhold findings from the public.",
                   key_points=["SRC_2:KP_4"], sources=["SRC_2"]),
        ]

        merged, _ = merge_similar_themes(themes)

        assert merged[0].related_key_points == ["SRC_1:KP_1", "SRC_2:KP_4"]
        assert merged[0].sources_supporting == ["SRC_1", "SRC_2"]
        assert merged[0].is_consensus is True

    def test_fullest_description_survives(self):
        """The merge keeps the version that says the most."""
        long_description = (
            "Officials are portrayed as actively withholding findings, refusing "
            "permits, and closing the site to independent survey teams."
        )
        themes = [
            _theme("T1", "Control and Suppression of Archaeological Information", "Short."),
            _theme("T2", "Suppression of Information", long_description),
        ]

        merged, _ = merge_similar_themes(themes)

        assert merged[0].description == long_description

    def test_empty_input(self):
        """No themes, no merges."""
        assert merge_similar_themes([]) == ([], [])
