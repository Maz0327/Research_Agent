"""
Run-based pipeline operations.

This module provides the V2 run abstraction for managing research outputs.
Each run produces a Doc 0/1/2 set, with optional Producer/Booster.
"""

from backend.pipeline.runs.storage import (
    store_run_outputs,
    load_run_document,
    get_merged_doc_0,
    store_run_producer,
    store_run_booster,
)
from backend.pipeline.runs.modes import (
    RunModeExecutor,
    run_add_sources,
    run_regenerate,
)

__all__ = [
    # Storage
    "store_run_outputs",
    "load_run_document",
    "get_merged_doc_0",
    "store_run_producer",
    "store_run_booster",
    # Modes
    "RunModeExecutor",
    "run_add_sources",
    "run_regenerate",
]
