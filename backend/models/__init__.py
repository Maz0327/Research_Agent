"""Pydantic models for the Research Agent."""
from backend.models.claim import (
    Citation,
    Claim,
    ClaimType,
    EvidenceRecord,
    EvidenceStatus,
)
from backend.models.job import CreateJobRequest, JobStatus, JobStatusResponse
from backend.models.job_record import Artifacts, JobRecord, Outputs
from backend.models.job_config import (
    BudgetsConfig,
    JobConfig,
    OutputConfig,
    ResearchMode,
    SourcesConfig,
    TimeWindow,
    YouTubeConfig,
)
from backend.models.source import SourceItem, SourceType

__all__ = [
    # Job models
    "JobStatus",
    "CreateJobRequest",
    "JobStatusResponse",
    # Job record models
    "JobRecord",
    "Artifacts",
    "Outputs",
    # Job config models
    "JobConfig",
    "ResearchMode",
    "TimeWindow",
    "YouTubeConfig",
    "SourcesConfig",
    "BudgetsConfig",
    "OutputConfig",
    # Source models
    "SourceItem",
    "SourceType",
    # Claim models
    "Claim",
    "ClaimType",
    "Citation",
    "EvidenceRecord",
    "EvidenceStatus",
]

