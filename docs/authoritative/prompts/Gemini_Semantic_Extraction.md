# Gemini Semantic Extraction Prompt

**Purpose:** Authoritative prompt template for extracting semantic content from a single source.
**Model:** Gemini 2.5 Pro
**Temperature:** 0.1
**Response Format:** JSON (response_mime_type: application/json)

---

## Critical Rules

1. **One source per call** — This prompt processes exactly ONE source in isolation
2. **Source identity is pre-resolved** — All metadata comes from the system, not LLM inference
3. **Confidence ceiling is enforced** — Output cannot exceed the declared ceiling
4. **Empty output is permitted** — Sparse accurate output beats dense hallucinated output
5. **All 5 components required** — Do not send prompt without all components

---

## Prompt Template

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SOURCE IDENTITY LOCK — DO NOT MODIFY                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  source_id:          {source_id}                                             ║
║  title:              {title}                                                 ║
║  creator:            {creator}                                               ║
║  date:               {date}                                                  ║
║  duration:           {duration}                                              ║
║  analysis_mode:      {analysis_mode}                                         ║
║  confidence_ceiling: {confidence_ceiling}                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are extracting semantic content from the source identified above.

══════════════════════════════════════════════════════════════════════════════
CONFIDENCE CEILING: {confidence_ceiling_upper}
══════════════════════════════════════════════════════════════════════════════

Your MAXIMUM allowed confidence for ANY output is: {confidence_ceiling_upper}

- If confidence_ceiling is HIGH: you may use high, medium, or low
- If confidence_ceiling is MEDIUM: you may use medium or low (NEVER high)
- If confidence_ceiling is LOW: you may ONLY use low

Any output with confidence exceeding this ceiling will be REJECTED by validation.
When uncertain, use a LOWER confidence level.

══════════════════════════════════════════════════════════════════════════════
EMPTY OUTPUT PERMISSION
══════════════════════════════════════════════════════════════════════════════

It is ACCEPTABLE — and PREFERRED — to return empty arrays if:
- No clear key points emerge from the content
- No tensions exist within this source
- No verifiable claims are made
- The content is off-topic or uninformative

DO NOT invent content to fill arrays.
DO NOT pad results to meet quantity expectations.
Sparse, accurate output >>> Dense, hallucinated output

══════════════════════════════════════════════════════════════════════════════
EXTRACTION LAYERS — Process in this order
══════════════════════════════════════════════════════════════════════════════

LAYER 1 — EXPLICIT CONTENT
What does the source EXPLICITLY state?
- Direct statements made by speakers/authors
- Specific facts or claims presented
- Quoted material or cited information

Rules for Layer 1:
- DO NOT interpret
- DO NOT infer meaning
- DO NOT add context not present
- If speaker says X, record X (not what X might mean)

LAYER 2 — PATTERNS
What patterns exist in Layer 1 content?
- Repeated ideas or themes
- Connected statements
- Logical groupings

Rules for Layer 2:
- Every pattern MUST reference Layer 1 items
- No pattern without explicit support
- Note which Layer 1 items support each pattern

LAYER 3 — STRUCTURAL ELEMENTS  
What themes, tensions, and gaps emerge from Layer 2?
- Overarching themes that unite patterns
- Internal tensions or contradictions
- Gaps or missing information

Rules for Layer 3:
- Must derive ONLY from Layer 2
- Cannot introduce new information
- Mark confidence appropriately

══════════════════════════════════════════════════════════════════════════════
{quote_or_observation_instructions}
══════════════════════════════════════════════════════════════════════════════

══════════════════════════════════════════════════════════════════════════════
SOURCE CONTENT
══════════════════════════════════════════════════════════════════════════════

{source_content}

══════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA
══════════════════════════════════════════════════════════════════════════════

Return valid JSON matching this exact structure:

{output_schema}

CRITICAL REQUIREMENTS:
- source_id must be exactly: {source_id}
- All IDs must use the format specified (KP_1, CLM_1, etc.)
- confidence values must not exceed {confidence_ceiling_upper}
- All arrays may be empty if no valid content found
- Do not include fields not in the schema
```

---

## Component Templates

### Quote Instructions (for transcript_grounded, caption_grounded, article_fetched)

```
QUOTE EXTRACTION RULES

You MUST extract verbatim quotes from the source.

For each quote:
- text: The EXACT words from the source (no paraphrasing)
- speaker: Who said it (if identifiable)
- timestamp: When it was said (format: "MM:SS" or "HH:MM:SS")
- context: Brief note on what was being discussed

Quote Selection Criteria:
- Prioritize quotes that support key points
- Prioritize quotes with strong claims or revelations
- Prioritize quotes that capture the source's main arguments
- Include quotes that might be controversial or contested

DO NOT:
- Paraphrase or clean up quotes
- Invent quotes not in the source
- Combine multiple statements into one quote
```

### Observation Instructions (for video_only, text_provided, ocr_extracted)

```
OBSERVATION EXTRACTION RULES

You are operating in {analysis_mode} mode.
Verbatim quotes are NOT AVAILABLE for this source.

Instead of quotes, extract APPROXIMATE OBSERVATIONS:
- description: What you observed (semantic description, NOT verbatim)
- timestamp: Approximate time (format: "~MM:SS")
- type: Always "observation"
- approximate: Always true

Observation Guidelines:
- Describe WHAT was communicated, not exact words
- Use phrases like "The speaker discusses...", "The content shows..."
- Note visual elements if relevant
- Be conservative — only observe what's clearly present

DO NOT:
- Present observations as direct quotes
- Use quotation marks in descriptions
- Claim verbatim accuracy
```

---

## Output Schema

### For Modes WITH Quotes (transcript_grounded, caption_grounded, article_fetched)

```json
{
  "source_id": "string — must match input exactly",
  "analysis_mode": "string — must match input exactly",
  "extraction_metadata": {
    "extracted_at": "ISO-8601 timestamp",
    "model": "gemini-2.5-pro",
    "confidence_ceiling": "high | medium | low"
  },
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "string — clear statement of the key point",
      "confidence": "high | medium | low",
      "timestamp": "MM:SS or null",
      "supporting_quote_ids": ["QT_1"]
    }
  ],
  "claims": [
    {
      "claim_id": "CLM_1",
      "statement": "string — the claim as stated",
      "speaker": "string or null",
      "timestamp": "MM:SS or null",
      "confidence": "high | medium | low",
      "verifiable": true | false,
      "claim_type": "factual | opinion | prediction"
    }
  ],
  "quotes": [
    {
      "quote_id": "QT_1",
      "text": "string — verbatim quote",
      "speaker": "string or null",
      "timestamp": "MM:SS or null",
      "context": "string — brief context"
    }
  ],
  "themes": [
    {
      "theme_id": "THEME_1",
      "name": "string — short theme name",
      "description": "string — what this theme represents",
      "supporting_key_point_ids": ["KP_1", "KP_2"]
    }
  ],
  "tensions": [
    {
      "tension_id": "TEN_1",
      "description": "string — what the tension is",
      "nature": "internal_contradiction | ambiguity | unresolved_question",
      "related_key_point_ids": ["KP_1", "KP_3"]
    }
  ],
  "entities": [
    {
      "name": "string",
      "type": "person | organization | place | event | concept",
      "first_mention_timestamp": "MM:SS or null"
    }
  ],
  "gaps": [
    {
      "gap_id": "GAP_1",
      "description": "string — what information is missing",
      "importance": "high | medium | low"
    }
  ]
}
```

### For Modes WITHOUT Quotes (video_only, text_provided, ocr_extracted)

```json
{
  "source_id": "string — must match input exactly",
  "analysis_mode": "string — must match input exactly",
  "extraction_metadata": {
    "extracted_at": "ISO-8601 timestamp",
    "model": "gemini-2.5-pro",
    "confidence_ceiling": "high | medium | low"
  },
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "string — clear statement of the key point",
      "confidence": "high | medium | low",
      "timestamp": "~MM:SS or null",
      "supporting_observation_ids": ["OBS_1"]
    }
  ],
  "claims": [
    {
      "claim_id": "CLM_1",
      "statement": "string — the claim as observed",
      "speaker": "string or null",
      "timestamp": "~MM:SS or null",
      "confidence": "low",
      "verifiable": true | false,
      "claim_type": "factual | opinion | prediction"
    }
  ],
  "approximate_observations": [
    {
      "observation_id": "OBS_1",
      "description": "string — semantic description of observed content",
      "timestamp": "~MM:SS or null",
      "type": "observation",
      "approximate": true
    }
  ],
  "themes": [
    {
      "theme_id": "THEME_1",
      "name": "string — short theme name",
      "description": "string — what this theme represents",
      "supporting_key_point_ids": ["KP_1", "KP_2"]
    }
  ],
  "tensions": [
    {
      "tension_id": "TEN_1",
      "description": "string — what the tension is",
      "nature": "internal_contradiction | ambiguity | unresolved_question",
      "related_key_point_ids": ["KP_1", "KP_3"]
    }
  ],
  "entities": [
    {
      "name": "string",
      "type": "person | organization | place | event | concept",
      "first_mention_timestamp": "~MM:SS or null"
    }
  ],
  "gaps": [
    {
      "gap_id": "GAP_1",
      "description": "string — what information is missing",
      "importance": "high | medium | low"
    }
  ]
}
```

**Key Difference:** `quotes` array replaced with `approximate_observations` array.

---

## Mode-Specific Configuration

| Mode | Quote Instructions | Schema | Max Claim Confidence |
|------|-------------------|--------|---------------------|
| `transcript_grounded` | Use Quote template | With quotes | high |
| `caption_grounded` | Use Quote template | With quotes | medium |
| `video_only` | Use Observation template | Without quotes | low |
| `text_provided` | Use Observation template | Without quotes | medium |
| `ocr_extracted` | Use Observation template | Without quotes | medium |
| `article_fetched` | Use Quote template | With quotes | high |

---

## Retry Prompt Addition

If validation fails and retry is needed, prepend this block:

```
══════════════════════════════════════════════════════════════════════════════
RETRY CONTEXT — Previous attempt failed validation
══════════════════════════════════════════════════════════════════════════════

Error: {validation_error}

Instructions for this retry:
- Be MORE conservative in extraction
- Prefer FEWER, higher-quality items over many low-quality items
- If uncertain about any item, OMIT it rather than guess
- Empty arrays are ACCEPTABLE
- Ensure all confidence values are at or below: {confidence_ceiling_upper}
- Ensure source_id is exactly: {source_id}

```

---

## Implementation Notes

### Building the Prompt

```python
def build_extraction_prompt(
    source_id: str,
    title: str,
    creator: str,
    date: str,
    duration: str,
    analysis_mode: AnalysisMode,
    confidence_ceiling: ConfidenceLevel,
    source_content: str,
    is_retry: bool = False,
    retry_error: str = None,
) -> str:
    """Build the semantic extraction prompt for a single source."""
    
    # Determine quote vs observation instructions
    if analysis_mode in [AnalysisMode.TRANSCRIPT_GROUNDED, 
                          AnalysisMode.CAPTION_GROUNDED,
                          AnalysisMode.ARTICLE_FETCHED]:
        quote_instructions = QUOTE_INSTRUCTIONS_TEMPLATE
        output_schema = SCHEMA_WITH_QUOTES
    else:
        quote_instructions = OBSERVATION_INSTRUCTIONS_TEMPLATE.format(
            analysis_mode=analysis_mode.value
        )
        output_schema = SCHEMA_WITHOUT_QUOTES
    
    # Build main prompt
    prompt = MAIN_TEMPLATE.format(
        source_id=source_id,
        title=title,
        creator=creator or "Unknown",
        date=date or "Unknown",
        duration=duration or "N/A",
        analysis_mode=analysis_mode.value,
        confidence_ceiling=confidence_ceiling.value,
        confidence_ceiling_upper=confidence_ceiling.value.upper(),
        quote_or_observation_instructions=quote_instructions,
        source_content=source_content,
        output_schema=json.dumps(output_schema, indent=2),
    )
    
    # Add retry context if needed
    if is_retry:
        retry_block = RETRY_TEMPLATE.format(
            validation_error=retry_error,
            confidence_ceiling_upper=confidence_ceiling.value.upper(),
            source_id=source_id,
        )
        prompt = retry_block + prompt
    
    return prompt
```

### Calling Gemini

```python
def extract_source(
    source_package: SourceIdentityPackage,
    source_content: str,
) -> SemanticExtractionResult:
    """Extract semantic content from a single source."""
    
    prompt = build_extraction_prompt(
        source_id=source_package.source_id,
        title=source_package.title,
        creator=source_package.creator,
        date=source_package.date,
        duration=source_package.duration,
        analysis_mode=source_package.analysis_mode,
        confidence_ceiling=source_package.confidence_ceiling,
        source_content=source_content,
    )
    
    result = gemini_client.generate_json(
        prompt=prompt,
        temperature=0.1,
        model="gemini-2.5-pro",
    )
    
    if result.get("error"):
        raise ExtractionError(result["error"])
    
    return SemanticExtractionResult(**result["data"])
```

---

## Validation After Extraction

The extraction result must pass these checks (see Validation_and_Retry_Rules.md):

1. **V1:** Valid JSON matching schema
2. **V2:** `source_id` matches input exactly
3. **V3:** No confidence exceeds ceiling
4. **V4:** Quotes verified against source text (if applicable)
5. **V5:** No quotes in no-quote modes

---

## Example: Complete Prompt Instance

For a `transcript_grounded` YouTube video:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SOURCE IDENTITY LOCK — DO NOT MODIFY                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  source_id:          SRC_1                                                   ║
║  title:              The Rise and Fall of TechStartup                        ║
║  creator:            TechExplained                                           ║
║  date:               2026-01-10                                              ║
║  duration:           18:42                                                   ║
║  analysis_mode:      transcript_grounded                                     ║
║  confidence_ceiling: high                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are extracting semantic content from the source identified above.

══════════════════════════════════════════════════════════════════════════════
CONFIDENCE CEILING: HIGH
══════════════════════════════════════════════════════════════════════════════

Your MAXIMUM allowed confidence for ANY output is: HIGH

- If confidence_ceiling is HIGH: you may use high, medium, or low
- If confidence_ceiling is MEDIUM: you may use medium or low (NEVER high)
- If confidence_ceiling is LOW: you may ONLY use low

Any output with confidence exceeding this ceiling will be REJECTED by validation.
When uncertain, use a LOWER confidence level.

══════════════════════════════════════════════════════════════════════════════
EMPTY OUTPUT PERMISSION
══════════════════════════════════════════════════════════════════════════════

It is ACCEPTABLE — and PREFERRED — to return empty arrays if:
- No clear key points emerge from the content
- No tensions exist within this source
- No verifiable claims are made
- The content is off-topic or uninformative

DO NOT invent content to fill arrays.
DO NOT pad results to meet quantity expectations.
Sparse, accurate output >>> Dense, hallucinated output

══════════════════════════════════════════════════════════════════════════════
EXTRACTION LAYERS — Process in this order
══════════════════════════════════════════════════════════════════════════════

LAYER 1 — EXPLICIT CONTENT
What does the source EXPLICITLY state?
...

[Rest of prompt continues with quote instructions, source content, and schema]
```

---

**END OF PROMPT CONTRACT**
