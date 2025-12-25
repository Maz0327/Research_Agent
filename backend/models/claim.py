"""Claim and evidence models."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    """Type of claim being made."""
    FACTUAL = "factual"
    OPINION = "opinion"
    PREDICTION = "prediction"
    ALLEGATION = "allegation"
    TIMELINE_EVENT = "timeline_event"


class EvidenceStatus(str, Enum):
    """Status of evidence validation for a claim."""
    VERIFIED = "Verified"
    DEBUNKED = "Debunked"
    UNPROVEN = "Unproven"


class Citation(BaseModel):
    """Citation pointing to a specific location in a source."""
    url: str = Field(..., description="URL of the source")
    locator: Optional[str] = Field(
        None,
        description="Specific location within the source (timestamp, page number, quote, etc.)",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "url": "https://www.youtube.com/watch?v=abc123",
                    "locator": "12:34",
                },
                {
                    "url": "https://example.com/article",
                    "locator": "Paragraph 3: 'She said that...'",
                },
            ]
        }


class Claim(BaseModel):
    """Canonical claim extracted from sources."""
    
    claim_id: str = Field(..., description="Unique identifier for the claim")
    canonical_claim: str = Field(
        ...,
        description="Normalized/canonical version of the claim statement",
    )
    verbatim_quote: Optional[str] = Field(
        None, description="Original verbatim quote if available"
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="List of citations supporting this claim",
    )
    claim_type: ClaimType = Field(..., description="Type of claim")
    entities: list[str] = Field(
        default_factory=list,
        description="Entities mentioned in the claim (people, organizations, places)",
    )
    confidence: float = Field(
        0.5, ge=0.0, le=1.0, description="Confidence score for claim extraction"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "claim_id": "claim_001",
                    "canonical_claim": "Candace Owens stated that Charlie Kirk made murder accusations",
                    "verbatim_quote": "Candace said 'Charlie accused him of murder'",
                    "citations": [
                        {
                            "url": "https://www.youtube.com/watch?v=abc123",
                            "locator": "15:42",
                        }
                    ],
                    "claim_type": "allegation",
                    "entities": ["Candace Owens", "Charlie Kirk"],
                    "confidence": 0.85,
                },
                {
                    "claim_id": "claim_002",
                    "canonical_claim": "The event occurred on March 15, 2024",
                    "verbatim_quote": "This happened on March 15th",
                    "citations": [
                        {
                            "url": "https://example.com/news",
                            "locator": "Opening paragraph",
                        }
                    ],
                    "claim_type": "timeline_event",
                    "entities": [],
                    "confidence": 0.95,
                },
            ]
        }


class EvidenceRecord(BaseModel):
    """Evidence validation record for a claim."""
    
    claim_id: str = Field(..., description="ID of the claim this evidence relates to")
    status: EvidenceStatus = Field(
        ..., description="Overall validation status of the claim"
    )
    evidence_for: list[Citation] = Field(
        default_factory=list,
        description="Citations that support/verify the claim",
    )
    evidence_against: list[Citation] = Field(
        default_factory=list,
        description="Citations that contradict/debunk the claim",
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the evidence evaluation"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "claim_id": "claim_001",
                    "status": "Unproven",
                    "evidence_for": [
                        {
                            "url": "https://www.youtube.com/watch?v=abc123",
                            "locator": "15:42",
                        }
                    ],
                    "evidence_against": [],
                    "notes": "Claim mentioned but no independent verification found",
                },
                {
                    "claim_id": "claim_002",
                    "status": "Verified",
                    "evidence_for": [
                        {
                            "url": "https://example.com/official-report",
                            "locator": "Section 3.2",
                        },
                        {
                            "url": "https://news.example.com/article",
                            "locator": "Paragraph 2",
                        },
                    ],
                    "evidence_against": [],
                    "notes": "Multiple independent sources confirm this timeline",
                },
                {
                    "claim_id": "claim_003",
                    "status": "Debunked",
                    "evidence_for": [],
                    "evidence_against": [
                        {
                            "url": "https://factcheck.example.com/debunk",
                            "locator": "Conclusion section",
                        },
                        {
                            "url": "https://official-source.gov/correction",
                            "locator": "Press release dated 2024-03-20",
                        },
                    ],
                    "notes": "Claim has been officially corrected by multiple authoritative sources",
                },
            ]
        }

