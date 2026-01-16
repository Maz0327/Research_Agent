"""
OCR Extraction Stage - Extract text from screenshots using Gemini Vision.

This stage runs for screenshot input jobs to extract text content
before semantic extraction. Uses Gemini 2.5 Pro Vision for OCR.

Based on: docs/authoritative/spec/RASS.md Section 4.2 Extended Inputs
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from loguru import logger

from backend.models.semantic_units import AnalysisMode, ConfidenceLevel
from backend.pipeline.context import PipelineContext
from backend.state import update_job


@dataclass
class OCRResult:
    """Result of OCR extraction from screenshot."""

    text: str
    word_count: int
    confidence: str  # "high", "medium", "low"
    platform_detected: Optional[str] = None  # May differ from hint
    missing_context_warning: bool = False  # True if content appears incomplete
    error_message: Optional[str] = None


def extract_text_from_screenshot(
    image_path: str,
    platform_hint: str = "other",
) -> OCRResult:
    """
    Extract text from screenshot using Gemini Vision.

    Args:
        image_path: Path to the screenshot image file
        platform_hint: Platform type ("reddit", "twitter", "forum", "other")

    Returns:
        OCRResult with extracted text and metadata
    """
    from backend.integrations.gemini_client import GeminiClient

    logger.info(f"OCR extraction starting for {image_path} (platform: {platform_hint})")

    # Validate file exists
    path = Path(image_path)
    if not path.exists():
        return OCRResult(
            text="",
            word_count=0,
            confidence="low",
            error_message=f"Screenshot file not found: {image_path}",
        )

    # Build OCR prompt based on platform hint
    platform_prompts = {
        "reddit": """Extract ALL text from this Reddit screenshot.
Include: post title, author, subreddit, post content, comments, usernames, timestamps.
Preserve the hierarchical structure of comments with indentation markers.
Note if the content appears to be a partial view (mid-thread).""",

        "twitter": """Extract ALL text from this Twitter/X screenshot.
Include: username, handle, tweet text, timestamp, reply/retweet info.
Note if this is part of a thread or a single tweet.
Include any quoted tweets or media descriptions.""",

        "forum": """Extract ALL text from this forum screenshot.
Include: thread title, author, post content, timestamps, reply hierarchy.
Preserve formatting indicators (quotes, code blocks).
Note if the content appears mid-conversation.""",

        "other": """Extract ALL text from this screenshot.
Include: all visible text, labels, headings, body content.
Preserve structure and hierarchy where possible.
Note if content appears to be incomplete or cropped.""",
    }

    prompt = platform_prompts.get(platform_hint, platform_prompts["other"])
    prompt += """

OUTPUT FORMAT:
{
  "extracted_text": "The complete extracted text content",
  "platform_detected": "reddit|twitter|forum|email|article|other",
  "content_quality": "high|medium|low",
  "is_partial": true/false,
  "partial_reason": "If is_partial is true, explain why (cropped, mid-thread, etc.)"
}

Extract every piece of text visible in the image. Do not summarize or paraphrase.
If text is unclear, include it with [unclear] marker."""

    try:
        client = GeminiClient()

        # Call Gemini with image using analyze_image method
        result = client.analyze_image(
            image_path=str(path),
            prompt=prompt,
            model="gemini-2.5-pro",  # Use Pro for vision
        )

        text_response = result.get("text", "") if isinstance(result, dict) else result

        if not text_response:
            return OCRResult(
                text="",
                word_count=0,
                confidence="low",
                error_message="Gemini returned empty response",
            )

        # Parse response
        import json
        try:
            # Try to extract JSON from code block if present
            json_text = text_response
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(json_text)
            extracted_text = parsed.get("extracted_text", "")
            platform_detected = parsed.get("platform_detected", platform_hint)
            content_quality = parsed.get("content_quality", "medium")
            is_partial = parsed.get("is_partial", False)

        except json.JSONDecodeError:
            # Fallback: treat entire response as extracted text
            extracted_text = text_response
            platform_detected = platform_hint
            content_quality = "medium"
            is_partial = False

        word_count = len(extracted_text.split()) if extracted_text else 0

        logger.info(
            f"OCR extraction complete: {word_count} words, "
            f"platform: {platform_detected}, quality: {content_quality}"
        )

        return OCRResult(
            text=extracted_text,
            word_count=word_count,
            confidence=content_quality,
            platform_detected=platform_detected,
            missing_context_warning=is_partial,
        )

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return OCRResult(
            text="",
            word_count=0,
            confidence="low",
            error_message=str(e),
        )


def stage_ocr_extraction(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Extract text from screenshots via OCR.

    This stage runs for screenshot_input jobs before source_identity.
    It extracts text from the uploaded screenshot and stores it in
    the job config for the source_identity stage to process.

    The extracted text will be used to create a SourceIdentityPackage
    with analysis_mode=OCR_EXTRACTED.
    """
    logger.info(f"[{ctx.job_id}] Stage: OCR Extraction")

    # Check if this is a screenshot input job
    job_type = ctx.job_config_dict.get("job_type")
    if job_type != "screenshot_input":
        logger.info(f"[{ctx.job_id}] Skipping OCR - not a screenshot input job")
        return

    update_job(
        ctx.job_id,
        stage="ocr_extraction",
        progress_percent=15,
    )

    screenshot_path = ctx.job_config_dict.get("screenshot_path")
    platform_hint = ctx.job_config_dict.get("platform_hint", "other")

    if not screenshot_path:
        ctx.add_warning("No screenshot path found in job config")
        return

    # Run OCR extraction
    result = extract_text_from_screenshot(screenshot_path, platform_hint)

    if result.error_message:
        ctx.add_warning(f"OCR extraction failed: {result.error_message}")
        # Continue anyway - we'll handle degraded mode in source_identity

    # Store OCR results in context for downstream stages
    ctx.ocr_result = result

    # Update job with OCR results
    update_job(
        ctx.job_id,
        partial_outputs={
            "ocr_extraction": {
                "word_count": result.word_count,
                "confidence": result.confidence,
                "platform_detected": result.platform_detected,
                "missing_context_warning": result.missing_context_warning,
                "error": result.error_message,
            }
        },
    )

    if result.word_count > 0:
        logger.info(
            f"[{ctx.job_id}] OCR complete: {result.word_count} words extracted "
            f"(confidence: {result.confidence})"
        )
    else:
        ctx.add_warning("OCR extraction returned no text")

    # Cleanup temp file after extraction
    try:
        path = Path(screenshot_path)
        if path.exists():
            path.unlink()
            logger.debug(f"Cleaned up temp screenshot: {screenshot_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp screenshot: {e}")
