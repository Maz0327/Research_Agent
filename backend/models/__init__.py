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
from backend.models.semantic_units import SemanticExtractionResult
from backend.models.semantic_extraction_schema import SemanticExtractionSchema
from backend.models.booster_models import (
    ContextBundle,
    BoosterOutput,
    MissingPerspective,
    PrimarySourceDirection,
    PrimarySourceType,
    PlatformSuggestion,
    SearchQuery,
    ResearchQuestion,
    ThemeSummary,
    TensionSummary,
    GapSummary,
)
from backend.models.producer_models import (
    ProducerPacket,
    StoryCore,
    NarrativeAngle,
    OpeningHook,
    StructureOption,
    KeyMoment,
    TitleOption,
    ThumbnailConcept,
    RiskAssessment,
    InterviewSuggestions,
    InterviewCandidate,
    BRollSuggestion,
    HookType,
    StructureType,
    TitleTone,
    SensitivityLevel,
)

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
    # Semantic models
    "SemanticExtractionResult",
    "SemanticExtractionSchema",
    # Claim models
    "Claim",
    "ClaimType",
    "Citation",
    "EvidenceRecord",
    "EvidenceStatus",
    # Booster models (Phase 7)
    "ContextBundle",
    "BoosterOutput",
    "MissingPerspective",
    "PrimarySourceDirection",
    "PrimarySourceType",
    "PlatformSuggestion",
    "SearchQuery",
    "ResearchQuestion",
    "ThemeSummary",
    "TensionSummary",
    "GapSummary",
    # Producer models (Phase 8)
    "ProducerPacket",
    "StoryCore",
    "NarrativeAngle",
    "OpeningHook",
    "StructureOption",
    "KeyMoment",
    "TitleOption",
    "ThumbnailConcept",
    "RiskAssessment",
    "InterviewSuggestions",
    "InterviewCandidate",
    "BRollSuggestion",
    "HookType",
    "StructureType",
    "TitleTone",
    "SensitivityLevel",
]

