"""Kimi K2.5 Vision client for visual analysis of video frames.

Follows gemini_client.py patterns: custom exceptions, rate limiting,
cost tracking, defensive JSON parsing.

Usage:
    from backend.integrations.kimi_vision_client import KimiVisionClient

    client = KimiVisionClient()
    result = client.analyze_video_frames(
        frame_paths=[Path("frame_0001.jpg"), ...],
        video_title="Source Video Title",
        research_topic="Topic being researched",
        source_id="SRC_1",
    )
    print(result.to_dict())

Requirements:
    - KIMI_API_KEY (Moonshot API key) in environment or config
    - httpx package installed
"""

import base64
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KIMI_API_BASE = "https://api.moonshot.ai/v1"
KIMI_MODEL = "kimi-k2.5"
KIMI_TIMEOUT_SECONDS = 120
KIMI_RATE_LIMIT_DELAY = 1.0  # Seconds between API calls
MAX_FRAMES_PER_REQUEST = 20   # API limit
VISION_TEMPERATURE = 0.1       # Low for factual visual analysis


# ---------------------------------------------------------------------------
# Custom Exceptions (following gemini_client.py patterns)
# ---------------------------------------------------------------------------
class KimiVisionError(Exception):
    """Base exception for Kimi Vision API errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class KimiVisionTimeoutError(KimiVisionError):
    """Raised when Kimi API call times out."""
    pass


class KimiVisionParseError(KimiVisionError):
    """Raised when Kimi response cannot be parsed as valid JSON."""
    def __init__(self, message: str, raw_response: str = ""):
        self.raw_response = raw_response
        super().__init__(message)


class KimiVisionRateLimitError(KimiVisionError):
    """Raised when Kimi API rate limit is hit."""
    pass


class KimiVisionConfigError(KimiVisionError):
    """Raised when Kimi API key is not configured."""
    pass


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------
@dataclass
class FrameAnalysis:
    """Analysis result for a single frame."""
    frame_index: int
    timestamp_approx: str = ""        # e.g. "0:00:15"
    content_type: str = ""            # "interview", "b-roll", "infographic", etc.
    is_original_content: bool = False # Creator's own camera work
    is_third_party: bool = False      # Third-party footage (movie, news, etc.)
    confidence: str = ""              # "high", "medium", "low"
    text_detected: str = ""           # Any on-screen text
    notable_elements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "timestamp_approx": self.timestamp_approx,
            "content_type": self.content_type,
            "is_original_content": self.is_original_content,
            "is_third_party": self.is_third_party,
            "confidence": self.confidence,
            "text_detected": self.text_detected,
            "notable_elements": self.notable_elements,
        }


@dataclass
class VideoVisualAnalysis:
    """Complete visual analysis for a video source."""
    source_id: str
    frame_analyses: list[FrameAnalysis] = field(default_factory=list)
    overall_content_mix: str = ""     # Summary of content types
    third_party_ratio: float = 0.0    # 0.0-1.0 ratio of third-party content
    analysis_cost: float = 0.0

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "frame_analyses": [f.to_dict() for f in self.frame_analyses],
            "overall_content_mix": self.overall_content_mix,
            "third_party_ratio": self.third_party_ratio,
            "analysis_cost": self.analysis_cost,
        }


# ---------------------------------------------------------------------------
# Vision prompt
# ---------------------------------------------------------------------------
FRAME_ANALYSIS_PROMPT = """Analyze these video frames from '{video_title}' for documentary research on: {research_topic}

For each frame, identify:
1. content_type: What type of content (interview, b-roll, infographic, screen_recording, movie_clip, news_clip, stock_footage, title_card, original_camera, other)
2. is_original_content: Is this the creator's own camera work? (true/false)
3. is_third_party: Is this footage from another source (movie, news, stock)? (true/false)
4. confidence: How confident are you in the classification? (high/medium/low)
5. text_detected: Any readable text on screen
6. notable_elements: List of visually notable elements (people, logos, locations, etc.)

Also provide:
- overall_content_mix: A sentence summarizing the visual content distribution
- third_party_ratio: Estimated ratio (0.0-1.0) of frames showing third-party content

Return JSON:
{{
    "frame_analyses": [
        {{
            "frame_index": 0,
            "content_type": "...",
            "is_original_content": false,
            "is_third_party": true,
            "confidence": "high",
            "text_detected": "...",
            "notable_elements": ["..."]
        }}
    ],
    "overall_content_mix": "...",
    "third_party_ratio": 0.5
}}"""


# ---------------------------------------------------------------------------
# Helper: strip markdown code fences from JSON
# ---------------------------------------------------------------------------
def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences from LLM JSON response."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        # Find the end of the first line (might be ```json)
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        # Remove trailing ```
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class KimiVisionClient:
    """Client for Kimi K2.5 Vision API (Moonshot).

    Follows gemini_client.py patterns:
    - Custom exceptions for different failure modes
    - Rate limiting between calls
    - Cost tracking
    - Defensive JSON parsing
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Kimi Vision client.

        Args:
            api_key: Moonshot API key. Falls back to KIMI_API_KEY env var.

        Raises:
            KimiVisionConfigError: If no API key is configured.
        """
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        if not self.api_key:
            raise KimiVisionConfigError(
                "KIMI_API_KEY not configured. "
                "Set it in your .env file or pass it directly."
            )
        self.base_url = KIMI_API_BASE
        self._last_call_time = 0.0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self._last_call_time
        if elapsed < KIMI_RATE_LIMIT_DELAY:
            time.sleep(KIMI_RATE_LIMIT_DELAY - elapsed)
        self._last_call_time = time.time()

    def _encode_frame(self, frame_path: Path) -> str:
        """Read and base64-encode a frame image."""
        with open(frame_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def analyze_video_frames(
        self,
        frame_paths: list[Path],
        video_title: str,
        research_topic: str,
        source_id: str = "",
        interval_seconds: int = 5,
    ) -> VideoVisualAnalysis:
        """Analyze video frames with Kimi K2.5 Vision.

        Args:
            frame_paths: List of frame image paths
            video_title: Title of the source video
            research_topic: Research topic for context
            source_id: Source identifier
            interval_seconds: Time interval between frames (for timestamp calc)

        Returns:
            VideoVisualAnalysis with per-frame and aggregate results

        Raises:
            KimiVisionError: On API errors
            KimiVisionTimeoutError: On timeout
            KimiVisionParseError: On response parse failure
            KimiVisionRateLimitError: On rate limit
        """
        # Lazy import httpx to avoid hard dependency
        try:
            import httpx
        except ImportError:
            raise KimiVisionError(
                "httpx package is required for Kimi Vision. "
                "Install with: pip install httpx"
            )

        # Limit frames
        frames_to_analyze = frame_paths[:MAX_FRAMES_PER_REQUEST]
        if len(frame_paths) > MAX_FRAMES_PER_REQUEST:
            logger.warning(
                f"Limiting to {MAX_FRAMES_PER_REQUEST} frames "
                f"(received {len(frame_paths)})"
            )

        # Encode frames
        logger.info(f"Encoding {len(frames_to_analyze)} frames for Kimi analysis")
        frames_b64 = []
        for path in frames_to_analyze:
            try:
                frames_b64.append(self._encode_frame(path))
            except Exception as e:
                logger.warning(f"Failed to encode frame {path}: {e}")

        if not frames_b64:
            logger.warning("No frames could be encoded for analysis")
            return VideoVisualAnalysis(source_id=source_id)

        # Build prompt
        prompt_text = FRAME_ANALYSIS_PROMPT.format(
            video_title=video_title,
            research_topic=research_topic,
        )

        # Build messages with images
        content_parts: list[dict[str, Any]] = [
            {"type": "text", "text": prompt_text}
        ]
        for frame_b64 in frames_b64:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}
            })

        messages = [
            {
                "role": "system",
                "content": "You analyze video frames for documentary research. "
                           "Return structured JSON only.",
            },
            {
                "role": "user",
                "content": content_parts,
            },
        ]

        # Rate limit
        self._rate_limit()

        # Call API
        logger.info(f"Calling Kimi K2.5 Vision with {len(frames_b64)} frames")
        try:
            with httpx.Client(timeout=KIMI_TIMEOUT_SECONDS) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": KIMI_MODEL,
                        "messages": messages,
                        "temperature": VISION_TEMPERATURE,
                        "response_format": {"type": "json_object"},
                    },
                )
        except httpx.TimeoutException:
            raise KimiVisionTimeoutError(
                f"Kimi API timed out after {KIMI_TIMEOUT_SECONDS}s"
            )
        except httpx.HTTPError as e:
            raise KimiVisionError(f"Kimi API HTTP error: {e}")

        # Check response status
        if response.status_code == 429:
            raise KimiVisionRateLimitError(
                "Kimi API rate limit exceeded. Wait and retry."
            )
        if response.status_code != 200:
            raise KimiVisionError(
                f"Kimi API error {response.status_code}: "
                f"{response.text[:500]}"
            )

        # Parse response
        try:
            resp_json = response.json()
        except Exception as e:
            raise KimiVisionParseError(
                f"Failed to parse Kimi response as JSON: {e}",
                raw_response=response.text[:1000],
            )

        # Extract content
        try:
            content = resp_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise KimiVisionParseError(
                f"Unexpected Kimi response structure: {e}",
                raw_response=json.dumps(resp_json)[:1000],
            )

        # Parse the JSON content
        content_cleaned = _strip_code_fences(content)
        try:
            data = json.loads(content_cleaned)
        except json.JSONDecodeError as e:
            raise KimiVisionParseError(
                f"Failed to parse Kimi content JSON: {e}",
                raw_response=content_cleaned[:1000],
            )

        # Extract cost estimate (from usage if available)
        usage = resp_json.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        # Rough cost estimate (Kimi pricing varies, estimate conservatively)
        cost = (prompt_tokens * 0.002 + completion_tokens * 0.006) / 1000

        # Parse frame analyses
        frame_analyses = []
        for fa in data.get("frame_analyses", []):
            idx = fa.get("frame_index", len(frame_analyses))
            # Calculate approximate timestamp
            timestamp_secs = idx * interval_seconds
            mins, secs = divmod(timestamp_secs, 60)
            hours, mins = divmod(mins, 60)
            timestamp = f"{hours}:{mins:02d}:{secs:02d}"

            frame_analyses.append(FrameAnalysis(
                frame_index=idx,
                timestamp_approx=timestamp,
                content_type=fa.get("content_type", ""),
                is_original_content=fa.get("is_original_content", False),
                is_third_party=fa.get("is_third_party", False),
                confidence=fa.get("confidence", ""),
                text_detected=fa.get("text_detected", ""),
                notable_elements=fa.get("notable_elements", []),
            ))

        # Calculate third-party ratio
        if frame_analyses:
            third_party_count = sum(
                1 for fa in frame_analyses if fa.is_third_party
            )
            third_party_ratio = third_party_count / len(frame_analyses)
        else:
            third_party_ratio = data.get("third_party_ratio", 0.0)

        result = VideoVisualAnalysis(
            source_id=source_id,
            frame_analyses=frame_analyses,
            overall_content_mix=data.get("overall_content_mix", ""),
            third_party_ratio=third_party_ratio,
            analysis_cost=cost,
        )

        logger.info(
            f"Kimi analysis complete for {source_id}: "
            f"{len(frame_analyses)} frames analyzed, "
            f"third-party ratio={third_party_ratio:.0%}, "
            f"cost=${cost:.4f}"
        )

        return result
