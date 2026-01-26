# Investigation: Document Output Formatting & UX Issues

**Date:** 2026-01-26
**Branch:** `claude/investigate-doc-display-aa05B`
**Status:** Complete

---

## Executive Summary

Output documents have significant UX issues with subheaders and visual hierarchy. The core problem: **section item headers use meaningless IDs instead of descriptive titles**, making documents hard to scan and navigate.

**Impact:** Users see "Theme 1", "Theme 2", "Tension 1" without knowing WHAT each item is about until they read the full description.

---

## Issues Found

### 1. Tension Headers Have No Title (Critical)

**File:** `backend/models/document_outputs.py:904-918`

```python
# CURRENT (BAD)
f"### {t.tension_id}",                            # → "### TEN_1"
f"**Description:** {t.description}",
f"**Involved:** `{', '.join(t.involved_key_points)}`",
```

**What user sees:**
```
### Tension 1
**Description:** Two sources give conflicting dates for the merger announcement
**Involved:** Key Point 3, Key Point 7
```

**Problem:** Header "Tension 1" is meaningless. User must read description to understand.

---

### 2. Gap Headers Have No Title in Doc 2 (Critical)

**File:** `backend/models/document_outputs.py:922-937`

```python
# CURRENT (BAD)
f"### {g.gap_id}",                                # → "### GAP_1"
f"**Why it matters:** {g.why_expected}",
```

**What user sees:**
```
### Open Question 1
**Why it matters:** No primary documentation for the $50M claim
```

**Note:** Doc 1 correctly uses `f"### {g.gap_id}: {g.description}"` - inconsistent!

---

### 3. ID References Remain Raw in Backticks (Medium)

**Multiple locations:**

```python
# Themes section - line 879
f"**Related Key Points:** `{', '.join(theme.related_key_points)}`"
# Output: **Related Key Points:** `KP_1, KP_2, KP_3`

# Tensions section - line 915
f"**Involved:** `{', '.join(t.involved_key_points)}`"
# Output: **Involved:** `KP_3, KP_7`
```

**Problem:** Backticks prevent frontend ID transformation. Users see raw IDs.

---

### 4. Numbered Items Without Context (Medium)

When user scrolls through document, they see:

```
## Key Themes

### Theme 1: Financial Opacity
...
### Theme 2: Timeline Inconsistencies
...

## Tensions & Contradictions

### Tension 1          ← User: "Wait, is this Theme 1 or Tension 1?"
...
### Tension 2
...

## Gaps & Weaknesses

### Open Question 1    ← User: "1 again? What section am I in?"
...
```

**Problem:** Numbers reset per section. Without clear section context, items blend together.

---

### 5. Inconsistent Formatting Across Documents

| Section | Doc 1 | Doc 2 |
|---------|-------|-------|
| Key Points | List: `- **KP_1:** statement` | Table: `\| KP_1 \| statement \| sources \|` |
| Themes | N/A | Header: `### THEME_1: {label}` ✅ |
| Tensions | List: `- **TEN_1:** description` | Header: `### TEN_1` ❌ |
| Gaps | Header: `### GAP_1: {description}` ✅ | Header: `### GAP_1` ❌ |

---

### 6. No Visual Dividers Between Items (Low)

Items are separated only by empty lines. Long descriptions make it hard to see where one item ends and another begins.

---

## Root Cause Analysis

### A. Data Model Has Titles, Code Doesn't Use Them

```python
# Theme model - has label AND description
@dataclass
class Theme:
    theme_id: str
    label: str              # ← "Financial Opacity" (short title)
    description: str        # ← Full description

# Tension model - has description but NO short label
@dataclass
class Tension:
    tension_id: str
    description: str        # ← Full description, no short title

# Gap model - has description but NO short label
@dataclass
class Gap:
    gap_id: str
    description: str        # ← Full description
    why_expected: str
```

**Problem:** Tension and Gap models don't have a `label` field for short titles.

### B. Frontend Transform Doesn't Touch Backticks

`document-formatters.ts` protects content in backticks from transformation:

```typescript
// Protect inline code (`...`)
result = result.replace(/`[^`\n]+`/g, (match) => {
    const placeholder = `${PLACEHOLDER_PREFIX}INLINE_${counter++}`;
    protectedMap.set(placeholder, match);
    return placeholder;
});
```

So `\`KP_1, KP_2\`` stays as raw IDs.

---

## Recommendations

### Priority 1: Add Titles to Headers (Critical)

**Fix Tensions in Doc 2:**

```python
# BEFORE
f"### {t.tension_id}",

# AFTER
# Truncate description for header, show full below
short_desc = t.description[:60] + "..." if len(t.description) > 60 else t.description
f"### {t.tension_id}: {short_desc}",
```

**Fix Gaps in Doc 2:**

```python
# BEFORE
f"### {g.gap_id}",

# AFTER
short_desc = g.description[:60] + "..." if len(g.description) > 60 else g.description
f"### {g.gap_id}: {short_desc}",
```

**Result:**
```
### Tension 1: Two sources give conflicting dates for the merger...
### Open Question 1: No primary documentation for the $50M claim...
```

---

### Priority 2: Transform IDs Before Storage (Medium)

**Option A:** Transform in `to_markdown()` methods

```python
def _format_id(id_str: str) -> str:
    """Convert SRC_1 → Source 1, KP_3 → Key Point 3, etc."""
    mapping = {
        "SRC": "Source",
        "KP": "Key Point",
        "THEME": "Theme",
        "TEN": "Tension",
        "GAP": "Open Question",
    }
    import re
    match = re.match(r"^([A-Z]+)_(\d+)$", id_str)
    if match:
        prefix, num = match.groups()
        label = mapping.get(prefix, prefix)
        return f"{label} {num}"
    return id_str
```

**Option B:** Remove backticks so frontend transforms them

```python
# BEFORE
f"**Related Key Points:** `{', '.join(theme.related_key_points)}`"

# AFTER
f"**Related Key Points:** {', '.join(theme.related_key_points)}"
```

---

### Priority 3: Add Visual Dividers (Medium)

```python
# Add horizontal rule between items
for i, theme in enumerate(self.themes):
    lines.extend([...theme content...])
    if i < len(self.themes) - 1:
        lines.append("")
        lines.append("---")
        lines.append("")
```

---

### Priority 4: Add Section Context to Item Headers (Low)

**Option A:** Prefix with section name
```
### [Theme] Financial Opacity
### [Tension] Timeline Conflict
### [Gap] Missing Documentation
```

**Option B:** Use different header levels per section type
```
## Key Themes
### Theme 1: Financial Opacity

## Tensions
#### Tension 1: Timeline Conflict   ← Different level (####)

## Gaps
##### Gap 1: Missing Documentation  ← Different level (#####)
```

---

### Priority 5: Consider Adding `label` Field to Models (Future)

```python
@dataclass
class Tension:
    tension_id: str
    label: str              # NEW: Short title like "Timeline Conflict"
    description: str        # Full description

@dataclass
class Gap:
    gap_id: str
    label: str              # NEW: Short title like "Missing Primary Docs"
    description: str
    why_expected: str
```

This would require:
1. Update models in `semantic_units.py`
2. Update extraction prompts to generate labels
3. Update JSON schemas

---

## Affected Files

| File | Changes Needed |
|------|----------------|
| `backend/models/document_outputs.py` | Fix `to_markdown()` for SemanticBrief, JumpStartDirections |
| `backend/models/semantic_units.py` | (Optional) Add `label` field to Tension, Gap |
| `backend/pipeline/prompts/*.py` | (If adding labels) Update extraction schemas |
| `frontend/lib/document-formatters.ts` | Consider removing backtick protection for ID lists |

---

## Implementation Plan

### Phase 1: Quick Wins (1-2 hours)
1. Add description snippet to Tension headers in Doc 2
2. Add description snippet to Gap headers in Doc 2
3. Remove backticks from ID reference lists

### Phase 2: Consistency Pass (2-3 hours)
1. Audit all `to_markdown()` methods for ID handling
2. Apply consistent formatting pattern across all docs
3. Add visual dividers between major items

### Phase 3: Model Enhancement (4+ hours, requires approval)
1. Add `label` field to Tension and Gap models
2. Update extraction prompts
3. Update validation rules

---

## Questions for Owner

1. **Labels vs. Truncated Descriptions:** Should we add a `label` field to models, or is truncating the description sufficient?

2. **Frontend vs. Backend Transform:** Should ID→label transformation happen in backend (stored as "Source 1") or frontend (stored as "SRC_1", transformed for display)?

3. **Visual Dividers:** Horizontal rules between all items, or only between major sections?

4. **Backtick Removal:** Safe to remove backticks from ID lists? Any reason they were added?

---

## Appendix: Current vs. Proposed Output

### Current (Doc 2 Tensions)
```markdown
## ⚡ Tensions & Contradictions

### TEN_1

**Description:** Two sources give conflicting dates for the merger announcement

**Involved:** `KP_3, KP_7`

### TEN_2

**Description:** Subject contradicts earlier public statements about funding
```

### Proposed (Doc 2 Tensions)
```markdown
## ⚡ Tensions & Contradictions

### Tension 1: Conflicting Merger Announcement Dates

> Two sources give conflicting dates for the merger announcement.

**Involved:** Key Point 3, Key Point 7

---

### Tension 2: Contradictory Funding Statements

> Subject contradicts earlier public statements about funding.
```
