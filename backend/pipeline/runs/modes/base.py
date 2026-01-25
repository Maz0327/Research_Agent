"""
Base run mode executor - Common logic for all run types.
"""

from datetime import datetime
from typing import Any, Optional

from loguru import logger

from backend.models.run_models import (
    Run, RunType, RunStatus, RunOutputs, RunMetrics,
)
from backend.pipeline.runs.storage import store_run_outputs, load_run_document
from backend.state import update_job


class RunModeExecutor:
    """
    Base class for run mode execution.

    Provides common infrastructure:
    - Progress tracking
    - Metrics collection
    - Document storage
    - Error handling
    """

    def __init__(self, job_id: str, run: Run, user_id: str):
        self.job_id = job_id
        self.run = run
        self.user_id = user_id
        self.metrics = RunMetricsCollector()
        self.start_time = datetime.utcnow()

    def update_progress(self, percent: int, detail: str = "") -> None:
        """Update run progress."""
        update_job(
            self.job_id,
            iteration_progress_percent=percent,
            pass_detail=detail[:100] if detail else None,
        )
        logger.debug(f"[{self.job_id}] Run {self.run.run_id}: {percent}% - {detail}")

    def load_parent_docs(self) -> dict[str, Any]:
        """Load documents from parent run."""
        parent_run_id = self.run.parent_run_id
        if not parent_run_id:
            raise ValueError("No parent run to load documents from")

        # Build paths based on parent run
        base_path = f"jobs/{self.job_id}/runs/{parent_run_id}"

        docs = {}
        for doc_num in [0, 1, 2]:
            path = f"{base_path}/doc_{doc_num}.json"
            doc = load_run_document(path)
            if doc:
                docs[f"doc_{doc_num}"] = doc
                logger.debug(f"[{self.job_id}] Loaded parent doc_{doc_num}")

        return docs

    def store_outputs(
        self,
        doc_0: Optional[dict] = None,
        doc_1: Optional[dict] = None,
        doc_2: Optional[dict] = None,
        is_doc_0_delta: bool = False,
        parent_doc_0_path: Optional[str] = None,
        new_source_ids: Optional[list[str]] = None,
    ) -> RunOutputs:
        """Store run outputs to GCS."""
        return store_run_outputs(
            job_id=self.job_id,
            run=self.run,
            doc_0=doc_0,
            doc_1=doc_1,
            doc_2=doc_2,
            is_doc_0_delta=is_doc_0_delta,
            parent_doc_0_path=parent_doc_0_path,
            new_source_ids=new_source_ids,
        )

    def get_metrics(self) -> RunMetrics:
        """Get collected metrics."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        return RunMetrics(
            wall_time_ms=int(elapsed),
            sources_processed=self.metrics.sources_processed,
            sources_new=self.metrics.sources_new,
            key_points_found=self.metrics.key_points_found,
            claims_extracted=self.metrics.claims_extracted,
            themes_identified=self.metrics.themes_identified,
            llm_cost_usd=self.metrics.llm_cost_usd,
            llm_tokens_input=self.metrics.tokens_in,
            llm_tokens_output=self.metrics.tokens_out,
        )


class RunMetricsCollector:
    """Collect metrics during run execution."""

    def __init__(self):
        self.sources_processed: int = 0
        self.sources_new: int = 0
        self.key_points_found: int = 0
        self.claims_extracted: int = 0
        self.themes_identified: int = 0
        self.llm_cost_usd: float = 0.0
        self.tokens_in: int = 0
        self.tokens_out: int = 0

    def record_llm_call(
        self,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Record an LLM API call."""
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.llm_cost_usd += cost

    def record_source(self, is_new: bool = False) -> None:
        """Record a processed source."""
        self.sources_processed += 1
        if is_new:
            self.sources_new += 1

    def record_extraction(
        self,
        key_points: int = 0,
        claims: int = 0,
        themes: int = 0,
    ) -> None:
        """Record extraction results."""
        self.key_points_found += key_points
        self.claims_extracted += claims
        self.themes_identified += themes
