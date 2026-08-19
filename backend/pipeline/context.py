"""Pipeline context for research job execution."""
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from backend.models.job_config import JobConfig

if TYPE_CHECKING:
    from backend.pipeline.cost_tracker import CostTracker


@dataclass
class PipelineContext:
    """
    Shared context passed through all pipeline stages.

    Updated 2026-01-19: Legacy fields removed (Slack, discovery stages).
    Only semantic pipeline fields are active.

    Holds all intermediate results and accumulates outputs/warnings.
    """
    # Input
    job_id: str
    topic: str
    # NOTE: slack_payload removed (2026-01-19 - Slack integration removed)

    # Configuration (set in Stage 1)
    job_config: Optional[JobConfig] = None
    short_title: str = ""

    # Disambiguation (set when processing multiple interpretations)
    interpretation_index: Optional[int] = None  # 1-based index (1, 2, 3...)
    interpretation_label: Optional[str] = None  # Short label like "Barney & Friends"

    # Cost tracking (initialized in Stage 0)
    cost_tracker: Optional["CostTracker"] = None

    # Niche configuration (set in Stage 1 if niche specified)
    # Default to empty dict to prevent NoneType errors in downstream stages
    niche_config: dict = field(default_factory=dict)

    # Legacy source collection fields (still referenced by source_identity.py, semantic_validation_stage.py)
    web_sources: list = field(default_factory=list)
    youtube_videos: list = field(default_factory=list)
    transcripts: list = field(default_factory=list)
    reddit_posts: list = field(default_factory=list)

    # NOTE: Dead legacy fields removed (Audit Fix 9.1, 2026-03-12):
    # angles, key_terms, claims, timeline_events, entities,
    # evidence_records, discovered_angles, documentary_analysis

    # Semantic Pipeline (Phase 1)
    # Source Identity stage outputs
    source_identity_packages: list = field(default_factory=list)
    # Semantic Extraction stage outputs
    semantic_extractions: list = field(default_factory=list)
    # Gap Analysis outputs
    identified_gaps: list = field(default_factory=list)
    # Scope Lock
    scope_in: list = field(default_factory=list)
    scope_out: list = field(default_factory=list)
    # Document Assembly outputs (Doc 0/1/2)
    source_ledger: dict = field(default_factory=dict)
    jump_start: dict = field(default_factory=dict)
    semantic_brief: dict = field(default_factory=dict)

    # Semantic Synthesis outputs (Phase 2A)
    semantic_core: str = ""  # 2-4 sentence core from synthesis
    semantic_core_based_on: list = field(default_factory=list)  # KeyPoint IDs
    synthesized_themes: list = field(default_factory=list)  # Theme objects
    speculative_observations: list = field(default_factory=list)  # Labeled speculation
    confidence_reasoning: list = field(default_factory=list)  # Reasons for confidence level
    overall_confidence: Optional[str] = None  # "high", "medium", "low"

    # Claim Graph (distillation stage) — the canonical layer every downstream
    # document projects from. Typed as object to avoid a circular import.
    claim_graph: Optional[object] = None

    # Phase 2B: Extended Inputs
    ocr_result: Optional[object] = None  # OCRResult from screenshot extraction
    job_config_dict: dict = field(default_factory=dict)  # Raw config dict from job

    # Phase 4: Validation Stage
    verification_rate: float = 0.0  # Fraction of quotes verified (0.0 to 1.0)
    validation_warnings: list = field(default_factory=list)  # Validation warning messages
    source_durations: dict = field(default_factory=dict)  # source_id → duration_seconds
    source_metadata: dict = field(default_factory=dict)  # source_id → metadata dict

    # Phase 5: Multi-Source Tracking
    source_coverage: dict = field(default_factory=dict)  # claim_id → [source_ids] that support it
    cross_source_conflicts: list = field(default_factory=list)  # Detected cross-source conflicts
    duplicate_sources: dict = field(default_factory=dict)  # duplicate source_id → canonical source_id
    duplicate_source_report: list = field(default_factory=list)  # detected syndication pairs + scores
    theme_merges: list = field(default_factory=list)  # themes merged as restatements of each other
    injection_flags: dict = field(default_factory=dict)  # source_id → model-addressed text found in it
    harvest: dict = field(default_factory=dict)  # source_id → dense fact statements
    harvest_inventory: list = field(default_factory=list)  # flat facts with IDs, the coverage-gate input
    briefing: Optional[object] = None  # the generated Research Briefing (D-025)
    briefing_report: dict = field(default_factory=dict)  # coverage + grounding gate results
    source_contributions: dict = field(default_factory=dict)  # source_id → {key_points: n, themes: n, ...}

    # Phase 6: Evolving Jobs (Add Sources to Completed Jobs)
    is_evolving_job: bool = False  # True when processing pending sources
    original_extractions: list = field(default_factory=list)  # Extractions from original job
    pending_source_ids: list = field(default_factory=list)  # Source IDs being processed
    addendum_sections: Optional[object] = None  # AddendumSection with new content
    cross_reference_notes: Optional[object] = None  # CrossReferenceNotes comparing old/new

    # NOTE: folder_url, doc_urls removed (Audit Fix 9.1 — Google Drive integration removed)

    # Quality Gate stats (set after Stage 3)
    quality_gate_stats: Optional[dict] = None

    # Accumulated outputs (markdown documents)
    outputs: dict = field(default_factory=dict)

    # Accumulated warnings
    warnings: list = field(default_factory=list)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def set_output(self, key: str, value: str) -> None:
        """Set an output markdown document."""
        self.outputs[key] = value

    def add_cost(self, api_name: str, amount: float, units: int = 1) -> None:
        """Track cost for an API call."""
        if self.cost_tracker:
            self.cost_tracker.add_cost(api_name, amount, units)

    def get_cost_summary(self) -> dict:
        """Get cost tracking summary."""
        if self.cost_tracker:
            return self.cost_tracker.get_summary()
        return {}
