"""Producer pipeline package (Phase 8 - Doc 3).

This package handles Producer Packet generation:
- Gating validation (V10 requirements)
- 4-stage producer pipeline

CRITICAL: All output is CREATIVE INTERPRETATION, not facts.
Doc 3 does not modify Doc 0/1/2.
"""

from backend.pipeline.producer.gating import (
    can_generate_producer_packet,
    get_source_summaries,
)

__all__ = [
    "can_generate_producer_packet",
    "get_source_summaries",
]
