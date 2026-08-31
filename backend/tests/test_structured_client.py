"""Tests for the multi-provider structured-output client.

The lineup is env-driven by design, which only works if the pipeline can talk
to whichever provider a model name belongs to. Each provider's schema dialect
differs, and those differences are exactly what these tests pin: Gemini
rejects `additionalProperties`, and it must never lose a property that happens
to be NAMED like a JSON Schema keyword.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.integrations.structured_client import (
    FatalCallError,
    OpenAIStructuredClient,
    StructuredCallError,
    _accepts_minimal_thinking,
    _error_kind,
    _strip_for_gemini,
    provider_for,
)


class TestProviderRouting:
    """A model name decides which client answers it."""

    def test_known_prefixes(self):
        """Every model in the lineup routes somewhere."""
        assert provider_for("claude-sonnet-5") == "anthropic"
        assert provider_for("gemini-3.6-flash") == "gemini"
        assert provider_for("gpt-5.6-terra") == "openai"
        assert provider_for("kimi-k2.6") == "moonshot"

    def test_unknown_model_is_an_error(self):
        """A typo in an env var fails loudly rather than silently defaulting."""
        with pytest.raises(StructuredCallError, match="No provider knows"):
            provider_for("llama-4-maverick")


class TestGeminiSchemaTranslation:
    """Gemini takes a subset of JSON Schema, and only a subset."""

    def test_additional_properties_is_removed(self):
        """Measured: Gemini 400s on `additionalProperties` with "Unknown name"."""
        cleaned = _strip_for_gemini(
            {"type": "object", "additionalProperties": False, "properties": {"a": {"type": "string"}}}
        )

        assert "additionalProperties" not in cleaned

    def test_a_property_named_title_survives(self):
        """The bug this test exists for: `title` is a keyword AND a field name.

        Filtering keys everywhere deleted the subject map's `title` field from
        the schema, and Gemini then answered without it.
        """
        cleaned = _strip_for_gemini(
            {
                "type": "object",
                "title": "SubjectMap",
                "properties": {
                    "title": {"type": "string"},
                    "fact_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "fact_ids"],
            }
        )

        assert "title" in cleaned["properties"]
        # The keyword at schema level is dropped; the field of the same name is not.
        assert "title" not in {key for key in cleaned if key != "properties"}
        assert cleaned["required"] == ["title", "fact_ids"]

    def test_nested_schemas_are_cleaned_all_the_way_down(self):
        """Array items are schemas too."""
        cleaned = _strip_for_gemini(
            {
                "type": "object",
                "properties": {
                    "subjects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {"title": {"type": "string"}},
                            "required": ["title"],
                        },
                    }
                },
                "required": ["subjects"],
            }
        )

        item = cleaned["properties"]["subjects"]["items"]
        assert "additionalProperties" not in item
        assert item["properties"]["title"] == {"type": "string"}

    def test_real_pass_schemas_survive_translation(self):
        """Every wire schema keeps its fields through the Gemini translation."""
        from backend.models.briefing import (
            DISPUTE_SCHEMA,
            FILE_SCHEMA,
            READ_SCHEMA,
            SUBJECT_MAP_SCHEMA,
        )

        for schema in (READ_SCHEMA, SUBJECT_MAP_SCHEMA, FILE_SCHEMA, DISPUTE_SCHEMA):
            cleaned = _strip_for_gemini(schema)
            assert set(cleaned["properties"]) == set(schema["properties"])
            assert cleaned["required"] == schema["required"]


class TestThinkingLevelFloor:
    """Not every Gemini 3.x model accepts every thinking level.

    Measured 2026-08-20 during the D-031 reasoning A/B: 3.1-pro answered a
    request carrying `thinking_level="minimal"` with HTTP 400, which read at
    first like the model scoring zero rather than never being called at all.
    """

    def test_only_3_6_flash_takes_minimal(self):
        """The cheap level is a 3.6-flash affordance, not a 3.x one."""
        assert _accepts_minimal_thinking("gemini-3.6-flash") is True
        assert _accepts_minimal_thinking("gemini-3.1-pro-preview") is False
        assert _accepts_minimal_thinking("gemini-3.7-flash") is False

    def test_non_gemini_names_are_unaffected(self):
        """The floor never reaches a model it does not describe."""
        assert _accepts_minimal_thinking("gpt-5.4-mini") is True
        assert _accepts_minimal_thinking("") is True


class TestOpenAICompatibleClient:
    """One client covers OpenAI and every OpenAI-shaped endpoint."""

    def _client(self, content):
        client = OpenAIStructuredClient.__new__(OpenAIStructuredClient)
        client.model = "gpt-5.6-terra"
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content=content))]
        response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        client.client = MagicMock()
        client.client.chat.completions.create.return_value = response
        return client

    def test_parses_structured_output(self):
        """The happy path returns parsed JSON and usage."""
        client = self._client(json.dumps({"lede": "A lede.", "paragraphs": []}))

        data, usage = client.generate_structured(
            prompt="write it", schema={"type": "object"}, system="you write"
        )

        assert data["lede"] == "A lede."
        assert usage["input_tokens"] == 10

    def test_unparseable_output_is_an_error(self):
        """Bad JSON fails loudly instead of half-populating a document.

        Both call shapes are tried first, so the error arrives only after the
        fallback has also failed.
        """
        client = self._client("not json at all")

        with pytest.raises(StructuredCallError, match="no usable structured output"):
            client.generate_structured(
                prompt="write it", schema={"type": "object"}, system="you write"
            )

    def test_empty_output_is_an_error(self):
        """A refusal or an empty completion is never treated as content."""
        client = self._client("")

        with pytest.raises(StructuredCallError, match="no usable structured output"):
            client.generate_structured(
                prompt="write it", schema={"type": "object"}, system="you write"
            )

    def test_a_fenced_answer_still_parses(self):
        """Some providers wrap JSON in a markdown fence; that is not a failure."""
        client = self._client('```json\n{"lede": "A lede.", "paragraphs": []}\n```')

        data, _ = client.generate_structured(
            prompt="write it", schema={"type": "object"}, system="you write"
        )

        assert data["lede"] == "A lede."

    def test_the_fallback_shape_runs_when_the_first_returns_nothing(self):
        """Measured: kimi-k2.6 answers a strict json_schema with whitespace."""
        client = OpenAIStructuredClient.__new__(OpenAIStructuredClient)
        client.model = "kimi-k2.6"
        empty = MagicMock()
        empty.choices = [MagicMock(message=MagicMock(content="   \n  "))]
        empty.usage = MagicMock(prompt_tokens=1, completion_tokens=0)
        good = MagicMock()
        good.choices = [MagicMock(message=MagicMock(content='{"verdict": "supported"}'))]
        good.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        client.client = MagicMock()
        client.client.chat.completions.create.side_effect = [empty, good]

        data, _ = client.generate_structured(
            prompt="judge it", schema={"type": "object"}, system="you judge"
        )

        assert data["verdict"] == "supported"
        assert client.client.chat.completions.create.call_count == 2

    def test_newer_openai_models_get_the_parameter_they_accept(self):
        """gpt-5.x rejects max_tokens outright; the adapter knows which to send."""
        client = self._client('{"ok": true}')
        client.model = "gpt-5.6-terra"

        client.generate_structured(
            prompt="judge it", schema={"type": "object"}, system="you judge", max_tokens=123
        )

        kwargs = client.client.chat.completions.create.call_args.kwargs
        assert kwargs["max_completion_tokens"] == 123
        assert "max_tokens" not in kwargs

    def test_moonshot_routes_through_the_compatible_endpoint(self, monkeypatch):
        """The repo Kimi key is dead; the Moonshot key and base URL are used."""
        monkeypatch.setenv("MOONSHOT_API_KEY", "test-key")

        with patch(
            "backend.integrations.structured_client.OpenAIStructuredClient"
        ) as constructed:
            from backend.integrations.structured_client import (
                MOONSHOT_BASE_URL,
                get_structured_client,
            )

            get_structured_client("kimi-k2.6")

        constructed.assert_called_once_with(
            model="kimi-k2.6", api_key="test-key", base_url=MOONSHOT_BASE_URL
        )


# --- rate limits vs walls -------------------------------------------------
# Both arrive as 429s and need opposite handling. Written after the
# 2026-08-31 semantic-check run: the account emptied mid-pass, every
# remaining call burned both request shapes before failing, and ~380 calls
# of finished work was lost with no report written.

RATE_LIMIT = Exception(
    "Error code: 429 - {'error': {'message': 'Rate limit reached for gpt-4o "
    "on tokens per min (TPM): Limit 30000. Please try again in 104ms.', "
    "'code': 'rate_limit_exceeded'}}"
)
NO_CREDIT = Exception(
    "Error code: 429 - {'error': {'message': 'You have no credits remaining.', "
    "'type': 'insufficient_quota', 'code': 'credit_balance_exhausted'}}"
)
SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


def _client() -> OpenAIStructuredClient:
    with patch("openai.OpenAI"):
        client = OpenAIStructuredClient("gpt-5.6-terra", api_key="test-key")
    client.client = MagicMock()
    return client


def _answer(payload: str = '{"ok": true}'):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = payload
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 2
    return response


class TestErrorKind:
    def test_a_rate_limit_is_retryable(self):
        assert _error_kind(RATE_LIMIT) == "retryable"

    def test_an_empty_account_is_fatal(self):
        assert _error_kind(NO_CREDIT) == "fatal"

    def test_a_bad_key_is_fatal(self):
        assert _error_kind(Exception("Incorrect API key provided: sk-xxx")) == "fatal"

    def test_an_ordinary_failure_is_neither(self):
        assert _error_kind(ValueError("schema mismatch")) == "other"


class TestBackoff:
    def test_a_rate_limit_waits_then_succeeds(self):
        client = _client()
        client.client.chat.completions.create.side_effect = [RATE_LIMIT, _answer()]

        with patch("backend.integrations.structured_client.time.sleep") as slept:
            data, _ = client.generate_structured(prompt="p", schema=SCHEMA, system="s")

        assert data == {"ok": True}
        slept.assert_called_once_with(1)

    def test_waits_lengthen_and_then_give_up(self):
        client = _client()
        client.client.chat.completions.create.side_effect = RATE_LIMIT

        with (
            patch("backend.integrations.structured_client.time.sleep") as slept,
            pytest.raises(StructuredCallError),
        ):
            client.generate_structured(prompt="p", schema=SCHEMA, system="s")

        assert [call.args[0] for call in slept.call_args_list][:3] == [1, 4, 10]

    def test_an_empty_account_stops_at_once(self):
        """No waiting, and no second request shape: nothing about either fixes
        an empty account."""
        client = _client()
        client.client.chat.completions.create.side_effect = NO_CREDIT

        with (
            patch("backend.integrations.structured_client.time.sleep") as slept,
            pytest.raises(FatalCallError),
        ):
            client.generate_structured(prompt="p", schema=SCHEMA, system="s")

        assert client.client.chat.completions.create.call_count == 1
        slept.assert_not_called()

    def test_a_clean_call_never_sleeps(self):
        client = _client()
        client.client.chat.completions.create.return_value = _answer()

        with patch("backend.integrations.structured_client.time.sleep") as slept:
            data, _ = client.generate_structured(prompt="p", schema=SCHEMA, system="s")

        assert data == {"ok": True}
        slept.assert_not_called()
