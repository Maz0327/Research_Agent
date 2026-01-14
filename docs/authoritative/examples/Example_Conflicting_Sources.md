# Example: Conflicting Sources

**Purpose:** Canonical example of how to handle sources that contradict each other.
**Key Point:** The system surfaces conflicts, it does not resolve them. That's the human's job.

---

## Scenario

**Topic:** Did a tech CEO make a specific promise about product pricing at a 2025 conference?

**Sources:**
- SRC_1: Official company keynote recording (transcript_grounded, HIGH)
- SRC_2: Tech journalist's analysis video (transcript_grounded, HIGH)
- SRC_3: Attendee's vlog from the event (caption_grounded, MEDIUM)
- SRC_4: Company press release (article_fetched, HIGH)

**The Conflict:** Sources directly contradict each other on what was promised.

---

## The Factual Dispute

| Source | Claim | Confidence |
|--------|-------|------------|
| SRC_1 (Keynote) | "Pricing will remain unchanged for existing customers" | HIGH |
| SRC_2 (Journalist) | "CEO clearly said grandfathered pricing would end in 2026" | HIGH |
| SRC_3 (Attendee) | "I heard him say prices were going up for everyone" | MEDIUM |
| SRC_4 (Press Release) | No mention of pricing at all | HIGH |

---

## Doc 0 — Source Ledger (Relevant Excerpts)

```json
{
  "document_type": "source_ledger",
  "document_version": "2.0",
  "job_id": "job_conflict_example",
  "generated_at": "2026-01-13T12:00:00Z",
  "sources": [
    {
      "source_id": "SRC_1",
      "source_type": "youtube",
      "analysis_mode": "transcript_grounded",
      "confidence_ceiling": "high",
      "metadata": {
        "title": "TechCorp Annual Keynote 2025 - Full Recording",
        "creator": "TechCorp Official",
        "date": "2025-09-15"
      },
      "skim_summary": "Official recording of CEO keynote. Discusses product roadmap, pricing changes, and customer commitments.",
      "status": "complete"
    },
    {
      "source_id": "SRC_2",
      "source_type": "youtube",
      "analysis_mode": "transcript_grounded",
      "confidence_ceiling": "high",
      "metadata": {
        "title": "TechCorp Keynote Analysis - What They ACTUALLY Said",
        "creator": "TechReview Channel",
        "date": "2025-09-16"
      },
      "skim_summary": "Journalist analysis of keynote with clips. Claims CEO made pricing commitment that contradicts company messaging.",
      "status": "complete"
    },
    {
      "source_id": "SRC_3",
      "source_type": "youtube",
      "analysis_mode": "caption_grounded",
      "confidence_ceiling": "medium",
      "metadata": {
        "title": "I Was There! TechCorp Keynote Vlog",
        "creator": "TechFan Sarah",
        "date": "2025-09-15"
      },
      "skim_summary": "Attendee perspective from audience. Reports what she heard but audio quality poor in her recording.",
      "status": "complete"
    },
    {
      "source_id": "SRC_4",
      "source_type": "article",
      "analysis_mode": "article_fetched",
      "confidence_ceiling": "high",
      "metadata": {
        "title": "TechCorp Announces Product Updates at Annual Conference",
        "creator": "TechCorp PR",
        "date": "2025-09-15"
      },
      "skim_summary": "Official press release covering keynote announcements. Notably omits any mention of pricing.",
      "status": "complete"
    }
  ],
  "indexes": {
    "quotes": [
      {
        "quote_id": "QT_1",
        "text": "For our existing customers, I want to be crystal clear: your pricing will remain unchanged. That's our commitment to you.",
        "source_id": "SRC_1",
        "speaker": "CEO",
        "timestamp": "34:22",
        "timestamp_seconds": 2062,
        "verification_status": "verified"
      },
      {
        "quote_id": "QT_2",
        "text": "Now, for new customers joining after January 2026, we will have updated pricing that reflects our expanded capabilities.",
        "source_id": "SRC_1",
        "speaker": "CEO",
        "timestamp": "34:45",
        "timestamp_seconds": 2085,
        "verification_status": "verified"
      },
      {
        "quote_id": "QT_3",
        "text": "If you listen carefully at the 34 minute mark, he says grandfathered pricing is ending. That's a complete reversal from last year.",
        "source_id": "SRC_2",
        "speaker": "Journalist",
        "timestamp": "05:30",
        "timestamp_seconds": 330,
        "verification_status": "verified"
      },
      {
        "quote_id": "QT_4",
        "text": "He definitely said prices are going up. I was sitting in the third row and heard it clearly.",
        "source_id": "SRC_3",
        "speaker": "Attendee",
        "timestamp": "02:15",
        "timestamp_seconds": 135,
        "verification_status": "partial"
      }
    ],
    "claims": [
      {
        "claim_id": "CLM_1",
        "statement": "Existing customer pricing will remain unchanged",
        "source_id": "SRC_1",
        "speaker": "CEO",
        "confidence": "high",
        "verifiable": true
      },
      {
        "claim_id": "CLM_2",
        "statement": "New customer pricing will increase starting January 2026",
        "source_id": "SRC_1",
        "speaker": "CEO",
        "confidence": "high",
        "verifiable": true
      },
      {
        "claim_id": "CLM_3",
        "statement": "Grandfathered pricing is ending",
        "source_id": "SRC_2",
        "speaker": "Journalist (interpreting CEO)",
        "confidence": "high",
        "verifiable": true
      },
      {
        "claim_id": "CLM_4",
        "statement": "Prices are going up for everyone",
        "source_id": "SRC_3",
        "speaker": "Attendee",
        "confidence": "medium",
        "verifiable": true
      }
    ]
  }
}
```

---

## Doc 2 — Semantic Research Brief (Conflict Handling)

```json
{
  "document_type": "semantic_research_brief",
  "document_version": "2.0",
  "job_id": "job_conflict_example",
  "generated_at": "2026-01-13T12:00:00Z",
  "executive_summary": {
    "one_sentence": "Sources directly conflict on whether TechCorp's CEO promised pricing protection for existing customers.",
    "three_sentences": "The official keynote recording (SRC_1) contains an explicit commitment that existing customer pricing 'will remain unchanged.' However, a tech journalist (SRC_2) interprets the same speech as announcing the end of grandfathered pricing, and an attendee (SRC_3) recalls hearing that prices would increase for everyone. The official press release (SRC_4) notably omits any mention of pricing, which could support either interpretation.",
    "key_takeaway": "There is a factual dispute that requires direct verification against the primary source recording. The conflict may stem from interpretation differences or selective quoting."
  },
  "confidence_assessment": {
    "overall_confidence": "medium",
    "confidence_rationale": "High-quality sources are available, but they directly contradict each other on a key factual claim. Confidence in any single interpretation is reduced by the conflict.",
    "high_confidence_claims": 4,
    "medium_confidence_claims": 2,
    "low_confidence_claims": 0,
    "limiting_factors": [
      "Direct factual contradiction between sources",
      "Journalist interpretation may differ from literal statement",
      "Attendee recall may be inaccurate (noisy environment)",
      "Press release omission is ambiguous"
    ]
  },
  "themes": [
    {
      "theme_id": "THEME_1",
      "name": "Pricing Communication Confusion",
      "description": "Multiple interpretations of the same event suggest either ambiguous communication or selective hearing.",
      "prevalence": "dominant",
      "source_ids": ["SRC_1", "SRC_2", "SRC_3"],
      "supporting_key_points": ["KP_1", "KP_2", "KP_3"],
      "supporting_quotes": ["QT_1", "QT_3", "QT_4"]
    },
    {
      "theme_id": "THEME_2",
      "name": "Official vs. Interpreted Messaging",
      "description": "Gap between what company officially states and how observers interpret it.",
      "prevalence": "significant",
      "source_ids": ["SRC_1", "SRC_2", "SRC_4"],
      "supporting_key_points": ["KP_1", "KP_2", "KP_4"],
      "supporting_quotes": ["QT_1", "QT_2", "QT_3"]
    }
  ],
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "CEO explicitly stated existing customer pricing 'will remain unchanged'",
      "source_ids": ["SRC_1"],
      "confidence": "high",
      "timestamp": "34:22",
      "supporting_evidence": {
        "quotes": ["QT_1"],
        "observations": [],
        "claims": ["CLM_1"]
      },
      "contested_by": ["SRC_2", "SRC_3"]
    },
    {
      "key_point_id": "KP_2",
      "statement": "Tech journalist claims CEO announced end of grandfathered pricing",
      "source_ids": ["SRC_2"],
      "confidence": "high",
      "timestamp": "05:30",
      "supporting_evidence": {
        "quotes": ["QT_3"],
        "observations": [],
        "claims": ["CLM_3"]
      },
      "contested_by": ["SRC_1"]
    },
    {
      "key_point_id": "KP_3",
      "statement": "Event attendee recalls hearing prices would increase for everyone",
      "source_ids": ["SRC_3"],
      "confidence": "medium",
      "timestamp": "02:15",
      "supporting_evidence": {
        "quotes": ["QT_4"],
        "observations": [],
        "claims": ["CLM_4"]
      },
      "contested_by": ["SRC_1"]
    },
    {
      "key_point_id": "KP_4",
      "statement": "Official press release omits all mention of pricing",
      "source_ids": ["SRC_4"],
      "confidence": "high",
      "timestamp": null,
      "supporting_evidence": {
        "quotes": [],
        "observations": [],
        "claims": []
      },
      "contested_by": []
    },
    {
      "key_point_id": "KP_5",
      "statement": "CEO announced new customer pricing would change starting January 2026",
      "source_ids": ["SRC_1"],
      "confidence": "high",
      "timestamp": "34:45",
      "supporting_evidence": {
        "quotes": ["QT_2"],
        "observations": [],
        "claims": ["CLM_2"]
      },
      "contested_by": []
    }
  ],
  "tensions": [
    {
      "tension_id": "TEN_1",
      "description": "Direct factual conflict: Did CEO promise pricing protection for existing customers or announce prices are increasing?",
      "nature": "factual_dispute",
      "sources_involved": ["SRC_1", "SRC_2", "SRC_3"],
      "position_a": {
        "summary": "Existing customer pricing will remain unchanged (explicit verbal commitment)",
        "source_ids": ["SRC_1"],
        "supporting_evidence": ["KP_1", "QT_1", "CLM_1"]
      },
      "position_b": {
        "summary": "Grandfathered/existing pricing is ending, prices going up",
        "source_ids": ["SRC_2", "SRC_3"],
        "supporting_evidence": ["KP_2", "KP_3", "QT_3", "QT_4", "CLM_3", "CLM_4"]
      },
      "resolution_status": "unresolved",
      "resolution_notes": "Primary source (SRC_1) appears to support Position A with direct quote. Position B may stem from misinterpretation of the 'new customer' pricing change announcement. Recommend re-watching 34:00-35:00 of SRC_1 to verify."
    },
    {
      "tension_id": "TEN_2",
      "description": "Press release omission: strategic ambiguity or irrelevant detail?",
      "nature": "perspective_difference",
      "sources_involved": ["SRC_1", "SRC_4"],
      "position_a": {
        "summary": "Pricing wasn't mentioned because it's not changing for existing customers (supports Position A of TEN_1)",
        "source_ids": ["SRC_1"],
        "supporting_evidence": ["KP_1"]
      },
      "position_b": {
        "summary": "Pricing was omitted to avoid controversy about changes (supports Position B of TEN_1)",
        "source_ids": [],
        "supporting_evidence": []
      },
      "resolution_status": "unresolved",
      "resolution_notes": "Position B is speculative - no source directly claims this. Included because omission is notable and could support multiple interpretations."
    }
  ],
  "assumptions": [
    {
      "assumption": "The official keynote recording (SRC_1) is complete and unedited",
      "source_ids": ["SRC_1"],
      "explicit_or_implicit": "implicit",
      "impact_if_wrong": "If edited, the 'unchanged pricing' quote might be out of context"
    },
    {
      "assumption": "Journalist (SRC_2) is reporting in good faith, not deliberately misleading",
      "source_ids": ["SRC_2"],
      "explicit_or_implicit": "implicit",
      "impact_if_wrong": "Conflict might be manufactured rather than genuine misunderstanding"
    },
    {
      "assumption": "Attendee (SRC_3) is recalling accurately despite noisy environment",
      "source_ids": ["SRC_3"],
      "explicit_or_implicit": "implicit",
      "impact_if_wrong": "Her account may simply be wrong"
    }
  ],
  "gaps_summary": {
    "total_gaps": 4,
    "critical_gaps": ["GAP_1"],
    "see_doc_1_for_details": true
  },
  "speculation_section": {
    "included": true,
    "speculation_items": [
      {
        "speculation": "The conflict may stem from confusion between 'existing customers' and 'grandfathered pricing' - these might be different customer segments",
        "basis": "SRC_1 uses 'existing customers' while SRC_2 uses 'grandfathered pricing' - potentially different categories",
        "confidence": "low",
        "explicitly_speculative": true
      },
      {
        "speculation": "Journalist may have conflated the 'new customer pricing changes' announcement with existing customer treatment",
        "basis": "SRC_1 quotes show two separate statements about existing vs new customers, closely timed",
        "confidence": "low",
        "explicitly_speculative": true
      }
    ]
  },
  "source_concordance": {
    "sources_agree_on": [
      "A keynote occurred on September 15, 2025",
      "Pricing was discussed",
      "Some kind of change is happening"
    ],
    "sources_disagree_on": [
      "Whether existing customer pricing is protected",
      "What exactly the CEO committed to"
    ],
    "single_source_claims": [
      "Explicit 'pricing unchanged' quote (SRC_1 only)",
      "'Grandfathered pricing ending' interpretation (SRC_2 only)"
    ]
  }
}
```

---

## Doc 1 — Jump-Start (Conflict-Focused Gaps)

```json
{
  "gaps": [
    {
      "gap_id": "GAP_1",
      "description": "Need to verify exact wording at 34:00-35:00 mark of keynote - this is the crux of the factual dispute",
      "importance": "high",
      "category": "verification",
      "would_answer": "What exactly did the CEO say, word-for-word?",
      "suggested_source_types": ["Re-watch SRC_1 primary source"]
    },
    {
      "gap_id": "GAP_2",
      "description": "Definition of 'existing customers' vs 'grandfathered pricing' - are these the same thing?",
      "importance": "high",
      "category": "factual",
      "would_answer": "Is there a customer segment distinction being missed?",
      "suggested_source_types": ["TechCorp pricing documentation", "Customer support clarification"]
    },
    {
      "gap_id": "GAP_3",
      "description": "Has TechCorp issued any clarification since the keynote?",
      "importance": "medium",
      "category": "context",
      "would_answer": "Did the company address the confusion?",
      "suggested_source_types": ["Company blog", "Twitter/X", "Support documentation"]
    },
    {
      "gap_id": "GAP_4",
      "description": "Other attendee perspectives - does anyone corroborate SRC_3's recollection?",
      "importance": "medium",
      "category": "verification",
      "would_answer": "Is the attendee's memory reliable?",
      "suggested_source_types": ["Other vlogs from event", "Reddit discussions"]
    }
  ],
  "top_three_next_steps": [
    {
      "step": "Re-watch SRC_1 from 33:00-36:00 and transcribe exact wording",
      "rationale": "The primary source should definitively resolve the factual dispute",
      "addresses": "GAP_1, TEN_1"
    },
    {
      "step": "Search for TechCorp's definition of 'existing' vs 'grandfathered' customers",
      "rationale": "The conflict may be semantic - different customer categories",
      "addresses": "GAP_2"
    },
    {
      "step": "Check if TechCorp has issued any clarification post-keynote",
      "rationale": "Company may have already addressed the confusion",
      "addresses": "GAP_3"
    }
  ]
}
```

---

## What This Example Demonstrates

### 1. Tensions Are Surfaced, Not Resolved

The system does NOT say "SRC_1 is right and SRC_2 is wrong." It:
- Documents both positions with evidence
- Notes which position has stronger sourcing
- Leaves resolution to the human

### 2. Contested_by Field Shows Conflicts

```json
{
  "key_point_id": "KP_1",
  "statement": "CEO explicitly stated existing customer pricing 'will remain unchanged'",
  "source_ids": ["SRC_1"],
  "confidence": "high",
  "contested_by": ["SRC_2", "SRC_3"]  // ← Shows who disagrees
}
```

### 3. Confidence Reflects Uncertainty

Even though individual claims are HIGH confidence, the overall brief is MEDIUM because:
> "High-quality sources are available, but they directly contradict each other"

### 4. Speculation Is Labeled

The system offers possible explanations for the conflict, but marks them clearly:
```json
{
  "speculation": "The conflict may stem from confusion between...",
  "confidence": "low",
  "explicitly_speculative": true
}
```

### 5. Source Concordance Highlights Agreement/Disagreement

```json
"source_concordance": {
  "sources_agree_on": ["A keynote occurred", "Pricing was discussed"],
  "sources_disagree_on": ["Whether existing customer pricing is protected"],
  "single_source_claims": ["Explicit 'pricing unchanged' quote (SRC_1 only)"]
}
```

### 6. Gaps Focus on Resolving Conflict

The first recommended action is to verify the primary source that could resolve the dispute.

---

## Anti-Patterns (What Would Be WRONG)

❌ **Picking a winner:**
```json
"executive_summary": {
  "key_takeaway": "The CEO promised pricing protection. The journalist is wrong."
}
```

❌ **Hiding the conflict:**
```json
"tensions": []  // Pretending there's no disagreement
```

❌ **Averaging the positions:**
```json
"key_point": "CEO probably said something about pricing that people interpreted differently"
// Too vague, loses the specific claims
```

❌ **Speculating without labeling:**
```json
"key_point": "The journalist misheard the CEO"
// This is speculation presented as fact
```

❌ **Downgrading confidence without reason:**
```json
{
  "statement": "CEO explicitly stated pricing unchanged",
  "source_ids": ["SRC_1"],
  "confidence": "low"  // WRONG - the quote is verified, confidence should be high
}
// The KEY POINT confidence stays high; the OVERALL BRIEF confidence accounts for conflict
```

---

## Correct Confidence Handling in Conflicts

| Level | What Gets This Confidence |
|-------|---------------------------|
| Individual claim | Based on source quality and verification |
| Key point | Based on supporting evidence |
| Overall brief | Reduced if major unresolved conflicts exist |

A verified quote from a high-confidence source is still HIGH confidence, even if another source disagrees. The disagreement is captured in:
- `contested_by` field
- `tensions` array
- `source_concordance`
- `confidence_assessment.limiting_factors`
- Overall brief confidence rationale

---

**END OF EXAMPLE**
