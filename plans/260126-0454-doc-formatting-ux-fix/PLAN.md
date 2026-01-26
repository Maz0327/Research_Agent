# Implementation Plan: Document Formatting UX Fix

**Created:** 2026-01-26
**Branch:** `claude/investigate-doc-display-aa05B`
**Status:** Ready for Implementation

---

## Objective

Fix document output formatting to improve user experience by:
1. Adding `label` field to Tension and Gap models
2. Transforming IDs to friendly labels in backend (stored in markdown)
3. Adding meaningful titles to all section headers
4. Improving visual hierarchy and consistency

---

## Decisions Made

| Question | Decision |
|----------|----------|
| Labels vs. Truncated Descriptions | Add `label` field to models |
| Frontend vs. Backend Transform | Backend (stored as "Source 1") |
| Implementation Approach | Phased rollout |

---

## Phases

### Phase 1: Model Updates
Add `label` field to Tension and Gap models.

### Phase 2: Markdown Formatting
Update `to_markdown()` methods to use labels and transform IDs.

### Phase 3: Extraction Prompts
Update LLM prompts to generate labels for Tension and Gap.

### Phase 4: Validation & Testing
Update validation rules and add tests.

---

## Phase 1: Model Updates

### Task 1.1: Add `label` to Tension Model

**File:** `backend/models/semantic_units.py`

```python
@dataclass
class Tension:
    tension_id: str
    label: str              # NEW: Short title (e.g., "Timeline Conflict")
    description: str
    involved_key_points: list[str] = field(default_factory=list)
    # ... rest unchanged
```

**Changes:**
- Add `label: str` field after `tension_id`
- Update `to_dict()` to include label
- Default to empty string for backwards compatibility

### Task 1.2: Add `label` to Gap Model

**File:** `backend/models/semantic_units.py`

```python
@dataclass
class Gap:
    gap_id: str
    label: str              # NEW: Short title (e.g., "Missing Primary Docs")
    description: str
    why_expected: str
    # ... rest unchanged
```

**Changes:**
- Add `label: str` field after `gap_id`
- Update `to_dict()` to include label
- Default to empty string for backwards compatibility

### Task 1.3: Add ID Formatting Helper

**File:** `backend/utils/markdown_helpers.py`

```python
def format_internal_id(id_str: str) -> str:
    """
    Convert internal ID to user-friendly label.

    Examples:
        SRC_1 → "Source 1"
        KP_3 → "Key Point 3"
        THEME_2 → "Theme 2"
        TEN_1 → "Tension 1"
        GAP_4 → "Open Question 4"
    """
    import re
    mapping = {
        "SRC": "Source",
        "KP": "Key Point",
        "CLM": "Claim",
        "QT": "Quote",
        "OBS": "Observation",
        "THEME": "Theme",
        "TEN": "Tension",
        "GAP": "Open Question",
        "REF": "Reference",
    }
    match = re.match(r"^([A-Z]+)_(\d+)$", id_str)
    if match:
        prefix, num = match.groups()
        label = mapping.get(prefix, prefix)
        return f"{label} {num}"
    return id_str


def format_id_list(ids: list[str], separator: str = ", ") -> str:
    """Format a list of IDs to user-friendly labels."""
    return separator.join(format_internal_id(id) for id in ids)
```

---

## Phase 2: Markdown Formatting

### Task 2.1: Fix Tension Headers in Doc 2

**File:** `backend/models/document_outputs.py`

**Location:** `SemanticBrief.to_markdown()` (~line 904-918)

```python
# BEFORE
f"### {t.tension_id}",
f"**Description:** {t.description}",
f"**Involved:** `{', '.join(t.involved_key_points)}`",

# AFTER
from backend.utils.markdown_helpers import format_internal_id, format_id_list

title = t.label if t.label else t.description[:50] + "..." if len(t.description) > 50 else t.description
lines.extend([
    f"### {format_internal_id(t.tension_id)}: {title}",
    "",
    f"> {t.description}",
    "",
    f"**Involved:** {format_id_list(t.involved_key_points)}",
    "",
])
```

### Task 2.2: Fix Gap Headers in Doc 2

**File:** `backend/models/document_outputs.py`

**Location:** `SemanticBrief.to_markdown()` (~line 922-937)

```python
# BEFORE
f"### {g.gap_id}",
f"**Why it matters:** {g.why_expected}",

# AFTER
title = g.label if g.label else g.description[:50] + "..." if len(g.description) > 50 else g.description
lines.extend([
    f"### {format_internal_id(g.gap_id)}: {title}",
    "",
    f"> {g.description}",
    "",
    f"**Why it matters:** {g.why_expected}",
    "",
])
```

### Task 2.3: Fix ID References (Remove Backticks)

**File:** `backend/models/document_outputs.py`

Multiple locations - search for backtick patterns:

```python
# BEFORE (multiple locations)
f"**Related Key Points:** `{', '.join(theme.related_key_points)}`"
f"**Involved:** `{', '.join(t.involved_key_points)}`"

# AFTER
f"**Related Key Points:** {format_id_list(theme.related_key_points)}"
f"**Involved:** {format_id_list(t.involved_key_points)}"
```

### Task 2.4: Fix Key Point References in Doc 1

**File:** `backend/models/document_outputs.py`

**Location:** `JumpStartDirections.to_markdown()` (~line 646-665)

```python
# BEFORE
lines.append(f"- **{kp.key_point_id}:** {kp.statement}")
lines.append(f"- **{t.tension_id}:** {t.description}")

# AFTER
lines.append(f"- **{format_internal_id(kp.key_point_id)}:** {kp.statement}")
title = t.label if t.label else t.description[:50] + "..."
lines.append(f"- **{format_internal_id(t.tension_id)}:** {title}")
```

### Task 2.5: Add Visual Dividers

Add horizontal rules between major items:

```python
# In SemanticBrief.to_markdown() - themes section
for i, theme in enumerate(self.themes):
    lines.extend([...theme content...])
    if i < len(self.themes) - 1:
        lines.append("")
        lines.append("---")
        lines.append("")
```

---

## Phase 3: Extraction Prompts

### Task 3.1: Update Tension Schema in Extraction Prompts

**Files to update:**
- `backend/pipeline/prompts/semantic_extraction_prompt.py`
- `backend/pipeline/prompts/semantic_synthesis_prompt.py`

Add `label` field to Tension schema:

```python
"tensions": [
    {
        "tension_id": "TEN_1",
        "label": "string - Short descriptive title (3-6 words, e.g., 'Timeline Conflict Between Sources')",
        "description": "string - Full description of the tension",
        "involved_key_points": ["KP_1", "KP_2"]
    }
]
```

### Task 3.2: Update Gap Schema in Extraction Prompts

**Files to update:**
- `backend/pipeline/prompts/gap_analysis_prompt.py`
- `backend/pipeline/prompts/semantic_synthesis_prompt.py`

Add `label` field to Gap schema:

```python
"gaps": [
    {
        "gap_id": "GAP_1",
        "label": "string - Short descriptive title (3-6 words, e.g., 'Missing Primary Documentation')",
        "description": "string - What information is missing",
        "why_expected": "string - Why this information would be expected",
        "suggested_research_direction": "string | null"
    }
]
```

### Task 3.3: Add Label Generation Instructions

Add to extraction prompts:

```
LABEL REQUIREMENTS:
- Each Tension must have a label: short title (3-6 words) describing the conflict
- Each Gap must have a label: short title (3-6 words) describing what's missing
- Labels should be scannable headlines, not full sentences
- Examples:
  - Tension label: "Timeline Conflict", "Funding Amount Dispute", "Contradictory Statements"
  - Gap label: "Missing Primary Docs", "No Expert Perspective", "Unverified Financial Data"
```

---

## Phase 4: Validation & Testing

### Task 4.1: Update Validation Rules

**File:** `backend/pipeline/validation/semantic_validator.py` (or equivalent)

Add validation for label field:

```python
def validate_tension(tension: dict) -> list[str]:
    warnings = []
    if not tension.get("label"):
        warnings.append(f"Tension {tension['tension_id']} missing label")
    elif len(tension["label"]) > 60:
        warnings.append(f"Tension {tension['tension_id']} label too long (max 60 chars)")
    return warnings

def validate_gap(gap: dict) -> list[str]:
    warnings = []
    if not gap.get("label"):
        warnings.append(f"Gap {gap['gap_id']} missing label")
    elif len(gap["label"]) > 60:
        warnings.append(f"Gap {gap['gap_id']} label too long (max 60 chars)")
    return warnings
```

### Task 4.2: Add Unit Tests

**File:** `backend/tests/test_document_outputs.py`

```python
def test_tension_to_markdown_has_label():
    """Tension markdown should include label in header."""
    tension = Tension(
        tension_id="TEN_1",
        label="Timeline Conflict",
        description="Two sources disagree on the date"
    )
    md = tension.to_markdown()
    assert "### Tension 1: Timeline Conflict" in md

def test_gap_to_markdown_has_label():
    """Gap markdown should include label in header."""
    gap = Gap(
        gap_id="GAP_1",
        label="Missing Primary Docs",
        description="No court filings found",
        why_expected="Legal dispute mentioned by sources"
    )
    md = gap.to_markdown()
    assert "### Open Question 1: Missing Primary Docs" in md

def test_format_internal_id():
    """ID formatting should convert to friendly labels."""
    from backend.utils.markdown_helpers import format_internal_id
    assert format_internal_id("SRC_1") == "Source 1"
    assert format_internal_id("KP_12") == "Key Point 12"
    assert format_internal_id("TEN_3") == "Tension 3"
    assert format_internal_id("GAP_5") == "Open Question 5"
```

### Task 4.3: Add Integration Test

**File:** `backend/tests/test_semantic_pipeline_integration.py`

```python
def test_document_output_has_friendly_ids():
    """Generated documents should use friendly ID labels."""
    # Run pipeline with test data
    result = run_test_pipeline()

    # Check Doc 2 markdown
    doc2_md = result["semantic_brief_md"]

    # Should NOT contain raw IDs
    assert "TEN_1" not in doc2_md or "Tension 1" in doc2_md
    assert "GAP_1" not in doc2_md or "Open Question 1" in doc2_md
    assert "`KP_" not in doc2_md  # No backtick-wrapped IDs
```

---

## Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `backend/models/semantic_units.py` | 1 | Add `label` to Tension, Gap |
| `backend/utils/markdown_helpers.py` | 1 | Add `format_internal_id()`, `format_id_list()` |
| `backend/models/document_outputs.py` | 2 | Update `to_markdown()` methods |
| `backend/pipeline/prompts/semantic_extraction_prompt.py` | 3 | Add label to schemas |
| `backend/pipeline/prompts/semantic_synthesis_prompt.py` | 3 | Add label to schemas |
| `backend/pipeline/prompts/gap_analysis_prompt.py` | 3 | Add label to Gap schema |
| `backend/tests/test_document_outputs.py` | 4 | Add unit tests |
| `backend/tests/test_semantic_pipeline_integration.py` | 4 | Add integration test |

---

## Rollout Checklist

### Pre-Implementation
- [ ] Read current files to understand exact structure
- [ ] Verify no breaking changes to existing data

### Phase 1
- [ ] Add `label` field to Tension model
- [ ] Add `label` field to Gap model
- [ ] Add helper functions to markdown_helpers.py
- [ ] Run existing tests (should pass with empty labels)

### Phase 2
- [ ] Update SemanticBrief.to_markdown() - Tension section
- [ ] Update SemanticBrief.to_markdown() - Gap section
- [ ] Update JumpStartDirections.to_markdown()
- [ ] Remove backticks from ID reference lists
- [ ] Add visual dividers between items

### Phase 3
- [ ] Update semantic_extraction_prompt.py
- [ ] Update semantic_synthesis_prompt.py
- [ ] Update gap_analysis_prompt.py
- [ ] Test with sample extraction

### Phase 4
- [ ] Add unit tests for new functionality
- [ ] Add integration test
- [ ] Run full test suite
- [ ] Manual verification with real job

### Post-Implementation
- [ ] Update PROGRESS.md
- [ ] Commit with descriptive message
- [ ] Push to branch

---

## Success Criteria

1. **Headers have meaningful titles:**
   - `### Tension 1: Timeline Conflict Between Sources` ✅
   - `### Open Question 1: Missing Primary Documentation` ✅

2. **ID references are friendly:**
   - `**Involved:** Key Point 3, Key Point 7` ✅
   - No raw IDs like `KP_3, KP_7` in output

3. **All tests pass**

4. **Backwards compatible:**
   - Existing jobs with empty labels still render correctly
   - Label falls back to truncated description if empty
