---
title: "Fix Producer Packet Storage Fetch"
description: "Add semantic_brief fetch from storage before producer pipeline runs"
status: done
priority: P1
effort: 30m
branch: main
tags: [backend, bugfix, producer, storage]
created: 2026-01-24
---

# Fix Producer Packet Storage Fetch

## Problem

Producer Packet (Doc 3) returns empty output because `semantic_brief` (Doc 2) is not fetched from storage before the producer pipeline runs.

**Root Cause:** Worker fetches `source_ledger` for gating but never fetches `semantic_brief` for the actual pipeline.

## Solution

Add storage fetch logic for `semantic_brief` in `worker.py` before calling `run_producer_pipeline()`.

## Phases

| Phase | Description | Status | Effort |
|-------|-------------|--------|--------|
| [Phase 1](phase-01-add-storage-fetch.md) | Add semantic_brief fetch logic | Done | 20m |
| [Phase 2](phase-02-validation.md) | Test with affected job | Pending | 10m |

## Files to Modify

- `backend/worker.py` - Add fetch logic in `run_producer_task`

## Success Criteria

1. Producer Packet generates Story Core with populated fields
2. Narrative angles, hooks, titles generated (2+ each)
3. No regression in gating logic
4. Works for storage-based and inline artifacts

## Related

- Brainstorm: `plans/reports/brainstorm-260124-1809-producer-packet-empty-output.md`
- Spec: `docs/authoritative/prompts/PRODUCER_PACKET_SPEC.md`
