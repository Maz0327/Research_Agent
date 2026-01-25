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

__all__ = [
    "store_run_outputs",
    "load_run_document",
    "get_merged_doc_0",
    "store_run_producer",
    "store_run_booster",
]
