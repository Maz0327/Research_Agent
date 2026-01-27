# Claim Extractor v2 Backend Implementation Report

**Date:** 2026-01-27
**Branch:** `claude/claim-extractor-v2-backend-KJ2Vg`
**Scope:** Backend only (models, pipeline, routes, worker)

---

## 1) Findings: Current Claim Extractor Behavior

### Before v2 Changes

| Component | File | Behavior | Issue |
|-----------|------|----------|-------|
| Timestamp Handling | `claim_extraction.py:226-232` | LLM returns `timestamp_start/end`, code uses directly | No validation against segment bounds |
| Transcript Source | `claim_extraction.py:557-568` | Supadata `get_transcript()` returns `text` only | Timing info (`segments`) not captured |
| Entity Extraction | N/A | Not implemented | Claims had no linked entities |
| Anchor Types | `claims.py:57-76` | `timestamp`, `line_range`, `image` | No `source_id` on nested anchors |
| Warnings | N/A | Not implemented | No warning system for extraction issues |

### Timestamps Were NOT "Guessed"
Contrary to initial assumption, timestamps were provided by the LLM based on the prompt. However:
- **No validation** that timestamps fall within known segment bounds
- **No fallback** to line anchors when timing unavailable
- **No warning** when transcript lacks timing metadata

---

## 2) Final Contracts

### A) Anchor Types (Allowed)

```
YOUTUBE_TIMESTAMP    - Requires transcript_segments with start_ms/end_ms
TEXT_LINE_RANGE      - For text/articles OR videos without timing
IMAGE_INDEX          - For screenshots with region + ocr_excerpt
```

Each anchor MUST include `source_id`.

### B) ClaimsDocument v2 Schema

```json
{
  "metadata": {
    "job_id": "string",
    "run_id": "string | null",
    "created_at": "ISO8601",
    "title": "string",
    "total_claims": 0,
    "total_explicit": 0,
    "total_implied": 0,
    "source_count": 0,
    "extraction_model": "gemini-2.5-flash",
    "total_entities": 0,
    "total_clusters": 0,
    "version": "2.0"
  },
  "sources": [{
    "source_id": "SRC_001",
    "source_type": "youtube|article|text|screenshot",
    "title": "string",
    "url": "string | null",
    "claim_count": 0,
    "explicit_count": 0,
    "implied_count": 0,
    "timing_available": true,
    "anchor_type_used": "youtube_timestamp|text_line_range|image_index",
    "entity_count": 0
  }],
  "claims": [{
    "claim_id": "CLM_SRC_001_001",
    "text": "Claim statement",
    "claim_type": "explicit|implied",
    "confidence": "high|medium|low",
    "anchor": {
      "timestamp": {"start_seconds": 120, "end_seconds": 145, "formatted": "2:00-2:25", "source_id": "SRC_001"},
      "line_range": null,
      "image": null,
      "source_id": "SRC_001"
    },
    "source_id": "SRC_001",
    "context": "Surrounding context",
    "verbatim_excerpt": "Exact text from source",
    "entities_involved": ["ENT_001", "ENT_002"]
  }],
  "entities": {
    "people": [{
      "entity_id": "ENT_SRC_001_001",
      "canonical_label": "John Smith",
      "entity_type": "person",
      "aliases": ["J. Smith"],
      "context_summary": "1-2 sentences derived from context_evidence only",
      "context_evidence": [{
        "excerpt": "Verbatim text",
        "anchor": { ... },
        "source_id": "SRC_001"
      }],
      "top_anchors": [{ ... }],
      "linked_claim_cluster_ids": [],
      "ambiguity_flags": []
    }],
    "orgs": [...],
    "places": [...],
    "unnamed": [...],
    "unresolved_references": [...]
  },
  "clusters": [...],
  "warnings": [{
    "code": "TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS",
    "message": "Human-readable message",
    "source_id": "SRC_001 | null",
    "details": { ... }
  }]
}
```

### C) Warning Codes

| Code | Trigger | Action |
|------|---------|--------|
| `TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS` | Transcript lacks timing | Use line anchors instead |
| `TIMESTAMP_OUT_OF_BOUNDS` | LLM timestamp > segment max | Clamp to bounds |
| `TIMESTAMP_COERCED_TO_LINE` | LLM returns timestamp when unavailable | Coerce to line anchor |
| `ENTITY_MISSING_EVIDENCE` | Entity has no verbatim excerpt | Use context_summary fallback |
| `CLAIM_MISSING_ANCHOR` | Claim has no verbatim evidence | Log warning |
| `EMPTY_EXTRACTION` | No claims/entities extracted | Log warning |

### D) Run-Scoped Claims Doc

Similar to `producer_packet` and `booster_expansion`:

```python
class RunClaimsDoc(BaseModel):
    status: RunStatus  # queued|running|completed|failed
    path: Optional[str]  # Storage path
    inline: Optional[dict]  # Fallback
    markdown: Optional[str]  # Rendered MD
    warnings: list[str]
    total_claims: int
    total_entities: int
```

---

## 3) Exact Patches

### Files Modified

| File | Lines Changed | Summary |
|------|---------------|---------|
| `backend/models/claims.py` | +200 | EntityIndex, WarningCode, v2 fields |
| `backend/pipeline/claim_extraction.py` | +350 | Timing detection, entity extraction, prompts |
| `backend/models/run_models.py` | +25 | RunClaimsDoc model, has_claims_doc() |
| `backend/models/job_record.py` | +10 | claims_doc tracking fields |
| `backend/app/routes/jobs_routes.py` | +100 | POST /claims-doc endpoint |
| `backend/worker.py` | +180 | run_claims_doc_task |
| `backend/tests/test_claim_extractor_v2.py` | +400 | New test file |

### Key Changes in `claim_extraction.py`

1. **Timing Detection** (`parse_transcript_segments`):
   - Checks Supadata response for `content[].start/end` fields
   - Returns `(segments, timing_available: bool)`

2. **Prompt Selection**:
   - `YOUTUBE_EXTRACTION_TIMED_PROMPT` for timed transcripts
   - `YOUTUBE_EXTRACTION_LINES_PROMPT` for non-timed

3. **Anchor Validation** (`validate_timestamp_bounds`):
   - Clamps timestamps to segment bounds
   - Returns warning if out of bounds

4. **Entity Extraction** (`extract_entities_from_response`):
   - Parses LLM entity output
   - Creates Entity objects with ContextEvidence

---

## 4) Tests Added

### `backend/tests/test_claim_extractor_v2.py`

| Test Class | Count | Coverage |
|------------|-------|----------|
| `TestAnchorModels` | 7 | Timestamp, LineRange, ClaimAnchor |
| `TestEntityModels` | 5 | Entity, EntityIndex, unnamed entities |
| `TestClaimsDocument` | 6 | create_empty, add_claim, add_entity, warnings |
| `TestWarningCodes` | 2 | All codes exist, ExtractionWarning |
| `TestClaimExtractionHelpers` | 4 | number_lines, format_timestamp, parse_segments |
| `TestRunClaimsDoc` | 2 | Model creation, has_claims_doc() |

**Total: 26 tests**

---

## 5) Local Verification Steps

### Prerequisites
```bash
cd /home/user/Research_Agent
source venv/bin/activate  # or .venv/bin/activate
```

### A) Run Tests
```bash
# Run new tests only
pytest backend/tests/test_claim_extractor_v2.py -v

# Run all tests
pytest backend/tests/ -v
```

### B) Verify Syntax (No venv needed)
```bash
python3 -c "import ast; ast.parse(open('backend/models/claims.py').read()); print('claims.py OK')"
python3 -c "import ast; ast.parse(open('backend/pipeline/claim_extraction.py').read()); print('claim_extraction.py OK')"
python3 -c "import ast; ast.parse(open('backend/models/run_models.py').read()); print('run_models.py OK')"
python3 -c "import ast; ast.parse(open('backend/app/routes/jobs_routes.py').read()); print('jobs_routes.py OK')"
python3 -c "import ast; ast.parse(open('backend/worker.py').read()); print('worker.py OK')"
```

### C) Start API/Worker
```bash
# Terminal 1: API
uvicorn backend.app.main:app --reload --port 8000

# Terminal 2: Worker
celery -A backend.worker worker --loglevel=INFO
```

### D) Create Sample Claim Job (Standalone Mode)
```bash
curl -X POST http://localhost:8000/api/jobs/claim-extraction \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Claim Extraction",
    "video_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    "model": "gemini-2.5-flash"
  }'
```

### E) Trigger Claims Doc for Run (Post-Run Mode)
```bash
# After a semantic job completes
curl -X POST http://localhost:8000/api/jobs/{job_id}/runs/run_0/claims-doc \
  -H "Authorization: Bearer {token}"
```

### F) Verify in Logs
Look for:
- `Extracted X claims, Y entities from YouTube: Title (timing=yes/no)`
- `Claims doc completed: X claims, Y entities (Z warnings)`
- No `timestamp_start` when timing unavailable
- Warning codes in response

---

## 6) Unresolved Questions

1. **Supadata Segments**: The current Supadata client returns `text` only. Need to verify if API supports `content[]` with timing.

2. **Screenshot OCR**: Screenshots in Doc 0 not yet supported in claims-doc trigger mode.

3. **Entity Deduplication**: Cross-source entity merging not implemented (same person in multiple sources).

4. **Claim Clustering**: ClaimCluster model added but clustering logic not implemented.

---

## Summary

Claim Extractor v2 backend implementation complete:
- Timestamp anchoring fixed (line fallback when unavailable)
- Entity Index with excerpt+anchor evidence
- Run-scoped claims_doc trigger (like producer/booster)
- Warning system for extraction issues
- 26 tests added

**Status:** Ready for frontend integration and end-to-end testing.
