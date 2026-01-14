# Legacy Pipeline Modules

This folder contains modules that have been superseded by the new semantic pipeline.

## Why These Are Here

| Module | Issue | Replacement |
|--------|-------|-------------|
| `transcripts.py` | Missing YouTube captions tier, spec-misaligned terminology | `backend.pipeline.transcript_acquisition` |
| `extraction.py` | Uses OpenAI, not Gemini; legacy claim/quote extraction | `backend.pipeline.stages.semantic_extraction` |

## Spec Misalignment (transcripts.py)

**Current implementation:**
1. Supadata native
2. Supadata AI (AI-generated, NOT YouTube captions)
3. Whisper

**Spec requirement (RASS.md Section 8.1):**
1. Supadata -> transcript_grounded
2. Whisper -> transcript_grounded
3. YouTube captions -> caption_grounded
4. None -> video_only

The "YouTube captions" tier is completely missing, and terminology differs.

## Do Not Use

These modules are kept for:
1. Backwards compatibility with existing imports (via deprecation shim)
2. Legacy topic research pipeline (non-video mode)

New semantic pipeline code MUST NOT import from this folder.
