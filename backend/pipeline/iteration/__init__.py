"""
Iteration loop pipeline for refining research results.

This package implements the iteration feature that allows users to:
- more_sources: Add new sources via web search, re-synthesize
- deeper: Re-extract existing sources with deeper prompts
- different_angle: Re-synthesize with angle-specific focus
- custom: Apply user prompt to synthesis

All iterations are APPEND-ONLY: baseline docs are NEVER modified.
"""

from .baseline_loader import load_baseline, BaselineData
from .context_initializer import create_iteration_context
from .storage_manager import store_iteration_docs
from .metrics_tracker import MetricsTracker

__all__ = [
    "load_baseline",
    "BaselineData",
    "create_iteration_context",
    "store_iteration_docs",
    "MetricsTracker",
]
