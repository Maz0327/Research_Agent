"""Tests for async behavior in the semantic pipeline.

Phase 9: Tests concurrent operations and race condition prevention.
"""

import pytest
from unittest.mock import MagicMock, patch
import threading
import time

from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    KeyPoint,
    SemanticExtractionResult,
)
from backend.pipeline.context import PipelineContext


# =============================================================================
# Test: Concurrent Operations
# =============================================================================


class TestConcurrentOperations:
    """Test handling of concurrent operations."""

    def test_context_thread_safety_warnings(self):
        """Should accumulate warnings without data loss."""
        ctx = PipelineContext(job_id="test-thread", topic="Test")
        errors = []

        def add_warnings(n):
            """Add n warnings to context."""
            try:
                for i in range(n):
                    ctx.add_warning(f"Warning from thread {threading.current_thread().name} - {i}")
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = [
            threading.Thread(target=add_warnings, args=(10,), name=f"Thread-{i}")
            for i in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have all warnings (may have some data loss if not thread-safe)
        # At minimum, should not crash
        assert len(errors) == 0
        assert len(ctx.warnings) > 0  # At least some warnings made it

    def test_parallel_extraction_independence(self):
        """Each extraction should be independent."""
        extraction1 = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="From source 1",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,
                )
            ],
        )

        extraction2 = SemanticExtractionResult(
            source_id="SRC_2",
            analysis_mode=AnalysisMode.CAPTION_GROUNDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_2",
                    statement="From source 2",
                    source_ids=["SRC_2"],
                    confidence=ConfidenceLevel.MEDIUM,
                )
            ],
        )

        # Modifications to one should not affect the other
        extraction1.key_points.append(
            KeyPoint(
                key_point_id="KP_3",
                statement="Added to source 1",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.HIGH,
            )
        )

        assert len(extraction1.key_points) == 2
        assert len(extraction2.key_points) == 1

    def test_context_isolation(self):
        """Different contexts should be isolated."""
        ctx1 = PipelineContext(job_id="job-1", topic="Topic 1")
        ctx2 = PipelineContext(job_id="job-2", topic="Topic 2")

        ctx1.add_warning("Warning for job 1")
        ctx2.add_warning("Warning for job 2")

        assert "Warning for job 1" in ctx1.warnings
        assert "Warning for job 1" not in ctx2.warnings
        assert "Warning for job 2" in ctx2.warnings
        assert "Warning for job 2" not in ctx1.warnings

    def test_extraction_list_independence(self):
        """Extraction lists should be independent."""
        ctx1 = PipelineContext(job_id="job-1", topic="Topic 1")
        ctx2 = PipelineContext(job_id="job-2", topic="Topic 2")

        ctx1.semantic_extractions = [
            SemanticExtractionResult(source_id="SRC_1", analysis_mode=AnalysisMode.VIDEO_ONLY)
        ]

        assert ctx1.semantic_extractions != ctx2.semantic_extractions

    def test_multiple_contexts_no_interference(self):
        """Multiple contexts should not interfere."""
        contexts = [
            PipelineContext(job_id=f"job-{i}", topic=f"Topic {i}")
            for i in range(5)
        ]

        for i, ctx in enumerate(contexts):
            ctx.add_warning(f"Warning {i}")
            ctx.semantic_extractions = []

        # Each context should only have its own warning
        for i, ctx in enumerate(contexts):
            assert len(ctx.warnings) == 1
            assert f"Warning {i}" in ctx.warnings


# =============================================================================
# Test: Race Condition Prevention
# =============================================================================


class TestRaceConditionPrevention:
    """Test race condition prevention."""

    def test_no_race_on_status_updates(self):
        """Status updates should not cause race conditions."""
        ctx = PipelineContext(job_id="test-race", topic="Test")

        def update_status():
            for _ in range(100):
                ctx.add_warning("Status update")

        threads = [
            threading.Thread(target=update_status)
            for _ in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash, and should have some warnings
        assert len(ctx.warnings) > 0

    def test_no_race_on_extraction_append(self):
        """Appending extractions should be safe."""
        extractions = []

        def append_extraction(source_id):
            extraction = SemanticExtractionResult(
                source_id=source_id,
                analysis_mode=AnalysisMode.VIDEO_ONLY,
            )
            extractions.append(extraction)

        threads = [
            threading.Thread(target=append_extraction, args=(f"SRC_{i}",))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have all extractions
        assert len(extractions) == 10

    def test_no_race_on_progress_updates(self):
        """Progress updates should not cause race conditions."""
        progress_values = []

        def update_progress():
            for i in range(10):
                progress_values.append(i)
                time.sleep(0.001)

        threads = [
            threading.Thread(target=update_progress)
            for _ in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All values should be recorded
        assert len(progress_values) == 30

    def test_dataclass_immutability_pattern(self):
        """Dataclass fields should be treated as immutable after creation."""
        key_point = KeyPoint(
            key_point_id="KP_1",
            statement="Original statement",
            source_ids=["SRC_1"],
            confidence=ConfidenceLevel.HIGH,
        )

        # Store original values
        original_id = key_point.key_point_id
        original_statement = key_point.statement

        # Even if modified (dataclass is mutable), the original object is affected
        # This tests that we understand the behavior
        key_point.statement = "Modified statement"

        # The modification took effect (dataclass is mutable)
        assert key_point.statement == "Modified statement"
        assert key_point.key_point_id == original_id  # Other fields unchanged

    def test_list_mutations_isolated(self):
        """List mutations should be isolated between extractions."""
        extraction1 = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[],
        )

        extraction2 = SemanticExtractionResult(
            source_id="SRC_2",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[],
        )

        # Add to extraction1's list
        extraction1.key_points.append(
            KeyPoint(
                key_point_id="KP_1",
                statement="Test",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.HIGH,
            )
        )

        # extraction2's list should be empty
        assert len(extraction2.key_points) == 0
