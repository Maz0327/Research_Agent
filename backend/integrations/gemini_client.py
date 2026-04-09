"""Google Gemini API client for planning and vision tasks.

Uses the new google-genai SDK (replaces deprecated google-generativeai).

Research-validated stack (Dec 2025):
- Gemini 2.5 Flash: $0.30/$2.50 per M tokens - used for planning, query gen
- Gemini 2.5 Pro: $1.25/$10 per M tokens - used for vision/PDF, validation, synthesis

Phase 3 (Jan 2026): Full Research Assistant Pipeline
- Pass 1: Extraction (ProducerPacket) - existing
- Pass 2: Structure Analysis (ContentBlueprint) - NEW
- Pass 3: Gap Analysis (GapAnalysis) - NEW
- Pass 4: Research Starter (ResearchStarter) - NEW
"""
import gc
import json
import re
import time  # H-010: Rate limiting between API calls
from pathlib import Path
from typing import Optional, Any, Callable
from urllib.parse import urlparse, parse_qs

from loguru import logger

from backend.utils.error_handling import sanitize_error_message
from backend.utils.rate_limiter import with_rate_limit
from backend.utils.llm_temperature import get_temperature, TaskType, TEMP_FACTUAL
from backend.pipeline.quote_verification import verify_extraction_results

# =============================================================================
# Constants (L-002, L-007: Extract magic numbers)
# =============================================================================
MAX_VIDEOS_PER_JOB = 20  # C-003: Prevent unbounded loops
MAX_CLIPS_IN_SUMMARY = 20  # L-002: Named constant for context window limit
MAX_QUOTES_IN_SUMMARY = 20  # L-002: Named constant for context window limit
API_TIMEOUT_SECONDS = 300  # C-002: 5 minute timeout for Gemini API calls
PROGRESS_START = 5  # L-007: Progress calculation base
PROGRESS_RANGE = 90  # L-007: Progress calculation range

# L-003: Proper type alias for progress callback
ProgressCallback = Callable[[int, int, str, str], None]


# =============================================================================
# Custom Exceptions (C-001: Proper error signaling)
# =============================================================================
class GeminiParseError(Exception):
    """Raised when LLM response cannot be parsed as valid JSON.
    
    C-001: This exception signals parse failures to callers instead of
    silently returning minimal/empty dataclasses.
    """
    def __init__(self, message: str, raw_response: str = ""):
        self.message = message
        self.raw_response = raw_response
        super().__init__(message)


class GeminiTimeoutError(Exception):
    """Raised when Gemini API call times out.

    C-002: Explicit timeout handling.
    """
    pass


class GeminiTruncationError(Exception):
    """Raised when Gemini response is truncated due to max_output_tokens limit.

    This typically happens with long transcripts where the extraction output
    exceeds the token limit, resulting in incomplete JSON that cannot be parsed.
    """
    def __init__(self, message: str, partial_response: str = "", tokens_used: int = 0):
        self.message = message
        self.partial_response = partial_response
        self.tokens_used = tokens_used
        super().__init__(message)


# =============================================================================
# Utility Functions (L-001: DRY - shared JSON parsing)
# =============================================================================
def parse_json_from_llm_response(text: str) -> dict:
    """Parse JSON from LLM response with multiple fallback strategies.

    H-001: Handles edge cases:
    - ```json code blocks
    - ``` code blocks without language
    - Plain JSON (no code blocks)
    - JSON with trailing text
    - Truncated JSON (attempts repair)

    L-001: Single source of truth for JSON extraction.

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON as dict

    Raises:
        GeminiParseError: If no valid JSON can be extracted
    """
    # Strategy 1: Look for ```json code blocks
    if "```json" in text:
        try:
            json_str = text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass  # Try next strategy

    # Strategy 2: Look for ``` code blocks without language
    if "```" in text:
        try:
            json_str = text.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass  # Try next strategy

    # Strategy 3: Try parsing the entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 4: Find first { to last } (H-001: handles trailing text)
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            json_str = text[first_brace:last_brace + 1]
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Strategy 5: Attempt truncation repair for incomplete JSON
    # This handles cases where Gemini output was cut off mid-response
    if first_brace != -1:
        try:
            repaired = _repair_truncated_json(text[first_brace:])
            if repaired:
                return repaired
        except Exception:
            pass

    # All strategies failed
    raise GeminiParseError(
        f"Could not extract valid JSON from response",
        raw_response=text[:500]  # Include first 500 chars for debugging
    )


def _repair_truncated_json(json_str: str) -> dict | None:
    """Attempt to repair truncated JSON by closing unclosed structures.

    This is a best-effort recovery for LLM responses that were cut off.
    It attempts to close unclosed strings, arrays, and objects.

    Args:
        json_str: Potentially truncated JSON string starting with {

    Returns:
        Repaired JSON dict or None if repair failed
    """
    # Track nesting depth of braces and brackets
    brace_depth = 0
    bracket_depth = 0
    in_string = False
    escape_next = False
    last_valid_pos = 0

    for i, char in enumerate(json_str):
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == '{':
            brace_depth += 1
        elif char == '}':
            brace_depth -= 1
            if brace_depth == 0:
                last_valid_pos = i + 1
        elif char == '[':
            bracket_depth += 1
        elif char == ']':
            bracket_depth -= 1

    # If we have a complete object, try parsing it
    if last_valid_pos > 0 and brace_depth >= 0:
        try:
            return json.loads(json_str[:last_valid_pos])
        except json.JSONDecodeError:
            pass

    # Try to repair by closing unclosed structures
    repair = json_str

    # Close unclosed string (if in_string is True)
    if in_string:
        repair += '"'

    # Close unclosed arrays
    repair += ']' * bracket_depth

    # Close unclosed objects
    repair += '}' * brace_depth

    try:
        result = json.loads(repair)
        logger.warning(f"JSON repair successful: closed {brace_depth} braces, {bracket_depth} brackets")
        return result
    except json.JSONDecodeError:
        # Try more aggressive repair: find last complete array element
        # Look for patterns like "}, {" or "], [" and truncate there
        for pattern in ['},', '],', '",']:
            last_good = json_str.rfind(pattern)
            if last_good > 0:
                truncated = json_str[:last_good + 1]
                # Count remaining structure
                b_depth = truncated.count('{') - truncated.count('}')
                a_depth = truncated.count('[') - truncated.count(']')
                if b_depth >= 0 and a_depth >= 0:
                    repaired = truncated + ']' * a_depth + '}' * b_depth
                    try:
                        result = json.loads(repaired)
                        logger.warning(f"JSON repair (aggressive) successful at position {last_good}")
                        return result
                    except json.JSONDecodeError:
                        continue

        return None


def validate_youtube_url(url: str) -> bool:
    """Validate that a URL is a valid YouTube video URL.
    
    H-012: URL validation before sending to prompts.
    H-011: Uses proper URL API instead of string parsing.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid YouTube URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        
        # Check domain
        valid_domains = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
        if parsed.netloc not in valid_domains:
            return False
        
        # Check for video ID
        if parsed.netloc == "youtu.be":
            # youtu.be/VIDEO_ID format
            return len(parsed.path) > 1
        else:
            # youtube.com/watch?v=VIDEO_ID format
            params = parse_qs(parsed.query)
            return "v" in params and len(params["v"]) > 0
            
    except Exception:
        return False


def safe_to_dict(obj: Any) -> dict:
    """Safely convert dataclass to dict with error handling.
    
    M-008: Consistent serialization pattern.
    
    Args:
        obj: Object with to_dict() method or dict
        
    Returns:
        Dictionary representation
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return {}


# Import prompts for multi-pass analysis
from backend.pipeline.prompts import (
    STRUCTURE_ANALYSIS_PROMPT,
    GAP_ANALYSIS_PROMPT,
    RESEARCH_STARTER_PROMPT,
)

# Import dataclasses for structured output
from backend.models.video_analysis_models import (
    ContentBlueprint,
    ActSection,
    OpenLoop,
    GapAnalysis,
    MissingPerspective,
    CoverageBlindSpot,
    Contradiction,
    ResearchStarter,
    SearchQuery,
    SourceSuggestion,
    RabbitHole,
    ContentAngle,
)

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-genai not installed. Install with: pip install google-genai")

# =============================================================================
# Safety Settings — disable all adjustable safety filters
# =============================================================================
# Gemini's safety filters cause false-positive refusals on politically sensitive
# but legitimate research content (documented: ADL March 2025, TechCrunch March 2025).
# CIVIC_INTEGRITY is the primary culprit for political topic over-caution.
# Built-in protections (child safety, etc.) remain active regardless of these settings.
SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
    types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="OFF"),
] if GEMINI_AVAILABLE else []


class GeminiClient:
    """Client for Google Gemini 2.5 Flash/Pro.

    Uses the new google-genai SDK for better performance and features.

    Used for:
    - Planning with thinking mode (Flash)
    - Query generation (Flash)
    - Vision/PDF analysis (Pro)
    - Validation and synthesis (Pro)
    """

    # Cost per 1M tokens (Dec 2025 verified pricing)
    COSTS = {
        "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
        "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    }

    def __init__(self):
        """Initialize Gemini client with new SDK."""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-genai library not installed")

        from backend.config import get_settings
        settings = get_settings()

        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")

        self._client = genai.Client(api_key=settings.google_api_key)
        self._api_key = settings.google_api_key

    @with_rate_limit("gemini")
    def generate(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash",
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate text with Gemini.

        Args:
            prompt: The prompt to send
            model: Model to use (gemini-2.5-flash or gemini-2.5-pro)
            system_instruction: Optional system instruction
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Dict with text response and cost estimate
        """
        try:
            logger.info(f"Gemini {model}: {prompt[:50]}...")

            # Build config
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_instruction,
                safety_settings=SAFETY_SETTINGS,
            )

            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            text = response.text

            # Estimate cost (rough approximation)
            input_tokens = len(prompt.split()) * 1.3  # ~1.3 tokens per word
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(f"Gemini response: {len(text)} chars, ~${cost:.4f}")

            return {
                "text": text,
                "model": model,
                "cost": cost,
            }

        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Gemini generate failed: {sanitized}")
            raise RuntimeError(f"Gemini generate failed: {sanitized}") from e

    @with_rate_limit("gemini")
    def generate_with_thinking(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash",
        thinking_budget: int = 1024,
        system_instruction: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate with thinking mode for complex reasoning.

        Args:
            prompt: The prompt to send
            model: Model to use
            thinking_budget: Token budget for thinking (default 1024)
            system_instruction: Optional system instruction

        Returns:
            Dict with text response, thinking content, and cost estimate
        """
        try:
            logger.info(f"Gemini {model} thinking: {prompt[:50]}...")

            # Build config with thinking mode
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=thinking_budget
                ),
                safety_settings=SAFETY_SETTINGS,
            )

            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )

            text = response.text

            # Extract thinking content if available
            thinking = None
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'thinking_content'):
                    thinking = candidate.thinking_content

            # Estimate cost (thinking uses more tokens)
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(text.split()) * 1.3 + thinking_budget
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(f"Gemini thinking response: {len(text)} chars, ~${cost:.4f}")

            return {
                "text": text,
                "thinking": thinking,
                "model": model,
                "cost": cost,
            }

        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Gemini thinking failed: {sanitized}")
            raise RuntimeError(f"Gemini thinking failed: {sanitized}") from e

    @with_rate_limit("gemini")
    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str = "gemini-2.5-pro",
    ) -> dict[str, Any]:
        """Analyze an image with Gemini Pro vision.

        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            model: Model to use (default: gemini-2.5-pro for best vision)

        Returns:
            Dict with analysis text and cost estimate
        """
        try:
            logger.info(f"Gemini vision: {prompt[:50]}...")

            # Read and encode image
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            with open(image_path, "rb") as f:
                image_data = f.read()

            # Determine MIME type
            suffix = image_path.suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_types.get(suffix, "image/jpeg")

            # Create image part using new SDK
            image_part = types.Part.from_bytes(
                data=image_data,
                mime_type=mime_type,
            )

            response = self._client.models.generate_content(
                model=model,
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(safety_settings=SAFETY_SETTINGS),
            )
            text = response.text

            # Estimate cost (images count as ~258 tokens)
            input_tokens = len(prompt.split()) * 1.3 + 258
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(f"Gemini vision response: {len(text)} chars, ~${cost:.4f}")

            return {
                "text": text,
                "model": model,
                "cost": cost,
            }

        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Gemini vision failed: {sanitized}")
            raise RuntimeError(f"Gemini vision failed: {sanitized}") from e

    @with_rate_limit("gemini")
    def generate_json_with_image(
        self,
        prompt: str,
        image_base64: str,
        system_message: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.1,
        mime_type: str = "image/png",
    ) -> dict[str, Any]:
        """Generate JSON output from an image with structured parsing.

        Used for claim extraction from screenshots where we need
        structured JSON output with vision capabilities.

        Args:
            prompt: The extraction prompt
            image_base64: Base64-encoded image data
            system_message: Optional system instruction/role
            model: Model to use (default: gemini-2.5-flash)
            temperature: Sampling temperature
            mime_type: Image MIME type (default: image/png)

        Returns:
            Dict with 'data' (parsed JSON), 'cost', and optional 'error'
        """
        import base64

        try:
            logger.info(f"Gemini JSON vision ({model}): {prompt[:50]}...")

            # Decode base64 image
            image_data = base64.b64decode(image_base64)

            # Create image part using SDK
            image_part = types.Part.from_bytes(
                data=image_data,
                mime_type=mime_type,
            )

            # Build config with JSON output
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=16384,
                system_instruction=system_message,
                response_mime_type="application/json",
                safety_settings=SAFETY_SETTINGS,
            )

            response = self._client.models.generate_content(
                model=model,
                contents=[prompt, image_part],
                config=config,
            )
            text = response.text or ""

            # Estimate cost (images count as ~258 tokens)
            input_tokens = len(prompt.split()) * 1.3 + 258
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            # Parse JSON from response
            try:
                data = parse_json_from_llm_response(text)
            except Exception as parse_error:
                logger.warning(f"JSON parse error: {parse_error}, raw: {text[:200]}")
                return {
                    "data": {},
                    "cost": cost,
                    "error": f"Failed to parse JSON: {parse_error}",
                    "model": model,
                }

            logger.info(f"Gemini JSON vision response: {len(text)} chars, ~${cost:.4f}")

            return {
                "data": data,
                "cost": cost,
                "model": model,
            }

        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Gemini JSON vision failed: {sanitized}")
            return {
                "data": {},
                "cost": 0,
                "error": f"Gemini JSON vision failed: {sanitized}",
                "model": model,
            }

    @with_rate_limit("gemini")
    def analyze_pdf(
        self,
        pdf_path: str,
        prompt: str,
        model: str = "gemini-2.5-pro",
    ) -> dict[str, Any]:
        """Analyze a PDF document with Gemini Pro.

        Args:
            pdf_path: Path to PDF file
            prompt: Analysis prompt
            model: Model to use

        Returns:
            Dict with analysis text and cost estimate
        """
        try:
            logger.info(f"Gemini PDF analysis: {prompt[:50]}...")

            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")

            with open(pdf_path, "rb") as f:
                pdf_data = f.read()

            # Upload file to Gemini using new SDK
            uploaded_file = self._client.files.upload(
                file=pdf_path,
                config=types.UploadFileConfig(mime_type="application/pdf"),
            )

            response = self._client.models.generate_content(
                model=model,
                contents=[prompt, uploaded_file],
                config=types.GenerateContentConfig(safety_settings=SAFETY_SETTINGS),
            )
            text = response.text

            # Clean up uploaded file
            try:
                self._client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

            # Estimate cost (PDFs can be large)
            file_size_mb = len(pdf_data) / (1024 * 1024)
            input_tokens = len(prompt.split()) * 1.3 + (file_size_mb * 1000)  # rough estimate
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(f"Gemini PDF response: {len(text)} chars, ~${cost:.4f}")

            return {
                "text": text,
                "model": model,
                "cost": cost,
            }

        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Gemini PDF analysis failed: {sanitized}")
            raise RuntimeError(f"Gemini PDF analysis failed: {sanitized}") from e

    def _estimate_cost(self, model: str, input_tokens: float, output_tokens: float) -> float:
        """Estimate cost in dollars."""
        costs = self.COSTS.get(model, self.COSTS["gemini-2.5-flash"])
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost

    # =========================================================================
    # Semantic Extraction Support (Phase 1)
    # =========================================================================

    @with_rate_limit("gemini")
    def generate_json(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        model: str = "gemini-2.5-pro",
        temperature: Optional[float] = None,
        response_schema: Optional[type] = None,
    ) -> dict[str, Any]:
        """Generate JSON output with structured parsing.

        Used for semantic extraction where we need strict JSON output.

        Args:
            prompt: The extraction prompt
            system_message: Optional system instruction/role
            model: Model to use (default: gemini-2.5-pro for thinking/quality)
            temperature: Override temperature (defaults to TEMP_FACTUAL)
            response_schema: Optional Pydantic model for Gemini response_schema.
                             Must have NO default values (Gemini API requirement).
                             See: backend/models/semantic_extraction_schema.py

        Returns:
            Dict with 'data' (parsed JSON), 'cost', and optional 'error'
        """
        try:
            logger.info(f"Gemini JSON generation ({model}): {prompt[:80]}...")

            # Use factual temperature for extraction tasks
            if temperature is None:
                temperature = TEMP_FACTUAL  # 0.0 for deterministic extraction

            # Model-aware max_output_tokens (both Flash and Pro support 65K)
            # Pro thinking model uses separate thinking_budget for reasoning tokens
            max_tokens = 65536  # 64K tokens - Gemini 2.5 Flash/Pro max output

            # Build config
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_message,
                response_mime_type="application/json",  # Force JSON output
                response_schema=response_schema,  # Enforce JSON structure if provided
                safety_settings=SAFETY_SETTINGS,
            )

            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            text = response.text or ""

            # Check for truncation - finish_reason "MAX_TOKENS" means output was cut off
            finish_reason = None
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, "finish_reason"):
                    finish_reason = str(candidate.finish_reason)

            if finish_reason and "MAX_TOKENS" in finish_reason.upper():
                logger.error(
                    f"Gemini response TRUNCATED (model={model}, finish_reason={finish_reason}). "
                    f"Output too large for max_output_tokens={max_tokens}. "
                    f"Partial response: {len(text)} chars"
                )
                return {
                    "data": {},
                    "cost": self._estimate_cost(model, len(prompt.split()) * 1.3, len(text.split()) * 1.3),
                    "error": f"Response truncated: extraction output exceeded {max_tokens // 1024}K token limit. "
                             f"Try with shorter source content or increase chunking.",
                    "truncated": True,
                    "partial_response_length": len(text),
                    "model": model,
                }

            # Estimate cost as best-effort regardless of parse status
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            # Prefer structured parse from SDK when schema is provided
            parsed_obj = None
            try:
                if hasattr(response, "parsed") and response.parsed:
                    parsed_obj = response.parsed
                    # Normalize to plain dict via JSON round-trip to handle BaseModel/TypedDict
                    try:
                        data = json.loads(json.dumps(parsed_obj))
                    except Exception:
                        # Fallback: attempt attribute-based dump if available (pydantic v2)
                        if hasattr(parsed_obj, "model_dump_json"):
                            data = json.loads(parsed_obj.model_dump_json())
                        elif hasattr(parsed_obj, "model_dump"):
                            data = parsed_obj.model_dump()  # already dict-like
                        else:
                            # Last resort: treat as plain mapping
                            data = dict(parsed_obj)
                else:
                    # Parse JSON from text with robust utility
                    data = parse_json_from_llm_response(text)
            except GeminiParseError as e:
                logger.warning(f"JSON parse failed: {e.message}")
                # Log raw response for debugging (first 500 chars)
                logger.debug(f"Raw response that failed to parse: {text[:500]}...")
                return {
                    "data": {},
                    "cost": cost,
                    "error": f"JSON parse error: {e.message}",
                    "raw_response": e.raw_response,
                }

            logger.info(f"Gemini JSON response: {len(text)} chars, ~${cost:.4f}")

            return {"data": data, "cost": cost}

        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Gemini JSON generation failed: {sanitized}")
            return {
                "data": {},
                "cost": 0,
                "error": sanitized,
            }

    # =========================================================================
    # Phase 1.5: YouTube Video Analysis
    # =========================================================================

    @with_rate_limit("gemini")
    def analyze_youtube_video(
        self,
        video_url: str,
        model: str = "gemini-2.5-flash",
        max_clips: int = 12,
    ) -> dict[str, Any]:
        """Analyze a YouTube video and extract clips, quotes, timestamps.

        Phase 1 validated: Gemini processes YouTube URLs directly without download.

        Args:
            video_url: YouTube video URL
            model: Model to use (flash for speed, pro for accuracy)
            max_clips: Maximum clips to extract (default 12)

        Returns:
            Dict with video_info, clips, quotes, and cost
        """
        extraction_prompt = f"""Analyze this YouTube video and extract the following. Be precise and literal.

Return ONLY valid JSON with this structure:
{{
  "video_info": {{
    "title": "video title",
    "duration_seconds": 123,
    "speaker_count": 2
  }},
  "clips": [
    {{
      "clip_id": "CLIP_1",
      "timestamp_start": "MM:SS",
      "timestamp_end": "MM:SS",
      "speaker": "Name or SPEAKER_A",
      "quote": "Exact verbatim quote from video",
      "quote_type": "statement|question|reaction"
    }}
  ],
  "quotes": [
    {{
      "quote_id": "QUOTE_1",
      "text": "Exact verbatim quote",
      "speaker": "Name or SPEAKER_A",
      "timestamp": "MM:SS"
    }}
  ]
}}

RULES:
1. Timestamps must be in MM:SS format
2. Quotes must be VERBATIM - exact words spoken
3. If speaker name unknown, use SPEAKER_A, SPEAKER_B, etc.
4. Extract 6-{max_clips} most significant clips
5. NO opinions, NO analysis, NO "why it matters" - just extraction"""

        try:
            logger.info(f"Gemini video analysis: {video_url}")

            # Create video Part from YouTube URL - Gemini fetches and analyzes the actual video
            # This replaces just passing URL as text which may not properly fetch video content
            video_part = types.Part.from_uri(file_uri=video_url, mime_type="video/*")

            # TO-001: Use deterministic temperature for factual quote/clip extraction
            config = types.GenerateContentConfig(
                temperature=TEMP_FACTUAL,  # 0.0 for verbatim extraction
                max_output_tokens=4096,
                safety_settings=SAFETY_SETTINGS,
            )

            response = self._client.models.generate_content(
                model=model,
                contents=[video_part, extraction_prompt],
                config=config,
            )
            text = response.text

            # Parse JSON from response (json imported at module level)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)

            # Estimate cost (video analysis uses significant tokens)
            # ~1000 tokens per minute of video content
            duration = data.get("video_info", {}).get("duration_seconds", 180)
            video_tokens = (duration / 60) * 1000
            input_tokens = len(extraction_prompt.split()) * 1.3 + video_tokens
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(
                f"Gemini video: {len(data.get('clips', []))} clips, "
                f"{len(data.get('quotes', []))} quotes, ~${cost:.4f}"
            )

            return {
                "video_url": video_url,
                "video_info": data.get("video_info", {}),
                "clips": data.get("clips", []),
                "quotes": data.get("quotes", []),
                "cost": cost,
                "model": model,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Gemini video JSON parse failed: {e}")
            return {
                "video_url": video_url,
                "video_info": {},
                "clips": [],
                "quotes": [],
                "cost": 0,
                "error": f"JSON parse error: {e}",
            }
        except Exception as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Gemini video analysis failed: {sanitized}")
            return {
                "video_url": video_url,
                "video_info": {},
                "clips": [],
                "quotes": [],
                "cost": 0,
                "error": sanitized,
            }

    @with_rate_limit("gemini")
    def analyze_youtube_video_chunked(
        self,
        video_url: str,
        duration_seconds: int,
        model: str = "gemini-2.5-flash",
        chunk_duration_seconds: int = 3600,  # 1 hour chunks
    ) -> dict[str, Any]:
        """Analyze a long video in chunks for better accuracy.

        Phase 1.5: Videos >1 hour are processed in chunks to maintain accuracy.
        Gemini accuracy degrades to 40-50% on videos >3 hours without chunking.

        Args:
            video_url: YouTube video URL
            duration_seconds: Total video duration in seconds
            model: Model to use
            chunk_duration_seconds: Size of each chunk (default 1 hour)

        Returns:
            Dict with merged clips, quotes from all chunks
        """
        # Short videos don't need chunking
        if duration_seconds <= chunk_duration_seconds:
            return self.analyze_youtube_video(video_url, model=model)

        logger.info(
            f"Chunking video: {duration_seconds}s into "
            f"{(duration_seconds // chunk_duration_seconds) + 1} chunks"
        )

        all_clips = []
        all_quotes = []
        total_cost = 0.0
        chunk_results = []

        # Process each chunk
        for start in range(0, duration_seconds, chunk_duration_seconds):
            end = min(start + chunk_duration_seconds, duration_seconds)

            # YouTube URL with time range using fragment
            chunk_url = f"{video_url}#t={start},{end}"

            chunk_prompt = f"""Analyze this YouTube video segment (from {start//60}:{start%60:02d} to {end//60}:{end%60:02d}).

Return ONLY valid JSON with this structure:
{{
  "clips": [
    {{
      "clip_id": "CLIP_1",
      "timestamp_start": "MM:SS",
      "timestamp_end": "MM:SS",
      "speaker": "Name or SPEAKER_A",
      "quote": "Exact verbatim quote from video",
      "quote_type": "statement|question|reaction"
    }}
  ],
  "quotes": [
    {{
      "quote_id": "QUOTE_1",
      "text": "Exact verbatim quote",
      "speaker": "Name or SPEAKER_A",
      "timestamp": "MM:SS"
    }}
  ]
}}

RULES:
1. Timestamps must be ABSOLUTE (from start of video, not chunk)
2. Quotes must be VERBATIM - exact words spoken
3. Extract 3-6 most significant clips from this segment
4. NO opinions, NO analysis

YouTube Video URL: {chunk_url}"""

            try:
                # Create video Part from YouTube URL - Gemini fetches and analyzes the actual video
                # Note: chunk_url includes #t=start,end fragment for time range
                video_part = types.Part.from_uri(file_uri=chunk_url, mime_type="video/*")

                response = self._client.models.generate_content(
                    model=model,
                    contents=[video_part, chunk_prompt],
                    config=types.GenerateContentConfig(safety_settings=SAFETY_SETTINGS),
                )
                text = response.text

                # Parse JSON (json imported at module level)
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                data = json.loads(text)

                # Offset timestamps to absolute
                clips = data.get("clips", [])
                quotes = data.get("quotes", [])

                all_clips.extend(clips)
                all_quotes.extend(quotes)

                # Estimate cost for this chunk
                chunk_duration = end - start
                video_tokens = (chunk_duration / 60) * 1000
                input_tokens = len(chunk_prompt.split()) * 1.3 + video_tokens
                output_tokens = len(text.split()) * 1.3
                chunk_cost = self._estimate_cost(model, input_tokens, output_tokens)
                total_cost += chunk_cost

                chunk_results.append({
                    "start": start,
                    "end": end,
                    "clips": len(clips),
                    "quotes": len(quotes),
                    "cost": chunk_cost,
                })

                logger.info(
                    f"Chunk {start//60}-{end//60}min: "
                    f"{len(clips)} clips, {len(quotes)} quotes"
                )

            except Exception as e:
                logger.warning(f"Chunk {start}-{end} failed: {e}")
                chunk_results.append({
                    "start": start,
                    "end": end,
                    "error": str(e),
                })

        # Deduplicate clips by quote similarity
        unique_clips = self._dedupe_clips(all_clips)
        unique_quotes = self._dedupe_quotes(all_quotes)

        logger.info(
            f"Chunked analysis complete: {len(unique_clips)} clips "
            f"({len(all_clips)} raw), ${total_cost:.4f}"
        )

        return {
            "video_url": video_url,
            "video_info": {"duration_seconds": duration_seconds},
            "clips": unique_clips,
            "quotes": unique_quotes,
            "cost": total_cost,
            "model": model,
            "chunk_results": chunk_results,
        }

    def _dedupe_clips(self, clips: list[dict]) -> list[dict]:
        """Deduplicate clips by quote similarity."""
        if not clips:
            return []

        seen_quotes = set()
        unique = []

        for clip in clips:
            quote = clip.get("quote", "").lower().strip()[:50]
            if quote and quote not in seen_quotes:
                seen_quotes.add(quote)
                unique.append(clip)

        return unique

    def _dedupe_quotes(self, quotes: list[dict]) -> list[dict]:
        """Deduplicate quotes by text similarity."""
        if not quotes:
            return []

        seen_texts = set()
        unique = []

        for quote in quotes:
            text = quote.get("text", "").lower().strip()[:50]
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique.append(quote)

        return unique

    def analyze_youtube_videos_batch(
        self,
        video_urls: list[str],
        model: str = "gemini-2.5-flash",
        progress_callback: Optional[callable] = None,
    ) -> dict[str, Any]:
        """Analyze multiple YouTube videos with per-video error handling.

        Phase 1.5: Per-video errors don't kill the batch.

        Args:
            video_urls: List of YouTube video URLs
            model: Model to use
            progress_callback: Optional callback(current, total, video_url, status)

        Returns:
            Dict with results, errors, and aggregated data
        """
        results = []
        errors = []
        all_clips = []
        all_quotes = []
        total_cost = 0.0

        total = len(video_urls)

        for i, url in enumerate(video_urls):
            try:
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, total, url, "processing")

                result = self.analyze_youtube_video(url, model=model)

                if result.get("error"):
                    errors.append({
                        "video_url": url,
                        "error": result["error"],
                        "status": "failed",
                    })
                else:
                    results.append(result)
                    # Enrich clips/quotes with parent video_url before aggregation
                    # Gemini LLM returns clips without video_url - it's at result top level
                    video_url = result.get("video_url", url)
                    enriched_clips = [
                        {**clip, "video_url": video_url} for clip in result.get("clips", [])
                    ]
                    enriched_quotes = [
                        {**quote, "video_url": video_url} for quote in result.get("quotes", [])
                    ]
                    all_clips.extend(enriched_clips)
                    all_quotes.extend(enriched_quotes)
                    total_cost += result.get("cost", 0)

                if progress_callback:
                    progress_callback(i + 1, total, url, "completed" if not result.get("error") else "failed")

            except Exception as e:
                logger.error(f"Video {i + 1}/{total} failed: {url} - {e}")
                errors.append({
                    "video_url": url,
                    "error": str(e),
                    "status": "failed",
                })
                if progress_callback:
                    progress_callback(i + 1, total, url, "failed")

        # Determine overall status
        if not results and errors:
            status = "failed"
        elif errors:
            status = "completed_with_warnings"
        else:
            status = "completed"

        return {
            "status": status,
            "results": results,
            "errors": errors,
            "clips": all_clips,
            "quotes": all_quotes,
            "total_cost": total_cost,
            "videos_processed": len(results),
            "videos_failed": len(errors),
        }

    # =========================================================================
    # Phase 3: Full Research Assistant Pipeline (Jan 2026)
    # =========================================================================

    @with_rate_limit("gemini")
    def analyze_video_structure(
        self,
        video_url: str,
        video_title: str,
        model: str = "gemini-2.5-flash",
    ) -> tuple[ContentBlueprint, float, Optional[str]]:
        """Pass 2: Analyze video structure and technique.

        Reverse-engineers a YouTube video's hook, narrative structure,
        re-engagement points, style, and likely sources.

        Args:
            video_url: YouTube video URL
            video_title: Video title for context
            model: Model to use

        Returns:
            Tuple of (ContentBlueprint, cost, error_message)
            - ContentBlueprint: dataclass with structure analysis
            - cost: Estimated API cost (H-002: track costs)
            - error_message: None if success, error string if failed (C-001)
        """
        cost = 0.0
        
        # H-012: Validate YouTube URL before processing
        if not validate_youtube_url(video_url):
            logger.warning(f"Pass 2 - Invalid YouTube URL: {video_url}")
            return (
                ContentBlueprint(
                    video_url=video_url,
                    title=video_title,
                    hook_timestamp="",
                    hook_technique="invalid_url",
                    hook_description="Invalid YouTube URL provided",
                    structure_type="unknown",
                ),
                0.0,
                f"Invalid YouTube URL: {video_url}"
            )
        
        try:
            logger.info(f"Pass 2 - Structure analysis: {video_title[:50]}...")

            # H-006: Validate prompt template variables
            try:
                prompt = STRUCTURE_ANALYSIS_PROMPT.format(
                    video_url=video_url,
                    video_title=video_title,
                )
            except KeyError as e:
                logger.error(f"Pass 2 - Prompt template missing variable: {e}")
                return (
                    ContentBlueprint(
                        video_url=video_url,
                        title=video_title,
                        hook_timestamp="",
                        hook_technique="template_error",
                        hook_description=f"Prompt template error: {e}",
                        structure_type="unknown",
                    ),
                    0.0,
                    f"Prompt template error: {e}"
                )

            # C-002: Add timeout configuration
            # TO-001: Structure analysis uses moderate temperature (some interpretation allowed)
            config = types.GenerateContentConfig(
                temperature=get_temperature(TaskType.STRUCTURE_ANALYSIS),  # 0.3
                max_output_tokens=4096,
                safety_settings=SAFETY_SETTINGS,
            )

            # Create video Part from YouTube URL - Gemini fetches and analyzes the actual video
            video_part = types.Part.from_uri(file_uri=video_url, mime_type="video/*")

            response = self._client.models.generate_content(
                model=model,
                contents=[video_part, prompt],
                config=config,
            )
            text = response.text

            # H-001, L-001: Use robust JSON parsing utility
            try:
                data = parse_json_from_llm_response(text)
            except GeminiParseError as e:
                # C-001: Return with explicit error, not silent failure
                logger.warning(f"Pass 2 JSON parse failed: {e.message}")
                return (
                    ContentBlueprint(
                        video_url=video_url,
                        title=video_title,
                        hook_timestamp="",
                        hook_technique="parse_error",
                        hook_description=f"JSON parse error: {e.message}",
                        structure_type="unknown",
                        parse_error=True,  # H-013: explicit error flag
                    ),
                    0.0,
                    f"JSON parse error: {e.message}"
                )

            # Build ContentBlueprint from parsed data
            hook = data.get("hook", {})
            narrative = data.get("narrative", {})
            style = data.get("style", {})
            sources = data.get("sources", {})

            # Parse act breakdown
            act_breakdown = []
            for act in narrative.get("acts", []):
                act_breakdown.append(ActSection(
                    name=act.get("name", ""),
                    timestamp_start=act.get("timestamp_start", ""),
                    timestamp_end=act.get("timestamp_end", ""),
                    description=act.get("description", ""),
                ))

            # Parse open loops
            open_loops = []
            for loop in data.get("open_loops", []):
                open_loops.append(OpenLoop(
                    timestamp=loop.get("timestamp", ""),
                    technique=loop.get("technique", ""),
                    description=loop.get("description", ""),
                ))

            blueprint = ContentBlueprint(
                video_url=video_url,
                title=video_title,
                hook_timestamp=hook.get("timestamp_end", ""),
                hook_technique=hook.get("technique", ""),
                hook_description=hook.get("description", ""),
                structure_type=narrative.get("structure_type", ""),
                act_breakdown=act_breakdown,
                open_loops=open_loops,
                pacing=style.get("pacing", "medium"),
                editing_style=style.get("editing_style", "standard"),
                likely_primary_sources=sources.get("likely_primary_sources", []),
                referenced_materials=sources.get("referenced_materials", []),
            )

            # H-002: Calculate and return cost
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(
                f"Pass 2 complete: {len(act_breakdown)} acts, "
                f"{len(open_loops)} open loops, ~${cost:.4f}"
            )

            return (blueprint, cost, None)

        # H-005: Catch specific exceptions, not generic Exception
        except (ValueError, RuntimeError, json.JSONDecodeError) as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.warning(f"Pass 2 failed (recoverable): {sanitized}")
            return (
                ContentBlueprint(
                    video_url=video_url,
                    title=video_title,
                    hook_timestamp="",
                    hook_technique="error",
                    hook_description=sanitized,
                    structure_type="unknown",
                ),
                cost,
                sanitized
            )
        except Exception as e:
            # Only catch truly unexpected errors
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Pass 2 failed (unexpected): {sanitized}")
            return (
                ContentBlueprint(
                    video_url=video_url,
                    title=video_title,
                    hook_timestamp="",
                    hook_technique="error",
                    hook_description=sanitized,
                    structure_type="unknown",
                ),
                cost,
                sanitized
            )

    @with_rate_limit("gemini")
    def analyze_gaps(
        self,
        clips_summary: str,
        quotes_summary: str,
        videos_list: str,
        num_videos: int,
        model: str = "gemini-2.5-flash",
    ) -> tuple[GapAnalysis, float, Optional[str]]:
        """Pass 3: Analyze gaps across all analyzed videos.

        Identifies missing perspectives, unanswered questions,
        unexplored topics, and contradictions between sources.

        Args:
            clips_summary: Formatted summary of all clips
            quotes_summary: Formatted summary of all quotes
            videos_list: Formatted list of videos analyzed
            num_videos: Number of videos analyzed
            model: Model to use

        Returns:
            Tuple of (GapAnalysis, cost, error_message)
            - GapAnalysis: dataclass with cross-video gaps
            - cost: Estimated API cost (H-002: track costs)
            - error_message: None if success, error string if failed (C-001)
        """
        cost = 0.0
        
        # C-004/H-011: Input validation with clear error messaging
        if num_videos == 0:
            logger.warning("Pass 3 - No videos to analyze")
            return (
                GapAnalysis(parse_error=True),
                0.0,
                "No videos provided for gap analysis"
            )
        
        if not clips_summary.strip() and not quotes_summary.strip():
            logger.warning("Pass 3 - Empty clips and quotes summaries")
            return (
                GapAnalysis(parse_error=True),
                0.0,
                "No content available for gap analysis"
            )
        
        try:
            logger.info(f"Pass 3 - Gap analysis: {num_videos} videos...")

            # M-006: Truncate summaries to prevent prompt bloat
            max_summary_len = 15000  # ~4000 tokens
            if len(clips_summary) > max_summary_len:
                clips_summary = clips_summary[:max_summary_len] + "\n[...truncated for length]"
            if len(quotes_summary) > max_summary_len:
                quotes_summary = quotes_summary[:max_summary_len] + "\n[...truncated for length]"

            # H-006: Validate prompt template variables
            try:
                prompt = GAP_ANALYSIS_PROMPT.format(
                    num_videos=num_videos,
                    clips_summary=clips_summary,
                    quotes_summary=quotes_summary,
                    videos_list=videos_list,
                )
            except KeyError as e:
                logger.error(f"Pass 3 - Prompt template missing variable: {e}")
                return (
                    GapAnalysis(parse_error=True),
                    0.0,
                    f"Prompt template error: {e}"
                )

            # C-002: Add timeout configuration
            # TO-001: Gap analysis allows moderate exploration
            config = types.GenerateContentConfig(
                temperature=get_temperature(TaskType.GAP_ANALYSIS),  # 0.4
                max_output_tokens=4096,
                safety_settings=SAFETY_SETTINGS,
            )

            response = self._client.models.generate_content(
                model=model,
                contents=[prompt],
                config=config,
            )
            text = response.text

            # H-001, L-001: Use robust JSON parsing utility
            try:
                data = parse_json_from_llm_response(text)
            except GeminiParseError as e:
                # C-001: Return with explicit error, not silent failure
                logger.warning(f"Pass 3 JSON parse failed: {e.message}")
                return (
                    GapAnalysis(parse_error=True),
                    0.0,
                    f"JSON parse error: {e.message}"
                )

            # Build GapAnalysis from parsed data
            missing_perspectives = []
            for mp in data.get("missing_perspectives", []):
                missing_perspectives.append(MissingPerspective(
                    perspective=mp.get("perspective", ""),
                    why_important=mp.get("why_important", ""),
                    suggested_search=mp.get("suggested_search", ""),
                ))

            mentioned_but_unexplored = []
            for topic in data.get("mentioned_but_unexplored", []):
                mentioned_but_unexplored.append(CoverageBlindSpot(
                    topic=topic.get("topic", ""),
                    where_mentioned=topic.get("where_mentioned", ""),
                    why_explore=topic.get("why_explore", ""),
                ))

            contradictions = []
            for c in data.get("contradictions", []):
                contradictions.append(Contradiction(
                    claim_a=c.get("claim_a", ""),
                    source_a=c.get("source_a", ""),
                    claim_b=c.get("claim_b", ""),
                    source_b=c.get("source_b", ""),
                    opportunity=c.get("opportunity", ""),
                ))

            gap_analysis = GapAnalysis(
                missing_perspectives=missing_perspectives,
                unanswered_questions=data.get("unanswered_questions", []),
                mentioned_but_unexplored=mentioned_but_unexplored,
                contradictions=contradictions,
            )

            # H-002: Calculate and return cost
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(
                f"Pass 3 complete: {len(missing_perspectives)} missing perspectives, "
                f"{len(data.get('unanswered_questions', []))} unanswered questions, ~${cost:.4f}"
            )

            return (gap_analysis, cost, None)

        # H-005: Catch specific exceptions, not generic Exception
        except (ValueError, RuntimeError, json.JSONDecodeError) as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.warning(f"Pass 3 failed (recoverable): {sanitized}")
            return (GapAnalysis(), cost, sanitized)
        except Exception as e:
            # Only catch truly unexpected errors
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Pass 3 failed (unexpected): {sanitized}")
            return (GapAnalysis(), cost, sanitized)

    @with_rate_limit("gemini")
    def generate_research_starter(
        self,
        gap_analysis: GapAnalysis,
        research_topic: str,
        num_videos: int,
        model: str = "gemini-2.5-flash",
    ) -> tuple[ResearchStarter, float, Optional[str]]:
        """Pass 4: Generate actionable research starting points.

        Based on the gap analysis, generates specific search queries,
        source type suggestions, bounded rabbit holes, and content angles.

        Args:
            gap_analysis: GapAnalysis from Pass 3
            research_topic: The topic being researched
            num_videos: Number of videos analyzed
            model: Model to use

        Returns:
            Tuple of (ResearchStarter, cost, error_message)
            - ResearchStarter: dataclass with actionable next steps
            - cost: Estimated API cost (H-002: track costs)
            - error_message: None if success, error string if failed (C-001)
        """
        cost = 0.0
        
        # C-004/H-011: Input validation with clear error messaging
        if not research_topic or not research_topic.strip():
            logger.warning("Pass 4 - Empty research topic provided")
            return (
                ResearchStarter(parse_error=True),
                0.0,
                "Empty research topic provided"
            )
        
        # H-013: Check if gap_analysis has parse_error flag
        if getattr(gap_analysis, 'parse_error', False):
            logger.warning("Pass 4 - Gap analysis had parse errors, proceeding with limited data")
        
        try:
            logger.info(f"Pass 4 - Research starter: {research_topic[:50]}...")

            # Format gap analysis summaries for the prompt
            missing_perspectives_text = "\n".join([
                f"- {mp.perspective}: {mp.why_important}"
                for mp in gap_analysis.missing_perspectives
            ]) or "None identified"

            unanswered_questions_text = "\n".join([
                f"- {q}" for q in gap_analysis.unanswered_questions
            ]) or "None identified"

            unexplored_topics_text = "\n".join([
                f"- {t.topic}: {t.why_explore}"
                for t in gap_analysis.mentioned_but_unexplored
            ]) or "None identified"

            # H-006: Validate prompt template variables
            try:
                prompt = RESEARCH_STARTER_PROMPT.format(
                    num_videos=num_videos,
                    missing_perspectives=missing_perspectives_text,
                    unanswered_questions=unanswered_questions_text,
                    unexplored_topics=unexplored_topics_text,
                    research_topic=research_topic,
                )
            except KeyError as e:
                logger.error(f"Pass 4 - Prompt template missing variable: {e}")
                return (
                    ResearchStarter(parse_error=True),
                    0.0,
                    f"Prompt template error: {e}"
                )

            # TO-001: Research starter allows moderate exploration
            config = types.GenerateContentConfig(
                temperature=get_temperature(TaskType.RESEARCH_STARTER),  # 0.5
                max_output_tokens=4096,
                safety_settings=SAFETY_SETTINGS,
            )

            response = self._client.models.generate_content(
                model=model,
                contents=[prompt],
                config=config,
            )
            text = response.text

            # H-001, L-001: Use robust JSON parsing utility
            try:
                data = parse_json_from_llm_response(text)
            except GeminiParseError as e:
                # C-001: Return with explicit error, not silent failure
                logger.warning(f"Pass 4 JSON parse failed: {e.message}")
                return (
                    ResearchStarter(parse_error=True),
                    0.0,
                    f"JSON parse error: {e.message}"
                )

            # Build ResearchStarter from parsed data
            search_queries = []
            for sq in data.get("search_queries", []):
                search_queries.append(SearchQuery(
                    query=sq.get("query", ""),
                    platform=sq.get("platform", "google"),
                    why=sq.get("why", ""),
                ))

            source_suggestions = []
            for ss in data.get("source_suggestions", []):
                source_suggestions.append(SourceSuggestion(
                    source_type=ss.get("source_type", ""),
                    description=ss.get("description", ""),
                    why_helpful=ss.get("why_helpful", ""),
                ))

            rabbit_holes = []
            for rh in data.get("rabbit_holes", []):
                rabbit_holes.append(RabbitHole(
                    topic=rh.get("topic", ""),
                    mentioned_in=rh.get("mentioned_in", ""),
                    potential_angle=rh.get("potential_angle", ""),
                ))

            content_angles = []
            for ca in data.get("content_angles", []):
                content_angles.append(ContentAngle(
                    angle=ca.get("angle", ""),
                    differentiator=ca.get("differentiator", ""),
                    why_unique=ca.get("why_unique", ""),
                ))

            research_starter = ResearchStarter(
                search_queries=search_queries,
                source_suggestions=source_suggestions,
                rabbit_holes=rabbit_holes,
                content_angles=content_angles,
            )

            # H-002: Calculate and return cost
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(
                f"Pass 4 complete: {len(search_queries)} queries, "
                f"{len(source_suggestions)} source types, "
                f"{len(content_angles)} angles, ~${cost:.4f}"
            )

            return (research_starter, cost, None)

        # H-005: Catch specific exceptions, not generic Exception
        except (ValueError, RuntimeError, json.JSONDecodeError) as e:
            sanitized = sanitize_error_message(e, include_type=False)
            logger.warning(f"Pass 4 failed (recoverable): {sanitized}")
            return (ResearchStarter(), cost, sanitized)
        except Exception as e:
            # Only catch truly unexpected errors
            sanitized = sanitize_error_message(e, include_type=False)
            logger.error(f"Pass 4 failed (unexpected): {sanitized}")
            return (ResearchStarter(), cost, sanitized)

    def run_full_analysis_pipeline(
        self,
        video_urls: list[str],
        research_topic: str,
        model: str = "gemini-2.5-flash",
        progress_callback: Optional[callable] = None,
        transcripts: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Run complete 4-pass analysis pipeline.

        Pass 1: Extract clips and quotes (existing)
        Pass 1.5: Verify quotes against transcripts (QV-003)
        Pass 2: Structure analysis per video (ContentBlueprint)
        Pass 3: Gap analysis across all videos (GapAnalysis)
        Pass 4: Research starter with actionable queries (ResearchStarter)

        Args:
            video_urls: List of YouTube video URLs
            research_topic: The topic being researched
            model: Model to use
            progress_callback: Optional callback(pass_num, total_passes, status, detail)
            transcripts: Optional dict mapping video_url -> transcript_text for quote verification

        Returns:
            Dict with all pipeline outputs including cost and error tracking
        """
        total_passes = 4
        total_cost = 0.0
        pipeline_errors: list[str] = []  # H-013: Track errors from each pass
        
        # C-005: Safe progress callback wrapper
        def safe_progress(pass_num: int, total: int, status: str, detail: str) -> None:
            if progress_callback:
                try:
                    progress_callback(pass_num, total, status, detail)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
        
        # C-004: Input validation
        if not video_urls:
            return {
                "status": "failed",
                "error": "No video URLs provided",
                "pipeline_errors": ["No video URLs provided"],
                "total_cost": 0.0,
            }
        
        if not research_topic or not research_topic.strip():
            return {
                "status": "failed",
                "error": "Empty research topic provided",
                "pipeline_errors": ["Empty research topic provided"],
                "total_cost": 0.0,
            }
        
        # C-003: Enforce maximum videos limit to prevent unbounded loops
        if len(video_urls) > MAX_VIDEOS_PER_JOB:
            logger.warning(
                f"Truncating video list from {len(video_urls)} to {MAX_VIDEOS_PER_JOB}"
            )
            video_urls = video_urls[:MAX_VIDEOS_PER_JOB]

        # Pass 1: Extract clips and quotes
        video_count = len(video_urls)
        safe_progress(1, total_passes, "extracting", f"Extracting clips & quotes from {video_count} video{'s' if video_count != 1 else ''}...")

        batch_result = self.analyze_youtube_videos_batch(video_urls, model=model)
        total_cost += batch_result.get("total_cost", 0)

        if batch_result["status"] == "failed":
            return {
                "status": "failed",
                "error": "Pass 1 extraction failed - no videos processed",
                "batch_result": batch_result,
                "pipeline_errors": ["Pass 1: All video extractions failed"],
                "total_cost": total_cost,
            }
        
        # Track partial failures from Pass 1
        if batch_result.get("errors"):
            for err in batch_result["errors"]:
                pipeline_errors.append(f"Pass 1: {err.get('video_url', 'unknown')} - {err.get('error', 'failed')}")

        # C-003: Limit results to prevent runaway processing
        results = batch_result.get("results", [])[:MAX_VIDEOS_PER_JOB]

        # QV-003: Quote verification against transcripts (if available)
        # This catches hallucinated quotes before they propagate downstream
        verification_warnings = []
        if transcripts:
            safe_progress(1, total_passes, "verifying", "Verifying quotes against transcripts...")
            verified_results = []
            for result in results:
                video_url = result.get("video_url", "")
                # Find transcript for this video
                transcript_text = transcripts.get(video_url)
                if transcript_text:
                    verified_result, warnings = verify_extraction_results(
                        result, transcript_text, video_url
                    )
                    verified_results.append(verified_result)
                    verification_warnings.extend(warnings)
                else:
                    # No transcript - keep unverified but flag
                    result["quote_verification"] = {
                        "transcript_available": False,
                        "clips_verified": 0,
                        "clips_removed": 0,
                    }
                    verification_warnings.append(
                        f"Quote verification skipped for {video_url}: no transcript"
                    )
                    verified_results.append(result)
            results = verified_results

            # Update batch_result with verified clips/quotes
            all_verified_clips = []
            all_verified_quotes = []
            for r in results:
                all_verified_clips.extend(r.get("clips", []))
                all_verified_quotes.extend(r.get("quotes", []))
            batch_result["clips"] = all_verified_clips
            batch_result["quotes"] = all_verified_quotes

            # Log verification summary
            total_removed = sum(
                r.get("quote_verification", {}).get("clips_removed", 0) +
                r.get("quote_verification", {}).get("quotes_removed", 0)
                for r in results
            )
            if total_removed > 0:
                logger.info(f"Quote verification: {total_removed} hallucinated items removed")
                pipeline_errors.extend(verification_warnings)

        # Prepare summaries for Pass 3
        clips_summary = "\n".join([
            f"- [{c.get('timestamp_start', '')}] {c.get('speaker', 'Unknown')}: \"{c.get('quote', '')[:100]}...\""
            for c in batch_result.get("clips", [])[:20]  # Limit for context
        ])

        quotes_summary = "\n".join([
            f"- {q.get('speaker', 'Unknown')} [{q.get('timestamp', '')}]: \"{q.get('text', '')[:100]}...\""
            for q in batch_result.get("quotes", [])[:20]
        ])

        videos_list = "\n".join([
            f"- {r.get('video_info', {}).get('title', r.get('video_url', 'Unknown'))}"
            for r in results
        ])

        # Pass 2: Structure analysis for each video
        total_videos = len(results)
        safe_progress(2, total_passes, "analyzing_structure", f"Analyzing video structure (0/{total_videos})...")

        content_blueprints = []
        pass2_errors = []
        
        for i, result in enumerate(results):
            video_url = result.get("video_url", "")
            video_title = result.get("video_info", {}).get("title", "Unknown")
            
            # Update progress per-video for better UX
            safe_progress(2, total_passes, "analyzing_structure", f"Analyzing video {i+1}/{total_videos}: {video_title[:40]}...")
            
            # H-010: Add small delay between videos to avoid rate limiting
            # Skip delay on first video
            if i > 0:
                time.sleep(0.5)  # 500ms delay between API calls

            # Handle new tuple return signature
            blueprint_result = self.analyze_video_structure(video_url, video_title, model=model)
            
            # Unpack tuple (blueprint, cost, error)
            if isinstance(blueprint_result, tuple):
                blueprint, bp_cost, bp_error = blueprint_result
                total_cost += bp_cost
                if bp_error:
                    pass2_errors.append(f"Pass 2: {video_title[:50]} - {bp_error}")
                    pipeline_errors.append(f"Pass 2: {video_title[:50]} - {bp_error}")
            else:
                # Backward compatibility if somehow old signature is used
                blueprint = blueprint_result
            
            content_blueprints.append(blueprint)

        # Pass 3: Gap analysis
        safe_progress(3, total_passes, "analyzing_gaps", "Identifying gaps and missing perspectives...")

        # Handle new tuple return signature
        gap_result = self.analyze_gaps(
            clips_summary=clips_summary,
            quotes_summary=quotes_summary,
            videos_list=videos_list,
            num_videos=len(results),
            model=model,
        )
        
        # Unpack tuple (gap_analysis, cost, error)
        if isinstance(gap_result, tuple):
            gap_analysis, gap_cost, gap_error = gap_result
            total_cost += gap_cost
            if gap_error:
                pipeline_errors.append(f"Pass 3: {gap_error}")
        else:
            # Backward compatibility
            gap_analysis = gap_result

        # Pass 4: Research starter
        safe_progress(4, total_passes, "generating_research", "Generating research starting points...")

        # Handle new tuple return signature
        starter_result = self.generate_research_starter(
            gap_analysis=gap_analysis,
            research_topic=research_topic,
            num_videos=len(results),
            model=model,
        )
        
        # Unpack tuple (research_starter, cost, error)
        if isinstance(starter_result, tuple):
            research_starter, starter_cost, starter_error = starter_result
            total_cost += starter_cost
            if starter_error:
                pipeline_errors.append(f"Pass 4: {starter_error}")
        else:
            # Backward compatibility
            research_starter = starter_result

        safe_progress(4, total_passes, "complete", "Pipeline complete!")

        # Determine overall status
        if pipeline_errors:
            # Check if critical passes failed
            critical_failures = [e for e in pipeline_errors if "Pass 3:" in e or "Pass 4:" in e]
            if critical_failures:
                status = "completed_with_errors"
            else:
                status = "completed_with_warnings"
        else:
            status = "completed"

        return {
            "status": status,
            "research_topic": research_topic,
            # Pass 1 outputs - include results for video metadata
            "results": batch_result.get("results", []),
            "clips": batch_result.get("clips", []),
            "quotes": batch_result.get("quotes", []),
            "videos_processed": batch_result.get("videos_processed", 0),
            "videos_failed": batch_result.get("videos_failed", 0),
            "extraction_errors": batch_result.get("errors", []),
            # Pass 2 outputs
            "content_blueprints": content_blueprints,
            # Pass 3 output
            "gap_analysis": gap_analysis,
            # Pass 4 output
            "research_starter": research_starter,
            # H-002: Cost tracking
            "total_cost": total_cost,
            # H-013: Error tracking
            "pipeline_errors": pipeline_errors,
        }


# Convenience functions for pipeline use

def generate_with_gemini(
    prompt: str,
    model: str = "gemini-2.5-flash",
    **kwargs
) -> str:
    """Generate text with Gemini. Returns text only."""
    client = GeminiClient()
    response = client.generate(prompt, model=model, **kwargs)
    return response["text"]


def plan_with_gemini(
    prompt: str,
    system_instruction: Optional[str] = None,
) -> str:
    """Plan using Gemini Flash with thinking mode."""
    client = GeminiClient()
    response = client.generate_with_thinking(
        prompt,
        model="gemini-2.5-flash",
        thinking_budget=2048,
        system_instruction=system_instruction,
    )
    return response["text"]


def analyze_image_with_gemini(image_path: str, prompt: str) -> str:
    """Analyze image with Gemini Pro vision. Returns text only."""
    client = GeminiClient()
    response = client.analyze_image(image_path, prompt)
    return response["text"]


def analyze_pdf_with_gemini(pdf_path: str, prompt: str) -> str:
    """Analyze PDF with Gemini Pro. Returns text only."""
    client = GeminiClient()
    response = client.analyze_pdf(pdf_path, prompt)
    return response["text"]
