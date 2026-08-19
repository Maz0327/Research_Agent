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
    OpenAIStructuredClient,
    StructuredCallError,
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
        """Bad JSON fails loudly instead of half-populating a document."""
        client = self._client("not json at all")

        with pytest.raises(StructuredCallError, match="not valid JSON"):
            client.generate_structured(
                prompt="write it", schema={"type": "object"}, system="you write"
            )

    def test_empty_output_is_an_error(self):
        """A refusal or an empty completion is never treated as content."""
        client = self._client("")

        with pytest.raises(StructuredCallError, match="no content"):
            client.generate_structured(
                prompt="write it", schema={"type": "object"}, system="you write"
            )

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
