"""Creator Analysis API route — analyze a creator's style from their videos.

POST /creator-analysis — Synchronous. Fetches transcripts, runs single
Gemini call for style analysis.

Flow:
1. Accept 3-5 YouTube URLs + creator name
2. Fetch transcripts via Supadata/Whisper fallback chain
3. Send transcripts to Gemini with style analysis prompt
4. Return Creator Style Profile
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.app.rate_limiter import limiter, RATE_LIMITS
from backend.auth import AuthUser
from backend.auth.ban_check import get_active_user
from backend.integrations.gemini_client import GeminiClient
from backend.integrations.transcripts import fetch_transcripts_batch
from backend.models.creator_analysis import (
    CreatorAnalysisRequest,
    CreatorStyleProfileResponse,
    CreatorStyleProfileSchema,
)
from backend.pipeline.prompts.creator_analysis_prompt import (
    CREATOR_ANALYSIS_ROLE,
    build_creator_analysis_prompt,
)

router = APIRouter(prefix="/creator-analysis", tags=["creator-analysis"])

# Temperature for creator analysis (brainstorm-level variety)
CREATOR_ANALYSIS_TEMPERATURE = 0.4


@router.post("", response_model=CreatorStyleProfileResponse)
@limiter.limit(RATE_LIMITS.get("search_discover", "5/minute"))
async def analyze_creator(
    request: Request,
    data: CreatorAnalysisRequest,
    user: AuthUser = Depends(get_active_user),
):
    """Analyze a creator's style from 3-5 YouTube video URLs.

    Fetches transcripts, runs Gemini style analysis, returns a Creator
    Style Profile that can be saved as a style guide.
    """
    logger.info(
        "Creator analysis requested",
        extra={
            "user_id": user.user_id,
            "creator_name": data.creator_name[:80],
            "video_count": len(data.video_urls),
            "event": "creator_analysis_requested",
        },
    )

    # Validate URLs are YouTube
    for url in data.video_urls:
        if "youtube.com" not in url and "youtu.be" not in url:
            raise HTTPException(
                status_code=400,
                detail=f"All URLs must be YouTube videos. Invalid: {url[:100]}",
            )

    # Step 1: Fetch transcripts
    try:
        transcript_items = fetch_transcripts_batch(data.video_urls)
    except Exception as e:
        logger.error(f"Transcript fetch failed: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch video transcripts: {str(e)[:200]}",
        )

    # Filter to only successful transcripts
    successful = [
        t for t in transcript_items
        if t.text and len(t.text.strip()) > 50
    ]

    if len(successful) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Could only extract {len(successful)} usable transcript(s) "
                f"from {len(data.video_urls)} videos. Need at least 2. "
                "Check that the videos have captions/subtitles available."
            ),
        )

    # Step 2: Build prompt
    transcripts_for_prompt = [
        {
            "title": t.title or f"Video {i+1}",
            "transcript": t.text,
            "url": t.video_url or data.video_urls[i] if i < len(data.video_urls) else "",
        }
        for i, t in enumerate(successful)
    ]

    prompt = build_creator_analysis_prompt(
        creator_name=data.creator_name,
        transcripts=transcripts_for_prompt,
    )

    # Step 3: Call Gemini
    try:
        client = GeminiClient()
        result = client.generate_json(
            prompt=prompt,
            system_message=CREATOR_ANALYSIS_ROLE,
            model="gemini-2.0-flash",
            temperature=CREATOR_ANALYSIS_TEMPERATURE,
            response_schema=CreatorStyleProfileSchema,
        )
    except Exception as e:
        logger.error(f"Creator analysis LLM call failed: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Style analysis failed: {str(e)[:200]}",
        )

    if result.get("error"):
        raise HTTPException(
            status_code=502,
            detail=f"Style analysis error: {result['error'][:200]}",
        )

    profile_data = result.get("data", {})
    if not profile_data:
        raise HTTPException(
            status_code=502,
            detail="Style analysis returned empty result",
        )

    logger.info(
        "Creator analysis completed",
        extra={
            "user_id": user.user_id,
            "creator_name": data.creator_name[:80],
            "transcripts_analyzed": len(successful),
            "cost": result.get("cost", 0),
            "event": "creator_analysis_completed",
        },
    )

    return CreatorStyleProfileResponse(
        job_id=f"ca_{user.user_id[:8]}_{data.creator_name[:20].replace(' ', '_').lower()}",
        creator_name=data.creator_name,
        profile=profile_data,
        video_count=len(successful),
        status="completed",
    )
