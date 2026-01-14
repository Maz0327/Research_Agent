# Gap Identification Prompt

**Purpose:** Authoritative prompt template for deep analysis of missing information after extraction and synthesis.
**Model:** Gemini 2.5 Pro
**Temperature:** 0.3 (moderate creativity for identifying non-obvious gaps)
**Response Format:** JSON (response_mime_type: application/json)

---

## Critical Rules

1. **Runs AFTER synthesis** — Has access to all extractions and synthesis results
2. **Focus on actionable gaps** — Every gap should suggest how to fill it
3. **Prioritize ruthlessly** — Not all gaps are equal; rank by impact
4. **Consider user's goal** — Gaps should matter for the investigation topic
5. **No speculation as fact** — Gaps are questions, not assumed answers

---

## When Gap Identification Runs

```
Extractions ─┐
             ├─→ Synthesis ─→ [GAP IDENTIFICATION] ─→ Doc 1 gaps
Topic scope ─┘
```

Gap identification enriches Doc 1 (Jump-Start Directions) with deep analysis of what's missing.

---

## Prompt Template

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                      GAP IDENTIFICATION CONTEXT                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  job_id:             {job_id}                                                ║
║  topic:              {topic}                                                 ║
║  total_sources:      {total_sources}                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are analyzing gaps in the research corpus for a documentary investigation.

The user is researching: {topic}

Your task: Identify what information is MISSING that would strengthen this investigation.

══════════════════════════════════════════════════════════════════════════════
INVESTIGATION SCOPE
══════════════════════════════════════════════════════════════════════════════

{scope_lock}

══════════════════════════════════════════════════════════════════════════════
GAP IDENTIFICATION RULES
══════════════════════════════════════════════════════════════════════════════

RULE 1: ACTIONABLE GAPS ONLY
Every gap you identify must include:
- What specific information is missing
- Why it matters for this investigation
- How it could be found (source suggestions, search queries)

Do NOT identify gaps without actionable next steps.

RULE 2: PRIORITIZE BY IMPACT
Categorize each gap:
- HIGH: Would significantly change conclusions or fill critical blind spots
- MEDIUM: Would strengthen analysis or add important context
- LOW: Nice to have, would add depth but not essential

RULE 3: CONSIDER PERSPECTIVES
Identify gaps in perspective coverage:
- Which stakeholders/viewpoints are missing?
- What would opponents/critics say?
- What expertise is not represented?

RULE 4: IDENTIFY VERIFICATION GAPS
What claims need verification?
- Which factual claims are unverified?
- What evidence is cited but not shown?
- What could be fact-checked?

RULE 5: TIMELINE AND CONTEXT GAPS
- What events are referenced but not explained?
- What happened before/after the covered period?
- What background context is assumed?

══════════════════════════════════════════════════════════════════════════════
WHAT WE HAVE — CORPUS SUMMARY
══════════════════════════════════════════════════════════════════════════════

{corpus_summary}

══════════════════════════════════════════════════════════════════════════════
SYNTHESIS RESULTS
══════════════════════════════════════════════════════════════════════════════

CROSS-SOURCE THEMES:
{themes_summary}

CROSS-SOURCE TENSIONS:
{tensions_summary}

CURRENT GAPS (from extraction/synthesis):
{existing_gaps}

══════════════════════════════════════════════════════════════════════════════
ANALYSIS TASKS
══════════════════════════════════════════════════════════════════════════════

Analyze the corpus and identify:

1. PERSPECTIVE GAPS
   Who is not represented? What viewpoints are missing?

2. FACTUAL GAPS
   What facts are assumed, claimed without evidence, or unverified?

3. TIMELINE GAPS
   What happened before, during, or after that we don't know?

4. CONTEXT GAPS
   What background information would help understand this better?

5. EVIDENCE GAPS
   What evidence is mentioned but not shown or verified?

6. COUNTER-NARRATIVE GAPS
   What would critics or opponents say? What's the other side?

7. EXPERT GAPS
   What expertise would help evaluate the claims made?

══════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA
══════════════════════════════════════════════════════════════════════════════

{output_schema}

```

---

## Input Formats

### Scope Lock Format

```
TOPIC: {topic}
BOUNDARIES: {boundaries}
NOT ABOUT: {not_about}
```

### Corpus Summary Format

```
SOURCES ({total_sources}):
- SRC_1: {title} [{analysis_mode}, {confidence_ceiling}]
  Key points: {count} | Claims: {count}
  
- SRC_2: {title} [{analysis_mode}, {confidence_ceiling}]
  Key points: {count} | Claims: {count}

[...for each source]

PERSPECTIVES REPRESENTED:
- {perspective_1}
- {perspective_2}

OVERALL CONFIDENCE: {overall_confidence}
```

### Themes Summary Format

```
- XTHEME_1: {name}
  Sources: {source_ids}
  Description: {description}

- XTHEME_2: {name}
  ...
```

### Tensions Summary Format

```
- XTEN_1: {description}
  Position A ({source_ids}): {summary}
  Position B ({source_ids}): {summary}
  Status: {resolution_status}

- XTEN_2: ...
```

### Existing Gaps Format

```
From extractions:
- GAP_1 (SRC_1): {description}
- GAP_2 (SRC_2): {description}

From synthesis:
- XGAP_1: {description}
```

---

## Output Schema

```json
{
  "job_id": "string",
  "gap_analysis_metadata": {
    "analyzed_at": "ISO-8601 timestamp",
    "model": "gemini-2.5-pro",
    "sources_considered": 0
  },
  "perspective_gaps": [
    {
      "gap_id": "PGAP_1",
      "missing_perspective": "string — who/what viewpoint is missing",
      "why_important": "string — why this matters for the investigation",
      "importance": "high | medium | low",
      "suggested_sources": ["string"],
      "search_queries": ["string"]
    }
  ],
  "factual_gaps": [
    {
      "gap_id": "FGAP_1",
      "missing_fact": "string — what factual information is missing",
      "currently_assumed": "string — what the corpus assumes without evidence",
      "importance": "high | medium | low",
      "verification_method": "string — how to verify or find this",
      "search_queries": ["string"]
    }
  ],
  "timeline_gaps": [
    {
      "gap_id": "TGAP_1",
      "period": "before | during | after",
      "description": "string — what timeline information is missing",
      "known_anchor_points": ["string — dates/events we do know"],
      "importance": "high | medium | low",
      "search_queries": ["string"]
    }
  ],
  "context_gaps": [
    {
      "gap_id": "CGAP_1",
      "missing_context": "string — what background is needed",
      "would_help_understand": "string — what this would clarify",
      "importance": "high | medium | low",
      "suggested_sources": ["string"],
      "search_queries": ["string"]
    }
  ],
  "evidence_gaps": [
    {
      "gap_id": "EGAP_1",
      "claimed_evidence": "string — what evidence is mentioned",
      "source_of_claim": "SRC_X",
      "verification_status": "not_shown | not_verified | contradicted",
      "importance": "high | medium | low",
      "how_to_verify": "string"
    }
  ],
  "counter_narrative_gaps": [
    {
      "gap_id": "CNGAP_1",
      "dominant_narrative": "string — what the corpus presents",
      "missing_counter": "string — what opposing view is absent",
      "who_would_present": "string — who would make this argument",
      "importance": "high | medium | low",
      "search_queries": ["string"]
    }
  ],
  "expert_gaps": [
    {
      "gap_id": "XGAP_1",
      "expertise_needed": "string — what type of expert",
      "would_help_evaluate": "string — which claims/themes this addresses",
      "importance": "high | medium | low",
      "suggested_experts": ["string — types or specific names if known"]
    }
  ],
  "open_questions": [
    {
      "question": "string — the unanswered question",
      "why_unanswered": "string — why corpus doesn't answer this",
      "related_gaps": ["PGAP_1", "FGAP_2"],
      "importance": "high | medium | low"
    }
  ],
  "verification_checklist": [
    {
      "item": "string — what needs verification",
      "claimed_by": "SRC_X",
      "current_status": "unverified | partially_verified | contradicted",
      "verification_source": "string — where to check",
      "importance": "high | medium | low"
    }
  ],
  "prioritized_next_steps": [
    {
      "priority": 1,
      "action": "string — specific action to take",
      "addresses_gaps": ["PGAP_1", "FGAP_2"],
      "effort": "quick | moderate | deep_dive",
      "expected_impact": "string"
    },
    {
      "priority": 2,
      "action": "string",
      "addresses_gaps": ["TGAP_1"],
      "effort": "quick | moderate | deep_dive",
      "expected_impact": "string"
    },
    {
      "priority": 3,
      "action": "string",
      "addresses_gaps": ["CGAP_1"],
      "effort": "quick | moderate | deep_dive",
      "expected_impact": "string"
    }
  ]
}
```

---

## Gap ID Prefixes

| Prefix | Gap Type |
|--------|----------|
| `PGAP_` | Perspective gap |
| `FGAP_` | Factual gap |
| `TGAP_` | Timeline gap |
| `CGAP_` | Context gap |
| `EGAP_` | Evidence gap |
| `CNGAP_` | Counter-narrative gap |
| `XGAP_` | Expert gap |

---

## Effort Estimates

| Level | Definition |
|-------|------------|
| `quick` | Single search, < 15 minutes |
| `moderate` | Multiple sources, 15-60 minutes |
| `deep_dive` | Extensive research, 1+ hours |

---

## Priority Rules

**Priority 1** should always address:
- Critical blind spots that could invalidate conclusions
- Missing primary source perspectives
- Unverified claims central to the narrative

**Priority 2** should address:
- Important context gaps
- Counter-narratives
- Timeline clarification

**Priority 3** should address:
- Depth and nuance
- Expert validation
- Nice-to-have context

---

## Implementation Notes

### Building the Prompt

```python
def build_gap_identification_prompt(
    job_id: str,
    topic: str,
    scope_lock: ScopeLock,
    source_packages: list[SourceIdentityPackage],
    extractions: list[SemanticExtractionResult],
    synthesis: SynthesisResult,
) -> str:
    """Build the gap identification prompt."""
    
    # Build corpus summary
    corpus_summary = format_corpus_summary(source_packages, extractions)
    
    # Build themes summary
    themes_summary = format_themes_for_gaps(synthesis.cross_source_themes)
    
    # Build tensions summary
    tensions_summary = format_tensions_for_gaps(synthesis.cross_source_tensions)
    
    # Collect existing gaps
    existing_gaps = collect_existing_gaps(extractions, synthesis)
    
    prompt = GAP_IDENTIFICATION_TEMPLATE.format(
        job_id=job_id,
        topic=topic,
        total_sources=len(source_packages),
        scope_lock=format_scope_lock(scope_lock),
        corpus_summary=corpus_summary,
        themes_summary=themes_summary,
        tensions_summary=tensions_summary,
        existing_gaps=existing_gaps,
        output_schema=json.dumps(GAP_OUTPUT_SCHEMA, indent=2),
    )
    
    return prompt
```

### Calling Gemini

```python
def identify_gaps(
    job_id: str,
    topic: str,
    scope_lock: ScopeLock,
    source_packages: list[SourceIdentityPackage],
    extractions: list[SemanticExtractionResult],
    synthesis: SynthesisResult,
) -> GapAnalysisResult:
    """Run deep gap identification analysis."""
    
    prompt = build_gap_identification_prompt(
        job_id=job_id,
        topic=topic,
        scope_lock=scope_lock,
        source_packages=source_packages,
        extractions=extractions,
        synthesis=synthesis,
    )
    
    result = gemini_client.generate_json(
        prompt=prompt,
        temperature=0.3,  # Moderate creativity
        model="gemini-2.5-pro",
    )
    
    if result.get("error"):
        raise GapAnalysisError(result["error"])
    
    return GapAnalysisResult(**result["data"])
```

---

## Merging with Doc 1

Gap identification results get merged into Doc 1:

```python
def merge_gaps_into_doc1(
    base_doc1: JumpStartDirections,
    gap_analysis: GapAnalysisResult,
) -> JumpStartDirections:
    """Merge gap analysis into Doc 1."""
    
    # Combine all gap types into unified gaps array
    all_gaps = []
    
    for pgap in gap_analysis.perspective_gaps:
        all_gaps.append(Gap(
            gap_id=pgap.gap_id,
            description=pgap.missing_perspective,
            importance=pgap.importance,
            category="perspective",
            would_answer=pgap.why_important,
            suggested_source_types=pgap.suggested_sources,
        ))
    
    # ... repeat for other gap types
    
    # Merge with existing gaps, deduplicate
    base_doc1.gaps = deduplicate_gaps(base_doc1.gaps + all_gaps)
    
    # Update research directions from prioritized_next_steps
    base_doc1.research_directions = convert_steps_to_directions(
        gap_analysis.prioritized_next_steps
    )
    
    # Update top three next steps
    base_doc1.top_three_next_steps = [
        step for step in gap_analysis.prioritized_next_steps[:3]
    ]
    
    # Update verification checklist
    base_doc1.verification_checklist = gap_analysis.verification_checklist
    
    return base_doc1
```

---

## Validation

Gap analysis output should be validated for:

1. **At least 3 gaps identified** — Unless corpus is exceptionally complete
2. **Exactly 3 prioritized next steps** — Required for Doc 1
3. **All gap IDs unique** — No duplicates
4. **Search queries provided** — For actionable gaps
5. **Importance levels assigned** — All gaps must have importance

---

## Retry Prompt Addition

```
══════════════════════════════════════════════════════════════════════════════
RETRY CONTEXT — Previous gap analysis failed validation
══════════════════════════════════════════════════════════════════════════════

Error: {validation_error}

Instructions for this retry:
- Ensure at least 3 gaps are identified across all categories
- Ensure exactly 3 prioritized_next_steps are provided
- Ensure all gaps have search_queries or suggested_sources
- Ensure all importance levels are assigned
- Use unique gap IDs (PGAP_1, FGAP_1, etc.)

```

---

**END OF PROMPT CONTRACT**
