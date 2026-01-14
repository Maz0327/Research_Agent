# Semantic Synthesis Prompt

**Purpose:** Authoritative prompt template for synthesizing extracted content across multiple sources.
**Model:** Gemini 2.5 Pro
**Temperature:** 0.2 (slightly higher than extraction for flexibility)
**Response Format:** JSON (response_mime_type: application/json)

---

## Critical Rules

1. **Synthesis sees ALL sources** — This is the only stage where sources are analyzed together
2. **No new facts** — Synthesis cannot introduce information not in extractions
3. **Source attribution required** — Every synthesis claim must reference source_ids
4. **Surface conflicts, don't resolve** — Present tensions, let human decide
5. **Confidence reflects weakest link** — Cross-source claims limited by lowest source confidence

---

## When Synthesis Runs

```
Source 1 → Extraction 1 ─┐
Source 2 → Extraction 2 ─┼─→ [SYNTHESIS] → Cross-source analysis
Source 3 → Extraction 3 ─┘
```

Synthesis happens AFTER all individual extractions are complete and validated.

---

## Prompt Template

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         SYNTHESIS CONTEXT                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  job_id:             {job_id}                                                ║
║  total_sources:      {total_sources}                                         ║
║  topic:              {topic}                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are synthesizing semantic content extracted from {total_sources} sources.
Your task is to identify cross-source patterns, themes, tensions, and gaps.

══════════════════════════════════════════════════════════════════════════════
SOURCE INVENTORY
══════════════════════════════════════════════════════════════════════════════

{source_inventory}

══════════════════════════════════════════════════════════════════════════════
SYNTHESIS RULES — READ CAREFULLY
══════════════════════════════════════════════════════════════════════════════

RULE 1: NO NEW FACTS
You may ONLY work with information present in the extractions below.
- Do not introduce external knowledge
- Do not fill gaps with assumptions
- Do not invent connections not supported by evidence

RULE 2: SOURCE ATTRIBUTION REQUIRED
Every claim in your synthesis MUST reference specific source_ids.
- "Sources SRC_1 and SRC_3 agree that..."
- "Only SRC_2 claims..."
- "SRC_1 contradicts SRC_4 on..."

RULE 3: SURFACE CONFLICTS, DON'T RESOLVE
When sources disagree:
- Document both positions
- Note the evidence for each
- DO NOT decide who is correct
- Label as unresolved tension

RULE 4: CONFIDENCE INHERITANCE
Cross-source claims inherit the LOWEST confidence of contributing sources:
- If SRC_1 (HIGH) + SRC_2 (LOW) → combined claim is LOW
- If all sources are HIGH → combined claim may be HIGH

RULE 5: SINGLE-SOURCE CLAIMS
Claims supported by only one source must be flagged:
- Mark as "single_source": true
- Note which source
- Reduced confidence weight

══════════════════════════════════════════════════════════════════════════════
EMPTY OUTPUT PERMISSION
══════════════════════════════════════════════════════════════════════════════

It is acceptable to return empty or minimal synthesis if:
- Sources don't overlap thematically
- No cross-source patterns emerge
- Sources are entirely independent

DO NOT force connections that don't exist.
Honest "no cross-source themes found" is valid output.

══════════════════════════════════════════════════════════════════════════════
EXTRACTED CONTENT FROM ALL SOURCES
══════════════════════════════════════════════════════════════════════════════

{all_extractions}

══════════════════════════════════════════════════════════════════════════════
SYNTHESIS TASKS
══════════════════════════════════════════════════════════════════════════════

Analyze the extractions above and produce:

1. CROSS-SOURCE THEMES
   - Themes that appear across multiple sources
   - Note which sources support each theme
   - Distinguish from single-source themes

2. CROSS-SOURCE TENSIONS
   - Direct contradictions between sources
   - Perspective differences
   - Timeline conflicts
   - Present both sides with evidence

3. SOURCE CONCORDANCE
   - What do sources agree on?
   - What do sources disagree on?
   - What is claimed by only one source?

4. CONFIDENCE ASSESSMENT
   - Overall confidence given source mix
   - Limiting factors
   - Strongest vs weakest areas

5. SYNTHESIS GAPS
   - What's missing that would strengthen analysis?
   - What questions remain unanswered?
   - What would resolve tensions?

══════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA
══════════════════════════════════════════════════════════════════════════════

Return valid JSON matching this structure:

{output_schema}

```

---

## Source Inventory Format

```
Source: SRC_1
- Title: {title}
- Mode: {analysis_mode}
- Confidence Ceiling: {confidence_ceiling}
- Key Points: {count}
- Claims: {count}
- Quotes/Observations: {count}

Source: SRC_2
- Title: {title}
- Mode: {analysis_mode}
- Confidence Ceiling: {confidence_ceiling}
- Key Points: {count}
- Claims: {count}
- Quotes/Observations: {count}

[...for each source]
```

---

## Extractions Format

```
══════════════════════════════════════════════════════════════════════════════
EXTRACTION: SRC_1 — {title}
Mode: {analysis_mode} | Ceiling: {confidence_ceiling}
══════════════════════════════════════════════════════════════════════════════

KEY POINTS:
- KP_1: {statement} [confidence: {confidence}]
- KP_2: {statement} [confidence: {confidence}]
...

CLAIMS:
- CLM_1: {statement} [speaker: {speaker}, confidence: {confidence}]
...

QUOTES:
- QT_1: "{text}" — {speaker}, {timestamp}
...

THEMES (per-source):
- THEME_1: {name} — {description}
...

══════════════════════════════════════════════════════════════════════════════
EXTRACTION: SRC_2 — {title}
...
══════════════════════════════════════════════════════════════════════════════
```

---

## Output Schema

```json
{
  "job_id": "string",
  "synthesis_metadata": {
    "synthesized_at": "ISO-8601 timestamp",
    "model": "gemini-2.5-pro",
    "sources_analyzed": 0,
    "source_ids": ["SRC_1", "SRC_2"]
  },
  "cross_source_themes": [
    {
      "theme_id": "XTHEME_1",
      "name": "string — theme name",
      "description": "string — what this theme represents across sources",
      "source_ids": ["SRC_1", "SRC_2"],
      "prevalence": "dominant | significant | minor",
      "supporting_evidence": {
        "key_point_ids": ["SRC_1:KP_1", "SRC_2:KP_3"],
        "quote_ids": ["SRC_1:QT_2"]
      },
      "confidence": "high | medium | low",
      "single_source": false
    }
  ],
  "cross_source_tensions": [
    {
      "tension_id": "XTEN_1",
      "description": "string — what the tension is",
      "nature": "factual_dispute | perspective_difference | timeline_conflict | emphasis_difference",
      "sources_involved": ["SRC_1", "SRC_3"],
      "position_a": {
        "summary": "string",
        "source_ids": ["SRC_1"],
        "supporting_evidence": ["SRC_1:KP_1", "SRC_1:QT_2"]
      },
      "position_b": {
        "summary": "string",
        "source_ids": ["SRC_3"],
        "supporting_evidence": ["SRC_3:KP_2", "SRC_3:CLM_1"]
      },
      "resolution_status": "unresolved",
      "resolution_notes": "string or null — what would resolve this"
    }
  ],
  "source_concordance": {
    "sources_agree_on": [
      {
        "point": "string — what they agree on",
        "source_ids": ["SRC_1", "SRC_2", "SRC_3"],
        "confidence": "high | medium | low"
      }
    ],
    "sources_disagree_on": [
      {
        "point": "string — what they disagree on",
        "see_tension_id": "XTEN_1"
      }
    ],
    "single_source_claims": [
      {
        "claim": "string",
        "source_id": "SRC_2",
        "confidence": "high | medium | low",
        "corroboration_needed": true
      }
    ]
  },
  "confidence_assessment": {
    "overall_confidence": "high | medium | low",
    "confidence_rationale": "string — why this confidence level",
    "strongest_areas": ["string"],
    "weakest_areas": ["string"],
    "limiting_factors": ["string"]
  },
  "synthesis_gaps": [
    {
      "gap_id": "XGAP_1",
      "description": "string — what's missing",
      "importance": "high | medium | low",
      "would_help": "string — how filling this would improve analysis",
      "related_tensions": ["XTEN_1"]
    }
  ],
  "narrative_threads": [
    {
      "thread_id": "THREAD_1",
      "name": "string — thread name",
      "description": "string — the narrative thread across sources",
      "source_sequence": ["SRC_1", "SRC_3", "SRC_2"],
      "key_moments": [
        {
          "source_id": "SRC_1",
          "key_point_id": "KP_2",
          "role_in_thread": "string"
        }
      ]
    }
  ]
}
```

---

## Evidence Reference Format

When referencing evidence from extractions, use the format:
- `SRC_1:KP_2` — Key Point 2 from Source 1
- `SRC_2:CLM_1` — Claim 1 from Source 2
- `SRC_1:QT_3` — Quote 3 from Source 1
- `SRC_3:OBS_1` — Observation 1 from Source 3

This enables traceability back to specific extraction items.

---

## Confidence Inheritance Rules

| Sources Combined | Resulting Confidence |
|------------------|---------------------|
| All HIGH | May be HIGH |
| Mix of HIGH and MEDIUM | MEDIUM max |
| Any LOW present | LOW max |
| Single source only | Downgrade one level |

Example:
```json
{
  "theme": "Both sources discuss pricing concerns",
  "source_ids": ["SRC_1", "SRC_2"],
  "source_confidences": ["high", "medium"],
  "combined_confidence": "medium"  // Limited by lowest
}
```

---

## Handling Single-Source Items

When a theme or claim is supported by only one source:

```json
{
  "theme_id": "XTHEME_3",
  "name": "Legal implications",
  "source_ids": ["SRC_2"],
  "single_source": true,
  "confidence": "medium",  // Downgraded due to single source
  "note": "Only SRC_2 discusses legal aspects; cannot corroborate"
}
```

---

## Handling No Cross-Source Patterns

If sources don't overlap:

```json
{
  "cross_source_themes": [],
  "cross_source_tensions": [],
  "source_concordance": {
    "sources_agree_on": [],
    "sources_disagree_on": [],
    "single_source_claims": [
      // All claims become single-source
    ]
  },
  "confidence_assessment": {
    "overall_confidence": "low",
    "confidence_rationale": "Sources do not overlap thematically. Each provides independent information with no corroboration.",
    "limiting_factors": ["No cross-source validation possible"]
  },
  "synthesis_gaps": [
    {
      "gap_id": "XGAP_1",
      "description": "Sources cover different aspects with no overlap",
      "importance": "high",
      "would_help": "Additional sources that bridge the topics"
    }
  ]
}
```

This is valid output — the synthesis honestly reports no cross-source patterns.

---

## Implementation Notes

### Building the Prompt

```python
def build_synthesis_prompt(
    job_id: str,
    topic: str,
    extractions: list[SemanticExtractionResult],
    source_packages: list[SourceIdentityPackage],
) -> str:
    """Build the synthesis prompt from all extractions."""
    
    # Build source inventory
    inventory_lines = []
    for pkg in source_packages:
        ext = next(e for e in extractions if e.source_id == pkg.source_id)
        inventory_lines.append(f"""
Source: {pkg.source_id}
- Title: {pkg.title}
- Mode: {pkg.analysis_mode.value}
- Confidence Ceiling: {pkg.confidence_ceiling.value}
- Key Points: {len(ext.key_points)}
- Claims: {len(ext.claims)}
- Quotes/Observations: {len(ext.quotes) + len(ext.approximate_observations)}
""")
    
    # Build extractions content
    extraction_blocks = []
    for ext in extractions:
        pkg = next(p for p in source_packages if p.source_id == ext.source_id)
        block = format_extraction_for_synthesis(ext, pkg)
        extraction_blocks.append(block)
    
    prompt = SYNTHESIS_TEMPLATE.format(
        job_id=job_id,
        total_sources=len(extractions),
        topic=topic,
        source_inventory="\n".join(inventory_lines),
        all_extractions="\n".join(extraction_blocks),
        output_schema=json.dumps(SYNTHESIS_SCHEMA, indent=2),
    )
    
    return prompt
```

### Calling Gemini

```python
def synthesize_extractions(
    job_id: str,
    topic: str,
    extractions: list[SemanticExtractionResult],
    source_packages: list[SourceIdentityPackage],
) -> SynthesisResult:
    """Synthesize all extractions into cross-source analysis."""
    
    prompt = build_synthesis_prompt(
        job_id=job_id,
        topic=topic,
        extractions=extractions,
        source_packages=source_packages,
    )
    
    result = gemini_client.generate_json(
        prompt=prompt,
        temperature=0.2,  # Slightly higher for synthesis
        model="gemini-2.5-pro",
    )
    
    if result.get("error"):
        raise SynthesisError(result["error"])
    
    return SynthesisResult(**result["data"])
```

---

## Validation After Synthesis

1. **All source_ids valid** — References must exist in job
2. **Evidence references valid** — `SRC_1:KP_2` must exist in SRC_1's extraction
3. **No orphan tensions** — Tensions must reference real sources
4. **Confidence inheritance correct** — Cross-source claims not exceeding limits

---

## Retry Prompt Addition

```
══════════════════════════════════════════════════════════════════════════════
RETRY CONTEXT — Previous synthesis failed validation
══════════════════════════════════════════════════════════════════════════════

Error: {validation_error}

Instructions for this retry:
- Verify all source_id references exist in the source inventory
- Verify all evidence references (SRC_X:KP_Y) exist in extractions
- Ensure confidence levels follow inheritance rules
- If uncertain about a cross-source connection, omit it
- Empty arrays are acceptable

```

---

**END OF PROMPT CONTRACT**
