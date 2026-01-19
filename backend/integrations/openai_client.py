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
from backend.utils.error_handling import sanitize_error_message
from backend.utils.rate_limiter import with_rate_limit
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


@with_rate_limit("openai")
def generate_short_title(prompt: str) -> str:
    """
    Generate a concise 3-6 word title from a verbose research prompt.

    Uses GPT-4o-mini to condense long prompts into short, descriptive titles.
    Rate limited with exponential backoff to prevent quota exhaustion.

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
        sanitized = sanitize_error_message(e, include_type=False)
        logger.warning(f"Failed to generate title: {sanitized}. Using truncated prompt.")
        words = prompt.strip().split()[:6]
        return " ".join(words).title()


@with_rate_limit("openai")
def generate_clarified_prompt(original_prompt: str, interpretation: dict) -> str:
    """
    Generate a natural, clarified version of an ambiguous prompt.

    Uses GPT-4o-mini to synthesize the original user question/request with
    the selected disambiguation, producing a clean prompt that preserves
    the original intent while incorporating the clarification.

    Args:
        original_prompt: The user's original research request
        interpretation: Dict with 'topic', 'description', and optionally 'label'

    Returns:
        A natural, clarified prompt combining the question intent with
        the specific interpretation. Falls back to concatenation on error.

    Examples:
        Input:
            original_prompt: "What fan theories exist about 'the barney show'?"
            interpretation: {"topic": "Barney the Dinosaur", "description": "Children's TV show"}
        Output:
            "What fan theories exist about Barney the Dinosaur (the children's TV show, 1992-2010)?"

    Cost: ~$0.003 per call
    """
    interpretation_topic = interpretation.get("topic", "")
    interpretation_desc = interpretation.get("description", "")

    # If no topic or same as original, just return original
    if not interpretation_topic or original_prompt.lower().strip() == interpretation_topic.lower().strip():
        return original_prompt

    # Fallback format (used on API failure)
    fallback = f"{original_prompt} [Clarification: This refers to {interpretation_topic}. {interpretation_desc}]"

    try:
        settings = require_openai()
    except MissingRequiredSettingError:
        logger.warning("OpenAI API key not configured. Using fallback prompt format.")
        return fallback

    client = OpenAI(api_key=settings.openai_api_key)

    system_prompt = """You are a prompt clarifier. Given an original research request and a clarification about what the user meant, synthesize them into a single, natural-sounding prompt.

Rules:
1. Preserve the original question/request structure and intent
2. Naturally integrate the clarified subject into the prompt
3. Add brief parenthetical context when helpful (dates, type of entity)
4. Keep the output concise - don't add unnecessary words
5. Return ONLY the clarified prompt, nothing else

Examples:
- "What fan theories exist about 'the barney show'?" + "Barney the Dinosaur (Children's TV show 1992-2010)"
  -> "What fan theories exist about Barney the Dinosaur (the children's TV show, 1992-2010)?"

- "Tell me about the Avatar controversy" + "Avatar (2009 James Cameron film)"
  -> "Tell me about the controversy surrounding Avatar (the 2009 James Cameron film)"

- "Why did The Office end?" + "The Office (US version, NBC sitcom 2005-2013)"
  -> "Why did The Office (the US version, 2005-2013) end?"
"""

    user_prompt = f"""Original request: "{original_prompt}"

Clarification - the user means: {interpretation_topic}
Additional context: {interpretation_desc}

Generate the clarified prompt:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=200,
        )

        result = response.choices[0].message.content
        if result:
            clarified = result.strip().strip('"\'')
            logger.info(f"Generated clarified prompt: '{clarified[:60]}...' from: '{original_prompt[:40]}...'")
            return clarified
        else:
            logger.warning("Empty response from clarification API, using fallback")
            return fallback

    except Exception as e:
        sanitized = sanitize_error_message(e, include_type=False)
        logger.warning(f"Failed to generate clarified prompt: {sanitized}. Using fallback.")
        return fallback


@with_rate_limit("openai")
def validate_extraction(
    source_text: str,
    extraction_result: dict,
    source_id: str = "UNKNOWN",
    model: str = "gpt-4o",
) -> dict:
    """Validate extraction using GPT-4o cross-model judge.

    Cross-model validation eliminates self-bias where the same model
    validates its own output. GPT-4o has different training data than
    Gemini, providing true independence.

    Args:
        source_text: Original source content
        extraction_result: Extraction result dict to validate
        source_id: Source identifier for logging
        model: OpenAI model to use (default gpt-4o)

    Returns:
        Dict with validation results:
        - items_reviewed: List of item validations
        - quotes_reviewed: List of quote validations
        - overall_quality: high/medium/low
        - hallucination_flags: List of likely hallucinated item IDs
        - confidence_overrides: List of suggested confidence changes
        - cost: Approximate API cost

    Raises:
        MissingRequiredSettingError: If OPENAI_API_KEY not configured
    """
    from backend.pipeline.llm_judge import (
        validate_extraction_with_judge,
        JudgeResult,
    )

    # Delegate to the llm_judge module
    result = validate_extraction_with_judge(
        source_text=source_text,
        extraction_result=extraction_result,
        source_id=source_id,
        model=model,
    )

    return result.to_dict()


@with_rate_limit("openai")
def plan_job(slack_text: str) -> dict:
    """
    Use OpenAI to plan a research job from Slack text input.

    This function uses structured output to generate a JobConfig from natural language.
    It detects YouTube channels, infers date windows, and applies conservative defaults.
    Rate limited with exponential backoff to prevent quota exhaustion.

    Dec 2025: Added disambiguation support for ambiguous topics.

    Args:
        slack_text: Natural language request from Slack

    Returns:
        Dict with one of two structures:
        - {"is_ambiguous": False, "config": JobConfig} for clear topics
        - {"is_ambiguous": True, "interpretations": [...]} for ambiguous topics
          Each interpretation: {"label": str, "description": str, "topic": str}

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
        return {"is_ambiguous": False, "config": _safe_default_config(slack_text.strip())}

    # Extract YouTube channels from text
    detected_channels = _extract_youtube_channels(slack_text)

    # Parse date window from text
    start_date, end_date = _parse_date_window(slack_text)

    # Get JSON schema from JobConfig
    JobConfig.model_json_schema()

    # Create OpenAI client
    client = OpenAI(api_key=settings.openai_api_key)

    # Build prompt for planning with disambiguation support
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
8. REDDIT SUBREDDITS: Suggest 2-5 relevant subreddits for this topic in "reddit.subreddits". Examples:
   - Fan theories: ["FanTheories", "plotholes", "AskScienceFiction"]
   - TV shows: ["television", show-specific sub like "BreakingBad"]
   - Movies: ["movies", "MovieDetails", "TrueFilm"]
   - Gaming: ["Games", "truegaming", game-specific subs]
   - Tech: ["technology", "programming", product-specific subs]
   - Politics: ["politics", "PoliticalDiscussion", "NeutralPolitics"]
   Match subreddits to the SPECIFIC topic, not generic defaults.
9. DISAMBIGUATION - BE PROACTIVE: If the topic could reasonably refer to multiple things, flag it as ambiguous. Examples:
   - "Barney" → children's show vs HIMYM character vs other
   - "The Office" → US version vs UK version
   - "Avatar" → James Cameron film vs animated series
   - Names that could be multiple people/characters
   - Show/movie titles that have remakes or share names
   When ambiguous, return ONLY: {{"is_ambiguous": true, "interpretations": [
     {{"label": "Short Name", "description": "Brief explanation", "topic": "Refined specific topic"}}
   ]}}
   Include 2-3 interpretations. When in doubt, ASK - it's better to disambiguate than research the wrong thing.

If clearly NOT ambiguous, return: {{"is_ambiguous": false, "config": {{...JobConfig with reddit.subreddits...}}}}"""

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
            return {"is_ambiguous": False, "config": _safe_default_config(slack_text)}

        # Check if response indicates ambiguity
        if config_dict.get("is_ambiguous") is True:
            interpretations = config_dict.get("interpretations", [])
            if interpretations:
                logger.info(f"Ambiguous topic detected: {len(interpretations)} interpretations")
                return {"is_ambiguous": True, "interpretations": interpretations}
            # Fallthrough if no interpretations provided

        # Extract config from response (may be nested under "config" key)
        if "config" in config_dict and isinstance(config_dict["config"], dict):
            config_dict = config_dict["config"]

        # Unwrap nested config if OpenAI returned wrapped response
        # e.g., {"jobConfig": {...}} instead of flat config
        for wrapper_key in ["jobConfig", "job_config"]:
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

        # Normalize topic field (OpenAI may return main_topic, subject, research_topic, etc.)
        if "topic" not in config_dict:
            for alt_name in ("main_topic", "subject", "research_topic", "query", "question"):
                if alt_name in config_dict:
                    config_dict["topic"] = config_dict.pop(alt_name)
                    logger.debug(f"Normalized '{alt_name}' -> 'topic'")
                    break

        # Fallback: use slack_text as topic if still missing
        if "topic" not in config_dict or not config_dict["topic"]:
            config_dict["topic"] = slack_text.strip()
            logger.debug("No topic field found, using slack_text as fallback")

        # Validate and return
        try:
            config = JobConfig.model_validate(config_dict)
            logger.info(f"Successfully planned job for topic: {config.topic}")
            return {"is_ambiguous": False, "config": config}
        except ValidationError as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Validation error in planned config: {sanitized}")
            logger.debug(f"Config dict: {config_dict}")
            return {"is_ambiguous": False, "config": _safe_default_config(slack_text)}

    except Exception as e:
        sanitized = sanitize_error_message(e, include_type=False)
        logger.exception(f"Failed to plan job with OpenAI: {sanitized}")
        return {"is_ambiguous": False, "config": _safe_default_config(slack_text)}

