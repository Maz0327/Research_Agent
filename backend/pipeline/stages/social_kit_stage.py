"""Social Media Kit Stage — Doc 6.

Temperature: 0.3-0.5 (varies by platform)

This stage is user-triggered. Generates platform-specific social media posts.
"""

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.social_kit_models import SocialKitDocument
from backend.pipeline.prompts.social_kit_prompt import (
    SOCIAL_KIT_ROLE,
    build_social_kit_prompt,
)

# Temperature by tone
TONE_TEMPERATURES = {
    "professional": 0.3,
    "casual": 0.45,
    "energetic": 0.5,
}


def run_social_kit_stage(
    job_id: str,
    job_data: dict[str, Any],
    platforms: list[str] | None = None,
    tone: str = "professional",
) -> tuple[SocialKitDocument, float, list[str]]:
    """Generate social media kit from job research data.

    Args:
        job_id: Job identifier.
        job_data: Dict with artifacts.
        platforms: List of platforms to generate for.
        tone: Tone (professional, casual, energetic).

    Returns:
        Tuple of (SocialKitDocument, cost, warnings).
    """
    if platforms is None:
        platforms = ["twitter_thread", "linkedin", "instagram", "youtube_description"]

    logger.info(f"[{job_id}] Social Kit stage starting (platforms={platforms}, tone={tone})")
    warnings: list[str] = []

    artifacts = job_data.get("artifacts", {})
    topic = job_data.get("topic", job_data.get("prompt", "Unknown Topic"))

    # Load docs
    from backend.pipeline.stages.blog_post_stage import (
        _resolve_doc_data,
        _format_sources,
        _format_claims,
        _format_themes,
    )

    source_ledger = _resolve_doc_data(artifacts, "source_ledger", "doc_0_path")
    sources = source_ledger.get("sources", [])
    source_count = len(sources)

    if source_count == 0:
        raise ValueError("No sources found — cannot generate social kit")

    semantic_brief = _resolve_doc_data(artifacts, "semantic_brief", "doc_2_path")

    # Build prompt
    prompt = build_social_kit_prompt(
        job_id=job_id,
        topic=topic,
        source_count=source_count,
        platforms=platforms,
        tone=tone,
        doc0_sources=_format_sources(sources),
        doc2_claims=_format_claims(semantic_brief),
        doc2_themes=_format_themes(semantic_brief.get("themes", [])),
    )

    # Single LLM call (all platforms at once for coherence)
    temperature = TONE_TEMPERATURES.get(tone, 0.4)
    client = GeminiClient()
    logger.info(f"[{job_id}] Calling LLM for Social Kit (temp={temperature})")

    response = client.generate_json(
        prompt=prompt,
        system_message=SOCIAL_KIT_ROLE,
        temperature=temperature,
    )

    if response.get("error"):
        raise ValueError(f"LLM error: {response['error']}")

    raw_data = response.get("data", {})
    if not raw_data:
        raise ValueError("LLM returned empty data")

    raw_data.setdefault("job_id", job_id)
    raw_data.setdefault("topic", topic)
    raw_data.setdefault("source_count", source_count)
    raw_data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())

    social_kit = SocialKitDocument(**raw_data)

    # Provenance validation
    valid_source_ids = {s.get("source_id", "") for s in sources if s.get("source_id")}
    bad_sources = social_kit.all_source_ids() - valid_source_ids
    if bad_sources:
        warnings.append(f"Social Kit references unknown source_ids: {sorted(bad_sources)}")

    cost = response.get("cost", 0.0)

    logger.info(
        f"[{job_id}] Social Kit generated: "
        f"{len(social_kit.platforms)} platforms"
    )

    return social_kit, cost, warnings
