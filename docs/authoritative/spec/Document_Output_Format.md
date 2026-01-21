# docs/authoritative/spec/Document_Output_Format.md

**Purpose:** Defines the **exact** structures (schemas) for Doc 0–3. Code MUST match these shapes.

**Rule hierarchy:**
- This spec governs the *shape* and *required fields*.
- Operational Definitions governs vocabulary and rules.

---

## 0) Document Identification

Every document must include:
- `document_type`
- `document_version`
- `job_id`
- `generated_at`

Document types:
- Doc 0: `source_ledger`
- Doc 1: `jump_start`
- Doc 2: `semantic_brief`
- Doc 3: `producer_packet`

---

## 1) Doc 0 — Source Ledger (canonical)

**Intent:** Preserve *canonical* data extracted from sources and all provenance.

### 1.1 Doc 0 JSON schema (canonical)

```json
{
  "document_type": "source_ledger",
  "document_version": "2.2",
  "job_id": "string",
  "generated_at": "ISO-8601 datetime",
  "sources": [
    {
      "source_id": "SRC_1",
      "source_type": "youtube_video | article_url | text_paste | screenshot",
      "analysis_mode": "transcript_grounded | caption_grounded | video_only | article_fetched | text_provided | ocr_extracted",
      "confidence_ceiling": "high | medium | low",
      "metadata": {
        "title": "string | null",
        "creator": "string | null",
        "published_date": "ISO-8601 date | null",
        "duration_seconds": "integer | null",
        "url": "string | null",
        "description": "string | null"
      },
      "transcript_provenance": {
        "method": "supadata | whisper | youtube_captions | none",
        "quality": "high | medium | low | unavailable",
        "timestamp_reliability": "precise | approximate | unavailable",
        "acquired_at": "ISO-8601 datetime"
      },
      "ocr_provenance": {
        "method": "gemini_ocr | tesseract | other | none",
        "ocr_quality": "high | medium | low | none",
        "acquired_at": "ISO-8601 datetime | null"
      },
      "full_text": "string | null",
      "full_text_storage": "inline | blob_reference | unavailable",
      "blob_reference": "string | null",
      "skim_summary": "string",
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
        "accuracy_unverified": true,
        "verbatim_confidence": "high | medium | low",
        "provenance": "user_provided | fetched | derived",
        "approximate": false
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
        "verifiable": true
      }
    ]
  },
  "corpus_stats": {
    "total_sources": 0,
    "sources_by_mode": {
      "transcript_grounded": 0,
      "caption_grounded": 0,
      "video_only": 0,
      "article_fetched": 0,
      "text_provided": 0,
      "ocr_extracted": 0
    },
    "total_quotes": 0,
    "total_observations": 0,
    "total_claims": 0,
    "total_duration_seconds": null
  }
}
```

### 1.2 Doc 0 mode rules (enforced via validation)

**video_only:**
- `indexes.quotes` MUST contain **no entries** where `source_id` refers to a `video_only` source.
- Any quote for a `video_only` source is a HARD FAIL.
- Observations are REQUIRED for `video_only` sources.

**ocr_extracted:**
- If `ocr_provenance.ocr_quality == low`, quotes MUST NOT be emitted; demote quote-like strings to observations + add warning.

**caption_grounded:**
- Quotes allowed only with `approximate=true` and `verbatim_confidence=medium`.

**transcript_grounded / article_fetched:**
- Quotes may be verbatim: `accuracy_unverified=false`, `verbatim_confidence=high`, `provenance=fetched`.

**text_provided:**
- Quotes may be verbatim but truth unverified: `accuracy_unverified=true`, `provenance=user_provided`.

### 1.3 Quote normalization rules

All quote objects MUST be normalized to the canonical fields. No alternative quote structures are permitted.

---

## 2) Doc 1 — Jump Start (gaps + next steps)

**Intent:** Reduce activation energy. Provide gaps and actionable next steps.

### 2.1 Doc 1 JSON schema (canonical)

```json
{
  "document_type": "jump_start",
  "document_version": "2.2",
  "job_id": "string",
  "generated_at": "ISO-8601 datetime",
  "summary": {
    "what_you_have": "string",
    "what_you_dont_have": "string",
    "confidence_note": "string"
  },
  "gaps": [
    {
      "gap_id": "GAP_1",
      "description": "string",
      "importance": "high | medium | low",
      "why_it_matters": "string",
      "supported_by": {
        "source_ids": ["SRC_1"],
        "key_point_ids": ["KP_1"],
        "claim_ids": ["CLM_1"]
      },
      "suggested_sources": ["string"],
      "research_queries": ["string"],
      "notes": "string"
    }
  ],
  "next_steps": [
    {
      "step_id": "STEP_1",
      "title": "string",
      "instruction": "string",
      "expected_output": "string",
      "priority": "high | medium | low",
      "references": {
        "source_ids": ["SRC_1"],
        "gap_ids": ["GAP_1"]
      }
    }
  ],
  "safety": {
    "no_new_facts_ack": true,
    "how_to_verify": ["string"],
    "limitations": ["string"]
  }
}
```

### 2.2 Doc 1 “no new facts” enforcement
Doc 1 may propose what to research next, but must not assert factual details not found in Doc 0.

Allowed:
- “We don’t know X.”
- “To confirm X, check Y.”

Forbidden:
- “X happened on DATE” unless Doc 0 contains that fact.

---

## 3) Doc 2 — Semantic Brief (themes + tensions)

**Intent:** Provide analysis and synthesis (without introducing new facts).

### 3.1 Doc 2 JSON schema (canonical)

```json
{
  "document_type": "semantic_brief",
  "document_version": "2.2",
  "job_id": "string",
  "generated_at": "ISO-8601 datetime",
  "brief": {
    "one_paragraph": "string",
    "what_is_certain": "string",
    "what_is_uncertain": "string"
  },
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "string",
      "source_ids": ["SRC_1"],
      "supporting_quote_ids": ["QT_1"],
      "supporting_claim_ids": ["CLM_1"],
      "confidence": "high | medium | low",
      "notes": "string"
    }
  ],
  "themes": [
    {
      "theme_id": "THEME_1",
      "name": "string",
      "description": "string",
      "source_ids": ["SRC_1"],
      "supporting_key_point_ids": ["KP_1"]
    }
  ],
  "tensions": [
    {
      "tension_id": "TEN_1",
      "description": "string",
      "nature": "factual_dispute | perspective_difference | timeline_conflict | other",
      "sources_involved": ["SRC_1"],
      "supporting_key_point_ids": ["KP_1"],
      "resolution_status": "unresolved | partially_resolved | resolved",
      "notes": "string"
    }
  ],
  "guardrails": {
    "no_new_facts_ack": true,
    "traceability": {
      "all_key_points_must_reference_doc0": true,
      "all_quotes_must_reference_doc0": true
    }
  }
}
```

### 3.2 Doc 2 confidence + traceability rules
- A key point’s `confidence` must not exceed the minimum ceiling among its supporting sources.
- Any `supporting_quote_ids` must exist in Doc 0 and match the referenced sources.

---

## 4) Doc 3 — Producer Packet (optional)

**Intent:** Creative layer. Must not modify Docs 0–2.

### 4.1 Gating requirements
Doc 3 may only be generated if ALL are true:
- Job is `completed`.
- User explicitly requests Doc 3.
- Job has ≥ 4 sources.
- Job has at least one `high` ceiling source.

### 4.2 Doc 3 JSON schema (canonical)

```json
{
  "document_type": "producer_packet",
  "document_version": "2.2",
  "job_id": "string",
  "generated_at": "ISO-8601 datetime",
  "angles": [
    {
      "angle_id": "ANGLE_1",
      "hook": "string",
      "one_sentence_premise": "string",
      "acts": [
        {
          "act": 1,
          "summary": "string",
          "beats": ["string"]
        }
      ],
      "must_include": ["string"],
      "must_avoid": ["string"],
      "references": {
        "source_ids": ["SRC_1"],
        "key_point_ids": ["KP_1"],
        "quote_ids": ["QT_1"]
      }
    }
  ],
  "notes": {
    "limitations": ["string"],
    "no_new_facts_ack": true
  }
}
```

---

## 5) Cross-document validation rules (authoritative)

1) Every referenced ID must exist.
2) Doc 1 and Doc 2 must not introduce facts beyond Doc 0.
3) Quotes forbidden in `video_only`.
4) OCR low-quality demotes quotes to observations.

---

**END**

