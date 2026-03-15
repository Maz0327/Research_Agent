"""Script Writer Stage — Doc 5.

Temperature: 0.5 (spoken word needs flexibility)
With voice mimicry: 0.55

This stage is user-triggered (not part of the main pipeline).
"""

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.script_models import ScriptDocument
from backend.pipeline.prompts.script_prompt import (
    SCRIPT_ROLE,
    build_script_prompt,
)

SCRIPT_TEMPERATURE = 0.5
SCRIPT_VOICE_TEMPERATURE = 0.55


def run_script_stage(
    job_id: str,
    job_data: dict[str, Any],
    tone: str = "conversational",
    target_length: str = "medium",
    story_arc: str = "",
    voice_profile_id: str | None = None,
) -> tuple[ScriptDocument, float, list[str]]:
    """Generate a video script from job research data.

    Args:
        job_id: Job identifier.
        job_data: Dict with artifacts.
        tone: Script tone.
        target_length: Target length.
        story_arc: Optional story arc name.
        voice_profile_id: Optional voice profile ID for voice mimicry.

    Returns:
        Tuple of (ScriptDocument, cost, warnings).

    Raises:
        ValueError: If LLM call fails or data is insufficient.
    """
    logger.info(f"[{job_id}] Script stage starting (tone={tone}, length={target_length})")
    warnings: list[str] = []

    artifacts = job_data.get("artifacts", {})
    topic = job_data.get("topic", job_data.get("prompt", "Unknown Topic"))

    # Load Doc 0
    source_ledger = _resolve_doc_data(artifacts, "source_ledger", "doc_0_path")
    sources = source_ledger.get("sources", [])
    source_count = len(sources)

    if source_count == 0:
        raise ValueError("No sources found in Doc 0 — cannot generate script")

    # Load Doc 2
    semantic_brief = _resolve_doc_data(artifacts, "semantic_brief", "doc_2_path")

    # Load Doc 3 (optional)
    creator_brief = artifacts.get("creator_brief", {})
    if isinstance(creator_brief, dict) and creator_brief.get("data"):
        creator_brief = creator_brief["data"]

    # Resolve story arc from Doc 3 if not provided
    if not story_arc and creator_brief:
        suggested = creator_brief.get("suggested_structure", {})
        if isinstance(suggested, dict):
            story_arc = suggested.get("arc_type", "discovery")
    if not story_arc:
        story_arc = "discovery"

    # Load voice profile instructions (Phase 3 hook)
    voice_instructions = ""
    temperature = SCRIPT_TEMPERATURE
    if voice_profile_id:
        voice_instructions = _load_voice_instructions(voice_profile_id)
        if voice_instructions:
            temperature = SCRIPT_VOICE_TEMPERATURE

    # Collect valid IDs
    valid_claim_ids = _collect_valid_claim_ids(source_ledger, semantic_brief)
    valid_source_ids = {s.get("source_id", "") for s in sources if s.get("source_id")}

    # Format data
    from backend.pipeline.stages.blog_post_stage import (
        _format_sources,
        _format_claims,
        _format_themes,
        _format_tensions,
        _extract_hooks,
    )

    prompt = build_script_prompt(
        job_id=job_id,
        topic=topic,
        source_count=source_count,
        tone=tone,
        target_length=target_length,
        doc0_sources=_format_sources(sources),
        doc2_claims=_format_claims(semantic_brief),
        doc2_themes=_format_themes(semantic_brief.get("themes", [])),
        doc2_tensions=_format_tensions(semantic_brief.get("tensions", [])),
        story_arc=story_arc,
        doc3_hooks=_extract_hooks(creator_brief),
        voice_instructions=voice_instructions,
    )

    # LLM call
    client = GeminiClient()
    logger.info(f"[{job_id}] Calling LLM for Script (temp={temperature})")

    response = client.generate_json(
        prompt=prompt,
        system_message=SCRIPT_ROLE,
        temperature=temperature,
    )

    if response.get("error"):
        raise ValueError(f"LLM error: {response['error']}")

    raw_data: dict = response.get("data", {})
    if not raw_data:
        raise ValueError("LLM returned empty data")

    # Inject defaults
    raw_data.setdefault("job_id", job_id)
    raw_data.setdefault("topic", topic)
    raw_data.setdefault("source_count", source_count)
    raw_data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    raw_data.setdefault("tone", tone)
    raw_data.setdefault("target_length", target_length)
    raw_data.setdefault("story_arc", story_arc)

    # Parse and validate
    script = ScriptDocument(**raw_data)

    # Provenance validation
    violations = _validate_provenance(script, valid_claim_ids, valid_source_ids)
    for v in violations:
        logger.warning(f"[{job_id}] Script provenance violation: {v}")
        warnings.append(f"Script provenance: {v}")

    cost = response.get("cost", 0.0)

    logger.info(
        f"[{job_id}] Script generated: "
        f"{len(script.sections)} sections, "
        f"{script.total_word_count} words, "
        f"tone={script.tone}"
    )

    return script, cost, warnings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_doc_data(artifacts: dict, inline_key: str, path_key: str) -> dict:
    """Resolve document data from inline artifacts or storage."""
    data = artifacts.get(inline_key, {})
    if isinstance(data, dict) and data.get("data"):
        data = data["data"]
    if data:
        return data

    path = artifacts.get(path_key)
    if path:
        try:
            from backend.integrations.supabase_storage import get_storage_client
            storage = get_storage_client()
            if storage:
                fetched = storage.download_document(path)
                if isinstance(fetched, dict) and fetched.get("data"):
                    return fetched["data"]
                return fetched or {}
        except Exception as e:
            logger.warning(f"Failed to fetch {inline_key} from storage: {e}")

    return {}


def _collect_valid_claim_ids(source_ledger: dict, semantic_brief: dict) -> set[str]:
    """Collect all valid claim_ids."""
    ids: set[str] = set()
    for source in source_ledger.get("sources", []):
        idx = source.get("extracted_index", {})
        ids.update(idx.get("claim_ids", []))
    for kp in semantic_brief.get("key_points", []):
        if kp.get("key_point_id"):
            ids.add(kp["key_point_id"])
        ids.update(kp.get("supporting_claims", []))
    return ids


def _validate_provenance(
    script: ScriptDocument,
    valid_claim_ids: set[str],
    valid_source_ids: set[str],
) -> list[str]:
    """Validate provenance chain."""
    violations: list[str] = []

    script_claim_ids = script.all_claim_ids()
    script_source_ids = script.all_source_ids()

    if valid_claim_ids:
        bad_claims = script_claim_ids - valid_claim_ids
        if bad_claims:
            violations.append(f"Script references unknown claim_ids: {sorted(bad_claims)}")

    bad_sources = script_source_ids - valid_source_ids
    if bad_sources:
        violations.append(f"Script references unknown source_ids: {sorted(bad_sources)}")

    return violations


def _load_voice_instructions(voice_profile_id: str) -> str:
    """Load voice mimicry instructions from a voice profile.

    This is a Phase 3 hook — returns empty string until voice profiles are implemented.

    Args:
        voice_profile_id: UUID of the voice profile.

    Returns:
        Voice instruction string or empty string.
    """
    # Phase 3 implementation will load from Supabase voice_profiles table
    logger.info(f"Voice profile {voice_profile_id} requested but Phase 3 not yet implemented")
    return ""
