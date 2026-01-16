"""Research pipeline runner and stages."""

# Mode selection (single source of truth for analysis modes)
from backend.pipeline.mode_selector import (
    CONFIDENCE_CEILINGS,
    DEGRADED_QUOTE_MODES,
    NO_QUOTE_MODES,
    QUOTES_ALLOWED,
    get_confidence_ceiling,
    get_confidence_ceiling_string,
    select_analysis_mode,
    are_quotes_allowed,
    requires_quote_warning,
    is_no_quote_mode,
)

__all__ = [
    # Mode selection
    "CONFIDENCE_CEILINGS",
    "DEGRADED_QUOTE_MODES",
    "NO_QUOTE_MODES",
    "QUOTES_ALLOWED",
    "get_confidence_ceiling",
    "get_confidence_ceiling_string",
    "select_analysis_mode",
    "are_quotes_allowed",
    "requires_quote_warning",
    "is_no_quote_mode",
]

