"""
Track iteration metrics (LLM calls, tokens, wall time).

Accumulates metrics during iteration execution and finalizes to IterationMetrics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.models.job_record import IterationMetrics


@dataclass
class MetricsTracker:
    """
    Accumulate metrics during iteration execution.

    Usage:
        metrics = MetricsTracker()
        # ... during execution ...
        metrics.record_llm_call(tokens_in=1000, tokens_out=500)
        # ... at end ...
        final = metrics.finalize()
    """

    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    def record_llm_call(
        self,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        """
        Record an LLM call with token counts.

        Args:
            tokens_in: Input tokens used
            tokens_out: Output tokens generated
        """
        self.llm_calls += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out

    def finalize(self) -> IterationMetrics:
        """
        Finalize metrics with wall time.

        Returns:
            IterationMetrics model with all accumulated metrics
        """
        end_time = datetime.now(timezone.utc)
        wall_time_ms = int((end_time - self.start_time).total_seconds() * 1000)

        return IterationMetrics(
            llm_calls=self.llm_calls,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            wall_time_ms=wall_time_ms,
        )
