# Research Agent — Producer Packet Specification

**Purpose**: Doc 3 — Creative interpretation layer that transforms research into production-ready planning.

**Status**: DRAFT — Pending review

**Date**: 2026-01-13

**Prerequisite**: Doc 0, Doc 1, Doc 2 must exist before Producer Packet can run.

---

# OVERVIEW

## What Is The Producer Packet?

The Producer Packet is an optional, user-triggered document that interprets the grounded research (Doc 0/1/2) into creative production planning. It's what a skilled research assistant would hand you before you start writing or filming.

**Doc 0/1/2:** "Here's what the sources say."
**Producer Packet:** "Here's what you could DO with it."

---

## Core Principle

Every suggestion in the Producer Packet MUST reference grounded content from Doc 0/1/2.

- Hooks reference actual quotes from Doc 2
- Structure references actual key points and themes
- Gaps reference Doc 1 identified gaps
- Nothing invented. Everything derived.

The packet has more creative freedom than the research docs, but it's **interpretation**, not **invention**.

---

## When It Runs

```
Job completes → Doc 0/1/2 delivered
                    ↓
        User reviews research
                    ↓
        User triggers Producer Packet (optional)
                    ↓
        4-stage pipeline executes
                    ↓
        Producer Packet delivered
```

Producer Packet is:
- **Optional** — User chooses to run it
- **Separate cost** — 4 additional LLM calls
- **Dependent** — Requires Doc 0/1/2 to exist
- **Genre-aware** — Uses genre context heavily

---

## Minimum Requirements

| Requirement | Threshold | Rationale |
|-------------|-----------|-----------|
| Source count | 4+ recommended | Thin input = thin packet |
| Confidence | At least 1 HIGH source | Need anchor content |
| Doc 2 themes | At least 1 theme | Need narrative spine |
| Doc 2 tensions OR gaps | At least 1 | Need story tension |

### Gating Logic

```python
def can_run_producer_packet(job_output: JobOutput) -> tuple[bool, str]:
    """Check if Producer Packet should be offered."""
    
    warnings = []
    
    # Source count check
    if job_output.source_count < 3:
        return False, "Producer Packet requires at least 3 sources."
    
    if job_output.source_count < 4:
        warnings.append("Packet may be limited with fewer than 4 sources.")
    
    # Confidence check
    high_confidence_sources = [s for s in job_output.sources if s.confidence_ceiling == "high"]
    if len(high_confidence_sources) == 0:
        warnings.append("No high-confidence sources. Packet will be speculative.")
    
    # Theme check
    if len(job_output.doc2.themes) == 0:
        return False, "No themes identified. Insufficient content for packet."
    
    # Tension/gap check
    has_tension = len(job_output.doc2.tensions) > 0
    has_gaps = len(job_output.doc1.gaps) > 0
    if not has_tension and not has_gaps:
        warnings.append("No tensions or gaps identified. Packet may lack narrative drive.")
    
    if warnings:
        return True, "Producer Packet available. Notes: " + "; ".join(warnings)
    
    return True, "Producer Packet available."
```

---

# 4-STAGE PIPELINE

The Producer Packet is built in 4 sequential stages. Each stage:
- Has ONE focused task
- Receives specific inputs (not everything)
- Produces specific outputs
- Is validated before next stage proceeds
- References previous stages but doesn't repeat work

---

## Stage 1: Story Core

**Task:** Identify the essential story — what it's about, why it matters, what angle to take.

### Input
- Doc 2: Themes (full)
- Doc 2: Tensions (full)
- Doc 1: Scope (in/out)
- Genre tag
- Source count and confidence summary

### Prompt Focus
```
You are identifying the CORE STORY from this research.

What is the central tension that drives interest?
Why does this matter NOW?
What is the angle that makes this YOUR video, not just a recap?

Do not write the video. Identify the story.
```

### Output Schema

```python
@dataclass
class StoryCoreOutput:
    """Stage 1 output: The essential story."""
    
    # One paragraph summary
    story_summary: str                    # What is this story in 3-4 sentences
    
    # Core tension (the engine)
    central_tension: CentralTension
    
    # Why now
    timeliness: str                       # Why this matters at this moment
    
    # Angle recommendation
    recommended_angle: AngleRecommendation
    
    # Alternative angles (rejected but noted)
    alternative_angles: List[AlternativeAngle]


@dataclass
class CentralTension:
    description: str                      # The core conflict/question
    source_reference: str                 # Which Doc 2 tension or theme this derives from
    why_it_hooks: str                     # Why audience cares


@dataclass
class AngleRecommendation:
    angle: str                            # e.g., "Accountability archaeology"
    description: str                      # What this angle means
    rationale: str                        # Why this angle over others
    genre_fit: str                        # How it fits the genre


@dataclass
class AlternativeAngle:
    angle: str
    why_rejected: str                     # Why not this one
```

### Validation
- central_tension.source_reference must exist in Doc 2
- story_summary must not introduce claims not in Doc 2
- Length check: summary under 500 chars

### Temperature
0.3 — Some interpretation allowed, but grounded.

---

## Stage 2: Structure

**Task:** Develop 2-3 story architecture options with full beat sheets.

### Input
- Stage 1 output (full)
- Doc 2: Key points (full)
- Doc 2: Supporting quotes (full)
- Doc 1: Gaps (full)
- Genre tag

### Prompt Focus
```
You are developing STRUCTURE OPTIONS for this story.

The core tension is: [from Stage 1]
The recommended angle is: [from Stage 1]

Create 2-3 different structural approaches.
For each, provide a full beat sheet with specific content mapped to each beat.
Every beat must reference specific key points or quotes from Doc 2.
```

### Output Schema

```python
@dataclass
class StructureOutput:
    """Stage 2 output: Architecture options."""
    
    structures: List[StoryStructure]      # 2-3 options


@dataclass
class StoryStructure:
    name: str                             # e.g., "Chronological", "Mystery", "Character Study"
    description: str                      # What this structure does
    pros: List[str]
    cons: List[str]
    best_if: str                          # When to use this structure
    
    beats: List[Beat]
    
    estimated_duration: str               # e.g., "12-15 minutes"


@dataclass
class Beat:
    beat_number: int
    beat_name: str                        # e.g., "Cold Open", "The Shift", "The Gap"
    
    timestamp_range: str                  # e.g., "0:00-0:30", "5:00-8:00"
    
    purpose: str                          # What this beat accomplishes
    
    content_references: List[str]         # KP_1, KP_3, QT_2, etc.
    
    key_quote: Optional[str]              # If this beat centers on a quote, which one
    
    notes: str                            # Specific guidance for this beat
```

### Validation
- Each beat.content_references must exist in Doc 2
- Each beat.key_quote must exist in Doc 2 supporting_quotes
- At least 2 structure options provided
- Each structure has at least 5 beats

### Temperature
0.3 — Structured output, limited creativity.

---

## Stage 3: Creative

**Task:** Write actual opening hooks, generate title/thumbnail options.

### Input
- Stage 1 output (story_summary, central_tension, recommended_angle)
- Stage 2 output (first structure option's opening beats)
- Doc 2: Supporting quotes (for verbatim use)
- Genre tag

### Prompt Focus
```
You are writing CREATIVE ELEMENTS for this video.

The story is: [from Stage 1]
The opening beat is: [from Stage 2]

Write 3-5 fully written opening hooks (2-4 sentences each).
Each hook must use at least one actual quote from Doc 2.

Generate 8-10 title options with strategy notes.
Generate 5-7 thumbnail concepts.
```

### Output Schema

```python
@dataclass
class CreativeOutput:
    """Stage 3 output: Written creative elements."""
    
    opening_hooks: List[OpeningHook]
    title_options: List[TitleOption]
    thumbnail_concepts: List[ThumbnailConcept]
    tone_guidance: ToneGuidance


@dataclass
class OpeningHook:
    hook_name: str                        # e.g., "The Juxtaposition", "The Question"
    
    full_text: str                        # The actual written hook, 2-4 sentences
    
    quotes_used: List[str]                # Quote IDs from Doc 2
    
    strategy: str                         # Why this hook works
    
    best_for: str                         # When to use this one


@dataclass
class TitleOption:
    title: str
    strategy: str                         # What this title does
    risk: str                             # Potential downside
    click_factor: str                     # "curiosity", "controversy", "clarity"


@dataclass
class ThumbnailConcept:
    concept: str                          # Description of visual
    text_overlay: Optional[str]           # Text on thumbnail, if any
    emotion: str                          # What feeling it evokes
    references: List[str]                 # What from the research this visualizes


@dataclass
class ToneGuidance:
    overall_tone: str                     # e.g., "Investigative but not prosecutorial"
    pacing_notes: str
    music_direction: str                  # General guidance, not specific tracks
    what_to_avoid: List[str]              # Tone pitfalls
```

### Validation
- Each opening_hook.quotes_used must exist in Doc 2
- Each opening_hook.full_text must be 50-300 chars
- At least 3 hooks, 8 titles, 5 thumbnails

### Temperature
0.5 — Most creative stage. Needs variety.

---

## Stage 4: Risk & Context

**Task:** Identify what to avoid, counter-narratives to prep for, missing voices, and follow-up opportunities.

### Input
- Stage 1 output (recommended_angle)
- Doc 1: Gaps (full)
- Doc 2: Tensions (full)
- Doc 2: Key points with confidence < high
- Genre tag

### Prompt Focus
```
You are identifying RISKS AND CONTEXT for this video.

The angle is: [from Stage 1]
The gaps in research are: [from Doc 1]
The unresolved tensions are: [from Doc 2]

What will critics say? How should the creator preempt it?
Who is missing from this story?
What should NOT be included despite being researched?
What follow-up opportunities exist?
```

### Output Schema

```python
@dataclass
class RiskContextOutput:
    """Stage 4 output: Risk mitigation and context."""
    
    counter_narratives: List[CounterNarrative]
    missing_voices: List[MissingVoice]
    what_to_exclude: List[ExclusionItem]
    follow_up_opportunities: List[FollowUp]
    scope_reminders: ScopeReminders


@dataclass
class CounterNarrative:
    criticism: str                        # What critics will say
    preempt_strategy: str                 # How to address it
    when_to_address: str                  # "In intro", "Don't address directly", etc.


@dataclass
class MissingVoice:
    who: str                              # Who is missing
    why_it_matters: str                   # Why their absence matters
    source_reference: str                 # Which gap from Doc 1
    handling_options: List[str]           # How to handle their absence


@dataclass
class ExclusionItem:
    content: str                          # What to leave out
    source_reference: str                 # Where it came from
    reason: str                           # Why to exclude (off-topic, low confidence, etc.)
    save_for: Optional[str]               # "follow-up video", "never", etc.


@dataclass
class FollowUp:
    opportunity: str                      # What the follow-up could be
    trigger: str                          # What would make it relevant
    research_needed: str                  # What additional research


@dataclass
class ScopeReminders:
    in_scope: List[str]                   # From Doc 1
    out_of_scope: List[str]               # From Doc 1
    boundary_risks: List[str]             # Where you might accidentally drift
```

### Validation
- Each missing_voice.source_reference must exist in Doc 1 gaps
- Each exclusion_item must reference real content from Doc 2
- scope_reminders must match Doc 1

### Temperature
0.3 — Analytical, not creative.

---

# FINAL ASSEMBLY

After all 4 stages complete and validate, assemble into single document.

## Document Structure

```markdown
# PRODUCER PACKET
*Creative interpretation based on research. Not factual claims.*
*Generated: [timestamp]*
*Based on: [source count] sources, [confidence summary]*

---

## EXECUTIVE SUMMARY

### The Story
[Stage 1: story_summary]

### Central Tension
[Stage 1: central_tension.description]

Source: [central_tension.source_reference]

### Why Now
[Stage 1: timeliness]

### Recommended Angle
**[Stage 1: recommended_angle.angle]**

[recommended_angle.description]

[recommended_angle.rationale]

#### Alternative Angles Considered
[Stage 1: alternative_angles — brief list]

---

## STORY STRUCTURE OPTIONS

### Option A: [Structure 1 name]
[Stage 2: structure description, pros, cons, best_if]

#### Beat Sheet

| Time | Beat | Purpose | Content |
|------|------|---------|---------|
| 0:00-0:30 | Cold Open | [purpose] | KP_1, QT_2 |
| ... | ... | ... | ... |

### Option B: [Structure 2 name]
[Same format]

### Option C: [Structure 3 name, if exists]
[Same format]

---

## OPENING HOOKS

### Hook 1: [hook_name]
> [full_text]

*Strategy: [strategy]*
*Uses: [quotes_used]*

### Hook 2: [hook_name]
> [full_text]

...

---

## TITLES & THUMBNAILS

### Title Options

| Title | Strategy | Risk |
|-------|----------|------|
| [title] | [strategy] | [risk] |
| ... | ... | ... |

### Thumbnail Concepts

1. **[concept]**
   - Text: [text_overlay]
   - Emotion: [emotion]

...

---

## TONE & STYLE GUIDANCE

**Overall Tone:** [tone]

**Pacing:** [pacing_notes]

**Music Direction:** [music_direction]

**Avoid:**
- [what_to_avoid items]

---

## MISSING VOICES

| Who | Why It Matters | How to Handle |
|-----|---------------|---------------|
| [who] | [why_it_matters] | [handling_options] |
| ... | ... | ... |

---

## COUNTER-NARRATIVE PREP

### "[criticism]"
**Preempt by:** [preempt_strategy]
**When:** [when_to_address]

...

---

## WHAT TO EXCLUDE

| Content | Reason | Save For |
|---------|--------|----------|
| [content] | [reason] | [save_for] |
| ... | ... | ... |

---

## FOLLOW-UP OPPORTUNITIES

1. **[opportunity]**
   - Trigger: [trigger]
   - Research needed: [research_needed]

...

---

## SCOPE REMINDERS

**In Scope:** [list]

**Out of Scope:** [list]

**Watch for drift toward:** [boundary_risks]

---

*End of Producer Packet*
```

---

# HALLUCINATION PROTECTION

## Stage-Specific Rules

### All Stages
- Every claim must reference Doc 0/1/2 content
- No external knowledge
- No invented quotes
- No assumed facts

### Stage 1 (Story Core)
- central_tension must map to existing Doc 2 tension or theme
- Cannot introduce entities not in sources

### Stage 2 (Structure)
- Every beat must reference at least one KP or QT
- Cannot suggest content not present in extraction

### Stage 3 (Creative)
- Hooks must use actual quotes (verified against Doc 2)
- Titles cannot assert facts not in research
- Thumbnails must reference actual content

### Stage 4 (Risk)
- Missing voices must tie to Doc 1 gaps
- Exclusions must reference real extracted content
- Cannot invent criticisms unrelated to actual content

---

## Validation Between Stages

```python
def validate_stage_output(stage: int, output: Any, context: PipelineContext) -> ValidationResult:
    """Validate stage output before proceeding."""
    
    if stage == 1:
        # Check central tension reference exists
        if output.central_tension.source_reference not in context.doc2_ids:
            return ValidationResult(valid=False, error="Central tension reference not found")
    
    elif stage == 2:
        # Check all beat references exist
        for structure in output.structures:
            for beat in structure.beats:
                for ref in beat.content_references:
                    if ref not in context.doc2_ids:
                        return ValidationResult(valid=False, error=f"Beat reference {ref} not found")
    
    elif stage == 3:
        # Check all quotes used exist
        for hook in output.opening_hooks:
            for quote_id in hook.quotes_used:
                if quote_id not in context.quote_ids:
                    return ValidationResult(valid=False, error=f"Quote {quote_id} not found")
    
    elif stage == 4:
        # Check gap references exist
        for voice in output.missing_voices:
            if voice.source_reference not in context.gap_ids:
                return ValidationResult(valid=False, error=f"Gap reference {voice.source_reference} not found")
    
    return ValidationResult(valid=True)
```

---

# COST ESTIMATE

| Stage | Estimated Tokens (Input) | Estimated Tokens (Output) |
|-------|-------------------------|---------------------------|
| Stage 1 | ~2,000 | ~500 |
| Stage 2 | ~3,000 | ~1,500 |
| Stage 3 | ~2,000 | ~1,500 |
| Stage 4 | ~2,500 | ~1,000 |
| **Total** | **~9,500** | **~4,500** |

Total: ~14,000 tokens for Producer Packet pipeline.

For comparison:
- Extraction (per source): ~3,000-5,000 tokens
- Synthesis: ~4,000-6,000 tokens
- Full job (5 sources): ~25,000-35,000 tokens
- Full job + Packet: ~40,000-50,000 tokens

---

# IMPLEMENTATION CHECKLIST

- [ ] Gating logic (minimum sources, confidence check)
- [ ] Stage 1 prompt template
- [ ] Stage 1 output schema (Pydantic)
- [ ] Stage 1 validation
- [ ] Stage 2 prompt template
- [ ] Stage 2 output schema
- [ ] Stage 2 validation
- [ ] Stage 3 prompt template
- [ ] Stage 3 output schema
- [ ] Stage 3 validation
- [ ] Stage 4 prompt template
- [ ] Stage 4 output schema
- [ ] Stage 4 validation
- [ ] Final assembly template
- [ ] User trigger endpoint
- [ ] Cost tracking

---

**END OF DOCUMENT**
