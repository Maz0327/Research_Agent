"""Model seats for the LWM writing/verification side — current authority, or a loud failure.

Never a silent substitution: a seat resolves to its currently-authoritative
model; a missing credential raises with the exact env var to fix. Env
overrides are deliberate acts, logged.

ROUTING PRECEDENCE (audited 2026-09-01 — do not resurrect D-23 wholesale):
- D-23 (lwm-pipeline DECISIONS, 2026-08-15): deepseek-v4-pro drafts ·
  claude-sonnet-5 edits · kimi-k3 judges.
- D-028 (Research_Agent DECISIONS, 2026-08-20) SUPERSEDES the judge seat:
  gpt-5.6-terra won the judge contest (kappa 0.900 vs kimi 0.550; kimi-k2.5
  sunset 2026-08-31; kimi-k2.6 is the documented fallback, not the default).
  `LLM_JUDGE_PRIMARY` was explicitly corrected to "openai" for the same
  reason. Kimi is NOT the judge.
- 2026-08-30 reseat (`2e2ff08` + D-034/D-035 lineage): everything off the
  dead Anthropic API path; production prose = gpt-5.6-luna via env. The
  Claude Code bridge (D-035) exists but is OFF by default.
- WRITER: D-23's drafter (deepseek-v4-pro, Maz's ear across two topics,
  writer-model test 2026-08-15) has no later superseding decision. It stays.
  DashScope serves it and the key is present.
- EDITOR: D-23 says claude-sonnet-5; the Anthropic API has been dead since
  2026-08-30 and NO recorded decision reseats the editor. This is a genuine
  unresolved conflict — the seat keeps its locked value and fails loudly,
  and the fix is Maz's decision (fund Anthropic, enable the D-035
  claude-code bridge, or reseat by decision), never a silent fallback.
"""

import os

from loguru import logger

SEATS = {
    # seat: (env override, locked default, authority)
    "writer": ("LWM_MODEL_WRITER", "deepseek-v4-pro", "D-23 (unsuperseded)"),
    "editor": ("LWM_MODEL_EDITOR", "claude-sonnet-5",
               "D-23 (UNRESOLVED: provider dead since 08-30, no superseding decision)"),
    # Judge-function seats (stage-4 judgment, 10b verdicts) follow D-028 via
    # the config's MODEL_JUDGE (default gpt-5.6-terra) so there is exactly one
    # judge authority in the system.
    "judge": ("LWM_MODEL_JUDGE", "", "D-028 via settings.model_judge"),
    # The blind readers have no locked model family (their protocol file is an
    # open audit item); the D-028 judge seat is the standing default.
    "reader": ("LWM_MODEL_READER", "", "no locked family; defaults to D-028 judge"),
}


def seat_model(seat: str) -> str:
    env, locked, _authority = SEATS[seat]
    override = os.environ.get(env)
    if override:
        logger.info(f"lwm routing: {seat} seat overridden via {env} → {override}")
        return override
    if not locked:
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
    authority = SEATS[seat][2]
    try:
        return get_structured_client(model), model
    except StructuredCallError as e:
        raise RuntimeError(
            f"the {seat} seat resolves to {model!r} ({authority}) and is unreachable: {e}. "
            f"Fix the credential, or override deliberately with {SEATS[seat][0]}. "
            "Silently switching models is not an option."
        ) from e
