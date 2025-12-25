"""OpenAI API client for job planning and LLM operations."""
import re
from datetime import date, datetime
from typing import Optional

try:
    from dateutil import parser as date_parser
except ImportError:
    # Fallback if dateutil not available (unlikely, but graceful)
    date_parser = None
from loguru import logger
from openai import OpenAI
from pydantic import ValidationError

from backend.config import require_openai, MissingRequiredSettingError
from backend.models.job_config import (
    BudgetsConfig,
    JobConfig,
    OutputConfig,
    ResearchMode,
    SourcesConfig,
    TimeWindow,
    YouTubeConfig,
)


def _extract_youtube_channels(text: str) -> list[str]:
    """
    Extract YouTube channel URLs and handles from text.
    
    Supports:
    - https://www.youtube.com/@channelhandle
    - https://www.youtube.com/channel/UCxxxxxxxx
    - https://youtube.com/@channelhandle
    - @channelhandle
    - youtube.com/channel/UCxxxxxxxx
    
    Returns:
        List of channel IDs or handles (with @ prefix preserved)
    """
    channels = []
    
    # Pattern for full YouTube URLs
    url_patterns = [
        r'youtube\.com/@([A-Za-z0-9_-]+)',
        r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})',
        r'youtube\.com/c/([A-Za-z0-9_-]+)',
        r'youtube\.com/user/([A-Za-z0-9_-]+)',
    ]
    
    for pattern in url_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            channel_id = match.group(1)
            if channel_id.startswith('UC'):
                channels.append(channel_id)
            else:
                channels.append(f"@{channel_id}")
    
    # Pattern for standalone @handles (not already captured)
    handle_pattern = r'(?:^|\s)@([A-Za-z0-9_-]+)(?=\s|$)'
    handle_matches = re.finditer(handle_pattern, text)
    for match in handle_matches:
        handle = f"@{match.group(1)}"
        if handle not in channels:
            channels.append(handle)
    
    return channels


def _parse_date_window(text: str) -> tuple[Optional[date], Optional[date]]:
    """
    Parse natural language date expressions from text.
    
    Examples:
    - "since September" -> (2024-09-01, today)
    - "since Sept 2023" -> (2023-09-01, today)
    - "last month" -> (one_month_ago, today)
    - "this year" -> (2024-01-01, today)
    
    Returns:
        Tuple of (start_date, end_date). end_date defaults to today if start is found.
    """
    text_lower = text.lower()
    today = date.today()
    start_date = None
    end_date = None
    
    # Common patterns
    if "since" in text_lower:
        # Extract the date part after "since"
        since_match = re.search(r'since\s+([^,.]+)', text_lower)
        if since_match:
            date_str = since_match.group(1).strip()
            if date_parser:
                try:
                    parsed_date = date_parser.parse(date_str, default=datetime(today.year, 1, 1))
                    start_date = parsed_date.date()
                    end_date = today  # Default end to today
                except (ValueError, Exception):  # date_parser.ParserError might not exist
                    logger.warning(f"Could not parse date from: {date_str}")
            else:
                logger.warning("dateutil not available, cannot parse dates")
    
    elif "last month" in text_lower:
        # Approximate: first day of previous month to today
        if today.month == 1:
            start_date = date(today.year - 1, 12, 1)
        else:
            start_date = date(today.year, today.month - 1, 1)
        end_date = today
    
    elif "this year" in text_lower:
        start_date = date(today.year, 1, 1)
        end_date = today
    
    elif "this month" in text_lower:
        start_date = date(today.year, today.month, 1)
        end_date = today
    
    return start_date, end_date


def _safe_default_config(topic: str) -> JobConfig:
    """
    Create a safe default JobConfig when planning fails.
    
    Args:
        topic: The topic text from Slack
        
    Returns:
        Default JobConfig with conservative settings
    """
    return JobConfig(
        mode=ResearchMode.CLAIMS_EVIDENCE,
        topic=topic.strip(),
        time_window=TimeWindow(),
        youtube=YouTubeConfig(
            channels=[],
            include_livestreams=True,
            exclude_shorts=True,
            max_videos=10,
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
            max_web_urls=50,
            max_transcription_minutes=120,
            max_claims_to_validate=25,
            max_validation_links_per_claim=6,
        ),
        output=OutputConfig(),
    )


def generate_short_title(prompt: str) -> str:
    """
    Generate a concise 3-6 word title from a verbose research prompt.

    Uses GPT-4o-mini to condense long prompts into short, descriptive titles.

    Args:
        prompt: The original research prompt (can be long/verbose)

    Returns:
        Short title (3-6 words) summarizing the research topic

    Examples:
        "Carlos Ghone former ceo of nissan story of his escape from japan"
        -> "Nissan CEO Escape Story"

        "What is the latest research on artificial intelligence safety and alignment"
        -> "AI Safety Research"
    """
    try:
        settings = require_openai()
    except MissingRequiredSettingError:
        logger.warning("OpenAI API key not configured. Using truncated prompt as title.")
        # Fallback: first 6 words of prompt
        words = prompt.strip().split()[:6]
        return " ".join(words).title()

    client = OpenAI(api_key=settings.openai_api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a title generator. Given a research topic or prompt, create a concise title of 3-6 words. Use title case. Be descriptive but brief. Return ONLY the title, nothing else."
                },
                {
                    "role": "user",
                    "content": f"Create a short title for this research topic:\n\n{prompt}"
                },
            ],
            temperature=0.3,
            max_tokens=50,
        )

        title = response.choices[0].message.content
        if title:
            # Clean up the title - remove quotes, extra whitespace
            title = title.strip().strip('"\'')
            # Limit to 60 chars max
            if len(title) > 60:
                title = title[:57] + "..."
            logger.info(f"Generated title: '{title}' from prompt: '{prompt[:50]}...'")
            return title
        else:
            raise ValueError("Empty response from OpenAI")

    except Exception as e:
        logger.warning(f"Failed to generate title: {e}. Using truncated prompt.")
        words = prompt.strip().split()[:6]
        return " ".join(words).title()


def plan_job(slack_text: str) -> JobConfig:
    """
    Use OpenAI to plan a research job from Slack text input.
    
    This function uses structured output to generate a JobConfig from natural language.
    It detects YouTube channels, infers date windows, and applies conservative defaults.
    
    Args:
        slack_text: Natural language request from Slack
        
    Returns:
        JobConfig object with all parameters configured
        
    Raises:
        MissingRequiredSettingError: If OPENAI_API_KEY is not configured
        ValueError: If slack_text is empty or invalid
    """
    # Validate input
    if not slack_text or not slack_text.strip():
        raise ValueError("slack_text cannot be empty")
    
    try:
        settings = require_openai()
    except MissingRequiredSettingError:
        logger.warning("OpenAI API key not configured. Returning safe default config.")
        return _safe_default_config(slack_text.strip())
    
    # Extract YouTube channels from text
    detected_channels = _extract_youtube_channels(slack_text)
    
    # Parse date window from text
    start_date, end_date = _parse_date_window(slack_text)
    
    # Get JSON schema from JobConfig
    JobConfig.model_json_schema()
    
    # Create OpenAI client
    client = OpenAI(api_key=settings.openai_api_key)
    
    # Build prompt for planning
    prompt = f"""You are a research job planner. Parse this user request and create a structured research job configuration.

User request: "{slack_text}"

Guidelines:
1. Extract the main research topic/question
2. If YouTube channels are mentioned ({detected_channels}), include them
3. If dates are mentioned, set time_window appropriately
4. Default to claims_evidence mode unless clearly a timeline request
5. Set conservative budgets: max_web_urls=50, max_claims_to_validate=25, max_validation_links_per_claim=6
6. Default: exclude_shorts=true, include_livestreams=true, fetch_transcripts=true
7. Enable web and news sources by default

Return a complete JobConfig JSON object matching the schema."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a research job planner. Return valid JSON matching the JobConfig schema.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        
        # Parse response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        import json
        
        try:
            config_dict = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from OpenAI response: {e}")
            logger.debug(f"Response content: {content}")
            return _safe_default_config(slack_text)

        # Unwrap nested config if OpenAI returned wrapped response
        # e.g., {"jobConfig": {...}} instead of flat config
        for wrapper_key in ["jobConfig", "job_config", "config"]:
            if wrapper_key in config_dict and isinstance(config_dict[wrapper_key], dict):
                logger.debug(f"Unwrapping nested config from '{wrapper_key}' key")
                config_dict = config_dict[wrapper_key]
                break
        
        # Merge detected channels if any
        if detected_channels:
            if "youtube" not in config_dict:
                config_dict["youtube"] = {}
            if "channels" not in config_dict["youtube"]:
                config_dict["youtube"]["channels"] = []
            # Add detected channels, avoiding duplicates
            existing = set(config_dict["youtube"]["channels"])
            for channel in detected_channels:
                if channel not in existing:
                    config_dict["youtube"]["channels"].append(channel)
        
        # Merge parsed date window
        if start_date or end_date:
            if "time_window" not in config_dict:
                config_dict["time_window"] = {}
            if start_date:
                config_dict["time_window"]["start"] = start_date.isoformat()
            if end_date:
                config_dict["time_window"]["end"] = end_date.isoformat()
        
        # Apply conservative defaults
        if "youtube" in config_dict:
            config_dict["youtube"].setdefault("exclude_shorts", True)
            config_dict["youtube"].setdefault("include_livestreams", True)
            config_dict["youtube"].setdefault("fetch_transcripts", True)
        
        if "budgets" not in config_dict:
            config_dict["budgets"] = {}
        config_dict["budgets"].setdefault("max_web_urls", 50)
        config_dict["budgets"].setdefault("max_claims_to_validate", 25)
        config_dict["budgets"].setdefault("max_validation_links_per_claim", 6)
        
        # Validate and return
        try:
            config = JobConfig.model_validate(config_dict)
            logger.info(f"Successfully planned job for topic: {config.topic}")
            return config
        except ValidationError as e:
            logger.error(f"Validation error in planned config: {e}")
            logger.debug(f"Config dict: {config_dict}")
            return _safe_default_config(slack_text)
    
    except Exception as e:
        logger.exception(f"Failed to plan job with OpenAI: {e}")
        return _safe_default_config(slack_text)

