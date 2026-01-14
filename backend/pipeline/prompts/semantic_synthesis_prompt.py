"""Semantic Synthesis Prompt - Produces Doc 2: Semantic Research Brief.

Based on: docs/authoritative/prompts/Semantic_Synthesis.md

Gemini's role here is research synthesizer, not analyst, narrator, or storyteller.
This prompt NEVER sees raw source text - only previously extracted structure.
"""

# Role definition for system message
SEMANTIC_SYNTHESIS_ROLE = """You are a research synthesizer.

You do NOT analyze raw sources.
You do NOT discover new facts.
You do NOT invent claims or conclusions.

You synthesize meaning ONLY from:
- Key Points
- Themes
- Tensions
- Gaps

Your job is to externalize structured understanding,
not to decide what is true or what story should be told."""


# Primary synthesis prompt
SEMANTIC_SYNTHESIS_PROMPT = """## HIGHEST PRIORITY CONSTRAINT

You have ONLY the JSON input provided. You have NO other knowledge.
Any fact, name, date, or claim NOT in this JSON is FABRICATION.
Before each sentence, ask: "Which source_id supports this?"
If no source_id supports it, DELETE the sentence.

---

## INPUT (STRICT)

You receive ONLY:
- Scope Lock: {scope_lock}
- Key Points (with IDs + sources): {key_points_json}
- Themes (with IDs): {themes_json}
- Tensions (if present): {tensions_json}
- Gaps: {gaps_json}
- Confidence signals:
  - Verification rate: {verification_rate}
  - Source diversity: {source_diversity}

You must not request additional input.

---

## SYNTHESIS TASKS (ORDER MATTERS)

### Task 1 — Identify the Semantic Core

**Definition:**
The Semantic Core explains *what this topic is fundamentally about beneath surface details*

**Rules:**
- 2–4 sentences maximum
- No conclusions
- No moral judgments
- No speculation

BAD: "This is a story about corruption and cover-ups."
GOOD: "This topic centers on conflicting accounts of decision-making processes and the absence of primary documentation to resolve those conflicts."

---

### Task 2 — Organize Themes

For each Theme:
- Brief description of what it represents
- List supporting Key Points
- No interpretation beyond description

**Theme Requirements:**
- Minimum total themes: 2
- Each theme must reference ≥2 Key Points
- If fewer than 2 themes emerge, this is valid but triggers confidence downgrade

---

### Task 3 — Surface Tensions & Competing Interpretations

If Tensions exist:
- Describe the nature of the disagreement
- Explain *why* it matters for understanding
- Do NOT resolve the tension

---

### Task 4 — Contextualize Gaps

For each Gap:
- Explain how the gap limits understanding
- Explain what kind of information would reduce uncertainty
- Do NOT speculate about what the missing info would show

---

### Task 5 — Optional Speculative Observations (Explicit)

Only if there is sufficient structure.

Speculation must:
- Be explicitly labeled
- Reference supporting Key Points
- Be framed as *possible interpretations*, not truths

---

## OUTPUT FORMAT (JSON ONLY)

{{
  "semantic_core": {{
    "text": "...",
    "based_on": ["KP_1", "KP_4"]
  }},
  "themes": [
    {{
      "theme_id": "THEME_1",
      "description": "...",
      "supporting_key_points": ["KP_2", "KP_5"]
    }}
  ],
  "tensions": [
    {{
      "tension_id": "TEN_1",
      "description": "...",
      "involved_key_points": ["KP_3", "KP_6"]
    }}
  ],
  "gaps": [
    {{
      "gap_id": "GAP_1",
      "impact_on_understanding": "...",
      "what_would_help": "..."
    }}
  ],
  "speculative_observations": [
    {{
      "text": "...",
      "based_on": ["KP_2", "KP_7"],
      "label": "speculative"
    }}
  ],
  "confidence_assessment": {{
    "level": "high | medium | low",
    "reasoning": [
      "Source diversity",
      "Verification rate",
      "Presence of unresolved tensions"
    ]
  }}
}}

---

## ABSOLUTE PROHIBITIONS (NON-NEGOTIABLE)

You must never:
- Introduce new facts
- Reference raw source text
- Write a script or narrative
- Decide intent or motive
- Resolve contradictions
- Pretend uncertainty doesn't exist

Violation of these rules invalidates the output.

---

## FAILURE & THIN OUTPUT HANDLING

If synthesis feels thin:
- Do NOT pad
- Do NOT generalize
- Return fewer sections
- Confidence must be downgraded

Thin synthesis is acceptable.
Dishonest synthesis is not.
"""


# Gap Identification prompt (separate pass for identifying gaps)
GAP_IDENTIFICATION_PROMPT = """You are a research completeness checker.

Your job is NOT to add information.
Your job is NOT to infer hidden facts.
Your job is NOT to speculate about truth.

Your job IS to identify what information a competent human researcher
would reasonably expect to see, but which is absent from the current corpus.

You must NOT:
- Guess which video/article is being discussed
- Substitute a "likely" source
- Assume information not in the Context Bundle

---

## INPUT (STRICT)

You receive a Context Bundle ONLY:
- Scope Lock: {scope_lock}
- Source Manifest (types + count only): {source_manifest}
- Key Points: {key_points_json}
- Themes: {themes_json}
- Tensions (if any): {tensions_json}

---

## TASK DEFINITION

Identify GAPS by comparing:
> what is present
> vs
> what would normally be expected for this type of topic

Gaps are EXPECTATIONS, not assertions.

---

## WHAT COUNTS AS A GAP

A valid Gap is one of:
- A **missing perspective**: e.g., no response from a key party
- A **missing primary source**: e.g., claims without original documentation
- A **missing timeline segment**: e.g., events discussed before/after a key moment
- A **missing consequence or outcome**: e.g., no discussion of results, aftermath, or impact
- A **missing verification path**: e.g., claims that would normally be checkable but aren't

---

## WHAT DOES NOT COUNT AS A GAP (NON-NEGOTIABLE)

You must NOT:
- Invent facts that might exist
- Assume wrongdoing
- Suggest narratives
- Ask speculative questions ("What if...?")
- Infer intent or motive

BAD GAP: "There may be corruption involved."
GOOD GAP: "No primary financial records are cited to support claims about funding."

---

## OUTPUT FORMAT (JSON ONLY)

{{
  "gaps": [
    {{
      "gap_id": "GAP_1",
      "description": "What information is missing",
      "why_expected": "Why a researcher would expect this information",
      "related_themes": ["THEME_1"],
      "related_key_points": ["KP_3", "KP_7"],
      "suggested_research_direction": "What type of source or query could address this gap"
    }}
  ]
}}

---

## GAP COUNT GUIDANCE

- Minimum: 0 (valid if corpus is comprehensive)
- Target: 3-7 gaps for typical research
- Maximum: 10 (prevent overwhelming user)

If fewer than 3 gaps identified for a multi-source corpus:
- This may indicate thin analysis
- Triggers soft fail review

---

## CONSTRAINTS

- Gaps must be NEUTRAL
- Gaps must be ACTIONABLE
- Gaps must be TRACEABLE to the current corpus
- It is acceptable to return few gaps if the corpus is narrow

Prefer PRECISION over QUANTITY.
"""


def build_semantic_synthesis_prompt(
    scope_lock: str,
    key_points: list[dict],
    themes: list[dict],
    tensions: list[dict],
    gaps: list[dict],
    verification_rate: float,
    source_diversity: int,
) -> str:
    """
    Build the complete semantic synthesis prompt.

    Args:
        scope_lock: What this research covers/doesn't cover
        key_points: List of KeyPoint dicts
        themes: List of Theme dicts
        tensions: List of Tension dicts
        gaps: List of Gap dicts
        verification_rate: Percentage of claims verified (0-1)
        source_diversity: Number of unique sources

    Returns:
        Complete prompt string ready for Gemini
    """
    import json

    return SEMANTIC_SYNTHESIS_PROMPT.format(
        scope_lock=scope_lock,
        key_points_json=json.dumps(key_points, indent=2),
        themes_json=json.dumps(themes, indent=2),
        tensions_json=json.dumps(tensions, indent=2),
        gaps_json=json.dumps(gaps, indent=2),
        verification_rate=f"{verification_rate:.0%}",
        source_diversity=f"{source_diversity} sources",
    )


def build_gap_identification_prompt(
    scope_lock: str,
    source_manifest: list[dict],
    key_points: list[dict],
    themes: list[dict],
    tensions: list[dict],
) -> str:
    """
    Build the gap identification prompt.

    Args:
        scope_lock: What this research covers
        source_manifest: List of {source_id, type, title, status} dicts
        key_points: List of KeyPoint dicts
        themes: List of Theme dicts
        tensions: List of Tension dicts

    Returns:
        Complete prompt string ready for Gemini
    """
    import json

    return GAP_IDENTIFICATION_PROMPT.format(
        scope_lock=scope_lock,
        source_manifest=json.dumps(source_manifest, indent=2),
        key_points_json=json.dumps(key_points, indent=2),
        themes_json=json.dumps(themes, indent=2),
        tensions_json=json.dumps(tensions, indent=2),
    )
