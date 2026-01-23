"""Job record model for storage."""
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class Artifacts(BaseModel):
    """Artifacts associated with a job.

    Updated: 2026-01-21 - Removed all legacy/deprecated fields.
    """
    # =========================================================================
    # SEMANTIC PIPELINE - Doc 0/1/2/3
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

    # Booster (Doc 1 expansion)
    booster_output: Optional[dict[str, Any]] = Field(None, description="Booster output for Doc 1 expansion")
    booster_expansion_md: Optional[str] = Field(None, description="Booster markdown for Doc 1")

    # Producer Packet (Doc 3)
    producer_packet: Optional[dict[str, Any]] = Field(None, description="Doc 3 - Producer Packet (inline)")
    producer_packet_md: Optional[str] = Field(None, description="Doc 3 markdown output")


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
