"""Claude Code bridge: the local CLI as a structured-output provider (D-035).

The Anthropic API has no credits, but the Claude Code subscription does, and
`claude -p` runs the same models headlessly. This client makes that a provider
like any other, so a model slot can read `claude-code:sonnet` and the pipeline
neither knows nor cares that the call left through a subprocess.

**Use it sparingly, and know why.** Measured 2026-08-20, every invocation pays a
fixed session-loading tax that does NOT amortize across calls:

    call 1: cache create 14,636 | read 30,238 | $0.0970 | 1.6s
    call 2: cache create 14,633 | read 30,238 | $0.0970 | 1.8s
    call 3: cache create 14,634 | read 30,238 | $0.0970 | 1.5s

That is roughly 45,000 tokens and ten cents of notional cost before the prompt
is even read. Routing a whole Briefing (~25 calls) through here would spend
~1.1M tokens on overhead alone. Routing the ONE call where the model choice was
measured to matter — the Read, where Sonnet scored 0% ungrounded against a
substitute's ~5% (D-034) — costs one session load.

`--bare` would cut the tax, and cannot be used: it forces `ANTHROPIC_API_KEY`
auth and never reads the subscription, which is the entire point of this file.
"""
import json
import os
import shutil
import subprocess
from typing import Optional

from loguru import logger

# Slots address this provider as "claude-code:<alias>", e.g. claude-code:sonnet.
PREFIX = "claude-code:"

DEFAULT_TIMEOUT = 900

# The CLI prefers an API key over the subscription login when both are present,
# and this pipeline loads ANTHROPIC_API_KEY from .env for its own use. Measured
# 2026-08-20, leaving it set makes the call fail outright: "claude.ai connectors
# are disabled because ANTHROPIC_API_KEY or another auth source is set and takes
# precedence over your claude.ai login". Using the API key is the exact thing
# this bridge exists to avoid, so the subprocess never sees these.
_STRIPPED_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")


def _subscription_env() -> dict:
    """The environment for the CLI, with API-key auth removed."""
    env = {k: v for k, v in os.environ.items() if k not in _STRIPPED_ENV}
    return env


class ClaudeCodeError(RuntimeError):
    """The CLI was missing, failed, or returned something unusable."""


def is_available() -> bool:
    """Is the Claude Code CLI on PATH?"""
    return shutil.which("claude") is not None


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of a model's reply.

    The CLI returns the model's text, not a schema-validated object, so the
    parsing the API would have done has to happen here.

    Args:
        text: The model's reply.

    Returns:
        The parsed object.

    Raises:
        ClaudeCodeError: If no JSON object can be recovered.
    """
    body = (text or "").strip()
    if body.startswith("```"):
        body = body.split("```", 2)[1] if body.count("```") >= 2 else body
        body = body.split("\n", 1)[1] if body.lower().startswith(("json\n", "json\r")) else body
        body = body.rsplit("```", 1)[0] if body.endswith("```") else body
        body = body.strip()

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass

    start, end = body.find("{"), body.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(body[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ClaudeCodeError(f"Claude Code returned unparsable JSON: {exc}") from exc
    raise ClaudeCodeError(f"Claude Code returned no JSON object: {body[:200]!r}")


class ClaudeCodeClient:
    """A structured-output client backed by the local `claude -p` CLI."""

    def __init__(self, model_id: str, timeout: int = DEFAULT_TIMEOUT):
        """Build a client for one model alias.

        Args:
            model_id: Slot value, e.g. "claude-code:sonnet".
            timeout: Seconds to allow a single call.

        Raises:
            ClaudeCodeError: If the CLI is not installed.
        """
        if not is_available():
            raise ClaudeCodeError(
                "The `claude` CLI is not on PATH; the Claude Code bridge needs it"
            )
        self.alias = (model_id or "").split(PREFIX, 1)[-1] or "sonnet"
        self.timeout = timeout

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system: str,
        max_tokens: int = 8_000,
        model: Optional[str] = None,
    ) -> tuple[dict, dict]:
        """Run a structured call through the CLI and return (data, usage).

        The schema travels in the turn rather than as a grammar — the CLI has
        no structured-output mode — so it is restated as an instruction and the
        reply is parsed here.

        Args:
            prompt: The user-turn prompt.
            schema: JSON Schema the reply must satisfy.
            system: The role prompt.
            max_tokens: Unused; the CLI manages its own ceiling. Accepted so
                this client is interchangeable with the others.
            model: Optional alias override.

        Returns:
            Tuple of (parsed data, usage dict).

        Raises:
            ClaudeCodeError: On CLI failure or unparsable output.
        """
        alias = (model or "").split(PREFIX, 1)[-1] or self.alias
        turn = (
            f"{prompt}\n\n"
            "---\n"
            "Reply with a single JSON object and nothing else — no prose before "
            "or after it, no markdown code fence. It must match this schema "
            "exactly, including every required key:\n"
            f"{json.dumps(schema)}"
        )

        argv = [
            "claude",
            "-p",
            "--model",
            alias,
            "--output-format",
            "json",
            # The call generates text; it must not touch the filesystem.
            "--permission-mode",
            "plan",
            "--append-system-prompt",
            system,
        ]

        try:
            done = subprocess.run(
                argv,
                input=turn,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                env=_subscription_env(),
            )
        except subprocess.TimeoutExpired as exc:
            raise ClaudeCodeError(f"Claude Code timed out after {self.timeout}s") from exc

        if done.returncode != 0:
            raise ClaudeCodeError(
                f"Claude Code exited {done.returncode}: {(done.stderr or '')[:300]}"
            )

        try:
            envelope = json.loads(done.stdout)
        except json.JSONDecodeError as exc:
            raise ClaudeCodeError(
                f"Claude Code returned no envelope: {(done.stdout or '')[:200]!r}"
            ) from exc

        if envelope.get("is_error"):
            raise ClaudeCodeError(f"Claude Code reported an error: {envelope.get('result')}")

        data = _extract_json(envelope.get("result", ""))
        raw = envelope.get("usage", {}) or {}
        usage = {
            "input_tokens": raw.get("input_tokens", 0),
            "output_tokens": raw.get("output_tokens", 0),
            "cache_creation_input_tokens": raw.get("cache_creation_input_tokens", 0),
            "cache_read_input_tokens": raw.get("cache_read_input_tokens", 0),
            "cost": envelope.get("total_cost_usd", 0.0),
            "provider": "claude-code",
            "model": alias,
        }
        logger.info(
            f"Claude Code bridge [{alias}]: {usage['output_tokens']} output tokens, "
            f"{envelope.get('duration_ms', 0)}ms, ${usage['cost']:.4f} "
            f"(session overhead is fixed per call — see D-035)"
        )
        return data, usage
