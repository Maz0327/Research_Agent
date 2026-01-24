"""
Tests for iteration pipeline components.

Tests cover:
- MetricsTracker functionality
- BaselineData loading (mocked)
- Context initialization
- Mode dispatcher routing
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import time


class TestMetricsTracker:
    """Test MetricsTracker accumulation and finalization."""

    def test_initial_state(self):
        """Metrics tracker starts with zero counts."""
        from backend.pipeline.iteration.metrics_tracker import MetricsTracker

        tracker = MetricsTracker()
        assert tracker.llm_calls == 0
        assert tracker.tokens_in == 0
        assert tracker.tokens_out == 0

    def test_record_llm_call(self):
        """Recording LLM calls accumulates counts."""
        from backend.pipeline.iteration.metrics_tracker import MetricsTracker

        tracker = MetricsTracker()
        tracker.record_llm_call(tokens_in=100, tokens_out=50)
        tracker.record_llm_call(tokens_in=200, tokens_out=150)

        assert tracker.llm_calls == 2
        assert tracker.tokens_in == 300
        assert tracker.tokens_out == 200

    def test_finalize_returns_iteration_metrics(self):
        """Finalize returns IterationMetrics model."""
        from backend.pipeline.iteration.metrics_tracker import MetricsTracker
        from backend.models.job_record import IterationMetrics

        tracker = MetricsTracker()
        tracker.record_llm_call(tokens_in=500, tokens_out=300)

        # Small delay to ensure wall_time_ms > 0
        time.sleep(0.01)
        result = tracker.finalize()

        assert isinstance(result, IterationMetrics)
        assert result.llm_calls == 1
        assert result.tokens_in == 500
        assert result.tokens_out == 300
        assert result.wall_time_ms > 0


class TestBaselineLoader:
    """Test baseline data loading."""

    def test_extract_source_urls_from_doc0(self):
        """Extract URLs from Source Ledger structure."""
        from backend.pipeline.iteration.baseline_loader import extract_source_urls

        doc_0 = {
            "sources": [
                {"source_id": "SRC_1", "url": "https://example.com/1"},
                {"source_id": "SRC_2", "url": "https://example.com/2"},
                {"source_id": "SRC_3", "source_url": "https://example.com/3"},  # Alternative key
            ]
        }

        urls = extract_source_urls(doc_0)
        assert len(urls) == 3
        assert "https://example.com/1" in urls
        assert "https://example.com/2" in urls
        assert "https://example.com/3" in urls

    def test_extract_source_urls_empty(self):
        """Handle empty sources list."""
        from backend.pipeline.iteration.baseline_loader import extract_source_urls

        doc_0 = {"sources": []}
        urls = extract_source_urls(doc_0)
        assert urls == []

    def test_reconstruct_source_packages(self):
        """Reconstruct minimal source packages from Doc 0."""
        from backend.pipeline.iteration.baseline_loader import reconstruct_source_packages

        doc_0 = {
            "sources": [
                {
                    "source_id": "SRC_1",
                    "url": "https://youtube.com/watch?v=abc",
                    "title": "Test Video",
                    "source_type": "youtube",
                },
                {
                    "source_id": "SRC_2",
                    "url": "https://example.com/article",
                    "title": "Test Article",
                    "source_type": "article",
                },
            ]
        }

        packages = reconstruct_source_packages(doc_0)
        assert len(packages) == 2
        assert packages[0]["source_id"] == "SRC_1"
        assert packages[0]["analysis_mode"] == "transcript_grounded"  # youtube -> transcript_grounded
        assert packages[1]["source_id"] == "SRC_2"
        assert packages[1]["analysis_mode"] == "article_fetched"


class TestContextInitializer:
    """Test context initialization for iterations."""

    def test_creates_pipeline_context(self):
        """Context initializer returns PipelineContext."""
        from backend.pipeline.iteration.context_initializer import create_iteration_context
        from backend.pipeline.iteration.baseline_loader import BaselineData
        from backend.pipeline.context import PipelineContext

        baseline = BaselineData(
            doc_0={"sources": []},
            doc_1={"gaps": []},
            doc_2={"themes": []},
            extractions=[{"source_id": "SRC_1", "key_points": []}],
            topic="Test topic",
            source_urls=["https://example.com"],
        )

        ctx, metrics = create_iteration_context(
            job_id="test-job",
            iteration_id="it_0001",
            baseline=baseline,
            mode="different_angle",
        )

        assert isinstance(ctx, PipelineContext)
        assert ctx.job_id == "test-job"
        assert ctx.topic == "Test topic"
        assert ctx.outputs["iteration_id"] == "it_0001"
        assert ctx.outputs["iteration_mode"] == "different_angle"

    def test_different_angle_preloads_extractions(self):
        """Different angle mode pre-populates extractions."""
        from backend.pipeline.iteration.context_initializer import create_iteration_context
        from backend.pipeline.iteration.baseline_loader import BaselineData

        baseline = BaselineData(
            doc_0={"sources": []},
            doc_1={"gaps": []},
            doc_2={"themes": []},
            extractions=[{"source_id": "SRC_1"}, {"source_id": "SRC_2"}],
            topic="Test",
            source_urls=[],
        )

        ctx, _ = create_iteration_context("job", "it_0001", baseline, "different_angle")
        assert len(ctx.semantic_extractions) == 2


class TestModeDispatcher:
    """Test iteration mode dispatcher."""

    def test_unknown_mode_raises(self):
        """Unknown mode raises ValueError."""
        from backend.pipeline.iteration.modes import run_iteration_mode
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.iteration.baseline_loader import BaselineData
        from backend.pipeline.iteration.metrics_tracker import MetricsTracker
        from backend.pipeline.cost_tracker import CostTracker

        ctx = PipelineContext(job_id="test", topic="Test", cost_tracker=CostTracker())
        baseline = BaselineData(
            doc_0={}, doc_1={}, doc_2={}, extractions=[], topic="Test", source_urls=[]
        )
        metrics = MetricsTracker()

        with pytest.raises(ValueError, match="Unknown iteration mode"):
            run_iteration_mode(
                mode="invalid_mode",
                ctx=ctx,
                baseline=baseline,
                metrics=metrics,
            )

    def test_different_angle_requires_angle(self):
        """Different angle mode requires angle parameter."""
        from backend.pipeline.iteration.modes import run_iteration_mode
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.iteration.baseline_loader import BaselineData
        from backend.pipeline.iteration.metrics_tracker import MetricsTracker
        from backend.pipeline.cost_tracker import CostTracker

        ctx = PipelineContext(job_id="test", topic="Test", cost_tracker=CostTracker())
        baseline = BaselineData(
            doc_0={}, doc_1={}, doc_2={}, extractions=[], topic="Test", source_urls=[]
        )
        metrics = MetricsTracker()

        with pytest.raises(ValueError, match="requires 'angle' parameter"):
            run_iteration_mode(
                mode="different_angle",
                ctx=ctx,
                baseline=baseline,
                metrics=metrics,
                angle=None,  # Missing angle
            )

    def test_custom_requires_user_prompt(self):
        """Custom mode requires user_prompt parameter."""
        from backend.pipeline.iteration.modes import run_iteration_mode
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.iteration.baseline_loader import BaselineData
        from backend.pipeline.iteration.metrics_tracker import MetricsTracker
        from backend.pipeline.cost_tracker import CostTracker

        ctx = PipelineContext(job_id="test", topic="Test", cost_tracker=CostTracker())
        baseline = BaselineData(
            doc_0={}, doc_1={}, doc_2={}, extractions=[], topic="Test", source_urls=[]
        )
        metrics = MetricsTracker()

        with pytest.raises(ValueError, match="requires 'user_prompt' parameter"):
            run_iteration_mode(
                mode="custom",
                ctx=ctx,
                baseline=baseline,
                metrics=metrics,
                user_prompt="",  # Empty prompt
            )


class TestIterationModels:
    """Test iteration-related models."""

    def test_iteration_request_model(self):
        """IterationRequest model validates correctly."""
        from backend.models.job_record import IterationRequest

        request = IterationRequest(
            mode="more_sources",
            user_prompt="Find more academic sources",
            max_new_sources=5,
        )
        assert request.mode == "more_sources"
        assert request.max_new_sources == 5

    def test_iteration_outputs_model(self):
        """IterationOutputs model handles paths and inline data."""
        from backend.models.job_record import IterationOutputs

        outputs = IterationOutputs(
            doc_0_path="jobs/123/iterations/it_0001/doc_0.json",
            doc_1_path=None,  # Storage failed
            doc_1_inline={"key_points": []},  # Fallback
        )
        assert outputs.doc_0_path is not None
        assert outputs.doc_1_inline is not None

    def test_iteration_metrics_model(self):
        """IterationMetrics model holds all metrics."""
        from backend.models.job_record import IterationMetrics

        metrics = IterationMetrics(
            llm_calls=5,
            tokens_in=5000,
            tokens_out=3000,
            wall_time_ms=45000,
        )
        assert metrics.llm_calls == 5
        assert metrics.wall_time_ms == 45000
