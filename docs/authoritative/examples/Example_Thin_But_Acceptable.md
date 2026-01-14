# Example: Thin But Acceptable Output

**Purpose:** Canonical example of minimum valid output when the corpus is very limited.
**Key Point:** Sparse and honest is valid. The system should never pad thin results with hallucinated content.

---

## Scenario

**Topic:** User wants to research a niche controversy they heard about
**Sources Submitted:** 1 YouTube video (only source they could find)

**What We Have:**
- SRC_1: Single commentary video (transcript_grounded, HIGH)
- 8 minutes long
- Discusses a minor dispute between two small creators
- Limited detail, mostly opinion

**Result:** Valid output, but explicitly thin. System does its job by being honest about limitations.

---

## Doc 0 — Source Ledger (Thin)

```json
{
  "document_type": "source_ledger",
  "document_version": "2.0",
  "job_id": "job_thin_example",
  "generated_at": "2026-01-13T14:00:00Z",
  "sources": [
    {
      "source_id": "SRC_1",
      "source_type": "youtube",
      "analysis_mode": "transcript_grounded",
      "confidence_ceiling": "high",
      "metadata": {
        "title": "The SkylerVsJamie Drama Explained",
        "creator": "SmallCreatorNews",
        "date": "2026-01-08",
        "duration_seconds": 487,
        "url": "https://youtube.com/watch?v=thin_example",
        "description": "Quick breakdown of what's happening between Skyler and Jamie"
      },
      "transcript_provenance": {
        "method": "supadata",
        "quality": "high",
        "timestamp_reliability": "precise",
        "acquisition_timestamp": "2026-01-13T13:55:00Z"
      },
      "full_text": "[Full transcript - 1,247 words]",
      "full_text_storage": "inline",
      "blob_reference": null,
      "skim_summary": "Commentary video providing third-party perspective on a dispute between two small creators over alleged content theft.",
      "status": "complete",
      "degradation_notes": []
    }
  ],
  "indexes": {
    "quotes": [
      {
        "quote_id": "QT_1",
        "text": "From what I can tell, Skyler posted the video first, but Jamie claims she had the idea months ago",
        "source_id": "SRC_1",
        "speaker": "SmallCreatorNews host",
        "timestamp": "01:45",
        "timestamp_seconds": 105,
        "verification_status": "verified"
      },
      {
        "quote_id": "QT_2",
        "text": "Neither of them has shown receipts, so honestly, we don't really know who's telling the truth",
        "source_id": "SRC_1",
        "speaker": "SmallCreatorNews host",
        "timestamp": "04:20",
        "timestamp_seconds": 260,
        "verification_status": "verified"
      },
      {
        "quote_id": "QT_3",
        "text": "I'm not picking sides here because there's just not enough information",
        "source_id": "SRC_1",
        "speaker": "SmallCreatorNews host",
        "timestamp": "06:55",
        "timestamp_seconds": 415,
        "verification_status": "verified"
      }
    ],
    "observations": [],
    "claims": [
      {
        "claim_id": "CLM_1",
        "statement": "Skyler posted the disputed video first",
        "source_id": "SRC_1",
        "speaker": "SmallCreatorNews host",
        "timestamp": "01:45",
        "confidence": "medium",
        "verifiable": true
      },
      {
        "claim_id": "CLM_2",
        "statement": "Jamie claims she had the idea months before Skyler's video",
        "source_id": "SRC_1",
        "speaker": "SmallCreatorNews host (reporting Jamie's claim)",
        "timestamp": "01:50",
        "confidence": "medium",
        "verifiable": true
      }
    ],
    "entities": [
      {
        "name": "Skyler",
        "type": "person",
        "source_ids": ["SRC_1"],
        "first_mention_timestamp": "00:30"
      },
      {
        "name": "Jamie",
        "type": "person",
        "source_ids": ["SRC_1"],
        "first_mention_timestamp": "00:35"
      }
    ],
    "timestamps": []
  },
  "corpus_stats": {
    "total_sources": 1,
    "sources_by_mode": {
      "transcript_grounded": 1,
      "caption_grounded": 0,
      "video_only": 0,
      "text_provided": 0,
      "ocr_extracted": 0,
      "article_fetched": 0
    },
    "total_quotes": 3,
    "total_observations": 0,
    "total_claims": 2,
    "total_duration_seconds": 487
  }
}
```

### What Makes This Valid

- Only 1 source, but it's complete
- Only 3 quotes, but they're verified
- Only 2 claims, but they're real
- Stats accurately reflect the thin corpus

---

## Doc 1 — Jump-Start Directions (Thin)

```json
{
  "document_type": "jump_start_directions",
  "document_version": "2.0",
  "job_id": "job_thin_example",
  "generated_at": "2026-01-13T14:00:00Z",
  "scope_lock": {
    "topic": "Alleged content dispute between creators Skyler and Jamie",
    "boundaries": "LIMITED TO single third-party commentary video. No primary sources from either party included.",
    "not_about": ["Other creator disputes", "Platform policies"]
  },
  "corpus_coverage": {
    "summary": "Corpus consists of ONE third-party commentary video. Neither primary party is represented. Commentary host explicitly states information is incomplete.",
    "sources_analyzed": 1,
    "high_confidence_sources": 1,
    "perspectives_represented": [
      "Third-party commentator (SRC_1)"
    ],
    "perspectives_missing": [
      "Skyler (accused party)",
      "Jamie (accusing party)",
      "Any witnesses or collaborators",
      "The original content in dispute"
    ]
  },
  "gaps": [
    {
      "gap_id": "GAP_1",
      "description": "Skyler's direct response or statement not in corpus",
      "importance": "high",
      "category": "perspective",
      "would_answer": "What is Skyler's version of events?",
      "suggested_source_types": ["Skyler's YouTube channel", "Skyler's Twitter/X", "Skyler's TikTok"]
    },
    {
      "gap_id": "GAP_2",
      "description": "Jamie's original accusation not in corpus",
      "importance": "high",
      "category": "perspective",
      "would_answer": "What exactly did Jamie claim and what evidence did she provide?",
      "suggested_source_types": ["Jamie's YouTube channel", "Jamie's Twitter/X", "Jamie's TikTok"]
    },
    {
      "gap_id": "GAP_3",
      "description": "The original disputed content not viewed",
      "importance": "high",
      "category": "factual",
      "would_answer": "What is the actual content being disputed?",
      "suggested_source_types": ["Skyler's original video", "Jamie's claimed prior work"]
    },
    {
      "gap_id": "GAP_4",
      "description": "No evidence ('receipts') from either party",
      "importance": "medium",
      "category": "verification",
      "would_answer": "Is there documentation supporting either claim?",
      "suggested_source_types": ["Screenshots", "Timestamps", "Collaboration records"]
    },
    {
      "gap_id": "GAP_5",
      "description": "Timeline of events not established",
      "importance": "medium",
      "category": "timeline",
      "would_answer": "When did each event occur?",
      "suggested_source_types": ["Social media post dates", "Video upload dates"]
    }
  ],
  "open_questions": [
    {
      "question": "Who actually created the concept first?",
      "why_unanswered": "Only third-party speculation available, no primary evidence",
      "related_gaps": ["GAP_3", "GAP_4"]
    },
    {
      "question": "What specific content is being disputed?",
      "why_unanswered": "Commentary video references it but doesn't show it",
      "related_gaps": ["GAP_3"]
    }
  ],
  "research_directions": [
    {
      "direction_id": "RD_1",
      "title": "Find primary sources from both parties",
      "description": "Locate Skyler's and Jamie's direct statements about the dispute.",
      "priority": "high",
      "effort_estimate": "quick",
      "addresses_gaps": ["GAP_1", "GAP_2"],
      "suggested_sources": ["YouTube channels", "Twitter/X", "TikTok"],
      "search_queries": [
        "Skyler Jamie drama",
        "Skyler response",
        "Jamie accusation Skyler"
      ]
    },
    {
      "direction_id": "RD_2",
      "title": "View the disputed content",
      "description": "Find and analyze the actual videos/content at the center of the dispute.",
      "priority": "high",
      "effort_estimate": "quick",
      "addresses_gaps": ["GAP_3"],
      "suggested_sources": ["Skyler's channel", "Jamie's channel"],
      "search_queries": []
    }
  ],
  "verification_checklist": [
    {
      "item": "Skyler posted first (claimed by SRC_1)",
      "status": "unverified",
      "source_for_verification": "Video upload dates",
      "importance": "high"
    },
    {
      "item": "Jamie had idea months prior (claimed by SRC_1 reporting Jamie)",
      "status": "unverified",
      "source_for_verification": "Jamie's evidence/receipts",
      "importance": "high"
    }
  ],
  "top_three_next_steps": [
    {
      "step": "Find and add Skyler's direct statement/response",
      "rationale": "Currently have zero primary sources - need at least one party's direct account",
      "addresses": "GAP_1"
    },
    {
      "step": "Find and add Jamie's original accusation",
      "rationale": "Cannot evaluate dispute without knowing specific claims",
      "addresses": "GAP_2"
    },
    {
      "step": "Locate the actual content being disputed",
      "rationale": "Core of the dispute is currently unseen",
      "addresses": "GAP_3"
    }
  ],
  "booster_augmentation": {
    "augmented": false,
    "augmented_at": null,
    "additional_directions": []
  }
}
```

### What Makes This Valid

- 5 gaps identified despite only 1 source
- Gaps are specific and actionable
- "Perspectives missing" explicitly names what's absent
- Next steps are clear and prioritized
- System isn't pretending to know more than it does

---

## Doc 2 — Semantic Research Brief (Thin)

```json
{
  "document_type": "semantic_research_brief",
  "document_version": "2.0",
  "job_id": "job_thin_example",
  "generated_at": "2026-01-13T14:00:00Z",
  "executive_summary": {
    "one_sentence": "A content dispute exists between creators Skyler and Jamie, but only third-party commentary is available—no primary sources.",
    "three_sentences": "According to a commentary video, Skyler and Jamie are in a dispute over allegedly stolen content ideas. Skyler reportedly posted first, but Jamie claims prior conception. The commentator explicitly states there is insufficient evidence to determine who is correct.",
    "key_takeaway": "This analysis is based on a single third-party source. Both primary parties' perspectives are missing. No conclusions can be drawn."
  },
  "confidence_assessment": {
    "overall_confidence": "low",
    "confidence_rationale": "Single source, third-party only, source itself admits insufficient information. Cannot establish basic facts of the dispute.",
    "high_confidence_claims": 0,
    "medium_confidence_claims": 2,
    "low_confidence_claims": 0,
    "limiting_factors": [
      "Only 1 source in corpus",
      "Source is third-party commentary, not primary",
      "Source explicitly states information is incomplete",
      "Neither party's direct statement included",
      "Disputed content not viewed"
    ]
  },
  "themes": [
    {
      "theme_id": "THEME_1",
      "name": "Unresolved Attribution Dispute",
      "description": "Two creators each claim ownership of a content idea, but no evidence has been presented publicly.",
      "prevalence": "dominant",
      "source_ids": ["SRC_1"],
      "supporting_key_points": ["KP_1", "KP_2"],
      "supporting_quotes": ["QT_1", "QT_2"]
    }
  ],
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "Skyler posted the disputed content first, but Jamie claims prior conception",
      "source_ids": ["SRC_1"],
      "confidence": "medium",
      "timestamp": "01:45",
      "supporting_evidence": {
        "quotes": ["QT_1"],
        "observations": [],
        "claims": ["CLM_1", "CLM_2"]
      },
      "contested_by": []
    },
    {
      "key_point_id": "KP_2",
      "statement": "Neither party has provided evidence ('receipts') to support their position",
      "source_ids": ["SRC_1"],
      "confidence": "medium",
      "timestamp": "04:20",
      "supporting_evidence": {
        "quotes": ["QT_2"],
        "observations": [],
        "claims": []
      },
      "contested_by": []
    },
    {
      "key_point_id": "KP_3",
      "statement": "The commentator declines to take a position due to insufficient information",
      "source_ids": ["SRC_1"],
      "confidence": "medium",
      "timestamp": "06:55",
      "supporting_evidence": {
        "quotes": ["QT_3"],
        "observations": [],
        "claims": []
      },
      "contested_by": []
    }
  ],
  "tensions": [],
  "assumptions": [
    {
      "assumption": "The commentary video accurately represents the dispute",
      "source_ids": ["SRC_1"],
      "explicit_or_implicit": "implicit",
      "impact_if_wrong": "Entire understanding of the dispute may be incorrect"
    },
    {
      "assumption": "Skyler and Jamie are real creators with a genuine dispute",
      "source_ids": ["SRC_1"],
      "explicit_or_implicit": "implicit",
      "impact_if_wrong": "May be dramatized or fabricated for content"
    }
  ],
  "gaps_summary": {
    "total_gaps": 5,
    "critical_gaps": ["GAP_1", "GAP_2", "GAP_3"],
    "see_doc_1_for_details": true
  },
  "speculation_section": {
    "included": false,
    "speculation_items": []
  },
  "source_concordance": {
    "sources_agree_on": [],
    "sources_disagree_on": [],
    "single_source_claims": [
      "Everything - only one source in corpus"
    ]
  }
}
```

### What Makes This Valid

- Only 1 theme (not padded to meet targets)
- Only 3 key points (reflecting actual content)
- No tensions (no conflicting sources to create tension)
- Overall confidence: LOW (honest assessment)
- Limiting factors extensively documented
- Source concordance notes "only one source"
- No speculation (not enough to speculate on)

---

## What This Example Demonstrates

### 1. Empty Arrays Are Acceptable

```json
"tensions": [],
"speculation_section": {
  "included": false,
  "speculation_items": []
}
```

The system permits empty outputs when there's nothing to report.

### 2. Below-Target Cardinality Is Acceptable

| Field | Target | Actual | Valid? |
|-------|--------|--------|--------|
| themes | 4-6 | 1 | ✅ Yes |
| key_points | 8-15 | 3 | ✅ Yes |
| tensions | 1-3 | 0 | ✅ Yes |

Targets are goals, not requirements. Thin corpus = thin output.

### 3. Honest Confidence Assessment

The system doesn't claim medium or high confidence just because the source quality is high. Overall confidence accounts for:
- Corpus size
- Perspective coverage
- Source type (primary vs secondary)

### 4. Doc 1 Does Heavy Lifting

When Doc 2 is thin, Doc 1 becomes more important:
- Identifies what's missing
- Provides clear next steps
- Guides user to expand corpus

### 5. Source Concordance Reflects Reality

```json
"single_source_claims": [
  "Everything - only one source in corpus"
]
```

Honest about the limitation.

---

## Job Status

```json
{
  "job_id": "job_thin_example",
  "status": "completed",
  "warnings": [
    {
      "type": "thin_corpus",
      "message": "Only 1 source analyzed. Results are limited.",
      "suggestion": "Add more sources for comprehensive analysis."
    }
  ]
}
```

**Note:** This is `completed`, not `completed_with_warnings`. A thin corpus isn't a failure—it's a valid state. The warning is informational.

---

## Anti-Patterns (What Would Be WRONG)

❌ **Padding to meet targets:**
```json
"themes": [
  {"name": "Content Dispute"},  // Real
  {"name": "Creator Ethics"},   // HALLUCINATED to pad
  {"name": "Platform Dynamics"}, // HALLUCINATED to pad
  {"name": "Community Response"}  // HALLUCINATED to pad
]
```

❌ **Inventing tensions:**
```json
"tensions": [
  {
    "description": "Skyler and Jamie have different views on content ownership",
    // HALLUCINATED - we only have third-party, not their views
  }
]
```

❌ **Overstating confidence:**
```json
"overall_confidence": "medium",
"confidence_rationale": "Source is high quality"
// WRONG - single third-party source should be LOW
```

❌ **Speculating to fill gaps:**
```json
"speculation_section": {
  "included": true,
  "speculation_items": [
    {"speculation": "Jamie probably has evidence she hasn't shared"}
    // HALLUCINATED - no basis for this
  ]
}
```

❌ **Pretending completeness:**
```json
"executive_summary": {
  "key_takeaway": "The dispute centers on content timing and creative ownership."
  // WRONG - should acknowledge severe limitations
}
```

---

## Minimum Valid Output Checklist

A thin output is valid if:

- [ ] At least 1 source fully processed
- [ ] At least 1 key point extracted
- [ ] Confidence accurately reflects limitations
- [ ] Gaps identify what's missing
- [ ] Next steps are actionable
- [ ] No hallucinated content to pad results
- [ ] Limitations explicitly stated in executive summary
- [ ] Source concordance reflects single-source reality

---

**END OF EXAMPLE**
