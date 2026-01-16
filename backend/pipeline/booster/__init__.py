"""
Booster Pipeline Package - Deep Research Booster.

The booster produces DIRECTIONS, not FACTS.
It tells you WHERE to look, not WHAT you'll find.
"""

from .context_bundle_generator import (
    generate_context_bundle,
    compute_bundle_hash,
)
from .expansion_builder import build_booster_expansion_markdown

__all__ = [
    "generate_context_bundle",
    "compute_bundle_hash",
    "build_booster_expansion_markdown",
]
