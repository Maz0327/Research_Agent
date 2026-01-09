# Jump-Start Consolidation Skill

**Skill ID:** `jump-start-consolidation`
**Auto-Trigger:** When implementing Doc 1 (Jump-Start) functionality
**Purpose:** Consolidate research direction outputs into unified format

---

## When This Skill Activates

- Working on gap_analysis outputs
- Working on research_starter outputs
- Implementing Doc 1 assembly
- Creating Context Bundle for Deep Research Booster

---

## Doc 1 Purpose

**Jump-Start answers THREE questions:**

1. What do I have?
2. What's missing?
3. Where do I go next?

This is the **activation trigger** for the user.

---

## Consolidation Mapping

Existing outputs map to Doc 1 as follows:

| Current Output | Maps To | Doc 1 Section |
|---------------|---------|---------------|
| `gap_analysis` | `gaps` | Gaps |
| `research_starter.search_queries` | `leads` | Research Directions |
| `research_starter.rabbit_holes` | `verification_checklist` | Verification |
| NEW | `open_questions` | Open Questions |
| NEW | `top_3_next_steps` | Next Steps |

---

## Required Structure

```python
class JumpStart:
    topic_lock: TopicLock
    corpus_summary: CorpusSummary
    gaps: List[Gap]                    # Min 5
    leads: List[Lead]                  # Min 10
    verification_checklist: List[str]  # Min 5
    open_questions: List[str]          # Min 5
    top_3_next_steps: List[str]        # Exactly 3
```

### CorpusSummary
```python
class CorpusSummary:
    source_count: int
    perspectives_represented: List[str]
    time_span: str  # e.g., "2019-2024"
    confidence_level: str
```

---

## Minimum Depth Requirements

| Element | Minimum | On Failure |
|---------|---------|------------|
| Gaps | 5 | Warning + emphasize |
| Leads | 10 | Warning |
| Verification Items | 5 | Warning |
| Open Questions | 5 | Warning |
| Top 3 Next Steps | 3 (exact) | Hard fail |

---

## Gap Format

```python
class Gap:
    gap_id: str  # GAP_001
    description: str
    why_it_matters: str
    what_would_help: str
    priority: Literal["high", "medium", "low"]
```

---

## Lead Format

```python
class Lead:
    lead_id: str  # LEAD_001
    description: str
    search_queries: List[str]
    source_types: List[str]  # youtube, academic, news
    booster_added: bool = False  # True if from Deep Research Booster
```

---

## Context Bundle (For Booster)

```python
class ContextBundle:
    topic_lock: TopicLock
    key_entities: List[str]
    key_points: List[str]  # Summaries only, not full text
    gaps: List[str]  # From Doc 1
    user_intent: Optional[str]
```

Context Bundle is the **input** to Deep Research Booster.

---

## Booster Integration Rules

- Booster ONLY adds to Doc 1 (leads, gaps)
- Booster NEVER modifies Doc 0
- Booster-added items marked `booster_added: true`
- Booster failures don't fail the job

---

## Checklist Before Commit

- [ ] All 5 sections present
- [ ] Minimum counts met (or warnings added)
- [ ] Top 3 Next Steps exactly 3 items
- [ ] All IDs follow scheme: `GAP_001`, `LEAD_001`
- [ ] No narrative conclusions
- [ ] Language is directive, not speculative

---

## Anti-Patterns to Avoid

- Claims of completeness
- Narrative conclusions
- Fewer than minimum counts without warning
- Missing "why it matters" on gaps
- Generic next steps ("research more")

---

## Reference Documents

- `Active Docs/REVIEW THESE FILES/Research Agent System Specification (RASS).md` - Section 3 (Doc 1)
- `Active Docs/REVIEW THESE FILES/Document Output Format Specification.md` - Doc 1 structure
- `Active Docs/REVIEW THESE FILES/Research Agent System Opirational Definitions.md` - Gap, Context Bundle
