"""Brainstorm API route — creative angle generation before research.

POST /jobs/brainstorm — Synchronous (not Celery). Single Gemini Flash call.
~$0.01 per brainstorm, 5-10 seconds.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.app.rate_limiter import limiter, RATE_LIMITS
from backend.auth import AuthUser
from backend.auth.ban_check import get_active_user
from backend.integrations.gemini_client import GeminiClient
from backend.models.brainstorm import (
    BrainstormRequest,
    BrainstormResponse,
    BrainstormAngle,
    BrainstormLLMOutput,
)
from backend.models.style_guide import DEFAULT_TEMPLATES
from backend.pipeline.prompts.brainstorm_prompt import build_brainstorm_prompt
from backend.state.style_guide_store import get_style_guide
from backend.utils.llm_temperature import TEMP_EXPLORATORY


router = APIRouter(prefix="/jobs", tags=["brainstorm"])


@router.post("/brainstorm", response_model=BrainstormResponse)
@limiter.limit(RATE_LIMITS.get("search_discover", "5/minute"))
async def brainstorm_topic(
    request: Request,
    data: BrainstormRequest,
    user: AuthUser = Depends(get_active_user),
):
    """Generate creative angles and vocabulary for a research topic.

    This is the brainstorm pre-stage — runs before source discovery.
    Single Gemini Flash call, synchronous, ~5-10 seconds.
    """
    logger.info(
        "Brainstorm requested",
        extra={
            "user_id": user.user_id,
            "topic": data.topic[:80],
            "audience_hint": data.audience_hint,
            "style_guide_id": data.style_guide_id,
            "event": "brainstorm_requested",
        },
    )

    # Resolve style guide context if provided
    style_context = None
    if data.style_guide_id:
        guide = get_style_guide(user.user_id, data.style_guide_id)
        if guide:
            # Build style context string from guide + template
            template = DEFAULT_TEMPLATES.get(guide.template_base.value, {})
            parts = []
            voice = guide.overrides.voice or template.get("voice", "")
            if voice:
                parts.append(f"Voice: {voice}")
            audience = guide.overrides.audience or template.get("audience", "")
            if audience:
                parts.append(f"Audience: {audience}")
            structure = guide.overrides.structure or template.get("structure", "")
            if structure:
                parts.append(f"Structure: {structure}")
            hook_style = guide.overrides.hook_style or template.get("hook_style", "")
            if hook_style:
                parts.append(f"Hook style: {hook_style}")
            vocab_use = guide.overrides.vocabulary_use or template.get("vocabulary_use", [])
            if vocab_use:
                parts.append(f"Use these phrases: {', '.join(vocab_use[:5])}")
            vocab_avoid = guide.overrides.vocabulary_avoid or template.get("vocabulary_avoid", [])
            if vocab_avoid:
                parts.append(f"Avoid: {', '.join(vocab_avoid[:5])}")
            style_context = "\n".join(parts) if parts else None

    # Build prompt
    prompt = build_brainstorm_prompt(
        topic=data.topic,
        audience_hint=data.audience_hint,
        style_context=style_context,
    )

    # Call Gemini Flash (fast, cheap)
    try:
        client = GeminiClient()
        result = client.generate_json(
            prompt=prompt,
            model="gemini-2.5-flash",
            temperature=TEMP_EXPLORATORY,  # 0.4
            response_schema=BrainstormLLMOutput,
        )
    except Exception as e:
        logger.error(f"Brainstorm Gemini call failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Brainstorm generation failed: {str(e)[:200]}",
        )

    if result.get("error"):
        logger.warning(f"Brainstorm Gemini returned error: {result['error']}")
        raise HTTPException(
            status_code=500,
            detail=f"Brainstorm generation error: {result['error'][:200]}",
        )

    raw_data = result.get("data", {})
    cost = result.get("cost", 0.0)

    # Convert raw LLM output to response with IDs
    angles = []
    for i, angle_data in enumerate(raw_data.get("angles", [])[:4]):
        angles.append(BrainstormAngle(
            angle_id=f"ANG_{i + 1}",
            title=angle_data.get("title", ""),
            description=angle_data.get("description", ""),
            hook_preview=angle_data.get("hook_preview", ""),
            story_arc=angle_data.get("story_arc", {
                "hook": "", "conflict": "", "build": "", "resolution": "", "cta": "",
            }),
            content_type=angle_data.get("content_type", "analysis"),
            estimated_depth=angle_data.get("estimated_depth", "medium"),
        ))

    response = BrainstormResponse(
        angles=angles,
        vocabulary=raw_data.get("vocabulary", [])[:15],
        key_questions=raw_data.get("key_questions", [])[:10],
        aesthetic_keywords=raw_data.get("aesthetic_keywords", [])[:10],
        suggested_search_queries=raw_data.get("suggested_search_queries", [])[:8],
        cost=cost,
    )

    logger.info(
        "Brainstorm completed",
        extra={
            "user_id": user.user_id,
            "topic": data.topic[:80],
            "angles_count": len(response.angles),
            "cost": cost,
            "event": "brainstorm_completed",
        },
    )

    return response
