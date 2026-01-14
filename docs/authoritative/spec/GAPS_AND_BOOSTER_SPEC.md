# Research Agent — Gaps, Weaknesses & Deep Research Booster Specification

**Purpose**: This document identifies what's missing from the current system specification and provides complete specifications for addressing those gaps, including the Deep Research Booster component.

**Status**: DRAFT — Pending user approval before integration into main context document

**Date**: 2026-01-12

---

# PART 1: IDENTIFIED GAPS & WEAKNESSES

The following gaps were identified after reviewing the complete specification and example set. Each gap represents a potential source of implementation drift, hallucination, or incorrect output.

---

## GAP 1: No Example for Multi-Source Synthesis

### Problem
Current examples cover:
- Degraded output (video_only mode)
- Thin output (limited sources)
- Conflicting sources (contradictions)

But there is **no example showing correct synthesis across 4-5 good sources**.

### Risk
Gemini doesn't know what "correct rich output" looks like — only what "degraded output" looks like. This biases the model toward thin, cautious output even when rich output is appropriate.

### Required Fix
Add a "Full Successful Extraction" example with multiple sources showing:
- How themes span sources (THEME_1 supported by KP from SRC_1, SRC_3, SRC_4)
- How confidence increases with corroboration
- What a properly dense Doc 2 looks like
- Proper cross-referencing between sources

### Example Structure Needed
```markdown
## Full Successful Multi-Source Example

**Scenario:** 4 sources provided (2 YouTube videos, 1 article, 1 thread). 
All transcripts available. Multiple perspectives represented.

**Confidence:** High (multiple corroborating sources, verified quotes)

### Source Manifest
- SRC_1: YouTube interview with Creator X (transcript_grounded)
- SRC_2: YouTube commentary by Analyst Y (transcript_grounded)  
- SRC_3: News article from Publication Z (full text)
- SRC_4: Reddit thread with primary source links (full text)

### Theme Example (Cross-Source)
THEME_1: Shifting Accountability
- Supported by: KP_1 (SRC_1), KP_4 (SRC_2), KP_7 (SRC_3)
- Confidence: High (3 independent sources)

### Key Point Example (Corroborated)
KP_1: Creator X changed explanation of Event Y between March and June
- Sources: SRC_1 (14:32), SRC_3 (paragraph 4)
- Confidence: High (verified quotes from both sources match)
```

---

## GAP 2: No Explicit JSON Schema Examples

### Problem
All examples are in markdown format. Gemini outputs JSON. There's a translation gap between "what we show" and "what Gemini produces."

### Risk
Gemini might structure JSON differently than expected, causing:
- Parsing failures
- Missing required fields
- Incorrect nesting
- Type mismatches

### Required Fix
Add complete JSON output examples for SemanticExtractionResult in both modes.

### JSON Example: transcript_grounded Mode

```json
{
  "source_id": "SRC_1",
  "analysis_mode": "transcript_grounded",
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "Creator X changed their explanation of Event Y between March and June",
      "source_ids": ["SRC_1"],
      "confidence": "high",
      "supporting_claims": ["CLM_1", "CLM_2"]
    },
    {
      "key_point_id": "KP_2",
      "statement": "The timeline provided in the March statement conflicts with documented events",
      "source_ids": ["SRC_1"],
      "confidence": "high",
      "supporting_claims": ["CLM_3"]
    }
  ],
  "claims": [
    {
      "claim_id": "CLM_1",
      "statement": "In March, Creator X stated the decision was voluntary",
      "source_id": "SRC_1",
      "supporting_quotes": ["QT_1"]
    },
    {
      "claim_id": "CLM_2",
      "statement": "In June, Creator X stated there was external pressure",
      "source_id": "SRC_1",
      "supporting_quotes": ["QT_2"]
    },
    {
      "claim_id": "CLM_3",
      "statement": "Creator X claims Event Y occurred in early 2023",
      "source_id": "SRC_1",
      "supporting_quotes": ["QT_3"]
    }
  ],
  "themes": [
    {
      "theme_id": "THEME_1",
      "label": "Shifting Accountability",
      "description": "The framing of responsibility changes over time from voluntary to coerced",
      "related_key_points": ["KP_1", "KP_2"]
    }
  ],
  "tensions": [
    {
      "tension_id": "TEN_1",
      "description": "March statement ('my choice') contradicts June statement ('I was pressured')",
      "involved_key_points": ["KP_1"]
    }
  ],
  "supporting_quotes": [
    {
      "quote_id": "QT_1",
      "text": "I made this choice on my own, nobody forced me to do anything",
      "source_id": "SRC_1",
      "timestamp": "14:32"
    },
    {
      "quote_id": "QT_2",
      "text": "There was a lot of pressure from multiple directions, I didn't feel like I had options",
      "source_id": "SRC_1",
      "timestamp": "47:15"
    },
    {
      "quote_id": "QT_3",
      "text": "This all started back in early 2023 when we first discussed the project",
      "source_id": "SRC_1",
      "timestamp": "8:44"
    }
  ],
  "observations": [],
  "confidence_ceiling": "high"
}
```

### JSON Example: video_only Mode

```json
{
  "source_id": "SRC_2",
  "analysis_mode": "video_only",
  "key_points": [
    {
      "key_point_id": "KP_3",
      "statement": "Speaker appears to discuss timeline inconsistencies",
      "source_ids": ["SRC_2"],
      "confidence": "low",
      "supporting_claims": []
    },
    {
      "key_point_id": "KP_4",
      "statement": "Speaker's demeanor shifts when discussing the March events",
      "source_ids": ["SRC_2"],
      "confidence": "low",
      "supporting_claims": []
    }
  ],
  "claims": [],
  "themes": [
    {
      "theme_id": "THEME_2",
      "label": "Narrative Discomfort",
      "description": "Observable shifts in speaker behavior when certain topics arise",
      "related_key_points": ["KP_3", "KP_4"]
    }
  ],
  "tensions": [],
  "supporting_quotes": [],
  "observations": [
    {
      "observation_id": "OBS_1",
      "description": "Speaker's tone becomes defensive when discussing March events",
      "source_id": "SRC_2",
      "approximate": true,
      "type": "observation",
      "timestamp_range": "~12:00-15:00"
    },
    {
      "observation_id": "OBS_2",
      "description": "Speaker pauses frequently when asked about timeline, suggesting uncertainty or discomfort",
      "source_id": "SRC_2",
      "approximate": true,
      "type": "observation",
      "timestamp_range": "~22:00-24:00"
    }
  ],
  "confidence_ceiling": "low"
}
```

---

## GAP 3: No "What Gemini Must NOT Output" Examples

### Problem
The specification tells Gemini what TO do but doesn't show what BAD output looks like.

### Risk
Gemini hallucinates in patterns not explicitly forbidden. Without negative examples, the model may produce technically-valid but semantically-wrong output.

### Required Fix
Add a "FORBIDDEN OUTPUT PATTERNS" section with explicit wrong/right comparisons.

### Forbidden Patterns Specification

```markdown
## FORBIDDEN OUTPUT PATTERNS

These patterns represent INCORRECT outputs that must be rejected or prevented.

---

### Pattern 1: Inventing Source Identity

Gemini must NEVER guess or infer which video/article is being analyzed.

❌ WRONG:
"Based on the video content, this appears to be from Creator X's March 2024 livestream where they discussed..."

✅ RIGHT:
Use only the source identity provided in the input. If metadata is incomplete, note: "Source title not provided in metadata."

**Why forbidden**: Source identity is resolved PRE-LLM. Gemini inferring identity could attribute quotes/claims to wrong sources.

---

### Pattern 2: Quotes in video_only Mode

When analysis_mode = "video_only", the supporting_quotes array MUST be empty.

❌ WRONG:
{
  "analysis_mode": "video_only",
  "supporting_quotes": [
    {"quote_id": "QT_1", "text": "I never said that", "timestamp": "14:32"}
  ]
}

✅ RIGHT:
{
  "analysis_mode": "video_only",
  "supporting_quotes": [],
  "observations": [
    {
      "observation_id": "OBS_1",
      "description": "Speaker appears to deny a previous statement",
      "approximate": true,
      "type": "observation",
      "timestamp_range": "~14:00-15:00"
    }
  ]
}

**Why forbidden**: Without transcript, there is no verbatim text. Presenting observations as quotes is hallucination.

---

### Pattern 3: High Confidence Without Corroboration

Single-source claims cannot be "high" confidence except with verbatim transcript quotes.

❌ WRONG:
{
  "key_point_id": "KP_1",
  "source_ids": ["SRC_1"],
  "confidence": "high"
}
(Single source, no indication of quote verification)

✅ RIGHT:
{
  "key_point_id": "KP_1",
  "source_ids": ["SRC_1"],
  "confidence": "medium",
  "supporting_claims": ["CLM_1"]
}
(Single source = medium max, unless verbatim quote from transcript_grounded source)

**Why forbidden**: High confidence implies verification. Single perspective cannot be verified.

---

### Pattern 4: Themes Without Key Point Support

Every theme must reference at least 2 key points.

❌ WRONG:
{
  "theme_id": "THEME_1",
  "label": "Financial Misconduct",
  "description": "There are signs of financial problems",
  "related_key_points": []
}

✅ RIGHT:
{
  "theme_id": "THEME_1",
  "label": "Financial Misconduct",
  "description": "Multiple sources reference unexplained financial decisions",
  "related_key_points": ["KP_2", "KP_5", "KP_8"]
}

**Why forbidden**: Themes without key point support are ungrounded assertions.

---

### Pattern 5: Resolving Contradictions

The system surfaces contradictions. It does NOT resolve them.

❌ WRONG:
"While sources disagree on the timeline, the most likely explanation is that Event Y occurred in March, because Source A is more credible and was published closer to the event."

✅ RIGHT:
{
  "tension_id": "TEN_1",
  "description": "Sources disagree on timing. SRC_1 claims March, SRC_2 claims June. This tension is unresolved.",
  "involved_key_points": ["KP_1", "KP_2"]
}

**Why forbidden**: Resolution requires judgment the system explicitly does not provide. Picking sides is editorial, not research.

---

### Pattern 6: Introducing External Knowledge

Gemini must ONLY use information from the provided sources.

❌ WRONG:
"Creator X has a history of similar controversies, including the 2021 incident where..."
(Information not from provided sources)

✅ RIGHT:
Only reference events/facts explicitly stated in the provided source material. If relevant context seems missing, add it as a GAP.

**Why forbidden**: External knowledge is not grounded in Doc 0. It's indistinguishable from hallucination.

---

### Pattern 7: Precise Timestamps in video_only Mode

Without transcript, precise timestamps cannot be claimed.

❌ WRONG:
{
  "observation_id": "OBS_1",
  "timestamp": "14:32"
}

✅ RIGHT:
{
  "observation_id": "OBS_1",
  "timestamp_range": "~14:00-15:00"
}

**Why forbidden**: Precise timestamps require transcript alignment. video_only can only estimate ranges.

---

### Pattern 8: Empty Source References

Every key point MUST have at least one source_id.

❌ WRONG:
{
  "key_point_id": "KP_1",
  "statement": "The company was involved in fraud",
  "source_ids": [],
  "confidence": "high"
}

✅ RIGHT:
{
  "key_point_id": "KP_1",
  "statement": "Source alleges the company was involved in fraud",
  "source_ids": ["SRC_1"],
  "confidence": "medium"
}

**Why forbidden**: Ungrounded key points are assertions without evidence. This is the core hallucination pattern.
```

---

## GAP 4: No Validation Error Examples

### Problem
Validation rules exist but there's no example of what happens when validation fails and how the system recovers.

### Risk
Unclear implementation of retry logic, degradation handling, and warning generation.

### Required Fix
Add validation failure handling examples.

### Validation Failure Examples

```markdown
## VALIDATION FAILURE HANDLING

### Example A: Ungrounded Key Point Detected

**Gemini Output (Invalid):**
```json
{
  "key_point_id": "KP_3",
  "statement": "The company was involved in fraud",
  "source_ids": [],
  "confidence": "high"
}
```

**Validation Error:**
- GROUNDING_FAILURE: KP_3 has empty source_ids
- CONFIDENCE_MISMATCH: Cannot be "high" without source support

**System Response:**
1. Log validation failure
2. Retry once with constrained prompt:
   "Your previous output contained ungrounded claims. KP_3 has no source references. 
   Either provide source_ids from the provided sources, or remove this key point.
   Do not invent sources."
3. If retry succeeds: Use retried output
4. If retry fails: Remove KP_3, add warning, continue with remaining valid output

**Warning Added to ctx.warnings:**
```json
{
  "type": "grounding_failure",
  "message": "Key point removed due to missing source grounding",
  "removed_item": "KP_3",
  "original_statement": "The company was involved in fraud"
}
```

**Job Status:** completed_with_warnings (NOT failed)

---

### Example B: Quotes Present in video_only Mode

**Gemini Output (Invalid):**
```json
{
  "analysis_mode": "video_only",
  "supporting_quotes": [
    {"quote_id": "QT_1", "text": "I never did that", "timestamp": "12:34"}
  ]
}
```

**Validation Error:**
- MODE_VIOLATION: video_only mode cannot have supporting_quotes

**System Response:**
1. Log validation failure
2. Retry once with constrained prompt:
   "Your previous output violated mode constraints. In video_only mode, 
   supporting_quotes must be empty. Convert any quotes to observations 
   with approximate=true and timestamp_range instead of precise timestamp."
3. If retry succeeds: Use retried output
4. If retry fails: Clear supporting_quotes, convert to observations if possible, add warning

**Warning Added:**
```json
{
  "type": "mode_violation",
  "message": "Quotes removed from video_only source — mode does not support verbatim quotes",
  "source_id": "SRC_2"
}
```

---

### Example C: Confidence Exceeds Ceiling

**Gemini Output (Invalid):**
```json
{
  "analysis_mode": "video_only",
  "key_points": [
    {"key_point_id": "KP_1", "confidence": "high", "source_ids": ["SRC_1"]}
  ]
}
```

**Validation Error:**
- CONFIDENCE_CEILING_EXCEEDED: video_only mode has ceiling of "low"

**System Response:**
1. Automatically downgrade confidence to ceiling
2. Add warning (no retry needed — this is auto-correctable)

**Auto-Correction Applied:**
```json
{
  "key_point_id": "KP_1",
  "confidence": "low",
  "source_ids": ["SRC_1"]
}
```

**Warning Added:**
```json
{
  "type": "confidence_downgrade",
  "message": "Confidence downgraded from 'high' to 'low' due to video_only mode ceiling",
  "key_point_id": "KP_1"
}
```

---

### Example D: Theme With Insufficient Key Points

**Gemini Output (Invalid):**
```json
{
  "theme_id": "THEME_1",
  "label": "Financial Issues",
  "related_key_points": ["KP_1"]
}
```

**Validation Error:**
- INSUFFICIENT_SUPPORT: Theme requires ≥2 related key points

**System Response:**
1. Retry once: "THEME_1 only has 1 supporting key point. Themes require ≥2. 
   Either add more supporting key points or remove this theme."
2. If retry fails: Remove theme, add warning

**Warning Added:**
```json
{
  "type": "insufficient_support",
  "message": "Theme removed due to insufficient key point support (had 1, requires 2)",
  "removed_item": "THEME_1"
}
```
```

---

## GAP 5: No Timestamp Handling Rules

### Problem
Examples mention timestamps but don't specify formatting rules by mode.

### Risk
Inconsistent timestamp formatting, false precision in degraded modes.

### Required Fix
Add explicit timestamp rules per analysis mode.

### Timestamp Rules Specification

```markdown
## TIMESTAMP RULES BY ANALYSIS MODE

### transcript_grounded Mode
- **Format:** Exact timestamps required
- **Examples:** "14:32", "1:23:45"
- **Precision:** Must match transcript timing exactly
- **Usage:** All quotes, claims with temporal reference

### caption_grounded Mode
- **Format:** Approximate timestamps with tolerance
- **Examples:** "~14:30", "14:32 ±5s"
- **Precision:** Within 5 seconds of actual moment
- **Note:** Caption sync may be imprecise; always indicate approximation

### video_only Mode
- **Format:** Timestamp ranges only
- **Examples:** "~12:00-15:00", "approximately mid-video"
- **Precision:** Cannot claim precise timestamps
- **Prefix:** Always use "~" to indicate approximation
- **Never:** Single precise timestamps like "14:32"

### Duration References
For all modes, duration should be formatted as:
- Under 1 hour: "MM:SS" (e.g., "45:30")
- Over 1 hour: "H:MM:SS" (e.g., "1:23:45")

### Invalid Timestamp Examples
❌ "14:32" in video_only mode
❌ "Around 14 minutes" (too vague for transcript_grounded)
❌ "1432" (missing colon)
❌ "14.32" (wrong separator)
```

---

## GAP 6: No Entity Extraction Rules

### Problem
Specifications mention entities but no examples show correct entity handling.

### Risk
Gemini extracts entities inconsistently, invents entity relationships, or adds entities from external knowledge.

### Required Fix
Add explicit entity extraction rules and examples.

### Entity Extraction Specification

```markdown
## ENTITY EXTRACTION RULES

### Definition
Entities are named items explicitly mentioned in source material:
- PERSON: Named individuals
- ORG: Companies, organizations, groups
- EVENT: Named events, incidents
- LOCATION: Places, venues
- DATE: Specific dates or time periods
- DOCUMENT: Named documents, reports, filings

### Core Rules

**Rule 1: Explicit Mention Only**
Entities must be explicitly named in the source. Do not infer entities.

❌ WRONG: Adding "SEC" because financial fraud is discussed
✅ RIGHT: Only add "SEC" if the source explicitly mentions it

**Rule 2: Source Linkage Required**
Every entity must link to the source(s) where it was mentioned.

```json
{
  "entities": [
    {
      "name": "Creator X",
      "type": "PERSON",
      "source_ids": ["SRC_1", "SRC_2", "SRC_3"]
    },
    {
      "name": "Company Y",
      "type": "ORG",
      "source_ids": ["SRC_1"]
    }
  ]
}
```

**Rule 3: No Relationship Inference**
Do not infer relationships between entities unless explicitly stated.

❌ WRONG: "Creator X works for Company Y" (inferred from context)
✅ RIGHT: "Creator X mentions Company Y" (stated relationship only)

**Rule 4: No External Knowledge**
Do not add entities from general knowledge not present in sources.

❌ WRONG: Adding "YouTube" as an entity because the source is a YouTube video
✅ RIGHT: Only add "YouTube" if the source content explicitly discusses YouTube

**Rule 5: Normalize Names**
Use consistent naming when the same entity appears with variations.

Source says: "John Smith", "Mr. Smith", "John"
Entity stored as: "John Smith" with aliases noted

### Entity JSON Schema

```json
{
  "entity_id": "ENT_1",
  "name": "Creator X",
  "type": "PERSON",
  "source_ids": ["SRC_1", "SRC_2"],
  "aliases": ["@creatorx", "Creator X Official"],
  "first_mention": {
    "source_id": "SRC_1",
    "timestamp": "2:34"
  }
}
```

### Entity Types Enum
```
PERSON | ORG | EVENT | LOCATION | DATE | DOCUMENT | PRODUCT | OTHER
```
```

---

# PART 2: DEEP RESEARCH BOOSTER SPECIFICATION

---

## Overview

The Deep Research Booster is an **optional, user-triggered** component that runs AFTER the initial job completes. Its purpose is to expand Doc 1 (Jump-Start Research Directions) with additional research directions, search queries, and perspectives to investigate.

### Critical Principle
The booster produces **DIRECTIONS**, not **FACTS**. It tells you WHERE to look, not WHAT you'll find.

---

## When It Runs

- **Trigger:** User-initiated action after viewing initial job output
- **Prerequisite:** Doc 0, Doc 1, Doc 2 must already exist
- **Independence:** Booster failure does not affect existing documents

### User Flow
```
1. User submits research job
2. System produces Doc 0, Doc 1, Doc 2
3. User reviews output, sees gaps in Doc 1
4. User clicks "Expand Research" / "Deep Research"
5. Booster runs using Context Bundle as input
6. Booster output appends to Doc 1 as new section
```

---

## Input: Context Bundle

The booster receives a **Context Bundle** — a constrained, automatically-generated input derived from the job output. The user does not type anything.

### Why Context Bundle?
- **Prevents topic drift:** Booster stays focused on what was actually researched
- **Standardizes input:** No guessing about what to provide
- **Limits scope:** Booster can't hallucinate about things outside the bundle

### Context Bundle Schema

```python
@dataclass
class ContextBundle:
    """
    Constrained input for Deep Research Booster.
    Auto-generated from job output. User provides nothing.
    """
    
    # Scope (from Doc 1)
    scope_in: List[str]           # What this research covers
    scope_out: List[str]          # What this research explicitly excludes
    
    # Semantic content (from extraction)
    themes: List[ThemeSummary]    # Theme ID, label, description (no full key points)
    key_point_summaries: List[str] # KP statements only (not full objects)
    tensions: List[TensionSummary] # Unresolved contradictions
    gaps: List[GapSummary]        # Already-identified gaps from Doc 1
    
    # Metadata
    source_count: int
    source_types: List[str]       # ["youtube", "article", "thread"]
    confidence_level: str         # Overall job confidence: "low", "medium", "high"
    
    # Job reference
    job_id: str
    generated_at: str             # ISO timestamp


@dataclass
class ThemeSummary:
    theme_id: str
    label: str
    description: str


@dataclass  
class TensionSummary:
    tension_id: str
    description: str


@dataclass
class GapSummary:
    gap_id: str
    description: str
```

### What Is NOT In The Context Bundle
- ❌ Full transcript text
- ❌ Verbatim quotes
- ❌ Doc 0 content
- ❌ Full key point objects with claims
- ❌ Source URLs or metadata

This prevents the booster from having access to information it might hallucinate about.

### Example Context Bundle

```json
{
  "scope_in": [
    "Creator X controversy regarding Event Y",
    "Timeline of public statements",
    "Accusations and responses"
  ],
  "scope_out": [
    "Creator X's earlier career before 2022",
    "Unrelated controversies",
    "Personal life outside professional context"
  ],
  "themes": [
    {
      "theme_id": "THEME_1",
      "label": "Shifting Accountability",
      "description": "Framing of responsibility changes from voluntary to coerced over time"
    },
    {
      "theme_id": "THEME_2",
      "label": "Timeline Inconsistencies",
      "description": "Conflicting dates provided for key events"
    }
  ],
  "key_point_summaries": [
    "Creator X changed explanation of Event Y between March and June",
    "Multiple sources report conflicting timelines",
    "No primary documentation has been provided for financial claims"
  ],
  "tensions": [
    {
      "tension_id": "TEN_1",
      "description": "March statement ('my choice') contradicts June statement ('I was pressured')"
    }
  ],
  "gaps": [
    {
      "gap_id": "GAP_1",
      "description": "No primary documentation for financial claims"
    },
    {
      "gap_id": "GAP_2",
      "description": "No statement from other involved party"
    },
    {
      "gap_id": "GAP_3",
      "description": "No neutral third-party reporting"
    }
  ],
  "source_count": 3,
  "source_types": ["youtube", "youtube", "article"],
  "confidence_level": "medium",
  "job_id": "job_12345",
  "generated_at": "2026-01-12T14:30:00Z"
}
```

---

## Output: Booster Result

The booster produces research DIRECTIONS organized into four categories.

### Output Schema

```python
@dataclass
class BoosterOutput:
    """
    Output that augments Doc 1. DIRECTIONS ONLY, no facts.
    """
    
    missing_perspectives: List[MissingPerspective]
    primary_source_directions: List[PrimarySourceDirection]
    suggested_search_queries: List[SearchQuery]
    research_questions: List[ResearchQuestion]
    
    # Metadata
    booster_provider: str         # "gemini", "claude", etc.
    booster_timestamp: str        # ISO timestamp
    context_bundle_hash: str      # SHA256 of input bundle (for verification)
    

@dataclass
class MissingPerspective:
    """A viewpoint or voice not represented in current sources."""
    
    description: str              # "No statement from legal team"
    why_it_matters: str           # "Could clarify contract interpretation"
    related_gaps: List[str]       # ["GAP_1", "GAP_3"]


@dataclass
class PrimarySourceDirection:
    """A type of primary source that might exist and should be sought."""
    
    source_type: str              # See enum below
    description: str              # "Court filings from 2019 lawsuit"
    search_suggestion: str        # "Search [court] [company name] [year]"
    related_gap: str              # "GAP_2"


# Primary Source Types Enum
PRIMARY_SOURCE_TYPES = [
    "court_filing",
    "sec_filing",
    "government_record",
    "academic_paper",
    "news_article",
    "press_release",
    "social_media_archive",
    "interview_transcript",
    "internal_document",
    "dataset",
    "financial_report",
    "other"
]


@dataclass
class SearchQuery:
    """A specific search query to find relevant sources."""
    
    query: str                    # "Creator X lawsuit 2019 breach of contract"
    purpose: str                  # "Find primary legal documents"
    platform_suggestion: str      # "google", "reddit", "twitter", "news"
    related_gap: Optional[str]    # "GAP_2"
    related_theme: Optional[str]  # "THEME_1"


@dataclass
class ResearchQuestion:
    """A question that would advance understanding if answered."""
    
    question: str                 # "What was their position before the controversy?"
    why_it_matters: str           # "Establishes baseline for measuring shift"
    related_theme: str            # "THEME_1"
```

### Example Booster Output

```json
{
  "missing_perspectives": [
    {
      "description": "No statement or response from the other involved party",
      "why_it_matters": "One-sided narrative cannot be verified without counter-perspective",
      "related_gaps": ["GAP_2"]
    },
    {
      "description": "No neutral third-party journalism (only commentary)",
      "why_it_matters": "Commentary sources may have bias; journalism provides investigation",
      "related_gaps": ["GAP_3"]
    },
    {
      "description": "No legal or contractual perspective",
      "why_it_matters": "Financial claims reference agreements but no contract analysis exists",
      "related_gaps": ["GAP_1"]
    }
  ],
  "primary_source_directions": [
    {
      "source_type": "social_media_archive",
      "description": "Original posts from Creator X during March 2024",
      "search_suggestion": "Use Wayback Machine or social media archive tools",
      "related_gap": "GAP_1"
    },
    {
      "source_type": "news_article",
      "description": "Contemporary news coverage (published during events, not retrospective)",
      "search_suggestion": "Filter search by date range of Event Y",
      "related_gap": "GAP_3"
    },
    {
      "source_type": "court_filing",
      "description": "Any legal filings if dispute involved formal action",
      "search_suggestion": "Search PACER or state court records",
      "related_gap": "GAP_1"
    }
  ],
  "suggested_search_queries": [
    {
      "query": "Creator X statement March 2024",
      "purpose": "Find earliest public statement to establish baseline timeline",
      "platform_suggestion": "google",
      "related_gap": null,
      "related_theme": "THEME_2"
    },
    {
      "query": "Creator X [other party name] response",
      "purpose": "Find counter-perspective from involved party",
      "platform_suggestion": "google",
      "related_gap": "GAP_2",
      "related_theme": null
    },
    {
      "query": "Creator X controversy site:reddit.com",
      "purpose": "Find community discussions that may link to primary sources",
      "platform_suggestion": "reddit",
      "related_gap": null,
      "related_theme": "THEME_1"
    },
    {
      "query": "\"Creator X\" \"Event Y\" before:2024-04-01",
      "purpose": "Find coverage from before narrative solidified",
      "platform_suggestion": "google",
      "related_gap": "GAP_3",
      "related_theme": null
    }
  ],
  "research_questions": [
    {
      "question": "What was Creator X's stated position BEFORE the controversy became public?",
      "why_it_matters": "Establishes baseline to measure how framing shifted",
      "related_theme": "THEME_1"
    },
    {
      "question": "Are there any archived or deleted posts that might show earlier statements?",
      "why_it_matters": "Deleted content often reveals contradictions",
      "related_theme": "THEME_2"
    },
    {
      "question": "Who else was involved that hasn't made a public statement?",
      "why_it_matters": "Identifies missing voices for GAP_2",
      "related_theme": "THEME_1"
    }
  ],
  "booster_provider": "gemini",
  "booster_timestamp": "2026-01-12T15:30:00Z",
  "context_bundle_hash": "a3f2b8c9d4e5f6..."
}
```

---

## Hallucination Protection Rules

The booster operates under strict constraints to prevent fact contamination.

### RULE 1: No Facts

The booster MUST NOT output:
- Dates, numbers, or statistics not in Context Bundle
- Names of people/companies not in Context Bundle
- Claims about what happened
- Answers to questions
- Conclusions or judgments

❌ WRONG: "SEC filings from 2019 show the company had $2M in debt"
✅ RIGHT: "Look for SEC filings to verify financial claims"

❌ WRONG: "The other party, John Smith, has denied these claims"
✅ RIGHT: "Search for statements from the other involved party"

### RULE 2: No Resolution

The booster MUST NOT:
- Resolve tensions from the Context Bundle
- Pick sides in contradictions
- Declare what is "true" or "likely"
- Prioritize one source over another

❌ WRONG: "The March date is probably correct because Source A was published closer to the event"
✅ RIGHT: "Search for contemporaneous sources to verify the disputed timeline"

### RULE 3: Grounded in Context Bundle

Every output item must connect to something in the Context Bundle:
- `related_gap` references a gap_id from the bundle
- `related_theme` references a theme_id from the bundle
- `related_gaps` array contains valid gap_ids

If the booster suggests something unconnected to the bundle, it's hallucinating scope.

❌ WRONG: "You should also investigate their 2018 tax issues" (not in bundle)
✅ RIGHT: All suggestions trace to bundle content

### RULE 4: Source Types, Not Source Content

The booster suggests WHERE to look, not WHAT you'll find.

❌ WRONG: "Court documents reveal that the contract was breached in June"
✅ RIGHT: "Court documents may exist if formal legal action was taken — search [query]"

❌ WRONG: "News reports confirm the timeline was falsified"
✅ RIGHT: "Search for news reports from the event period to verify timeline claims"

### RULE 5: No Invented Entities

The booster cannot introduce people, companies, events, or organizations not already in the Context Bundle.

❌ WRONG: "You should contact Company Y's legal department"
✅ RIGHT: "Search for statements from other parties mentioned in the sources"

❌ WRONG: "The SEC investigation in 2020 is relevant"
✅ RIGHT: "If financial misconduct is alleged, SEC filings may exist — search [query]"

### RULE 6: Query Specificity Without Assertion

Search queries should be specific enough to be useful but must not assert facts.

❌ WRONG: "Creator X fraud conviction 2019" (asserts conviction happened)
✅ RIGHT: "Creator X lawsuit 2019" (searches without asserting outcome)

❌ WRONG: "Creator X admits wrongdoing interview" (asserts admission)
✅ RIGHT: "Creator X interview [topic] [date range]" (neutral search)

---

## Integration With Doc 1

When the booster runs successfully, its output appends to Doc 1 as a visually distinct section.

### Why Visually Distinct?
The user should know which directions came from:
- Source analysis (original Doc 1 content)
- Research expansion (booster content)

This maintains transparency about the provenance of suggestions.

### Doc 1 Integration Format

```markdown
# JUMP-START RESEARCH DIRECTIONS

## SCOPE LOCK
[Original scope content...]

## WHAT WE KNOW
[Original content from extraction...]

## GAPS
[Original gaps identified from sources...]

## TOP 3 NEXT STEPS
[Original next steps...]

---

## 🔍 DEEP RESEARCH EXPANSION
*Generated by Deep Research Booster on 2026-01-12*
*Based on: 3 sources, medium confidence, 3 gaps identified*

### Missing Perspectives to Seek
- **No response from other involved party**
  - Why it matters: One-sided narrative cannot be verified
  - Related gap: GAP_2
  
- **No neutral journalism (only commentary)**
  - Why it matters: Commentary may have bias; journalism investigates
  - Related gap: GAP_3

### Primary Sources to Find
| Type | Description | Search Approach |
|------|-------------|-----------------|
| Social media archive | Original posts from disputed period | Wayback Machine, archive tools |
| News article | Contemporary coverage (not retrospective) | Date-filtered search |
| Court filing | Legal documents if formal action exists | PACER, state court records |

### Suggested Search Queries
1. `Creator X statement March 2024`
   - Purpose: Find earliest public statement
   - Platform: Google
   
2. `Creator X [other party] response`
   - Purpose: Find counter-perspective
   - Platform: Google
   
3. `Creator X controversy site:reddit.com`
   - Purpose: Community discussions with source links
   - Platform: Reddit

4. `"Creator X" "Event Y" before:2024-04-01`
   - Purpose: Coverage before narrative solidified
   - Platform: Google (date-filtered)

### Research Questions to Pursue
- What was Creator X's position BEFORE the controversy went public?
- Are there archived/deleted posts showing earlier statements?
- Who else was involved that hasn't made a statement?

---
*Deep Research Expansion complete. These are DIRECTIONS to explore, not facts.*
*Original source analysis above. Expansion suggestions below the divider.*
```

---

## Provider Recommendation

### Recommended: Gemini or Claude with Direction-Only Prompt

**Why:**
- Fully controllable prompt
- No external search (prevents fact injection)
- Can enforce all hallucination rules
- Consistent output format
- Lower cost than deep research APIs

### Not Recommended: OpenAI Deep Research

**Why Not:**
- Designed to ANSWER questions (returns synthesized facts)
- Black box — cannot control what it searches or returns
- Produces conclusions that contaminate evidence layer
- High cost
- Output format not controllable

**Example of problematic output from OpenAI Deep Research:**
> "Based on my research, Company X was sued in 2019 for $2.3M. Court documents show the CEO admitted to misrepresenting quarterly earnings..."

This is FACT PRODUCTION, not direction. It cannot be traced to your Doc 0. It may be hallucinated. It contaminates your research.

### Alternative: Two-Stage Hybrid (Future Enhancement)

If source discovery is needed later:

**Stage A:** Direction generation (Gemini/Claude) — produces queries
**Stage B:** Search execution (Exa/Brave) — returns URLs only, no content

User then decides which URLs to add to their NEXT research job, keeping the evidence pipeline clean.

---

## Prompt Template

```markdown
## SYSTEM

You are a research direction generator. Your job is to suggest WHERE to look for information, not to provide information itself.

You will receive a Context Bundle describing completed research: themes, key points, tensions, and gaps.

Your task is to suggest:
1. Missing perspectives that should be sought
2. Types of primary sources that might exist
3. Specific search queries to find relevant sources
4. Research questions that would advance understanding

## ABSOLUTE RULES (VIOLATION = INVALID OUTPUT)

1. **NO FACTS**: Do not state anything as true. Do not provide dates, numbers, names, or events not in the Context Bundle.

2. **NO RESOLUTION**: Do not resolve tensions or pick sides in contradictions.

3. **NO NEW ENTITIES**: Do not introduce people, companies, or events not mentioned in the Context Bundle.

4. **DIRECTIONS ONLY**: Every output must be a suggestion of where to look, not what will be found.

5. **GROUNDED**: Every suggestion must connect to a gap_id or theme_id from the Context Bundle.

## CONTEXT BUNDLE

{context_bundle_json}

## OUTPUT FORMAT

Return valid JSON matching this exact schema:

{output_schema}

## REMEMBER

You are generating a research TODO list, not conducting research.
"Look for X" is correct. "X shows that Y" is forbidden.
```

---

## Error Handling

### Booster Failure Does Not Affect Core Docs

If the booster fails for any reason:
- Doc 0, Doc 1, Doc 2 remain unchanged
- User sees message: "Deep Research expansion unavailable"
- Job status remains as it was (completed or completed_with_warnings)

### Validation of Booster Output

Before appending to Doc 1, validate:

1. **Schema validity**: Output matches expected JSON structure
2. **Grounding check**: All related_gap and related_theme values exist in Context Bundle
3. **No-facts check**: Scan for patterns indicating factual assertions
4. **Entity check**: No names/orgs not in Context Bundle

If validation fails:
- Retry once with constrained prompt
- If still fails: Return error to user, do not append invalid content

---

## Implementation Checklist

- [ ] Context Bundle auto-generation from job output
- [ ] Booster prompt template with all hallucination rules
- [ ] Booster output schema and validation
- [ ] Doc 1 integration formatting
- [ ] Booster error handling (failure doesn't affect core docs)
- [ ] User trigger mechanism (button/endpoint)
- [ ] Booster metadata tracking (provider, timestamp, bundle hash)

---

## Future Enhancements (Not For Initial Implementation)

1. **Search execution stage**: Take suggested queries, run through Exa/Brave, return URLs only
2. **Source preview**: Let user preview suggested sources before adding to new job
3. **Iterative expansion**: Run booster again after new sources are added
4. **Provider switching**: Let user choose between Gemini/Claude/Perplexity for booster

---

**END OF DOCUMENT**
