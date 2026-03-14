"""
Search Discovery Routes — Topic-first source discovery.

POST /jobs/search — Discover sources for a topic (no job created yet)
POST /jobs/search/{search_id}/quick-brief — Generate a Quick Brief preview
POST /jobs/search/{search_id}/approve — Approve sources and create full job

Flow:
1. User enters topic → POST /jobs/search → returns candidates + search_id
2. Optionally: POST /jobs/search/{search_id}/quick-brief → preview Creator Brief
3. User selects sources → POST /jobs/search/{search_id}/approve → creates job
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.pipeline.search.relevance_validator import (
    score_and_filter_candidates,
    SearchCandidate,
)

router = APIRouter(prefix="/jobs", tags=["search"])

# ---------------------------------------------------------------------------
# In-memory search session store (TTL = 30 minutes)
# In production, use Redis with TTL.
# ---------------------------------------------------------------------------

_search_sessions: dict[str, dict] = {}


def _cleanup_expired():
    """Remove expired sessions (simple GC)."""
    now = datetime.utcnow()
    expired = [k for k, v in _search_sessions.items() if v["expires_at"] < now]
    for k in expired:
        del _search_sessions[k]


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    """Request body for POST /jobs/search."""
    topic: str = Field(..., min_length=3, max_length=500, description="Research topic")
    depth: Optional[str] = Field(
        default="full",
        description="Research depth: quick, full, investigation"
    )
    category: Optional[str] = Field(
        default=None,
        description="Category hint: pop_culture, political, true_crime, etc."
    )


class SearchCandidateResponse(BaseModel):
    """A single search candidate in the response."""
    url: str
    title: str
    snippet: str
    relevance_score: float
    provider: str
    source_type: Optional[str] = None


class SearchResponse(BaseModel):
    """Response from POST /jobs/search."""
    search_id: str
    topic: str
    candidates: list[SearchCandidateResponse]
    total_found: int
    expires_in_seconds: int = 1800


class ApproveRequest(BaseModel):
    """Request body for POST /jobs/search/{search_id}/approve."""
    selected_urls: list[str] = Field(..., min_length=1, description="URLs to include")
    depth: Optional[str] = Field(default="full", description="Research depth override")


class ApproveResponse(BaseModel):
    """Response from POST /jobs/search/{search_id}/approve."""
    job_id: str
    status: str
    source_count: int


class QuickBriefResponse(BaseModel):
    """Response from POST /jobs/search/{search_id}/quick-brief."""
    search_id: str
    brief: dict
    is_preview: bool = True
    brief_type: str = "quick"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/search", response_model=SearchResponse)
async def search_topic(
    request: SearchRequest,
    user=Depends(get_current_user),
):
    """
    Discover sources for a topic without creating a job.

    Returns a search_id and candidate list. The search_id is used
    to approve sources and create a job.
    """
    _cleanup_expired()

    search_id = f"srch_{uuid.uuid4().hex[:12]}"
    logger.info(f"[{search_id}] Search discovery for topic: {request.topic[:80]}")

    try:
        # Use the grounded search pipeline to find candidates
        # For topic-first flow, we don't have Doc 0 yet, so use ungrounded search
        candidates = await _discover_sources(
            topic=request.topic,
            category=request.category,
            max_results=12,
        )

        # Score and filter candidates
        scored = score_and_filter_candidates(
            candidates=candidates,
            topic=request.topic,
            min_score=0.3,
        )

        # Store session
        _search_sessions[search_id] = {
            "topic": request.topic,
            "depth": request.depth,
            "category": request.category,
            "candidates": scored,
            "user_id": user.user_id if user else "anonymous",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30),
        }

        return SearchResponse(
            search_id=search_id,
            topic=request.topic,
            candidates=[
                SearchCandidateResponse(
                    url=c.url,
                    title=c.title,
                    snippet=c.snippet,
                    relevance_score=c.relevance_score,
                    provider=c.provider,
                    source_type=c.source_type,
                )
                for c in scored
            ],
            total_found=len(scored),
        )

    except Exception as e:
        logger.error(f"[{search_id}] Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search discovery failed")


@router.post("/search/{search_id}/quick-brief", response_model=QuickBriefResponse)
async def generate_quick_brief(
    search_id: str,
    user=Depends(get_current_user),
):
    """
    Generate a Quick Brief preview from search candidates.

    This is a fast single-LLM-call preview, not a full pipeline run.
    Target: <15 seconds.
    """
    _cleanup_expired()

    session = _search_sessions.get(search_id)
    if not session:
        raise HTTPException(status_code=404, detail="Search session not found or expired")

    try:
        from backend.pipeline.stages.quick_brief_stage import generate_quick_brief as gen_brief

        brief_data = await gen_brief(
            topic=session["topic"],
            candidates=session["candidates"],
        )

        return QuickBriefResponse(
            search_id=search_id,
            brief=brief_data,
            is_preview=True,
            brief_type="quick",
        )

    except Exception as e:
        logger.error(f"[{search_id}] Quick brief generation failed: {e}")
        raise HTTPException(status_code=500, detail="Quick brief generation failed")


@router.post("/search/{search_id}/approve", response_model=ApproveResponse)
async def approve_search_sources(
    search_id: str,
    request: ApproveRequest,
    user=Depends(get_current_user),
):
    """
    Approve selected sources and create a full research job.

    Links the search context to the new job for continuity.
    """
    _cleanup_expired()

    session = _search_sessions.get(search_id)
    if not session:
        raise HTTPException(status_code=404, detail="Search session not found or expired")

    try:
        from backend.state import create_job
        from backend.worker import run_research_job

        # Build selected URLs from validated candidates
        from backend.pipeline.utils.url_dedup import is_youtube_url

        selected_urls = [
            url for url in request.selected_urls
            if any(c.url == url for c in session["candidates"])
        ]

        if not selected_urls:
            raise HTTPException(
                status_code=400,
                detail="No valid URLs selected from search candidates"
            )

        # Split by URL type: YouTube videos need transcript pipeline, not HTML scraping
        video_urls = [url for url in selected_urls if is_youtube_url(url)]
        article_urls = [url for url in selected_urls if not is_youtube_url(url)]

        if video_urls:
            logger.info(
                f"[{search_id}] Auto-classified {len(video_urls)} YouTube URL(s) "
                f"for transcript pipeline"
            )

        # Build config for the job (matches mixed-input format)
        config_json = {
            "topic": session["topic"],
            "job_type": "mixed_input",
            "input_mode": "mixed",
            "video_urls": video_urls,
            "article_urls": article_urls,
            "text_inputs": [],
            "screenshots": [],
            "source_count": len(selected_urls),
            "search_id": search_id,
            "depth": request.depth or session.get("depth", "full"),
        }

        # Create job via state store
        job = create_job(config_json=config_json, user_id=session["user_id"])

        # Enqueue Celery task
        run_research_job.apply_async(
            (job.job_id, session["topic"]),
            task_id=job.job_id,
        )

        logger.info(
            f"[{search_id}] Search approved -> job {job.job_id} "
            f"({len(selected_urls)} sources)"
        )

        # Clean up session
        del _search_sessions[search_id]

        return ApproveResponse(
            job_id=job.job_id,
            status="queued",
            source_count=len(selected_urls),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{search_id}] Approve failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create job from search")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _discover_sources(
    topic: str,
    category: Optional[str] = None,
    max_results: int = 12,
) -> list[SearchCandidate]:
    """
    Discover sources for a topic using available search providers.

    Unlike grounded_search (which uses Doc 0 context), this performs
    ungrounded search directly from the topic string.
    """
    candidates: list[SearchCandidate] = []
    seen_urls: set[str] = set()

    # Try each search provider
    try:
        from backend.config import Settings
        settings = Settings()

        # Generate search queries from topic
        queries = _generate_topic_queries(topic, category)

        for query in queries[:3]:  # Limit to 3 queries
            try:
                # Try Tavily first (best for research)
                if settings.tavily_api_key:
                    tavily_results = await _search_tavily(query, settings.tavily_api_key)
                    for r in tavily_results:
                        if r.url not in seen_urls:
                            seen_urls.add(r.url)
                            candidates.append(r)

                # Try Serper as fallback
                if settings.serper_api_key and len(candidates) < max_results:
                    serper_results = await _search_serper(query, settings.serper_api_key)
                    for r in serper_results:
                        if r.url not in seen_urls:
                            seen_urls.add(r.url)
                            candidates.append(r)

            except Exception as e:
                logger.warning(f"Search query failed: {query}: {e}")
                continue

    except Exception as e:
        logger.error(f"Source discovery failed: {e}")

    return candidates[:max_results]


def _generate_topic_queries(topic: str, category: Optional[str] = None) -> list[str]:
    """Generate search queries from a topic string."""
    queries = [topic]

    # Add category-specific variations
    if category == "pop_culture":
        queries.append(f"{topic} drama controversy")
    elif category == "political":
        queries.append(f"{topic} policy analysis")
    elif category == "true_crime":
        queries.append(f"{topic} investigation timeline")
    elif category == "controversy":
        queries.append(f"{topic} different perspectives debate")
    else:
        queries.append(f"{topic} analysis overview")
        queries.append(f"{topic} latest news developments")

    return queries


async def _search_tavily(query: str, api_key: str) -> list[SearchCandidate]:
    """Search using Tavily API."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                    "api_key": api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            return [
                SearchCandidate(
                    url=r["url"],
                    title=r.get("title", ""),
                    snippet=r.get("content", "")[:300],
                    relevance_score=r.get("score", 0.5),
                    provider="tavily",
                )
                for r in data.get("results", [])
            ]
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return []


async def _search_serper(query: str, api_key: str) -> list[SearchCandidate]:
    """Search using Serper API."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": 5},
                headers={"X-API-KEY": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

            return [
                SearchCandidate(
                    url=r["link"],
                    title=r.get("title", ""),
                    snippet=r.get("snippet", "")[:300],
                    relevance_score=0.5,  # Serper doesn't return scores
                    provider="serper",
                )
                for r in data.get("organic", [])
            ]
    except Exception as e:
        logger.warning(f"Serper search failed: {e}")
        return []
