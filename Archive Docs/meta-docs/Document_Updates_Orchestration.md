# Document Updates for Orchestration Specs Integration

**Instructions:** For each file below, find the "FIND" section and replace it with the "REPLACE" section. Only these sections change; the rest of each file stays the same.

---

## 1. INDEX.md

### Update 1: Add Orchestration Documents section

**FIND** (in Authoritative Documents section, after "Prompt Contracts"):

```markdown
### Canonical Examples
- `examples/Example_Producer_Packet.md`
- `examples/Example_Content_Blueprint.md`
- `examples/Example_Degraded_Output.md`
- `examples/Example_Thin_But_Acceptable.md`
- `examples/Example_Conflicting_Sources.md`
```

**REPLACE WITH:**

```markdown
### Orchestration Specifications
- `Job_State_Machine.md` — Job lifecycle, status transitions, failure handling
- `API_Endpoint_Spec.md` — REST API contract, request/response shapes
- `Celery_Task_Flow.md` — Task orchestration, retry logic, queue configuration

### Canonical Examples
- `examples/Example_Producer_Packet.md`
- `examples/Example_Content_Blueprint.md`
- `examples/Example_Degraded_Output.md`
- `examples/Example_Thin_But_Acceptable.md`
- `examples/Example_Conflicting_Sources.md`
```

---

## 2. CLAUDE.md

### Update 1: Add orchestration docs to Key Documents table

**FIND:**

```markdown
| Document | Location | Purpose |
|----------|----------|---------|
| RASS.md | docs/authoritative/spec/ | System specification |
| INDEX.md | docs/authoritative/ | Repo constitution |
| PROGRESS.md | Project root | Current implementation status |
| DECISIONS.md | Project root | Architectural decisions |
| IMPLEMENTATION_PLAN.md | Project root | Phase-by-phase build plan |
| SPEC_MANIFEST.md | Project root | Maps specs to phases |
| operational-reference.md | docs/ | Commands, costs, stack |
```

**REPLACE WITH:**

```markdown
| Document | Location | Purpose |
|----------|----------|---------|
| RASS.md | docs/authoritative/spec/ | System specification |
| INDEX.md | docs/authoritative/ | Repo constitution |
| PROGRESS.md | Project root | Current implementation status |
| DECISIONS.md | Project root | Architectural decisions |
| IMPLEMENTATION_PLAN.md | Project root | Phase-by-phase build plan |
| SPEC_MANIFEST.md | Project root | Maps specs to phases |
| operational-reference.md | docs/ | Commands, costs, stack |
| Job_State_Machine.md | Project root | Job lifecycle, status transitions |
| API_Endpoint_Spec.md | Project root | REST API contract |
| Celery_Task_Flow.md | Project root | Task orchestration, retry logic |
```

---

## 3. SPEC_MANIFEST.md

### Update 1: Add Orchestration Documents to Document Inventory

**FIND** (after Implementation Documents table):

```markdown
### Authoritative Documents (docs/authoritative/)

| Document | File Name | Purpose |
|----------|-----------|---------|
| Repo Constitution | `INDEX.md` | Precedence rules, non-negotiables |
```

**REPLACE WITH:**

```markdown
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
```

### Update 2: Add orchestration specs to Phase 1

**FIND:**

```markdown
### Phase 1: Fix Blocking Issues
**Specs Needed:**
- `spec/RASS.md` — For PipelineContext fields
- `INDEX.md` — For 6 modes
```

**REPLACE WITH:**

```markdown
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
```

### Update 3: Add orchestration specs to Phase 2

**FIND:**

```markdown
### Phase 2: Wire Semantic Pipeline
**Specs Needed:**
- `spec/RASS.md` Section 4 — Pipeline flow
- `INDEX.md` — Source isolation rule

**What to Reference:**
- Pipeline stage order
- Stage input/output contracts
```

**REPLACE WITH:**

```markdown
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
```

### Update 4: Add API spec to relevant phase (add new section after Phase 8)

**FIND:**

```markdown
### Phase 9: Tests
**Specs Needed:**
- `canonical-examples.md` — Expected outputs for test assertions
- All specs — For comprehensive test coverage
```

**REPLACE WITH:**

```markdown
### Phase 8.5: API Endpoints
**Specs Needed:**
- `API_Endpoint_Spec.md` — All endpoint definitions

**What to Reference:**
- Route definitions (22 endpoints)
- Request/response shapes
- Error codes and HTTP status mapping
- Polling pattern for frontend

### Phase 9: Tests
**Specs Needed:**
- `canonical-examples.md` — Expected outputs for test assertions
- All specs — For comprehensive test coverage
```

### Update 5: Update Quick Reference Table

**FIND:**

```markdown
## Quick Reference Table

| Phase | Primary Spec Document(s) |
|-------|-------------------------|
| 0 | None |
| 0.5 | INDEX.md, RASS.md, extended-specifications |
| 1 | RASS.md, INDEX.md |
| 2 | RASS.md Section 4, INDEX.md |
```

**REPLACE WITH:**

```markdown
## Quick Reference Table

| Phase | Primary Spec Document(s) |
|-------|-------------------------|
| 0 | None |
| 0.5 | INDEX.md, RASS.md, extended-specifications |
| 1 | RASS.md, INDEX.md, **Job_State_Machine.md** |
| 2 | RASS.md Section 4, INDEX.md, **Celery_Task_Flow.md**, **Job_State_Machine.md** |
```

---

## 4. SESSION_HANDOFF.md

### Update 1: Add Orchestration Documents to Section 6

**FIND** (in Section 6, after "Prompt Contract Files"):

```markdown
### Prompt Contract Files (NEW)

| File | Location | Purpose |
|------|----------|---------|
| `Gemini_Semantic_Extraction.md` | `docs/authoritative/prompts/` | Core extraction prompt (5 components) |
| `Semantic_Synthesis.md` | `docs/authoritative/prompts/` | Cross-source synthesis prompt |
| `Gap_Identification.md` | `docs/authoritative/prompts/` | Deep gap analysis prompt |
| `Deep_Research_Booster.md` | `docs/authoritative/prompts/` | Optional 4-stage booster pipeline |
```

**REPLACE WITH:**

```markdown
### Prompt Contract Files (NEW)

| File | Location | Purpose |
|------|----------|---------|
| `Gemini_Semantic_Extraction.md` | `docs/authoritative/prompts/` | Core extraction prompt (5 components) |
| `Semantic_Synthesis.md` | `docs/authoritative/prompts/` | Cross-source synthesis prompt |
| `Gap_Identification.md` | `docs/authoritative/prompts/` | Deep gap analysis prompt |
| `Deep_Research_Booster.md` | `docs/authoritative/prompts/` | Optional 4-stage booster pipeline |

### Orchestration Documents (NEW)

| File | Location | Purpose |
|------|----------|---------|
| `Job_State_Machine.md` | Project root | Job lifecycle, status transitions, failure handling |
| `API_Endpoint_Spec.md` | Project root | REST API contract, 22 endpoints |
| `Celery_Task_Flow.md` | Project root | Task orchestration, 9 tasks, retry logic |
```

### Update 2: Add to Project Structure tree (Section 7)

**FIND:**

```markdown
Research_Agent/
├── CLAUDE.md                           ← Replace
├── PROGRESS.md                         ← New
├── DECISIONS.md                        ← New
├── IMPLEMENTATION_PLAN.md              ← New
├── SPEC_MANIFEST.md                    ← New
├── .claude/
```

**REPLACE WITH:**

```markdown
Research_Agent/
├── CLAUDE.md                           ← Replace
├── PROGRESS.md                         ← New
├── DECISIONS.md                        ← New
├── IMPLEMENTATION_PLAN.md              ← New
├── SPEC_MANIFEST.md                    ← New
├── Job_State_Machine.md                ← New
├── API_Endpoint_Spec.md                ← New
├── Celery_Task_Flow.md                 ← New
├── .claude/
```

---

## 5. IMPLEMENTATION_PLAN.md

### Update 1: Add JobStatus enum to Phase 1

**FIND:**

```markdown
### 1.2 Add Missing PipelineContext Fields

**File:** `backend/pipeline/context.py`

Add to PipelineContext dataclass:
```python
# Semantic pipeline fields
source_identity_packages: list = field(default_factory=list)
```

**REPLACE WITH:**

```markdown
### 1.2 Add JobStatus Enum

**Spec:** `Job_State_Machine.md` Section 7

**File:** `backend/models/job.py` (or appropriate location)

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    ACQUIRING_SOURCES = "acquiring_sources"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    SYNTHESIZING = "synthesizing"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    RUNNING_BOOSTER = "running_booster"
    RUNNING_PRODUCER = "running_producer"
```

### 1.3 Add Missing PipelineContext Fields

**File:** `backend/pipeline/context.py`

Add to PipelineContext dataclass:
```python
# Semantic pipeline fields
source_identity_packages: list = field(default_factory=list)
```

*(Note: Renumber subsequent sections 1.3 → 1.4, 1.4 → 1.5, etc.)*

### Update 2: Add orchestration spec references to Phase 2

**FIND:**

```markdown
## Phase 2: Wire Semantic Pipeline (Day 3)

**Goal:** Connect semantic stages into working task.
```

**REPLACE WITH:**

```markdown
## Phase 2: Wire Semantic Pipeline (Day 3)

**Goal:** Connect semantic stages into working task.

**Specs:**
- `Celery_Task_Flow.md` — Task definitions, signatures, orchestration
- `Job_State_Machine.md` — Status transitions during pipeline execution
```

---

## 6. CLAUDE_CODE_MEGA_PROMPT.md

### Update 1: Fix JobState enum to match Job_State_Machine.md

**FIND:**

```python
class JobState(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    SYNTHESIZING = "synthesizing"
    ASSEMBLING = "assembling"
    COMPLETE = "complete"
    FAILED = "failed"
```

**REPLACE WITH:**

```python
class JobStatus(str, Enum):
    """Job lifecycle states. See Job_State_Machine.md for transition rules."""
    PENDING = "pending"
    ACQUIRING_SOURCES = "acquiring_sources"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    SYNTHESIZING = "synthesizing"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    RUNNING_BOOSTER = "running_booster"
    RUNNING_PRODUCER = "running_producer"
```

### Update 2: Update Job model to use JobStatus

**FIND:**

```python
class Job(BaseModel):
    job_id: str
    state: JobState
    sources: List[SourceMetadata] = []
```

**REPLACE WITH:**

```python
class Job(BaseModel):
    job_id: str
    status: JobStatus  # Renamed from 'state' for consistency
    sources: List[SourceMetadata] = []
    warnings: List[dict] = []  # Added for degradation tracking
    warning_count: int = 0
```

### Update 3: Add reference to orchestration specs

**FIND** (near the top, after CRITICAL INSTRUCTIONS):

```markdown
---

# PROJECT OVERVIEW

## What We're Building
```

**REPLACE WITH:**

```markdown
---

# ORCHESTRATION SPECIFICATIONS

For job lifecycle, API contract, and task orchestration, refer to:
- `Job_State_Machine.md` — 11 job statuses, transition rules, failure handling
- `API_Endpoint_Spec.md` — 22 REST endpoints, request/response shapes
- `Celery_Task_Flow.md` — 9 Celery tasks, retry logic, queue configuration

These specs are authoritative for orchestration behavior.

---

# PROJECT OVERVIEW

## What We're Building
```

---

# Summary of All Changes

| File | Changes Made |
|------|--------------|
| INDEX.md | Added Orchestration Specifications section |
| CLAUDE.md | Added 3 orchestration docs to Key Documents table |
| SPEC_MANIFEST.md | Added Orchestration Documents section, updated Phase 1/2 specs, added Phase 8.5, updated Quick Reference |
| SESSION_HANDOFF.md | Added Orchestration Documents section, updated project tree |
| IMPLEMENTATION_PLAN.md | Added JobStatus enum to Phase 1, added spec references to Phase 2 |
| CLAUDE_CODE_MEGA_PROMPT.md | Fixed JobStatus enum (11 states), renamed state→status, added warnings field, added orchestration reference |

---

**END OF UPDATES**
