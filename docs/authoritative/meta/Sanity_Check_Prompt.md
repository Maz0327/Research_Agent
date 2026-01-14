# Pre-Implementation Sanity Check

**For:** Claude Code
**Purpose:** Verify all specification documents are consistent, complete, and ready for implementation
**Run this BEFORE starting Phase 0**

---

## Instructions

Do NOT write any code. This is a documentation audit only.

Read all specification documents and produce a **Sanity Check Report** that verifies everything is aligned. Flag any inconsistencies, missing references, or conflicts.

---

## Step 1: Locate and List All Spec Documents

Find and confirm these files exist in the repository:

### Root Level
- [ ] `CLAUDE.md`
- [ ] `PROGRESS.md`
- [ ] `DECISIONS.md`
- [ ] `IMPLEMENTATION_PLAN.md`
- [ ] `SPEC_MANIFEST.md`
- [ ] `Job_State_Machine.md`
- [ ] `API_Endpoint_Spec.md`
- [ ] `Celery_Task_Flow.md`

### docs/authoritative/
- [ ] `INDEX.md`
- [ ] `spec/RASS.md`
- [ ] `spec/Operational_Definitions.md`
- [ ] `spec/Document_Output_Format.md`
- [ ] `spec/Validation_and_Retry_Rules.md`

### docs/authoritative/prompts/
- [ ] `Gemini_Semantic_Extraction.md`
- [ ] `Semantic_Synthesis.md`
- [ ] `Gap_Identification.md`
- [ ] `Deep_Research_Booster.md`

### Other
- [ ] `PRODUCER_PACKET_SPEC.md` (location may vary)

**Output:** List of files found vs missing. If any critical files are missing, STOP and report.

---

## Step 2: Verify JobStatus/JobState Consistency

Check that the job status enum is IDENTICAL across all documents.

**Authoritative source:** `Job_State_Machine.md` Section 7

**Expected values (11 statuses):**
```
pending
acquiring_sources
extracting
validating
synthesizing
assembling
completed
completed_with_warnings
failed
running_booster
running_producer
```

**Check these files for consistency:**
1. `Job_State_Machine.md` — Should define authoritative enum
2. `CLAUDE_CODE_MEGA_PROMPT.md` — Should match (was `JobState`, should now be `JobStatus`)
3. `API_Endpoint_Spec.md` — Status values in responses should match
4. `Celery_Task_Flow.md` — Status updates should use these values
5. `IMPLEMENTATION_PLAN.md` — Any enum references should match

**Output:** 
- Confirm all match, OR
- List discrepancies with file name, line number, and incorrect value

---

## Step 3: Verify Analysis Mode Consistency

Check that the 6 analysis modes are IDENTICAL across all documents.

**Expected modes:**
```
transcript_grounded  → HIGH confidence, quotes allowed
caption_grounded     → MEDIUM confidence, quotes allowed
video_only           → LOW confidence, NO quotes
text_provided        → MEDIUM confidence, NO quotes
ocr_extracted        → MEDIUM confidence, NO quotes
article_fetched      → HIGH confidence, quotes allowed
```

**Check these files:**
1. `INDEX.md` — Six Analysis Modes table
2. `RASS.md` — Mode definitions
3. `Operational_Definitions.md` — Mode definitions
4. `CLAUDE.md` — Confidence Ceilings section
5. `CLAUDE_CODE_MEGA_PROMPT.md` — Analysis Modes table
6. `Gemini_Semantic_Extraction.md` — Mode-specific prompts
7. `Validation_and_Retry_Rules.md` — Mode-based validation

**Output:**
- Confirm all match, OR
- List discrepancies

---

## Step 4: Verify Document Model Consistency

Check that Doc 0/1/2/3 definitions are consistent.

**Expected:**
- Doc 0: Source Ledger (canonical data)
- Doc 1: Jump-Start Directions (research directions)
- Doc 2: Semantic Brief (analysis)
- Doc 3: Producer Packet (creative, GATED: 4+ sources, 1+ HIGH confidence)

**Check these files:**
1. `INDEX.md` — Canonical Document Model section
2. `RASS.md` — Document definitions
3. `Document_Output_Format.md` — JSON schemas
4. `CLAUDE.md` — Output Documents section
5. `CLAUDE_CODE_MEGA_PROMPT.md` — Output Documents section

**Output:**
- Confirm all match, OR
- List discrepancies

---

## Step 5: Verify Validation Rules Consistency

Check that V1-V10 validation checks are consistently defined.

**Expected checks:**
- V1: JSON Schema validation
- V2: Source ID consistency
- V3: Confidence ceiling enforcement
- V4: Quote verification (fuzzy match)
- V5: Quote permission by mode
- V6: Timestamp validation
- V7: Empty output check
- V8: Provenance chain validation
- V9: Cardinality check
- V10: Doc 3 gating validation

**Check these files:**
1. `Validation_and_Retry_Rules.md` — Authoritative source
2. `Celery_Task_Flow.md` — `validate_extraction` task implementation
3. `IMPLEMENTATION_PLAN.md` — Phase 4 validation references

**Output:**
- Confirm all match, OR
- List discrepancies

---

## Step 6: Verify Cross-References

Check that all document cross-references are valid.

### SPEC_MANIFEST.md references
Verify every document listed in SPEC_MANIFEST.md exists at the specified location.

### INDEX.md references
Verify every document listed in INDEX.md Authoritative Documents section exists.

### CLAUDE.md references
Verify every document in the Key Documents table exists.

### Phase-to-Spec mappings
Verify every spec referenced in IMPLEMENTATION_PLAN.md phase descriptions exists.

**Output:**
- List of broken references (file referenced but not found)
- List of orphaned specs (file exists but not referenced anywhere)

---

## Step 7: Verify API ↔ Celery ↔ State Machine Alignment

Check that the three orchestration specs are internally consistent.

### Job State Machine → API
- Every status in Job_State_Machine.md should appear in API_Endpoint_Spec.md responses
- Transition triggers should match API endpoints

### Job State Machine → Celery
- Every status transition should have a corresponding task or task step
- `update_job_status()` calls should use valid statuses

### API → Celery
- Every API endpoint that triggers async work should have a corresponding Celery task
- Task return values should match API response shapes

**Output:**
- Confirm alignment, OR
- List mismatches

---

## Step 8: Check for Deprecated/Conflicting Patterns

Look for any of these known issues:

1. **`state` vs `status`** — Should be `status` everywhere (not `state`)
2. **`JobState` vs `JobStatus`** — Should be `JobStatus` everywhere
3. **`INGESTING` status** — Should be `ACQUIRING_SOURCES`
4. **`COMPLETE` status** — Should be `COMPLETED`
5. **Missing `completed_with_warnings`** — Must exist for degradation
6. **`approximate_quotes`** — Should be `approximate_observations`

**Output:**
- List any occurrences of deprecated patterns with file and line number

---

## Step 9: Verify Prompt Components

Check that all LLM prompts include the 5 required components.

**Required components:**
1. Source Identity Lock block (visual box)
2. Confidence Ceiling declaration
3. Empty Output Permission
4. Layered Extraction instructions (for extraction prompts)
5. Output Schema

**Check these prompt files:**
1. `Gemini_Semantic_Extraction.md`
2. `Semantic_Synthesis.md`
3. `Gap_Identification.md`
4. `Deep_Research_Booster.md`
5. `PRODUCER_PACKET_SPEC.md`

**Output:**
- For each prompt file, confirm all 5 components present, OR
- List missing components

---

## Step 10: Final Readiness Assessment

Based on all checks above, provide:

### Readiness Status
```
[ ] READY — All checks passed, proceed to Phase 0
[ ] READY WITH WARNINGS — Minor issues noted, can proceed
[ ] NOT READY — Critical issues must be resolved first
```

### Critical Issues (if any)
List any issues that MUST be fixed before implementation.

### Warnings (if any)
List any issues that should be noted but don't block implementation.

### Recommendations
Any suggestions for improvement before starting.

---

## Output Format

```markdown
# Sanity Check Report

**Date:** [date]
**Status:** [READY | READY WITH WARNINGS | NOT READY]

## 1. Document Inventory
[List of found/missing files]

## 2. JobStatus Consistency
[Results]

## 3. Analysis Mode Consistency
[Results]

## 4. Document Model Consistency
[Results]

## 5. Validation Rules Consistency
[Results]

## 6. Cross-References
[Results]

## 7. Orchestration Alignment
[Results]

## 8. Deprecated Patterns
[Results]

## 9. Prompt Components
[Results]

## 10. Final Assessment

### Status: [READY | READY WITH WARNINGS | NOT READY]

### Critical Issues
[List or "None"]

### Warnings
[List or "None"]

### Recommendations
[List or "None"]

---

**Next Step:** [What to do next based on results]
```

---

## After Running This Check

**If READY:** Proceed to Phase 0 per IMPLEMENTATION_PLAN.md

**If READY WITH WARNINGS:** Note the warnings, proceed to Phase 0

**If NOT READY:** Report critical issues. Do NOT proceed until resolved.

---

**END OF SANITY CHECK PROMPT**
