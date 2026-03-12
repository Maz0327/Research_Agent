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


# Synthesis Context Lock - prevents fabrication during synthesis
SYNTHESIS_CONTEXT_LOCK = """
╔══════════════════════════════════════════════════════════╗
║  SYNTHESIS CONTEXT LOCK — STRICT INPUT BOUNDARY          ║
╠══════════════════════════════════════════════════════════╣
║  Input Type: Pre-extracted semantic units                ║
║  Source Count: {source_count}                            ║
║  Verification Rate: {verification_rate}                  ║
║  Maximum Synthesis Confidence: MEDIUM (unless all HIGH)  ║
╚══════════════════════════════════════════════════════════╝

RULE: You may ONLY reference information from the JSON input.
Any external knowledge = FABRICATION = REJECTED.
"""

# Phase 5: Cross-Source Analysis Instructions
CROSS_SOURCE_INSTRUCTIONS = """
## CROSS-SOURCE ANALYSIS (Phase 5)

When synthesizing from multiple sources, you MUST track source agreement:

### 1. CONVERGENCE (Multiple Sources Agree)
When 2+ sources support the same claim/theme:
- Mark theme with "is_consensus": true
- List all supporting source_ids in "sources_supporting"
- Higher confidence justified when sources agree

### 2. DIVERGENCE (Sources Disagree)
When sources provide conflicting information:
- Surface as a Tension (do NOT resolve)
- Tag with "is_cross_source": true
- List which sources support each position
- Present BOTH positions neutrally

### 3. SINGLE-SOURCE CLAIMS
When only one source supports a claim:
- Note it comes from single source
- Confidence should NOT exceed MEDIUM unless transcript_grounded

### Source Attribution Format
For each theme, include:
```json
{
    "theme_id": "THEME_1",
    "description": "...",
    "supporting_key_points": ["KP_1", "KP_2"],
    "sources_supporting": ["SRC_1", "SRC_2"],
    "is_consensus": true
}
```

For cross-source tensions:
```json
{
    "tension_id": "TEN_1",
    "label": "Conflicting Timeline Claims",
    "description": "Source A claims X while Source B claims Y",
    "is_cross_source": true,
    "sources_position_a": ["SRC_1"],
    "sources_position_b": ["SRC_2"]
}
```
"""

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
      "label": "Short title (3-6 words describing the conflict)",
      "description": "...",
      "involved_key_points": ["KP_3", "KP_6"],
      "source_ids": ["SRC_1", "SRC_2"]
    }}
  ],
  "gaps": [
    {{
      "gap_id": "GAP_1",
      "label": "Short title (3-6 words describing what's missing)",
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
- MUST include "synthesis_warnings" explaining what's missing and why

Thin synthesis is acceptable.
Dishonest synthesis is not.

**Warning format:**
```json
{{
  "speculative_observations": [],
  "synthesis_warnings": [
    "speculative_observations empty: Insufficient cross-source patterns to support speculation",
    "tensions limited: Only 1 source provided - cross-source tensions require 2+ sources"
  ]
}}
```

## EXAMPLE OUTPUT (for synthesis of Theranos research)

NOTE: This example shows output for a multi-source corpus with clear tensions.
Your output may be shorter if input is limited. Match QUALITY and SPECIFICITY,
not QUANTITY.

```json
{{
  "semantic_core": {{
    "text": "This topic centers on the gap between public demonstrations of blood testing technology and the documented practices inside the laboratory. Multiple sources describe parallel processes: one presented externally and another used for actual patient samples. The central unresolved question is when leadership became aware of this divergence.",
    "based_on": ["KP_1", "KP_2", "KP_4"]
  }},
  "themes": [
    {{
      "theme_id": "THEME_1",
      "description": "Systematic concealment of technical limitations from external stakeholders, including demonstrations with predetermined results and restricted lab access during partnership negotiations.",
      "supporting_key_points": ["KP_1", "KP_2", "KP_4"]
    }},
    {{
      "theme_id": "THEME_2",
      "description": "Authority figures prioritizing institutional relationships over internal whistleblower concerns, resulting in delayed response to documented problems.",
      "supporting_key_points": ["KP_3", "KP_4"]
    }}
  ],
  "tensions": [
    {{
      "tension_id": "TEN_1",
      "label": "Technology Readiness Contradiction",
      "description": "Leadership's public statements about technology readiness contradict technician accounts of workarounds required for every patient sample. This tension remains unresolved because no primary documentation of internal testing protocols has been made public.",
      "involved_key_points": ["KP_1", "KP_2"],
      "source_ids": ["SRC_1", "SRC_2"]
    }}
  ],
  "gaps": [
    {{
      "gap_id": "GAP_1",
      "label": "Missing Internal Technical Memos",
      "impact_on_understanding": "Without internal technical memos, we cannot determine whether leadership was aware of device limitations or genuinely believed in its capabilities.",
      "what_would_help": "FDA inspection reports or internal engineering documents from 2014-2015."
    }},
    {{
      "gap_id": "GAP_2",
      "label": "No Patient Perspective",
      "impact_on_understanding": "No perspective from patients who received test results, limiting understanding of real-world impact.",
      "what_would_help": "Court testimony from affected patients or medical professionals who acted on Theranos results."
    }}
  ],
  "speculative_observations": [
    {{
      "text": "The pattern of board member responses suggests a possible information silo where technical staff concerns did not reach decision-makers through normal channels.",
      "based_on": ["KP_3", "KP_4"],
      "label": "speculative"
    }}
  ],
  "confidence_assessment": {{
    "level": "medium",
    "reasoning": [
      "High source diversity (5 sources)",
      "Verification rate: 70%",
      "Unresolved tension between leadership claims and technician accounts",
      "Missing internal documentation limits certainty on intent"
    ]
  }}
}}
```
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
      "label": "Short title (3-6 words describing what's missing)",
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

## EXAMPLE OUTPUT (for gap identification on Theranos corpus)

NOTE: This example shows output for a corpus with significant documentation gaps.
Your output may have fewer gaps if the corpus is more complete. Match QUALITY,
not QUANTITY.

```json
{{
  "gaps": [
    {{
      "gap_id": "GAP_1",
      "label": "Missing Device Accuracy Docs",
      "description": "No internal engineering documentation showing device accuracy metrics",
      "why_expected": "Medical device companies typically maintain validation protocols; regulatory filings would reference these documents",
      "related_themes": ["THEME_1"],
      "related_key_points": ["KP_1", "KP_2"],
      "suggested_research_direction": "Search for FDA 483 inspection reports or SEC filings that reference internal quality data"
    }},
    {{
      "gap_id": "GAP_2",
      "label": "No Walgreens Due Diligence",
      "description": "Missing perspective from Walgreens due diligence team",
      "why_expected": "A $350M partnership would involve legal and technical review; those reviewers could describe what they were shown",
      "related_themes": ["THEME_1"],
      "related_key_points": ["KP_4"],
      "suggested_research_direction": "Search for interviews with former Walgreens executives involved in the Theranos partnership"
    }},
    {{
      "gap_id": "GAP_3",
      "label": "Missing Board Meeting Records",
      "description": "No primary documentation of board meeting discussions about technology status",
      "why_expected": "Board members testified about their knowledge; meeting minutes could verify timeline of awareness",
      "related_themes": ["THEME_2"],
      "related_key_points": ["KP_3"],
      "suggested_research_direction": "Check trial exhibits or court filings for board meeting records"
    }},
    {{
      "gap_id": "GAP_4",
      "label": "No Patient Outcomes Data",
      "description": "Missing patient outcomes data from Theranos test results",
      "why_expected": "Claims about harm require documentation of actual medical decisions made based on faulty results",
      "related_themes": [],
      "related_key_points": [],
      "suggested_research_direction": "Search for class action lawsuit filings that document specific patient cases"
    }}
  ]
}}
```
"""


def build_semantic_synthesis_prompt(
    scope_lock: str,
    key_points: list[dict],
    themes: list[dict],
    tensions: list[dict],
    gaps: list[dict],
    verification_rate: float,
    source_diversity: int,
    source_coverage: dict | None = None,
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
        source_coverage: Optional dict mapping key_point_id → [source_ids] (Phase 5)

    Returns:
        Complete prompt string ready for Gemini
    """
    import json

    # Build context lock
    context_lock = SYNTHESIS_CONTEXT_LOCK.format(
        source_count=source_diversity,
        verification_rate=f"{verification_rate:.0%}",
    )

    # Phase 5: Include cross-source instructions when multiple sources
    cross_source_section = ""
    if source_diversity > 1:
        cross_source_section = CROSS_SOURCE_INSTRUCTIONS
        # Add source coverage data if provided
        if source_coverage:
            cross_source_section += f"\n\nSource Coverage Map:\n{json.dumps(source_coverage, indent=2)}\n"

    # Build full prompt with context lock prepended
    prompt = context_lock + cross_source_section + "\n\n" + SEMANTIC_SYNTHESIS_PROMPT.format(
        scope_lock=scope_lock,
        key_points_json=json.dumps(key_points, indent=2),
        themes_json=json.dumps(themes, indent=2),
        tensions_json=json.dumps(tensions, indent=2),
        gaps_json=json.dumps(gaps, indent=2),
        verification_rate=f"{verification_rate:.0%}",
        source_diversity=f"{source_diversity} sources",
    )

    return prompt


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
