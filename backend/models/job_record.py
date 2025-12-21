"""Job record model for storage."""
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class Artifacts(BaseModel):
    """Artifacts associated with a job (Drive folder, docs, etc.)."""
    drive_folder_url: Optional[str] = Field(None, description="Google Drive folder URL")
    doc_urls: Optional[list[str]] = Field(None, description="List of Google Doc URLs")


class Outputs(BaseModel):
    """Research outputs as markdown files."""
    research_map_md: Optional[str] = Field(None, description="Research map markdown")
    source_shortlist_md: Optional[str] = Field(None, description="Source shortlist markdown")
    youtube_index_md: Optional[str] = Field(None, description="YouTube index markdown")
    quote_bank_md: Optional[str] = Field(None, description="Quote bank markdown")
    claims_ledger_md: Optional[str] = Field(None, description="Claims ledger markdown")
    evidence_table_md: Optional[str] = Field(None, description="Evidence table markdown")
    missing_angles_md: Optional[str] = Field(None, description="Missing angles markdown")


class JobRecord(BaseModel):
    """Complete job record for storage."""
    job_id: str = Field(..., description="Unique job identifier")
    user_id: Optional[str] = Field(None, description="User ID (from Supabase auth)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Job creation timestamp")
    status: str = Field(default="queued", description="Job status (queued, running, completed, failed)")
    stage: Optional[str] = Field(None, description="Current pipeline stage")
    progress_percent: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    config_json: dict[str, Any] = Field(default_factory=dict, description="Job configuration as JSON")
    warnings: list[str] = Field(default_factory=list, description="List of warnings encountered")
    artifacts: Artifacts = Field(default_factory=Artifacts, description="Job artifacts")
    outputs: Outputs = Field(default_factory=Outputs, description="Research outputs")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
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

