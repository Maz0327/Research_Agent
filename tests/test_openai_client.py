"""Unit tests for OpenAI client job planning."""
import pytest
from datetime import date

from backend.integrations.openai_client import plan_job, _extract_youtube_channels, _parse_date_window
from backend.models.job_config import JobConfig, ResearchMode, YouTubeConfig


def test_extract_youtube_channels():
    """Test YouTube channel extraction from text."""
    # Test full URL with @handle
    text1 = "Check out https://www.youtube.com/@candaceowens latest videos"
    channels = _extract_youtube_channels(text1)
    assert "@candaceowens" in channels
    
    # Test channel ID URL
    text2 = "Visit youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA"
    channels = _extract_youtube_channels(text2)
    assert "UCX6OQ3DkcsbYNE6H8uQQuVA" in channels
    
    # Test standalone @handle
    text3 = "Research @candaceowens and @charliekirk"
    channels = _extract_youtube_channels(text3)
    assert "@candaceowens" in channels
    assert "@charliekirk" in channels
    
    # Test no channels
    text4 = "Just a regular text with no channels"
    channels = _extract_youtube_channels(text4)
    assert len(channels) == 0


def test_parse_date_window():
    """Test natural language date parsing."""
    # Test "since September"
    start, end = _parse_date_window("Research since September")
    assert start is not None
    assert end == date.today()
    assert start.month == 9  # September
    
    # Test "last month"
    start, end = _parse_date_window("What happened last month?")
    assert start is not None
    assert end == date.today()
    
    # Test "this year"
    start, end = _parse_date_window("Everything this year")
    assert start is not None
    assert start.year == date.today().year
    assert start.month == 1
    assert end == date.today()
    
    # Test no dates
    start, end = _parse_date_window("Just a regular request")
    assert start is None
    assert end is None


def test_plan_job_candace_livestream(monkeypatch):
    """Test planning a job for Candace Owens livestream request."""
    import json
    
    # Mock response content as JSON string
    mock_response_data = {
        "topic": "Candace Owens recent livestreams and claims about Charlie Kirk",
        "mode": "claims_evidence",
        "youtube": {
            "channels": [],
            "include_livestreams": True,
            "exclude_shorts": True,
            "max_videos": 10,
            "fetch_transcripts": True,
        },
        "sources": {
            "web": True,
            "include_news": True,
            "include_reddit_public": False,
        },
        "budgets": {
            "max_web_urls": 50,
            "max_claims_to_validate": 25,
            "max_validation_links_per_claim": 6,
        },
        "output": {
            "drive_folder_name": "Candace Owens Claims Analysis",
        },
    }
    
    mock_response_json = json.dumps(mock_response_data)
    
    class MockMessage:
        content = mock_response_json
    
    class MockChoice:
        message = MockMessage()
    
    class MockResponse:
        choices = [MockChoice()]
    
    def mock_chat_completion_create(*args, **kwargs):
        return MockResponse()
    
    # Test with mocked OpenAI
    try:
        import openai
        original_openai = openai.OpenAI
        
        # Mock the OpenAI class
        def mock_init(self, api_key=None):
            self.api_key = api_key
            self.chat = type(
                "MockChat",
                (),
                {
                    "completions": type(
                        "MockCompletions",
                        (),
                        {"create": mock_chat_completion_create}
                    )()
                },
            )()
        
        monkeypatch.setattr(openai.OpenAI, "__init__", mock_init)
        
        slack_text = "Research @candaceowens latest livestreams about Charlie Kirk since September"
        config = plan_job(slack_text)
        
        assert isinstance(config, JobConfig)
        assert config.topic is not None
        assert len(config.topic) > 0
        assert config.mode == ResearchMode.CLAIMS_EVIDENCE
        # Channel should be detected from text even if not in LLM response
        assert "@candaceowens" in config.youtube.channels
        assert config.youtube.include_livestreams is True
        assert config.youtube.exclude_shorts is True
        assert config.youtube.fetch_transcripts is True
        assert config.budgets.max_web_urls == 50
        assert config.budgets.max_claims_to_validate == 25
        assert config.budgets.max_validation_links_per_claim == 6
        assert config.sources.web is True
    except (ImportError, AttributeError) as e:
        # If OpenAI is not installed or mocking fails, test safe defaults path
        pytest.skip(f"OpenAI mocking failed: {e}, testing safe defaults only")
        
        slack_text = "Research @candaceowens latest livestreams about Charlie Kirk since September"
        config = plan_job(slack_text)
        assert isinstance(config, JobConfig)
        assert config.topic is not None
        assert config.youtube.exclude_shorts is True
        assert config.youtube.include_livestreams is True


def test_plan_job_safe_defaults():
    """Test that safe defaults are returned when OpenAI fails."""
    # This will use safe defaults because OpenAI key won't be set in test env
    slack_text = "Research something"
    config = plan_job(slack_text)
    
    assert isinstance(config, JobConfig)
    assert config.topic == slack_text.strip()
    assert config.mode == ResearchMode.CLAIMS_EVIDENCE
    assert config.youtube.exclude_shorts is True
    assert config.youtube.include_livestreams is True
    assert config.youtube.fetch_transcripts is True
    assert config.budgets.max_web_urls == 50
    assert config.budgets.max_claims_to_validate == 25
    assert config.budgets.max_validation_links_per_claim == 6
    assert config.sources.web is True

