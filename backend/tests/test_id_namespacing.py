"""Tests for globally-unique unit IDs and measured corroboration.

Cover for P3 work-order item B6. Source-isolated extraction numbers each
source's units from 1, so pooling them collided every `KP_1`: on the 16-source
Hawara run the whole corpus read as "Source 16, 100% single-source". IDs are
now qualified at the parse boundary, and corroboration is measured by matching
statements across sources instead of copied from a field that can only ever
name one source.
"""
from backend.models.semantic_units import (
    AnalysisMode,
    Claim,
    KeyPoint,
    Quote,
    SemanticExtractionResult,
    Tension,
    Theme,
)
from backend.pipeline.id_namespacing import (
    local_id,
    namespace_extraction_ids,
    namespaced_id,
    source_of,
)
from backend.pipeline.stages.semantic_synthesis import build_source_coverage


def _extraction(source_id: str) -> SemanticExtractionResult:
    """A one-source extraction with the usual cross-references inside it."""
    return SemanticExtractionResult(
        source_id=source_id,
        analysis_mode=AnalysisMode.ARTICLE_FETCHED,
        quotes=[Quote(quote_id="QT_1", text="a quote", source_id=source_id)],
        claims=[
            Claim(claim_id="CLM_1", statement="a claim", source_id=source_id,
                  supporting_quotes=["a quote"])
        ],
        key_points=[
            KeyPoint(key_point_id="KP_1", statement="a point", source_ids=[],
                     supporting_claims=["CLM_1"]),
            KeyPoint(key_point_id="KP_2", statement="another point", source_ids=[]),
        ],
        themes=[
            Theme(theme_id="THEME_1", label="L", description="D",
                  related_key_points=["KP_1", "KP_2"])
        ],
        tensions=[
            Tension(tension_id="TEN_1", description="a tension",
                    involved_key_points=["KP_1"])
        ],
    )


class TestNamespacedId:
    """Qualifying is idempotent and reversible."""

    def test_qualifies_a_local_id(self):
        """`KP_1` from SRC_3 becomes `SRC_3:KP_1`."""
        assert namespaced_id("SRC_3", "KP_1") == "SRC_3:KP_1"

    def test_leaves_qualified_ids_alone(self):
        """Applying it twice changes nothing."""
        assert namespaced_id("SRC_3", "SRC_3:KP_1") == "SRC_3:KP_1"

    def test_handles_empty(self):
        """Empty IDs pass through untouched."""
        assert namespaced_id("SRC_3", "") == ""
        assert namespaced_id("SRC_3", None) is None

    def test_reads_the_parts_back(self):
        """Both halves are recoverable."""
        assert source_of("SRC_3:KP_1") == "SRC_3"
        assert local_id("SRC_3:KP_1") == "KP_1"
        assert source_of("KP_1") is None
        assert local_id("KP_1") == "KP_1"


class TestNamespaceExtractionIds:
    """Every ID and every internal reference is qualified together."""

    def test_all_unit_ids_are_qualified(self):
        """Quotes, claims, key points, themes, and tensions all get prefixes."""
        result = namespace_extraction_ids(_extraction("SRC_3"))

        assert result.quotes[0].quote_id == "SRC_3:QT_1"
        assert result.claims[0].claim_id == "SRC_3:CLM_1"
        assert result.key_points[0].key_point_id == "SRC_3:KP_1"
        assert result.themes[0].theme_id == "SRC_3:THEME_1"
        assert result.tensions[0].tension_id == "SRC_3:TEN_1"

    def test_internal_references_follow(self):
        """A theme still points at its own source's key points."""
        result = namespace_extraction_ids(_extraction("SRC_3"))

        assert result.themes[0].related_key_points == ["SRC_3:KP_1", "SRC_3:KP_2"]
        assert result.tensions[0].involved_key_points == ["SRC_3:KP_1"]
        assert result.key_points[0].supporting_claims == ["SRC_3:CLM_1"]

    def test_source_ids_are_pinned_to_the_owner(self):
        """Isolated extraction can only attribute to its own source."""
        result = namespace_extraction_ids(_extraction("SRC_3"))

        assert result.key_points[0].source_ids == ["SRC_3"]
        assert result.tensions[0].source_ids == ["SRC_3"]

    def test_quote_text_references_are_untouched(self):
        """`supporting_quotes` holds text, not IDs, so it is left alone."""
        result = namespace_extraction_ids(_extraction("SRC_3"))

        assert result.claims[0].supporting_quotes == ["a quote"]

    def test_two_sources_no_longer_collide(self):
        """The bug itself: pooling two extractions used to lose one."""
        pooled = {}
        for source_id in ("SRC_1", "SRC_16"):
            for kp in namespace_extraction_ids(_extraction(source_id)).key_points:
                pooled[kp.key_point_id] = kp

        assert len(pooled) == 4
        assert pooled["SRC_1:KP_1"].source_ids == ["SRC_1"]
        assert pooled["SRC_16:KP_1"].source_ids == ["SRC_16"]

    def test_idempotent(self):
        """Running it twice is a no-op."""
        once = namespace_extraction_ids(_extraction("SRC_3"))
        twice = namespace_extraction_ids(once)

        assert twice.key_points[0].key_point_id == "SRC_3:KP_1"
        assert twice.themes[0].related_key_points == ["SRC_3:KP_1", "SRC_3:KP_2"]


class TestBuildSourceCoverage:
    """Corroboration is measured across sources, not asserted by a model."""

    def test_matching_statements_corroborate(self):
        """Two sources saying the same thing show two supporting sources."""
        key_points = [
            {
                "key_point_id": "SRC_1:KP_1",
                "statement": "Jurassic Park changed visual effects forever",
                "source_ids": ["SRC_1"],
            },
            {
                "key_point_id": "SRC_2:KP_1",
                "statement": "Jurassic Park changed the visual effects industry forever",
                "source_ids": ["SRC_2"],
            },
        ]

        coverage = build_source_coverage(key_points)

        assert coverage["SRC_1:KP_1"] == ["SRC_1", "SRC_2"]
        assert coverage["SRC_2:KP_1"] == ["SRC_1", "SRC_2"]

    def test_different_statements_stay_single_source(self):
        """Unrelated points are not merged into false corroboration."""
        key_points = [
            {
                "key_point_id": "SRC_1:KP_1",
                "statement": "Digital intermediate grading flattened contrast",
                "source_ids": ["SRC_1"],
            },
            {
                "key_point_id": "SRC_2:KP_1",
                "statement": "Practical effects aged better than early computer graphics",
                "source_ids": ["SRC_2"],
            },
        ]

        coverage = build_source_coverage(key_points)

        assert coverage["SRC_1:KP_1"] == ["SRC_1"]
        assert coverage["SRC_2:KP_1"] == ["SRC_2"]

    def test_conflicting_numbers_never_corroborate(self):
        """Same sentence, different figure, is a disagreement not a second source."""
        key_points = [
            {
                "key_point_id": "SRC_1:KP_1",
                "statement": "The dig uncovered 1,200 chambers beneath the site",
                "source_ids": ["SRC_1"],
            },
            {
                "key_point_id": "SRC_2:KP_1",
                "statement": "The dig uncovered 12,000 chambers beneath the site",
                "source_ids": ["SRC_2"],
            },
        ]

        coverage = build_source_coverage(key_points)

        assert coverage["SRC_1:KP_1"] == ["SRC_1"]
        assert coverage["SRC_2:KP_1"] == ["SRC_2"]

    def test_syndicated_copies_count_once(self):
        """A wire story republished elsewhere does not inflate corroboration."""
        key_points = [
            {
                "key_point_id": "SRC_7:KP_1",
                "statement": "Jurassic Park changed visual effects forever",
                "source_ids": ["SRC_7"],
            },
            {
                "key_point_id": "SRC_8:KP_1",
                "statement": "Jurassic Park changed visual effects forever",
                "source_ids": ["SRC_8"],
            },
        ]

        coverage = build_source_coverage(key_points, duplicate_of={"SRC_8": "SRC_7"})

        assert coverage["SRC_7:KP_1"] == ["SRC_7"]
        assert coverage["SRC_8:KP_1"] == ["SRC_7"]
