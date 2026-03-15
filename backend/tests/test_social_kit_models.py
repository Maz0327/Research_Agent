"""Tests for Social Media Kit (Doc 6) models."""
import pytest

from backend.models.social_kit_models import (
    SocialKitDocument,
    PlatformPost,
    TweetItem,
    GenerateSocialKitRequest,
)


def _make_twitter_post() -> dict:
    return {
        "platform": "twitter_thread",
        "tweets": [
            {"tweet_number": 1, "text": "This is tweet one about the topic.", "claim_ids": ["CLM_1"]},
            {"tweet_number": 2, "text": "And here's the second tweet.", "claim_ids": ["CLM_2"]},
        ],
        "hashtags": ["#research", "#thread"],
        "char_count": 65,
        "claim_ids": ["CLM_1", "CLM_2"],
        "source_ids": ["SRC_1"],
    }


def _make_linkedin_post() -> dict:
    return {
        "platform": "linkedin",
        "body": "Here's a LinkedIn post about the research findings. It has more detail.",
        "hashtags": ["#insights"],
        "char_count": 80,
        "claim_ids": ["CLM_1"],
        "source_ids": ["SRC_1"],
    }


def _make_kit(**overrides) -> dict:
    base = {
        "document_type": "social_kit",
        "job_id": "test-job-123",
        "generated_at": "2026-03-15T00:00:00Z",
        "topic": "Test Topic",
        "source_count": 3,
        "platforms": [_make_twitter_post(), _make_linkedin_post()],
        "guardrails": {
            "no_new_facts_ack": True,
            "all_facts_reference_doc2": True,
            "all_facts_reference_doc0": True,
        },
    }
    base.update(overrides)
    return base


class TestSocialKitDocument:
    def test_valid_kit(self):
        kit = SocialKitDocument(**_make_kit())
        assert kit.document_type == "social_kit"
        assert len(kit.platforms) == 2

    def test_empty_platforms_rejected(self):
        with pytest.raises(ValueError):
            SocialKitDocument(**_make_kit(platforms=[]))

    def test_all_claim_ids(self):
        kit = SocialKitDocument(**_make_kit())
        assert kit.all_claim_ids() == {"CLM_1", "CLM_2"}

    def test_all_source_ids(self):
        kit = SocialKitDocument(**_make_kit())
        assert kit.all_source_ids() == {"SRC_1"}


class TestTweetItem:
    def test_valid_tweet(self):
        tweet = TweetItem(tweet_number=1, text="Short tweet.", claim_ids=[])
        assert tweet.tweet_number == 1

    def test_tweet_over_280(self):
        """TweetItem max_length is enforced by Pydantic."""
        with pytest.raises(ValueError):
            TweetItem(tweet_number=1, text="x" * 281, claim_ids=[])


class TestGenerateSocialKitRequest:
    def test_defaults(self):
        req = GenerateSocialKitRequest()
        assert "twitter_thread" in req.platforms
        assert req.tone == "professional"

    def test_custom_platforms(self):
        req = GenerateSocialKitRequest(platforms=["linkedin", "tiktok"], tone="casual")
        assert len(req.platforms) == 2
        assert req.tone == "casual"
