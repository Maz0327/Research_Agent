# Research Agent — Pipeline Hardening Recommendations

**Purpose**: Low-complexity improvements to strengthen hallucination protection without adding architectural complexity.

**Principle**: Constraint > Detection > Correction

Better to prevent hallucination than catch it. Better to catch it than fix it.

**Status**: RECOMMENDATIONS — Pending review and integration

**Date**: 2026-01-12

---

# OVERVIEW

These recommendations fall into three categories:

| Category | What It Is | Implementation |
|----------|------------|----------------|
| **Prompt Constraints** | Tell the model what it cannot do | Prompt engineering |
| **Structural Constraints** | Force output shapes that prevent drift | Schema enforcement |
| **Post-Extraction Validation** | Simple checks that catch obvious errors | Code validation |

None of these require new pipeline stages or additional LLM calls.

---

# RECOMMENDATION 1: Layered Extraction Sequencing

**Problem**: Model receives "extract everything" prompt. Can hallucinate connections that skip logical steps (theme without supporting key points).

**Solution**: Explicit layer constraints in extraction prompt.

```
EXTRACTION LAYERS — Process in order. Each layer builds ONLY on previous.

LAYER 1 — EXPLICIT CONTENT
What does the source explicitly state?
- Direct claims made by speakers
- Facts presented
- Statements quoted
DO NOT interpret. DO NOT infer meaning. Just extract what is said.

LAYER 2 — PATTERNS (from Layer 1 only)
What patterns exist in the Layer 1 content?
- Recurring topics
- Repeated phrases or framing
- Contradictions within source
Every pattern MUST reference specific Layer 1 items.

LAYER 3 — STRUCTURAL ELEMENTS (from Layer 2 only)
What themes, tensions, or gaps emerge from Layer 2 patterns?
- Themes must connect 2+ patterns
- Tensions must show specific contradicting items
- Gaps must identify what's missing relative to patterns
DO NOT introduce new information not present in Layers 1-2.
```

**Validation**: Check that Layer 3 items reference Layer 2 items. Layer 2 items reference Layer 1 items. Broken chain = validation failure.

**Complexity**: Prompt change only. No new calls.

---

# RECOMMENDATION 2: Confidence Pre-Declaration

**Problem**: Model outputs confidence levels after extraction. May claim high confidence when mode doesn't allow it.

**Solution**: Declare confidence ceiling BEFORE extraction begins.

```
CONFIDENCE CEILING: MEDIUM

Your analysis mode is: caption_grounded
Your maximum allowed confidence is: MEDIUM

Any key point, claim, or observation you produce CANNOT exceed MEDIUM confidence.
If you are uncertain, use LOW. You may NEVER use HIGH in this extraction.
```

**Why it works**: Model is less likely to output high confidence if told upfront it's not allowed. Current approach catches violations after; this prevents them.

**Complexity**: Prompt change only.

---

# RECOMMENDATION 3: Source Identity Lock Block

**Problem**: Source identity passed in prompt might get lost in context. Model might infer different source than provided.

**Solution**: Prominent, structured source identity block that model must echo back.

```
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  source_id: SRC_1                                        ║
║  title: "Interview with Creator X"                       ║
║  creator: "Channel Y"                                    ║
║  duration: 1:42:10                                       ║
║  analysis_mode: transcript_grounded                      ║
║  confidence_ceiling: high                                ║
╚══════════════════════════════════════════════════════════╝

REQUIREMENT: Your output MUST use exactly this source_id.
You may NOT change, guess, or infer different source identity.
If the content seems to reference a different source, FLAG IT — do not substitute.
```

**Validation**: Check that all output source_ids match provided source_id. Mismatch = hard failure.

**Complexity**: Prompt formatting + simple string validation.

---

# RECOMMENDATION 4: Explicit Null Permission

**Problem**: LLMs have a "helpfulness" instinct. When asked "what themes exist?" they'll find some, even if none are strong.

**Solution**: Explicitly permit empty outputs.

```
EMPTY OUTPUT PERMISSION

It is acceptable — and preferred — to return empty arrays if:
- No clear themes emerge (themes: [])
- No tensions exist (tensions: [])
- No gaps are identifiable (gaps: [])
- No quotes support a claim (supporting_quotes: [])

DO NOT invent content to fill arrays.
Sparse, accurate output is better than dense, hallucinated output.
A thin extraction from a thin source is CORRECT behavior.
```

**Why it works**: Counters the padding instinct. Model knows empty is okay.

**Complexity**: Prompt addition only.

---

# RECOMMENDATION 5: Source-Isolated Extraction

**Problem**: When processing multiple sources, model might bleed information between them (attribute quote from SRC_1 to SRC_2).

**Solution**: Extract each source in isolation. Synthesis happens only after all extractions complete.

```
EXTRACTION FLOW

Source 1 → Extraction Call 1 → Result 1
Source 2 → Extraction Call 2 → Result 2
Source 3 → Extraction Call 3 → Result 3

Then: [Result 1, Result 2, Result 3] → Synthesis Call → Themes, Tensions

RULE: Each extraction call receives ONLY ONE source.
Model never sees other sources during extraction.
Cross-source patterns identified only in synthesis.
```

**Why it works**: Model can't hallucinate connections between sources it can't see.

**Trade-off**: Multiple extraction calls instead of one. But prevents a major hallucination vector.

**Complexity**: Pipeline flow change, but same total work.

---

# RECOMMENDATION 6: Quote Verification (transcript_grounded only)

**Problem**: Model might hallucinate quotes that don't exist in transcript.

**Solution**: Post-extraction string matching.

```python
def verify_quotes(extraction: dict, transcript: str) -> list[str]:
    """Verify extracted quotes exist in transcript."""
    warnings = []
    
    for quote in extraction.get("supporting_quotes", []):
        quote_text = quote.get("text", "")
        
        # Normalize whitespace for matching
        normalized_quote = normalize(quote_text)
        normalized_transcript = normalize(transcript)
        
        if normalized_quote not in normalized_transcript:
            warnings.append(f"Quote not found in transcript: '{quote_text[:50]}...'")
            # Option: Remove quote from output
            # Option: Downgrade confidence
            # Option: Flag for retry
    
    return warnings
```

**Why it works**: Hallucinated quotes are caught programmatically. No LLM needed.

**Limitation**: Only works for transcript_grounded mode where we have text. Fuzzy matching needed for minor OCR/transcription variations.

**Complexity**: Simple string matching. Add to validation stage.

---

# RECOMMENDATION 7: Timestamp Sanity Check

**Problem**: Model outputs timestamp "47:32" for a 30-minute video.

**Solution**: Validate timestamps against known duration.

```python
def verify_timestamps(extraction: dict, duration_seconds: int) -> list[str]:
    """Check timestamps are within video duration."""
    warnings = []
    
    for quote in extraction.get("supporting_quotes", []):
        timestamp = quote.get("timestamp")
        if timestamp:
            seconds = parse_timestamp(timestamp)
            if seconds > duration_seconds:
                warnings.append(f"Timestamp {timestamp} exceeds video duration")
    
    return warnings
```

**Why it works**: Obvious errors caught cheaply.

**Complexity**: Simple math. Requires duration in source metadata.

---

# RECOMMENDATION 8: Entity Pre-Registration

**Problem**: Model invents entities not mentioned in source (adds "SEC" because fraud is discussed, even if SEC never mentioned).

**Solution**: Two-pass approach. First pass extracts entities. Second pass is constrained to only those entities.

**Simplified version**: Just validate post-extraction.

```python
def verify_entities(extraction: dict, transcript: str) -> list[str]:
    """Check that referenced entities appear in source."""
    warnings = []
    
    for entity in extraction.get("entities", []):
        entity_name = entity.get("name", "")
        if entity_name.lower() not in transcript.lower():
            warnings.append(f"Entity '{entity_name}' not found in source text")
    
    return warnings
```

**Complexity**: String matching validation.

---

# RECOMMENDATION 9: Proportional Extraction Guidance

**Problem**: Model extracts 10 themes from a 500-word article. Over-extraction from thin sources.

**Solution**: Pass word count and set expectations.

```
SOURCE METRICS
- Word count: 847 words
- Duration: N/A (text source)
- Density: Low-medium

PROPORTIONALITY GUIDANCE
This is a relatively short source. Your extraction should be proportionally sparse:
- Expect 2-4 key points maximum
- Expect 0-2 themes maximum
- If you're extracting more, you're likely over-interpreting

A thin source produces thin extraction. This is correct.
```

**Why it works**: Calibrates model expectations before it starts.

**Complexity**: Prompt addition. Word count already available.

---

# RECOMMENDATION 10: Structured Output Enforcement

**Problem**: Model adds unexpected fields, changes structure, or embeds explanations in data fields.

**Solution**: Strict JSON schema mode with rejection of non-conforming output.

```python
# Use Gemini's JSON mode with explicit schema
response = model.generate_content(
    prompt,
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": SemanticExtractionSchema
    }
)
```

**Combined with**: Post-extraction schema validation using Pydantic.

```python
from pydantic import BaseModel, ValidationError

class KeyPoint(BaseModel):
    key_point_id: str
    statement: str
    source_ids: list[str]  # Must be non-empty
    confidence: Literal["low", "medium", "high"]
    
    @validator('source_ids')
    def source_ids_not_empty(cls, v):
        if not v:
            raise ValueError('source_ids cannot be empty')
        return v
```

**Why it works**: Model can't drift if output shape is enforced.

**Complexity**: Schema definition + Pydantic validation.

---

# RECOMMENDATION 11: Assertion vs Question Framing

**Problem**: "What themes exist?" invites invention. Model feels obligated to find something.

**Solution**: Frame as conditional assertions.

```
THEME IDENTIFICATION

Do significant themes emerge from the patterns identified above?

A theme is significant if:
- It connects 2+ distinct key points
- It is explicitly discussed, not merely implied
- Multiple sources reference it (for multi-source jobs)

IF significant themes exist, list them with supporting key point IDs.
IF no significant themes emerge, return empty array. This is acceptable.

Do not create themes to fill space.
```

**Why it works**: Conditional framing + explicit criteria reduces invention.

**Complexity**: Prompt wording only.

---

# RECOMMENDATION 12: Scratchpad Reasoning (Optional)

**Problem**: Model makes logical leaps. No visibility into reasoning.

**Solution**: Require scratchpad that shows work, then extract only structured output.

```
RESPONSE FORMAT

<scratchpad>
[Show your reasoning here. What facts did you find? What patterns connect them?
This section is for your working — it will be discarded.]
</scratchpad>

<output>
{
  "key_points": [...],
  "themes": [...],
  ...
}
</output>
```

**Processing**: Parse out only `<output>` block. Scratchpad discarded but forces explicit reasoning.

**Why it works**: Model must articulate reasoning, which exposes gaps in logic.

**Trade-off**: More output tokens. May increase cost.

**Complexity**: Prompt change + parsing. Optional enhancement.

---

# RECOMMENDATION 13: Cross-Reference Source ID Repetition

**Problem**: Model assigns source_id once, then forgets to maintain it through nested objects.

**Solution**: Require source_id at every level.

```json
{
  "key_point_id": "KP_1",
  "statement": "...",
  "source_ids": ["SRC_1"],
  "supporting_claims": [
    {
      "claim_id": "CLM_1",
      "statement": "...",
      "source_id": "SRC_1",  // Repeated here
      "supporting_quotes": [
        {
          "quote_id": "QT_1",
          "text": "...",
          "source_id": "SRC_1"  // Repeated here too
        }
      ]
    }
  ]
}
```

**Validation**: Every nested object with source_id must match parent or be in parent's source_ids array.

**Why it works**: Repetition reinforces grounding. Validation catches any drift.

**Complexity**: Schema design + validation logic.

---

# RECOMMENDATION 14: Mode-Specific Prompt Variants

**Problem**: One generic prompt for all modes. Mode constraints buried in conditionals.

**Solution**: Separate prompt templates per mode with constraints baked in.

```
PROMPT_TRANSCRIPT_GROUNDED.md
- Quotes required
- High confidence allowed
- Precise timestamps expected

PROMPT_CAPTION_GROUNDED.md  
- Quotes allowed but marked approximate
- Medium confidence max
- Timestamps approximate

PROMPT_VIDEO_ONLY.md
- NO quotes section (field doesn't exist in this prompt)
- Low confidence only
- Timestamp ranges only
- Observations field used instead

PROMPT_TEXT_PROVIDED.md
- No quotes (user-provided content)
- Medium confidence max
- No timestamps

PROMPT_OCR_EXTRACTED.md
- No quotes
- Medium confidence max
- Missing context warning included
```

**Why it works**: Model never sees "quotes" field in video_only prompt. Can't fill what doesn't exist.

**Complexity**: Multiple prompt files. Router selects based on mode.

---

# RECOMMENDATION 15: Temperature Optimization

**Problem**: Default temperature may encourage creative output.

**Solution**: Use low temperature for extraction, slightly higher for synthesis.

```python
# Extraction: Precision matters, creativity doesn't
extraction_config = {
    "temperature": 0.1,  # Very low — deterministic
    "top_p": 0.8
}

# Synthesis: Slightly more flexibility for pattern recognition  
synthesis_config = {
    "temperature": 0.3,  # Still low, but allows some variation
    "top_p": 0.9
}

# Booster: More creative for directions
booster_config = {
    "temperature": 0.5,  # Moderate — want varied suggestions
    "top_p": 0.95
}
```

**Why it works**: Lower temperature = more deterministic = fewer hallucinations.

**Complexity**: Configuration change only.

---

# SUMMARY: IMPLEMENTATION PRIORITY

## High Priority (Implement First)

| # | Recommendation | Complexity | Impact |
|---|----------------|------------|--------|
| 1 | Layered Extraction Sequencing | Low (prompt) | High |
| 2 | Confidence Pre-Declaration | Low (prompt) | High |
| 3 | Source Identity Lock Block | Low (prompt) | High |
| 4 | Explicit Null Permission | Low (prompt) | Medium |
| 5 | Source-Isolated Extraction | Medium (flow) | High |
| 14 | Mode-Specific Prompt Variants | Medium (files) | High |

## Medium Priority (Implement Second)

| # | Recommendation | Complexity | Impact |
|---|----------------|------------|--------|
| 6 | Quote Verification | Low (code) | Medium |
| 7 | Timestamp Sanity Check | Low (code) | Medium |
| 10 | Structured Output Enforcement | Medium (schema) | High |
| 11 | Assertion vs Question Framing | Low (prompt) | Medium |
| 13 | Source ID Repetition | Low (schema) | Medium |
| 15 | Temperature Optimization | Low (config) | Medium |

## Lower Priority (Implement If Needed)

| # | Recommendation | Complexity | Impact |
|---|----------------|------------|--------|
| 8 | Entity Pre-Registration | Medium (code) | Low |
| 9 | Proportional Extraction Guidance | Low (prompt) | Low |
| 12 | Scratchpad Reasoning | Medium (parsing) | Medium |

---

# VALIDATION STAGE ENHANCEMENT

Based on recommendations above, validation stage should check:

```python
def validate_extraction(
    extraction: dict,
    source_metadata: SourceMetadata,
    transcript: Optional[str],
    mode: str
) -> ValidationResult:
    """Comprehensive extraction validation."""
    
    errors = []
    warnings = []
    
    # 1. Schema validation (Rec 10)
    try:
        validated = SemanticExtractionSchema.parse_obj(extraction)
    except ValidationError as e:
        errors.append(f"Schema validation failed: {e}")
        return ValidationResult(valid=False, errors=errors)
    
    # 2. Source ID consistency (Rec 3, 13)
    source_ids_used = collect_all_source_ids(extraction)
    for sid in source_ids_used:
        if sid != source_metadata.source_id:
            errors.append(f"Invalid source_id: {sid}")
    
    # 3. Confidence ceiling (Rec 2)
    ceiling = get_confidence_ceiling(mode)
    for kp in extraction.get("key_points", []):
        if confidence_exceeds(kp.get("confidence"), ceiling):
            warnings.append(f"Confidence exceeds ceiling for {kp.get('key_point_id')}")
            kp["confidence"] = ceiling  # Auto-correct
    
    # 4. Quote verification (Rec 6) — transcript_grounded only
    if mode == "transcript_grounded" and transcript:
        quote_warnings = verify_quotes(extraction, transcript)
        warnings.extend(quote_warnings)
    
    # 5. Timestamp sanity (Rec 7)
    if source_metadata.duration_seconds:
        ts_warnings = verify_timestamps(extraction, source_metadata.duration_seconds)
        warnings.extend(ts_warnings)
    
    # 6. Mode rule enforcement (Rec 14)
    if mode == "video_only":
        if extraction.get("supporting_quotes"):
            errors.append("Quotes present in video_only mode")
    
    # 7. Grounding check — key points have source_ids
    for kp in extraction.get("key_points", []):
        if not kp.get("source_ids"):
            errors.append(f"Ungrounded key point: {kp.get('key_point_id')}")
    
    # 8. Theme support check — themes have 2+ key points
    for theme in extraction.get("themes", []):
        if len(theme.get("related_key_points", [])) < 2:
            warnings.append(f"Theme {theme.get('theme_id')} has insufficient support")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        corrected_extraction=extraction
    )
```

---

# PROMPT TEMPLATE STRUCTURE

Based on recommendations, extraction prompt should follow this structure:

```markdown
# SYSTEM CONTEXT
[Role definition, task description]

# SOURCE IDENTITY LOCK (Rec 3)
╔═══════════════════════════════════════╗
║  source_id: {source_id}               ║
║  title: {title}                       ║
║  ...                                  ║
╚═══════════════════════════════════════╝

# CONFIDENCE CEILING (Rec 2)
Your maximum confidence is: {ceiling}
You may NOT exceed this.

# EXTRACTION LAYERS (Rec 1)
[Layer 1, 2, 3 instructions]

# EMPTY OUTPUT PERMISSION (Rec 4)
[Permission to return empty arrays]

# PROPORTIONALITY (Rec 9)
Source word count: {word_count}
[Calibration guidance]

# OUTPUT SCHEMA (Rec 10)
[Exact JSON structure required]

# MODE-SPECIFIC RULES (Rec 14)
[Rules for this specific mode]

# SOURCE CONTENT
{transcript or content}
```

---

**END OF DOCUMENT**
