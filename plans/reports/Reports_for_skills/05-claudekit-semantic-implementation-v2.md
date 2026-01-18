# ClaudeKit Tools for Semantic-First Implementation (v2)

**Purpose:** Map ClaudeKit capabilities to the 7-phase semantic-first architecture implementation
**Created:** January 8, 2026
**Focus:** Prevent code drift, maintain focus, write clean organized code

---

## Executive Summary

The ClaudeKit research reveals **5 specific tools** that directly address the challenges of implementing the semantic-first architecture:

| Challenge | ClaudeKit Solution | Impact |
|-----------|-------------------|--------|
| 3-doc model complexity | Custom skills for each doc type | 100% pattern consistency |
| JSON schema gaps in specs | Pydantic + Structured Outputs | Zero schema violations |
| 7-phase implementation drift | Hooks + Plan Mode | Guaranteed quality gates |
| Context loss in long sessions | CLAUDE.md + Progressive Disclosure | Sharp focus throughout |
| Epistemic category enforcement | Semantic extraction skill | Correct grounding always |

---

## Part 1: Skills for Semantic-First Implementation

### Skill 1: Semantic Extraction (Doc 2)

**File:** `.claude/skills/semantic-extraction/SKILL.md`

**Purpose:** Enforce epistemic categories (Source Data → Descriptive Extraction → Semantic Interpretation → Speculation)

```yaml
---
name: semantic-extraction
description: |
  Extract semantic units (Key Points, Themes, Tensions, Gaps) from source content.
  MUST enforce 4-layer epistemic contract:
  1. Source Data (verbatim quotes)
  2. Descriptive Extraction (what source says)
  3. Semantic Interpretation (patterns across sources)
  4. Speculation (labeled hypotheses)
  Use when: Building Doc 2, extracting themes, identifying tensions.
allowed_tools: [read, write]
---

# Semantic Extraction

## Epistemic Categories (ENFORCE)

### Layer 1: Source Data
- Verbatim quotes with timestamps
- No paraphrasing
- Format: `QUOTE_{id}`, `CLIP_{id}`

### Layer 2: Descriptive Extraction
- What the source literally says
- No interpretation
- Grounded to Layer 1 citations

### Layer 3: Semantic Interpretation
- Patterns across multiple sources
- Themes, tensions, key points
- Must cite Layer 1/2 evidence

### Layer 4: Speculation
- MUST be labeled "speculative"
- Based on gaps, not invention
- Optional - prefer thin output over padding

## Output Schema

```python
class KeyPoint:
    id: str  # "KP_001"
    text: str
    based_on: List[str]  # ["QUOTE_003", "CLIP_007"]
    confidence: str  # "high" | "medium" | "speculative"

class Theme:
    id: str  # "THEME_001"
    description: str
    supporting_key_points: List[str]  # ["KP_001", "KP_004"]
```

## Anti-Patterns (NEVER DO)

- ❌ Invent facts not in sources
- ❌ Collapse epistemic layers
- ❌ Skip confidence labels
- ❌ Pad thin output with speculation
- ❌ Use "significant" without evidence
```

---

### Skill 2: Source Ledger Assembly (Doc 0)

**File:** `.claude/skills/source-ledger-assembly/SKILL.md`

**Purpose:** Build Doc 0 with full context preservation

```yaml
---
name: source-ledger-assembly
description: |
  Assemble Source Ledger (Doc 0) with full transcript storage and skimmable index.
  Contains: Source manifest, skim summaries, extracted indexes, blob references.
  NO INTERPRETATION in Doc 0 - raw facts only.
  Use when: Building Doc 0, ingesting sources, creating topic lock.
allowed_tools: [read, write, bash]
---

# Source Ledger Assembly (Doc 0)

## Components

### 1. Topic Lock
```python
class TopicLock:
    one_sentence: str
    in_scope: List[str]
    out_of_scope: List[str]
    key_entities: List[str]
```

### 2. Source Entry
```python
class SourceEntry:
    source_id: str  # "SRC_1"
    type: str  # "youtube" | "article" | "thread"
    title: str
    creator: str
    url: str
    blob_key: str  # Supabase Storage path
    skim_summary: str  # 2-3 sentences
    extracted_items: List[str]  # Quote/Clip IDs
```

### 3. Quote Index
- All quotes with `QUOTE_{id}` format
- Include: text, speaker, timestamp, source_id
- Verification flags: verified/probable/unverified

## Rules

1. NEVER interpret - only describe
2. ALWAYS store full transcript in blob storage
3. ALWAYS create skimmable index
4. NEVER collapse sources into single summary
```

---

### Skill 3: Jump-Start Consolidation (Doc 1)

**File:** `.claude/skills/jump-start-consolidation/SKILL.md`

**Purpose:** Build actionable research directions

```yaml
---
name: jump-start-consolidation
description: |
  Build Jump-Start document (Doc 1) with gaps, leads, verification checklist.
  Consolidates gap_analysis + research_starter into unified output.
  Focus: Actionable next steps, not conclusions.
  Use when: Building Doc 1, identifying gaps, suggesting research directions.
allowed_tools: [read, write]
---

# Jump-Start Consolidation (Doc 1)

## Required Sections

1. **Scope Lock** (from Doc 0)
2. **What We Know** (grounded summary)
3. **Gaps** (minimum 5)
4. **Research Directions** (minimum 10 leads)
5. **Top 3 Next Steps** (always visible)
6. **Verification Checklist** (minimum 5 items)

## Minimum Depth Requirements

- ≥5 gaps
- ≥10 leads
- ≥5 verification items
- ≥5 open questions

## Output Format

```python
class JumpStart:
    scope_lock: TopicLock
    corpus_summary: str  # What we know
    gaps: List[Gap]  # Minimum 5
    leads: List[Lead]  # Minimum 10
    verification_checklist: List[str]  # Minimum 5
    open_questions: List[str]  # Minimum 5
    top_3_next_steps: List[str]  # ALWAYS 3
```

## Rules

1. Top 3 next steps always at top (ADHD-first)
2. All gaps cite Doc 0 sources
3. Leads are actionable (not "research more")
4. No conclusions - directions only
```

---

### Skill 4: Validation Rules

**File:** `.claude/skills/semantic-validation/SKILL.md`

**Purpose:** Enforce hard/soft failure handling

```yaml
---
name: semantic-validation
description: |
  Validate semantic extraction output against spec rules.
  Hard failures: Invalid JSON, missing grounding.
  Soft failures: Thin output, low diversity.
  1 retry per stage, downgrade confidence instead of failing.
  Use when: Validating extraction output, handling failures.
allowed_tools: [read]
---

# Semantic Validation Rules

## Hard Failures (MUST FIX)

1. Invalid JSON schema
2. Key point without citation
3. Theme without supporting key points
4. Speculation without label
5. Empty required fields

## Soft Failures (DOWNGRADE)

1. Thin output (<8 key points)
2. Low theme diversity (<4 themes)
3. Few gaps (<5 gaps)
4. Missing perspectives

## Retry Policy

- 1 retry per stage maximum
- No retry chaining
- On soft failure: downgrade confidence, return partial
- On hard failure: retry once, then fail job

## Confidence Levels

| Level | Criteria |
|-------|----------|
| High | 3+ independent sources, verified quotes |
| Medium | 2 sources, probable quotes |
| Low | 1 source or unverified |
| Speculative | Inference, labeled |

## Job States

- `completed` - All docs pass
- `completed_with_warnings` - Soft failures present
- `failed` - Hard failure unrecoverable
```

---

## Part 2: Hooks for Implementation Quality

### Hook 1: Validate Pydantic Models

**File:** `.claude/hooks/claude.json` (add to existing)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "name": "validate-pydantic-models",
        "matcher": {
          "tool": ["Write", "Edit"],
          "path": "backend/models/*.py"
        },
        "command": "python -c \"from backend.models import *; print('Models valid')\" 2>&1 || echo 'PYDANTIC ERROR'"
      }
    ]
  }
}
```

### Hook 2: Check JSON Schema Generation

```json
{
  "name": "check-json-schema",
  "matcher": {
    "tool": ["Write", "Edit"],
    "path": "backend/models/semantic*.py"
  },
  "command": "python -c \"from backend.models.semantic_brief import SemanticBrief; print(SemanticBrief.model_json_schema())\""
}
```

### Hook 3: Run Pipeline Tests

```json
{
  "name": "run-pipeline-tests",
  "matcher": {
    "tool": "Bash",
    "command": "git commit"
  },
  "command": "pytest backend/tests/pipeline/ -v --tb=short"
}
```

---

## Part 3: CLAUDE.md Enhancements

### Add Semantic-First Section

```markdown
## Semantic-First Architecture (Jan 2026)

### 3-Document Model
| Doc | Purpose | Contains |
|-----|---------|----------|
| Doc 0 (Source Ledger) | Canonical context | Full transcripts, quotes, topic lock |
| Doc 1 (Jump-Start) | Research directions | Gaps, leads, verification, next steps |
| Doc 2 (Semantic Brief) | Understanding | Themes, key points, tensions |

### Epistemic Categories (MUST ENFORCE)
1. **Source Data** - Verbatim quotes, no paraphrase
2. **Descriptive Extraction** - What source says, grounded
3. **Semantic Interpretation** - Patterns, cite evidence
4. **Speculation** - Labeled, based on gaps

### ID Scheme
- Sources: `SRC_1`, `SRC_2`
- Quotes: `QUOTE_001`
- Clips: `CLIP_001`
- Key Points: `KP_001`
- Themes: `THEME_001`
- Gaps: `GAP_001`

### Minimum Depth Requirements
- Doc 0: ≥1 source, ≥6 quotes OR ≥10 clips
- Doc 1: ≥5 gaps, ≥10 leads, ≥5 verification items
- Doc 2: ≥8 key points, ≥4 themes, ≥5 gaps

### Skills to Activate
- `/semantic-extraction` - For Doc 2 work
- `/source-ledger-assembly` - For Doc 0 work
- `/jump-start-consolidation` - For Doc 1 work
- `/semantic-validation` - For validation
```

---

## Part 4: Structured Outputs for JSON Schemas

### Problem Solved

The spec review identified "No JSON schemas for docs" as a gap. Solution:

### Implementation

**Step 1:** Create Pydantic models (already planned in Phase 2-4)

```python
# backend/models/source_ledger.py
from pydantic import BaseModel

class TopicLock(BaseModel):
    one_sentence: str
    in_scope: list[str]
    out_of_scope: list[str]
    key_entities: list[str]

class SourceEntry(BaseModel):
    source_id: str
    type: str
    title: str
    blob_key: str
    skim_summary: str
    extracted_items: list[str]
```

**Step 2:** Auto-generate JSON schemas

```python
# Generate schema for documentation
schema = TopicLock.model_json_schema()
# Output to docs/schemas/topic-lock.json
```

**Step 3:** Use Structured Outputs for Gemini calls

```python
# In gemini_client.py - semantic extraction
response = model.generate_content(
    prompt,
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": SemanticBrief.model_json_schema()
    }
)
# Guaranteed schema compliance - no retry needed
```

---

## Part 5: Context Management Strategy

### For 7-Phase Implementation

**Phase 1-2 (Storage + Doc 0):**
- Single focus: blob storage + source ingestion
- Use `/clear` between phases
- Skill: `source-ledger-assembly`

**Phase 3-4 (Doc 1 + Doc 2):**
- Semantic extraction is complex
- Use extended thinking: "think harder"
- Skills: `jump-start-consolidation`, `semantic-extraction`

**Phase 5-6 (API + Booster):**
- Integration work
- Use existing `integrating-external-apis` skill
- Keep sessions short (30 min max)

**Phase 7 (Frontend):**
- UI work separate from backend
- Use `frontend-design` skill
- New context each component

### Session Strategy

```
Phase 1 → /clear → Phase 2 → /clear → Phase 3...
```

- One phase per session
- Todo tracking between sessions
- Plan file maintains continuity

---

## Part 6: Implementation Priority

### Immediate (Before Phase 1)

| Action | Time | Impact |
|--------|------|--------|
| Create 4 semantic skills | 2h | High |
| Add CLAUDE.md semantic section | 30m | High |
| Add Pydantic validation hook | 15m | Medium |

### During Implementation

| Phase | Skill to Use | Hook Active |
|-------|--------------|-------------|
| 1. Storage | - | Pydantic validation |
| 2. Doc 0 | `source-ledger-assembly` | JSON schema check |
| 3. Doc 1 | `jump-start-consolidation` | Pydantic validation |
| 4. Doc 2 | `semantic-extraction` | All hooks |
| 5. API | `integrating-external-apis` | Tests before commit |
| 6. Booster | `integrating-external-apis` | Tests before commit |
| 7. Frontend | `frontend-design` | Lint on save |

---

## Part 7: Files to Create

```
.claude/skills/
├── semantic-extraction/
│   └── SKILL.md           # Doc 2 extraction patterns
├── source-ledger-assembly/
│   └── SKILL.md           # Doc 0 assembly patterns
├── jump-start-consolidation/
│   └── SKILL.md           # Doc 1 consolidation patterns
└── semantic-validation/
    └── SKILL.md           # Validation rules

scripts/hooks/
├── validate-pydantic.sh   # Model validation
└── check-json-schema.sh   # Schema generation test
```

---

## Summary: How ClaudeKit Prevents Drift

| Drift Risk | Prevention |
|------------|------------|
| Forgetting epistemic categories | `semantic-extraction` skill enforces |
| Mixing interpretation in Doc 0 | `source-ledger-assembly` skill prohibits |
| Thin output | `semantic-validation` skill catches |
| Schema violations | Pydantic hooks + Structured Outputs |
| Context loss between phases | Session boundaries + plan file |
| Inconsistent ID scheme | CLAUDE.md reference + skill enforcement |

---

## Unresolved Questions

1. **Gemini Structured Outputs** - Does Gemini 2.5 support response_schema like Claude? Need to test.
2. **Hook Python wrappers** - Can validation hooks call Python directly? Testing needed.
3. **Skill auto-activation** - Will Claude activate semantic skills automatically? May need explicit invocation initially.

---

## Next Step

Create the 4 semantic skills and enhance CLAUDE.md **before** starting Phase 1 implementation. This foundation ensures clean, focused code throughout the 7-phase build.

**Time investment:** 2.5 hours
**Return:** Zero drift, consistent patterns, valid schemas
