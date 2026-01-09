# Semantic Extraction Skill

**Skill ID:** `semantic-extraction`
**Auto-Trigger:** When implementing Doc 2 (Semantic Research Brief) functionality
**Purpose:** Enforce semantic-first extraction patterns and epistemic categories

---

## When This Skill Activates

- Working on Gemini semantic extraction prompts
- Implementing Doc 2 assembly logic
- Creating or modifying Theme/KeyPoint/Tension models
- Writing extraction validation code

---

## Epistemic Categories (Mandatory)

All extracted information must fall into ONE of these categories:

| Layer | Name | Description | Example |
|-------|------|-------------|---------|
| 1 | **Source Data** | Verbatim text, no interpretation | Full transcript |
| 2 | **Descriptive Extraction** | What source explicitly says | Claims, quotes |
| 3 | **Semantic Interpretation** | Patterns across sources | Themes, tensions |
| 4 | **Speculation** | Hypotheses beyond evidence | Creative directions |

**Rule:** Never mix layers. Each output field must be tagged with its epistemic level.

---

## Doc 2 Structure Requirements

```python
class SemanticBrief:
    confidence_overall: Literal["high", "medium", "low"]
    themes: List[Theme]          # 4-10 themes
    key_points: List[KeyPoint]   # 8-20 with citations
    interpretations: List[Interpretation]  # Competing framings
    tensions: List[Tension]      # Contradictions
    gaps: List[Gap]              # Missing areas
    creative_directions: List[Direction]  # Optional, speculative
    confidence_calibration: ConfidenceCalibration
```

---

## Extraction Rules

### Key Points
- Must be neutral assertions
- Must cite `based_on: [QUOTE_xxx, CLIP_xxx]`
- No narrative framing
- No conclusions

### Themes
- Must span 2+ key points
- Describe patterns, not topics
- Bad: "Funding"
- Good: "Inconsistent explanations regarding funding sources"

### Tensions
- Must cite all involved key points
- Surface contradictions, do NOT resolve them
- System is not an arbiter of truth

---

## Minimum Depth Requirements

| Element | Minimum | On Failure |
|---------|---------|------------|
| Key Points | 8 | `status: "needs_more_sources"` |
| Themes | 4 | Warning, proceed |
| Gaps | 5 | Warning, proceed |
| Citations | All assertions | Hard fail |

---

## Checklist Before Commit

- [ ] Every KeyPoint has `based_on` field
- [ ] No Theme has fewer than 2 related key points
- [ ] Speculation clearly labeled
- [ ] Confidence calibration present
- [ ] All IDs follow scheme: `KEY_POINT_001`, `THEME_001`, etc.

---

## Anti-Patterns to Avoid

- "The video discusses..." (summary, not extraction)
- High confidence without multiple sources
- Resolving tensions instead of surfacing them
- Missing gap identification
- Speculation presented without label

---

## Reference Documents

- `Active Docs/REVIEW THESE FILES/Research Agent System Specification (RASS).md` - Section 3 (Doc 2)
- `Active Docs/REVIEW THESE FILES/Document Output Format Specification.md` - Doc 2 structure
- `Active Docs/REVIEW THESE FILES/Gemini Semantic Extraction Prompt Pack.md` - Prompt patterns
