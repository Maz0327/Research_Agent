"""Legacy pipeline modules - preserved for backwards compatibility.

This package contains modules that have been superseded by the new
semantic pipeline but are kept for backwards compatibility with
existing imports and the legacy extraction pipeline.

MODULES:
- transcripts.py: Legacy transcript fetching (spec-misaligned)
  - Use: backend.pipeline.transcript_acquisition instead
- extraction.py: Legacy OpenAI-based extraction
  - Use: backend.pipeline.stages.semantic_extraction instead

These modules should NOT be used in new code.
"""
