# Specification Review Analysis Report

**Date**: January 8, 2026
**Reviewer**: Claude Code
**Documents Reviewed**: 9 files in "REVIEW THESE FILES" folder

---

## Executive Summary

These documents form a **comprehensive, well-structured specification** for the semantic-first Research Agent architecture. They align closely with the Blueprint Chat design decisions and provide sufficient detail for implementation.

**Overall Assessment**: **READY FOR IMPLEMENTATION** with minor gaps noted below.

| Document | Quality | Implementation-Ready | Notes |
|----------|---------|---------------------|-------|
| System Specification (RASS) | Excellent | Yes | Strong foundation |
| Operational Definitions | Excellent | Yes | Critical for consistency |
| Document Output Format | Good | Yes | Minor additions needed |
| Gemini Extraction Prompt | Good | Mostly | Needs output examples |
| Gap Identification Prompt | Good | Yes | Well-constrained |
| Semantic Synthesis Prompt | Good | Yes | Clear boundaries |
| Deep Research Booster | Good | Yes | Provider-agnostic |
| Validation & Retry Rules | Excellent | Yes | Thorough failure handling |
| Claude Build Instructions | Good | Mostly | Missing some file mappings |

---

## Document-by-Document Analysis

### 1. Research Agent System Specification (RASS)

**Strengths**:
- Clear articulation of system intent vs non-goals
- ADHD-first design explicitly codified
- Epistemic contract is well-defined (4 categories: Source Data, Descriptive Extraction, Semantic Interpretation, Speculation)
- Pipeline stages clearly ordered with failure behavior defined
- Storage split (Postgres vs Supabase Storage) matches our plan

**Weaknesses**:
- Section 5 (Storage) could be more specific about blob paths and naming conventions
- No explicit mention of transcript acquisition fallback chain (YouTube captions → Supadata → Whisper)

**Verdict**: Strong spec. Ready for implementation.

---

### 2. Operational Definitions

**Strengths**:
- Precise definitions prevent ambiguity during implementation
- Clear distinction between Quote, Claim, Key Point, Theme, Tension, Gap
- Confidence levels well-defined (High/Medium/Low with specific criteria)
- Context Bundle definition matches our plan exactly

**Weaknesses**:
- Missing definition for "Scope Lock" (referenced but not formally defined)
- Missing definition for "Skim Summary" (appears in Doc 0 format)

**Verdict**: Excellent. Critical reference document for developers.

---

### 3. Document Output Format Specification

**Strengths**:
- Clear markdown + JSON dual-format requirement
- Stable ID scheme (SRC_1, KP_3, THEME_2, GAP_1) enforced
- Skimmable-first design explicitly required
- Per-source section structure well-defined
- Failure/degradation display rules included

**Weaknesses**:
- Missing: JSON schema for Doc 0 (only markdown template shown)
- Missing: How to handle partial source ingestion failures in manifest
- Missing: Character/word limits for skim summaries

**Recommendation**: Add JSON schema equivalents for all 3 docs.

---

### 4. Gemini Semantic Extraction Prompt Pack

**Strengths**:
- Role definition is strict and correct ("semantic analyst, not summarizer")
- Good/bad examples provided for Key Points and Themes
- Retry prompt and failure recovery prompt included
- Absolute prohibitions clearly listed
- Success criteria defined for human evaluation

**Weaknesses**:
- Missing: Complete example output JSON (not just schema)
- Missing: How to handle multi-source extraction (batch vs individual)
- Schema uses inconsistent IDs (`KP_X` vs `key_point_id: "KP_X"`)

**Recommendation**: Add 1-2 full example outputs showing expected detail level.

---

### 5. Gap Identification Prompt

**Strengths**:
- Clear distinction between valid gaps and invalid gaps
- Input strictly defined as Context Bundle only (no raw text)
- Good/bad gap examples provided
- Neutral, actionable gaps required
- Graceful handling of "no gaps found" scenario

**Weaknesses**:
- Missing: Minimum/maximum gap count guidance
- Missing: How gaps relate to existing gap_analysis in current codebase

**Verdict**: Well-designed. Ready for implementation.

---

### 6. Semantic Synthesis Prompt

**Strengths**:
- Task ordering explicitly required (Core → Themes → Tensions → Gaps → Speculation)
- Input strictly defined (no raw source text)
- Speculation handling is explicit and constrained
- Confidence assessment included in output
- Good/bad examples for Semantic Core

**Weaknesses**:
- Missing: How to handle synthesis when only 1 source exists
- Missing: Theme minimum (currently ≥2 key points per theme, but what about total themes?)

**Verdict**: Strong prompt. Minor edge cases to address.

---

### 7. Deep Research Booster Prompt

**Strengths**:
- Provider-agnostic design (works with Gemini, Perplexity, OpenAI, Exa)
- Strict "directions only, no facts" constraint
- Context Bundle input prevents topic drift
- Four allowed output types clearly defined
- Failure does not block core docs

**Weaknesses**:
- Missing: Rate limiting/cost considerations
- Missing: How to merge booster output into Doc 1 (append vs replace sections?)
- Missing: Deduplication logic if booster returns similar gaps to existing

**Recommendation**: Add merge strategy for booster results.

---

### 8. Validation & Retry Rules Specification

**Strengths**:
- Four validation levels clearly separated (Schema, Grounding, Structural, Confidence)
- Hard vs soft failure distinction well-defined
- Retry policy bounded (1 retry per stage, no chaining)
- Job states match existing codebase patterns
- Partial success rules prevent cascade failures
- Booster-specific validation separate from core

**Weaknesses**:
- Missing: Specific thresholds for "thin output" (e.g., exactly how many KP per 30 min video?)
- Missing: Timeout handling for LLM calls

**Verdict**: Excellent failure handling spec. Production-ready.

---

### 9. Claude Code Build Instructions

**Strengths**:
- Global rules prevent common AI mistakes (no collapse, no invention)
- File structure provided with clear separation of concerns
- Pipeline stages match RASS exactly
- Explicit non-goals prevent scope creep
- Acceptance tests listed

**Weaknesses**:
- File paths don't match current repo structure (e.g., `workers/` vs `backend/worker.py`)
- Missing: Integration with existing `backend/pipeline/dual_output.py`
- Missing: How to handle existing `producer_packet`/`clips`/`quotes` artifacts
- Missing: Frontend instruction (even minimal API contract)

**Recommendation**: Update file paths to match existing repo, add backward compatibility notes.

---

## Cross-Document Consistency Check

| Concept | Consistent Across Docs? | Notes |
|---------|------------------------|-------|
| 3-Doc Model | ✅ Yes | Doc 0/1/2 consistent everywhere |
| ID Scheme | ✅ Yes | SRC_x, KP_x, GAP_x consistent |
| Epistemic Categories | ✅ Yes | 4 categories referenced consistently |
| Context Bundle | ✅ Yes | Same definition everywhere |
| Confidence Levels | ✅ Yes | High/Medium/Low with same criteria |
| Retry Policy | ✅ Yes | 1 retry per stage |
| Failure States | ✅ Yes | completed_with_warnings, failed |

---

## Gaps Between Specs and Current Codebase

| Spec Requirement | Current Codebase | Gap |
|------------------|------------------|-----|
| Full transcript storage | Not persisted | **Critical** - needs blob storage |
| Doc 0 Source Ledger | Doesn't exist | **Major** - new artifact type |
| Doc 1 Jump-Start | Partial (gap_analysis + research_starter) | **Medium** - consolidation needed |
| Doc 2 Semantic Brief | Doesn't exist | **Major** - replaces producer_packet focus |
| Context Bundle | Not implemented | **Medium** - new data structure |
| Semantic extraction | Clip/quote focused | **Major** - prompt rewrite needed |
| Validation rules | Basic schema validation only | **Medium** - needs grounding validation |

---

## Implementation Priority Recommendations

### Must Have (Blocking)
1. Blob storage for full transcripts (Phase 1 of our plan)
2. Source Ledger (Doc 0) assembly
3. Semantic extraction prompt (replace clip-first)
4. Grounding validation

### Should Have
5. Jump-Start consolidation
6. Semantic Brief (Doc 2) assembly
7. Gap identification integration
8. Confidence calibration logic

### Nice to Have
9. Deep Research Booster
10. Full acceptance test suite

---

## Unresolved Questions

1. **Backward Compatibility**: Should existing `producer_packet` be deprecated or kept alongside new docs?
2. **Transcript Fallback Chain**: Spec doesn't explicitly order YouTube captions → Supadata → Whisper. Should it?
3. **Multi-Video Handling**: How does semantic extraction work across multiple videos? Batch then merge, or per-video then synthesize?
4. **UI Integration**: No frontend spec provided. What API contract does frontend need?
5. **Cost Tracking**: Current system tracks costs per stage. How does new pipeline map?

---

## Final Verdict

**These specifications are production-quality** and represent a well-thought-out architectural redesign. The level of detail is appropriate for implementation, with clear boundaries between documents.

**Recommended Action**: Proceed with implementation following the 7-phase plan we created earlier. These specs provide the "what" - our plan provides the "how".

**Key Strength**: The epistemic contract (Section 2 of RASS) is the foundation. If developers internalize "Source Data → Descriptive Extraction → Semantic Interpretation → Speculation", the rest follows logically.

**Key Risk**: The semantic extraction prompt is the linchpin. If Gemini doesn't produce semantic-first output, the entire downstream pipeline degrades. Recommend early testing with real video content.

---

*Report generated by Claude Code analysis*
