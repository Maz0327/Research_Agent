# Document Output Format Specification

**Purpose:** Defines the exact JSON schemas for Doc 0, Doc 1, Doc 2, and Doc 3.
**Authority:** These schemas are canonical. Pydantic models must match these structures.

---

## Doc 0 — Source Ledger

**Purpose:** Canonical data layer. Preserves 100% of source content and metadata.

### Schema

```json
{
  "document_type": "source_ledger",
  "document_version": "2.0",
  "job_id": "string",
  "generated_at": "ISO-8601 datetime",
  "sources": [
    {
      "source_id": "SRC_1",
      "source_type": "youtube | article | text | screenshot",
      "analysis_mode": "transcript_grounded | caption_grounded | video_only | text_provided | ocr_extracted | article_fetched",
      "confidence_ceiling": "high | medium | low",
      "metadata": {
        "title": "string",
        "creator": "string | null",
        "date": "ISO-8601 date | null",
        "duration_seconds": "integer | null",
        "url": "string | null",
        "description": "string | null"
      },
      "transcript_provenance": {
        "method": "supadata | whisper | youtube_captions | none",
        "quality": "high | medium | low | unavailable",
        "timestamp_reliability": "precise | approximate | unavailable",
        "acquisition_timestamp": "ISO-8601 datetime"
      },
      "full_text": "string | null",
      "full_text_storage": "inline | blob_reference | unavailable",
      "blob_reference": "string | null",
      "skim_summary": "string (2-3 sentences)",
      "status": "complete | partial | failed",
      "degradation_notes": ["string"] 
    }
  ],
  "indexes": {
    "quotes": [
      {
        "quote_id": "QT_1",
        "text": "string",
        "source_id": "SRC_1",
        "speaker": "string | null",
        "timestamp": "string | null",
        "timestamp_seconds": "integer | null",
        "verification_status": "verified | partial | unverified"
      }
    ],
    "observations": [
      {
        "observation_id": "OBS_1",
        "description": "string",
        "source_id": "SRC_1",
        "timestamp": "string | null",
        "approximate": true,
        "type": "observation"
      }
    ],
    "claims": [
      {
        "claim_id": "CLM_1",
        "statement": "string",
        "source_id": "SRC_1",
        "speaker": "string | null",
        "timestamp": "string | null",
        "confidence": "high | medium | low",
        "verifiable": "boolean"
      }
    ],
    "entities": [
      {
        "name": "string",
        "type": "person | organization | place | event | other",
        "source_ids": ["SRC_1"],
        "first_mention_timestamp": "string | null"
      }
    ],
    "timestamps": [
      {
        "timestamp": "string",
        "timestamp_seconds": "integer",
        "source_id": "SRC_1",
        "description": "string"
      }
    ]
  },
  "corpus_stats": {
    "total_sources": "integer",
    "sources_by_mode": {
      "transcript_grounded": "integer",
      "caption_grounded": "integer",
      "video_only": "integer",
      "text_provided": "integer",
      "ocr_extracted": "integer",
      "article_fetched": "integer"
    },
    "total_quotes": "integer",
    "total_observations": "integer",
    "total_claims": "integer",
    "total_duration_seconds": "integer | null"
  }
}
```

### Field Requirements

| Field | Required | Notes |
|-------|----------|-------|
| `sources` | Yes | At least 1 source |
| `sources[].source_id` | Yes | Format: `SRC_N` |
| `sources[].analysis_mode` | Yes | One of 6 modes |
| `sources[].full_text` | Conditional | Required if `full_text_storage: inline` |
| `indexes.quotes` | Conditional | Only for modes that allow quotes |
| `indexes.observations` | Conditional | Only for modes that don't allow quotes |

---

## Doc 1 — Jump-Start Directions

**Purpose:** Research direction layer. Reduces activation energy for next steps.

### Schema

```json
{
  "document_type": "jump_start_directions",
  "document_version": "2.0",
  "job_id": "string",
  "generated_at": "ISO-8601 datetime",
  "scope_lock": {
    "topic": "string",
    "boundaries": "string",
    "not_about": ["string"]
  },
  "corpus_coverage": {
    "summary": "string (2-3 sentences)",
    "sources_analyzed": "integer",
    "high_confidence_sources": "integer",
    "perspectives_represented": ["string"],
    "perspectives_missing": ["string"]
  },
  "gaps": [
    {
      "gap_id": "GAP_1",
      "description": "string",
      "importance": "high | medium | low",
      "category": "factual | perspective | timeline | context | verification",
      "would_answer": "string",
      "suggested_source_types": ["string"]
    }
  ],
  "open_questions": [
    {
      "question": "string",
      "why_unanswered": "string",
      "related_gaps": ["GAP_1"]
    }
  ],
  "research_directions": [
    {
      "direction_id": "RD_1",
      "title": "string",
      "description": "string",
      "priority": "high | medium | low",
      "effort_estimate": "quick | moderate | deep_dive",
      "addresses_gaps": ["GAP_1"],
      "suggested_sources": ["string"],
      "search_queries": ["string"]
    }
  ],
  "verification_checklist": [
    {
      "item": "string",
      "status": "unverified | partially_verified | verified",
      "source_for_verification": "string | null",
      "importance": "high | medium | low"
    }
  ],
  "top_three_next_steps": [
    {
      "step": "string",
      "rationale": "string",
      "addresses": "string"
    }
  ],
  "booster_augmentation": {
    "augmented": "boolean",
    "augmented_at": "ISO-8601 datetime | null",
    "additional_directions": []
  }
}
```

### Field Requirements

| Field | Required | Notes |
|-------|----------|-------|
| `scope_lock` | Yes | Defines what this research is/isn't |
| `gaps` | Yes | Minimum 3 gaps recommended |
| `top_three_next_steps` | Yes | Exactly 3 items |
| `research_directions` | Yes | Minimum 2 directions |
| `booster_augmentation` | Yes | Placeholder for Booster results |

### Cardinality Targets

| Field | Minimum | Target | Maximum |
|-------|---------|--------|---------|
| `gaps` | 3 | 5-8 | 15 |
| `research_directions` | 2 | 4-6 | 10 |
| `open_questions` | 1 | 3-5 | 10 |
| `verification_checklist` | 1 | 3-5 | 10 |

---

## Doc 2 — Semantic Research Brief

**Purpose:** Analysis layer. The "80% finished" semantic understanding.

### Schema

```json
{
  "document_type": "semantic_research_brief",
  "document_version": "2.0",
  "job_id": "string",
  "generated_at": "ISO-8601 datetime",
  "executive_summary": {
    "one_sentence": "string",
    "three_sentences": "string",
    "key_takeaway": "string"
  },
  "confidence_assessment": {
    "overall_confidence": "high | medium | low",
    "confidence_rationale": "string",
    "high_confidence_claims": "integer",
    "medium_confidence_claims": "integer",
    "low_confidence_claims": "integer",
    "limiting_factors": ["string"]
  },
  "themes": [
    {
      "theme_id": "THEME_1",
      "name": "string",
      "description": "string",
      "prevalence": "dominant | significant | minor",
      "source_ids": ["SRC_1"],
      "supporting_key_points": ["KP_1", "KP_2"],
      "supporting_quotes": ["QT_1"]
    }
  ],
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "string",
      "source_ids": ["SRC_1"],
      "confidence": "high | medium | low",
      "timestamp": "string | null",
      "supporting_evidence": {
        "quotes": ["QT_1"],
        "observations": ["OBS_1"],
        "claims": ["CLM_1"]
      },
      "contested_by": ["SRC_2"] 
    }
  ],
  "tensions": [
    {
      "tension_id": "TEN_1",
      "description": "string",
      "nature": "factual_dispute | perspective_difference | timeline_conflict | internal_contradiction | other",
      "sources_involved": ["SRC_1", "SRC_2"],
      "position_a": {
        "summary": "string",
        "source_ids": ["SRC_1"],
        "supporting_evidence": ["KP_1", "QT_1"]
      },
      "position_b": {
        "summary": "string",
        "source_ids": ["SRC_2"],
        "supporting_evidence": ["KP_2", "QT_2"]
      },
      "resolution_status": "unresolved | partially_resolved | resolved",
      "resolution_notes": "string | null"
    }
  ],
  "assumptions": [
    {
      "assumption": "string",
      "source_ids": ["SRC_1"],
      "explicit_or_implicit": "explicit | implicit",
      "impact_if_wrong": "string"
    }
  ],
  "gaps_summary": {
    "total_gaps": "integer",
    "critical_gaps": ["GAP_1"],
    "see_doc_1_for_details": true
  },
  "speculation_section": {
    "included": "boolean",
    "speculation_items": [
      {
        "speculation": "string",
        "basis": "string",
        "confidence": "low",
        "explicitly_speculative": true
      }
    ]
  },
  "source_concordance": {
    "sources_agree_on": ["string"],
    "sources_disagree_on": ["string"],
    "single_source_claims": ["string"]
  }
}
```

### Field Requirements

| Field | Required | Notes |
|-------|----------|-------|
| `executive_summary` | Yes | All three fields required |
| `confidence_assessment` | Yes | Must reflect actual extraction |
| `themes` | Yes | Minimum 2 themes |
| `key_points` | Yes | Minimum 5 key points |
| `tensions` | No | Empty array if no tensions |
| `speculation_section.included` | Yes | Boolean, items optional |

### Cardinality Targets

| Field | Minimum | Target | Maximum |
|-------|---------|--------|---------|
| `themes` | 2 | 4-6 | 10 |
| `key_points` | 5 | 8-15 | 25 |
| `tensions` | 0 | 1-3 | 10 |
| `assumptions` | 1 | 2-4 | 8 |

---

## Doc 3 — Producer Packet

**Purpose:** Creative interpretation layer. Story angles and narrative elements.

### Gating Requirements (ALL must be met)

- 4+ sources in job
- At least 1 source with `confidence_ceiling: high`
- Job status: `completed`
- User explicitly requests Doc 3

### Schema

```json
{
  "document_type": "producer_packet",
  "document_version": "2.0",
  "job_id": "string",
  "generated_at": "ISO-8601 datetime",
  "creative_interpretation_notice": "This document contains creative interpretation and narrative suggestions. It is not factual research output. All content should be verified against Doc 0/1/2.",
  "story_core": {
    "central_question": "string",
    "one_sentence_pitch": "string",
    "why_this_matters": "string",
    "target_audience": "string",
    "emotional_arc": "string"
  },
  "narrative_angles": [
    {
      "angle_id": "ANG_1",
      "title": "string",
      "description": "string",
      "strengths": ["string"],
      "weaknesses": ["string"],
      "best_for": "string",
      "key_sources": ["SRC_1"]
    }
  ],
  "opening_hooks": [
    {
      "hook_type": "cold_open | provocative_question | surprising_fact | personal_story | scene_setting",
      "content": "string",
      "tone": "string",
      "source_basis": ["SRC_1"] 
    }
  ],
  "structure_options": [
    {
      "structure_type": "chronological | thematic | mystery_reveal | compare_contrast | problem_solution",
      "description": "string",
      "section_breakdown": ["string"],
      "pros": ["string"],
      "cons": ["string"]
    }
  ],
  "key_moments": [
    {
      "moment": "string",
      "source_id": "SRC_1",
      "timestamp": "string | null",
      "why_compelling": "string",
      "potential_use": "string"
    }
  ],
  "title_options": [
    {
      "title": "string",
      "subtitle": "string | null",
      "tone": "serious | provocative | curious | urgent",
      "seo_considerations": "string | null"
    }
  ],
  "thumbnail_concepts": [
    {
      "concept": "string",
      "visual_elements": ["string"],
      "text_overlay": "string | null",
      "emotional_appeal": "string"
    }
  ],
  "risk_assessment": {
    "sensitivity_level": "low | medium | high",
    "potential_issues": ["string"],
    "mitigation_suggestions": ["string"],
    "legal_considerations": ["string"],
    "ethical_considerations": ["string"]
  },
  "interview_suggestions": {
    "people_to_contact": [
      {
        "name": "string",
        "role": "string",
        "why_relevant": "string",
        "potential_questions": ["string"]
      }
    ],
    "expert_perspectives_needed": ["string"]
  },
  "b_roll_suggestions": [
    {
      "description": "string",
      "purpose": "string",
      "source_options": ["string"]
    }
  ]
}
```

### Field Requirements

| Field | Required | Notes |
|-------|----------|-------|
| `creative_interpretation_notice` | Yes | Exact text as shown |
| `story_core` | Yes | All fields required |
| `narrative_angles` | Yes | Minimum 2 angles |
| `opening_hooks` | Yes | Minimum 2 hooks |
| `structure_options` | Yes | Minimum 2 options |
| `risk_assessment` | Yes | All fields required |

### Cardinality Targets

| Field | Minimum | Target | Maximum |
|-------|---------|--------|---------|
| `narrative_angles` | 2 | 3-4 | 6 |
| `opening_hooks` | 2 | 3-4 | 6 |
| `structure_options` | 2 | 3 | 5 |
| `title_options` | 2 | 4-5 | 8 |
| `key_moments` | 3 | 5-8 | 15 |

---

## Validation Rules

### Cross-Document Consistency

1. All `source_id` references in Docs 1/2/3 must exist in Doc 0
2. All `quote_id` references must exist in Doc 0 indexes
3. All `key_point_id` references must exist in Doc 2
4. All `gap_id` references must exist in Doc 1

### Confidence Ceiling Enforcement

No item in Doc 2 may have confidence higher than its source's ceiling:

```
If source.confidence_ceiling == "medium":
  key_point.confidence cannot be "high"
```

### Mode-Specific Rules

| Mode | Quotes Allowed | Observations Required |
|------|---------------|----------------------|
| `transcript_grounded` | Yes | No |
| `caption_grounded` | Yes | No |
| `video_only` | No | Yes |
| `text_provided` | No | Yes |
| `ocr_extracted` | No | Yes |
| `article_fetched` | Yes | No |

---

## Markdown Rendering

When documents are rendered for human consumption, use this structure:

### Doc 0 Markdown Template

```markdown
# Source Ledger

**Job ID:** {job_id}
**Generated:** {generated_at}
**Sources:** {total_sources}

---

## Sources

### {source_id}: {title}

- **Type:** {source_type}
- **Mode:** {analysis_mode}
- **Confidence Ceiling:** {confidence_ceiling}
- **Status:** {status}

**Skim Summary:** {skim_summary}

[Full text available in expandable section or blob]

---

## Quote Index

| ID | Text | Source | Speaker | Timestamp |
|----|------|--------|---------|-----------|
| {quote_id} | {text} | {source_id} | {speaker} | {timestamp} |

---

## Claim Index

| ID | Claim | Source | Confidence | Verifiable |
|----|-------|--------|------------|------------|
| {claim_id} | {statement} | {source_id} | {confidence} | {verifiable} |
```

### Doc 1 Markdown Template

```markdown
# Jump-Start Research Directions

**Job ID:** {job_id}
**Generated:** {generated_at}

---

## Scope

**Topic:** {scope_lock.topic}
**Boundaries:** {scope_lock.boundaries}
**Not About:** {scope_lock.not_about}

---

## What We Have

{corpus_coverage.summary}

- **Sources Analyzed:** {sources_analyzed}
- **High Confidence:** {high_confidence_sources}

---

## Gaps

### {gap_id}: {description}

- **Importance:** {importance}
- **Category:** {category}
- **Would Answer:** {would_answer}

---

## Top 3 Next Steps

1. **{step}** — {rationale}
2. **{step}** — {rationale}
3. **{step}** — {rationale}
```

### Doc 2 Markdown Template

```markdown
# Semantic Research Brief

**Job ID:** {job_id}
**Generated:** {generated_at}
**Overall Confidence:** {overall_confidence}

---

## Executive Summary

{executive_summary.three_sentences}

**Key Takeaway:** {key_takeaway}

---

## Themes

### {theme_id}: {name}

{description}

**Prevalence:** {prevalence}
**Sources:** {source_ids}

---

## Key Points

### {key_point_id}

> {statement}

- **Confidence:** {confidence}
- **Sources:** {source_ids}

---

## Tensions

### {tension_id}: {description}

**Nature:** {nature}

**Position A:** {position_a.summary}
- Sources: {position_a.source_ids}

**Position B:** {position_b.summary}
- Sources: {position_b.source_ids}

**Status:** {resolution_status}
```

---

## Pydantic Model Mapping

| Schema | Pydantic Model | Location |
|--------|---------------|----------|
| Doc 0 | `SourceLedger` | `backend/models/document_outputs.py` |
| Doc 1 | `JumpStartDirections` | `backend/models/document_outputs.py` |
| Doc 2 | `SemanticBrief` | `backend/models/document_outputs.py` |
| Doc 3 | `ProducerPacket` | `backend/models/document_outputs.py` |

Nested models should match nested schema objects.

---

**END OF DOCUMENT OUTPUT FORMAT SPECIFICATION**
