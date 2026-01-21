# CONSTITUTION CONFLICT AUDIT

**Date:** 2026-01-19
**Mode:** READ-ONLY Analysis
**Auditor:** Claude Code

---

## 1. CANONICAL CONSTITUTION LOCATION

**Primary Constitution:** `docs/authoritative/INDEX.md`

This file explicitly declares:
> "This file is the single, repo-level pointer for what is **authoritative** vs **legacy** for the Research Agent."

**Supporting Authoritative Documents:**
- `docs/authoritative/spec/RASS.md` - System specification
- `docs/authoritative/spec/Operational_Definitions.md` - Vocabulary authority
- `docs/authoritative/spec/modes/*.md` - Mode specifications
- `docs/authoritative/prompts/*.md` - Prompt contracts

---

## 2. LOCKED CONTRACTS (from INDEX.md)

| Contract | Summary |
|----------|---------|
| **Precedence Rules** | Examples > Prose > Inferred behavior |
| **Vocabulary Authority** | `Operational_Definitions.md` is authoritative |
| **Source Isolation** | Each source in SEPARATE LLM call (NON-NEGOTIABLE) |
| **Six Analysis Modes** | transcript_grounded, caption_grounded, video_only, text_provided, ocr_extracted, article_fetched |
| **Confidence Ceilings** | HIGH, MEDIUM, LOW per mode |
| **Quote Rules** | Mode-specific (see conflict below) |
| **Three Core Docs** | Doc 0, Doc 1, Doc 2 + optional Doc 3 |
| **Transcript Chain** | Supadata → Whisper → captions → video_only |
| **Prompt Requirements** | 5 components required |

---

## 3. CONFLICT TABLE

| SEV | Conflict | Constitution Says | Conflicting Doc Says | Files |
|-----|----------|-------------------|---------------------|-------|
| **SEV-1** | text_provided quote policy | **NO** quotes | **YES** with warnings | INDEX.md:122-125 vs modes/text_provided.md:27-28,76-77 |
| **SEV-1** | ocr_extracted quote policy | **NO** quotes | **YES** with warnings | INDEX.md:122-125 vs modes/ocr_extracted.md:29,78-79 |
| **SEV-1** | modes/INDEX.md quote policy | N/A (conflict within authoritative/) | YES with warnings | modes/INDEX.md:17-24 |
| **SEV-1** | DECISIONS.md ADR-002 | **NO** quotes | Contradicted by spec files | DECISIONS.md:58-60 |
| **SEV-1** | .claude/rules/architecture.md | N/A | YES per "owner decision 2026-01-15" | .claude/rules/architecture.md:45-49 |
| **SEV-2** | docs/architecture.md endpoints | N/A | Lists deprecated endpoints as valid | docs/architecture.md:33-39 |
| **SEV-2** | docs/architecture.md legacy pipeline | N/A | Lists removed legacy stages | docs/architecture.md:65-80 |
| **SEV-3** | Document numbering | Doc 0/1/2/3 | Doc 20/21/22/3 in code | initialization.py, sanity report |

---

## 4. DETAILED CONFLICT ANALYSIS

### SEV-1: Quote Policy Contradiction (CRITICAL)

**The Issue:**
The main constitution `INDEX.md` (Line 122-125) states:

```
| Mode | Quotes Allowed |
| `text_provided` | **No** |
| `ocr_extracted` | **No** |
```

BUT the authoritative spec files within the SAME `docs/authoritative/` directory contradict this:

- `spec/modes/text_provided.md` (Line 27-28): `Quotes Allowed: **YES — with warnings**`
- `spec/modes/ocr_extracted.md` (Line 29): `Quotes Allowed: **YES — with warnings**`
- `spec/modes/INDEX.md` (Line 22-23): `text_provided | YES (with warnings)`, `ocr_extracted | YES (with warnings)`

**Root Cause:**
The `.claude/rules/architecture.md` file (Line 49) claims:
> "\*Owner Decision (2026-01-15): TEXT_PROVIDED and OCR_EXTRACTED allow quotes but marked as unverified."

This owner decision was applied to the mode spec files BUT NOT to:
1. `docs/authoritative/INDEX.md` (the constitution)
2. `DECISIONS.md` ADR-002

**Violation of INDEX.md's Own Rules:**
The constitution states:
> "Change Policy (Drift Prevention): 1. Update **canonical examples first** 2. Then update prose specs 3. Then update code"

If the decision changed, INDEX.md should have been updated FIRST.

---

### SEV-2: docs/architecture.md Stale Information

**The Issue:**
`docs/architecture.md` references:
- `POST /jobs` (Line 34) - Now returns 410 Gone
- `POST /jobs/preview` (Line 35) - Now returns 410 Gone
- `POST /jobs/{id}/select-interpretation` (Line 39) - Now returns 410 Gone
- Legacy pipeline stages including Google Drive upload (Line 65-80) - Removed

**Impact:** Developers reading this file will have incorrect understanding of the API.

---

### SEV-3: Document Numbering Drift

**The Issue:**
- Constitution and specs say: Doc 0, Doc 1, Doc 2, Doc 3
- Code (`initialization.py`, `job_record.py`) uses: doc_0_path, doc_1_path, doc_2_path, doc_3_path
- Sanity report and artifact_manifest use: 20, 21, 22 for core docs

**Evidence from initialization.py (Line 211-224):**
```python
"core_docs": {
    "20": {"present": ..., "title": "Source Ledger"},
    "21": {"present": ..., "title": "Jump Start"},
    "22": {"present": ..., "title": "Semantic Brief"},
}
```

---

## 5. SUPERSESSION PLAN

### Phase A: Resolve SEV-1 Quote Policy (Requires Owner Decision)

**Option 1: Constitution Wins (Revert to NO quotes)**
- Update `spec/modes/text_provided.md` to disallow quotes
- Update `spec/modes/ocr_extracted.md` to disallow quotes
- Update `spec/modes/INDEX.md` to show NO quotes
- Remove owner decision note from `.claude/rules/architecture.md`
- Update code to match

**Option 2: Owner Decision Wins (Update Constitution)**
- Update `docs/authoritative/INDEX.md` Line 122-125 to show YES with warnings
- Update `DECISIONS.md` ADR-002 to reflect change
- Add ADR-013 documenting the policy change

**RECOMMENDATION:** Option 2 (Update Constitution)
- The spec files already have detailed implementation
- The owner decision is documented
- Constitution just needs to be synchronized

---

### Phase B: Update docs/architecture.md (SEV-2)

1. Remove deprecated endpoint listings (POST /jobs, POST /jobs/preview, select-interpretation)
2. Remove legacy pipeline stages section (65-80)
3. Add reference to current semantic pipeline
4. Add reference to deprecated_endpoints.py (when created)

---

### Phase C: Document Numbering Standardization (SEV-3)

**Decision Required:**
- Use Doc 0/1/2/3 (spec naming) OR
- Use Doc 20/21/22/3 (code naming)

**RECOMMENDATION:** Keep both as aliases
- Spec refers to concept: Doc 0 = Source Ledger
- Code uses numbers for manifest: "20" = Source Ledger
- Add mapping table to spec

---

## 6. FILES REQUIRING UPDATE

| File | Action | Priority |
|------|--------|----------|
| `docs/authoritative/INDEX.md` | Update quote policy for text_provided, ocr_extracted | SEV-1 |
| `DECISIONS.md` | Update ADR-002 OR add ADR-013 | SEV-1 |
| `docs/architecture.md` | Remove deprecated endpoints, update pipeline info | SEV-2 |
| `.claude/rules/architecture.md` | Already correct (has owner decision) | None |
| `docs/authoritative/spec/Document_Output_Format.md` | Add Doc numbering mapping | SEV-3 |

---

## 7. DOCUMENTS CONFIRMED ALIGNED

| Document | Status |
|----------|--------|
| `CLAUDE.md` | ✅ Aligned (silent on quotes, lists modes correctly) |
| `.claude/rules/implementation.md` | ✅ Aligned |
| `.claude/rules/testing.md` | ✅ Aligned |
| `docs/authoritative/spec/RASS.md` | ⚠️ Need to verify quote policy |
| `docs/authoritative/prompts/*.md` | ⚠️ Need verification |

---

## 8. IMMEDIATE ACTION REQUIRED

**Before any further development:**

1. **OWNER DECISION:** Which quote policy is correct?
   - A) NO quotes for text_provided/ocr_extracted (per INDEX.md constitution)
   - B) YES with warnings (per mode spec files and owner decision note)

2. **Once decided:** Update INDEX.md to match decision

3. **Then:** Update or remove conflicting documents

---

## 9. SUMMARY

| Severity | Count | Description |
|----------|-------|-------------|
| SEV-1 | 5 | Quote policy contradictions within authoritative docs |
| SEV-2 | 2 | Stale API/pipeline documentation |
| SEV-3 | 1 | Document numbering drift |

**The constitution (INDEX.md) is OUT OF SYNC with its own spec files.**

This must be resolved before the documentation can be considered complete.

---

**END OF AUDIT**
