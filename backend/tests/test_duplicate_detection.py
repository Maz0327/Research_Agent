"""Tests for code-decided syndication detection.

Cover for P3 work-order item B7. On the films corpus SRC_7 and SRC_8 are the
same Conversation article, republished by ScreenHub, and the pipeline counted
them as two independent sources agreeing. Detection is mechanical: 8-word
shingle containment, measured at 0.976 for that pair and 0.000 for all 27
others.
"""
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.duplicate_detection import (
    canonical_source,
    find_duplicate_sources,
    stage_duplicate_detection,
)

BASE = (
    "Jurassic Park changed film making forever by putting computer generated "
    "dinosaurs on screen beside animatronic ones and the industry never went "
    "back to what it had been doing before that summer. Steven Spielberg had "
    "planned to shoot the dinosaurs in stop motion until Industrial Light and "
    "Magic showed him a test that changed his mind about what was possible. "
) * 6

TRIMMED_COPY = BASE[: int(len(BASE) * 0.7)]

DIFFERENT = (
    "The Hawara labyrinth has been described by ancient writers for two "
    "thousand years and every surviving account disagrees with the next about "
    "what was buried under the sand. Herodotus wrote that he walked the upper "
    "chambers himself and was refused entry to the lower ones. "
) * 6


class TestFindDuplicateSources:
    """Republished copies are found; independent articles are not."""

    def test_syndicated_copy_is_detected(self):
        """A trimmed republication is mapped to its fuller original."""
        duplicate_of, report = find_duplicate_sources(
            [("SRC_7", BASE), ("SRC_8", TRIMMED_COPY)]
        )

        assert duplicate_of == {"SRC_8": "SRC_7"}
        assert report[0]["duplicate"] == "SRC_8"
        assert report[0]["canonical"] == "SRC_7"
        assert report[0]["overlap"] > 0.5

    def test_the_fuller_copy_is_canonical_without_dates(self):
        """With no dates, order of arrival does not decide which copy is kept."""
        duplicate_of, _ = find_duplicate_sources(
            [("SRC_3", TRIMMED_COPY), ("SRC_9", BASE)]
        )

        assert duplicate_of == {"SRC_3": "SRC_9"}

    def test_the_first_publisher_is_canonical(self):
        """The outlet that ran it first is the one attributed, even if shorter."""
        duplicate_of, _ = find_duplicate_sources(
            [
                ("SRC_7", TRIMMED_COPY, "2023-06-12"),
                ("SRC_8", BASE, "2023-06-23"),
            ]
        )

        assert duplicate_of == {"SRC_8": "SRC_7"}

    def test_independent_sources_are_left_alone(self):
        """Two different articles are two sources."""
        duplicate_of, report = find_duplicate_sources(
            [("SRC_1", BASE), ("SRC_2", DIFFERENT)]
        )

        assert duplicate_of == {}
        assert report == []

    def test_three_copies_collapse_to_one_canonical(self):
        """A chain of republications resolves to a single source."""
        duplicate_of, _ = find_duplicate_sources(
            [("SRC_1", BASE), ("SRC_2", TRIMMED_COPY), ("SRC_3", TRIMMED_COPY)]
        )

        assert duplicate_of == {"SRC_2": "SRC_1", "SRC_3": "SRC_1"}

    def test_short_sources_are_not_compared(self):
        """Below the word floor, shingle overlap is not a reliable signal."""
        duplicate_of, _ = find_duplicate_sources(
            [("SRC_1", "a short note"), ("SRC_2", "a short note")]
        )

        assert duplicate_of == {}

    def test_missing_text_is_skipped(self):
        """A source with no captured text cannot be compared."""
        duplicate_of, _ = find_duplicate_sources([("SRC_1", BASE), ("SRC_2", "")])

        assert duplicate_of == {}


class TestStageDuplicateDetection:
    """The stage records what it found and says so out loud."""

    def _ctx(self, packages):
        ctx = PipelineContext(job_id="job-1", topic="A topic")
        ctx.source_identity_packages = packages
        return ctx

    def _package(self, source_id, content):
        class _Pkg:
            pass

        pkg = _Pkg()
        pkg.source_id = source_id
        pkg.content = content
        return pkg

    def test_stage_stores_map_and_warns(self):
        """Detection lands on the context and in the job's warnings."""
        ctx = self._ctx(
            [self._package("SRC_7", BASE), self._package("SRC_8", TRIMMED_COPY)]
        )

        stage_duplicate_detection(ctx)

        assert ctx.duplicate_sources == {"SRC_8": "SRC_7"}
        assert len(ctx.duplicate_source_report) == 1
        assert any("republished copy" in w for w in ctx.warnings)

    def test_no_duplicates_no_warning(self):
        """A clean corpus produces no noise."""
        ctx = self._ctx(
            [self._package("SRC_1", BASE), self._package("SRC_2", DIFFERENT)]
        )

        stage_duplicate_detection(ctx)

        assert ctx.duplicate_sources == {}
        assert ctx.warnings == []

    def test_canonical_source_resolves(self):
        """Lookups resolve duplicates and pass everything else through."""
        ctx = self._ctx(
            [self._package("SRC_7", BASE), self._package("SRC_8", TRIMMED_COPY)]
        )
        stage_duplicate_detection(ctx)

        assert canonical_source(ctx, "SRC_8") == "SRC_7"
        assert canonical_source(ctx, "SRC_1") == "SRC_1"
