"""Pipeline context for research job execution."""
from dataclasses import dataclass, field
from typing import Optional

from backend.models.job_config import JobConfig


@dataclass
class PipelineContext:
    """
    Shared context passed through all pipeline stages.

    Holds all intermediate results and accumulates outputs/warnings.
    """
    # Input
    job_id: str
    topic: str
    slack_payload: Optional[dict] = None

    # Configuration (set in Stage 1)
    job_config: Optional[JobConfig] = None
    short_title: str = ""

    # Stage 2: Research mapping
    angles: list = field(default_factory=list)
    key_terms: list = field(default_factory=list)

    # Stage 3: Source shortlist
    web_sources: list = field(default_factory=list)

    # Stage 4: YouTube
    youtube_videos: list = field(default_factory=list)

    # Stage 5: Transcripts
    transcripts: list = field(default_factory=list)

    # Stage 6.5: Reddit
    reddit_posts: list = field(default_factory=list)

    # Stage 7: Claims
    claims: list = field(default_factory=list)

    # Stage 7.5: Timeline
    timeline_events: list = field(default_factory=list)

    # Stage 7.6: Entities
    entities: dict = field(default_factory=dict)

    # Stage 8: Validation
    evidence_records: list = field(default_factory=list)

    # Stage 8.5: Angle discovery
    discovered_angles: dict = field(default_factory=dict)

    # Stage 8.6: Documentary analysis
    documentary_analysis: dict = field(default_factory=dict)

    # Stage 9: Drive
    folder_url: Optional[str] = None
    doc_urls: dict = field(default_factory=dict)

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
