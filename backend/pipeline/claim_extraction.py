"""Claim Extraction Pipeline for the Claim Extractor feature.

This module handles extracting claims from various source types:
- YouTube videos (with timestamp anchors)
- Articles/URLs (with line range anchors)
- User-provided text (with line range anchors)
- Screenshots (with image index anchors)

Key Design Decisions:
- NO claim verification - extraction only
- NO source retrieval - only analyze provided inputs
- Claims have anchors to locate them in source material
- Output stored as ClaimsDocument in Supabase Storage
"""
from datetime import datetime, timezone
from typing import Any, Optional, Callable

from loguru import logger

from backend.models.claims import (
    Claim,
    ClaimAnchor,
    ClaimType,
    ClaimsDocument,
    ClaimsDocumentMetadata,
    ConfidenceLevel,
    ImageAnchor,
    LineRangeAnchor,
    SourceSummary,
    SourceType,
    TimestampAnchor,
)


# Prompt templates for claim extraction

CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are a claim extraction specialist. Your job is to identify ALL claims made in the provided content.

A claim is any statement that:
1. Asserts something is true or false
2. Makes a factual statement (even if unverified)
3. Expresses an opinion presented as fact
4. Implies something through context

Types of claims:
- EXPLICIT: Directly stated in the content
- IMPLIED: Not directly stated but clearly suggested by the context

For each claim, you must:
1. Extract the exact claim statement
2. Classify it as explicit or implied
3. Assign a confidence level (high/medium/low) based on clarity
4. Provide an anchor (location reference) in the source

IMPORTANT RULES:
- Extract ALL claims, not just controversial ones
- Do NOT verify claims - just extract them
- Do NOT add claims not present in the source
- Include both major and minor claims
- Be thorough - missing claims is worse than over-extracting"""

YOUTUBE_EXTRACTION_PROMPT = """Analyze this YouTube video transcript and extract ALL claims made.

VIDEO TITLE: {title}
VIDEO URL: {url}

TRANSCRIPT:
{transcript}

For each claim found, provide:
1. claim_text: The claim statement (paraphrase if needed for clarity)
2. claim_type: "explicit" or "implied"
3. confidence: "high", "medium", or "low"
4. timestamp_start: Start time in seconds where claim appears
5. timestamp_end: End time in seconds (optional, use same as start if point-in-time)
6. context: Brief surrounding context (1-2 sentences)

Return a JSON object with this structure:
{{
  "claims": [
    {{
      "claim_text": "string",
      "claim_type": "explicit" | "implied",
      "confidence": "high" | "medium" | "low",
      "timestamp_start": number,
      "timestamp_end": number | null,
      "context": "string"
    }}
  ]
}}"""

TEXT_EXTRACTION_PROMPT = """Analyze this text content and extract ALL claims made.

SOURCE TITLE: {title}
SOURCE TYPE: {source_type}

CONTENT:
{content}

For each claim found, provide:
1. claim_text: The claim statement (paraphrase if needed for clarity)
2. claim_type: "explicit" or "implied"
3. confidence: "high", "medium", or "low"
4. start_line: Line number where claim starts (1-indexed)
5. end_line: Line number where claim ends
6. excerpt: The exact text that contains the claim (up to 200 chars)
7. context: Brief surrounding context (1-2 sentences)

Return a JSON object with this structure:
{{
  "claims": [
    {{
      "claim_text": "string",
      "claim_type": "explicit" | "implied",
      "confidence": "high" | "medium" | "low",
      "start_line": number,
      "end_line": number,
      "excerpt": "string",
      "context": "string"
    }}
  ]
}}"""

SCREENSHOT_EXTRACTION_PROMPT = """Analyze this screenshot image and extract ALL claims visible in it.

IMAGE INDEX: {image_index}
PLATFORM HINT: {platform_hint}
OCR TEXT (if available):
{ocr_text}

For each claim found, provide:
1. claim_text: The claim statement
2. claim_type: "explicit" or "implied"
3. confidence: "high", "medium", or "low"
4. region: Where in the image the claim appears (e.g., "top", "center", "bottom-left")
5. ocr_excerpt: The exact text containing the claim (if OCR available)
6. context: Brief context about what the image shows

Return a JSON object with this structure:
{{
  "claims": [
    {{
      "claim_text": "string",
      "claim_type": "explicit" | "implied",
      "confidence": "high" | "medium" | "low",
      "region": "string",
      "ocr_excerpt": "string" | null,
      "context": "string"
    }}
  ]
}}"""


def format_timestamp(seconds: int) -> str:
    """Format seconds as human-readable timestamp (MM:SS or HH:MM:SS)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def extract_claims_from_youtube(
    gemini_client: Any,
    video_url: str,
    title: str,
    transcript: str,
    source_id: str,
    model: str = "gemini-2.5-flash",
) -> tuple[list[Claim], SourceSummary]:
    """Extract claims from a YouTube video transcript.

    Args:
        gemini_client: GeminiClient instance
        video_url: YouTube video URL
        title: Video title
        transcript: Video transcript text
        source_id: Unique source identifier (SRC_001, ...)
        model: Gemini model to use

    Returns:
        Tuple of (list of Claims, SourceSummary)
    """
    prompt = YOUTUBE_EXTRACTION_PROMPT.format(
        title=title,
        url=video_url,
        transcript=transcript,
    )

    try:
        result = gemini_client.generate_json(
            prompt=prompt,
            system_message=CLAIM_EXTRACTION_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,  # Low temperature for extraction
        )

        if result.get("error"):
            logger.warning(f"Claim extraction error for {video_url}: {result['error']}")
            return [], SourceSummary(
                source_id=source_id,
                source_type=SourceType.YOUTUBE,
                title=title,
                url=video_url,
                claim_count=0,
            )

        data = result.get("data", {})
        raw_claims = data.get("claims", [])

        claims: list[Claim] = []
        explicit_count = 0
        implied_count = 0

        for i, raw in enumerate(raw_claims):
            claim_type = ClaimType.EXPLICIT if raw.get("claim_type") == "explicit" else ClaimType.IMPLIED
            confidence = ConfidenceLevel(raw.get("confidence", "medium"))

            # Build timestamp anchor
            start_sec = raw.get("timestamp_start", 0)
            end_sec = raw.get("timestamp_end")
            if end_sec:
                formatted = f"{format_timestamp(start_sec)}-{format_timestamp(end_sec)}"
            else:
                formatted = format_timestamp(start_sec)
                end_sec = start_sec

            anchor = ClaimAnchor(
                timestamp=TimestampAnchor(
                    start_seconds=start_sec,
                    end_seconds=end_sec,
                    formatted=formatted,
                )
            )

            claim = Claim(
                claim_id=f"CLM_{source_id}_{i+1:03d}",
                text=raw.get("claim_text", ""),
                claim_type=claim_type,
                confidence=confidence,
                anchor=anchor,
                source_id=source_id,
                context=raw.get("context"),
            )
            claims.append(claim)

            if claim_type == ClaimType.EXPLICIT:
                explicit_count += 1
            else:
                implied_count += 1

        source_summary = SourceSummary(
            source_id=source_id,
            source_type=SourceType.YOUTUBE,
            title=title,
            url=video_url,
            claim_count=len(claims),
            explicit_count=explicit_count,
            implied_count=implied_count,
        )

        logger.info(f"Extracted {len(claims)} claims from YouTube video: {title}")
        return claims, source_summary

    except Exception as e:
        logger.error(f"Failed to extract claims from YouTube {video_url}: {e}")
        return [], SourceSummary(
            source_id=source_id,
            source_type=SourceType.YOUTUBE,
            title=title,
            url=video_url,
            claim_count=0,
        )


def extract_claims_from_text(
    gemini_client: Any,
    content: str,
    title: str,
    source_id: str,
    source_type: SourceType = SourceType.TEXT,
    url: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> tuple[list[Claim], SourceSummary]:
    """Extract claims from text content.

    Args:
        gemini_client: GeminiClient instance
        content: Text content to analyze
        title: Content title
        source_id: Unique source identifier
        source_type: Type of source (TEXT or ARTICLE)
        url: Optional URL for articles
        model: Gemini model to use

    Returns:
        Tuple of (list of Claims, SourceSummary)
    """
    prompt = TEXT_EXTRACTION_PROMPT.format(
        title=title,
        source_type=source_type.value,
        content=content,
    )

    try:
        result = gemini_client.generate_json(
            prompt=prompt,
            system_message=CLAIM_EXTRACTION_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,
        )

        if result.get("error"):
            logger.warning(f"Claim extraction error for {title}: {result['error']}")
            return [], SourceSummary(
                source_id=source_id,
                source_type=source_type,
                title=title,
                url=url,
                claim_count=0,
            )

        data = result.get("data", {})
        raw_claims = data.get("claims", [])

        claims: list[Claim] = []
        explicit_count = 0
        implied_count = 0

        for i, raw in enumerate(raw_claims):
            claim_type = ClaimType.EXPLICIT if raw.get("claim_type") == "explicit" else ClaimType.IMPLIED
            confidence = ConfidenceLevel(raw.get("confidence", "medium"))

            # Build line range anchor
            anchor = ClaimAnchor(
                line_range=LineRangeAnchor(
                    start_line=raw.get("start_line", 1),
                    end_line=raw.get("end_line", 1),
                    excerpt=raw.get("excerpt"),
                )
            )

            claim = Claim(
                claim_id=f"CLM_{source_id}_{i+1:03d}",
                text=raw.get("claim_text", ""),
                claim_type=claim_type,
                confidence=confidence,
                anchor=anchor,
                source_id=source_id,
                context=raw.get("context"),
            )
            claims.append(claim)

            if claim_type == ClaimType.EXPLICIT:
                explicit_count += 1
            else:
                implied_count += 1

        source_summary = SourceSummary(
            source_id=source_id,
            source_type=source_type,
            title=title,
            url=url,
            claim_count=len(claims),
            explicit_count=explicit_count,
            implied_count=implied_count,
        )

        logger.info(f"Extracted {len(claims)} claims from text: {title}")
        return claims, source_summary

    except Exception as e:
        logger.error(f"Failed to extract claims from text {title}: {e}")
        return [], SourceSummary(
            source_id=source_id,
            source_type=source_type,
            title=title,
            url=url,
            claim_count=0,
        )


def extract_claims_from_screenshot(
    gemini_client: Any,
    image_base64: str,
    image_index: int,
    source_id: str,
    platform_hint: Optional[str] = None,
    ocr_text: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> tuple[list[Claim], SourceSummary]:
    """Extract claims from a screenshot image.

    Args:
        gemini_client: GeminiClient instance
        image_base64: Base64-encoded image data
        image_index: Index of this screenshot (0-indexed)
        source_id: Unique source identifier
        platform_hint: Optional platform hint (twitter, reddit, etc.)
        ocr_text: Optional pre-extracted OCR text
        model: Gemini model to use

    Returns:
        Tuple of (list of Claims, SourceSummary)
    """
    prompt = SCREENSHOT_EXTRACTION_PROMPT.format(
        image_index=image_index,
        platform_hint=platform_hint or "unknown",
        ocr_text=ocr_text or "(No OCR text available)",
    )

    title = f"Screenshot #{image_index + 1}"
    if platform_hint:
        title = f"{platform_hint.title()} Screenshot #{image_index + 1}"

    try:
        # Use vision capabilities
        result = gemini_client.generate_json_with_image(
            prompt=prompt,
            image_base64=image_base64,
            system_message=CLAIM_EXTRACTION_SYSTEM_PROMPT,
            model=model,
            temperature=0.1,
        )

        if result.get("error"):
            logger.warning(f"Claim extraction error for screenshot {image_index}: {result['error']}")
            return [], SourceSummary(
                source_id=source_id,
                source_type=SourceType.SCREENSHOT,
                title=title,
                claim_count=0,
            )

        data = result.get("data", {})
        raw_claims = data.get("claims", [])

        claims: list[Claim] = []
        explicit_count = 0
        implied_count = 0

        for i, raw in enumerate(raw_claims):
            claim_type = ClaimType.EXPLICIT if raw.get("claim_type") == "explicit" else ClaimType.IMPLIED
            confidence = ConfidenceLevel(raw.get("confidence", "medium"))

            # Build image anchor
            anchor = ClaimAnchor(
                image=ImageAnchor(
                    image_index=image_index,
                    region=raw.get("region"),
                    ocr_excerpt=raw.get("ocr_excerpt"),
                )
            )

            claim = Claim(
                claim_id=f"CLM_{source_id}_{i+1:03d}",
                text=raw.get("claim_text", ""),
                claim_type=claim_type,
                confidence=confidence,
                anchor=anchor,
                source_id=source_id,
                context=raw.get("context"),
            )
            claims.append(claim)

            if claim_type == ClaimType.EXPLICIT:
                explicit_count += 1
            else:
                implied_count += 1

        source_summary = SourceSummary(
            source_id=source_id,
            source_type=SourceType.SCREENSHOT,
            title=title,
            claim_count=len(claims),
            explicit_count=explicit_count,
            implied_count=implied_count,
        )

        logger.info(f"Extracted {len(claims)} claims from screenshot {image_index}")
        return claims, source_summary

    except Exception as e:
        logger.error(f"Failed to extract claims from screenshot {image_index}: {e}")
        return [], SourceSummary(
            source_id=source_id,
            source_type=SourceType.SCREENSHOT,
            title=title,
            claim_count=0,
        )


def run_claim_extraction_pipeline(
    gemini_client: Any,
    job_id: str,
    title: str,
    video_urls: list[str] = None,
    article_urls: list[str] = None,
    text_inputs: list[dict] = None,
    screenshots: list[dict] = None,
    model: str = "gemini-2.5-flash",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> ClaimsDocument:
    """Run the complete claim extraction pipeline.

    Args:
        gemini_client: GeminiClient instance
        job_id: Job identifier
        title: Job title
        video_urls: List of YouTube URLs to analyze
        article_urls: List of article URLs to fetch and analyze
        text_inputs: List of dicts with {title, content}
        screenshots: List of dicts with {filename, base64, platform_hint}
        model: Gemini model to use
        progress_callback: Optional callback(current, total, status)

    Returns:
        ClaimsDocument with all extracted claims
    """
    from backend.integrations.supadata_client import SupadataClient

    video_urls = video_urls or []
    article_urls = article_urls or []
    text_inputs = text_inputs or []
    screenshots = screenshots or []

    # Calculate total sources for progress
    total_sources = len(video_urls) + len(article_urls) + len(text_inputs) + len(screenshots)
    current_source = 0

    # Create claims document
    doc = ClaimsDocument.create_empty(job_id, title)
    doc.metadata.extraction_model = model

    # Process YouTube videos
    for i, url in enumerate(video_urls):
        current_source += 1
        if progress_callback:
            progress_callback(current_source, total_sources, f"Processing video {i+1}/{len(video_urls)}")

        source_id = f"SRC_{current_source:03d}"

        # Fetch transcript using Supadata
        try:
            supadata = SupadataClient()
            transcript_result = supadata.get_transcript(url)
            transcript = transcript_result.get("transcript", "")
            video_title = transcript_result.get("title", f"Video {i+1}")

            if not transcript:
                logger.warning(f"No transcript available for {url}")
                doc.add_source(SourceSummary(
                    source_id=source_id,
                    source_type=SourceType.YOUTUBE,
                    title=video_title,
                    url=url,
                    claim_count=0,
                ))
                continue

            claims, summary = extract_claims_from_youtube(
                gemini_client, url, video_title, transcript, source_id, model
            )
            doc.add_source(summary)
            for claim in claims:
                doc.add_claim(claim)

        except Exception as e:
            logger.error(f"Failed to process YouTube video {url}: {e}")
            doc.add_source(SourceSummary(
                source_id=source_id,
                source_type=SourceType.YOUTUBE,
                title=f"Video {i+1}",
                url=url,
                claim_count=0,
            ))

    # Process article URLs
    for i, url in enumerate(article_urls):
        current_source += 1
        if progress_callback:
            progress_callback(current_source, total_sources, f"Processing article {i+1}/{len(article_urls)}")

        source_id = f"SRC_{current_source:03d}"

        # Fetch article content
        try:
            from backend.integrations.firecrawl_client import FirecrawlClient

            firecrawl = FirecrawlClient()
            article = firecrawl.scrape_url(url)
            content = article.get("content", article.get("markdown", ""))
            article_title = article.get("title", f"Article {i+1}")

            if not content:
                logger.warning(f"No content fetched for {url}")
                doc.add_source(SourceSummary(
                    source_id=source_id,
                    source_type=SourceType.ARTICLE,
                    title=article_title,
                    url=url,
                    claim_count=0,
                ))
                continue

            claims, summary = extract_claims_from_text(
                gemini_client, content, article_title, source_id,
                source_type=SourceType.ARTICLE, url=url, model=model
            )
            doc.add_source(summary)
            for claim in claims:
                doc.add_claim(claim)

        except Exception as e:
            logger.error(f"Failed to process article {url}: {e}")
            doc.add_source(SourceSummary(
                source_id=source_id,
                source_type=SourceType.ARTICLE,
                title=f"Article {i+1}",
                url=url,
                claim_count=0,
            ))

    # Process text inputs
    for i, text_input in enumerate(text_inputs):
        current_source += 1
        if progress_callback:
            progress_callback(current_source, total_sources, f"Processing text {i+1}/{len(text_inputs)}")

        source_id = f"SRC_{current_source:03d}"
        text_title = text_input.get("title", f"Text Input {i+1}")
        content = text_input.get("content", "")

        if not content:
            doc.add_source(SourceSummary(
                source_id=source_id,
                source_type=SourceType.TEXT,
                title=text_title,
                claim_count=0,
            ))
            continue

        claims, summary = extract_claims_from_text(
            gemini_client, content, text_title, source_id,
            source_type=SourceType.TEXT, model=model
        )
        doc.add_source(summary)
        for claim in claims:
            doc.add_claim(claim)

    # Process screenshots
    for i, screenshot in enumerate(screenshots):
        current_source += 1
        if progress_callback:
            progress_callback(current_source, total_sources, f"Processing screenshot {i+1}/{len(screenshots)}")

        source_id = f"SRC_{current_source:03d}"
        image_base64 = screenshot.get("base64", "")
        platform_hint = screenshot.get("platform_hint")

        if not image_base64:
            doc.add_source(SourceSummary(
                source_id=source_id,
                source_type=SourceType.SCREENSHOT,
                title=f"Screenshot {i+1}",
                claim_count=0,
            ))
            continue

        claims, summary = extract_claims_from_screenshot(
            gemini_client, image_base64, i, source_id,
            platform_hint=platform_hint, model=model
        )
        doc.add_source(summary)
        for claim in claims:
            doc.add_claim(claim)

    logger.info(
        f"Claim extraction complete: {doc.metadata.total_claims} claims from {doc.metadata.source_count} sources"
    )
    return doc
