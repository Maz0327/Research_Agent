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

**CHECKPOINT 1 — Before proceeding to Layer 2:**
- [ ] Every quote exists VERBATIM in the source text
- [ ] Every claim has supporting text I can point to
- [ ] No specific numbers, dates, or names were added that aren't in the source
- [ ] Confidence levels match evidence strength (explicit = high, approximate = medium)

If any check fails, REVISE Layer 1 output before continuing.

### LAYER 2: PATTERNS
Identify patterns WITHIN Layer 1 content.
- Recurring topics or themes
- Repeated assertions
- Consistent framing

Every pattern MUST reference specific Layer 1 items.

**CHECKPOINT 2 — Before proceeding to Layer 3:**
- [ ] Every pattern references at least 2 Layer 1 items
- [ ] Patterns are derived from Layer 1, not external knowledge
- [ ] No new claims or quotes were introduced in Layer 2

If any check fails, REVISE Layer 2 output before continuing.

### LAYER 3: STRUCTURAL ELEMENTS
Identify higher-order structures:
- Themes (patterns spanning multiple key points)
- Tensions (contradictions or shifts in meaning)
- Gaps (what's missing or unexplained)

MUST derive from Layer 2 only. No external inference.

**CHECKPOINT 3 — Before finalizing output:**
- [ ] Themes reference 2+ key points that exist in Layer 1
- [ ] Tensions cite specific key points involved
- [ ] Gaps identify what's MISSING, not what's INFERRED
- [ ] No external knowledge has been injected anywhere
- [ ] confidence_rationale explains each confidence decision
"""


# =============================================================================
# COMPONENT 6: Chain-of-Thought Reasoning (Hallucination Prevention)
# =============================================================================

CHAIN_OF_THOUGHT_SECTION = """
## REASONING PROCESS (Required)

Before generating your final output, complete these reasoning steps internally:

### Step 1: Content Inventory
List the key elements present in the source:
- Main topics or subjects discussed
- Speakers or entities mentioned
- Explicit claims or statements made
- Time periods, dates, or events referenced

### Step 2: Evidence Assessment
For each potential key point you will extract:
- What specific text supports this assertion?
- Is this explicit in the source or inferred?
- What confidence level is appropriate given the evidence?

### Step 3: Gap and Hallucination Check
Before finalizing your output, verify:
- [ ] Every claim has direct textual evidence
- [ ] Every quote appears verbatim in the source (if quotes allowed)
- [ ] Confidence levels match evidence strength
- [ ] No external knowledge has been injected
- [ ] No assumptions fill gaps in the source

Include your reasoning summary in the "reasoning_trace" field.
Format: ["Step 1: Found X topics...", "Step 2: Evidence for KP_1...", "Step 3: Verified no hallucinations..."]
"""


# =============================================================================
# COMPONENT 7: Anti-Hallucination Examples
# =============================================================================

ANTI_HALLUCINATION_EXAMPLES = """
## ANTI-HALLUCINATION GUIDE

### BAD Examples — DO NOT DO THIS:

1. **Invented Quote**
   Source says: "The company grew quickly"
   BAD extraction: "CEO stated 'We achieved 300% growth in Q1'"
   Why: Specific numbers and attribution not in source

2. **Overclaiming Confidence**
   Source says: "around 2010 or so"
   BAD: {"confidence": "high", "statement": "Event occurred in 2010"}
   GOOD: {"confidence": "medium", "statement": "Event occurred approximately 2010"}

3. **Inference Presented as Fact**
   Source shows: Person disagreeing in meeting
   BAD: "The CEO was angry about the decision"
   GOOD: "The CEO expressed disagreement with the decision"

4. **Fabricated Details**
   Source says: "The company raised funding"
   BAD: "The company raised $50M in Series A funding"
   GOOD: "The company raised funding (amount not specified)"

5. **Filling Gaps with External Knowledge**
   Source discusses: A tech company's challenges
   BAD: "Like other companies such as Theranos and WeWork..."
   Why: External examples not mentioned in source

### GOOD Examples — DO THIS:

1. **Accurate Quote with Context**
   {"quote_id": "QT_1", "text": "We grew quickly", "timestamp": "2:34", "speaker": "CEO"}

2. **Appropriate Confidence**
   {"confidence": "medium", "statement": "Event occurred around 2010", "confidence_rationale": "Source used approximate language"}

3. **Observable Facts Only**
   "The speaker disagreed with the proposed timeline"

4. **Acknowledge Gaps**
   "Funding was raised (specific amount not disclosed in source)"

5. **Stay Within Source**
   "The company faced challenges similar to those described by the speaker"
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
      "label": "Short title (3-6 words)",
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
    include_chain_of_thought: bool = True,
    include_anti_hallucination_examples: bool = True,
) -> str:
    """Build a complete prompt with all required components.

    Args:
        source_id: Stable source identifier
        source_content: Full source text
        title: Source title
        analysis_mode: Mode string
        confidence_ceiling: "HIGH", "MEDIUM", or "LOW"
        mode_specific_instructions: Mode-specific rules and constraints
        quote_schema_extension: Additional schema for quotes (if allowed)
        include_chain_of_thought: Include CoT reasoning section (default True)
        include_anti_hallucination_examples: Include examples (default True)

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

    # Add reasoning_trace field to schema
    reasoning_schema_extension = """
ADDITIONAL REQUIRED FIELD:
```json
{
  "reasoning_trace": [
    "Step 1: Content inventory - found topics X, Y, Z...",
    "Step 2: Evidence assessment - KP_1 supported by text at 2:34...",
    "Step 3: Verified all claims grounded, no hallucinations detected"
  ]
}
```
"""

    # Build optional sections
    cot_section = CHAIN_OF_THOUGHT_SECTION if include_chain_of_thought else ""
    anti_hallucination_section = ANTI_HALLUCINATION_EXAMPLES if include_anti_hallucination_examples else ""

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

{cot_section}

---

{anti_hallucination_section}

---

## SOURCE CONTENT

{source_content}

---

{mode_specific_instructions}

---

{output_schema}

{quote_schema_extension}

{reasoning_schema_extension}

---

{QUALITY_CONSTRAINTS}
"""

    return prompt
