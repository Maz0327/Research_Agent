# Research Agent — Extended Specifications & Design Decisions

**Purpose**: This document captures all design discussions and decisions made after the initial Gaps & Booster Spec. It covers new input types, evolving jobs architecture, genre handling, and additional gaps identified.

**Status**: DRAFT — Pending user approval before integration

**Date**: 2026-01-12

**Builds On**: GAPS_AND_BOOSTER_SPEC.md, RESEARCH_AGENT_COMPLETE_CONTEXT.md

---

# PART 1: EXPANDED INPUT TYPES

The system now supports three input modes beyond YouTube URLs.

---

## Overview: Three Input Modes

| Mode | Input | Best For | Confidence Ceiling | Quotes Allowed? |
|------|-------|----------|-------------------|-----------------|
| **URL** | YouTube, articles | Primary sources with metadata | HIGH | Yes (if transcript available) |
| **Text** | Copy-pasted content | Paywalled articles, cleaned extracts | MEDIUM | No |
| **Screenshot** | Images of UI | Reddit comments, tweets, forums | MEDIUM | No |

### Core Principle

Text and screenshot inputs are treated like **video_only mode**:
- No verbatim quotes (observations only)
- Confidence ceiling enforced
- Explicit provenance disclaimers
- User is responsible for chain of custody

The system organizes and analyzes. The system does NOT verify user-provided content.

---

## Input Mode: URL

**Status**: Currently implemented (YouTube), needs expansion (articles)

### Supported URL Types

| Source Type | URL Pattern | Extraction Method |
|-------------|-------------|-------------------|
| YouTube | `youtube.com/watch?v=`, `youtu.be/` | Supadata → Whisper → Captions → video_only |
| Article | Any non-video URL | Content extraction service |
| PDF | `.pdf` extension | PDF text extraction |

### Article Handling

**Paywall Detection**:
- If content extraction fails or returns minimal text
- Return clear error: "This content appears to be paywalled. Use text input to paste accessible content."
- Job does not fail — source marked as `extraction_failed`

**Extraction Service Options**:
- Jina Reader
- Diffbot
- Custom Readability implementation

### Provenance: URL Mode

```
source_id: SRC_1
source_type: youtube | article | pdf
input_mode: url
url: [provided URL]
title: [auto-extracted]
creator: [auto-extracted]
published_date: [auto-extracted if available]
provenance: "system_extracted"
confidence_ceiling: high
```

---

## Input Mode: Text

**Status**: New — Not yet implemented

### Description

User pastes text content directly. System processes as-is without verification.

### Use Cases

1. Paywalled articles user has access to
2. Cleaned/edited extracts from complex sources
3. Forum posts, emails, documents
4. Any content where URL extraction fails or isn't possible

### Input Schema

```python
@dataclass
class TextSourceInput:
    """User-provided text content."""
    
    content: str                          # The pasted text (required)
    title: str                            # User-provided title (required)
    creator: Optional[str] = None         # Who wrote/said this
    source_url: Optional[str] = None      # Where it came from (not verified)
    date: Optional[str] = None            # When it was published
    source_description: Optional[str] = None  # User's description of source
```

### Provenance: Text Mode

```
source_id: SRC_2
source_type: user_text
input_mode: text
url: [user-provided, not verified]
title: [user-provided]
creator: [user-provided]
provenance: "user_provided"
confidence_ceiling: medium
confidence_note: "Content provided by user, not system-verified"
```

### Processing Rules

1. **No quotes** — Extracted content uses observations, not verbatim quotes
2. **Confidence ceiling: MEDIUM** — Cannot exceed regardless of content quality
3. **Provenance disclaimer** — Output explicitly states content was user-provided
4. **No metadata verification** — System trusts user-provided metadata without validation

### Size Limits

**To be determined**, but must define:
- Maximum character count per text input
- Maximum word count per text input
- Clear error message when exceeded

---

## Input Mode: Screenshot

**Status**: New — Not yet implemented

### Description

User uploads screenshots of content (Reddit threads, tweets, forum posts). System extracts text via OCR/Vision and processes.

### Use Cases

1. Reddit comments (bypasses API restrictions)
2. Twitter/X threads (bypasses broken API)
3. Forum posts from any platform
4. Any UI where copy-paste loses structure

### Advantages

- Bypasses all API problems
- User-curated input (they select exactly what matters)
- Works for platforms with broken/expensive APIs
- Future-proof against API changes

### Input Schema

```python
@dataclass
class ScreenshotSourceInput:
    """User-provided screenshot."""
    
    image: bytes                          # The screenshot image (required)
    platform_hint: Optional[str] = None   # "reddit", "twitter", "forum", "other"
    title: Optional[str] = None           # User-provided title
    source_url: Optional[str] = None      # URL of page (not verified)
    context_note: Optional[str] = None    # User's note about what this shows
```

### Provenance: Screenshot Mode

```
source_id: SRC_3
source_type: screenshot
input_mode: screenshot
platform_hint: reddit
url: [user-provided, not verified]
extracted_text: [OCR/Vision output]
provenance: "ocr_extracted"
confidence_ceiling: medium
confidence_note: "Extracted from screenshot via vision model"
```

### Processing Rules

1. **No quotes** — Even if text is extracted, treat as observations
2. **Confidence ceiling: MEDIUM** — OCR variance, missing context
3. **Each screenshot = one source** — No attempt to reconstruct threading
4. **Explicit extraction disclosure** — Output states content was OCR-extracted

### OCR Strategy: Two-Stage Approach

**Recommended approach** (pending cost testing):

Stage 1: Cheap OCR extracts raw text
- Options: Tesseract, EasyOCR, Google Cloud Vision API

Stage 2: Cheap text LLM structures the text
- Input: "Here's OCR output from a Reddit screenshot. Identify: poster username, post content, subreddit, timestamp if visible."
- Options: Gemini Flash, Claude Haiku

**Alternative**: Direct Gemini Vision (simpler but potentially more expensive)

**Decision**: Test both approaches on 10 sample screenshots. Compare cost and accuracy. Choose based on data.

### OCR Tool Options

| Tool | Cost | Quality | Notes |
|------|------|---------|-------|
| Tesseract | Free | Medium | Open source, struggles with complex UI |
| EasyOCR | Free | Medium-Good | Multi-language support |
| PaddleOCR | Free | Good | Setup complexity |
| Google Cloud Vision | ~$1.50/1000 | Good | Pure text, no structure |
| AWS Textract | ~$1.50/1000 | Good | Document-focused |
| Gemini Vision | ~$0.0025/image | Excellent | Understands structure |

### Size Limits

**To be determined**, but must define:
- Maximum screenshots per job
- Maximum file size per screenshot
- Maximum dimensions
- Clear error messages

### Missing Context Warning

Screenshots often capture mid-conversation content without setup context.

**Handling**:
- Prompt LLM to flag when content seems to be mid-conversation
- Add warning in output: "This content may lack surrounding context"
- User can provide context_note to clarify

---

## Unified Provenance Model

All three input modes produce sources with consistent provenance structure:

```python
@dataclass
class SourceProvenance:
    """Provenance record for any source."""
    
    source_id: str                        # SRC_1, SRC_2, etc.
    input_mode: str                       # "url", "text", "screenshot"
    source_type: str                      # "youtube", "article", "user_text", "screenshot"
    
    # Verification status
    provenance: str                       # "system_extracted", "user_provided", "ocr_extracted"
    system_verified: bool                 # True only for URL mode with successful extraction
    
    # Confidence
    confidence_ceiling: str               # "high", "medium", "low"
    confidence_note: Optional[str]        # Explanation of confidence level
    
    # Metadata (verification varies by mode)
    title: Optional[str]
    creator: Optional[str]
    url: Optional[str]
    date: Optional[str]
    
    # Mode-specific
    transcript_source: Optional[str]      # URL/YouTube only
    analysis_mode: Optional[str]          # "transcript_grounded", "caption_grounded", "video_only", "text_provided", "ocr_extracted"
    platform_hint: Optional[str]          # Screenshot only
```

### Confidence Ceiling by Mode

| Input Mode | Analysis Mode | Confidence Ceiling | Quotes Allowed |
|------------|---------------|-------------------|----------------|
| URL (YouTube) | transcript_grounded | HIGH | Yes |
| URL (YouTube) | caption_grounded | MEDIUM | Yes (marked approximate) |
| URL (YouTube) | video_only | LOW | No |
| URL (Article) | text_extracted | HIGH | Yes |
| URL (Article) | extraction_failed | — | Source excluded |
| Text | text_provided | MEDIUM | No |
| Screenshot | ocr_extracted | MEDIUM | No |

---

## Quote vs Observation Rules (Extended)

### When Quotes Are Allowed

```
transcript_grounded (Supadata/Whisper): YES — verbatim, timestamped
caption_grounded (YouTube captions): YES — marked approximate
text_extracted (articles): YES — verbatim from extracted text
```

### When Only Observations Are Allowed

```
video_only: Observations only, no quotes
text_provided: Observations only (user-provided, unverified)
ocr_extracted: Observations only (OCR variance, missing context)
```

### Observation Format (For Non-Quote Modes)

```json
{
  "observation_id": "OBS_1",
  "description": "Source discusses timeline inconsistencies",
  "source_id": "SRC_2",
  "approximate": true,
  "type": "observation",
  "input_mode": "text"
}
```

---

# PART 2: EVOLVING JOBS ARCHITECTURE

Jobs are persistent containers that evolve over time, not one-shot tasks.

---

## Core Concept

**Old Model (One-Shot)**:
```
User provides sources → Job runs → Output delivered → Done
New research = entirely new job
```

**New Model (Evolving)**:
```
User provides sources → Job runs → Output delivered
User adds more sources → Job updates → Output evolves
User runs booster → Doc 1 enriched
One topic = one evolving artifact
```

### Why Evolving Jobs?

1. **Research is iterative** — Users don't have all sources upfront
2. **Context accumulates** — Later sources should connect to earlier findings
3. **ADHD-friendly** — Don't force users to start over or mentally merge outputs
4. **Booster integration** — Natural fit for enrichment without new jobs

---

## Job Structure

```
Job (persistent container)
│
├── Metadata
│   ├── job_id
│   ├── topic
│   ├── genre (optional, toggleable)
│   ├── created_at
│   └── updated_at
│
├── Sources (can be added over time)
│   ├── SRC_1 (YouTube) - status: processed
│   ├── SRC_2 (YouTube) - status: processed
│   ├── SRC_3 (Screenshot) - status: processed (added later)
│   └── SRC_4 (Text) - status: failed (added later)
│
├── Extractions (cached per source)
│   ├── SRC_1 extraction result
│   ├── SRC_2 extraction result
│   └── SRC_3 extraction result
│
├── Documents
│   ├── Doc 0 - Source Ledger
│   │   ├── Original section (SRC_1, SRC_2)
│   │   └── Addendum (SRC_3)
│   │
│   ├── Doc 1 - Jump-Start
│   │   ├── Original section
│   │   ├── Addendum
│   │   ├── Cross-Reference Notes
│   │   └── Booster Expansion (if run)
│   │
│   └── Doc 2 - Semantic Brief
│       ├── Original section
│       ├── Addendum
│       └── Cross-Reference Notes
│
└── Booster Output (if run)
    └── Enrichment data for Doc 1
```

---

## Additive + Cross-Reference Model

When sources are added, the system does NOT re-synthesize everything from scratch.

### Process

1. **Original content stays frozen** — Initial Doc 0/1/2 preserved
2. **New sources extracted** — Only process newly added sources
3. **New section appended** — Addendum added to each document
4. **Cross-reference pass** — Lightweight check for connections

### Cross-Reference Pass

A focused prompt that checks:
- Do new sources **support** existing themes?
- Do new sources **contradict** existing key points?
- Are there **new themes** unique to the new batch?
- Any **new tensions** between old and new sources?

Output: "Cross-Reference Notes" section

### Document Structure After Addition

```markdown
# Doc 2 — Semantic Brief

## Original Analysis
[Content from initial sources SRC_1, SRC_2]

### Themes
- THEME_1: Shifting Accountability
- THEME_2: Timeline Inconsistencies

### Tensions
- TEN_1: March vs June timeline conflict

---

## Addendum: Sources Added 2026-01-15
*Sources: SRC_3 (screenshot), SRC_4 (text)*

### New Themes
- THEME_3: Financial Pressure (unique to new sources)

### New Key Points
- KP_5: Third party confirms timeline issues
- KP_6: Internal pressure referenced

---

## Cross-Reference Notes

### Supports Existing Analysis
- SRC_3 **supports THEME_1** — Additional evidence of accountability shifting
- SRC_4 **supports TEN_1** — Provides third perspective on timeline conflict

### Contradictions Identified
- SRC_4 **contradicts KP_2** — Claims Event Y occurred in April, not March or June
- New tension: Three-way timeline conflict (March vs June vs April)

### New Gaps Identified
- No documentation of claimed April timeline
- Financial pressure claims lack primary evidence
```

---

## Advantages of This Model

1. **Fast** — Only process new sources, not everything
2. **Cheap** — Small cross-reference call, not full re-synthesis
3. **Clear provenance** — User sees what's original vs added
4. **No information loss** — Original analysis preserved
5. **Contradictions surfaced** — Cross-source tensions explicitly identified

---

## Source States Within Job

Each source has a status:

| Status | Meaning |
|--------|---------|
| `pending` | Added but not yet processed |
| `processing` | Currently being extracted |
| `processed` | Extraction complete |
| `failed` | Extraction failed (with reason) |
| `excluded` | User removed from job |

### Partial Failure Handling

If user adds 5 sources and 2 fail:
- Job status: `completed_with_warnings`
- 3 successful sources included in addendum
- 2 failed sources listed with failure reasons
- User can retry failed sources or remove them

---

## Triggers and Timing

### What Triggers Document Update?

| Action | Triggers Update? |
|--------|------------------|
| Add source(s) | Yes — extraction + addendum + cross-ref |
| Run booster | Yes — Doc 1 enrichment only |
| Remove source | No — source marked excluded, docs unchanged |
| Retry failed source | Yes — if successful, treated as new addition |
| Edit source metadata | No — metadata update only |

### Batch vs Immediate Processing

**Problem**: User adds sources one at a time. Each triggers cross-reference.

**Solution**: Batch window

1. User adds source → status: `pending`
2. User adds another → status: `pending`
3. User clicks "Process" OR 60-second idle timeout
4. All pending sources processed together
5. Single addendum, single cross-reference pass

This prevents 10 additions = 10 cross-ref calls.

---

# PART 3: DEEP RESEARCH BOOSTER (Clarified)

Clarifications based on discussion. Refer to GAPS_AND_BOOSTER_SPEC.md for full specification.

---

## Purpose Clarification

**The booster is NOT for finding sources.**

The booster enriches Doc 1 with:
- More search query suggestions
- More topic suggestions
- More perspective suggestions
- More angle ideas
- Potential gaps people haven't considered

**The booster does NOT:**
- Execute searches
- Return URLs
- Provide source content
- Do research for the user

User reads booster output → User manually searches → User finds sources → User adds sources to job

---

## Booster in Evolving Jobs

The booster fits naturally into the evolving job model:

1. Initial job runs → Doc 0/1/2 created
2. User reviews output, wants more directions
3. User triggers booster → Doc 1 enriched with expansion section
4. User manually researches using booster suggestions
5. User finds new sources → Adds to job
6. Job updates with addendum + cross-reference
7. Repeat as needed

### Booster Availability

- Available after initial extraction completes
- Can run multiple times, but...
- Subsequent runs have diminishing returns if no new sources added
- Consider cooldown or warning: "No new sources since last booster run"

---

## Booster Input (Unchanged)

Context Bundle auto-generated from current job state:
- Scope (in/out)
- Themes, key points, tensions, gaps
- Source count and types
- Confidence level

**Not included**: Full text, quotes, Doc 0 content

---

## Booster Output Location

Booster output appends to Doc 1 as visually distinct section:

```markdown
# Doc 1 — Jump-Start Research Directions

## Original Directions
[From initial extraction]

## Addendum Directions
[From added sources, if any]

---

## 🔍 Deep Research Expansion
*Generated by Deep Research Booster on 2026-01-15*

### Missing Perspectives to Seek
[...]

### Suggested Search Queries
[...]

### Research Questions to Pursue
[...]

---
*These are DIRECTIONS to explore, not facts. Execute searches manually.*
```

---

# PART 4: GENRE TAGS

---

## Current Genre Tags

Topics embedded in system:
- Mystery
- Conspiracy
- Pop culture news
- Political news
- (Others TBD)

---

## Genre Influence by Stage

| Stage | Genre Used? | Rationale |
|-------|-------------|-----------|
| Extraction | NO | Must be objective, genre-blind |
| Validation | NO | Rule-based, no interpretation |
| Synthesis/Assembly | YES | Influences presentation |
| Booster | YES (heavily) | Influences direction suggestions |

### Why Genre-Blind Extraction?

If Gemini knows this is "conspiracy" research during extraction, it might:
- Over-interpret ambiguity as suspicious
- Emphasize certain claims over others
- Introduce confirmation bias

Extraction asks: "What does this source say?"
Synthesis asks: "How do I organize this for someone making a [genre] video?"

Different questions. Genre belongs in the second only.

---

## Genre Toggle

User can disable genre influence entirely:

```
use_genre_context: bool = True (default)
```

**When off:**
- Genre not passed to synthesis
- Genre not passed to booster
- Output is genre-neutral

**Use case:** Output seems biased or weird. User reruns without genre to see if it helps.

---

## Genre Tag Constraints

Genre tags should be **descriptive of content type**, not thesis-driven.

**Good genre tags:**
- Mystery
- Controversy
- Investigation
- Profile
- Breaking news

**Bad genre tags:**
- "Conspiracy to prove X is guilty"
- "Exposé on corruption"
- "Defense of X"

Genre describes format/approach, not conclusion.

---

# PART 5: DECISIONS MADE

---

## Quick Mode vs Deep Mode

**Decision: Not implementing separate modes.**

**Rationale:**
1. User already controls source count
2. Adding modes increases complexity before core is validated
3. Creates decision fatigue for ADHD users
4. Build one mode well, ship it, add modes if demand exists

**Alternative implemented:**
- Soft guidance in UI: "1-3 sources for quick research, 5-10 for deep investigation"
- Same pipeline regardless of source count

---

## Twitter/X Support

**Decision: Not directly supporting.**

**Rationale:**
- API is broken/expensive
- Too complex to implement reliably
- Screenshots work as fallback

**Workaround:**
- Users can screenshot tweets/threads
- Screenshot input mode handles Twitter content
- No special Twitter integration needed

---

## URL Extraction in Booster

**Decision: Not implementing.**

**Rationale:**
- Risk of topic drift when LLM executes searches
- Previous experience with legacy pipeline showed unreliable results
- Contradicts "system enables research, doesn't do research" philosophy

**Alternative:**
- Booster outputs search queries and directions
- User executes searches manually
- User selects and adds sources themselves

---

# PART 6: ADDITIONAL GAPS IDENTIFIED

These gaps were identified after discussing the extended input types and evolving jobs.

---

## Gap 7: Source Deduplication

**Problem**: User adds same URL twice, pastes same text, or screenshots overlapping content.

**Risk**: 
- Duplicate content inflates themes
- Skews synthesis
- Wastes processing

**Required**: Detection and handling strategy
- Option A: Reject duplicates with warning
- Option B: Warn user, allow override
- Option C: Merge silently

**Recommendation**: Option B — Warn but allow. User might intentionally want to track same source at different times.

---

## Gap 8: Text/Screenshot Size Limits

**Problem**: User pastes 50,000 words or uploads massive screenshots.

**Risk**:
- Token limits exceeded
- Job fails unexpectedly
- Cost spike

**Required**: Define and enforce limits
- Maximum characters per text input
- Maximum file size per screenshot
- Maximum dimensions for screenshots
- Clear error messages when exceeded

**Suggested limits** (pending testing):
- Text: 50,000 characters (~10,000 words)
- Screenshot: 10MB file size, 4000x4000 max dimensions

---

## Gap 9: Cross-Reference Cost Accumulation

**Problem**: With evolving jobs, each source addition triggers cross-reference. Adding sources one at a time = many calls.

**Risk**: Expensive, slow, poor UX

**Required**: Batching strategy

**Solution**: Batch window
- New sources marked `pending`
- Process triggered by user action OR idle timeout (60 seconds)
- All pending processed together
- Single cross-reference pass

---

## Gap 10: Confidence Aggregation Across Input Types

**Problem**: Job has mixed sources with different confidence ceilings.
- 2 YouTube (HIGH)
- 3 Screenshots (MEDIUM)
- 1 Text (MEDIUM)

What's the overall job confidence?

**Risk**: Unclear how much user can trust output.

**Options**:
1. Lowest ceiling wins (conservative)
2. Weighted by source count
3. Show per-source confidence, no aggregate
4. Tiered: "High-confidence sources: 2, Medium-confidence: 4"

**Recommendation**: Option 4 — Show breakdown, don't flatten to single value.

---

## Gap 11: Screenshot Missing Context

**Problem**: Screenshot captures mid-thread content. Previous comments provided context. System doesn't see them.

**Risk**: Extraction is confident but wrong due to missing context.

**Required**: 
1. User can provide `context_note` field
2. LLM prompted to flag when content seems mid-conversation
3. Warning in output: "This content may lack surrounding context"

---

## Gap 12: Booster Timing and Repeat Runs

**Problem**: 
- When can booster run?
- Can it run multiple times?
- What happens if user runs it repeatedly with no new sources?

**Risk**: User runs booster 5 times expecting different results. Booster has no new information, produces near-identical output.

**Required**: Clear rules
- Booster available after initial extraction completes
- Can run after new sources added
- Warning if run with no changes since last run
- Consider cooldown (optional)

---

## Gap 13: Partial Failure in Evolving Jobs

**Problem**: User adds 5 sources. 3 succeed, 2 fail. What's the job state?

**Risk**: Unclear UX. Are failed sources stuck? Can user retry? Remove?

**Required**: Source-level status management
- Each source has status: pending, processing, processed, failed, excluded
- Failed sources show reason and allow retry
- User can exclude sources to remove from job
- Job continues with successful sources

---

## Gap 14: Regeneration Triggers

**Problem**: With evolving jobs, unclear when documents actually update.

**Risk**: User confusion about what they're looking at.

**Required**: Explicit rules (defined in Part 2 above)
- Add source(s) → Yes
- Run booster → Yes (Doc 1 only)
- Remove source → No
- Retry failed → Yes (if successful)
- Edit metadata → No

---

# PART 7: IMPLEMENTATION PRIORITY

---

## Phase 1: Core Pipeline (Must Have)

- URL input (YouTube, articles)
- Single-job processing
- Doc 0/1/2 generation
- Basic error handling

**Ship when**: Core pipeline works reliably

---

## Phase 2: Extended Inputs

- Text input mode
- Screenshot input mode
- OCR integration
- Confidence model for new modes

**Depends on**: Phase 1 complete

---

## Phase 3: Evolving Jobs

- Job as persistent container
- Source addition
- Additive documents with addendum
- Cross-reference pass
- Batch processing window

**Depends on**: Phase 1 complete (can parallel with Phase 2)

---

## Phase 4: Deep Research Booster

- Context bundle generation
- Booster prompt and output schema
- Doc 1 integration
- Booster timing rules

**Depends on**: Phase 1 complete

---

## Not Prioritized

- Quick mode vs deep mode (not implementing)
- Twitter/X direct support (not implementing)
- Automated source discovery (not implementing)

---

# PART 8: PIPELINE HARDENING

Low-complexity improvements to strengthen hallucination protection without adding architectural complexity.

**Principle**: Constraint > Detection > Correction. Better to prevent hallucination than catch it.

---

## High Priority Recommendations

### 1. Layered Extraction Sequencing

Force logical progression in extraction prompt:

```
LAYER 1 — EXPLICIT CONTENT
What does the source explicitly state? DO NOT interpret.

LAYER 2 — PATTERNS (from Layer 1 only)
What patterns exist? Every pattern MUST reference specific Layer 1 items.

LAYER 3 — STRUCTURAL ELEMENTS (from Layer 2 only)
What themes, tensions, gaps emerge? DO NOT introduce new information.
```

Each layer constrained by previous. Validation checks that Layer 3 references Layer 2, etc.

---

### 2. Confidence Pre-Declaration

Declare ceiling BEFORE extraction, not after:

```
CONFIDENCE CEILING: MEDIUM

Your analysis mode is: caption_grounded
Your maximum allowed confidence is: MEDIUM
You may NEVER use HIGH in this extraction.
```

Prevents violations rather than catching them.

---

### 3. Source Identity Lock Block

Prominent visual block that model must reference:

```
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  source_id: SRC_1                                        ║
║  title: "Interview with Creator X"                       ║
║  analysis_mode: transcript_grounded                      ║
║  confidence_ceiling: high                                ║
╚══════════════════════════════════════════════════════════╝
```

Validation: All output source_ids must match. Mismatch = hard failure.

---

### 4. Explicit Null Permission

Counter the "helpfulness" instinct:

```
EMPTY OUTPUT PERMISSION

It is acceptable to return empty arrays if:
- No clear themes emerge (themes: [])
- No tensions exist (tensions: [])

DO NOT invent content to fill arrays.
Sparse, accurate output is better than dense, hallucinated output.
```

---

### 5. Source-Isolated Extraction

Each source extracted in complete isolation:

```
Source 1 → Extraction Call 1 → Result 1
Source 2 → Extraction Call 2 → Result 2

Then: [Result 1, Result 2] → Synthesis Call → Cross-source themes
```

Model can't hallucinate connections between sources it can't see.

---

### 6. Mode-Specific Prompt Variants

Separate prompt templates per mode:

- **PROMPT_TRANSCRIPT_GROUNDED.md** — Quotes required, high confidence allowed
- **PROMPT_VIDEO_ONLY.md** — NO quotes field exists, low confidence only
- **PROMPT_TEXT_PROVIDED.md** — No quotes, medium confidence max

Model can't fill a quotes field that doesn't exist in the prompt.

---

## Medium Priority Recommendations

### 7. Quote Verification (transcript_grounded only)

Post-extraction string matching:

```python
if normalized_quote not in normalized_transcript:
    warnings.append(f"Quote not found in transcript")
```

Catches hallucinated quotes programmatically.

---

### 8. Timestamp Sanity Check

Validate timestamps against duration:

```python
if timestamp_seconds > video_duration_seconds:
    warnings.append(f"Timestamp exceeds video duration")
```

---

### 9. Proportional Extraction Guidance

Set expectations based on source size:

```
SOURCE METRICS
- Word count: 847 words

PROPORTIONALITY GUIDANCE
This is a short source. Expect 2-4 key points maximum.
If you're extracting more, you're likely over-interpreting.
```

---

### 10. Temperature Optimization

```python
extraction_config = {"temperature": 0.1}   # Very low — deterministic
synthesis_config = {"temperature": 0.3}    # Still low
booster_config = {"temperature": 0.5}      # Moderate — want variety
```

Lower temperature = fewer hallucinations.

---

### 11. Assertion vs Question Framing

Instead of: "What themes exist?"

Use: "Do significant themes emerge? A theme is significant if it connects 2+ key points. IF none exist, return empty array."

Conditional framing + explicit criteria reduces invention.

---

### 12. Source ID Repetition at Every Level

Require source_id on every nested object:

```json
{
  "key_point_id": "KP_1",
  "source_ids": ["SRC_1"],
  "supporting_claims": [{
    "claim_id": "CLM_1",
    "source_id": "SRC_1",
    "supporting_quotes": [{
      "quote_id": "QT_1",
      "source_id": "SRC_1"
    }]
  }]
}
```

Repetition reinforces grounding. Validation catches drift.

---

## Validation Stage Checks

Based on above, validation should verify:

1. Schema validity (Pydantic)
2. Source ID consistency (all match provided source)
3. Confidence ceiling (auto-correct if exceeded)
4. Quote existence in transcript (string match)
5. Timestamp sanity (within duration)
6. Mode rules (no quotes in video_only)
7. Grounding (key points have source_ids)
8. Theme support (themes have 2+ key points)

---

## Prompt Template Structure

```markdown
# SOURCE IDENTITY LOCK
[Prominent visual block]

# CONFIDENCE CEILING
[Pre-declared ceiling]

# EXTRACTION LAYERS
[Layer 1, 2, 3 instructions]

# EMPTY OUTPUT PERMISSION
[Permission for sparse output]

# PROPORTIONALITY
[Word count and calibration]

# MODE-SPECIFIC RULES
[Rules for this mode only]

# OUTPUT SCHEMA
[Exact JSON structure]

# SOURCE CONTENT
[Transcript or content]
```

---

## Gemini 2.5 Pro — Specific Configuration

**Target Model:** Gemini 2.5 Pro

Based on current documentation and developer experiences.

---

### 1. Temperature: Use Low Values

For extraction tasks, use low temperature:

```python
generation_config={
    "temperature": 0.1,  # Deterministic, minimal hallucination
    "top_p": 0.8
}
```

**Recommended settings by task:**

| Task | Temperature | Rationale |
|------|-------------|-----------|
| Extraction | 0.1 | Maximum determinism |
| Validation | 0.1 | Consistency matters |
| Synthesis (cross-source) | 0.2-0.3 | Slight flexibility for pattern recognition |
| Booster (directions) | 0.4-0.5 | More variety in suggestions |

---

### 2. Structured Output is Native

Gemini 2.5 Pro has built-in JSON mode. Use `response_mime_type` and `response_schema` for guaranteed schema compliance.

```python
response = model.generate_content(
    prompt,
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": SemanticExtractionSchema,
        "temperature": 0.1
    }
)
```

**Why it matters:** Schema enforcement prevents hallucinated fields, unexpected structure, and parsing failures at the API level.

**Key limitation:** Complex schemas (long property names, deep nesting, many optional fields) can cause `InvalidArgument: 400` errors. Keep schemas focused and reasonably flat.

---

### 3. Explicit "I Don't Know" Permission

Critical for reducing hallucination. Tell the model it's okay to return nothing.

```
EMPTY OUTPUT PERMISSION

Using ONLY the source content provided below, extract information.

If the source does not contain relevant information:
- Return empty arrays
- Do not infer, guess, or use external knowledge
- Respond with "Information not found in source" for questions

Empty output is correct behavior when data is incomplete.
```

This single instruction significantly reduces fabrication.

---

### 4. Prompt Structure with XML Delimiters

Use consistent XML-style tags to separate prompt sections:

```xml
<role>
You are an extraction assistant for research analysis.
You extract only what is explicitly stated in the source.
You do not interpret, infer, or add external knowledge.
</role>

<source_identity_lock>
source_id: SRC_1
title: "Interview with Creator X"
analysis_mode: transcript_grounded
confidence_ceiling: high
</source_identity_lock>

<constraints>
- Extract only explicit content from the source
- Do not interpret or infer meaning
- Empty arrays are acceptable and preferred over invention
- Maximum confidence: high (transcript available)
</constraints>

<extraction_layers>
LAYER 1: Extract explicit statements (facts only)
LAYER 2: Identify patterns from Layer 1 content
LAYER 3: Derive themes/tensions from Layer 2 patterns
Each layer must reference the previous layer.
</extraction_layers>

<output_schema>
{schema here}
</output_schema>

<source_content>
{transcript here}
</source_content>
```

---

### 5. Avoid Leading Questions

Phrase extraction prompts neutrally to prevent fabrication.

**Bad (implies facts exist):**
- "What financial misconduct did the company commit?"
- "Extract the timeline of the scandal."
- "List the accusations against Creator X."

**Good (neutral, conditional):**
- "Does the source mention any financial issues? If so, what specifically is stated?"
- "Are any dates or time references mentioned? List them if present."
- "What claims or accusations appear in the source, if any?"

---

### 6. Few-Shot Examples Improve Consistency

Provide one example of correct output structure before the actual extraction task:

```
EXAMPLE EXTRACTION:

INPUT: "John said the project started in March. He mentioned they had budget issues."

OUTPUT:
{
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "Project started in March",
      "source_ids": ["SRC_1"],
      "confidence": "high",
      "supporting_quotes": ["QT_1"]
    },
    {
      "key_point_id": "KP_2", 
      "statement": "Project had budget issues",
      "source_ids": ["SRC_1"],
      "confidence": "high",
      "supporting_quotes": ["QT_2"]
    }
  ],
  "supporting_quotes": [
    {
      "quote_id": "QT_1",
      "text": "the project started in March",
      "source_id": "SRC_1"
    },
    {
      "quote_id": "QT_2",
      "text": "they had budget issues",
      "source_id": "SRC_1"
    }
  ],
  "themes": []
}

Note: No themes extracted because single source with only 2 key points.

---

NOW EXTRACT FROM THE FOLLOWING SOURCE:
```

---

### 7. Post-Extraction Quote Verification

Gemini can hallucinate quotes even when given source text. Verify programmatically:

```python
def verify_quotes(extraction: dict, transcript: str) -> list:
    """Check extracted quotes exist in transcript."""
    warnings = []
    normalized_transcript = normalize_whitespace(transcript.lower())
    
    for quote in extraction.get("supporting_quotes", []):
        quote_text = normalize_whitespace(quote["text"].lower())
        if quote_text not in normalized_transcript:
            warnings.append({
                "type": "quote_not_found",
                "quote_id": quote["quote_id"],
                "text": quote["text"][:50]
            })
    return warnings
```

This catches fabricated quotes before they reach output.

---

### 8. Multimodal Has Higher Hallucination Rates

Research shows ~14% higher hallucination rate on image-augmented prompts vs text-only.

**Implications for screenshot input:**
- Confidence ceiling: MEDIUM (enforced)
- No verbatim quotes from OCR extraction
- Two-stage approach (cheap OCR → text LLM) may be more reliable than direct Vision
- Always flag OCR-extracted content in output

---

### 9. DO NOT Use Google Search Grounding

Gemini offers `google_search_retrieval` tool for fact-checking.

**Why NOT to use it in this system:**
- Contaminates evidence layer with external data
- Introduces facts not traceable to Doc 0
- Undermines provenance model
- User loses control over what's "true"

**Keep extraction closed to user-provided sources only.**

---

### 10. Chain of Thought for Complex Extraction

For Gemini 2.5 Pro, use manual chain-of-thought prompting for complex tasks:

```
Before extracting, analyze the source:

1. What type of content is this? (interview, commentary, news report)
2. Who are the speakers/sources cited?
3. What is the main topic being discussed?
4. Are there any obvious contradictions within the source?

Then proceed with extraction, referencing your analysis.
```

This forces the model to reason before outputting, catching logical errors.

---

### Summary: Gemini 2.5 Pro Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Model | `gemini-2.5-pro` | |
| Temperature (extraction) | 0.1 | Deterministic |
| Temperature (synthesis) | 0.2-0.3 | Slight flexibility |
| Temperature (booster) | 0.4-0.5 | Variety wanted |
| response_mime_type | `application/json` | Always |
| response_schema | Pydantic model | Enforced at API level |
| Prompt structure | XML tags | Consistent delimiters |
| "I don't know" | Explicit permission | Critical |
| Quote verification | Post-extraction | String matching |
| Google grounding | DO NOT USE | Breaks provenance |

---

### Future: Gemini 3 Migration Notes

If upgrading to Gemini 3 later, key changes:
- **Temperature:** Must stay at 1.0 (lowering causes looping)
- **Chain of thought:** Replace with `thinking_level` parameter
- **Thought signatures:** Required for function calling

Do not migrate without testing. Gemini 3 has different behavior.

---

# PART 9: OPEN QUESTIONS

Items requiring decisions before implementation:

1. **OCR approach**: Two-stage (OCR + text LLM) vs direct Vision? Needs cost testing.

2. **Exact size limits**: Text character limit? Screenshot file size? Need to define.

3. **Max sources per job**: Is there a ceiling? 10? 20? Unlimited?

4. **Max screenshots per job**: Given cost, probably need soft cap.

5. **Job expiration**: Do evolving jobs live forever? Archive after X days?

6. **Deduplication strategy**: Warn and allow? Reject? Merge?

7. **Batch window timing**: 60 seconds idle? User-triggered only? Both?

---

**END OF DOCUMENT**
