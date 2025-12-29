"""Unit tests for cost tracking functionality."""
import pytest

from backend.pipeline.cost_tracker import CostTracker, API_COSTS, MODE_BUDGETS


def test_cost_tracker_initialization():
    """Test CostTracker initializes with correct budget based on mode."""
    tracker = CostTracker(mode="quick")
    assert tracker.mode == "quick"
    assert tracker.budget_limit == MODE_BUDGETS["quick"]

    tracker = CostTracker(mode="investigation")
    assert tracker.mode == "investigation"
    assert tracker.budget_limit == MODE_BUDGETS["investigation"]


def test_cost_tracker_unknown_mode_defaults():
    """Test unknown mode uses default budget."""
    tracker = CostTracker(mode="unknown_mode")
    assert tracker.budget_limit == 5.0  # Default from __post_init__


def test_add_cost():
    """Test adding costs to tracker."""
    tracker = CostTracker(mode="full")

    tracker.add_cost("openai_gpt4o_mini", 0.001)
    tracker.add_cost("perplexity_search", 0.005)
    tracker.add_cost("openai_gpt4o_mini", 0.002)  # Add more to same API

    assert tracker.costs["openai_gpt4o_mini"] == 0.003
    assert tracker.costs["perplexity_search"] == 0.005
    assert tracker.call_counts["openai_gpt4o_mini"] == 2
    assert tracker.call_counts["perplexity_search"] == 1


def test_add_openai_cost():
    """Test adding OpenAI API costs."""
    tracker = CostTracker(mode="full")

    # Test GPT-4o-mini
    cost = tracker.add_openai_cost(input_tokens=1000, output_tokens=500, model="gpt-4o-mini")
    expected = (1000 / 1000) * API_COSTS["openai_gpt4o_mini_input"] + (500 / 1000) * API_COSTS["openai_gpt4o_mini_output"]
    assert abs(cost - expected) < 0.0001


def test_add_perplexity_cost():
    """Test adding Perplexity API costs."""
    tracker = CostTracker(mode="full")

    cost = tracker.add_perplexity_cost(num_queries=3)
    expected = 3 * API_COSTS["perplexity_search"]
    assert cost == expected


def test_add_whisper_cost():
    """Test adding Whisper transcription costs."""
    tracker = CostTracker(mode="full")

    cost = tracker.add_whisper_cost(minutes=10.5)
    expected = 10.5 * API_COSTS["whisper_minute"]
    assert cost == expected


def test_total_cost():
    """Test total cost calculation."""
    tracker = CostTracker(mode="full")

    tracker.add_cost("api1", 0.10)
    tracker.add_cost("api2", 0.25)
    tracker.add_cost("api3", 0.15)

    assert tracker.total_cost == 0.50


def test_remaining_budget():
    """Test remaining budget calculation."""
    tracker = CostTracker(mode="quick")  # $2 budget

    tracker.add_cost("api", 0.50)
    assert tracker.remaining_budget == 1.50

    tracker.add_cost("api", 2.00)
    assert tracker.remaining_budget == 0.0  # Cannot go negative


def test_is_over_budget():
    """Test over budget detection."""
    tracker = CostTracker(mode="quick")  # $2 budget

    tracker.add_cost("api", 1.00)
    assert not tracker.is_over_budget

    tracker.add_cost("api", 1.50)
    assert tracker.is_over_budget


def test_check_budget():
    """Test budget check for estimated costs."""
    tracker = CostTracker(mode="quick")  # $2 budget

    tracker.add_cost("api", 1.00)

    assert tracker.check_budget(0.50)  # Would leave $0.50 remaining
    assert tracker.check_budget(1.00)  # Would use exactly budget
    assert not tracker.check_budget(1.50)  # Would exceed budget


def test_get_summary():
    """Test summary generation."""
    tracker = CostTracker(mode="investigation")

    tracker.add_cost("openai", 0.10)
    tracker.add_cost("perplexity", 0.05)

    summary = tracker.get_summary()

    assert summary["mode"] == "investigation"
    assert summary["budget_limit"] == MODE_BUDGETS["investigation"]
    assert summary["total_cost"] == 0.15
    assert summary["remaining_budget"] == MODE_BUDGETS["investigation"] - 0.15
    assert not summary["is_over_budget"]
    assert "openai" in summary["costs_by_api"]
    assert "perplexity" in summary["costs_by_api"]


def test_str_representation():
    """Test string representation of tracker."""
    tracker = CostTracker(mode="full")
    tracker.add_cost("api", 1.23)

    str_repr = str(tracker)
    assert "full" in str_repr
    assert "1.23" in str_repr


def test_api_costs_defined():
    """Test that all expected API costs are defined."""
    expected_apis = [
        "openai_gpt4o_mini_input",
        "openai_gpt4o_mini_output",
        "perplexity_search",
        "whisper_minute",
    ]

    for api in expected_apis:
        assert api in API_COSTS


def test_mode_budgets_defined():
    """Test that all research modes have budgets defined."""
    expected_modes = ["quick", "full", "breaking_news", "investigation", "profile", "controversy"]

    for mode in expected_modes:
        assert mode in MODE_BUDGETS
        assert MODE_BUDGETS[mode] > 0
