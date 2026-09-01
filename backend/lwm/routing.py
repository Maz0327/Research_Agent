"""Model seats for the writing side — D-23's locked routing, or a loud failure.

Never a silent substitution: the seat's locked model resolves through the
existing structured-client provider table; a missing credential raises with
the exact env var to fix. Env overrides are deliberate acts, logged.
"""

import os

from loguru import logger

# D-23 (2026-08-15, DECISIONS.md): DeepSeek-v4-pro drafts · Sonnet 5 edits ·
# kimi-k3 judges. These are the LOCKED defaults; changing them is a decision,
# not a fallback.
SEATS = {
    "writer": ("LWM_MODEL_WRITER", "deepseek-v4-pro"),
    "editor": ("LWM_MODEL_EDITOR", "claude-sonnet-5"),
    "judge": ("LWM_MODEL_JUDGE", "kimi-k3"),
    # The blind readers have no locked model family (their protocol file is an
    # open item); the RA judge seat is the standing default.
    "reader": ("LWM_MODEL_READER", ""),
}


def seat_model(seat: str) -> str:
    env, locked = SEATS[seat]
    override = os.environ.get(env)
    if override:
        logger.info(f"lwm routing: {seat} seat overridden via {env} → {override}")
        return override
    if seat == "reader" and not locked:
        from backend.config import get_settings
        return get_settings().model_judge
    return locked


def seat_client(seat: str):
    """The seat's client — or an actionable error, never a quiet different model."""
    from backend.integrations.structured_client import (
        StructuredCallError,
        get_structured_client,
    )
    model = seat_model(seat)
    try:
        return get_structured_client(model), model
    except StructuredCallError as e:
        raise RuntimeError(
            f"the {seat} seat is locked to {model!r} (D-23) and is unreachable: {e}. "
            f"Fix the credential, or override deliberately with {SEATS[seat][0]}. "
            "Silently switching models is not an option."
        ) from e
