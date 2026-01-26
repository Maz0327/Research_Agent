"""Job record model for storage."""
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.models.run_models import Run


# =============================================================================
# ITERATION DATA MODELS
# =============================================================================

class IterationRequest(BaseModel):
    """Request parameters for an iteration."""
    mode: str = Field(..., description="Iteration mode: more_sources, deeper, different_angle, custom")
    user_prompt: str = Field(default="", description="User prompt for iteration")
    target: str = Field(default="semantic_docs", description="Target for iteration (semantic_docs only for now)")
    max_new_sources: int = Field(default=4, ge=0, le=10, description="Max new sources to add")
    angle: Optional[str] = Field(None, description="Specific angle to explore")
    constraints: dict[str, Any] = Field(default_factory=lambda: {"keep_doc0_schema": True})


class IterationInputs(BaseModel):
    """Inputs captured at iteration start."""
    baseline_doc_0_path: Optional[str] = Field(None, description="Baseline Doc 0 storage path")
    baseline_doc_1_path: Optional[str] = Field(None, description="Baseline Doc 1 storage path")
    baseline_doc_2_path: Optional[str] = Field(None, description="Baseline Doc 2 storage path")
    baseline_sources_hash: Optional[str] = Field(None, description="Hash of baseline sources for delta detection")
    source_urls_added: list[str] = Field(default_factory=list, description="URLs added in this iteration")
    source_urls_used: list[str] = Field(default_factory=list, description="All URLs used (baseline + added)")


class IterationOutputs(BaseModel):
    """Outputs produced by an iteration."""
    doc_0_path: Optional[str] = Field(None, description="Iteration Doc 0 storage path")
    doc_1_path: Optional[str] = Field(None, description="Iteration Doc 1 storage path")
    doc_2_path: Optional[str] = Field(None, description="Iteration Doc 2 storage path")
    doc_0_inline: Optional[dict[str, Any]] = Field(None, description="Doc 0 inline data (fallback)")
    doc_1_inline: Optional[dict[str, Any]] = Field(None, description="Doc 1 inline data (fallback)")
    doc_2_inline: Optional[dict[str, Any]] = Field(None, description="Doc 2 inline data (fallback)")


class IterationMetrics(BaseModel):
    """Metrics for an iteration."""
    llm_calls: int = Field(default=0, description="Number of LLM calls")
    tokens_in: int = Field(default=0, description="Total input tokens")
    tokens_out: int = Field(default=0, description="Total output tokens")
    wall_time_ms: int = Field(default=0, description="Wall clock time in milliseconds")


class IterationError(BaseModel):
    """Error information for a failed iteration."""
    message: str = Field(..., description="Error message")
    stack: Optional[str] = Field(None, description="Stack trace")


class Iteration(BaseModel):
    """A single iteration in the iteration loop.

    Each iteration produces a new set of doc_0/doc_1/doc_2 WITHOUT modifying baseline.
    """
    iteration_id: str = Field(..., description="Stable iteration ID (it_0001, it_0002, ...)")
    index: int = Field(..., ge=1, description="1-based iteration index")
    created_at: str = Field(..., description="ISO8601 timestamp when iteration was created")
    started_at: Optional[str] = Field(None, description="ISO8601 timestamp when iteration started running")
    completed_at: Optional[str] = Field(None, description="ISO8601 timestamp when iteration completed/failed")
    status: str = Field(default="queued", description="Status: queued, running, completed, failed")
    error: Optional[IterationError] = Field(None, description="Error info if failed")

    request: IterationRequest = Field(..., description="Request parameters")
    inputs: IterationInputs = Field(default_factory=IterationInputs, description="Captured inputs")
    outputs: IterationOutputs = Field(default_factory=IterationOutputs, description="Produced outputs")
    metrics: IterationMetrics = Field(default_factory=IterationMetrics, description="Execution metrics")


class Artifacts(BaseModel):
    """Artifacts associated with a job.

    Updated: 2026-01-25 - Added runs[] for unified run abstraction.

    V2 Architecture (runs):
    - All outputs are organized under runs[]
    - run_0 is always the baseline
    - run_1+ are iterations/regenerations
    - Producer/Booster are scoped to individual runs

    V1 Architecture (legacy, deprecated):
    - doc_*_path for baseline
    - iterations[] for iterations
    - Job-level producer_packet and booster_output
    """
    # =========================================================================
    # V2: RUN-BASED STORAGE (preferred)
    # =========================================================================
    # Import Run at runtime to avoid circular imports
    runs: list[Any] = Field(
        default_factory=list,
        description="All runs (baseline + iterations). Type: list[Run]"
    )

    # =========================================================================
    # V1 LEGACY: SEMANTIC PIPELINE - Doc 0/1/2/3
    # DEPRECATED: Use runs[0].outputs instead for new code
    # =========================================================================
    # Inline document data (for backward compatibility with existing jobs)
    source_ledger: Optional[dict[str, Any]] = Field(None, description="Doc 0 - Source Ledger (inline)")
    jump_start: Optional[dict[str, Any]] = Field(None, description="Doc 1 - Jump-Start Directions (inline)")
    semantic_brief: Optional[dict[str, Any]] = Field(None, description="Doc 2 - Semantic Research Brief (inline)")
    semantic_extractions: Optional[list[dict[str, Any]]] = Field(None, description="Per-source extractions")

    # Storage paths (lazy loading - frontend fetches via API)
    doc_0_path: Optional[str] = Field(None, description="Storage path for Source Ledger")
    doc_1_path: Optional[str] = Field(None, description="Storage path for Jump-Start")
    doc_2_path: Optional[str] = Field(None, description="Storage path for Semantic Brief")
    doc_3_path: Optional[str] = Field(None, description="Storage path for Producer Packet")

    # Artifact Manifest (Option B storage strategy)
    artifact_manifest: Optional[dict[str, Any]] = Field(
        None, description="Manifest of available artifacts with storage paths"
    )

    # V1 LEGACY: Booster (Doc 1 expansion) - DEPRECATED: Use runs[n].booster_expansion
    booster_output: Optional[dict[str, Any]] = Field(None, description="Booster output for Doc 1 expansion")
    booster_expansion_md: Optional[str] = Field(None, description="Booster markdown for Doc 1")

    # V1 LEGACY: Producer Packet (Doc 3) - DEPRECATED: Use runs[n].producer_packet
    producer_packet: Optional[dict[str, Any]] = Field(None, description="Doc 3 - Producer Packet (inline)")
    producer_packet_md: Optional[str] = Field(None, description="Doc 3 markdown output")

    # =========================================================================
    # V1 LEGACY: ITERATIONS - DEPRECATED: Use runs[1:] instead
    # =========================================================================
    # Each iteration produces new doc_0/doc_1/doc_2 WITHOUT modifying baseline.
    # IMPORTANT: Never overwrite baseline doc_*_path keys - iterations are ADDITIVE.
    iterations: list[Iteration] = Field(default_factory=list, description="Iteration history (append-only)")

    # =========================================================================
    # SHARED DATA (used across all runs)
    # =========================================================================
    video_metadata: Optional[dict[str, Any]] = Field(None, description="Video metadata from Supadata")
    source_identity_packages: Optional[list[dict[str, Any]]] = Field(None, description="Source identity packages")

    # =========================================================================
    # V2 HELPER METHODS
    # =========================================================================
    def get_run(self, run_id: str) -> Optional[Any]:
        """Get a run by ID."""
        for run in self.runs:
            if hasattr(run, 'run_id') and run.run_id == run_id:
                return run
            elif isinstance(run, dict) and run.get('run_id') == run_id:
                return run
        return None

    def get_baseline_run(self) -> Optional[Any]:
        """Get the baseline run (run_0)."""
        return self.get_run("run_0")

    def get_latest_completed_run(self) -> Optional[Any]:
        """Get the most recent completed run."""
        completed = []
        for run in self.runs:
            if hasattr(run, 'status'):
                if run.status == "completed":
                    completed.append(run)
            elif isinstance(run, dict) and run.get('status') == "completed":
                completed.append(run)

        if not completed:
            return None

        # Sort by run_index and return highest
        return max(completed, key=lambda r: r.run_index if hasattr(r, 'run_index') else r.get('run_index', 0))

    def has_runs(self) -> bool:
        """Check if job uses V2 run-based storage."""
        return len(self.runs) > 0


class Outputs(BaseModel):
    """Research outputs as markdown files."""
    research_map_md: Optional[str] = Field(None, description="Research map markdown")
    source_shortlist_md: Optional[str] = Field(None, description="Source shortlist markdown")
    youtube_index_md: Optional[str] = Field(None, description="YouTube index markdown")
    quote_bank_md: Optional[str] = Field(None, description="Quote bank markdown")
    claims_ledger_md: Optional[str] = Field(None, description="Claims ledger markdown")
    evidence_table_md: Optional[str] = Field(None, description="Evidence table markdown")
    missing_angles_md: Optional[str] = Field(None, description="Missing angles markdown")
    timeline_md: Optional[str] = Field(None, description="Timeline markdown")
    entities_md: Optional[str] = Field(None, description="Entities markdown")
    reddit_discussions_md: Optional[str] = Field(None, description="Reddit discussions markdown")


class QualityGateStats(BaseModel):
    """Quality gate statistics for source filtering."""
    total_sources: Optional[int] = Field(None, description="Total sources before filtering")
    passed_sources: Optional[int] = Field(None, description="Sources that passed quality gate")
    filtered_sources: Optional[int] = Field(None, description="Sources filtered out")
    filter_reasons: Optional[dict[str, int]] = Field(None, description="Count of each filter reason")


class AngleInfo(BaseModel):
    """Information about a discovered angle."""
    angle_name: Optional[str] = Field(None, description="Name of the angle")
    description: Optional[str] = Field(None, description="Description of the angle")
    confidence: Optional[float] = Field(None, description="Confidence score 0-1")
    supporting_sources: Optional[list[str]] = Field(None, description="URLs supporting this angle")


class CoverageAnalysis(BaseModel):
    """Analysis of topic coverage."""
    covered_aspects: Optional[list[str]] = Field(None, description="Aspects with good coverage")
    missing_aspects: Optional[list[str]] = Field(None, description="Aspects needing more research")
    coverage_score: Optional[float] = Field(None, description="Overall coverage score 0-1")


class ApiCosts(BaseModel):
    """API cost tracking per service."""
    openai: Optional[float] = Field(None, description="OpenAI API costs in USD")
    perplexity: Optional[float] = Field(None, description="Perplexity API costs in USD")
    tavily: Optional[float] = Field(None, description="Tavily API costs/credits")
    whisper: Optional[float] = Field(None, description="Whisper API costs in USD")
    supadata: Optional[float] = Field(None, description="Supadata API credits")
    gemini: Optional[float] = Field(None, description="Gemini API costs in USD")
    total: Optional[float] = Field(None, description="Total costs in USD")


class JobRecord(BaseModel):
    """Complete job record for storage.

    This model corresponds to the 'jobs' table in the database.
    All fields are kept in sync with database migrations.
    """
    # Core identifiers
    job_id: str = Field(..., description="Unique job identifier")
    user_id: Optional[str] = Field(None, description="User ID (from Supabase auth)")
    title: Optional[str] = Field(None, description="AI-generated short title for the job")
    pipeline: str = Field(default="investigation", description="Pipeline mode")
    niche: Optional[str] = Field(None, description="Niche overlay applied to job")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Job creation timestamp")
    stage_started_at: Optional[datetime] = Field(None, description="When current stage started")

    # Status and progress (main pipeline)
    status: str = Field(default="queued", description="Job status (queued, running, disambiguating, completed, failed, cancelled)")
    stage: Optional[str] = Field(None, description="Current pipeline stage")
    progress_percent: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    error: Optional[str] = Field(None, description="Error message if job failed")
    warnings: list[str] = Field(default_factory=list, description="List of warnings encountered")

    # Booster tracking (separate from main pipeline status)
    # IMPORTANT: Booster must NEVER modify jobs.status - these fields track booster independently
    booster_status: Optional[str] = Field(None, description="Booster status: queued, running, completed, failed")
    booster_started_at: Optional[datetime] = Field(None, description="When booster started")
    booster_completed_at: Optional[datetime] = Field(None, description="When booster completed/failed")
    booster_error: Optional[str] = Field(None, description="Booster error message if failed")
    booster_progress_percent: Optional[int] = Field(None, ge=0, le=100, description="Booster progress (0-100)")

    # Producer tracking (separate from main pipeline status)
    # IMPORTANT: Producer must NEVER modify jobs.status - these fields track producer independently
    producer_status: Optional[str] = Field(None, description="Producer status: queued, running, completed, failed")
    producer_started_at: Optional[datetime] = Field(None, description="When producer started")
    producer_completed_at: Optional[datetime] = Field(None, description="When producer completed/failed")
    producer_error: Optional[str] = Field(None, description="Producer error message if failed")
    producer_progress_percent: Optional[int] = Field(None, ge=0, le=100, description="Producer progress (0-100)")

    # Iteration tracking (separate from main pipeline status)
    # IMPORTANT: Iteration must NEVER modify jobs.status - these fields track iteration independently
    iteration_status: Optional[str] = Field(None, description="Current iteration status: queued, running, completed, failed")
    iteration_id: Optional[str] = Field(None, description="Current iteration ID being processed (it_0001, ...)")
    iteration_started_at: Optional[datetime] = Field(None, description="When current iteration started")
    iteration_completed_at: Optional[datetime] = Field(None, description="When current iteration completed/failed")
    iteration_error: Optional[str] = Field(None, description="Current iteration error message if failed")
    iteration_progress_percent: Optional[int] = Field(None, ge=0, le=100, description="Current iteration progress (0-100)")

    # Configuration
    config_json: dict[str, Any] = Field(default_factory=dict, description="Job configuration as JSON")

    # Metrics
    total_sources: Optional[int] = Field(None, description="Total sources collected")
    total_claims: Optional[int] = Field(None, description="Total claims extracted")
    api_costs: Optional[dict[str, Any]] = Field(None, description="API costs per service")

    # Artifacts and outputs
    artifacts: Optional[Artifacts] = Field(None, description="Job artifacts")
    outputs: Optional[Outputs] = Field(None, description="Research outputs")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "pipeline": "semantic",
                "created_at": "2026-01-21T10:30:00Z",
                "status": "completed",
                "stage": "completed",
                "progress_percent": 100,
                "config_json": {
                    "topic": "Test topic",
                    "sources": [],
                },
                "warnings": [],
                "artifacts": {
                    "doc_0_path": "documents/550e8400/doc_0.json",
                    "doc_1_path": "documents/550e8400/doc_1.json",
                    "doc_2_path": "documents/550e8400/doc_2.json",
                },
                "outputs": {},
            }
        }
