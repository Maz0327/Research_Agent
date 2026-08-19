"""One structured-output interface, several providers behind it.

The lineup is env-driven by design (EXECUTION-PLAN Section 1): no model string
is hardcoded, and a lineup change is a config change. That only works if the
pipeline can talk to whichever provider a model name belongs to, which is what
this module adds.

Every client here exposes the same call:

    generate_structured(prompt, schema, system, max_tokens) -> (data, usage)

`schema` is always our JSON Schema. Each adapter translates it into whatever
its provider actually accepts, which is not the same thing anywhere: Gemini
rejects `additionalProperties`, OpenAI requires it, Anthropic takes the schema
as written. Those differences belong here rather than in the passes.
"""

import json
from typing import Any, Optional

from loguru import logger

from backend.config import get_settings

# Which provider owns which model-name prefix
_PREFIXES = (
    ("claude-", "anthropic"),
    ("gemini-", "gemini"),
    ("gpt-", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("kimi-", "moonshot"),
    ("moonshot", "moonshot"),
)

MOONSHOT_BASE_URL = "https://api.moonshot.ai/v1"


class StructuredCallError(Exception):
    """A structured call failed in a way the caller has to handle."""


def provider_for(model_id: str) -> str:
    """Name the provider a model belongs to.

    Args:
        model_id: A model identifier.

    Returns:
        Provider name.

    Raises:
        StructuredCallError: If the model belongs to no known provider.
    """
    lowered = (model_id or "").lower()
    for prefix, provider in _PREFIXES:
        if lowered.startswith(prefix):
            return provider
    raise StructuredCallError(f"No provider knows the model {model_id!r}")


# JSON Schema keywords Gemini rejects or ignores. `title` is on the list as a
# KEYWORD only: a property legitimately named "title" must survive, which is
# why this walk distinguishes schema nodes from `properties` maps rather than
# filtering keys everywhere.
_GEMINI_UNSUPPORTED = {"additionalProperties", "$schema", "definitions", "$defs", "title"}


def _strip_for_gemini(node: Any) -> Any:
    """Translate our JSON Schema into the subset Gemini accepts.

    Gemini rejects `additionalProperties` outright (measured: HTTP 400 "Unknown
    name"). Lowercase type names are fine, so only unsupported keywords are
    removed - and only where they are keywords. Inside a `properties` map the
    keys are the caller's field names, and stripping one there silently deletes
    a field from the schema, which the model then omits from its answer.

    Args:
        node: A JSON Schema fragment.

    Returns:
        The same schema without the keywords Gemini rejects.
    """
    if isinstance(node, list):
        return [_strip_for_gemini(n) for n in node]
    if not isinstance(node, dict):
        return node

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in _GEMINI_UNSUPPORTED:
            continue
        if key == "properties" and isinstance(value, dict):
            # Field names, not keywords: keep every one, clean their schemas.
            out[key] = {name: _strip_for_gemini(schema) for name, schema in value.items()}
        else:
            out[key] = _strip_for_gemini(value)
    return out


class GeminiStructuredClient:
    """Gemini, speaking the same structured-output interface as the others."""

    def __init__(self, model: str):
        """Build a client for one Gemini model.

        Args:
            model: Exact model ID, e.g. `gemini-3.6-flash`.

        Raises:
            StructuredCallError: If no API key is configured.
        """
        from google import genai

        settings = get_settings()
        api_key = settings.google_api_key
        if not api_key:
            raise StructuredCallError("GOOGLE_API_KEY is not configured")

        self.model = model
        self.client = genai.Client(api_key=api_key)

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system: str,
        max_tokens: int = 8_000,
        model: Optional[str] = None,
    ) -> tuple[dict, dict]:
        """Run a structured call and return (parsed data, usage).

        Args:
            prompt: The user-turn prompt.
            schema: Our JSON Schema for the response.
            system: System instruction.
            max_tokens: Output ceiling.
            model: Overrides the configured model for this call.

        Returns:
            Tuple of (parsed JSON, usage dict with token counts and cost).

        Raises:
            StructuredCallError: On API failure or unparsable output.
        """
        from google.genai import types

        model_id = model or self.model
        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_schema": _strip_for_gemini(schema),
            "system_instruction": system,
            "max_output_tokens": max_tokens,
        }
        # The 3.x line bills thinking at output rates and gains nothing on
        # extraction-shaped work (measured, MODEL-DOSSIER): keep it minimal.
        if model_id.startswith("gemini-3"):
            config["thinking_config"] = types.ThinkingConfig(thinking_level="minimal")

        try:
            response = self.client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(**config),
            )
        except Exception as e:
            raise StructuredCallError(f"Gemini call failed: {e}") from e

        text = (response.text or "").strip()
        if not text:
            raise StructuredCallError("Gemini returned no content")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise StructuredCallError(f"Gemini response was not valid JSON: {e}") from e

        usage_meta = getattr(response, "usage_metadata", None)
        usage = {
            "input_tokens": getattr(usage_meta, "prompt_token_count", 0) or 0,
            "output_tokens": getattr(usage_meta, "candidates_token_count", 0) or 0,
            "cost": 0.0,
        }
        logger.info(
            f"Gemini structured call: model={model_id} in={usage['input_tokens']} "
            f"out={usage['output_tokens']}"
        )
        return data, usage


class OpenAIStructuredClient:
    """OpenAI and any OpenAI-compatible endpoint (Moonshot included)."""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Build a client for one model.

        Args:
            model: Exact model ID.
            api_key: Overrides the configured key, for compatible endpoints.
            base_url: Overrides the endpoint, for compatible providers.

        Raises:
            StructuredCallError: If no API key is available.
        """
        import openai

        settings = get_settings()
        key = api_key or settings.openai_api_key
        if not key:
            raise StructuredCallError("No API key configured for this endpoint")

        self.model = model
        self.client = openai.OpenAI(api_key=key, base_url=base_url) if base_url else openai.OpenAI(api_key=key)

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system: str,
        max_tokens: int = 8_000,
        model: Optional[str] = None,
    ) -> tuple[dict, dict]:
        """Run a structured call and return (parsed data, usage).

        Args:
            prompt: The user-turn prompt.
            schema: Our JSON Schema for the response.
            system: System instruction.
            max_tokens: Output ceiling.
            model: Overrides the configured model for this call.

        Returns:
            Tuple of (parsed JSON, usage dict).

        Raises:
            StructuredCallError: On API failure or unparsable output.
        """
        model_id = model or self.model
        try:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response",
                        "strict": True,
                        "schema": schema,
                    },
                },
            )
        except Exception as e:
            raise StructuredCallError(f"{model_id} call failed: {e}") from e

        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise StructuredCallError(f"{model_id} returned no content")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise StructuredCallError(f"{model_id} response was not valid JSON: {e}") from e

        usage = {
            "input_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
            "cost": 0.0,
        }
        logger.info(
            f"{model_id} structured call: in={usage['input_tokens']} "
            f"out={usage['output_tokens']}"
        )
        return data, usage


def get_structured_client(model_id: str) -> Any:
    """Build the right client for a model ID.

    Args:
        model_id: Exact model identifier from config.

    Returns:
        A client exposing `generate_structured`.

    Raises:
        StructuredCallError: If the provider is unknown or unconfigured.
    """
    provider = provider_for(model_id)

    if provider == "anthropic":
        from backend.integrations.anthropic_client import get_anthropic_client

        return get_anthropic_client(model=model_id)

    if provider == "gemini":
        return GeminiStructuredClient(model=model_id)

    if provider == "openai":
        return OpenAIStructuredClient(model=model_id)

    if provider == "moonshot":
        import os

        key = os.environ.get("MOONSHOT_API_KEY") or get_settings().kimi_api_key
        if not key:
            raise StructuredCallError(
                "MOONSHOT_API_KEY is not set; the repo KIMI_API_KEY is dead (work order F)"
            )
        return OpenAIStructuredClient(model=model_id, api_key=key, base_url=MOONSHOT_BASE_URL)

    raise StructuredCallError(f"No client for provider {provider!r}")
