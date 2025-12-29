"""Cost tracking for API calls throughout the pipeline.

Tracks estimated costs per API and enforces budget limits.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from loguru import logger


# API cost estimates (per call or per unit)
API_COSTS = {
    # OpenAI (per 1K tokens, approximate)
    "openai_gpt4o_mini_input": 0.00015,  # $0.15 per 1M input tokens
    "openai_gpt4o_mini_output": 0.0006,  # $0.60 per 1M output tokens
    "openai_gpt4_input": 0.03,  # $30 per 1M input tokens
    "openai_gpt4_output": 0.06,  # $60 per 1M output tokens

    # Perplexity (per request)
    "perplexity_search": 0.005,  # ~$0.005 per search

    # YouTube (free tier, but track for quotas)
    "youtube_search": 0.0,  # Free
    "youtube_video_details": 0.0,  # Free

    # Transcription
    "supadata_transcript": 0.0,  # Free tier
    "whisper_minute": 0.006,  # $0.006 per minute

    # Web capture (mostly free)
    "jina_reader": 0.0,  # Free
    "trafilatura": 0.0,  # Local
    "playwright": 0.0,  # Local

    # Other APIs
    "tavily_search": 0.001,  # ~$0.001 per search
    "exa_search": 0.001,  # ~$0.001 per search
    "reddit_api": 0.0,  # Free
}

# Budget limits per mode (USD)
MODE_BUDGETS = {
    "quick": 2.0,
    "full": 5.0,
    "breaking_news": 2.0,
    "investigation": 15.0,
    "profile": 8.0,
    "controversy": 10.0,
}


@dataclass
class CostTracker:
    """Tracks API costs throughout pipeline execution."""

    mode: str = "full"
    budget_limit: float = 5.0
    costs: Dict[str, float] = field(default_factory=dict)
    call_counts: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Set budget based on mode."""
        self.budget_limit = MODE_BUDGETS.get(self.mode, 5.0)

    def update_mode(self, new_mode: str) -> None:
        """Update mode and budget limit while preserving existing costs.

        Use this instead of creating a new CostTracker to avoid losing
        costs accumulated in earlier stages.
        """
        self.mode = new_mode
        self.budget_limit = MODE_BUDGETS.get(new_mode, 5.0)

    def add_cost(self, api_name: str, amount: float, units: int = 1) -> None:
        """
        Add cost for an API call.

        Args:
            api_name: Name of the API (e.g., 'openai_gpt4o_mini_input')
            amount: Cost amount in USD
            units: Number of units (e.g., tokens, minutes)
        """
        if api_name not in self.costs:
            self.costs[api_name] = 0.0
            self.call_counts[api_name] = 0

        self.costs[api_name] += amount * units
        self.call_counts[api_name] += 1

    def add_openai_cost(self, input_tokens: int, output_tokens: int, model: str = "gpt-4o-mini") -> float:
        """Add cost for OpenAI API call. Returns cost added."""
        if "gpt-4o-mini" in model:
            input_cost = (input_tokens / 1000) * API_COSTS["openai_gpt4o_mini_input"]
            output_cost = (output_tokens / 1000) * API_COSTS["openai_gpt4o_mini_output"]
        else:
            input_cost = (input_tokens / 1000) * API_COSTS["openai_gpt4_input"]
            output_cost = (output_tokens / 1000) * API_COSTS["openai_gpt4_output"]

        total = input_cost + output_cost
        self.add_cost(f"openai_{model}", total)
        return total

    def add_perplexity_cost(self, num_queries: int = 1) -> float:
        """Add cost for Perplexity search. Returns cost added."""
        cost = num_queries * API_COSTS["perplexity_search"]
        self.add_cost("perplexity_search", cost)
        return cost

    def add_whisper_cost(self, minutes: float) -> float:
        """Add cost for Whisper transcription. Returns cost added."""
        cost = minutes * API_COSTS["whisper_minute"]
        self.add_cost("whisper_transcription", cost)
        return cost

    @property
    def total_cost(self) -> float:
        """Get total cost across all APIs."""
        return sum(self.costs.values())

    @property
    def remaining_budget(self) -> float:
        """Get remaining budget."""
        return max(0.0, self.budget_limit - self.total_cost)

    @property
    def is_over_budget(self) -> bool:
        """Check if total cost exceeds budget."""
        return self.total_cost > self.budget_limit

    def check_budget(self, estimated_cost: float) -> bool:
        """Check if estimated cost would exceed budget."""
        return (self.total_cost + estimated_cost) <= self.budget_limit

    def get_summary(self) -> Dict:
        """Get cost summary for reporting."""
        return {
            "mode": self.mode,
            "budget_limit": self.budget_limit,
            "total_cost": round(self.total_cost, 4),
            "remaining_budget": round(self.remaining_budget, 4),
            "is_over_budget": self.is_over_budget,
            "costs_by_api": {k: round(v, 4) for k, v in self.costs.items()},
            "calls_by_api": self.call_counts.copy(),
        }

    def __str__(self) -> str:
        """String representation for logging."""
        return f"CostTracker(mode={self.mode}, total=${self.total_cost:.4f}/{self.budget_limit:.2f})"
