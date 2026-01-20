"""Export API routes for downloading research data in various formats."""
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from loguru import logger
from pydantic import BaseModel

from backend.app.rate_limiter import limiter
from backend.auth import AuthUser
from backend.auth.ban_check import get_active_user
from backend.state import get_job
from backend.pipeline.formats import ExportManager
from backend.pipeline.video_export_formatter import (
    format_video_analysis_for_export,
    format_clips_only,
    format_quotes_only,
)

router = APIRouter(prefix="/jobs/{job_id}/export", tags=["export"])


class GoogleDocsExportResponse(BaseModel):
    """Response model for Google Docs export."""
    success: bool
    folder_url: Optional[str] = None
    doc_url: Optional[str] = None
    error: Optional[str] = None


class ExportFormat(str, Enum):
    """Available export formats."""
    JSON = "json"
    BIBTEX = "bibtex"
    RIS = "ris"
    CHAPTERS = "chapters"
    YOUTUBE_CHAPTERS = "youtube_chapters"
    PODCAST_CHAPTERS = "podcast_chapters"
    CLIPS = "clips"
    SOCIAL = "social"
    BRIEF = "brief"


# Content types for each format
CONTENT_TYPES = {
    ExportFormat.JSON: "application/json",
    ExportFormat.BIBTEX: "application/x-bibtex",
    ExportFormat.RIS: "application/x-research-info-systems",
    ExportFormat.CHAPTERS: "application/json",
    ExportFormat.YOUTUBE_CHAPTERS: "text/plain",
    ExportFormat.PODCAST_CHAPTERS: "application/json",
    ExportFormat.CLIPS: "application/json",
    ExportFormat.SOCIAL: "application/json",
    ExportFormat.BRIEF: "text/markdown",
}

# File extensions for each format
FILE_EXTENSIONS = {
    ExportFormat.JSON: "json",
    ExportFormat.BIBTEX: "bib",
    ExportFormat.RIS: "ris",
    ExportFormat.CHAPTERS: "json",
    ExportFormat.YOUTUBE_CHAPTERS: "txt",
    ExportFormat.PODCAST_CHAPTERS: "json",
    ExportFormat.CLIPS: "json",
    ExportFormat.SOCIAL: "json",
    ExportFormat.BRIEF: "md",
}


@router.get("")
@limiter.limit("60/minute")
async def export_job(
    request: Request,
    job_id: str,
    format: ExportFormat,
    download: bool = False,
    user: AuthUser = Depends(get_active_user),
):
    """
    Export job research data in specified format.

    Args:
        job_id: Job UUID
        format: Export format (json, bibtex, ris, chapters, clips, social)
        download: If true, sets Content-Disposition for file download

    Returns:
        Formatted export data with appropriate Content-Type
    """
    logger.info(f"Export request: job={job_id}, format={format}, user={user.user_id}")

    # Fetch job (sync function)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")

    # Check job status
    if job.status not in ["completed", "completed_with_warnings"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job not ready for export (status: {job.status})"
        )

    # Gather research data from job record
    export_manager = ExportManager()
    data = _extract_research_data(job)

    # Generate export
    try:
        content = _generate_export(export_manager, format, data)
    except Exception as e:
        logger.error(f"Export generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate export")

    # Build response
    content_type = CONTENT_TYPES[format]
    headers = {}

    if download:
        ext = FILE_EXTENSIONS[format]
        topic = job.config_json.get("topic", "research") if job.config_json else "research"
        topic_slug = _slugify(topic)[:30]
        filename = f"{topic_slug}_{format.value}.{ext}"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return Response(
        content=content,
        media_type=content_type,
        headers=headers,
    )


@router.get("/all")
@limiter.limit("30/minute")
async def export_all_formats(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Export job in all available formats at once.

    Returns:
        JSON object with all exports
    """
    logger.info(f"Export all request: job={job_id}, user={user.user_id}")

    # Fetch job (sync function)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")

    # Check job status
    if job.status not in ["completed", "completed_with_warnings"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job not ready for export (status: {job.status})"
        )

    # Gather and export
    export_manager = ExportManager()
    data = _extract_research_data(job)

    try:
        exports = export_manager.generate_all_from_data(data)
    except Exception as e:
        logger.error(f"Export all generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate exports")

    topic = job.config_json.get("topic", "") if job.config_json else ""
    return {
        "job_id": job_id,
        "topic": topic,
        "exports": exports,
    }


def _extract_research_data(job: "JobRecord") -> dict:
    """Extract research data from JobRecord for export."""
    from backend.models.job_record import JobRecord

    # Get config and outputs from JobRecord
    config = job.config_json or {}
    outputs = job.outputs

    # Build sources list from various JobRecord fields
    sources = []
    if job.reddit_posts:
        for r in job.reddit_posts:
            if isinstance(r, dict):
                sources.append({
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "type": "social",
                    "author": r.get("author"),
                    "published_at": r.get("created_at"),
                    "quality_score": r.get("quality_score", 0.5),
                })

    return {
        "job_id": job.job_id,
        "topic": config.get("topic", ""),
        "mode": job.pipeline or config.get("mode", "full"),
        "category": job.niche or config.get("category", "auto"),
        "created_at": job.created_at,
        "claims": config.get("claims", []),
        "entities": job.entities or {},
        "timeline_events": job.timeline_events or [],
        "sources": sources,
        "validation_results": config.get("validation_results", []),
        "documentary_analysis": config.get("documentary_analysis", {}),
        "discovered_angles": job.discovered_angles or [],
        "transcripts": config.get("transcripts", []),
    }


def _gather_sources_from_results(results: dict) -> list:
    """Gather all sources from job results."""
    sources = []

    # Web sources
    web_sources = results.get("web_sources", []) or results.get("sources", [])
    for s in web_sources:
        if isinstance(s, dict):
            sources.append({
                "url": s.get("url", ""),
                "title": s.get("title", ""),
                "type": s.get("type", "web"),
                "author": s.get("author"),
                "published_at": s.get("published_at"),
                "quality_score": s.get("quality_score", 0.5),
            })

    # Videos
    videos = results.get("videos", []) or results.get("youtube_videos", [])
    for v in videos:
        if isinstance(v, dict):
            sources.append({
                "url": v.get("url", ""),
                "title": v.get("title", ""),
                "type": "video",
                "author": v.get("channel") or v.get("author"),
                "published_at": v.get("published_at"),
                "quality_score": v.get("quality_score", 0.5),
            })

    # Reddit
    reddit = results.get("reddit_posts", []) or results.get("reddit", [])
    for r in reddit:
        if isinstance(r, dict):
            sources.append({
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "type": "social",
                "author": r.get("author"),
                "published_at": r.get("created_at"),
                "quality_score": r.get("quality_score", 0.5),
            })

    return sources


def _generate_export(manager: ExportManager, format: ExportFormat, data: dict) -> str:
    """Generate export content for specified format."""
    if format == ExportFormat.JSON:
        return manager.to_json(data)
    elif format == ExportFormat.BIBTEX:
        return manager.to_bibtex(data)
    elif format == ExportFormat.RIS:
        return manager.to_ris(data)
    elif format == ExportFormat.CHAPTERS:
        return manager.to_chapters(data)
    elif format == ExportFormat.YOUTUBE_CHAPTERS:
        return manager.to_youtube_chapters(data)
    elif format == ExportFormat.PODCAST_CHAPTERS:
        return manager.to_podcast_chapters(data)
    elif format == ExportFormat.CLIPS:
        return manager.to_clips(data)
    elif format == ExportFormat.SOCIAL:
        return manager.to_social(data)
    elif format == ExportFormat.BRIEF:
        return manager.to_brief(data)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    import re
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug or "export"


# ============================================================================
# Video Analysis Export Endpoints
# ============================================================================

@router.post("/google-docs", response_model=GoogleDocsExportResponse, deprecated=True)
@limiter.limit("10/minute")
async def export_to_google_docs(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    DEPRECATED: Google Drive export is no longer supported (2026-01-19).

    Use /jobs/{job_id}/attachments to get download links for exports,
    or /jobs/{job_id}/download.pdf for PDF generation.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "message": "Google Drive export is no longer supported",
            "deprecated_since": "2026-01-19",
            "alternative": "Use /jobs/{job_id}/attachments for export downloads or /jobs/{job_id}/download.pdf for PDF",
        },
    )


@router.get("/markdown")
@limiter.limit("60/minute")
async def export_video_analysis_markdown(
    request: Request,
    job_id: str,
    download: bool = False,
    user: AuthUser = Depends(get_active_user),
):
    """
    Export video analysis results as Markdown.
    
    Args:
        job_id: Job UUID
        download: If true, sets Content-Disposition for file download
        
    Returns:
        Markdown formatted text
    """
    logger.info(f"Markdown export request: job={job_id}, user={user.user_id}")
    
    # Fetch job
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify ownership
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    # Check job status
    if job.status not in ["completed", "completed_with_warnings"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job not ready for export (status: {job.status})"
        )
    
    # Get artifacts
    if not job.artifacts:
        raise HTTPException(status_code=400, detail="No artifacts to export")
    
    artifacts_dict = job.artifacts.model_dump(exclude_none=True) if hasattr(job.artifacts, "model_dump") else {}
    
    # Get title and topic
    config = job.config_json or {}
    title = config.get("title", job.title or "Video Analysis")
    research_topic = config.get("research_topic", config.get("topic", ""))
    
    # Format the content
    content = format_video_analysis_for_export(
        artifacts=artifacts_dict,
        title=title,
        research_topic=research_topic,
    )
    
    headers = {}
    if download:
        filename = f"{_slugify(title)[:30]}_analysis.md"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    return Response(
        content=content,
        media_type="text/markdown",
        headers=headers,
    )


@router.get("/clips-only")
@limiter.limit("60/minute")
async def export_clips_only(
    request: Request,
    job_id: str,
    download: bool = False,
    user: AuthUser = Depends(get_active_user),
):
    """
    Export just the clips from video analysis.
    
    Args:
        job_id: Job UUID
        download: If true, sets Content-Disposition for file download
        
    Returns:
        Markdown formatted clips
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    if job.status not in ["completed", "completed_with_warnings"]:
        raise HTTPException(status_code=400, detail=f"Job not ready (status: {job.status})")
    
    if not job.artifacts:
        raise HTTPException(status_code=400, detail="No artifacts to export")
    
    artifacts_dict = job.artifacts.model_dump(exclude_none=True) if hasattr(job.artifacts, "model_dump") else {}
    clips = artifacts_dict.get("clips", [])
    
    content = format_clips_only(clips)
    
    headers = {}
    if download:
        headers["Content-Disposition"] = 'attachment; filename="clips.md"'
    
    return Response(content=content, media_type="text/markdown", headers=headers)


@router.get("/quotes-only")
@limiter.limit("60/minute")
async def export_quotes_only(
    request: Request,
    job_id: str,
    download: bool = False,
    user: AuthUser = Depends(get_active_user),
):
    """
    Export just the quotes from video analysis.
    
    Args:
        job_id: Job UUID
        download: If true, sets Content-Disposition for file download
        
    Returns:
        Markdown formatted quotes
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    if job.status not in ["completed", "completed_with_warnings"]:
        raise HTTPException(status_code=400, detail=f"Job not ready (status: {job.status})")
    
    if not job.artifacts:
        raise HTTPException(status_code=400, detail="No artifacts to export")
    
    artifacts_dict = job.artifacts.model_dump(exclude_none=True) if hasattr(job.artifacts, "model_dump") else {}
    quotes = artifacts_dict.get("quotes", [])
    
    content = format_quotes_only(quotes)
    
    headers = {}
    if download:
        headers["Content-Disposition"] = 'attachment; filename="quotes.md"'
    
    return Response(content=content, media_type="text/markdown", headers=headers)
