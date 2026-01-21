# Data Model Audit: Phase 3 Full Research Assistant Pipeline

**Date:** 2026-01-06
**Auditor:** code-reviewer
**Files Audited:**
- `backend/pipeline/dual_output.py` - Phase 2 & 3 dataclasses
- `backend/models/job_record.py` - Extended Artifacts model

**Status:** ✅ PASSED with 2 medium issues, 3 low issues

---

## Executive Summary

Audited Phase 2 (ProducerPacket) and Phase 3 (ContentBlueprint, GapAnalysis, ResearchStarter) dataclasses for:
- Type correctness
- Serialization/deserialization safety
- Field naming consistency with prompts
- Required field coverage
- Method implementation correctness

**Result:** No critical issues. 2 medium (type annotation consistency), 3 low (default handling, validation). All models compile correctly and align with prompts.

---

## Issue Breakdown

### Critical Issues
**Count:** 0

None found.

---

### Medium Priority Issues

#### M1: Inconsistent Hook Field Mapping (ContentBlueprint)
**Severity:** Medium
**File:** `backend/pipeline/dual_output.py:261-361`

**Issue:**
Prompt uses `hook.timestamp_end` (line 63 of structure_analysis_prompt.py), but dataclass field is `hook_timestamp` without clarifying it's the END timestamp.

```python
# Prompt expects:
"hook": {
  "timestamp_end": "MM:SS",  # End of hook
  ...
}

# Dataclass has:
hook_timestamp: str  # Ambiguous - start or end?
```

**Impact:**
- Field name doesn't match prompt exactly
- Semantic ambiguity (is it start or end?)
- Integration code correctly uses `.get("timestamp_end")` but field name unclear

**Recommendation:**
Rename `hook_timestamp` → `hook_timestamp_end` for clarity and prompt alignment.

```python
@dataclass
class ContentBlueprint:
    hook_timestamp_end: str  # Matches prompt exactly
    hook_technique: str
    hook_description: str
```

---

#### M2: Missing Type Annotations for Nested Dicts (ProducerPacket)
**Severity:** Medium
**File:** `backend/pipeline/dual_output.py:98-106`

**Issue:**
`verified_claims` and `candidate_claims` use `List[Dict[str, Any]]` without defining structure.

```python
verified_claims: List[Dict[str, Any]] = field(default_factory=list)
candidate_claims: List[Dict[str, Any]] = field(default_factory=list)
```

**Impact:**
- No type safety for claim structure
- Schema validation must happen at runtime
- Consumers don't know available fields without reading implementation

**Example Data:**
```python
# verified_claims contains:
{
    "claim": str,
    "source": str,
    "timestamp": str,
    "video_url": str,
}

# candidate_claims contains:
{
    "claim": str,
    "clip_id": str,
    "timestamp": str,
    "video_url": str,
}
```

**Recommendation:**
Create TypedDict or dataclass for claim structures:

```python
from typing import TypedDict

class VerifiedClaim(TypedDict):
    claim: str
    source: str
    timestamp: str
    video_url: str

class CandidateClaim(TypedDict):
    claim: str
    clip_id: str
    timestamp: str
    video_url: str

@dataclass
class ProducerPacket:
    verified_claims: List[VerifiedClaim] = field(default_factory=list)
    candidate_claims: List[CandidateClaim] = field(default_factory=list)
```

---

### Low Priority Issues

#### L1: Empty Default Lists Not Validated (ResearchStarter)
**Severity:** Low
**File:** `backend/pipeline/dual_output.py:550-631`

**Issue:**
`ResearchStarter` can be instantiated with all empty lists, producing meaningless output.

```python
# This is valid but useless:
starter = ResearchStarter()  # All fields are empty lists
```

**Impact:**
- No quality gate for minimum content
- Could upload empty markdown to Drive
- User gets "Research Starter" document with no actual guidance

**Recommendation:**
Add quality check method:

```python
def has_content(self) -> bool:
    """Check if starter has meaningful content."""
    return (
        len(self.search_queries) > 0
        or len(self.source_suggestions) > 0
        or len(self.rabbit_holes) > 0
        or len(self.content_angles) > 0
    )
```

---

#### L2: NotebookLMPacket Timeline Overflow (to_markdown)
**Severity:** Low
**File:** `backend/pipeline/dual_output.py:872`

**Issue:**
Timeline narrative built by joining events with space separator. No truncation if timeline exceeds reasonable length.

```python
timeline_narrative = " ".join(timeline_parts)  # Could be 10,000+ chars
```

**Impact:**
- Markdown file could have multi-page timeline paragraph
- Poor readability
- NotebookLM may truncate or skip

**Recommendation:**
Add length limit and summary:

```python
timeline_narrative = " ".join(timeline_parts[:50])  # First 50 events
if len(timeline) > 50:
    timeline_narrative += f" (... {len(timeline) - 50} more events)"
```

---

#### L3: Quote Extraction Regex Too Greedy (NotebookLMPacket)
**Severity:** Low
**File:** `backend/pipeline/dual_output.py:882-883`

**Issue:**
Quote extraction uses `re.findall(r'"([^"]{20,200})"', text)` with arbitrary length bounds.

```python
quoted = re.findall(r'"([^"]{20,200})"', text)  # Why 20-200?
```

**Impact:**
- Misses quotes < 20 chars ("Yes, I agree.")
- Misses quotes > 200 chars (longer statements)
- No context or attribution validation

**Recommendation:**
Adjust bounds or use better heuristic:

```python
quoted = re.findall(r'"([^"]{10,500})"', text)  # More flexible
```

Better: Use speaker labels from extraction stage if available.

---

## Positive Observations

### Type Safety
- All dataclasses use proper type hints
- Enums for verification levels (VerificationLevel) - excellent
- Optional fields correctly marked
- No bare `dict` or `list` types except where noted (M2)

### Serialization
- All dataclasses implement `to_dict()` correctly
- Enum values properly extracted with `.value`
- Nested dataclasses recursively converted
- No circular references

### Prompt Alignment
**Structure Analysis Prompt → ContentBlueprint:**
- ✅ `hook.timestamp_end` → `hook_timestamp` (M1 noted)
- ✅ `hook.technique` → `hook_technique`
- ✅ `hook.description` → `hook_description`
- ✅ `narrative.structure_type` → `structure_type`
- ✅ `narrative.acts[]` → `act_breakdown: List[ActSection]`
- ✅ `open_loops[]` → `open_loops: List[OpenLoop]`
- ✅ `style.pacing` → `pacing`
- ✅ `style.editing_style` → `editing_style`
- ✅ `sources.likely_primary_sources` → `likely_primary_sources`
- ✅ `sources.referenced_materials` → `referenced_materials`

**Gap Analysis Prompt → GapAnalysis:**
- ✅ `missing_perspectives[]` → `missing_perspectives: List[MissingPerspective]`
- ✅ `unanswered_questions[]` → `unanswered_questions: List[str]`
- ✅ `mentioned_but_unexplored[]` → `mentioned_but_unexplored: List[CoverageBlindSpot]`
- ✅ `contradictions[]` → `contradictions: List[Contradiction]`

**Research Starter Prompt → ResearchStarter:**
- ✅ `search_queries[]` → `search_queries: List[SearchQuery]`
- ✅ `source_suggestions[]` → `source_suggestions: List[SourceSuggestion]`
- ✅ `rabbit_holes[]` → `rabbit_holes: List[RabbitHole]`
- ✅ `content_angles[]` → `content_angles: List[ContentAngle]`

### Markdown Generation
- All Phase 3 dataclasses implement `to_markdown()`
- Well-formatted with proper heading hierarchy
- Uses emoji indicators (✅, ⚠️) for status - good UX
- Grouped sections logically

### Verification Logic
**ProducerClip verification:**
- ✅ `range_verified` checks timestamp format
- ✅ `quote_verified` cross-references transcript
- ✅ `verification_level` enum based on both checks
- ✅ Helper `_verify_quote()` and `_verify_timestamp_format()` functions

**ProducerQuote verification:**
- ✅ `match_score` float 0-1 for fuzzy matching
- ✅ Substring matching with fallback to word overlap

### Job Record Integration
**File:** `backend/models/job_record.py:19-31`

Phase 3 fields properly added to `Artifacts`:
```python
content_blueprints: Optional[list[dict[str, Any]]]  # List[ContentBlueprint.to_dict()]
gap_analysis: Optional[dict[str, Any]]               # GapAnalysis.to_dict()
research_starter: Optional[dict[str, Any]]           # ResearchStarter.to_dict()
```

- ✅ Optional fields (correct for progressive enhancement)
- ✅ Descriptive field comments
- ✅ Uses `dict[str, Any]` for JSON storage (correct for Pydantic/Supabase)

---

## Data Flow Validation

### ProducerPacket Creation
**Function:** `create_producer_packet_from_gemini()` (line 1033-1158)

✅ Correct:
- Extracts `video_url`, `title`, `duration_seconds` from Gemini results
- Converts clips with verification against transcripts
- Converts quotes with match scoring
- Splits claims into verified (has quote) vs candidate (clip only)
- Aggregates warnings from Gemini errors

✅ Quality Gate:
- `passes_quality_gate()` checks clips >= 4, quotes >= 8, verified_claims >= 2
- Returns (bool, List[str]) with failures
- Included in `to_dict()` output

### ContentBlueprint Parsing
**Function:** `GeminiClient.analyze_video_structure()` (line 735-848)

✅ Correct:
- Parses JSON from Gemini response
- Extracts nested `hook`, `narrative`, `open_loops`, `style`, `sources`
- Converts `acts[]` to `List[ActSection]`
- Converts `open_loops[]` to `List[OpenLoop]`
- Fallback to minimal blueprint on error

### GapAnalysis Parsing
**Function:** `GeminiClient.analyze_gaps()` (line 853-951)

✅ Correct:
- Parses `missing_perspectives[]` → `List[MissingPerspective]`
- Parses `mentioned_but_unexplored[]` → `List[CoverageBlindSpot]`
- Parses `contradictions[]` → `List[Contradiction]`
- Fallback to empty `GapAnalysis()` on error

### ResearchStarter Parsing
**Function:** `GeminiClient.generate_research_starter()` (line 954-1075)

✅ Correct:
- Parses `search_queries[]` → `List[SearchQuery]`
- Parses `source_suggestions[]` → `List[SourceSuggestion]`
- Parses `rabbit_holes[]` → `List[RabbitHole]`
- Parses `content_angles[]` → `List[ContentAngle]`
- Fallback to empty `ResearchStarter()` on error

---

## Field-by-Field Validation

### ProducerClip (Lines 29-59)
| Field | Type | Default | Required | Valid? |
|-------|------|---------|----------|--------|
| clip_id | str | - | Yes | ✅ |
| video_url | str | - | Yes | ✅ |
| timestamp_start | str | - | Yes | ✅ MM:SS |
| timestamp_end | str | - | Yes | ✅ MM:SS |
| speaker | str | - | Yes | ✅ |
| quote | str | - | Yes | ✅ |
| quote_type | str | - | Yes | ✅ |
| range_verified | bool | False | No | ✅ |
| quote_verified | bool | False | No | ✅ |
| verification_level | VerificationLevel | UNVERIFIED | No | ✅ Enum |

**to_dict():** ✅ All fields, enum converted to `.value`

---

### ProducerQuote (Lines 62-83)
| Field | Type | Default | Required | Valid? |
|-------|------|---------|----------|--------|
| quote_id | str | - | Yes | ✅ |
| video_url | str | - | Yes | ✅ |
| text | str | - | Yes | ✅ |
| speaker | str | - | Yes | ✅ |
| timestamp | str | - | Yes | ✅ MM:SS |
| quote_verified | bool | False | No | ✅ |
| match_score | float | 0.0 | No | ✅ 0-1 |

**to_dict():** ✅ All fields

---

### ProducerPacket (Lines 86-221)
| Field | Type | Default | Valid? |
|-------|------|---------|--------|
| title | str | - | ✅ |
| videos_analyzed | List[Dict[str, Any]] | - | ✅ |
| clips | List[ProducerClip] | [] | ✅ |
| quotes | List[ProducerQuote] | [] | ✅ |
| verified_claims | List[Dict] | [] | ⚠️ M2 |
| candidate_claims | List[Dict] | [] | ⚠️ M2 |
| warnings | List[str] | [] | ✅ |
| extraction_cost | float | 0.0 | ✅ |

**to_dict():** ✅ Includes quality gate status
**to_markdown():** ✅ Sorted clips/quotes, status indicators

---

### ContentBlueprint (Lines 261-361)
| Field | Type | Default | Valid? | Notes |
|-------|------|---------|--------|-------|
| video_url | str | - | ✅ | |
| title | str | - | ✅ | |
| hook_timestamp | str | - | ⚠️ M1 | Should be `hook_timestamp_end` |
| hook_technique | str | - | ✅ | |
| hook_description | str | - | ✅ | |
| structure_type | str | - | ✅ | |
| act_breakdown | List[ActSection] | [] | ✅ | |
| open_loops | List[OpenLoop] | [] | ✅ | |
| pacing | str | "medium" | ✅ | |
| editing_style | str | "standard" | ✅ | |
| likely_primary_sources | List[str] | [] | ✅ | |
| referenced_materials | List[str] | [] | ✅ | |

**to_dict():** ✅ Nested structure with hook/narrative/style/sources dicts
**to_markdown():** ✅ Hierarchical structure with acts

---

### GapAnalysis (Lines 413-486)
| Field | Type | Default | Valid? |
|-------|------|---------|--------|
| missing_perspectives | List[MissingPerspective] | [] | ✅ |
| unanswered_questions | List[str] | [] | ✅ |
| mentioned_but_unexplored | List[CoverageBlindSpot] | [] | ✅ |
| contradictions | List[Contradiction] | [] | ✅ |

**to_dict():** ✅ All nested dataclasses converted
**to_markdown():** ✅ Sections with fallback text for empty

---

### ResearchStarter (Lines 550-631)
| Field | Type | Default | Valid? |
|-------|------|---------|--------|
| search_queries | List[SearchQuery] | [] | ✅ |
| source_suggestions | List[SourceSuggestion] | [] | ✅ |
| rabbit_holes | List[RabbitHole] | [] | ✅ |
| content_angles | List[ContentAngle] | [] | ✅ |

**to_dict():** ✅ All nested dataclasses converted
**to_markdown():** ✅ Grouped by platform, formatted queries

⚠️ L1: No validation for all-empty instance

---

## Helper Dataclasses

### ActSection (Lines 228-242)
✅ All fields string, `to_dict()` correct

### OpenLoop (Lines 245-257)
✅ All fields string, `to_dict()` correct

### MissingPerspective (Lines 363-375)
✅ All fields string, `to_dict()` correct

### CoverageBlindSpot (Lines 378-390)
✅ All fields string, `to_dict()` correct

### Contradiction (Lines 393-409)
✅ All fields string, `to_dict()` correct

### SearchQuery (Lines 489-501)
✅ All fields string, `to_dict()` correct

### SourceSuggestion (Lines 504-516)
✅ All fields string, `to_dict()` correct

### RabbitHole (Lines 519-531)
✅ All fields string, `to_dict()` correct

### ContentAngle (Lines 534-546)
✅ All fields string, `to_dict()` correct

---

## Recommendations Summary

### Must Fix (Before Production)
None - code is production-ready.

### Should Fix (Next Sprint)
1. **M1:** Rename `hook_timestamp` → `hook_timestamp_end`
2. **M2:** Add TypedDict for verified_claims and candidate_claims

### Nice to Have (Backlog)
1. **L1:** Add `ResearchStarter.has_content()` validation
2. **L2:** Truncate timeline narrative with summary
3. **L3:** Improve quote extraction regex bounds

---

## Compilation Status

✅ **PASSED**
```bash
$ python3 -m py_compile backend/pipeline/dual_output.py
$ python3 -m py_compile backend/models/job_record.py
# No errors
```

---

## Test Coverage Recommendations

### Unit Tests Needed

**ProducerPacket:**
- Quality gate thresholds (4 clips, 8 quotes, 2 verified claims)
- Markdown generation with verified/unverified sorting
- Empty vs populated packet

**ContentBlueprint:**
- JSON parsing from Gemini response
- Fallback on parse error
- Markdown generation with acts/loops

**GapAnalysis:**
- Empty arrays handling
- Markdown with no missing perspectives

**ResearchStarter:**
- Platform grouping in markdown
- Empty starter validation (L1)

**Helper Functions:**
- `_verify_quote()` with exact/partial/no match
- `_verify_timestamp_format()` with MM:SS and HH:MM:SS
- `create_producer_packet_from_gemini()` with transcript verification

---

## Conclusion

Phase 3 dataclasses are well-structured with proper type hints, serialization, and prompt alignment. No blocking issues found. 2 medium issues (field naming, nested dict types) should be addressed for improved type safety and consistency. 3 low issues are polish items.

**Approval:** ✅ APPROVED for production use
**Next Steps:** Address M1, M2 in next sprint; L1-L3 as time permits
