"""Shared prompt components for all analysis modes.

Contains the 5 required components per architecture rules:
1. Source Identity Lock Block
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction Instructions
5. Output Schema (base version - modes may extend)

All mode-specific prompts import from here to ensure consistency.
"""

# =============================================================================
# COMPONENT 1: Source Identity Lock Block
# =============================================================================

SOURCE_IDENTITY_LOCK_BLOCK = """
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  source_id: {source_id}                                  ║
║  title: {title}                                          ║
║  analysis_mode: {analysis_mode}                          ║
║  confidence_ceiling: {confidence_ceiling}                ║
╚══════════════════════════════════════════════════════════╝

The source_id and metadata above are CANONICAL. You MUST NOT:
- Guess or infer which source this is
- Substitute or correct source metadata
- Assume information not explicitly provided
- Reference external knowledge about this topic
"""


# =============================================================================
# COMPONENT 2: Confidence Ceiling Declaration
# =============================================================================

CONFIDENCE_CEILING_DECLARATION = """
## CONFIDENCE CEILING: {confidence_ceiling}

Your MAXIMUM allowed confidence for any output is: {confidence_ceiling}

Confidence Enforcement Rules:
- Any key_point or claim with confidence > {confidence_ceiling} will be REJECTED
- This ceiling is NON-NEGOTIABLE regardless of source quality
- When uncertain, use LOWER confidence, never higher

Ceiling Meanings:
- HIGH: Verbatim transcript available, quotes verified
- MEDIUM: Content available but may have errors (captions, OCR, unverified)
- LOW: No transcript, visual inference only
"""


# =============================================================================
# COMPONENT 3: Empty Output Permission
# =============================================================================

EMPTY_OUTPUT_PERMISSION = """
## EMPTY OUTPUT PERMISSION

It is ACCEPTABLE to return empty arrays if:
- No clear themes emerge from the content
- No tensions or contradictions exist
- No relevant claims or key points are found
- Content is too brief or unclear for extraction

DO NOT invent content to fill arrays.
DO NOT pad output with generic or speculative items.

Sparse, accurate output > dense, hallucinated output.

If arrays are empty, explain why in "extraction_warnings":
```json
{{
  "themes": [],
  "extraction_warnings": ["themes empty: Single-topic content with no recurring patterns"]
}}
```
"""


# =============================================================================
# COMPONENT 4: Layered Extraction Instructions
# =============================================================================

LAYERED_EXTRACTION_INSTRUCTIONS = """
## EXTRACTION LAYERS — Process in Order

### LAYER 1: EXPLICIT CONTENT
Extract what the source EXPLICITLY states.
- Verbatim quotes (if allowed for this mode)
- Direct assertions
- Stated facts and claims
- Named entities and relationships

DO NOT interpret. DO NOT infer.

### LAYER 2: PATTERNS
Identify patterns WITHIN Layer 1 content.
- Recurring topics or themes
- Repeated assertions
- Consistent framing

Every pattern MUST reference specific Layer 1 items.

### LAYER 3: STRUCTURAL ELEMENTS
Identify higher-order structures:
- Themes (patterns spanning multiple key points)
- Tensions (contradictions or shifts in meaning)
- Gaps (what's missing or unexplained)

MUST derive from Layer 2 only. No external inference.
"""


# =============================================================================
# COMPONENT 5: Base Output Schema
# =============================================================================

BASE_OUTPUT_SCHEMA = """
## OUTPUT FORMAT — JSON ONLY

Return ONLY valid JSON matching this structure:

```json
{{
  "source_id": "{source_id}",
  "analysis_mode": "{analysis_mode}",

  "key_points": [
    {{
      "key_point_id": "KP_1",
      "statement": "Neutral assertion derived from source",
      "supporting_claims": ["CLM_1"],
      "confidence": "high | medium | low"
    }}
  ],

  "claims": [
    {{
      "claim_id": "CLM_1",
      "statement": "Declarative statement from source",
      "supporting_quotes": ["QT_1"]
    }}
  ],

  "themes": [
    {{
      "theme_id": "THEME_1",
      "label": "Pattern description (NOT topic)",
      "related_key_points": ["KP_1", "KP_2"]
    }}
  ],

  "tensions": [
    {{
      "tension_id": "TEN_1",
      "description": "Contradiction or meaning shift",
      "involved_key_points": ["KP_1", "KP_3"]
    }}
  ],

  "extraction_warnings": []
}}
```

ID FORMAT REQUIREMENTS:
- source_id: SRC_1, SRC_2, ...
- key_point_id: KP_1, KP_2, ...
- claim_id: CLM_1, CLM_2, ...
- quote_id: QT_1, QT_2, ...
- theme_id: THEME_1, THEME_2, ...
- tension_id: TEN_1, TEN_2, ...
"""


# =============================================================================
# ROLE DEFINITION
# =============================================================================

SEMANTIC_ANALYST_ROLE = """You are a semantic research analyst.

Your job is NOT to summarize, explain, persuade, or conclude.

Your job is to:
- Extract meaning from source material
- Identify patterns and structures
- Surface tensions and contradictions
- Preserve uncertainty
- Stay grounded in source material

You must remain neutral, descriptive, and cautious.
You do not write narratives.
You do not decide what is true.
You do not fill gaps with assumptions."""


# =============================================================================
# QUALITY CONSTRAINTS (shared across modes)
# =============================================================================

QUALITY_CONSTRAINTS = """
## QUALITY CONSTRAINTS

### Key Points
- Must be SPECIFIC (not abstract)
- Must be GROUNDED (traceable to source)
- Must be NEUTRAL (no opinion or framing)

BAD: "The video discusses controversy."
GOOD: "The speaker gives conflicting accounts of when funding was secured."

### Themes
- Must describe PATTERNS, not topics
- Must span 2+ key points

BAD: "Funding"
GOOD: "Inconsistent explanations regarding funding sources"

### Tensions
- Surface contradictions, do NOT resolve them
- Cite all involved key points
- System is not arbiter of truth

### Minimum Requirements
For long-form content (30+ minutes or 3000+ words):
- At least 3 key points
- At least 2 themes
- Each theme references 2+ key points
"""


# =============================================================================
# HELPER: Build prompt with all 5 components
# =============================================================================

def build_base_prompt(
    source_id: str,
    source_content: str,
    title: str,
    analysis_mode: str,
    confidence_ceiling: str,
    mode_specific_instructions: str,
    quote_schema_extension: str = "",
) -> str:
    """Build a complete prompt with all 5 required components.

    Args:
        source_id: Stable source identifier
        source_content: Full source text
        title: Source title
        analysis_mode: Mode string
        confidence_ceiling: "HIGH", "MEDIUM", or "LOW"
        mode_specific_instructions: Mode-specific rules and constraints
        quote_schema_extension: Additional schema for quotes (if allowed)

    Returns:
        Complete prompt string
    """
    # Component 1: Lock block
    lock_block = SOURCE_IDENTITY_LOCK_BLOCK.format(
        source_id=source_id,
        title=title,
        analysis_mode=analysis_mode,
        confidence_ceiling=confidence_ceiling,
    )

    # Component 2: Ceiling declaration
    ceiling_declaration = CONFIDENCE_CEILING_DECLARATION.format(
        confidence_ceiling=confidence_ceiling,
    )

    # Component 5: Output schema (with optional quote extension)
    output_schema = BASE_OUTPUT_SCHEMA.format(
        source_id=source_id,
        analysis_mode=analysis_mode,
    )

    # Assemble all components
    prompt = f"""{SEMANTIC_ANALYST_ROLE}

---

{lock_block}

---

{ceiling_declaration}

---

{EMPTY_OUTPUT_PERMISSION}

---

{LAYERED_EXTRACTION_INSTRUCTIONS}

---

## SOURCE CONTENT

{source_content}

---

{mode_specific_instructions}

---

{output_schema}

{quote_schema_extension}

---

{QUALITY_CONSTRAINTS}
"""

    return prompt
