"""
V2 Run Modes - Execution logic for different run types.

Run types:
- expand: Find/add new sources, append findings to Doc 0/1/2
- refine: Re-analyze existing sources from new angle, append to Doc 1/2
- regenerate: Full rewrite of Doc 1/2 from all sources

Legacy types (mapped to canonical):
- add_sources → expand
- fix_weak → refine
- counter → expand
- angle → refine
"""

from backend.pipeline.runs.modes.base import RunModeExecutor
from backend.pipeline.runs.modes.expand import run_expand
from backend.pipeline.runs.modes.refine import run_refine
from backend.pipeline.runs.modes.regenerate import run_regenerate

# Keep legacy import for backward compatibility
from backend.pipeline.runs.modes.add_sources import run_add_sources

__all__ = [
    "RunModeExecutor",
    "run_expand",
    "run_refine",
    "run_regenerate",
    "run_add_sources",  # Legacy, kept for backward compat
]
