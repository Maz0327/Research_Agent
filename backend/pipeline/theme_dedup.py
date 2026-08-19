"""Merge themes that are restatements of each other.

The labyrinth run produced 39 themes including "Suppression of Information"
and "Control and Suppression of Archaeological Information", which are the
same theme said twice. Repetition like that makes a document look like it
found more than it did.

The merge is mechanical and deliberately narrow: one theme's label has to be
wholly contained in the other's, or their descriptions have to overlap
heavily. Measured on both fixtures, that merges one pair on the labyrinth
corpus and none on the films corpus. Themes that restate each other in
genuinely different words (measured maximum similarity 0.38 across 741
labyrinth pairs) are a semantic problem, not a string problem, and are handled
by the Briefing's subject-mapping pass instead.
"""

from loguru import logger

from backend.models.semantic_units import Theme
from backend.pipeline.text_similarity import content_tokens, statement_similarity

# The shorter label must be entirely inside the longer one
_LABEL_CONTAINMENT = 1.0

# Below this many content words a label subsumes too easily to mean anything
_MIN_LABEL_TOKENS = 2

# Or the descriptions themselves are near-verbatim restatements
_DESCRIPTION_THRESHOLD = 0.60


def _is_restatement(a: Theme, b: Theme) -> bool:
    """Decide whether two themes say the same thing.

    Args:
        a: First theme.
        b: Second theme.

    Returns:
        True when one is a restatement of the other.
    """
    tokens_a = content_tokens(a.label or "")
    tokens_b = content_tokens(b.label or "")

    if tokens_a and tokens_b and min(len(tokens_a), len(tokens_b)) >= _MIN_LABEL_TOKENS:
        containment = len(tokens_a & tokens_b) / min(len(tokens_a), len(tokens_b))
        if containment >= _LABEL_CONTAINMENT:
            return True

    return (
        statement_similarity(a.description or "", b.description or "")
        >= _DESCRIPTION_THRESHOLD
    )


def merge_similar_themes(themes: list[Theme]) -> tuple[list[Theme], list[dict]]:
    """Collapse restated themes into one, keeping every reference.

    The fullest description survives, since it is the one that says the most.
    References are unioned, so no key point loses its theme.

    Args:
        themes: Themes to deduplicate, in their original order.

    Returns:
        Tuple of (merged themes, report). The report lists what was folded into
        what, so the merge is visible rather than silent.
    """
    kept: list[Theme] = []
    report: list[dict] = []

    for theme in themes:
        match = next((k for k in kept if _is_restatement(k, theme)), None)
        if match is None:
            kept.append(theme)
            continue

        report.append(
            {
                "merged": theme.theme_id,
                "into": match.theme_id,
                "merged_label": theme.label,
                "kept_label": match.label,
            }
        )

        # Keep the fuller description and the more specific label.
        if len(theme.description or "") > len(match.description or ""):
            match.description = theme.description
        if len(content_tokens(theme.label or "")) > len(content_tokens(match.label or "")):
            match.label = theme.label

        for key_point_id in theme.related_key_points or []:
            if key_point_id not in match.related_key_points:
                match.related_key_points.append(key_point_id)
        for source_id in theme.sources_supporting or []:
            if source_id not in match.sources_supporting:
                match.sources_supporting.append(source_id)
        match.is_consensus = len(match.sources_supporting) >= 2

    if report:
        logger.info(
            f"Theme dedup: merged {len(report)} restatement(s), "
            f"{len(themes)} themes -> {len(kept)}"
        )

    return kept, report
