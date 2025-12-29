"""Unit tests for parallel stage executor."""
import time
from unittest.mock import MagicMock, patch

import pytest

from backend.pipeline.context import PipelineContext
from backend.pipeline.parallel_executor import (
    run_parallel_stages,
    _run_stage_safely,
)


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    ctx = PipelineContext(
        job_id="test-job-123",
        topic="Test Topic",
    )
    return ctx


def test_run_stage_safely_success(mock_context):
    """Test successful stage execution."""
    def successful_stage(ctx):
        ctx.warnings.append("Stage executed")

    error = _run_stage_safely(mock_context, successful_stage, "test_stage")

    assert error is None
    assert "Stage executed" in mock_context.warnings


def test_run_stage_safely_failure(mock_context):
    """Test stage failure is caught and returned."""
    def failing_stage(ctx):
        raise ValueError("Test error")

    error = _run_stage_safely(mock_context, failing_stage, "test_stage")

    assert error is not None
    assert isinstance(error, ValueError)
    assert "test_stage failed" in mock_context.warnings[-1]


def test_run_parallel_stages_empty(mock_context):
    """Test running no stages returns empty dict."""
    results = run_parallel_stages(mock_context, [], [])
    assert results == {}


def test_run_parallel_stages_single(mock_context):
    """Test running a single stage."""
    def single_stage(ctx):
        ctx.warnings.append("Single stage done")

    results = run_parallel_stages(
        mock_context,
        [single_stage],
        ["single"],
        max_workers=1
    )

    assert "single" in results
    assert results["single"] is None  # No error
    assert "Single stage done" in mock_context.warnings


def test_run_parallel_stages_multiple(mock_context):
    """Test running multiple stages in parallel."""
    execution_order = []

    def stage_a(ctx):
        time.sleep(0.1)
        execution_order.append("a")
        ctx.key_terms = ["a"]

    def stage_b(ctx):
        execution_order.append("b")
        ctx.angles = ["b"]

    def stage_c(ctx):
        time.sleep(0.05)
        execution_order.append("c")
        ctx.reddit_posts = ["c"]

    results = run_parallel_stages(
        mock_context,
        [stage_a, stage_b, stage_c],
        ["stage_a", "stage_b", "stage_c"],
        max_workers=3
    )

    assert len(results) == 3
    assert all(err is None for err in results.values())
    # All stages should have run
    assert len(execution_order) == 3
    # Due to parallelism, stage_b should often finish first (no sleep)
    # But we can't guarantee order, just that all ran


def test_run_parallel_stages_partial_failure(mock_context):
    """Test handling partial failures in parallel stages."""
    def success_stage(ctx):
        ctx.key_terms = ["success"]

    def failing_stage(ctx):
        raise RuntimeError("Stage failed")

    results = run_parallel_stages(
        mock_context,
        [success_stage, failing_stage],
        ["success", "failing"],
        max_workers=2
    )

    assert results["success"] is None
    assert results["failing"] is not None
    assert isinstance(results["failing"], RuntimeError)


def test_run_parallel_stages_modifies_context(mock_context):
    """Test that stages can modify shared context."""
    def add_key_terms(ctx):
        ctx.key_terms = ["term1", "term2"]

    def add_angles(ctx):
        ctx.angles = ["angle1", "angle2"]

    run_parallel_stages(
        mock_context,
        [add_key_terms, add_angles],
        ["terms", "angles"],
        max_workers=2
    )

    assert mock_context.key_terms == ["term1", "term2"]
    assert mock_context.angles == ["angle1", "angle2"]


def test_run_parallel_stages_default_names(mock_context):
    """Test default stage names are generated."""
    stages = [lambda ctx: None, lambda ctx: None]

    results = run_parallel_stages(mock_context, stages, max_workers=2)

    assert "stage_0" in results
    assert "stage_1" in results


def test_run_parallel_stages_max_workers_limit(mock_context):
    """Test that max_workers limits concurrent execution."""
    concurrent_count = []
    max_concurrent = 0
    current_concurrent = 0

    def counting_stage(ctx):
        nonlocal current_concurrent, max_concurrent
        current_concurrent += 1
        max_concurrent = max(max_concurrent, current_concurrent)
        time.sleep(0.1)
        current_concurrent -= 1

    # Run 5 stages with max 2 workers
    stages = [counting_stage for _ in range(5)]
    names = [f"stage_{i}" for i in range(5)]

    run_parallel_stages(mock_context, stages, names, max_workers=2)

    # Should never have had more than 2 concurrent
    assert max_concurrent <= 2
