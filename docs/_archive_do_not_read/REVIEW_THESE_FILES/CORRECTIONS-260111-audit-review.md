# Corrections to Initial Audit (2026-01-11)

> **Purpose**: This document records corrections to the initial hallucination protection audit after careful line-by-line review of the Context Handoff Document.

---

## Key Corrections

### 1. "All changes must be ADDITIVE" (Context Handoff Section 11)

**Initial audit error**: Suggested creating new files that *replace* existing structures.

**Correction**: The Context Handoff explicitly states:
> - All changes must be additive
> - No files deleted
> - No refactors unless explicitly requested

This means we should NOT rename `validation.py` to `claim_validation.py` or replace existing output structures.

---

### 2. Legacy outputs MUST be preserved (Context Handoff Section 9)

**Initial audit error**: Treated the new Doc 0/1/2 model as replacing ContentBlueprint, GapAnalysis, etc.

**Correction**: The Context Handoff explicitly states:
> Legacy outputs exist and MUST be preserved:
> - producer_packet
> - clips
> - quotes
>
> New semantic docs are **additive**, not replacements.

The 3-document model **coexists** with existing outputs.

---

### 3. Storage Model for Doc 0 (Context Handoff Section 3)

**Initial audit error**: Proposed storing full source text in Postgres via migration.

**Correction**: The Context Handoff explicitly states:
> - Full transcripts / full article text / full thread text (stored in **Supabase Storage**)
> - Skim summaries (short, factual, non-interpretive)

Full source text goes to **Supabase Storage** (media bucket), not Postgres. Postgres stores metadata and derived data only.

---

### 4. Doc 1 has mandatory "Top 3 next steps" (Context Handoff Section 3)

**Initial audit error**: Did not call out this as a hard requirement.

**Correction**: Doc 1 explicitly requires:
> - Top 3 next steps (mandatory)

This must be enforced in validation.

---

### 5. Semantic-First, Not Clip-First (Context Handoff Section 6)

**Initial audit error**: Did not properly prioritize semantic extraction over clips.

**Correction**: The Context Handoff explicitly states:
> Clips are handles to meaning — they are not the meaning itself.

The existing clips/quotes pipeline is **secondary** to semantic extraction. We add semantic on top, we don't delete clips.

---

### 6. Deep Research Booster is POST-JOB (Context Handoff Section 7)

**Initial audit error**: Did not make clear this is optional and late-stage.

**Correction**: The Context Handoff explicitly states:
> Deep research only runs AFTER Doc 0 / 1 / 2 exist

This is an optional late-stage addition using Context Bundle input, not part of core extraction.

---

## Revised Understanding: What We Actually Need

### Must Create (New Files - Additive)
1. `backend/models/semantic_units.py` - KeyPoint, Theme, Tension, Gap, SemanticExtractionResult
2. `backend/models/document_outputs.py` - SourceLedger, JumpStartDirections, SemanticBrief
3. `backend/pipeline/prompts/semantic_extraction_prompt.py` - Core Gemini prompt
4. `backend/pipeline/prompts/semantic_synthesis_prompt.py` - For Doc 2
5. `backend/pipeline/stages/semantic_extraction.py` - New stage
6. `backend/pipeline/stages/document_assembly.py` - Generates Doc 0/1/2
7. `backend/pipeline/semantic_validation.py` - 4-level validation
8. `backend/migrations/018_add_semantic_fields.sql` - New columns (metadata only)

### Must Extend (Existing Files - Additive Only)
1. `backend/models/source.py` - Add `confidence_ceiling` to SourceItem
2. `backend/models/job_record.py` - Add new artifact fields
3. `backend/integrations/gemini_client.py` - Wire analysis_mode, add validation
4. `backend/pipeline/extraction.py` - Set TranscriptProvenance during acquisition
5. `frontend/store/jobs.ts` - Add types for new structures

### Must NOT Do
- Don't rename/delete existing files
- Don't replace ContentBlueprint, GapAnalysis, ResearchStarter
- Don't modify existing dual_output.py structure
- Don't remove producer_packet/clips/quotes from Artifacts

---

**END OF CORRECTIONS DOCUMENT**
