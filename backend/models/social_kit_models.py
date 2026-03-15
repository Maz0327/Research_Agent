"""Social Media Kit (Doc 6) data models.

Multi-platform social media content generated from research.
Each platform has specific format constraints.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class TweetItem(BaseModel):
    """A single tweet in a Twitter thread."""
    tweet_number: int = Field(..., ge=1)
    text: str = Field(..., max_length=280, description="Tweet text, max 280 chars")
    claim_ids: list[str] = Field(default_factory=list)


class TimestampEntry(BaseModel):
    """A timestamp entry for YouTube descriptions."""
    timestamp: str = Field(..., description="e.g. '0:00'")
    label: str = Field(..., description="Timestamp label")


class PlatformPost(BaseModel):
    """Content for a single social media platform."""
    platform: Literal[
        "twitter_thread", "linkedin", "instagram",
        "youtube_description", "tiktok", "newsletter"
    ]
    tweets: Optional[list[TweetItem]] = Field(None, description="Twitter thread only")
    body: Optional[str] = Field(None, description="Single-body platforms")
    description_body: Optional[str] = Field(None, description="YouTube description body")
    timestamps: Optional[list[TimestampEntry]] = Field(None, description="YouTube timestamps")
    hashtags: list[str] = Field(default_factory=list)
    char_count: int = Field(..., ge=0)
    claim_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)

    @field_validator("tweets")
    @classmethod
    def validate_tweet_lengths(cls, v: Optional[list[TweetItem]]) -> Optional[list[TweetItem]]:
        """Validate all tweets are within 280 char limit."""
        if v:
            for tweet in v:
                if len(tweet.text) > 280:
                    raise ValueError(
                        f"Tweet {tweet.tweet_number} exceeds 280 chars ({len(tweet.text)})"
                    )
        return v


class SocialKitGuardrails(BaseModel):
    """Provenance acknowledgments."""
    no_new_facts_ack: bool = Field(True)
    all_facts_reference_doc2: bool = Field(True)
    all_facts_reference_doc0: bool = Field(True)


class SocialKitDocument(BaseModel):
    """Social Media Kit — Doc 6.

    Multi-platform social media content generated from research.
    """
    document_type: Literal["social_kit"] = "social_kit"
    job_id: str
    generated_at: str
    topic: str
    source_count: int = Field(..., ge=1)
    platforms: list[PlatformPost] = Field(
        ...,
        min_length=1,
        description="At least one platform post"
    )
    guardrails: SocialKitGuardrails = Field(default_factory=SocialKitGuardrails)

    def all_claim_ids(self) -> set[str]:
        """Return all claim_ids across all platforms."""
        ids: set[str] = set()
        for p in self.platforms:
            ids.update(p.claim_ids)
            if p.tweets:
                for t in p.tweets:
                    ids.update(t.claim_ids)
        return ids

    def all_source_ids(self) -> set[str]:
        """Return all source_ids across all platforms."""
        ids: set[str] = set()
        for p in self.platforms:
            ids.update(p.source_ids)
        return ids


class GenerateSocialKitRequest(BaseModel):
    """Request body for POST /jobs/{job_id}/social-kit."""
    platforms: list[str] = Field(
        default=["twitter_thread", "linkedin", "instagram", "youtube_description"],
        description="Platforms to generate for"
    )
    tone: Literal["professional", "casual", "energetic"] = "professional"
    style_guide_id: Optional[str] = None
