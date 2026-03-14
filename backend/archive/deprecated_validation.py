"""
Deprecated validation functions removed 2026-03-14.

These functions validated a `based_on` field that never existed in current models.
Moved here from backend/pipeline/semantic_validation.py (lines 911-1022).
"""

from loguru import logger


def validate_based_on_references(
    assertions: list[dict],
    valid_ids: set[str],
) -> tuple[list[dict], list[str]]:
    """
    Validate that based_on references point to existing IDs.

    Rule CV-001: Citation IDs must exist - hard fail removes invalid refs.

    DEPRECATED: The based_on field does not exist in current models.

    Args:
        assertions: List of assertion dicts with "based_on" field
        valid_ids: Set of valid IDs that can be referenced

    Returns:
        Tuple of (validated_assertions, warnings)
    """
    warnings = []
    valid_assertions = []

    for assertion in assertions:
        based_on = assertion.get("based_on", [])

        if not based_on:
            valid_assertions.append(assertion)
            continue

        valid_refs = [ref for ref in based_on if ref in valid_ids]
        invalid_refs = [ref for ref in based_on if ref not in valid_ids]

        if invalid_refs:
            assertion_id = assertion.get("key_point_id") or assertion.get("claim_id") or "UNKNOWN"
            warning = f"Assertion {assertion_id}: removed invalid refs {invalid_refs}"
            warnings.append(warning)
            logger.warning(warning)
            assertion["_validation_warning"] = f"Removed invalid refs: {invalid_refs}"
            assertion["_removed_refs"] = invalid_refs

        assertion["based_on"] = valid_refs

        if valid_refs:
            valid_assertions.append(assertion)
        else:
            assertion["_all_refs_invalid"] = True
            assertion["confidence"] = "low"
            valid_assertions.append(assertion)
            warnings.append(
                f"Assertion {assertion.get('key_point_id', 'UNKNOWN')}: "
                "all based_on refs invalid, confidence downgraded to low"
            )

    return valid_assertions, warnings


def collect_valid_ids(data: dict) -> set[str]:
    """
    Collect all valid IDs from extraction data for citation validation.

    DEPRECATED: Used only by validate_based_on_references().

    Args:
        data: Semantic extraction output dict

    Returns:
        Set of valid IDs (SRC_*, QUOTE_*, CLIP_*, etc.)
    """
    valid_ids = set()

    source_id = data.get("source_id")
    if source_id:
        valid_ids.add(source_id)

    for quote in data.get("quotes", []):
        quote_id = quote.get("quote_id")
        if quote_id:
            valid_ids.add(quote_id)

    for clip in data.get("clips", []):
        clip_id = clip.get("clip_id")
        if clip_id:
            valid_ids.add(clip_id)

    for kp in data.get("key_points", []):
        kp_id = kp.get("key_point_id")
        if kp_id:
            valid_ids.add(kp_id)

    for claim in data.get("claims", []):
        claim_id = claim.get("claim_id")
        if claim_id:
            valid_ids.add(claim_id)

    for theme in data.get("themes", []):
        theme_id = theme.get("theme_id")
        if theme_id:
            valid_ids.add(theme_id)

    return valid_ids
