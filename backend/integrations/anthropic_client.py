"""Anthropic Claude client for claim-graph distillation and briefing prose.

Model IDs are env-driven (EXECUTION-PLAN Section 1) - no hardcoded model
strings at call sites. The defaults below are the owner-approved lineup from
DECISIONS.md Decision 023 and were verified callable on 2026-08-15.

Two model behaviors this client depends on, both verified live rather than
recalled:

- Sonnet 5 and Opus 5 reject ``temperature``/``top_p``/``top_k`` outright, so
  this client never sends them. Architecture Rule 16's temperature table
  applies only to models that accept it (Decision 023).
- Structured outputs are engine-enforced via ``output_config.format``. Schema
  conformance is guaranteed; factual accuracy is not, which is what the
  downstream validators and the judge slot exist for.
"""

import json
from typing import Any, Optional

import anthropic
from loguru import logger

from backend.config import MissingRequiredSettingError, get_settings, require_anthropic
from backend.utils.error_handling import sanitize_error_message

# Post-introductory list prices (USD per 1K tokens). Sonnet 5's introductory
# rate ends 2026-08-31, so budgeting at the post-intro price from day one keeps
# cost estimates conservative rather than optimistic.
MODEL_PRICING = {
    "claude-sonnet-5": {"input": 0.003, "output": 0.015},
    "claude-opus-5": {"input": 0.005, "output": 0.025},
}

# Streaming is required above roughly 16K output tokens or the SDK raises on
# the estimated request duration.
STREAM_THRESHOLD_TOKENS = 16_000


class AnthropicError(RuntimeError):
    """Raised when a Claude call fails or returns unusable output."""


class SchemaInvalidError(AnthropicError):
    """Raised when the model's structured output does not parse.

    Distinct from AnthropicError so the caller can decide to escalate rather
    than treating it as a transport failure.
    """


class AnthropicClient:
    """Client for Claude models used by the distillation and briefing stages."""

    def __init__(self, model: Optional[str] = None) -> None:
        settings = require_anthropic()
        self.api_key = settings.anthropic_api_key
        self.model = model or settings.model_distill
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system: str,
        max_tokens: int = 32_000,
        model: Optional[str] = None,
    ) -> tuple[dict, dict]:
        """Run a structured-output call and return (parsed_data, usage).

        Args:
            prompt: The user-turn prompt.
            schema: JSON Schema the response must conform to. Must already be
                stripped of keywords structured outputs reject - see
                ``backend.models.claim_graph.api_json_schema``.
            system: System prompt.
            max_tokens: Output ceiling. Thinking and response text share it.
            model: Overrides the client's configured model for this call.

        Returns:
            Tuple of (parsed JSON dict, usage dict with token counts and cost).

        Raises:
            SchemaInvalidError: If the response is not parseable JSON.
            AnthropicError: On API failure or refusal.
        """
        model_id = model or self.model
        logger.info(
            f"Claude structured call: model={model_id} max_tokens={max_tokens} "
            f"prompt_chars={len(prompt)}"
        )

        request: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
        }

        try:
            if max_tokens > STREAM_THRESHOLD_TOKENS:
                with self.client.messages.stream(**request) as stream:
                    response = stream.get_final_message()
            else:
                response = self.client.messages.create(**request)
        except anthropic.APIStatusError as e:
            logger.error(f"Claude API error ({e.status_code}): {e.message}")
            raise AnthropicError(
                f"Claude call failed ({e.status_code}): "
                f"{sanitize_error_message(str(e.message))}"
            ) from e
        except anthropic.APIConnectionError as e:
            logger.error(f"Claude connection error: {e}")
            raise AnthropicError("Claude call failed: connection error") from e

        # Safety classifiers can decline with HTTP 200; content is then empty
        # or partial, so check before reading it.
        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            logger.error(f"Claude refused the request (category={category})")
            raise AnthropicError(f"Claude refused the request (category={category})")

        if response.stop_reason == "max_tokens":
            logger.error(f"Claude hit max_tokens={max_tokens}; output truncated")
            raise SchemaInvalidError(
                f"Output truncated at max_tokens={max_tokens} - raise the ceiling"
            )

        text = next((b.text for b in response.content if b.type == "text"), "")
        if not text.strip():
            raise SchemaInvalidError("Claude returned no text content")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Claude returned unparseable JSON: {e}")
            raise SchemaInvalidError(f"Response was not valid JSON: {e}") from e

        usage = self._usage(response, model_id)
        logger.info(
            f"Claude call complete: in={usage['input_tokens']} "
            f"out={usage['output_tokens']} cost=${usage['cost']:.4f}"
        )
        return data, usage

    def _usage(self, response: Any, model_id: str) -> dict:
        """Build a usage dict with an estimated cost for this call."""
        input_tokens = getattr(response.usage, "input_tokens", 0) or 0
        output_tokens = getattr(response.usage, "output_tokens", 0) or 0
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0

        pricing = MODEL_PRICING.get(model_id)
        if pricing is None:
            logger.warning(f"No pricing entry for {model_id}; cost reported as 0")
            cost = 0.0
        else:
            cost = (input_tokens / 1000) * pricing["input"] + (
                output_tokens / 1000
            ) * pricing["output"]

        return {
            "model": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read,
            "cost": cost,
        }


def get_anthropic_client(model: Optional[str] = None) -> AnthropicClient:
    """Build a client, or raise if the key is missing.

    Never returns a stub. A missing key must fail loudly rather than let the
    pipeline emit research-shaped output that no model produced.
    """
    try:
        return AnthropicClient(model=model)
    except MissingRequiredSettingError:
        raise
