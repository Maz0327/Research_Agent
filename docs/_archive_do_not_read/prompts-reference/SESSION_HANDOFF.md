# Session Handoff Document
## Research Agent System — Project Context Bundle

**Created:** January 13, 2026
**Purpose:** Restore full context in a new Claude chat session
**User:** Maz (YouTube documentary creator, ADHD, builds systems to reduce activation energy)

---

## 1. Project Overview

### What Is This?

The **Research Agent** is an "external research brain" for YouTube documentary production. It automates the mechanical labor of research while preserving human creative judgment.

### The Problem It Solves

Maz spends 10-15 hours on manual research per video. The system:
- Ingests YouTube videos (and other sources)
- Extracts semantic content (key points, claims, quotes, themes)
- Identifies gaps and research directions
- Produces structured deliverables that reduce activation energy

### Core Philosophy

- **Source Isolation:** Each source extracted in separate LLM call (prevents cross-contamination)
- **Confidence Ceilings:** Output confidence can't exceed source quality
- **Thin > Hallucinated:** Sparse accurate output beats dense fabricated output
- **Human Judgment Preserved:** System surfaces conflicts, doesn't resolve them

---

## 2. Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python) |
| Task Queue | Celery + Redis |
| Database | Supabase (PostgreSQL) |
| LLM | Gemini 2.5 Pro (via API) |
| Transcript | Supadata → Whisper fallback → YouTube captions fallback |
| Deployment | (TBD) |

---

## 3. Output Documents

The system produces 3 core documents (+ 1 optional):

| Doc | Name | Purpose |
|-----|------|---------|
| **Doc 0** | Source Ledger | Canonical data layer. Full text, metadata, indexes. No interpretation. |
| **Doc 1** | Jump-Start Directions | Research direction layer. Gaps, next steps, verification checklist. |
| **Doc 2** | Semantic Research Brief | Analysis layer. Themes, key points, tensions, confidence assessment. |
| **Doc 3** | Producer Packet | (Optional) Creative layer. Story angles, hooks, structure options. Gated: requires 4+ sources, 1+ high-confidence. |

---

## 4. Analysis Modes

| Mode | Source Type | Confidence Ceiling | Quotes Allowed |
|------|-------------|-------------------|----------------|
| `transcript_grounded` | YouTube w/ full transcript | HIGH | ✅ |
| `caption_grounded` | YouTube w/ auto-captions only | MEDIUM | ✅ |
| `video_only` | YouTube w/ no text | LOW | ❌ (observations only) |
| `text_provided` | User-pasted text | MEDIUM | ❌ |
| `ocr_extracted` | Screenshot | MEDIUM | ❌ |
| `article_fetched` | Article URL | HIGH | ✅ |

---

## 5. Key Architectural Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Source isolation (1 source per LLM call) | Prevents hallucinated cross-references |
| 2 | Confidence ceilings enforced programmatically | LLM can't claim HIGH on LOW-quality source |
| 3 | Quotes vs Observations based on mode | No fake quotes from video_only sources |
| 4 | Quote verification via fuzzy matching | Catches hallucinated quotes |
| 5 | Empty output explicitly permitted | Prevents padding with hallucinations |
| 6 | 5-component prompt structure | Source ID lock, ceiling, empty permission, layers, schema |
| 7 | Synthesis is the ONLY cross-source stage | Clean separation of concerns |
| 8 | Doc 3 gated (4+ sources, 1+ HIGH) | Creative output needs solid foundation |
| 9 | Addendum pattern for evolving jobs | New sources don't overwrite original analysis |
| 10 | Degraded output is valid output | System never hides failures |
| 11 | Booster is optional, augments Doc 1 only | Doesn't modify canonical data |
| 12 | Gemini for direct YouTube analysis | Solves timestamp extraction challenges |

---

## 6. Files Created (Complete Manifest)

### Root Project Files

| File | Purpose | Action |
|------|---------|--------|
| `CLAUDE.md` | Implementation rules for Claude Code | **Replace existing** |
| `PROGRESS.md` | Session-by-session task tracker | **New** |
| `DECISIONS.md` | 12 architectural decisions (final) | **New** |
| `IMPLEMENTATION_PLAN.md` | Phase-by-phase build instructions | **New** |
| `SPEC_MANIFEST.md` | Maps specs to implementation phases | **New** |
| `INITIALIZATION_PROMPT.md` | First message to give Claude Code | **Keep separate** |

### .claude/ Directory

| File | Location | Purpose |
|------|----------|---------|
| `implementation.md` | `.claude/rules/` | Code quality, testing, git rules |
| `architecture.md` | `.claude/rules/` | Pipeline rules, confidence rules |
| `checkpoint.md` | `.claude/commands/` | `/checkpoint` command |
| `review-file.md` | `.claude/commands/` | `/review-file` command |
| `phase-status.md` | `.claude/commands/` | `/phase-status` command |
| `start-session.md` | `.claude/workflows/` | Session start procedure |
| `end-session.md` | `.claude/workflows/` | Session end procedure |

### docs/ Directory

| File | Location | Purpose |
|------|----------|---------|
| `operational-reference.md` | `docs/` | Commands, API costs, stack reference |
| `INDEX.md` | `docs/authoritative/` | Repo constitution | **Replace existing** |
| `RASS.md` | `docs/authoritative/spec/` | System spec | **Replace existing** |

### Spec Files (NEW)

| File | Location | Purpose |
|------|----------|---------|
| `Operational_Definitions.md` | `docs/authoritative/spec/` | Vocabulary authority — all term definitions |
| `Document_Output_Format.md` | `docs/authoritative/spec/` | JSON schemas for Doc 0/1/2/3 |
| `Validation_and_Retry_Rules.md` | `docs/authoritative/spec/` | 10 validation checks, retry logic, failure handling |

### Example Files (NEW)

| File | Location | Purpose |
|------|----------|---------|
| `Example_Producer_Packet.md` | `docs/authoritative/examples/` | What Doc 3 should look like |
| `Example_Degraded_Output.md` | `docs/authoritative/examples/` | Output when sources fail/limited |
| `Example_Conflicting_Sources.md` | `docs/authoritative/examples/` | How to handle source disagreements |
| `Example_Thin_But_Acceptable.md` | `docs/authoritative/examples/` | Minimum valid output (1 source) |

### Prompt Contract Files (NEW)

| File | Location | Purpose |
|------|----------|---------|
| `Gemini_Semantic_Extraction.md` | `docs/authoritative/prompts/` | Core extraction prompt (5 components) |
| `Semantic_Synthesis.md` | `docs/authoritative/prompts/` | Cross-source synthesis prompt |
| `Gap_Identification.md` | `docs/authoritative/prompts/` | Deep gap analysis prompt |
| `Deep_Research_Booster.md` | `docs/authoritative/prompts/` | Optional 4-stage booster pipeline |

---

## 7. Project Structure (Target)

```
Research_Agent/
├── CLAUDE.md                           ← Replace
├── PROGRESS.md                         ← New
├── DECISIONS.md                        ← New
├── IMPLEMENTATION_PLAN.md              ← New
├── SPEC_MANIFEST.md                    ← New
├── .claude/
│   ├── rules/
│   │   ├── implementation.md           ← New/Replace
│   │   └── architecture.md             ← New/Replace
│   ├── commands/
│   │   ├── checkpoint.md               ← New/Replace
│   │   ├── review-file.md              ← New/Replace
│   │   └── phase-status.md             ← New/Replace
│   └── workflows/
│       ├── start-session.md            ← New/Replace
│       └── end-session.md              ← New/Replace
├── docs/
│   ├── operational-reference.md        ← New
│   └── authoritative/
│       ├── INDEX.md                    ← Replace
│       ├── spec/
│       │   ├── RASS.md                 ← Replace
│       │   ├── Operational_Definitions.md    ← New
│       │   ├── Document_Output_Format.md     ← New
│       │   └── Validation_and_Retry_Rules.md ← New
│       ├── examples/
│       │   ├── Example_Producer_Packet.md       ← New
│       │   ├── Example_Degraded_Output.md       ← New
│       │   ├── Example_Conflicting_Sources.md   ← New
│       │   └── Example_Thin_But_Acceptable.md   ← New
│       └── prompts/
│           ├── Gemini_Semantic_Extraction.md    ← New
│           ├── Semantic_Synthesis.md            ← New
│           ├── Gap_Identification.md            ← New
│           └── Deep_Research_Booster.md         ← New
└── backend/
    └── (existing code - to be refactored)
```

---

## 8. What's Done vs Not Done

### ✅ Complete

- [x] System specification (RASS.md updated)
- [x] Repository constitution (INDEX.md updated)
- [x] Operational definitions (all terms)
- [x] Document output schemas (Doc 0/1/2/3 JSON)
- [x] Validation rules (10 checks)
- [x] Retry logic
- [x] 4 canonical examples
- [x] 4 prompt contracts
- [x] Claude Code setup files (CLAUDE.md, rules, commands, workflows)
- [x] Implementation plan (phased)
- [x] Architectural decisions (12 decisions)

### ❓ Pending (Needs Your Input)

- [ ] Database schema documentation (you were going to run SQL query)
- [ ] Confirmation that all files deployed to repo

### ❌ Not Started (Claude Code Will Do)

- [ ] Actual code implementation
- [ ] Pydantic model updates
- [ ] Pipeline refactoring
- [ ] API endpoint updates
- [ ] Tests

---

## 9. Implementation Phases

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 0** | Commit untracked, deploy docs | Not started |
| **Phase 0.5** | Review existing code against specs | Not started |
| **Phase 1** | Source Identity + Analysis Modes | Not started |
| **Phase 2** | Extraction hardening | Not started |
| **Phase 3** | Validation layer | Not started |
| **Phase 4** | Synthesis stage | Not started |
| **Phase 5** | Assembly + Doc outputs | Not started |
| **Phase 6** | Booster pipeline | Not started |
| **Phase 7** | Doc 3 (Producer Packet) | Not started |

---

## 10. Open Items / Questions

1. **Database Schema:** Still need to document existing tables. Run the SQL query in Supabase and share results.

2. **Existing Code State:** Claude Code will audit in Phase 0.5, but knowing what's currently working helps.

3. **Deployment Target:** Where will this run? (Affects some implementation choices)

4. **API Authentication:** Current auth approach for the endpoints?

---

## 11. How to Continue in New Chat

### Option A: Give Context + Resume

Paste this entire document at the start of a new Claude chat, then say:

> "This is the context for my Research Agent project. I want to continue where we left off. [Your specific request]"

### Option B: Start Claude Code

1. Deploy all files to your repo (use the ZIP or copy manually)
2. Start a Claude Code session in the Research_Agent directory
3. Paste the contents of `INITIALIZATION_PROMPT.md` as first message
4. Claude Code will read PROGRESS.md and begin Phase 0

---

## 12. Initialization Prompt for Claude Code

```
I'm starting a new session on the Research Agent project.

Please:
1. Read PROGRESS.md to see current status
2. Read CLAUDE.md for implementation rules
3. Confirm which phase we're in
4. Tell me what the next task is

If PROGRESS.md shows no sessions yet, we're starting Phase 0.
```

---

## 13. Key Concepts Quick Reference

### Confidence Levels
- **HIGH:** Directly verifiable in source text
- **MEDIUM:** Reasonable interpretation, paraphrased
- **LOW:** Inferred or uncertain

### Source Isolation Rule
Each source extracted in separate LLM call. Sources never "see" each other until synthesis stage.

### Quote vs Observation
- **Quote:** Verbatim text (only for modes with text available)
- **Observation:** Semantic description (for video_only, text_provided, ocr_extracted)

### The 5 Prompt Components
1. Source Identity Lock (visual box)
2. Confidence Ceiling declaration
3. Empty Output Permission
4. Layered Extraction instructions
5. Output Schema

### Validation Priority
1. V1: JSON Schema
2. V2: Source ID consistency
3. V3: Confidence ceiling enforcement
4. V4: Quote verification
5. V5-V10: See Validation_and_Retry_Rules.md

---

## 14. Contact / Resources

- **Project:** Research Agent (internal name: RASS)
- **User:** Maz
- **Use Case:** YouTube mini-documentaries, investigative livestreams
- **Key Constraint:** ADHD-friendly outputs (reduce activation energy)

---

**END OF HANDOFF DOCUMENT**

*To resume: Paste this document into a new Claude chat and state your request.*
