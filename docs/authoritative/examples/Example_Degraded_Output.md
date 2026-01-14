# Example: Degraded Output

**Purpose:** Canonical example of valid output when sources are limited, transcripts fail, or confidence is low.
**Key Point:** Degraded output is still valid output. Thin and honest beats dense and hallucinated.

---

## Scenario

**Topic:** Investigation into a viral TikTok controversy
**Sources Submitted:** 3 YouTube videos

**What Went Wrong:**
- SRC_1: Supadata failed, Whisper failed, YouTube captions failed → `video_only` mode
- SRC_2: Supadata succeeded → `transcript_grounded` mode
- SRC_3: Only YouTube auto-captions available → `caption_grounded` mode

**Result:** Job completes with warnings, produces valid but degraded output.

---

## Doc 0 — Source Ledger (Degraded)

```json
{
  "document_type": "source_ledger",
  "document_version": "2.0",
  "job_id": "job_degraded_example",
  "generated_at": "2026-01-13T10:00:00Z",
  "sources": [
    {
      "source_id": "SRC_1",
      "source_type": "youtube",
      "analysis_mode": "video_only",
      "confidence_ceiling": "low",
      "metadata": {
        "title": "SHOCKING Truth About the Situation",
        "creator": "DramaChannel",
        "date": "2026-01-10",
        "duration_seconds": 847,
        "url": "https://youtube.com/watch?v=example1",
        "description": "My take on what really happened..."
      },
      "transcript_provenance": {
        "method": "none",
        "quality": "unavailable",
        "timestamp_reliability": "unavailable",
        "acquisition_timestamp": "2026-01-13T09:45:00Z",
        "failure_log": [
          "Supadata: 404 - Video not indexed",
          "Whisper: Timeout after 60s",
          "YouTube captions: No captions available"
        ]
      },
      "full_text": null,
      "full_text_storage": "unavailable",
      "blob_reference": null,
      "skim_summary": "Commentary video discussing a TikTok controversy. Unable to extract transcript - analysis based on visual observation only.",
      "status": "partial",
      "degradation_notes": [
        "No transcript available - video_only mode",
        "All quotes from this source are approximate observations",
        "Confidence ceiling: LOW"
      ]
    },
    {
      "source_id": "SRC_2",
      "source_type": "youtube",
      "analysis_mode": "transcript_grounded",
      "confidence_ceiling": "high",
      "metadata": {
        "title": "Official Response to Allegations",
        "creator": "MainChannel",
        "date": "2026-01-11",
        "duration_seconds": 612,
        "url": "https://youtube.com/watch?v=example2",
        "description": "Addressing the recent controversy..."
      },
      "transcript_provenance": {
        "method": "supadata",
        "quality": "high",
        "timestamp_reliability": "precise",
        "acquisition_timestamp": "2026-01-13T09:46:00Z"
      },
      "full_text": "[Full transcript - 4,523 words]",
      "full_text_storage": "inline",
      "blob_reference": null,
      "skim_summary": "Creator's official response denying allegations, providing context about timeline of events, and announcing legal action.",
      "status": "complete",
      "degradation_notes": []
    },
    {
      "source_id": "SRC_3",
      "source_type": "youtube",
      "analysis_mode": "caption_grounded",
      "confidence_ceiling": "medium",
      "metadata": {
        "title": "Drama Recap - What You Need to Know",
        "creator": "NewsChannel",
        "date": "2026-01-12",
        "duration_seconds": 423,
        "url": "https://youtube.com/watch?v=example3",
        "description": "Summary of the ongoing situation..."
      },
      "transcript_provenance": {
        "method": "youtube_captions",
        "quality": "medium",
        "timestamp_reliability": "approximate",
        "acquisition_timestamp": "2026-01-13T09:47:00Z",
        "caption_note": "Auto-generated captions, may contain errors"
      },
      "full_text": "[Auto-caption transcript - 2,156 words, ~85% accuracy estimate]",
      "full_text_storage": "inline",
      "blob_reference": null,
      "skim_summary": "News-style recap of controversy timeline with clips from multiple sources.",
      "status": "complete",
      "degradation_notes": [
        "Auto-generated captions - some transcription errors likely",
        "Timestamps approximate (±5 seconds)"
      ]
    }
  ],
  "indexes": {
    "quotes": [
      {
        "quote_id": "QT_1",
        "text": "I want to be absolutely clear - I never said those things in that context",
        "source_id": "SRC_2",
        "speaker": "MainChannel creator",
        "timestamp": "02:34",
        "timestamp_seconds": 154,
        "verification_status": "verified"
      },
      {
        "quote_id": "QT_2",
        "text": "We have documentation that contradicts this narrative",
        "source_id": "SRC_2",
        "speaker": "MainChannel creator",
        "timestamp": "05:12",
        "timestamp_seconds": 312,
        "verification_status": "verified"
      },
      {
        "quote_id": "QT_3",
        "text": "The timeline doesn't add up when you look at the actual dates",
        "source_id": "SRC_3",
        "speaker": "NewsChannel host",
        "timestamp": "03:45",
        "timestamp_seconds": 225,
        "verification_status": "partial"
      }
    ],
    "observations": [
      {
        "observation_id": "OBS_1",
        "description": "Video shows screenshots of alleged DMs, but text is not fully legible",
        "source_id": "SRC_1",
        "timestamp": "~04:30",
        "approximate": true,
        "type": "observation"
      },
      {
        "observation_id": "OBS_2",
        "description": "Creator appears emotional, voice cracking while discussing personal impact",
        "source_id": "SRC_1",
        "timestamp": "~08:00",
        "approximate": true,
        "type": "observation"
      },
      {
        "observation_id": "OBS_3",
        "description": "On-screen text claims '3 witnesses have come forward' but no names shown",
        "source_id": "SRC_1",
        "timestamp": "~11:20",
        "approximate": true,
        "type": "observation"
      }
    ],
    "claims": [
      {
        "claim_id": "CLM_1",
        "statement": "The original TikTok was posted on January 8th",
        "source_id": "SRC_2",
        "speaker": "MainChannel creator",
        "timestamp": "01:15",
        "confidence": "high",
        "verifiable": true
      },
      {
        "claim_id": "CLM_2",
        "statement": "Legal team has sent cease and desist letters",
        "source_id": "SRC_2",
        "speaker": "MainChannel creator",
        "timestamp": "08:30",
        "confidence": "medium",
        "verifiable": true
      },
      {
        "claim_id": "CLM_3",
        "statement": "Multiple witnesses support the allegations",
        "source_id": "SRC_1",
        "speaker": null,
        "timestamp": "~11:20",
        "confidence": "low",
        "verifiable": true
      }
    ],
    "entities": [],
    "timestamps": []
  },
  "corpus_stats": {
    "total_sources": 3,
    "sources_by_mode": {
      "transcript_grounded": 1,
      "caption_grounded": 1,
      "video_only": 1,
      "text_provided": 0,
      "ocr_extracted": 0,
      "article_fetched": 0
    },
    "total_quotes": 3,
    "total_observations": 3,
    "total_claims": 3,
    "total_duration_seconds": 1882
  }
}
```

### Key Degradation Indicators in Doc 0

1. **Source status: "partial"** — Not all sources fully analyzed
2. **`video_only` mode present** — One source has no transcript
3. **`failure_log` populated** — Shows what was tried
4. **`observations` array used** — Instead of quotes for SRC_1
5. **`degradation_notes` on sources** — Explicit about limitations
6. **Mixed confidence ceilings** — LOW, HIGH, MEDIUM

---

## Doc 1 — Jump-Start Directions (Degraded)

```json
{
  "document_type": "jump_start_directions",
  "document_version": "2.0",
  "job_id": "job_degraded_example",
  "generated_at": "2026-01-13T10:00:00Z",
  "scope_lock": {
    "topic": "TikTok controversy involving MainChannel creator",
    "boundaries": "Limited to the three video sources provided. One source (SRC_1) analyzed without transcript.",
    "not_about": ["Unrelated creator controversies", "Platform policies"]
  },
  "corpus_coverage": {
    "summary": "Analysis covers three perspectives but is LIMITED by transcript availability. Only one source (SRC_2) provides high-confidence data. SRC_1 observations are approximate only.",
    "sources_analyzed": 3,
    "high_confidence_sources": 1,
    "perspectives_represented": [
      "Accused party's response (SRC_2 - HIGH confidence)",
      "News recap perspective (SRC_3 - MEDIUM confidence)",
      "Drama commentary perspective (SRC_1 - LOW confidence, no transcript)"
    ],
    "perspectives_missing": [
      "Original accuser's statement",
      "Alleged witnesses",
      "Platform/TikTok response",
      "Independent fact-checker analysis"
    ]
  },
  "gaps": [
    {
      "gap_id": "GAP_1",
      "description": "No transcript for SRC_1 - claims about 'witnesses' cannot be verified",
      "importance": "high",
      "category": "verification",
      "would_answer": "What exactly did DramaChannel claim, and what evidence did they show?",
      "suggested_source_types": ["Manual transcript of SRC_1", "DramaChannel's written post"]
    },
    {
      "gap_id": "GAP_2",
      "description": "Original accuser's statement not in corpus",
      "importance": "high",
      "category": "perspective",
      "would_answer": "What specific allegations were made and by whom?",
      "suggested_source_types": ["Original TikTok", "Accuser's follow-up posts"]
    },
    {
      "gap_id": "GAP_3",
      "description": "Witness claims mentioned in SRC_1 but unverified",
      "importance": "high",
      "category": "factual",
      "would_answer": "Do these witnesses exist and what did they say?",
      "suggested_source_types": ["Witness statements", "News interviews"]
    },
    {
      "gap_id": "GAP_4",
      "description": "Documentation mentioned in SRC_2 not shown",
      "importance": "medium",
      "category": "verification",
      "would_answer": "What documentation does MainChannel have?",
      "suggested_source_types": ["Screenshots if released", "Legal filings"]
    },
    {
      "gap_id": "GAP_5",
      "description": "Timeline of events not fully established",
      "importance": "medium",
      "category": "timeline",
      "would_answer": "When did each event occur?",
      "suggested_source_types": ["Social media archives", "News reports with dates"]
    }
  ],
  "open_questions": [
    {
      "question": "What did DramaChannel's video actually claim? (transcript unavailable)",
      "why_unanswered": "SRC_1 analyzed in video_only mode - only visual observations available",
      "related_gaps": ["GAP_1"]
    },
    {
      "question": "Who are the alleged witnesses and what did they say?",
      "why_unanswered": "Only mentioned in SRC_1 (low confidence), no direct statements in corpus",
      "related_gaps": ["GAP_3"]
    },
    {
      "question": "What documentation does MainChannel claim to have?",
      "why_unanswered": "Mentioned but not shown in SRC_2",
      "related_gaps": ["GAP_4"]
    }
  ],
  "research_directions": [
    {
      "direction_id": "RD_1",
      "title": "Manual transcript of SRC_1",
      "description": "Watch DramaChannel video and manually transcribe key claims. This would upgrade SRC_1 from LOW to MEDIUM confidence.",
      "priority": "high",
      "effort_estimate": "moderate",
      "addresses_gaps": ["GAP_1"],
      "suggested_sources": ["Re-watch SRC_1 video"],
      "search_queries": []
    },
    {
      "direction_id": "RD_2",
      "title": "Find original accusation",
      "description": "Locate the original TikTok or statement that started the controversy.",
      "priority": "high",
      "effort_estimate": "quick",
      "addresses_gaps": ["GAP_2"],
      "suggested_sources": ["TikTok", "Twitter/X", "Reddit threads"],
      "search_queries": [
        "MainChannel controversy original TikTok",
        "MainChannel allegations January 2026"
      ]
    },
    {
      "direction_id": "RD_3",
      "title": "Verify witness claims",
      "description": "Search for any public statements from alleged witnesses.",
      "priority": "high",
      "effort_estimate": "moderate",
      "addresses_gaps": ["GAP_3"],
      "suggested_sources": ["Twitter/X", "TikTok", "News articles"],
      "search_queries": [
        "MainChannel witnesses speak out",
        "MainChannel controversy corroboration"
      ]
    }
  ],
  "verification_checklist": [
    {
      "item": "January 8th TikTok post date (claimed by SRC_2)",
      "status": "unverified",
      "source_for_verification": "Original TikTok post",
      "importance": "medium"
    },
    {
      "item": "Cease and desist letters sent (claimed by SRC_2)",
      "status": "unverified",
      "source_for_verification": "Legal documents or recipient confirmation",
      "importance": "medium"
    },
    {
      "item": "3 witnesses exist (claimed in SRC_1)",
      "status": "unverified",
      "source_for_verification": "Witness statements or identification",
      "importance": "high"
    }
  ],
  "top_three_next_steps": [
    {
      "step": "Manually transcribe SRC_1 to recover lost context",
      "rationale": "One-third of corpus is LOW confidence due to missing transcript",
      "addresses": "GAP_1, improves overall corpus quality"
    },
    {
      "step": "Find and analyze the original accusation TikTok",
      "rationale": "Cannot evaluate response without knowing what's being responded to",
      "addresses": "GAP_2"
    },
    {
      "step": "Search for witness statements or identification",
      "rationale": "Key factual claim (witnesses exist) is currently unverified LOW confidence",
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

### Key Degradation Indicators in Doc 1

1. **Scope lock mentions limitation** — "One source analyzed without transcript"
2. **Coverage summary flags issue** — "LIMITED by transcript availability"
3. **Perspectives note confidence levels** — "(LOW confidence, no transcript)"
4. **First gap is about missing transcript** — GAP_1 directly addresses degradation
5. **First next step is to fix degradation** — "Manually transcribe SRC_1"
6. **Open questions reference video_only mode**

---

## Doc 2 — Semantic Research Brief (Degraded)

```json
{
  "document_type": "semantic_research_brief",
  "document_version": "2.0",
  "job_id": "job_degraded_example",
  "generated_at": "2026-01-13T10:00:00Z",
  "executive_summary": {
    "one_sentence": "An unfolding controversy with conflicting claims, significantly limited by incomplete source analysis.",
    "three_sentences": "MainChannel creator has issued a denial and announced legal action in response to unspecified allegations. A drama commentary channel (analyzed without transcript) appears to present counter-evidence including alleged witness claims. Due to transcript failures, one-third of the source material could only be analyzed through visual observation, limiting confidence in the full picture.",
    "key_takeaway": "The accused party's response is well-documented (HIGH confidence), but the accusation side is poorly represented in this corpus (one LOW confidence source, original accuser missing entirely)."
  },
  "confidence_assessment": {
    "overall_confidence": "low",
    "confidence_rationale": "Only 1 of 3 sources provides high-confidence data. Critical perspective (SRC_1) limited to visual observations. Original accusation not in corpus.",
    "high_confidence_claims": 2,
    "medium_confidence_claims": 3,
    "low_confidence_claims": 4,
    "limiting_factors": [
      "SRC_1 transcript unavailable - video_only analysis",
      "Original accusation not included in sources",
      "Witness claims unverified",
      "Auto-captions in SRC_3 may contain errors"
    ]
  },
  "themes": [
    {
      "theme_id": "THEME_1",
      "name": "Contested Narrative",
      "description": "Two incompatible versions of events are being presented, but one side is poorly documented in this corpus.",
      "prevalence": "dominant",
      "source_ids": ["SRC_1", "SRC_2"],
      "supporting_key_points": ["KP_1", "KP_2"],
      "supporting_quotes": ["QT_1"]
    },
    {
      "theme_id": "THEME_2",
      "name": "Legal Escalation",
      "description": "MainChannel is pursuing legal remedies, suggesting high stakes.",
      "prevalence": "significant",
      "source_ids": ["SRC_2"],
      "supporting_key_points": ["KP_3"],
      "supporting_quotes": ["QT_2"]
    }
  ],
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "MainChannel creator explicitly denies the allegations and claims context was removed",
      "source_ids": ["SRC_2"],
      "confidence": "high",
      "timestamp": "02:34",
      "supporting_evidence": {
        "quotes": ["QT_1"],
        "observations": [],
        "claims": ["CLM_1"]
      },
      "contested_by": ["SRC_1"]
    },
    {
      "key_point_id": "KP_2",
      "statement": "DramaChannel video appears to show screenshots of alleged evidence (content not legible in video_only analysis)",
      "source_ids": ["SRC_1"],
      "confidence": "low",
      "timestamp": "~04:30",
      "supporting_evidence": {
        "quotes": [],
        "observations": ["OBS_1"],
        "claims": []
      },
      "contested_by": []
    },
    {
      "key_point_id": "KP_3",
      "statement": "Legal action has been initiated including cease and desist letters",
      "source_ids": ["SRC_2"],
      "confidence": "medium",
      "timestamp": "08:30",
      "supporting_evidence": {
        "quotes": ["QT_2"],
        "observations": [],
        "claims": ["CLM_2"]
      },
      "contested_by": []
    },
    {
      "key_point_id": "KP_4",
      "statement": "Multiple witnesses allegedly support the accusations (unverified)",
      "source_ids": ["SRC_1"],
      "confidence": "low",
      "timestamp": "~11:20",
      "supporting_evidence": {
        "quotes": [],
        "observations": ["OBS_3"],
        "claims": ["CLM_3"]
      },
      "contested_by": []
    },
    {
      "key_point_id": "KP_5",
      "statement": "News recap suggests timeline inconsistencies exist in the accusations",
      "source_ids": ["SRC_3"],
      "confidence": "medium",
      "timestamp": "03:45",
      "supporting_evidence": {
        "quotes": ["QT_3"],
        "observations": [],
        "claims": []
      },
      "contested_by": []
    }
  ],
  "tensions": [
    {
      "tension_id": "TEN_1",
      "description": "Fundamental disagreement about whether allegations are true",
      "nature": "factual_dispute",
      "sources_involved": ["SRC_1", "SRC_2"],
      "position_a": {
        "summary": "Allegations are false, taken out of context",
        "source_ids": ["SRC_2"],
        "supporting_evidence": ["KP_1", "QT_1"]
      },
      "position_b": {
        "summary": "Evidence and witnesses support allegations (LOW CONFIDENCE - no transcript)",
        "source_ids": ["SRC_1"],
        "supporting_evidence": ["KP_2", "KP_4", "OBS_1", "OBS_3"]
      },
      "resolution_status": "unresolved",
      "resolution_notes": "Cannot fully evaluate SRC_1's claims due to video_only analysis mode"
    }
  ],
  "assumptions": [
    {
      "assumption": "Visual observations from SRC_1 accurately represent video content",
      "source_ids": ["SRC_1"],
      "explicit_or_implicit": "implicit",
      "impact_if_wrong": "Key claims about evidence and witnesses may be mischaracterized"
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
    "sources_agree_on": [
      "A controversy exists",
      "MainChannel has responded"
    ],
    "sources_disagree_on": [
      "Whether allegations have merit",
      "Whether evidence supports accusations"
    ],
    "single_source_claims": [
      "Legal action initiated (SRC_2 only)",
      "Witnesses exist (SRC_1 only, LOW confidence)"
    ]
  }
}
```

### Key Degradation Indicators in Doc 2

1. **Executive summary mentions limitation** — "significantly limited by incomplete source analysis"
2. **Overall confidence: LOW** — Explicit downgrade
3. **Confidence rationale explains why** — "Only 1 of 3 sources provides high-confidence data"
4. **Limiting factors listed** — Transcript unavailable, auto-captions, etc.
5. **Key points show mixed confidence** — KP_2 and KP_4 are LOW
6. **Tension notes confidence issue** — "LOW CONFIDENCE - no transcript"
7. **Assumptions section flags risk** — "Visual observations... may be mischaracterized"
8. **Single source claims identified** — Shows what can't be corroborated

---

## Job Warnings (What Gets Surfaced to User)

```json
{
  "job_id": "job_degraded_example",
  "status": "completed_with_warnings",
  "warnings": [
    {
      "type": "transcript_failure",
      "source_id": "SRC_1",
      "message": "All transcript acquisition methods failed. Source analyzed in video_only mode with LOW confidence ceiling.",
      "impact": "Quotes unavailable. Only visual observations extracted.",
      "suggestion": "Consider manual transcription or finding alternative source."
    },
    {
      "type": "caption_quality",
      "source_id": "SRC_3",
      "message": "Using auto-generated YouTube captions. Transcription errors likely.",
      "impact": "Quotes may contain errors. Timestamps approximate.",
      "suggestion": "Verify critical quotes against video."
    },
    {
      "type": "confidence_imbalance",
      "source_id": null,
      "message": "Corpus confidence is imbalanced: 1 HIGH, 1 MEDIUM, 1 LOW.",
      "impact": "Analysis may over-represent high-confidence sources.",
      "suggestion": "Add more high-quality sources for balanced analysis."
    }
  ]
}
```

---

## What Makes This Valid Despite Degradation

1. **Explicit about limitations** — Never hides what went wrong
2. **Confidence levels accurate** — LOW where appropriate
3. **Observations instead of quotes** — Correct format for video_only
4. **Gaps prioritize fixing degradation** — First gap is about missing transcript
5. **Next steps address limitations** — Suggests manual transcription
6. **No hallucinated content** — Doesn't invent quotes that weren't captured
7. **Still actionable** — User knows exactly what to do next

---

## Anti-Patterns (What Would Be WRONG)

❌ **Hiding the failure:**
```json
"transcript_provenance": {
  "method": "supadata",  // LIE - it failed
  "quality": "high"
}
```

❌ **Inventing quotes for video_only source:**
```json
"quotes": [
  {
    "text": "The evidence is clear",  // HALLUCINATED
    "source_id": "SRC_1"  // video_only mode - quotes not allowed
  }
]
```

❌ **Overstating confidence:**
```json
"confidence": "high"  // WRONG - source ceiling is LOW
```

❌ **Not flagging single-source claims:**
```json
"key_points": [
  {
    "statement": "Witnesses exist",
    "confidence": "medium"  // WRONG - should be LOW, should note single source
  }
]
```

---

**END OF EXAMPLE**
