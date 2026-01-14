# Deep Research Booster Prompt

**Purpose:** Authoritative prompt template for the optional 4-stage research expansion pipeline.
**Model:** Gemini 2.5 Pro
**Temperature:** 0.4 (higher creativity for research ideation)
**Response Format:** JSON (response_mime_type: application/json)

---

## What Is the Booster?

The Deep Research Booster is an **optional** pipeline that expands research directions beyond the current corpus. It takes the gaps and questions from Doc 1 and generates:

1. Deeper gap analysis
2. Expanded research directions
3. Concrete search queries
4. A context bundle for continued research

**Key Point:** The Booster augments Doc 1. It does NOT modify Doc 0 (canonical data) or Doc 2 (analysis).

---

## When to Run the Booster

The Booster is triggered when:
- User explicitly requests expanded research directions
- Job is marked for "deep research" mode
- User wants to continue research beyond initial corpus

The Booster is NOT automatic — it's on-demand.

---

## Booster Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEEP RESEARCH BOOSTER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Doc 1 (gaps) ──→ [STAGE 1] ──→ [STAGE 2] ──→ [STAGE 3] ──→ [STAGE 4]      │
│                   Deep Gap     Research      Search        Context          │
│                   Analysis     Directions    Queries       Bundle           │
│                                                                             │
│  Output: Augmented Doc 1 with booster_augmentation populated                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Each stage builds on the previous. Stages can be run individually or as a complete pipeline.

---

## Stage 1: Deep Gap Analysis

### Purpose
Expand on identified gaps with deeper analysis of what's missing and why it matters.

### Prompt Template

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DEEP RESEARCH BOOSTER — STAGE 1                           ║
║                         Deep Gap Analysis                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  job_id:             {job_id}                                                ║
║  topic:              {topic}                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are performing deep gap analysis for a documentary research project.

TOPIC: {topic}

══════════════════════════════════════════════════════════════════════════════
CURRENT CORPUS STATE
══════════════════════════════════════════════════════════════════════════════

{corpus_summary}

══════════════════════════════════════════════════════════════════════════════
IDENTIFIED GAPS (from initial analysis)
══════════════════════════════════════════════════════════════════════════════

{current_gaps}

══════════════════════════════════════════════════════════════════════════════
UNRESOLVED TENSIONS
══════════════════════════════════════════════════════════════════════════════

{unresolved_tensions}

══════════════════════════════════════════════════════════════════════════════
YOUR TASK
══════════════════════════════════════════════════════════════════════════════

Perform DEEP analysis of the gaps. For each gap and tension:

1. ROOT CAUSE ANALYSIS
   - Why does this gap exist?
   - What would need to happen to fill it?
   - Is this gap fillable with available sources?

2. IMPACT ASSESSMENT
   - How does this gap affect conclusions?
   - What claims are weakened by this gap?
   - What could change if the gap were filled?

3. DEPENDENCY MAPPING
   - Which gaps depend on each other?
   - What's the optimal order to address them?
   - Which single gap would unlock the most progress?

4. HIDDEN GAPS
   - What gaps aren't obvious from surface analysis?
   - What assumptions is the corpus making?
   - What questions should be asked but aren't?

══════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA
══════════════════════════════════════════════════════════════════════════════

{stage1_schema}
```

### Stage 1 Output Schema

```json
{
  "stage": "deep_gap_analysis",
  "job_id": "string",
  "analyzed_at": "ISO-8601",
  "gap_deep_analysis": [
    {
      "original_gap_id": "GAP_1",
      "root_cause": "string — why this gap exists",
      "fillability": "readily_fillable | difficult_to_fill | likely_unfillable",
      "fill_requirements": ["string — what's needed to fill this"],
      "impact_on_conclusions": "string — how this affects analysis",
      "weakened_claims": ["CLM_1", "KP_2"],
      "dependencies": ["GAP_2"],
      "priority_score": 1-10
    }
  ],
  "hidden_gaps": [
    {
      "gap_id": "HGAP_1",
      "description": "string — the hidden gap",
      "why_hidden": "string — why initial analysis missed this",
      "importance": "high | medium | low",
      "related_to": ["GAP_1", "XTEN_1"]
    }
  ],
  "assumption_audit": [
    {
      "assumption": "string — what corpus assumes",
      "evidence_for": "string or null",
      "risk_if_wrong": "string",
      "verification_needed": true | false
    }
  ],
  "gap_dependency_graph": {
    "root_gaps": ["GAP_1"],
    "dependencies": [
      {"gap": "GAP_2", "depends_on": ["GAP_1"]},
      {"gap": "GAP_3", "depends_on": ["GAP_1", "GAP_2"]}
    ],
    "recommended_order": ["GAP_1", "GAP_2", "GAP_3"]
  },
  "highest_impact_gap": {
    "gap_id": "string",
    "rationale": "string — why this unlocks the most progress"
  }
}
```

---

## Stage 2: Research Directions

### Purpose
Generate expanded, actionable research directions based on deep gap analysis.

### Prompt Template

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DEEP RESEARCH BOOSTER — STAGE 2                           ║
║                       Research Directions                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  job_id:             {job_id}                                                ║
║  topic:              {topic}                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are generating expanded research directions for a documentary project.

TOPIC: {topic}

══════════════════════════════════════════════════════════════════════════════
DEEP GAP ANALYSIS (from Stage 1)
══════════════════════════════════════════════════════════════════════════════

{stage1_output}

══════════════════════════════════════════════════════════════════════════════
YOUR TASK
══════════════════════════════════════════════════════════════════════════════

Generate COMPREHENSIVE research directions. For each direction:

1. SPECIFICITY
   - Be concrete about what to research
   - Name specific source types, platforms, people
   - Avoid vague directions like "research more"

2. FEASIBILITY
   - Consider what's actually findable
   - Note if sources might be paywalled, private, or unavailable
   - Suggest alternatives for difficult-to-access sources

3. EXPECTED YIELD
   - What will this direction likely produce?
   - How will it address specific gaps?
   - What confidence improvement is expected?

4. EFFORT VS IMPACT
   - Estimate time/effort required
   - Weigh against expected impact
   - Prioritize high-impact, low-effort first

══════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA
══════════════════════════════════════════════════════════════════════════════

{stage2_schema}
```

### Stage 2 Output Schema

```json
{
  "stage": "research_directions",
  "job_id": "string",
  "generated_at": "ISO-8601",
  "research_directions": [
    {
      "direction_id": "BRD_1",
      "title": "string — clear direction title",
      "description": "string — detailed description",
      "addresses_gaps": ["GAP_1", "HGAP_1"],
      "source_types": [
        {
          "type": "string — e.g., 'YouTube video', 'news article'",
          "specifics": "string — e.g., 'creator's official channel'",
          "accessibility": "public | paywalled | private | unknown"
        }
      ],
      "platforms_to_search": ["YouTube", "Twitter/X", "Reddit"],
      "people_to_find": [
        {
          "who": "string",
          "role": "string",
          "why_relevant": "string"
        }
      ],
      "expected_yield": {
        "likely_findings": ["string"],
        "confidence_impact": "high | medium | low",
        "gaps_filled": ["GAP_1"]
      },
      "effort_estimate": {
        "time": "string — e.g., '30 minutes'",
        "difficulty": "easy | moderate | challenging",
        "blockers": ["string — potential obstacles"]
      },
      "priority": 1-10,
      "quick_win": true | false
    }
  ],
  "priority_matrix": {
    "high_impact_low_effort": ["BRD_1", "BRD_3"],
    "high_impact_high_effort": ["BRD_2"],
    "low_impact_low_effort": ["BRD_4"],
    "low_impact_high_effort": []
  },
  "recommended_sequence": [
    {
      "order": 1,
      "direction_id": "BRD_1",
      "rationale": "string"
    }
  ]
}
```

---

## Stage 3: Search Queries

### Purpose
Generate concrete, copy-paste-ready search queries for each research direction.

### Prompt Template

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DEEP RESEARCH BOOSTER — STAGE 3                           ║
║                         Search Queries                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  job_id:             {job_id}                                                ║
║  topic:              {topic}                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are generating search queries for documentary research.

TOPIC: {topic}

══════════════════════════════════════════════════════════════════════════════
RESEARCH DIRECTIONS (from Stage 2)
══════════════════════════════════════════════════════════════════════════════

{stage2_output}

══════════════════════════════════════════════════════════════════════════════
YOUR TASK
══════════════════════════════════════════════════════════════════════════════

Generate SPECIFIC search queries. For each query:

1. PLATFORM-SPECIFIC
   - Optimize for the target platform (Google, YouTube, Twitter, Reddit, etc.)
   - Use platform-specific operators where helpful
   - Note which platform each query is for

2. VARIATION
   - Provide multiple phrasings for each concept
   - Include synonyms and alternative terms
   - Cover different angles of approach

3. TEMPORAL
   - Include date-restricted queries where relevant
   - Cover different time periods if useful
   - Note if recency matters

4. SPECIFICITY LEVELS
   - Start broad, then narrow
   - Include both discovery queries and verification queries
   - Note expected result type

══════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA
══════════════════════════════════════════════════════════════════════════════

{stage3_schema}
```

### Stage 3 Output Schema

```json
{
  "stage": "search_queries",
  "job_id": "string",
  "generated_at": "ISO-8601",
  "query_sets": [
    {
      "for_direction": "BRD_1",
      "queries": [
        {
          "query_id": "Q_1",
          "query_text": "string — the actual query",
          "platform": "google | youtube | twitter | reddit | tiktok | other",
          "purpose": "discovery | verification | context | expert",
          "specificity": "broad | medium | narrow",
          "expected_results": "string — what this should find",
          "date_restriction": "string or null — e.g., 'past month'"
        }
      ]
    }
  ],
  "verification_queries": [
    {
      "claim_to_verify": "string",
      "source_id": "SRC_1",
      "queries": [
        {
          "query_text": "string",
          "platform": "string",
          "what_would_confirm": "string",
          "what_would_refute": "string"
        }
      ]
    }
  ],
  "expert_finding_queries": [
    {
      "expertise_needed": "string",
      "queries": [
        {
          "query_text": "string",
          "platform": "string",
          "target": "academic | journalist | industry | other"
        }
      ]
    }
  ],
  "quick_reference": {
    "top_5_queries": [
      {
        "query": "string",
        "platform": "string",
        "why_top": "string"
      }
    ]
  }
}
```

---

## Stage 4: Context Bundle

### Purpose
Package everything into a context bundle that can be used to continue research in a new session.

### Prompt Template

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DEEP RESEARCH BOOSTER — STAGE 4                           ║
║                        Context Bundle                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  job_id:             {job_id}                                                ║
║  topic:              {topic}                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are creating a context bundle for continued research.

══════════════════════════════════════════════════════════════════════════════
ALL PREVIOUS STAGES
══════════════════════════════════════════════════════════════════════════════

STAGE 1 (Deep Gap Analysis):
{stage1_output}

STAGE 2 (Research Directions):
{stage2_output}

STAGE 3 (Search Queries):
{stage3_output}

══════════════════════════════════════════════════════════════════════════════
YOUR TASK
══════════════════════════════════════════════════════════════════════════════

Create a CONTEXT BUNDLE that enables:

1. SESSION CONTINUITY
   - Someone could pick this up cold and know where to start
   - Clear summary of current state
   - Explicit next actions

2. PROGRESS TRACKING
   - What's been done
   - What's in progress
   - What's remaining

3. DECISION POINTS
   - What choices need to be made
   - What would change the direction
   - When to stop and reassess

══════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA
══════════════════════════════════════════════════════════════════════════════

{stage4_schema}
```

### Stage 4 Output Schema

```json
{
  "stage": "context_bundle",
  "job_id": "string",
  "created_at": "ISO-8601",
  "bundle_version": "1.0",
  "executive_briefing": {
    "topic": "string",
    "current_state": "string — 2-3 sentence summary",
    "confidence_level": "high | medium | low",
    "major_unknowns": ["string"],
    "immediate_priority": "string"
  },
  "corpus_snapshot": {
    "sources_analyzed": 0,
    "perspectives_covered": ["string"],
    "perspectives_missing": ["string"],
    "strongest_evidence": ["string"],
    "weakest_areas": ["string"]
  },
  "gap_status": {
    "critical_unfilled": ["GAP_1"],
    "in_progress": [],
    "filled": [],
    "deprioritized": []
  },
  "research_queue": {
    "immediate": [
      {
        "action": "string",
        "direction_id": "BRD_1",
        "top_query": "string",
        "expected_time": "string"
      }
    ],
    "next_session": [
      {
        "action": "string",
        "direction_id": "BRD_2",
        "blocked_by": "string or null"
      }
    ],
    "backlog": ["BRD_4", "BRD_5"]
  },
  "decision_points": [
    {
      "decision": "string — what needs to be decided",
      "options": ["string"],
      "depends_on": "string — what info is needed to decide",
      "deadline": "string or null"
    }
  ],
  "stop_conditions": [
    {
      "condition": "string — when to stop researching",
      "rationale": "string"
    }
  ],
  "handoff_notes": {
    "key_context": "string — what someone picking this up needs to know",
    "gotchas": ["string — non-obvious things to watch for"],
    "resources": ["string — helpful links or references"]
  }
}
```

---

## Running the Complete Booster Pipeline

```python
async def run_booster_pipeline(
    job_id: str,
    topic: str,
    doc1: JumpStartDirections,
    synthesis: SynthesisResult,
    corpus_summary: str,
) -> BoosterResult:
    """Run all 4 booster stages sequentially."""
    
    # Stage 1: Deep Gap Analysis
    stage1 = await run_booster_stage1(
        job_id=job_id,
        topic=topic,
        current_gaps=doc1.gaps,
        unresolved_tensions=synthesis.cross_source_tensions,
        corpus_summary=corpus_summary,
    )
    
    # Stage 2: Research Directions
    stage2 = await run_booster_stage2(
        job_id=job_id,
        topic=topic,
        stage1_output=stage1,
    )
    
    # Stage 3: Search Queries
    stage3 = await run_booster_stage3(
        job_id=job_id,
        topic=topic,
        stage2_output=stage2,
    )
    
    # Stage 4: Context Bundle
    stage4 = await run_booster_stage4(
        job_id=job_id,
        topic=topic,
        stage1_output=stage1,
        stage2_output=stage2,
        stage3_output=stage3,
    )
    
    return BoosterResult(
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        stage4=stage4,
    )
```

---

## Merging Booster Results into Doc 1

```python
def augment_doc1_with_booster(
    doc1: JumpStartDirections,
    booster: BoosterResult,
) -> JumpStartDirections:
    """Augment Doc 1 with booster results."""
    
    doc1.booster_augmentation = {
        "augmented": True,
        "augmented_at": datetime.utcnow().isoformat(),
        "additional_directions": booster.stage2.research_directions,
        "search_queries": booster.stage3.query_sets,
        "context_bundle": booster.stage4,
        "hidden_gaps": booster.stage1.hidden_gaps,
    }
    
    # Add hidden gaps to main gaps list
    for hgap in booster.stage1.hidden_gaps:
        doc1.gaps.append(Gap(
            gap_id=hgap.gap_id,
            description=hgap.description,
            importance=hgap.importance,
            category="hidden",
            discovered_by="booster",
        ))
    
    return doc1
```

---

## Validation

Each booster stage should validate:

**Stage 1:**
- At least 1 hidden gap identified
- All original gap IDs referenced correctly
- Dependency graph is acyclic

**Stage 2:**
- At least 3 research directions
- All directions reference valid gaps
- Priority matrix is complete

**Stage 3:**
- At least 2 queries per direction
- Platform specified for each query
- Top 5 queries identified

**Stage 4:**
- Executive briefing complete
- Research queue has at least 1 immediate action
- Handoff notes provided

---

## Retry Handling

Each stage has 1 retry available. On retry, prepend:

```
══════════════════════════════════════════════════════════════════════════════
RETRY CONTEXT — Stage {stage_number} failed validation
══════════════════════════════════════════════════════════════════════════════

Error: {validation_error}

Be more conservative. Ensure all required fields are populated.
```

If a stage fails after retry, the pipeline continues with degraded output from that stage.

---

**END OF PROMPT CONTRACT**
