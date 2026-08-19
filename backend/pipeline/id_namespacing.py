"""Make per-source unit IDs globally unique.

Extraction is source-isolated (Architecture Rule 1), so every source's
extraction numbers its own units from 1: six sources produce six `KP_1`s.
Downstream, all of them are collected into one list and keyed by ID, so the
last source written wins. On the 16-source Hawara run that read as "every key
point comes from Source 16, 100% single-source" - the corroboration signal was
destroyed by an ID collision, not by the corpus.

Namespacing them as `SRC_3:KP_1` at the parse boundary fixes every consumer at
once, because nothing downstream has to change.
"""

from typing import Optional

from backend.models.semantic_units import SemanticExtractionResult

NAMESPACE_SEPARATOR = ":"


def namespaced_id(source_id: str, local_id: Optional[str]) -> Optional[str]:
    """Qualify a per-source unit ID with the source that produced it.

    Idempotent: an already-qualified ID is returned unchanged, so the function
    is safe to apply more than once (re-parsing, iterate runs).

    Args:
        source_id: The owning source, e.g. `SRC_3`.
        local_id: The unit's per-source ID, e.g. `KP_1`.

    Returns:
        `SRC_3:KP_1`, or the input unchanged when it is empty or already
        qualified.
    """
    if not local_id or NAMESPACE_SEPARATOR in local_id:
        return local_id
    return f"{source_id}{NAMESPACE_SEPARATOR}{local_id}"


def local_id(unit_id: str) -> str:
    """Strip the source prefix from a qualified ID.

    Args:
        unit_id: Either `SRC_3:KP_1` or `KP_1`.

    Returns:
        The per-source part of the ID.
    """
    return unit_id.split(NAMESPACE_SEPARATOR, 1)[-1] if unit_id else unit_id


def source_of(unit_id: str) -> Optional[str]:
    """Read the owning source out of a qualified ID.

    Args:
        unit_id: A unit ID.

    Returns:
        The source ID, or None when the ID carries no namespace.
    """
    if not unit_id or NAMESPACE_SEPARATOR not in unit_id:
        return None
    return unit_id.split(NAMESPACE_SEPARATOR, 1)[0]


def namespace_extraction_ids(
    result: SemanticExtractionResult,
) -> SemanticExtractionResult:
    """Qualify every ID and internal reference in one source's extraction.

    Also pins `source_ids` to the owning source: extraction is isolated, so a
    key point can only be attributed to the source it came from. Corroboration
    across sources is computed later, from matching statements, never from a
    model asserting it.

    Args:
        result: One source's extraction result, modified in place.

    Returns:
        The same result, for chaining.
    """
    source_id = result.source_id
    if not source_id:
        return result

    def qualify(unit_id: Optional[str]) -> Optional[str]:
        return namespaced_id(source_id, unit_id)

    def qualify_all(unit_ids: list[str]) -> list[str]:
        return [namespaced_id(source_id, unit_id) for unit_id in unit_ids or []]

    for quote in result.quotes:
        quote.quote_id = qualify(quote.quote_id)

    for claim in result.claims:
        claim.claim_id = qualify(claim.claim_id)
        # supporting_quotes holds quote TEXT, not IDs (see Claim), so it is
        # deliberately left alone.

    for key_point in result.key_points:
        key_point.key_point_id = qualify(key_point.key_point_id)
        key_point.supporting_claims = qualify_all(key_point.supporting_claims)
        key_point.source_ids = [source_id]

    for theme in result.themes:
        theme.theme_id = qualify(theme.theme_id)
        theme.related_key_points = qualify_all(theme.related_key_points)

    for tension in result.tensions:
        tension.tension_id = qualify(tension.tension_id)
        tension.involved_key_points = qualify_all(tension.involved_key_points)
        tension.source_ids = [source_id]

    for observation in result.approximate_observations:
        observation.observation_id = qualify(observation.observation_id)

    return result
