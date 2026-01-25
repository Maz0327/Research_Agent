"""
Run Models - Unified abstraction for research runs.

A Run represents a single execution that produces Doc 0/1/2 outputs.
Runs can be:
- baseline: Initial research job
- add_sources: Add more sources (Doc 0 append-only)
- fix_weak: Address gaps/weaknesses
- counter: Find opposing viewpoints
- angle: Explore different perspective
- regenerate: Re-run synthesis with same sources

Runs are append-only. Once created, outputs are immutable.
New iterations create new runs that may inherit from previous runs.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RunType(str, Enum):
    """Type of research run."""

    BASELINE = "baseline"
    ADD_SOURCES = "add_sources"
    FIX_WEAK_SPOTS = "fix_weak"
    COUNTERARGUMENT = "counter"
    DIFFERENT_ANGLE = "angle"
    REGENERATE = "regenerate"


class RunStatus(str, Enum):
    """Run execution status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunError(BaseModel):
    """Error details if run failed."""

    code: str = Field(..., description="Error code (e.g., 'timeout', 'extraction_failed')")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error context")


class RunRequest(BaseModel):
    """Request that triggered the run."""

    # User guidance
    user_prompt: Optional[str] = Field(None, max_length=2000, description="Optional guidance from user")

    # For add_sources type
    new_source_urls: Optional[list[str]] = Field(None, description="URLs to add")
    max_new_sources: Optional[int] = Field(None, ge=1, le=10, description="Max sources to add")

    # For fix_weak type
    gap_ids: Optional[list[str]] = Field(None, description="GAP IDs to address")

    # For counterargument type
    claim_ids: Optional[list[str]] = Field(None, description="CLM IDs to find counters for")

    # For different_angle type
    perspective: Optional[str] = Field(None, description="New angle/perspective to explore")

    # Common
    requested_by: str = Field(..., description="User ID who requested")
    requested_at: datetime = Field(default_factory=datetime.utcnow)


class RunOutputs(BaseModel):
    """Output documents from a completed run."""

    # Storage paths (primary)
    doc_0_path: Optional[str] = Field(None, description="GCS path to Source Ledger")
    doc_1_path: Optional[str] = Field(None, description="GCS path to Jump-Start")
    doc_2_path: Optional[str] = Field(None, description="GCS path to Semantic Brief")

    # Inline fallback (if storage failed)
    doc_0_inline: Optional[dict[str, Any]] = Field(None, description="Inline Source Ledger")
    doc_1_inline: Optional[dict[str, Any]] = Field(None, description="Inline Jump-Start")
    doc_2_inline: Optional[dict[str, Any]] = Field(None, description="Inline Semantic Brief")

    # Doc 0 append metadata (for add_sources runs)
    doc_0_is_delta: bool = Field(
        False,
        description="True if Doc 0 only contains new sources (needs merge with parent)"
    )
    doc_0_parent_path: Optional[str] = Field(
        None,
        description="Parent Doc 0 path to merge with (if doc_0_is_delta)"
    )
    new_source_ids: Optional[list[str]] = Field(
        None,
        description="Source IDs added in this run"
    )

    def has_doc_0(self) -> bool:
        """Check if Doc 0 is available."""
        return bool(self.doc_0_path or self.doc_0_inline)

    def has_doc_1(self) -> bool:
        """Check if Doc 1 is available."""
        return bool(self.doc_1_path or self.doc_1_inline)

    def has_doc_2(self) -> bool:
        """Check if Doc 2 is available."""
        return bool(self.doc_2_path or self.doc_2_inline)


class RunMetrics(BaseModel):
    """Execution metrics for the run."""

    wall_time_ms: int = Field(0, ge=0, description="Total wall time in milliseconds")
    sources_processed: int = Field(0, ge=0, description="Number of sources processed")
    sources_new: int = Field(0, ge=0, description="New sources added (for add_sources)")
    key_points_found: int = Field(0, ge=0, description="Key points extracted")
    claims_extracted: int = Field(0, ge=0, description="Claims extracted")
    themes_identified: int = Field(0, ge=0, description="Themes identified in synthesis")
    llm_cost_usd: float = Field(0.0, ge=0.0, description="LLM API cost in USD")
    llm_tokens_input: int = Field(0, ge=0, description="Total input tokens")
    llm_tokens_output: int = Field(0, ge=0, description="Total output tokens")


class RunProducerPacket(BaseModel):
    """Producer Packet (Doc 3) scoped to this run."""

    status: RunStatus = Field(RunStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    path: Optional[str] = Field(None, description="GCS path to producer packet JSON")
    inline: Optional[dict[str, Any]] = Field(None, description="Inline producer packet")
    markdown: Optional[str] = Field(None, description="Rendered markdown")
    error: Optional[str] = None


class RunBoosterExpansion(BaseModel):
    """Booster expansion scoped to this run."""

    status: RunStatus = Field(RunStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[dict[str, Any]] = Field(None, description="Booster output data")
    markdown: Optional[str] = Field(None, description="Rendered markdown for Doc 1 expansion")
    error: Optional[str] = None


class Run(BaseModel):
    """
    A single research run producing Doc 0/1/2 outputs.

    Runs are append-only. Once created, a run's outputs are immutable.
    New iterations create new runs that may inherit from previous runs.

    Hierarchy:
    - run_0: Always the baseline run (initial job completion)
    - run_1+: Iteration runs that reference a parent_run_id

    For add_sources runs:
    - Doc 0 is a delta (new sources only)
    - Full Doc 0 is computed by merging parent + delta
    - Doc 1/2 are regenerated with all sources

    For regenerate runs:
    - Doc 0 is unchanged (inherit from parent)
    - Doc 1/2 are regenerated
    """

    # Identity
    run_id: str = Field(..., description="Unique run ID: run_0, run_1, ...")
    run_index: int = Field(..., ge=0, description="Sequential index (0 for baseline)")
    run_type: RunType = Field(..., description="Type of run")

    # Lineage
    parent_run_id: Optional[str] = Field(
        None,
        description="Parent run for iterations (None for baseline)"
    )

    # Request (what was asked)
    request: RunRequest = Field(..., description="What triggered this run")

    # Status tracking
    status: RunStatus = Field(RunStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[RunError] = None

    # Outputs (set on completion)
    outputs: Optional[RunOutputs] = None

    # Metrics (set on completion)
    metrics: Optional[RunMetrics] = None

    # Run-scoped enhancements (optional, triggered separately)
    producer_packet: Optional[RunProducerPacket] = None
    booster_expansion: Optional[RunBoosterExpansion] = None

    def is_baseline(self) -> bool:
        """Check if this is the baseline run."""
        return self.run_type == RunType.BASELINE and self.run_index == 0

    def is_completed(self) -> bool:
        """Check if run completed successfully."""
        return self.status == RunStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if run failed."""
        return self.status == RunStatus.FAILED

    def has_producer(self) -> bool:
        """Check if producer packet was generated."""
        return (
            self.producer_packet is not None
            and self.producer_packet.status == RunStatus.COMPLETED
        )

    def has_booster(self) -> bool:
        """Check if booster expansion was generated."""
        return (
            self.booster_expansion is not None
            and self.booster_expansion.status == RunStatus.COMPLETED
        )


# Mapping from legacy iteration modes to RunType
ITERATION_MODE_TO_RUN_TYPE: dict[str, RunType] = {
    "more_sources": RunType.ADD_SOURCES,
    "deeper": RunType.FIX_WEAK_SPOTS,
    "custom": RunType.REGENERATE,
    "different_angle": RunType.DIFFERENT_ANGLE,
}


def map_iteration_mode_to_run_type(mode: str) -> RunType:
    """
    Map legacy iteration mode string to RunType enum.

    Args:
        mode: Legacy mode string ('more_sources', 'deeper', etc.)

    Returns:
        Corresponding RunType
    """
    return ITERATION_MODE_TO_RUN_TYPE.get(mode, RunType.REGENERATE)


# Display labels for UI
RUN_TYPE_LABELS: dict[RunType, str] = {
    RunType.BASELINE: "Baseline",
    RunType.ADD_SOURCES: "Add Sources",
    RunType.FIX_WEAK_SPOTS: "Fix Weak Spots",
    RunType.COUNTERARGUMENT: "Counterargument",
    RunType.DIFFERENT_ANGLE: "Different Angle",
    RunType.REGENERATE: "Regenerate",
}


def get_run_type_label(run_type: RunType) -> str:
    """Get display label for run type."""
    return RUN_TYPE_LABELS.get(run_type, run_type.value)


# =============================================================================
# BACKWARD COMPATIBILITY SHIM
# =============================================================================

def ensure_runs_migrated(artifacts: Any, job_created_at: Optional[datetime] = None,
                          job_completed_at: Optional[datetime] = None,
                          user_id: str = "system") -> list["Run"]:
    """
    Ensure artifacts has runs[] populated by migrating legacy data if needed.

    This is the backward compatibility shim. It converts V1 artifacts (doc_*_path,
    iterations[]) to V2 runs[] without modifying the original data.

    Args:
        artifacts: Artifacts object (from job_record.py)
        job_created_at: Job creation timestamp (for baseline run)
        job_completed_at: Job completion timestamp (for baseline run)
        user_id: User ID for run requests

    Returns:
        List of Run objects (may be from artifacts.runs or migrated from legacy)
    """
    # If already has runs, return them
    if hasattr(artifacts, 'runs') and artifacts.runs:
        # Ensure they're Run objects
        runs = []
        for r in artifacts.runs:
            if isinstance(r, Run):
                runs.append(r)
            elif isinstance(r, dict):
                runs.append(Run(**r))
        return runs

    runs: list[Run] = []

    # Migrate baseline (run_0) from legacy doc_*_path
    has_baseline = (
        (hasattr(artifacts, 'doc_0_path') and artifacts.doc_0_path) or
        (hasattr(artifacts, 'doc_1_path') and artifacts.doc_1_path) or
        (hasattr(artifacts, 'doc_2_path') and artifacts.doc_2_path)
    )

    if has_baseline:
        # Create run_0 from legacy baseline
        run_0 = Run(
            run_id="run_0",
            run_index=0,
            run_type=RunType.BASELINE,
            parent_run_id=None,
            status=RunStatus.COMPLETED,
            request=RunRequest(requested_by=user_id),
            created_at=job_created_at or datetime.utcnow(),
            completed_at=job_completed_at,
            outputs=RunOutputs(
                doc_0_path=getattr(artifacts, 'doc_0_path', None),
                doc_1_path=getattr(artifacts, 'doc_1_path', None),
                doc_2_path=getattr(artifacts, 'doc_2_path', None),
            ),
        )

        # Migrate job-level producer to run_0
        if hasattr(artifacts, 'producer_packet') and artifacts.producer_packet:
            run_0.producer_packet = RunProducerPacket(
                status=RunStatus.COMPLETED,
                inline=artifacts.producer_packet,
                markdown=getattr(artifacts, 'producer_packet_md', None),
            )
        elif hasattr(artifacts, 'doc_3_path') and artifacts.doc_3_path:
            run_0.producer_packet = RunProducerPacket(
                status=RunStatus.COMPLETED,
                path=artifacts.doc_3_path,
                markdown=getattr(artifacts, 'producer_packet_md', None),
            )

        # Migrate job-level booster to run_0
        if hasattr(artifacts, 'booster_output') and artifacts.booster_output:
            run_0.booster_expansion = RunBoosterExpansion(
                status=RunStatus.COMPLETED,
                output=artifacts.booster_output,
                markdown=getattr(artifacts, 'booster_expansion_md', None),
            )

        runs.append(run_0)

    # Migrate legacy iterations to runs
    if hasattr(artifacts, 'iterations') and artifacts.iterations:
        for iteration in artifacts.iterations:
            # Handle both Iteration objects and dicts
            if isinstance(iteration, dict):
                it_id = iteration.get('iteration_id', f"it_{iteration.get('index', 1):04d}")
                it_index = iteration.get('index', 1)
                it_status = iteration.get('status', 'completed')
                it_created = iteration.get('created_at')
                it_started = iteration.get('started_at')
                it_completed = iteration.get('completed_at')
                it_request = iteration.get('request', {})
                it_outputs = iteration.get('outputs', {})
            else:
                it_id = iteration.iteration_id
                it_index = iteration.index
                it_status = iteration.status
                it_created = iteration.created_at
                it_started = iteration.started_at
                it_completed = iteration.completed_at
                it_request = iteration.request if hasattr(iteration, 'request') else {}
                it_outputs = iteration.outputs if hasattr(iteration, 'outputs') else {}

            # Parse request
            if isinstance(it_request, dict):
                mode = it_request.get('mode', 'custom')
                user_prompt = it_request.get('user_prompt', '')
            else:
                mode = getattr(it_request, 'mode', 'custom')
                user_prompt = getattr(it_request, 'user_prompt', '')

            # Map iteration mode to run type
            run_type = map_iteration_mode_to_run_type(mode)

            # Parse outputs
            if isinstance(it_outputs, dict):
                doc_0_path = it_outputs.get('doc_0_path')
                doc_1_path = it_outputs.get('doc_1_path')
                doc_2_path = it_outputs.get('doc_2_path')
                doc_0_inline = it_outputs.get('doc_0_inline')
                doc_1_inline = it_outputs.get('doc_1_inline')
                doc_2_inline = it_outputs.get('doc_2_inline')
            else:
                doc_0_path = getattr(it_outputs, 'doc_0_path', None)
                doc_1_path = getattr(it_outputs, 'doc_1_path', None)
                doc_2_path = getattr(it_outputs, 'doc_2_path', None)
                doc_0_inline = getattr(it_outputs, 'doc_0_inline', None)
                doc_1_inline = getattr(it_outputs, 'doc_1_inline', None)
                doc_2_inline = getattr(it_outputs, 'doc_2_inline', None)

            # Create run from iteration
            run = Run(
                run_id=f"run_{it_index}",
                run_index=it_index,
                run_type=run_type,
                parent_run_id=f"run_{it_index - 1}",
                status=RunStatus(it_status) if it_status in [s.value for s in RunStatus] else RunStatus.COMPLETED,
                request=RunRequest(
                    user_prompt=user_prompt,
                    requested_by=user_id,
                ),
                created_at=datetime.fromisoformat(it_created) if isinstance(it_created, str) else (it_created or datetime.utcnow()),
                started_at=datetime.fromisoformat(it_started) if isinstance(it_started, str) else it_started,
                completed_at=datetime.fromisoformat(it_completed) if isinstance(it_completed, str) else it_completed,
                outputs=RunOutputs(
                    doc_0_path=doc_0_path,
                    doc_1_path=doc_1_path,
                    doc_2_path=doc_2_path,
                    doc_0_inline=doc_0_inline,
                    doc_1_inline=doc_1_inline,
                    doc_2_inline=doc_2_inline,
                ) if any([doc_0_path, doc_1_path, doc_2_path, doc_0_inline, doc_1_inline, doc_2_inline]) else None,
            )

            runs.append(run)

    return runs


def create_baseline_run(
    user_id: str,
    created_at: Optional[datetime] = None,
) -> Run:
    """
    Create a new baseline run (run_0) for a job.

    Args:
        user_id: User who created the job
        created_at: Job creation time

    Returns:
        New Run object in QUEUED status
    """
    return Run(
        run_id="run_0",
        run_index=0,
        run_type=RunType.BASELINE,
        parent_run_id=None,
        status=RunStatus.QUEUED,
        request=RunRequest(requested_by=user_id),
        created_at=created_at or datetime.utcnow(),
    )


def create_iteration_run(
    parent_run: Run,
    run_type: RunType,
    request: RunRequest,
    run_index: Optional[int] = None,
) -> Run:
    """
    Create a new iteration run from a parent run.

    Args:
        parent_run: The parent run this iteration builds on
        run_type: Type of iteration
        request: Request parameters
        run_index: Explicit run index (defaults to parent + 1)

    Returns:
        New Run object in QUEUED status
    """
    index = run_index if run_index is not None else parent_run.run_index + 1

    return Run(
        run_id=f"run_{index}",
        run_index=index,
        run_type=run_type,
        parent_run_id=parent_run.run_id,
        status=RunStatus.QUEUED,
        request=request,
        created_at=datetime.utcnow(),
    )
