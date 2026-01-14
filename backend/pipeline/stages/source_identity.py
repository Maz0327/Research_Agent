"""
Source Identity Builder Stage - Pre-LLM deterministic identity resolution.

This stage runs BEFORE any LLM call to ensure Gemini receives:
- Resolved source_id (SRC_1, SRC_2, etc.)
- Determined transcript_source and analysis_mode
- Built TranscriptProvenance metadata
- Validated source accessibility

Based on: docs/authoritative/spec/RASS.md Section 4.2
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger

from backend.models.semantic_units import AnalysisMode, ConfidenceLevel
from backend.models.document_outputs import TranscriptProvenance
from backend.pipeline.context import PipelineContext
from backend.pipeline.transcript_acquisition import (
    TranscriptResult,
    acquire_transcript,
    is_transcript_available,
)
from backend.state import update_job


@dataclass
class SourceIdentityPackage:
    """
    Deterministic identity resolved BEFORE any LLM sees the data.

    This package contains everything needed for semantic extraction
    without requiring the LLM to guess or infer source identity.
    """
    # Stable identifiers
    source_id: str  # SRC_1, SRC_2, etc.
    source_type: str  # "youtube", "article", "reddit"

    # Canonical metadata
    url: str
    title: str
    creator: Optional[str] = None
    published: Optional[str] = None
    duration_seconds: Optional[int] = None

    # Transcript provenance (REQUIRED for video sources)
    transcript_source: Optional[str] = None  # "supadata", "whisper", "youtube_captions", "none"
    analysis_mode: AnalysisMode = AnalysisMode.VIDEO_ONLY

    # Content (resolved BEFORE LLM)
    content: Optional[str] = None  # Transcript text or web content
    content_word_count: Optional[int] = None

    # Validation status
    is_accessible: bool = True
    failure_reason: Optional[str] = None

    # Provenance metadata (full object)
    provenance: Optional[TranscriptProvenance] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "url": self.url,
            "title": self.title,
            "creator": self.creator,
            "published": self.published,
            "duration_seconds": self.duration_seconds,
            "transcript_source": self.transcript_source,
            "analysis_mode": self.analysis_mode.value,
            "content_word_count": self.content_word_count,
            "is_accessible": self.is_accessible,
            "failure_reason": self.failure_reason,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }

    @property
    def confidence_ceiling(self) -> ConfidenceLevel:
        """Return max allowed confidence based on analysis mode."""
        ceilings = {
            AnalysisMode.TRANSCRIPT_GROUNDED: ConfidenceLevel.HIGH,
            AnalysisMode.CAPTION_GROUNDED: ConfidenceLevel.MEDIUM,
            AnalysisMode.VIDEO_ONLY: ConfidenceLevel.LOW,
        }
        return ceilings.get(self.analysis_mode, ConfidenceLevel.LOW)


def build_source_identity_from_video(
    video_data: dict,
    source_index: int,
) -> SourceIdentityPackage:
    """
    Build identity package from YouTube video data.

    This function acquires the transcript and resolves all
    identity fields deterministically.

    Args:
        video_data: Video metadata from YouTube stage
        source_index: 0-based index for source_id generation

    Returns:
        SourceIdentityPackage with resolved identity
    """
    source_id = f"SRC_{source_index + 1}"
    url = video_data.get("url", video_data.get("video_url", ""))
    title = video_data.get("title", "Untitled Video")
    creator = video_data.get("channel", video_data.get("creator"))
    published = video_data.get("published", video_data.get("upload_date"))
    duration_seconds = video_data.get("duration_seconds")

    logger.info(f"Building identity for {source_id}: {title[:50]}...")

    # Acquire transcript with spec-compliant fallback chain
    transcript_result: Optional[TranscriptResult] = None
    content: Optional[str] = None
    transcript_source: Optional[str] = None
    analysis_mode = AnalysisMode.VIDEO_ONLY
    provenance: Optional[TranscriptProvenance] = None
    is_accessible = True
    failure_reason: Optional[str] = None

    try:
        transcript_result = acquire_transcript(url)

        if is_transcript_available(transcript_result):
            content = transcript_result.text
            transcript_source = transcript_result.transcript_source.value
            analysis_mode = transcript_result.analysis_mode
            provenance = transcript_result.to_provenance()
            logger.info(
                f"  ✓ Transcript acquired via {transcript_source} "
                f"(mode: {analysis_mode.value})"
            )
        else:
            # Transcript failed but video is still accessible
            transcript_source = "none"
            analysis_mode = AnalysisMode.VIDEO_ONLY
            provenance = transcript_result.to_provenance()
            failure_reason = transcript_result.error_message
            logger.warning(f"  ⚠ Transcript unavailable for {source_id}: {failure_reason}")

    except Exception as e:
        logger.error(f"  ✗ Failed to acquire transcript for {source_id}: {e}")
        is_accessible = False
        failure_reason = str(e)
        # Build degraded provenance
        provenance = TranscriptProvenance(
            transcript_source="none",
            transcript_status="failed",
            captions_status="failed",
            gemini_analysis_mode=AnalysisMode.VIDEO_ONLY,
            quote_verification=False,
            timestamp_grounding=False,
            semantic_precision=ConfidenceLevel.LOW,
            notes=str(e),
        )

    # Calculate word count
    content_word_count = len(content.split()) if content else 0

    return SourceIdentityPackage(
        source_id=source_id,
        source_type="youtube",
        url=url,
        title=title,
        creator=creator,
        published=published,
        duration_seconds=duration_seconds,
        transcript_source=transcript_source,
        analysis_mode=analysis_mode,
        content=content,
        content_word_count=content_word_count,
        is_accessible=is_accessible,
        failure_reason=failure_reason,
        provenance=provenance,
    )


def build_source_identity_from_article(
    article_data: dict,
    source_index: int,
) -> SourceIdentityPackage:
    """
    Build identity package from web article data.

    Articles are always TRANSCRIPT_GROUNDED since we have the full text.

    Args:
        article_data: Article metadata from web capture stage
        source_index: 0-based index for source_id generation

    Returns:
        SourceIdentityPackage with resolved identity
    """
    source_id = f"SRC_{source_index + 1}"
    url = article_data.get("url", "")
    title = article_data.get("title", "Untitled Article")
    creator = article_data.get("author", article_data.get("creator"))
    published = article_data.get("published", article_data.get("date"))
    content = article_data.get("content", article_data.get("text", ""))

    # Articles are always transcript_grounded (we have the text)
    analysis_mode = AnalysisMode.TRANSCRIPT_GROUNDED
    is_accessible = bool(content)
    failure_reason = None if content else "No content extracted"

    # Calculate word count
    content_word_count = len(content.split()) if content else 0

    # Build provenance for article (simpler than video)
    provenance = TranscriptProvenance(
        transcript_source="article_text",
        transcript_status="success" if content else "failed",
        captions_status="n/a",
        gemini_analysis_mode=analysis_mode,
        quote_verification=True,
        timestamp_grounding=False,  # Articles don't have timestamps
        semantic_precision=ConfidenceLevel.HIGH if content else ConfidenceLevel.LOW,
        notes=None if content else failure_reason,
    )

    return SourceIdentityPackage(
        source_id=source_id,
        source_type="article",
        url=url,
        title=title,
        creator=creator,
        published=published,
        transcript_source="article_text" if content else "none",
        analysis_mode=analysis_mode,
        content=content,
        content_word_count=content_word_count,
        is_accessible=is_accessible,
        failure_reason=failure_reason,
        provenance=provenance,
    )


def build_source_identity_from_reddit(
    post_data: dict,
    source_index: int,
) -> SourceIdentityPackage:
    """
    Build identity package from Reddit post data.

    Reddit posts are TRANSCRIPT_GROUNDED since we have the text.

    Args:
        post_data: Post metadata from Reddit stage
        source_index: 0-based index for source_id generation

    Returns:
        SourceIdentityPackage with resolved identity
    """
    source_id = f"SRC_{source_index + 1}"
    url = post_data.get("url", "")
    title = post_data.get("title", "Untitled Post")
    creator = post_data.get("author")
    published = post_data.get("created_utc")

    # Combine title, selftext, and comments
    content_parts = []
    if post_data.get("selftext"):
        content_parts.append(post_data["selftext"])
    for comment in post_data.get("comments", []):
        if comment.get("body"):
            content_parts.append(comment["body"])

    content = "\n\n".join(content_parts) if content_parts else ""

    analysis_mode = AnalysisMode.TRANSCRIPT_GROUNDED
    is_accessible = bool(content)
    failure_reason = None if content else "No content extracted"
    content_word_count = len(content.split()) if content else 0

    provenance = TranscriptProvenance(
        transcript_source="reddit_text",
        transcript_status="success" if content else "failed",
        captions_status="n/a",
        gemini_analysis_mode=analysis_mode,
        quote_verification=True,
        timestamp_grounding=False,
        semantic_precision=ConfidenceLevel.HIGH if content else ConfidenceLevel.LOW,
        notes=None if content else failure_reason,
    )

    return SourceIdentityPackage(
        source_id=source_id,
        source_type="reddit",
        url=url,
        title=title,
        creator=creator,
        published=str(published) if published else None,
        transcript_source="reddit_text" if content else "none",
        analysis_mode=analysis_mode,
        content=content,
        content_word_count=content_word_count,
        is_accessible=is_accessible,
        failure_reason=failure_reason,
        provenance=provenance,
    )


def stage_source_identity(ctx: PipelineContext) -> None:
    """
    Pipeline stage: Build source identity packages BEFORE any LLM call.

    This stage:
    1. Collects all sources from previous stages (videos, articles, reddit)
    2. Acquires transcripts for video sources
    3. Assigns stable source_id (SRC_1, SRC_2, ...)
    4. Builds TranscriptProvenance metadata
    5. Stores packages in ctx.source_identity_packages

    The output ctx.source_identity_packages is consumed by semantic_extraction.
    """
    logger.info(f"[{ctx.job_id}] Stage: Source Identity Builder")

    update_job(
        ctx.job_id,
        stage="source_identity",
        progress_percent=30,
    )

    packages: list[SourceIdentityPackage] = []
    source_index = 0

    # Process YouTube videos
    for video in ctx.youtube_videos:
        try:
            package = build_source_identity_from_video(video, source_index)
            packages.append(package)
            source_index += 1

            if not package.is_accessible:
                ctx.add_warning(
                    f"Source {package.source_id} ({package.title[:30]}...) "
                    f"is not accessible: {package.failure_reason}"
                )

        except Exception as e:
            logger.error(f"Failed to build identity for video: {e}")
            ctx.add_warning(f"Failed to process video source: {str(e)}")

    # Process web articles (from web_sources with content)
    for article in ctx.web_sources:
        # Only process articles that have been captured (have content)
        if not article.get("content") and not article.get("text"):
            continue

        try:
            package = build_source_identity_from_article(article, source_index)
            packages.append(package)
            source_index += 1

            if not package.is_accessible:
                ctx.add_warning(
                    f"Source {package.source_id} ({package.title[:30]}...) "
                    f"has no content: {package.failure_reason}"
                )

        except Exception as e:
            logger.error(f"Failed to build identity for article: {e}")
            ctx.add_warning(f"Failed to process article source: {str(e)}")

    # Process Reddit posts
    for post in ctx.reddit_posts:
        try:
            package = build_source_identity_from_reddit(post, source_index)
            packages.append(package)
            source_index += 1

            if not package.is_accessible:
                ctx.add_warning(
                    f"Source {package.source_id} ({package.title[:30]}...) "
                    f"has no content: {package.failure_reason}"
                )

        except Exception as e:
            logger.error(f"Failed to build identity for reddit post: {e}")
            ctx.add_warning(f"Failed to process reddit source: {str(e)}")

    # Store packages in context for downstream stages
    ctx.source_identity_packages = packages

    # Summary statistics
    accessible_count = sum(1 for p in packages if p.is_accessible)
    video_only_count = sum(1 for p in packages if p.analysis_mode == AnalysisMode.VIDEO_ONLY)
    transcript_grounded_count = sum(
        1 for p in packages if p.analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED
    )

    logger.info(
        f"Source identity complete: {len(packages)} packages "
        f"({accessible_count} accessible, {transcript_grounded_count} transcript_grounded, "
        f"{video_only_count} video_only)"
    )

    # Update job with identity summary
    update_job(
        ctx.job_id,
        partial_outputs={
            "source_identity_summary": {
                "total_sources": len(packages),
                "accessible": accessible_count,
                "transcript_grounded": transcript_grounded_count,
                "video_only": video_only_count,
                "sources": [p.to_dict() for p in packages],
            }
        },
    )

    # Warn if all sources are inaccessible
    if accessible_count == 0 and len(packages) > 0:
        ctx.add_warning("All sources are inaccessible - output will be severely degraded")

    # Warn if all video sources are video_only
    video_packages = [p for p in packages if p.source_type == "youtube"]
    if video_packages and all(p.analysis_mode == AnalysisMode.VIDEO_ONLY for p in video_packages):
        ctx.add_warning(
            "All video sources are in video_only mode - no transcripts available. "
            "Confidence ceiling is LOW for all video-derived claims."
        )
