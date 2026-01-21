"""
Unit tests for pipeline stages.

Updated: 2026-01-19 - Removed Slack mocks (integration deprecated).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.pipeline.context import PipelineContext


@pytest.fixture
def mock_context():
    """Create mock pipeline context for testing."""
    ctx = PipelineContext(
        job_id="test-job-123",
        topic="Test research topic about AI ethics",
    )
    return ctx


class TestInitializationStage:
    """Tests for stage_0_initialize."""

    @patch("backend.pipeline.stages.initialization.update_job")
    def test_initialize_sets_job_running(self, mock_update, mock_context):
        """Initialize stage should set job status to running."""
        from backend.pipeline.stages.initialization import stage_0_initialize

        stage_0_initialize(mock_context)

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["status"] == "running"
        assert call_kwargs["stage"] == "initializing"
        assert call_kwargs["progress_percent"] == 0


class TestCompletionStage:
    """Tests for stage_10_completion."""

    @patch("backend.pipeline.stages.initialization.get_storage_client", return_value=None)
    @patch("backend.pipeline.stages.initialization.update_job")
    def test_completion_sets_job_completed(self, mock_update, mock_storage, mock_context):
        """Completion stage should set job status to completed."""
        from backend.pipeline.stages.initialization import stage_10_completion

        # Set up source_identity_packages with source_type for youtube counting
        mock_pkg = Mock()
        mock_pkg.source_type = "article"
        mock_context.source_identity_packages = [mock_pkg]
        # Set up semantic_extractions with claims
        mock_extraction = Mock()
        mock_extraction.claims = [Mock(claim_id="CLM_1")]
        mock_context.semantic_extractions = [mock_extraction]
        # Set up empty outputs (no storage configured)
        mock_context.outputs = {}

        result = stage_10_completion(mock_context)

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["status"] == "completed"
        assert call_kwargs["progress_percent"] == 100

        # CRITICAL: Verify partial_artifacts is used, NOT artifacts
        # This prevents regression of the empty artifacts JSONB bug
        assert "partial_artifacts" in call_kwargs, "Must use partial_artifacts for atomic path"
        assert "artifacts" not in call_kwargs, "Must NOT use artifacts with atomic updates"
        assert isinstance(call_kwargs["partial_artifacts"], dict)

    @patch("backend.pipeline.stages.initialization.update_job")
    def test_completion_returns_result_dict(self, mock_update, mock_context):
        """Completion stage should return result dictionary with doc_paths and counts."""
        from backend.pipeline.stages.initialization import stage_10_completion

        # Mock storage client that returns actual paths
        mock_storage_client = Mock()
        mock_storage_client.upload_document.side_effect = lambda job_id, doc_type, _: f"{job_id}/{doc_type}.json"

        # Set up source_identity_packages with youtube source_type
        mock_yt_pkg = Mock()
        mock_yt_pkg.source_type = "youtube"
        mock_yt_pkg.kind = None
        mock_context.source_identity_packages = [mock_yt_pkg]

        # Set up semantic_extractions with claims
        mock_extraction = Mock()
        mock_extraction.claims = [Mock(claim_id="CLM_1"), Mock(claim_id="CLM_2")]
        mock_context.semantic_extractions = [mock_extraction]

        # Set up document outputs (required for storage upload)
        mock_context.outputs = {
            "source_ledger": {"topic": "test"},
            "source_ledger_md": "# Source Ledger",
            "jump_start": {"scope_in": ["test"]},
            "jump_start_md": "# Jump Start",
            "semantic_brief": {"semantic_core": "test"},
            "semantic_brief_md": "# Semantic Brief",
        }

        with patch("backend.pipeline.stages.initialization.get_storage_client", return_value=mock_storage_client):
            result = stage_10_completion(mock_context)

        # Core assertions
        assert result["job_id"] == mock_context.job_id
        assert result["status"] == "completed"

        # doc_paths should have 3 entries when storage is configured
        assert "doc_paths" in result
        assert "doc_urls" in result
        assert result["doc_paths"] == result["doc_urls"]
        assert len(result["doc_paths"]) == 3

        # folder_url must be documents/{job_id} when doc_paths exists
        assert result["folder_url"] == f"documents/{mock_context.job_id}"

        # Count fields must be integers
        assert result["claims_count"] == 2
        assert result["sources_count"] == 1
        assert result["youtube_videos_count"] == 1
        assert result["warnings_count"] == 0

        # Schema-aligned aliases
        assert result["total_claims"] == result["claims_count"]
        assert result["total_sources"] == result["sources_count"]
        assert result["source_count"] == result["sources_count"]
        assert result["warning_count"] == result["warnings_count"]

        # CRITICAL: Verify partial_artifacts contains doc paths (prevents empty artifacts bug)
        call_kwargs = mock_update.call_args[1]
        assert "partial_artifacts" in call_kwargs, "Must use partial_artifacts for atomic path"
        assert "artifacts" not in call_kwargs, "Must NOT use artifacts with atomic updates"
        partial_artifacts = call_kwargs["partial_artifacts"]
        assert "doc_0_path" in partial_artifacts, "partial_artifacts must contain doc_0_path"
        assert "doc_1_path" in partial_artifacts, "partial_artifacts must contain doc_1_path"
        assert "doc_2_path" in partial_artifacts, "partial_artifacts must contain doc_2_path"

    @patch("backend.pipeline.stages.initialization.get_storage_client", return_value=None)
    @patch("backend.pipeline.stages.initialization.update_job")
    def test_completion_handles_no_storage_paths(self, mock_update, mock_storage, mock_context):
        """Completion stage should handle missing storage paths gracefully."""
        from backend.pipeline.stages.initialization import stage_10_completion

        # Empty context - no storage_paths, no extractions
        mock_context.outputs = {}
        mock_context.semantic_extractions = []
        mock_context.source_identity_packages = []

        result = stage_10_completion(mock_context)

        # folder_url is None when no doc_paths
        assert result["folder_url"] is None
        assert result["doc_paths"] == {}
        assert result["doc_urls"] == {}
        assert result["status"] == "completed"

        # Counts should be zero
        assert result["claims_count"] == 0
        assert result["sources_count"] == 0
        assert result["youtube_videos_count"] == 0

    @patch("backend.pipeline.stages.initialization.get_storage_client", return_value=None)
    @patch("backend.pipeline.stages.initialization.update_job")
    def test_completion_youtube_count_uses_kind_fallback(self, mock_update, mock_storage, mock_context):
        """youtube_videos_count should check both source_type and kind attributes."""
        from backend.pipeline.stages.initialization import stage_10_completion

        # Set up source with kind="youtube" instead of source_type
        mock_pkg = Mock()
        mock_pkg.source_type = None
        mock_pkg.kind = "youtube"
        mock_context.source_identity_packages = [mock_pkg]
        mock_context.outputs = {}
        mock_context.semantic_extractions = []

        result = stage_10_completion(mock_context)

        assert result["youtube_videos_count"] == 1
        assert result["sources_count"] == 1

    @patch("backend.pipeline.stages.initialization.update_job")
    def test_completion_no_placeholder_markdown_when_storage_exists(self, mock_update, mock_context):
        """
        CRITICAL: When storage paths exist, do NOT write placeholder markdown to inline fields.

        Placeholder markdown (e.g., "Document Available via Cloud Storage") causes the
        frontend to display stubs instead of fetching real content from storage.
        """
        from backend.pipeline.stages.initialization import stage_10_completion

        # Mock storage client that returns actual paths
        mock_storage_client = Mock()
        mock_storage_client.upload_document.side_effect = lambda job_id, doc_type, _: f"{job_id}/{doc_type}.json"

        # Set up document outputs (required for storage upload)
        mock_context.outputs = {
            "source_ledger": {"topic": "test"},
            "source_ledger_md": "# Real Source Ledger Content",
            "jump_start": {"scope_in": ["test"]},
            "jump_start_md": "# Real Jump Start Content",
            "semantic_brief": {"semantic_core": "test"},
            "semantic_brief_md": "# Real Semantic Brief Content",
        }
        mock_context.semantic_extractions = []
        mock_context.source_identity_packages = []

        with patch("backend.pipeline.stages.initialization.get_storage_client", return_value=mock_storage_client):
            stage_10_completion(mock_context)

        # Get the partial_artifacts that was passed to update_job
        call_kwargs = mock_update.call_args[1]
        partial_artifacts = call_kwargs["partial_artifacts"]

        # CRITICAL: Storage paths MUST be present
        assert "doc_0_path" in partial_artifacts
        assert "doc_1_path" in partial_artifacts
        assert "doc_2_path" in partial_artifacts

        # CRITICAL: Inline fields MUST NOT contain placeholder markdown
        # These fields should NOT be in partial_artifacts when storage paths exist
        if "source_ledger" in partial_artifacts:
            inline_md = partial_artifacts["source_ledger"].get("markdown", "")
            assert "Document Available via Cloud Storage" not in inline_md, \
                "source_ledger must NOT contain placeholder markdown"
            assert "inline JSON omitted" not in inline_md, \
                "source_ledger must NOT contain stub text"

        if "jump_start" in partial_artifacts:
            inline_md = partial_artifacts["jump_start"].get("markdown", "")
            assert "Document Available via Cloud Storage" not in inline_md, \
                "jump_start must NOT contain placeholder markdown"

        if "semantic_brief" in partial_artifacts:
            inline_md = partial_artifacts["semantic_brief"].get("markdown", "")
            assert "Document Available via Cloud Storage" not in inline_md, \
                "semantic_brief must NOT contain placeholder markdown"


class TestPipelineContext:
    """Tests for PipelineContext dataclass."""

    def test_context_initialization(self):
        """Context should initialize with defaults."""
        ctx = PipelineContext(
            job_id="test-123",
            topic="Test topic"
        )

        assert ctx.job_id == "test-123"
        assert ctx.topic == "Test topic"
        assert ctx.claims == []
        assert ctx.warnings == []
        assert ctx.outputs == {}

    def test_add_warning(self):
        """add_warning should append to warnings list."""
        ctx = PipelineContext(job_id="test", topic="test")

        ctx.add_warning("First warning")
        ctx.add_warning("Second warning")

        assert len(ctx.warnings) == 2
        assert "First warning" in ctx.warnings

    def test_set_output(self):
        """set_output should store markdown output."""
        ctx = PipelineContext(job_id="test", topic="test")

        ctx.set_output("research_map_md", "# Research Map\nContent here")

        assert "research_map_md" in ctx.outputs
        assert "Research Map" in ctx.outputs["research_map_md"]

    def test_add_cost_without_tracker(self):
        """add_cost should not fail without cost tracker."""
        ctx = PipelineContext(job_id="test", topic="test")

        # Should not raise
        ctx.add_cost("openai", 0.01)

    def test_get_cost_summary_without_tracker(self):
        """get_cost_summary should return empty dict without tracker."""
        ctx = PipelineContext(job_id="test", topic="test")

        summary = ctx.get_cost_summary()

        assert summary == {}


# Note: TestDiscoveryStages removed (2026-01-19 - Legacy pipeline deprecated)
# Discovery stages (1-6.5) have been removed from the semantic pipeline.
# Tests for semantic pipeline stages are in test_semantic_*.py files.


class TestUpdateJobGuard:
    """Tests for the update_job guard against artifacts + atomic path misuse."""

    def test_guard_raises_when_artifacts_used_with_atomic_path(self):
        """Guard should raise ValueError when artifacts= is combined with atomic updates."""
        from backend.state.impl.supabase_store import SupabaseJobStore
        from backend.models.job_record import Artifacts

        store = SupabaseJobStore()

        # Create a minimal Artifacts object
        artifacts = Artifacts()

        # Calling update_job with BOTH partial_outputs AND artifacts should raise
        with pytest.raises(ValueError) as exc_info:
            store.update_job(
                job_id="00000000-0000-0000-0000-000000000001",
                status="completed",
                partial_outputs={"some": "data"},  # triggers atomic path
                artifacts=artifacts,  # should be rejected
            )

        # Verify error message is descriptive
        assert "artifacts= cannot be used with atomic updates" in str(exc_info.value)
        assert "partial_artifacts=" in str(exc_info.value)

    def test_guard_raises_when_artifacts_used_with_warnings_append(self):
        """Guard should raise when artifacts= is combined with warnings_append."""
        from backend.state.impl.supabase_store import SupabaseJobStore
        from backend.models.job_record import Artifacts

        store = SupabaseJobStore()
        artifacts = Artifacts()

        with pytest.raises(ValueError) as exc_info:
            store.update_job(
                job_id="00000000-0000-0000-0000-000000000002",
                status="completed",
                warnings_append=["some warning"],  # triggers atomic path
                artifacts=artifacts,  # should be rejected
            )

        assert "artifacts= cannot be used with atomic updates" in str(exc_info.value)
