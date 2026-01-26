"""
V2 Run Modes - Execution logic for different run types.

Each run type has specific logic for:
- add_sources: Find/add new sources, append to Doc 0 (delta), regenerate Doc 1/2
- fix_weak: Address gaps/weaknesses from previous run
- counter: Find counterarguments to claims
- angle: Explore different perspective
- regenerate: Re-run synthesis with same sources
"""

from backend.pipeline.runs.modes.base import RunModeExecutor
from backend.pipeline.runs.modes.add_sources import run_add_sources
from backend.pipeline.runs.modes.regenerate import run_regenerate

__all__ = [
    "RunModeExecutor",
    "run_add_sources",
    "run_regenerate",
]
