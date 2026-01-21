# Phase 02: Backend Modularization

## Context Links
- [Pipeline Modularization Audit](../reports/code-reviewer-251228-1819-pipeline-modularization-audit.md)
- [Integration Clients Audit](../reports/code-reviewer-251228-1819-integration-clients-audit.md)
- [Development Rules](../../docs/development-rules.md) - 200 LOC limit

## Overview

| Field | Value |
|-------|-------|
| Priority | P1 (High) |
| Status | Pending |
| Effort | 12 hours |
| Risk | Medium |

Split 5 large backend files exceeding 200 LOC limit into focused modules.

**Files to split:**
| File | Current LOC | Target |
|------|-------------|--------|
| `stages.py` | 898 | 8 modules (~80-120 each) |
| `extraction.py` | 811 | 5 modules (~150 each) |
| `quality_gate.py` | 645 | 6 modules (~100 each) |
| `perplexity_client.py` | 546 | 3 modules (~180 each) |
| `google_drive_docs.py` | 519 | 3 modules (~170 each) |

## Requirements

### Functional
1. Split files without changing external API
2. Preserve all existing imports through `__init__.py`
3. Maintain backward compatibility

### Non-Functional
- Each resulting file under 200 lines
- No functionality changes (pure refactor)
- All tests pass after refactor

## Architecture

### 1. Pipeline Stages Split

```
backend/pipeline/stages/
├── __init__.py              # Export all stage functions
├── initialization.py        # stage_0_initialize, stage_10_completion (~80 lines)
├── planning.py              # stage_1_planning, stage_2_research_mapping (~120 lines)
├── discovery.py             # stage_3_source_shortlist, stage_3_5_quality_gate (~100 lines)
├── youtube.py               # stage_4_youtube_enumeration, stage_5_transcripts (~130 lines)
├── web_capture.py           # stage_6_web_capture, stage_6_5_reddit (~120 lines)
├── extraction_stages.py     # stage_7_claims, stage_7_5_timeline, stage_7_6_entities (~130 lines)
├── analysis.py              # stage_8_validation, stage_8_5_angles, stage_8_6_doc_intel (~150 lines)
├── output.py                # stage_9_drive_upload (~65 lines)
└── helpers.py               # post_slack_message, shared utilities (~20 lines)
```

### 2. Extraction Split

```
backend/pipeline/extraction/
├── __init__.py              # Export extract_claims()
├── chunking.py              # _chunk_transcript_text, _chunk_web_text (~140 lines)
├── candidates.py            # _extract_claim_candidates (~70 lines)
├── canonicalization.py      # _canonicalize_claims_with_openai (~110 lines)
├── deduplication.py         # _dedupe_claims, MinHash/fallback (~150 lines)
└── formatting.py            # _generate_quote_bank_md, _generate_claims_ledger_md (~110 lines)
```

### 3. Quality Gate Split

```
backend/pipeline/quality_gate/
├── __init__.py              # Export run_quality_gate, quality_gate
├── config.py                # Constants, whitelists, patterns (~120 lines)
├── models.py                # Source, QualityGateStats, QualityGateOutput (~100 lines)
├── scoring.py               # _calculate_quality_score, _calculate_bm25_scores (~100 lines)
├── filtering.py             # _deduplicate, _check_hard_rejection (~80 lines)
├── allocation.py            # _allocate_slots, _calculate_type_weights (~160 lines)
└── core.py                  # quality_gate main function (~80 lines)
```

### 4. Perplexity Client Split

```
backend/integrations/perplexity/
├── __init__.py              # Export PerplexityClient
├── client.py                # Core API wrapper (~180 lines)
├── parsers.py               # URL extraction, classification (~180 lines)
└── formatters.py            # Markdown generation (~180 lines)
```

### 5. Google Drive Split

```
backend/integrations/google_drive/
├── __init__.py              # Export main functions
├── client.py                # Core Drive/Docs API wrapper (~180 lines)
├── research_packet.py       # Research packet creation (~170 lines)
└── permissions.py           # Sharing and permission logic (~170 lines)
```

## Implementation Steps

### Step 1: Create stages/ Module (3h)

1. Create directory:
   ```bash
   mkdir -p backend/pipeline/stages
   ```

2. Create `__init__.py`:
   ```python
   # backend/pipeline/stages/__init__.py
   from .initialization import stage_0_initialize, stage_10_completion
   from .planning import stage_1_planning, stage_2_research_mapping
   from .discovery import stage_3_source_shortlist, stage_3_5_quality_gate
   from .youtube import stage_4_youtube_enumeration, stage_5_transcripts
   from .web_capture import stage_6_web_capture, stage_6_5_reddit
   from .extraction_stages import stage_7_claims, stage_7_5_timeline, stage_7_6_entities
   from .analysis import stage_8_validation, stage_8_5_angles, stage_8_6_doc_intel
   from .output import stage_9_drive_upload
   from .helpers import post_slack_message

   __all__ = [
       "stage_0_initialize",
       "stage_1_planning",
       # ... all stages
   ]
   ```

3. Split stages.py by line ranges:
   - Lines 31-109 → `planning.py`
   - Lines 115-134 → `planning.py`
   - Lines 140-235 → `discovery.py`
   - Lines 241-329 → `discovery.py`
   - Lines 335-403 → `youtube.py`
   - Lines 409-490 → `web_capture.py`
   - Lines 496-533 → `web_capture.py`
   - Lines 540-620 → `extraction_stages.py`
   - Lines 626-768 → `analysis.py`
   - Lines 774-835 → `output.py`
   - Lines 841-898 → `initialization.py`

4. Update worker.py imports:
   ```python
   # backend/worker.py
   from backend.pipeline.stages import (
       stage_0_initialize,
       stage_1_planning,
       # ... all stages
   )
   ```

### Step 2: Create extraction/ Module (2h)

1. Create directory:
   ```bash
   mkdir -p backend/pipeline/extraction
   ```

2. Split extraction.py:
   - Lines 76-138 → `chunking.py`
   - Lines 141-210 → `candidates.py`
   - Lines 213-326 → `canonicalization.py`
   - Lines 368-512 → `deduplication.py`
   - Lines 707-810 → `formatting.py`

3. Create `__init__.py`:
   ```python
   from .core import extract_claims
   __all__ = ["extract_claims"]
   ```

4. Create `core.py` with main orchestrator (extract_claims function)

### Step 3: Create quality_gate/ Module (2h)

1. Create directory:
   ```bash
   mkdir -p backend/pipeline/quality_gate
   ```

2. Split quality_gate.py:
   - Lines 39-106 → `config.py`
   - Lines 113-208 → `models.py`
   - Lines 348-445 → `scoring.py`
   - Lines 334-463 → `filtering.py`
   - Lines 466-597 → `allocation.py`
   - Lines 214-316 → `core.py`

3. Create `__init__.py`:
   ```python
   from .core import quality_gate, run_quality_gate
   from .models import Source, QualityGateStats, QualityGateOutput
   __all__ = ["quality_gate", "run_quality_gate", "Source", "QualityGateStats", "QualityGateOutput"]
   ```

### Step 4: Create perplexity/ Module (2h)

1. Create directory:
   ```bash
   mkdir -p backend/integrations/perplexity
   ```

2. Split perplexity_client.py:
   - Core client methods → `client.py`
   - URL extraction/validation → `parsers.py`
   - Markdown generation → `formatters.py`

3. Create `__init__.py`:
   ```python
   from .client import PerplexityClient
   __all__ = ["PerplexityClient"]
   ```

### Step 5: Create google_drive/ Module (2h)

1. Create directory:
   ```bash
   mkdir -p backend/integrations/google_drive
   ```

2. Split google_drive_docs.py:
   - Service initialization → `client.py`
   - Research packet creation → `research_packet.py`
   - Sharing logic → `permissions.py`

3. Create `__init__.py`:
   ```python
   from .client import get_drive_service, get_docs_service
   from .research_packet import create_research_packet
   from .permissions import share_folder
   __all__ = ["get_drive_service", "get_docs_service", "create_research_packet", "share_folder"]
   ```

### Step 6: Update Imports (1h)

Update all files importing from old locations:

1. `backend/worker.py` - stages imports
2. `backend/pipeline/stages/*.py` - extraction/quality_gate imports
3. `backend/app/routes/*.py` - integration imports

Use grep to find all imports:
```bash
grep -r "from backend.pipeline.stages import" backend/
grep -r "from backend.pipeline.extraction import" backend/
grep -r "from backend.integrations.perplexity_client import" backend/
```

## Related Code Files

### Files to Create (New Modules)

| Module | Files |
|--------|-------|
| `stages/` | 9 files + `__init__.py` |
| `extraction/` | 5 files + `__init__.py` |
| `quality_gate/` | 6 files + `__init__.py` |
| `perplexity/` | 3 files + `__init__.py` |
| `google_drive/` | 3 files + `__init__.py` |

### Files to Delete (After Migration)

| File | Replacement |
|------|-------------|
| `backend/pipeline/stages.py` | `backend/pipeline/stages/` |
| `backend/pipeline/extraction.py` | `backend/pipeline/extraction/` |
| `backend/pipeline/quality_gate.py` | `backend/pipeline/quality_gate/` |
| `backend/integrations/perplexity_client.py` | `backend/integrations/perplexity/` |
| `backend/integrations/google_drive_docs.py` | `backend/integrations/google_drive/` |

## Todo List

### Stages Module
- [ ] Create `backend/pipeline/stages/` directory
- [ ] Create `stages/__init__.py` with all exports
- [ ] Create `stages/initialization.py`
- [ ] Create `stages/planning.py`
- [ ] Create `stages/discovery.py`
- [ ] Create `stages/youtube.py`
- [ ] Create `stages/web_capture.py`
- [ ] Create `stages/extraction_stages.py`
- [ ] Create `stages/analysis.py`
- [ ] Create `stages/output.py`
- [ ] Create `stages/helpers.py`
- [ ] Update worker.py imports
- [ ] Delete original `stages.py`

### Extraction Module
- [ ] Create `backend/pipeline/extraction/` directory
- [ ] Create `extraction/__init__.py`
- [ ] Create `extraction/chunking.py`
- [ ] Create `extraction/candidates.py`
- [ ] Create `extraction/canonicalization.py`
- [ ] Create `extraction/deduplication.py`
- [ ] Create `extraction/formatting.py`
- [ ] Create `extraction/core.py`
- [ ] Update imports in stages/extraction_stages.py
- [ ] Delete original `extraction.py`

### Quality Gate Module
- [ ] Create `backend/pipeline/quality_gate/` directory
- [ ] Create `quality_gate/__init__.py`
- [ ] Create `quality_gate/config.py`
- [ ] Create `quality_gate/models.py`
- [ ] Create `quality_gate/scoring.py`
- [ ] Create `quality_gate/filtering.py`
- [ ] Create `quality_gate/allocation.py`
- [ ] Create `quality_gate/core.py`
- [ ] Update imports in stages/discovery.py
- [ ] Delete original `quality_gate.py`

### Integration Modules
- [ ] Create `backend/integrations/perplexity/` module
- [ ] Create `backend/integrations/google_drive/` module
- [ ] Update all integration imports
- [ ] Delete original client files

### Verification
- [ ] Run pytest
- [ ] Verify all imports resolve
- [ ] Check file sizes (wc -l)

## Success Criteria

- [ ] All new files under 200 lines
- [ ] All imports resolve without errors
- [ ] pytest passes
- [ ] No functionality changes (pure refactor)
- [ ] Original large files deleted

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports | Medium | High | Careful dependency ordering in modules |
| Missing exports | Medium | Medium | Comprehensive `__all__` lists |
| Broken imports | Medium | High | Test after each module split |
| worker.py breaks | Low | Critical | Keep backup, test incrementally |

## Security Considerations

- No security changes (pure refactor)
- Maintain existing error sanitization
- Keep API key handling unchanged

## Next Steps

After completing this phase:
1. Add unit tests for split modules (Phase 4)
2. Consider async refactor for I/O bound operations (future)
3. Re-run code quality audit to verify improvements
