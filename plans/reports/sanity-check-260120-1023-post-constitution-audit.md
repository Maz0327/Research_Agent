# POST-CONSTITUTION SANITY CHECK — READ-ONLY AUDIT

**Date:** 2026-01-20 10:23
**Authority Lock:** `docs/authoritative/INDEX.md`
**Mode:** READ-ONLY (no code changes)

---

## 1) EXECUTIVE SUMMARY

| Section | Status | Evidence |
|---------|--------|----------|
| A) Entrypoints + Reachability | ✅ PASS | All routes enumerated; deprecated return 410 |
| B) Forbidden Surfaces | ✅ PASS | Slack/Drive/Legacy unreachable |
| C) Storage Option B | ✅ PASS | Artifacts in JSON; Supabase Storage for files |
| D) Quote Policy | ✅ PASS | 6 modes enforced; video_only NO quotes |
| E) Transcript Chain | ✅ PASS | Supadata→Whisper→Captions→video_only |
| F) Failure Semantics | ✅ PASS | Graceful degradation; warnings accumulated |
| G) Doc Authority | ✅ PASS | INDEX.md sole authority; archives ignored |

**FINAL VERDICT: INTERNALLY CONSISTENT**

---

## 2) REACHABLE FLOWS

### API Routes (jobs_routes.py)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /jobs` | 410 GONE | Deprecated, line 118-135 |
| `POST /jobs/video-analysis` | ACTIVE | Semantic pipeline |
| `POST /jobs/text-input` | ACTIVE | Semantic pipeline |
| `POST /jobs/screenshot-input` | ACTIVE | Semantic pipeline |
| `POST /jobs/mixed-input` | ACTIVE | Semantic pipeline |
| `POST /jobs/{id}/sources` | ACTIVE | Add sources to evolving job |
| `POST /jobs/{id}/booster` | ACTIVE | Trigger booster |
| `POST /jobs/{id}/producer-packet` | ACTIVE | Trigger producer |
| `POST /jobs/preview` | 410 GONE | Deprecated, line 1283-1297 |
| `POST /jobs/{id}/select-interpretation` | 410 GONE | Deprecated, line 1601-1617 |
| `GET /jobs/{id}/manifest` | ACTIVE | Option B manifest |
| `GET /jobs/{id}/doc/{doc_id}` | ACTIVE | Lazy-load doc |
| `GET /jobs/{id}/attachments` | ACTIVE | List attachments |
| `GET /jobs/{id}/download.pdf` | ACTIVE | On-demand PDF |

### Celery Tasks (worker.py)

| Task | Line | Status |
|------|------|--------|
| `run_research_job` | 52 | ACTIVE - Mixed-input only (line 102-115 rejects legacy) |
| `run_transcript_job` | 381 | ACTIVE |
| `run_gemini_video_job` | 580 | ACTIVE |
| Task 4 | 842 | ACTIVE |
| Task 5 | 1220 | ACTIVE |
| Task 6 | 1392 | ACTIVE |

### Route → Task → Stages

```
POST /jobs/mixed-input
  → run_research_job (Celery)
  → _run_mixed_input_job()
    → source_identity
    → semantic_extraction (per source, isolated)
    → semantic_validation
    → gap_analysis
    → semantic_synthesis
    → document_assembly (Doc 0/1/2)
    → completion (manifest, storage)
```

---

## 3) FORBIDDEN SURFACES

### Slack (REMOVED)

| Item | Status | Evidence |
|------|--------|----------|
| `slack_routes.py` | ❌ DELETED | Not in `backend/app/routes/__init__.py` |
| `post_slack_message()` | STUB | `helpers.py:11-17` - logs only, no-op |
| `integrations/slack.py` | ❌ DELETED | Not in integrations/ |
| `slack_payload` param | DEPRECATED | worker.py:56 - ignored |
| Config slack fields | DEPRECATED | config.py:63-66 - not used |

**Verdict:** No Slack call sites are reachable.

### Google Drive (REMOVED)

| Item | Status | Evidence |
|------|--------|----------|
| `google_drive_docs.py` | ❌ DELETED | Not in integrations/ |
| `/export/google-docs` | 410 GONE | export_routes.py:311-329 |
| `validate-folder` | 410 GONE | settings_routes.py:59-63 |
| `oauth-status` | 410 GONE | settings_routes.py:72-76 |

**Verdict:** No Drive call sites are reachable.

### Legacy Pipeline Stages

| Item | Status | Evidence |
|------|--------|----------|
| `stage_2_research_mapping` | ❌ NOT FOUND | grep returned no matches |
| `stage_3_source_shortlist` | ❌ NOT FOUND | grep returned no matches |
| `stage_4_youtube*` | ❌ NOT FOUND | grep returned no matches |
| `stage_6_web_capture` | ❌ NOT FOUND | grep returned no matches |
| `parallel_executor` | ❌ NOT FOUND | grep returned no matches |
| `discovery.py` | ❌ NOT FOUND | Not in pipeline/stages/ |
| `planning.py` | ❌ NOT FOUND | Not in pipeline/stages/ |

**Verdict:** Legacy pipeline stages are deleted and unreachable.

---

## 4) OPTION B STORAGE

### Artifact Keys (jobs_routes.py:1008-1011, 1786-1788)

| Conceptual | Alias | Artifact Key |
|------------|-------|--------------|
| Doc 0 | "20" | `source_ledger` |
| Doc 1 | "21" | `jump_start` |
| Doc 2 | "22" | `semantic_brief` |
| Doc 3 | "3" | `producer_packet` |

### Storage Paths

- **Core docs:** `job.artifacts` JSON fields (lazy-loaded)
- **Attachments:** Supabase Storage `documents` bucket
- **Manifest:** Built in `initialization.py:173-252`
- **PDF:** Generated on-demand via `/jobs/{id}/download.pdf`

### Endpoints Wired

| Endpoint | Line | Purpose |
|----------|------|---------|
| `/jobs/{id}/manifest` | 1700 | Get artifact manifest |
| `/jobs/{id}/doc/{doc_id}` | 1744 | Lazy-load doc content |
| `/jobs/{id}/attachments` | 1823 | List attachment files |
| `/jobs/{id}/attachments/{filename}` | 1926 | Download attachment |
| `/jobs/{id}/download.pdf` | 1982 | On-demand PDF |

### Legacy Docs 00–11

- **grep 00_MASTER_INDEX:** No matches
- **Verdict:** No legacy numbered docs generated

---

## 5) POLICY ENFORCEMENT

### Quote Policy (3 layers)

**Layer 1 - Prompt Contracts:**
- `prompts/modes/video_only.py` - NO quotes instructions
- `semantic_extraction_prompt.py:281-320` - VIDEO_ONLY_INSTRUCTIONS forbids quotes

**Layer 2 - Schema/Validation:**
- `mode_selector.py:41-51` - `QUOTES_ALLOWED[VIDEO_ONLY] = False`
- `mode_selector.py:61-63` - `NO_QUOTE_MODES = {VIDEO_ONLY}`
- `semantic_validation.py:31-37` - Imports NO_QUOTE_MODES for enforcement

**Layer 3 - Post-Processing:**
- `llm_judge.py` - Quote verification / hallucination detection
- `quote_verification.py` - RAG grounding checks

### Mode → Confidence → Quote Policy

| Mode | Ceiling | Quotes | Flag | Enforcement File |
|------|---------|--------|------|------------------|
| transcript_grounded | HIGH | Yes | verbatim | mode_selector.py:26,43 |
| caption_grounded | MEDIUM | Yes | approximate | mode_selector.py:27,44,57 |
| video_only | LOW | **NO** | N/A | mode_selector.py:28,45,62 |
| text_provided | MEDIUM | Yes | unverified | mode_selector.py:31,48,55 |
| ocr_extracted | MEDIUM | Yes | unverified | mode_selector.py:32,49,56 |
| article_fetched | HIGH | Yes | verbatim | mode_selector.py:33,50 |

---

## 6) TRANSCRIPT CHAIN

**Locked Order (transcript_acquisition.py:4-8):**

```
1. Supadata → transcript_grounded (line 96)
2. Whisper → transcript_grounded (line 97)
3. YouTube captions → caption_grounded (line 77-78)
4. None → video_only (line 83-88, 334-343)
```

**Evidence:**
- `transcript_acquisition.py:266` - Documents the 4-tier chain
- `transcript_acquisition.py:334` - "Tier 4: All failed → video_only"
- `transcript_acquisition.py:343` - Returns `AnalysisMode.VIDEO_ONLY`

---

## 7) FAILURE SEMANTICS

### Graceful Degradation

| Mechanism | File | Evidence |
|-----------|------|----------|
| Stage runner with fallbacks | stage_runner.py:33-99 | `critical=False` default |
| Per-source error handling | semantic_extraction.py:579 | "Stage failures are handled gracefully" |
| Warnings accumulation | context.py | `ctx.add_warning()` throughout |
| Retry with bounded max | semantic_extraction.py:427,457 | `max_retries` with validation |

### Specific Rules

| Failure Type | Behavior | Evidence |
|--------------|----------|----------|
| Transcript failure | Degrades to video_only | transcript_acquisition.py:334-343 |
| Single source failure | Continues with others | semantic_extraction.py:579 |
| Gemini invalid JSON | Retry then degrade | semantic_extraction.py:457,481,493 |
| Non-critical stage | Continues with warning | stage_runner.py:90-99 |

---

## 8) DOC AUTHORITY CONFLICT MAP

### Sole Authority

- **Constitution:** `docs/authoritative/INDEX.md` ✅
- **CLAUDE.md:** Points to INDEX.md (line 9) ✅
- **`.claude/rules/authority.md`:** Points to INDEX.md (line 9) ✅

### Archive Folders (Excluded)

| Folder | Status | README |
|--------|--------|--------|
| `docs/_archive_do_not_read/` | ✅ EXISTS | Has LEGACY banner |
| `Archive Docs/` | ✅ EXISTS | Historical |
| `Active Docs/` | Copied to archive | Superseded |

### Ignore Rules

- **CLAUDE.md:13-16** - Lists ignore folders
- **authority.md:19-25** - Lists ignore folders
- **No .claudeignore file** - Relies on explicit rules

### Docs That Defer Correctly

| Doc | Deferral | Line |
|-----|----------|------|
| Index.md (root) | Points to INDEX.md | 5 |
| Context_Handoff.md | Points to INDEX.md | 7 |
| Database_Schema.md | Points to INDEX.md | 9 |
| SPEC_MANIFEST.md | Identifies INDEX.md as constitution | 31 |

---

## 9) FINAL VERDICT

**INTERNALLY CONSISTENT** ✅

All locked decisions from `docs/authoritative/INDEX.md` are:
1. Documented in the constitution
2. Enforced in code at appropriate surfaces
3. Not contradicted by other docs (archives properly excluded)

---

## 10) NO FIXES REQUIRED

All acceptance tests pass. No changes needed.

---

## Unresolved Questions

**None.** The system is internally consistent with the constitution.
