"""Producer pipeline package (Phase 8 - Doc 4).

This package handles Producer Packet generation (Doc 4).
Formerly Doc 3 — renamed 2026-03-12 (Phase 1.3.3). Doc 3 is now Creator Brief.

- Gating validation (V10 requirements)
- 4-stage producer pipeline

CRITICAL: All output is CREATIVE INTERPRETATION, not facts.
Doc 4 does not modify Doc 0/1/2/3.
"""

from backend.pipeline.producer.gating import (
    can_generate_producer_packet,
    get_source_summaries,
)

__all__ = [
    "can_generate_producer_packet",
    "get_source_summaries",
]
