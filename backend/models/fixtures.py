"""Test fixtures and example data for models."""
from datetime import date, datetime

from backend.models.claim import Claim, Citation, ClaimType, EvidenceRecord, EvidenceStatus
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


# Example JobConfig with small budgets for testing
EXAMPLE_JOB_CONFIG = JobConfig(
    mode=ResearchMode.CLAIMS_EVIDENCE,
    topic="Test research topic",
    time_window=TimeWindow(
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
    ),
    youtube=YouTubeConfig(
        channels=["@candaceowens"],  # Known channel for testing
        include_livestreams=True,
        exclude_shorts=True,
        max_videos=5,  # Small budget for testing
        fetch_transcripts=True,
    ),
    sources=SourcesConfig(
        web=True,
        include_reddit_public=False,
        include_news=True,
        include_academic=False,
        include_gov=False,
    ),
    budgets=BudgetsConfig(
        max_web_urls=10,  # Small budget for testing
        max_transcription_minutes=30,  # Small budget for testing
        max_claims_to_validate=10,  # Small budget for testing
        max_validation_links_per_claim=3,  # Small budget for testing
    ),
    output=OutputConfig(
        drive_folder_name="Test Research Packet",
    ),
)


# Minimal JobConfig for quick testing (even smaller budgets)
MINIMAL_JOB_CONFIG = JobConfig(
    mode=ResearchMode.CLAIMS_EVIDENCE,
    topic="Quick test topic",
    time_window=TimeWindow(),
    youtube=YouTubeConfig(
        channels=["@candaceowens"],
        include_livestreams=False,
        exclude_shorts=True,
        max_videos=2,  # Very small
        fetch_transcripts=True,
    ),
    sources=SourcesConfig(
        web=True,
        include_news=True,
        include_reddit_public=False,
        include_academic=False,
        include_gov=False,
    ),
    budgets=BudgetsConfig(
        max_web_urls=5,  # Very small
        max_transcription_minutes=15,  # Very small
        max_claims_to_validate=5,  # Very small
        max_validation_links_per_claim=2,  # Very small
    ),
    output=OutputConfig(
        drive_folder_name="Quick Test Packet",
    ),
)


# Example SourceItem
EXAMPLE_SOURCE_ITEM = SourceItem(
    url="https://example.com/article",
    title="Example Article Title",
    source_type=SourceType.WEB,
    published_at=datetime(2024, 3, 15, 14, 30, 0),
    text="This is example article content that would be extracted from the web page.",
    notes="Example source notes",
    angle="neutral",
)


# Example Claim
EXAMPLE_CLAIM = Claim(
    claim_id="claim_001",
    canonical_claim="Example canonical claim statement",
    verbatim_quote="Original verbatim quote from source",
    citations=[
        Citation(
            url="https://example.com/article",
            locator="Paragraph 3",
        )
    ],
    claim_type=ClaimType.FACTUAL,
    entities=["Entity 1", "Entity 2"],
    confidence=0.85,
)


# Example EvidenceRecord
EXAMPLE_EVIDENCE_RECORD = EvidenceRecord(
    claim_id="claim_001",
    status=EvidenceStatus.VERIFIED,
    evidence_for=[
        Citation(
            url="https://example.com/verify",
            locator="Section 2.1",
        )
    ],
    evidence_against=[],
    notes="Evidence record notes",
)


# Test Slack text examples
TEST_SLACK_TEXTS = [
    "Research Candace Owens claims about Charlie Kirk",
    "Check @candaceowens latest livestreams about Charlie Kirk since September",
    "Research topic about X, check @candaceowens videos from last month",
    "Quick test research",
]


# Known test channels (these should work if API key is configured)
KNOWN_TEST_CHANNELS = [
    "@candaceowens",  # Candace Owens channel
    "@charliekirk",  # Charlie Kirk channel
    # Add more known channels as needed
]
