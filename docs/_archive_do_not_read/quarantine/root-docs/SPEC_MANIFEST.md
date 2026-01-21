# Spec Document Manifest

> **Constitution:** `docs/authoritative/INDEX.md`
> This document is a **non-authoritative navigation aid**. If anything conflicts with INDEX.md, INDEX.md wins.

**Purpose:** Maps specification documents to implementation phases. Claude Code should reference these specs when building each phase.

---

## Document Inventory

### Implementation Documents (Project Root)

| Document | File Name | Purpose |
|----------|-----------|---------|
| Implementation Plan | `IMPLEMENTATION_PLAN.md` | Phase-by-phase build instructions |
| Claude Instructions | `CLAUDE.md` | Main rules for Claude Code |
| Progress Tracker | `PROGRESS.md` | Task tracking, updated each session |
| Decisions | `DECISIONS.md` | Architectural decision records |
| Spec Manifest | `SPEC_MANIFEST.md` | This file — maps specs to phases |

### Orchestration Documents (Project Root)

| Document | File Name | Purpose |
|----------|-----------|---------|
| Job State Machine | `Job_State_Machine.md` | Job lifecycle, status transitions, failure handling |
| API Endpoint Spec | `API_Endpoint_Spec.md` | REST API contract, request/response shapes |
| Celery Task Flow | `Celery_Task_Flow.md` | Task orchestration, retry logic, queue config |

### Authoritative Documents (docs/authoritative/)

| Document | File Name | Purpose |
|----------|-----------|---------|
| Repo Constitution | `INDEX.md` | Precedence rules, non-negotiables |
| System Spec | `spec/RASS.md` | Full system specification |
| Operational Definitions | `spec/Operational_Definitions.md` | Vocabulary authority |
| Document Output Format | `spec/Document_Output_Format.md` | Doc 0/1/2/3 schemas |
| Validation Rules | `spec/Validation_and_Retry_Rules.md` | Failure handling |

### Operational Reference (docs/)

| Document | File Name | Purpose |
|----------|-----------|---------|
| Operational Reference | `operational-reference.md` | Commands, costs, stack |

### Specification Documents (from previous sessions)

If these exist, place in `docs/authoritative/spec/`:

| Document | Purpose |
|----------|---------|
| `extended-specifications.md` | Detailed field definitions |
| `producer-packet-spec.md` | Doc 3 specification |
| `gaps-and-booster-spec.md` | Booster pipeline spec |
| `pipeline-hardening.md` | Validation/guardrails spec |
| `canonical-examples.md` | Example outputs |

---

## Phase-to-Spec Mapping

### Phase 0: Commit & Stabilize
**Specs Needed:** None (housekeeping only)

**Tasks:**
- Commit untracked files
- Archive dead code
- Deploy setup documents (including updated INDEX.md and RASS.md)

---

### Phase 0.5: Review Existing Code
**Specs Needed:**
- `INDEX.md` — Source isolation, 6 modes, prompt requirements
- `spec/RASS.md` — Full pipeline spec
- `extended-specifications.md` — Compare models against field definitions
- `canonical-examples.md` — Compare output format against examples
- `pipeline-hardening.md` — Check for required guardrails

**What to Compare:**

| File to Review | Compare Against |
|----------------|-----------------|
| `semantic_units.py` | RASS 4.3, INDEX modes table |
| `document_outputs.py` | RASS Section 3 |
| `source_identity.py` | RASS 4.2 |
| `semantic_extraction.py` | RASS 4.3, INDEX source isolation |
| `document_assembly.py` | RASS 4.6 |
| Prompt files | INDEX prompt requirements |

---

### Phase 1: Fix Blocking Issues
**Specs Needed:**
- `spec/RASS.md` — For PipelineContext fields
- `INDEX.md` — For 6 modes
- `Job_State_Machine.md` — For JobStatus enum values

**What to Reference:**
- JobStatus enum (11 values) from Job_State_Machine.md Section 7
- PipelineContext schema for new fields
- AnalysisMode enum values
- Artifacts model for Doc 0/1/2/3 fields

---

### Phase 2: Wire Semantic Pipeline
**Specs Needed:**
- `spec/RASS.md` Section 4 — Pipeline flow
- `INDEX.md` — Source isolation rule
- `Celery_Task_Flow.md` — Task definitions and orchestration
- `Job_State_Machine.md` — Status transitions

**What to Reference:**
- Pipeline stage order
- Stage input/output contracts
- Task signatures from Celery_Task_Flow.md
- Status update pattern from Job_State_Machine.md

---

### Phase 3: Add Analysis Modes
**Specs Needed:**
- `INDEX.md` — Six modes table
- `spec/RASS.md` 4.3, 8.4 — Mode-specific behavior
- `pipeline-hardening.md` — Confidence ceilings

**What to Reference:**
- 6 mode definitions
- Confidence ceiling per mode
- Quote rules per mode

---

### Phase 4: Add Validation
**Specs Needed:**
- `spec/RASS.md` Section 4.4 — Validation stage
- `pipeline-hardening.md` — Validation requirements
- `INDEX.md` — Prompt requirements

**What to Reference:**
- Validation checks list
- Quote verification algorithm
- Confidence enforcement rules

---

### Phase 5: Multi-Source Support
**Specs Needed:**
- `spec/RASS.md` Section 4.5 — Synthesis stage
- `INDEX.md` — Source isolation (still applies)

**What to Reference:**
- Source isolation during extraction
- Synthesis stage specification

---

### Phase 6: Evolving Jobs
**Specs Needed:**
- `spec/RASS.md` — Cross-reference pattern

**What to Reference:**
- Addendum document format
- Cross-reference output schema

---

### Phase 7: Booster Pipeline
**Specs Needed:**
- `spec/RASS.md` Section 4.7 — Booster spec
- `gaps-and-booster-spec.md` — Detailed booster spec

**What to Reference:**
- 4-stage booster pipeline
- Each stage's input/output
- Gap analysis format

---

### Phase 8: Producer Packet
**Specs Needed:**
- `spec/RASS.md` Section 3 (Doc 3)
- `producer-packet-spec.md` — Detailed spec
- `INDEX.md` — Gating requirements

**What to Reference:**
- 4-stage producer pipeline
- Gating requirements (4+ sources, 1 high-confidence)
- Creative interpretation guidelines

---

### Phase 8.5: API Endpoints
**Specs Needed:**
- `API_Endpoint_Spec.md` — All endpoint definitions

**What to Reference:**
- Route definitions (22 endpoints)
- Request/response shapes
- Error codes and HTTP status mapping
- Polling pattern for frontend

---

### Phase 9: Tests
**Specs Needed:**
- `canonical-examples.md` — Expected outputs for test assertions
- All specs — For comprehensive test coverage

**What to Reference:**
- Example inputs and expected outputs
- Edge cases mentioned in specs

---

### Phase 10: Documentation
**Specs Needed:**
- All specs — Ensure docs match implementation

---

## Quick Reference Table

| Phase | Primary Spec Document(s) |
|-------|-------------------------|
| 0 | None |
| 0.5 | INDEX.md, RASS.md, extended-specifications |
| 1 | RASS.md, INDEX.md, **Job_State_Machine.md** |
| 2 | RASS.md Section 4, INDEX.md, **Celery_Task_Flow.md**, **Job_State_Machine.md** |
| 3 | INDEX.md (modes), RASS.md 4.3/8.4 |
| 4 | RASS.md 4.4, pipeline-hardening |
| 5 | RASS.md 4.5, INDEX.md |
| 6 | RASS.md |
| 7 | RASS.md 4.7, **gaps-and-booster-spec** |
| 8 | RASS.md Section 3, **producer-packet-spec** |
| 9 | canonical-examples, all specs |
| 10 | All specs |

---

## File Organization

```
Research_Agent/
├── CLAUDE.md                          # Implementation instructions
├── PROGRESS.md                        # Task tracking
├── DECISIONS.md                       # Architecture decisions
├── IMPLEMENTATION_PLAN.md             # Phase details
├── SPEC_MANIFEST.md                   # This file
├── Job_State_Machine.md               # Job lifecycle specification
├── API_Endpoint_Spec.md               # REST API contract
├── Celery_Task_Flow.md                # Task orchestration
├── .claude/
│   ├── rules/
│   │   ├── implementation.md
│   │   └── architecture.md
│   ├── commands/
│   │   ├── checkpoint.md
│   │   ├── review-file.md
│   │   └── phase-status.md
│   └── workflows/
│       ├── start-session.md
│       └── end-session.md
└── docs/
    ├── operational-reference.md       # Commands, costs, stack
    └── authoritative/
        ├── INDEX.md                   # Repo constitution (UPDATED)
        ├── spec/
        │   ├── RASS.md               # System spec (UPDATED)
        │   ├── Operational_Definitions.md
        │   ├── Document_Output_Format.md
        │   └── Validation_and_Retry_Rules.md
        ├── prompts/
        │   └── ...
        └── examples/
            └── ...
```

---

## Usage Instructions

### For Claude Code

At the start of each phase:

1. Check this manifest for required spec documents
2. Read those spec documents before implementing
3. Use `/review-file` to compare code against specs
4. Reference INDEX.md for non-negotiable rules

### Example

Starting Phase 3 (Analysis Modes):

```
1. Read SPEC_MANIFEST.md → Phase 3 needs INDEX.md and RASS.md 4.3/8.4
2. Read INDEX.md Six Analysis Modes section
3. Read RASS.md Section 4.3 and 8.4
4. Implement mode selector per spec
5. Verify against INDEX.md mode table
6. Run /checkpoint
```

---

## Notes

- INDEX.md and RASS.md have been UPDATED with new rules
- Previous "Claude Code Mega Prompt" superseded by new CLAUDE.md
- If specs conflict with DECISIONS.md, DECISIONS.md wins
- When in doubt, check canonical-examples.md for expected output format
