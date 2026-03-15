"""Blog Post Generation Stage — Doc 7.

Temperature: 0.4 (creative writing, fact-grounded)

This stage is user-triggered (not part of the main pipeline).
It reads:
- Doc 0 data: source ledger (sources, titles, URLs)
- Doc 2 data: semantic brief (themes, tensions, key_points)
- Doc 3 data: creator brief (hooks, setup — optional framing)

It outputs:
- BlogPostDocument as dict
- Markdown-formatted blog post

Failure is FATAL for this task (it's the only thing the task does).
"""

import json
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.models.blog_post_models import BlogPostDocument
from backend.pipeline.prompts.blog_post_prompt import (
    BLOG_POST_ROLE,
    build_blog_post_prompt,
)

# Temperature for Blog Post (creative writing, fact-grounded)
BLOG_POST_TEMPERATURE = 0.4


def run_blog_post_stage(
    job_id: str,
    job_data: dict[str, Any],
) -> tuple[BlogPostDocument, float, list[str]]:
    """Generate a blog post from job research data.

    Args:
        job_id: Job identifier.
        job_data: Dict with artifacts (source_ledger, semantic_brief, creator_brief).

    Returns:
        Tuple of (BlogPostDocument, cost, warnings).

    Raises:
        ValueError: If LLM call fails or data is insufficient.
    """
    logger.info(f"[{job_id}] Blog Post stage starting")
    warnings: list[str] = []

    artifacts = job_data.get("artifacts", {})

    # Load Doc 0 (Source Ledger)
    source_ledger = _resolve_doc_data(artifacts, "source_ledger", "doc_0_path")
    sources = source_ledger.get("sources", [])
    source_count = len(sources)
    topic = job_data.get("topic", job_data.get("prompt", "Unknown Topic"))

    if source_count == 0:
        raise ValueError("No sources found in Doc 0 — cannot generate blog post")

    # Load Doc 2 (Semantic Brief)
    semantic_brief = _resolve_doc_data(artifacts, "semantic_brief", "doc_2_path")

    # Load Doc 3 (Creator Brief — optional, for framing)
    creator_brief = artifacts.get("creator_brief", {})
    if isinstance(creator_brief, dict) and creator_brief.get("data"):
        creator_brief = creator_brief["data"]

    # Collect valid IDs for provenance validation
    valid_claim_ids = _collect_valid_claim_ids(source_ledger, semantic_brief)
    valid_source_ids = {s.get("source_id", "") for s in sources if s.get("source_id")}

    # Format data for prompt
    doc0_sources_str = _format_sources(sources)
    doc2_claims_str = _format_claims(semantic_brief)
    doc2_themes_str = _format_themes(semantic_brief.get("themes", []))
    doc2_tensions_str = _format_tensions(semantic_brief.get("tensions", []))

    # Extract Doc 3 framing (optional)
    doc3_hooks = _extract_hooks(creator_brief)
    doc3_setup = _extract_setup(creator_brief)

    # Build prompt
    prompt = build_blog_post_prompt(
        job_id=job_id,
        topic=topic,
        source_count=source_count,
        doc0_sources=doc0_sources_str,
        doc2_claims=doc2_claims_str,
        doc2_themes=doc2_themes_str,
        doc2_tensions=doc2_tensions_str,
        doc3_hooks=doc3_hooks,
        doc3_setup=doc3_setup,
    )

    # LLM call
    client = GeminiClient()
    logger.info(f"[{job_id}] Calling LLM for Blog Post (temp={BLOG_POST_TEMPERATURE})")

    response = client.generate_json(
        prompt=prompt,
        system_message=BLOG_POST_ROLE,
        temperature=BLOG_POST_TEMPERATURE,
    )

    if response.get("error"):
        raise ValueError(f"LLM error: {response['error']}")

    raw_data: dict = response.get("data", {})
    if not raw_data:
        raise ValueError("LLM returned empty data")

    # Inject job_id and topic if LLM omitted them
    raw_data.setdefault("job_id", job_id)
    raw_data.setdefault("topic", topic)
    raw_data.setdefault("source_count", source_count)
    raw_data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())

    # Parse and validate with Pydantic
    blog_post = BlogPostDocument(**raw_data)

    # Provenance validation
    violations = _validate_provenance(blog_post, valid_claim_ids, valid_source_ids)
    for v in violations:
        logger.warning(f"[{job_id}] Blog Post provenance violation: {v}")
        warnings.append(f"Blog Post provenance: {v}")

    cost = response.get("cost", 0.0)

    logger.info(
        f"[{job_id}] Blog Post generated: "
        f"{len(blog_post.sections)} sections, "
        f"{len(blog_post.seo_keywords)} keywords"
    )

    return blog_post, cost, warnings


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _resolve_doc_data(artifacts: dict, inline_key: str, path_key: str) -> dict:
    """Resolve document data from inline artifacts or storage.

    Args:
        artifacts: Job artifacts dict.
        inline_key: Key for inline data (e.g. 'source_ledger').
        path_key: Key for storage path (e.g. 'doc_0_path').

    Returns:
        Document data dict.
    """
    data = artifacts.get(inline_key, {})
    if isinstance(data, dict) and data.get("data"):
        data = data["data"]
    if data:
        return data

    # Fetch from storage if path exists
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


def _collect_valid_claim_ids(
    source_ledger: dict, semantic_brief: dict
) -> set[str]:
    """Collect all valid claim_ids from source ledger extraction indices and semantic brief.

    Args:
        source_ledger: Doc 0 data.
        semantic_brief: Doc 2 data.

    Returns:
        Set of valid claim_ids.
    """
    ids: set[str] = set()

    # From source extraction indices
    for source in source_ledger.get("sources", []):
        idx = source.get("extracted_index", {})
        ids.update(idx.get("claim_ids", []))

    # From semantic brief key_points
    for kp in semantic_brief.get("key_points", []):
        if kp.get("key_point_id"):
            ids.add(kp["key_point_id"])
        ids.update(kp.get("supporting_claims", []))

    return ids


def _validate_provenance(
    blog_post: BlogPostDocument,
    valid_claim_ids: set[str],
    valid_source_ids: set[str],
) -> list[str]:
    """Validate provenance: all IDs in the post must exist in Doc 0/2.

    Args:
        blog_post: Parsed BlogPostDocument.
        valid_claim_ids: Claim IDs from Doc 2.
        valid_source_ids: Source IDs from Doc 0.

    Returns:
        List of violation messages. Empty = valid.
    """
    violations: list[str] = []

    post_claim_ids = blog_post.all_claim_ids()
    post_source_ids = blog_post.all_source_ids()

    if valid_claim_ids:
        bad_claims = post_claim_ids - valid_claim_ids
        if bad_claims:
            violations.append(
                f"Blog Post references unknown claim_ids: {sorted(bad_claims)}"
            )

    bad_sources = post_source_ids - valid_source_ids
    if bad_sources:
        violations.append(
            f"Blog Post references unknown source_ids: {sorted(bad_sources)}"
        )

    return violations


def _format_sources(sources: list[dict]) -> str:
    """Format sources for the prompt.

    Args:
        sources: List of source dicts from Doc 0.

    Returns:
        Human-readable source list.
    """
    if not sources:
        return "(No sources in Doc 0)"

    lines = []
    for s in sources:
        source_id = s.get("source_id", "?")
        title = s.get("title", "Untitled")
        url = s.get("url", "")
        source_type = s.get("source_type", "unknown")
        creator = s.get("creator", "")

        line = f"- {source_id}: [{source_type}] {title}"
        if creator:
            line += f" by {creator}"
        if url:
            line += f" | {url}"
        lines.append(line)

    return "\n".join(lines)


def _format_claims(semantic_brief: dict) -> str:
    """Format claims/key_points for the prompt.

    Args:
        semantic_brief: Doc 2 data.

    Returns:
        Formatted claims string.
    """
    key_points = semantic_brief.get("key_points", [])
    if not key_points:
        return "(No key points available)"

    lines = []
    for kp in key_points[:60]:
        kp_id = kp.get("key_point_id", "?")
        statement = kp.get("statement", "")
        confidence = kp.get("confidence", "medium")
        source_ids = ", ".join(kp.get("source_ids", []))
        lines.append(f"- {kp_id} [{confidence}]: {statement} (sources: {source_ids})")

    return "\n".join(lines)


def _format_themes(themes: list[dict]) -> str:
    """Format themes for the prompt.

    Args:
        themes: List of theme dicts.

    Returns:
        Formatted themes string.
    """
    if not themes:
        return "(No themes identified)"

    lines = []
    for t in themes:
        theme_id = t.get("theme_id", "?")
        label = t.get("label", "")
        desc = t.get("description", "")
        lines.append(f"- {theme_id}: {label} — {desc}")

    return "\n".join(lines)


def _format_tensions(tensions: list[dict]) -> str:
    """Format tensions for the prompt.

    Args:
        tensions: List of tension dicts.

    Returns:
        Formatted tensions string.
    """
    if not tensions:
        return "(No tensions identified)"

    lines = []
    for t in tensions:
        tension_id = t.get("tension_id", "?")
        label = t.get("label", "")
        desc = t.get("description", "")
        lines.append(f"- {tension_id}: {label} — {desc}")

    return "\n".join(lines)


def _extract_hooks(creator_brief: dict) -> str:
    """Extract hook text from Creator Brief for framing guidance.

    Args:
        creator_brief: Doc 3 data.

    Returns:
        Formatted hooks string.
    """
    hooks = creator_brief.get("hook_options", [])
    if not hooks:
        return ""

    lines = []
    for h in hooks:
        text = h.get("text", "")
        if text:
            lines.append(f"- {h.get('hook_id', '?')}: {text}")

    return "\n".join(lines)


def _extract_setup(creator_brief: dict) -> str:
    """Extract setup text from Creator Brief.

    Args:
        creator_brief: Doc 3 data.

    Returns:
        Setup text or empty string.
    """
    setup = creator_brief.get("setup", {})
    return setup.get("text", "")
