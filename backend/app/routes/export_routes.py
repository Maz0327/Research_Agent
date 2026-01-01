"""Export API routes for downloading research data in various formats."""
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from loguru import logger

from backend.app.rate_limiter import limiter
from backend.auth import AuthUser
from backend.auth.ban_check import get_active_user
from backend.state import get_job
from backend.pipeline.formats import ExportManager

router = APIRouter(prefix="/jobs/{job_id}/export", tags=["export"])


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
    logger.info(f"Export request: job={job_id}, format={format}, user={user.id}")

    # Fetch job
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if job.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")

    # Check job status
    status = job.get("status", "")
    if status not in ["completed", "completed_with_warnings"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job not ready for export (status: {status})"
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
        topic_slug = _slugify(job.get("topic", "research"))[:30]
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
    logger.info(f"Export all request: job={job_id}, user={user.id}")

    # Fetch job
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if job.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this job")

    # Check job status
    status = job.get("status", "")
    if status not in ["completed", "completed_with_warnings"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job not ready for export (status: {status})"
        )

    # Gather and export
    export_manager = ExportManager()
    data = _extract_research_data(job)

    try:
        exports = export_manager.generate_all_from_data(data)
    except Exception as e:
        logger.error(f"Export all generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate exports")

    return {
        "job_id": job_id,
        "topic": job.get("topic", ""),
        "exports": exports,
    }


def _extract_research_data(job: dict) -> dict:
    """Extract research data from job record for export."""
    # Get results from job
    results = job.get("results", {}) or {}

    return {
        "job_id": job.get("id", ""),
        "topic": job.get("topic", ""),
        "mode": job.get("mode", "full"),
        "category": job.get("niche") or job.get("category", "auto"),
        "created_at": job.get("created_at"),
        "claims": results.get("claims", []),
        "entities": results.get("entities", {}),
        "timeline_events": results.get("timeline", []) or results.get("timeline_events", []),
        "sources": _gather_sources_from_results(results),
        "validation_results": results.get("validation", []) or results.get("validation_results", []),
        "documentary_analysis": results.get("documentary", {}) or results.get("documentary_analysis", {}),
        "discovered_angles": results.get("angles", []) or results.get("discovered_angles", []),
        "transcripts": results.get("transcripts", []),
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
