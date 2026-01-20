"""Job record model for storage."""
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class Artifacts(BaseModel):
    """Artifacts associated with a job.

    Updated: 2026-01-19 - Drive fields deprecated, Supabase Storage is primary.
    """
    # =========================================================================
    # DEPRECATED (2026-01-19 - Drive integration removed)
    # =========================================================================
    drive_folder_url: Optional[str] = Field(
        None, description="DEPRECATED: Google Drive folder URL (Drive removed)"
    )
    doc_urls: Optional[list[str]] = Field(
        None, description="DEPRECATED: List of Google Doc URLs (Drive removed)"
    )

    # =========================================================================
    # SEMANTIC PIPELINE (Active) - Doc 0/1/2/3
    # =========================================================================
    # Inline document data (backward compatible with existing jobs)
    source_ledger: Optional[dict[str, Any]] = Field(None, description="Doc 0 - Source Ledger (inline)")
    jump_start: Optional[dict[str, Any]] = Field(None, description="Doc 1 - Jump-Start Directions (inline)")
    semantic_brief: Optional[dict[str, Any]] = Field(None, description="Doc 2 - Semantic Research Brief (inline)")
    semantic_extractions: Optional[list[dict[str, Any]]] = Field(None, description="Per-source extractions")

    # Storage paths for new jobs (added 260117 - lazy loading support)
    # When present, frontend fetches docs via API instead of inline data
    doc_0_path: Optional[str] = Field(None, description="Storage path for Source Ledger (new jobs)")
    doc_1_path: Optional[str] = Field(None, description="Storage path for Jump-Start (new jobs)")
    doc_2_path: Optional[str] = Field(None, description="Storage path for Semantic Brief (new jobs)")
    doc_3_path: Optional[str] = Field(None, description="Storage path for Producer Packet (new jobs)")

    # Artifact Manifest (Option B storage strategy - 2026-01-19)
    # Provides manifest-first UI with lazy loading for docs and attachments
    artifact_manifest: Optional[dict[str, Any]] = Field(
        None, description="Manifest of available artifacts with storage paths"
    )

    # Booster (Phase 7)
    booster_output: Optional[dict[str, Any]] = Field(None, description="Booster output for Doc 1 expansion")
    booster_expansion_md: Optional[str] = Field(None, description="Booster markdown for Doc 1")

    # Producer Packet (Phase 8 - Doc 3)
    producer_packet: Optional[dict[str, Any]] = Field(None, description="Doc 3 - Producer Packet (inline, legacy)")
    producer_packet_md: Optional[str] = Field(None, description="Doc 3 markdown output")

    # =========================================================================
    # LEGACY (Deprecated per D5 - 2026-01-17)
    # Fields preserved for backward compatibility but NOT populated by
    # new jobs. Legacy pipeline stages (7-8.6) are completely disabled.
    # =========================================================================
    # Video analysis artifacts (Legacy Gemini pivot - run_gemini_video_job only)
    clips: Optional[list[dict[str, Any]]] = Field(
        None, description="DEPRECATED: Legacy extracted video clips (D5)"
    )
    quotes: Optional[list[dict[str, Any]]] = Field(
        None, description="DEPRECATED: Legacy extracted quotes (D5)"
    )
    quality_gate_passed: Optional[bool] = Field(
        None, description="DEPRECATED: Legacy ProducerPacket quality gate (D5)"
    )

    # Legacy Phase 3: Full Research Assistant Pipeline (Jan 2026)
    # These were from the old 4-pass Gemini pipeline, now replaced by semantic pipeline
    content_blueprints: Optional[list[dict[str, Any]]] = Field(
        None, description="DEPRECATED: Legacy ContentBlueprint per video (D5)"
    )
    gap_analysis: Optional[dict[str, Any]] = Field(
        None, description="DEPRECATED: Legacy GapAnalysis (D5)"
    )
    research_starter: Optional[dict[str, Any]] = Field(
        None, description="DEPRECATED: Legacy ResearchStarter (D5)"
    )


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

    # Status and progress
    status: str = Field(default="queued", description="Job status (queued, running, disambiguating, completed, failed, cancelled)")
    stage: Optional[str] = Field(None, description="Current pipeline stage")
    progress_percent: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    error: Optional[str] = Field(None, description="Error message if job failed")
    warnings: list[str] = Field(default_factory=list, description="List of warnings encountered")

    # Configuration
    config_json: dict[str, Any] = Field(default_factory=dict, description="Job configuration as JSON")
    manual_guidance: Optional[dict[str, Any]] = Field(None, description="Manual guidance/overrides")

    # Disambiguation - DEPRECATED (2026-01-19 - Legacy pipeline removed)
    interpretations: Optional[list[dict[str, Any]]] = Field(
        None, description="DEPRECATED: Possible topic interpretations (legacy pipeline)"
    )
    selected_interpretations: Optional[list[int]] = Field(
        None, description="DEPRECATED: Indices of user-selected interpretations (legacy)"
    )

    # Extracted data
    timeline_events: Optional[list[dict[str, Any]]] = Field(None, description="Extracted timeline events")
    entities: Optional[dict[str, Any]] = Field(None, description="Extracted entities (people, orgs, etc.)")
    reddit_posts: Optional[list[dict[str, Any]]] = Field(None, description="Collected Reddit posts")

    # Angle discovery
    discovered_angles: Optional[list[dict[str, Any]]] = Field(None, description="Discovered angles/perspectives")
    coverage_analysis: Optional[dict[str, Any]] = Field(None, description="Topic coverage analysis")
    recommended_angle: Optional[dict[str, Any]] = Field(None, description="AI-recommended angle")

    # Quality gate
    quality_gate_stats: Optional[dict[str, Any]] = Field(None, description="Quality gate filtering stats")

    # Metrics
    total_sources: Optional[int] = Field(None, description="Total sources collected")
    total_claims: Optional[int] = Field(None, description="Total claims extracted")
    api_costs: Optional[dict[str, Any]] = Field(None, description="API costs per service")

    # Output URLs - DEPRECATED (2026-01-19 - Drive integration removed)
    notebooklm_packet_url: Optional[str] = Field(
        None, description="DEPRECATED: NotebookLM packet Google Doc URL (Drive removed)"
    )
    documentary_blueprint_url: Optional[str] = Field(
        None, description="DEPRECATED: Documentary blueprint Google Doc URL (Drive removed)"
    )

    # Artifacts and outputs
    artifacts: Optional[Artifacts] = Field(None, description="Job artifacts")
    outputs: Optional[Outputs] = Field(None, description="Research outputs")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "pipeline": "investigation",
                "created_at": "2024-01-15T10:30:00Z",
                "status": "running",
                "stage": "gathering_sources",
                "progress_percent": 45,
                "config_json": {
                    "mode": "claims_evidence",
                    "topic": "Test topic",
                },
                "warnings": ["Some sources failed to fetch"],
                "artifacts": {
                    "drive_folder_url": "https://drive.google.com/folders/abc123",
                    "doc_urls": [],
                },
                "outputs": {
                    "research_map_md": "# Research Map\n...",
                    "source_shortlist_md": None,
                },
            }
        }
