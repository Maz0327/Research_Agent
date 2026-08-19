"""Tests for the fact-harvest stage.

Cover for P3 work-order item B10. Semantic extraction abstracts: on the films
corpus it turned 10,465 words carrying 85 numbers into 1,165 words carrying 1.
The harvest pass keeps the concrete material, and its inventory is what the
Briefing's coverage gate checks the finished document against.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.models.semantic_units import AnalysisMode
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.harvest_stage import (
    HARVEST_SYSTEM,
    build_inventory,
    fact_id,
    harvest_source,
    stage_harvest,
)


def _client(facts, cost=0.03):
    """A structured-output client returning the given facts."""
    client = MagicMock()
    client.generate_structured.return_value = ({"facts": facts}, {"cost": cost})
    return client


def _package(source_id, content, title="A source"):
    """A minimal source identity package."""
    return SimpleNamespace(
        source_id=source_id,
        title=title,
        content=content,
        analysis_mode=AnalysisMode.ARTICLE_FETCHED,
    )


class TestHarvestSource:
    """One source, one call, facts back."""

    def test_returns_facts_and_cost(self):
        """Facts are trimmed and the call's cost is reported."""
        client = _client(["  Jurassic Park contains about 50 digital shots.  ", "", "  "])

        facts, cost = harvest_source(client, "SRC_1", "A film essay", "body text")

        assert facts == ["Jurassic Park contains about 50 digital shots."]
        assert cost == 0.03

    def test_prompt_carries_the_identity_lock(self):
        """The constitution's guardrails travel with every call."""
        client = _client(["A fact."])

        harvest_source(client, "SRC_3", "A film essay", "body text", ceiling="HIGH")

        kwargs = client.generate_structured.call_args.kwargs
        assert "SOURCE IDENTITY LOCK" in kwargs["prompt"]
        assert "source_id: SRC_3" in kwargs["prompt"]
        assert "CONFIDENCE CEILING: HIGH" in kwargs["prompt"]
        assert "EMPTY OUTPUT PERMISSION" in kwargs["system"]
        assert kwargs["system"] == HARVEST_SYSTEM

    def test_text_is_truncated_to_the_configured_limit(self):
        """Long sources are cut at the proven character budget."""
        client = _client(["A fact."])

        harvest_source(client, "SRC_1", "T", "x" * 50_000, max_chars=100)

        prompt = client.generate_structured.call_args.kwargs["prompt"]
        assert prompt.endswith("x" * 100)
        assert not prompt.endswith("x" * 101)


class TestInventory:
    """The inventory is the gate's input, so its IDs must be stable."""

    def test_fact_ids_are_source_qualified(self):
        """Facts follow the same ID convention as every other unit."""
        assert fact_id("SRC_3", 0) == "SRC_3:F_1"

    def test_inventory_shape(self):
        """Each entry names its source and whether it carries a number."""
        inventory = build_inventory(
            {"SRC_1": ["The dig ran for 3 seasons.", "Excavation was abandoned."]}
        )

        assert inventory == [
            {
                "fact_id": "SRC_1:F_1",
                "source_id": "SRC_1",
                "text": "The dig ran for 3 seasons.",
                "has_number": True,
            },
            {
                "fact_id": "SRC_1:F_2",
                "source_id": "SRC_1",
                "text": "Excavation was abandoned.",
                "has_number": False,
            },
        ]

    def test_empty_harvest(self):
        """No facts, no inventory."""
        assert build_inventory({}) == []


class TestStageHarvest:
    """The stage runs per source and never fails a job on its own."""

    @pytest.fixture(autouse=True)
    def _no_job_updates(self, monkeypatch):
        """Keep the stage from writing to job state during tests."""
        monkeypatch.setattr(
            "backend.pipeline.stages.harvest_stage.update_job", lambda *a, **k: None
        )

    def _ctx(self, packages):
        ctx = PipelineContext(job_id="job-1", topic="A topic")
        ctx.source_identity_packages = packages
        return ctx

    def test_harvests_every_source(self, monkeypatch):
        """Each source gets its own call, and the inventory pools them."""
        client = _client(["Fact one.", "Fact two with 3 numbers."])
        monkeypatch.setattr(
            "backend.integrations.anthropic_client.get_anthropic_client",
            lambda model=None: client,
        )
        ctx = self._ctx([_package("SRC_1", "body one"), _package("SRC_2", "body two")])

        stage_harvest(ctx)

        assert client.generate_structured.call_count == 2
        assert set(ctx.harvest) == {"SRC_1", "SRC_2"}
        assert len(ctx.harvest_inventory) == 4
        assert ctx.harvest_inventory[0]["fact_id"] == "SRC_1:F_1"

    def test_a_failing_source_is_a_warning_not_a_failure(self, monkeypatch):
        """One bad source does not cost the job its harvest."""
        client = MagicMock()
        client.generate_structured.side_effect = [
            RuntimeError("API down"),
            ({"facts": ["Fact two."]}, {"cost": 0.01}),
        ]
        monkeypatch.setattr(
            "backend.integrations.anthropic_client.get_anthropic_client",
            lambda model=None: client,
        )
        ctx = self._ctx([_package("SRC_1", "body one"), _package("SRC_2", "body two")])

        stage_harvest(ctx)

        assert set(ctx.harvest) == {"SRC_2"}
        assert any("Fact harvest failed for SRC_1" in w for w in ctx.warnings)

    def test_sources_without_text_are_skipped(self, monkeypatch):
        """Nothing to harvest means no call and no cost."""
        client = _client(["Fact."])
        monkeypatch.setattr(
            "backend.integrations.anthropic_client.get_anthropic_client",
            lambda model=None: client,
        )
        ctx = self._ctx([_package("SRC_1", "")])

        stage_harvest(ctx)

        assert client.generate_structured.call_count == 0
        assert ctx.harvest == {}

    def test_disabled_by_config(self, monkeypatch):
        """The stage can be turned off without touching code."""
        from backend.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "harvest_enabled", False)
        client = _client(["Fact."])
        monkeypatch.setattr(
            "backend.integrations.anthropic_client.get_anthropic_client",
            lambda model=None: client,
        )
        ctx = self._ctx([_package("SRC_1", "body")])

        stage_harvest(ctx)

        assert client.generate_structured.call_count == 0
