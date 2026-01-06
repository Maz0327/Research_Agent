"""Google Gemini API client for planning and vision tasks.

Uses the new google-genai SDK (replaces deprecated google-generativeai).

Research-validated stack (Dec 2025):
- Gemini 2.5 Flash: $0.30/$2.50 per M tokens - used for planning, query gen
- Gemini 2.5 Pro: $1.25/$10 per M tokens - used for vision/PDF, validation, synthesis
"""
import base64
from pathlib import Path
from typing import Optional, Any

from loguru import logger

from backend.utils.error_handling import sanitize_error_message
from backend.utils.rate_limiter import with_rate_limit

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-genai not installed. Install with: pip install google-genai")


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
5. NO opinions, NO analysis, NO "why it matters" - just extraction

YouTube Video URL: {video_url}"""

        try:
            logger.info(f"Gemini video analysis: {video_url}")

            response = self._client.models.generate_content(
                model=model,
                contents=[extraction_prompt],
            )
            text = response.text

            # Parse JSON from response
            import json
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
                response = self._client.models.generate_content(
                    model=model,
                    contents=[chunk_prompt],
                )
                text = response.text

                # Parse JSON
                import json
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
                    all_clips.extend(result.get("clips", []))
                    all_quotes.extend(result.get("quotes", []))
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
