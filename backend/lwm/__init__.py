"""LWM V1 control surface — the one supported backend for the Lost With Maz pipeline.

This package is the production bridge between the Research Agent (this repo)
and the v4 writing pipeline (repo `Maz0327/lwm-pipeline`, on disk at
`~/.openclaw/workspace`). It replaces the one-off scratchpad adapters that
carried the Packer episode across by hand.

Ownership: the Research Agent owns research outputs (Doc 0 stays source
truth); lwm-pipeline owns episode state (STAGE-LEDGER.md stays the only
detailed authority); THIS package is the single home of the transformation
logic between them. Entry point: `python -m backend.lwm.cli`, wrapped by
`bin/lwm` in the workspace repo. Contract for the Phase 2 UI:
`pipeline/PHASE2-CONTRACT.md` in lwm-pipeline.
"""
