# Research Agent System — Claude Code Context Document

**Purpose**: This document provides complete context for implementing the Research Agent semantic pipeline. Read this ENTIRELY before writing any code.

**Status**: AUTHORITATIVE — Do not deviate without explicit user approval.

---

## 1. WHAT THIS SYSTEM IS

### The Problem
The user is a YouTube content creator who makes mini-documentaries and investigative livestreams. Each video requires 10-15 hours of manual research: watching videos, reading articles, extracting quotes, organizing facts, identifying gaps.

The user has ADHD, which means:
- Starting tasks is hard (activation energy)
- Holding context in working memory is hard
- Reading through hours of transcripts is painful
- But once in creative mode, they're effective

### The Solution
An AI-powered **semantic research assistant** that:
- Ingests video/article sources
- Extracts meaning (not summaries)
- Organizes information with full traceability
- Surfaces contradictions and gaps
- Delivers an "80% finished" research packet

The user does the final 20%: judgment, narrative framing, creative decisions.

### What This Is NOT
- NOT a summarizer
- NOT a script writer
- NOT a clip generator
- NOT a fact-checker
- NOT a replacement for human judgment

---

## 2. THE 3-DOCUMENT MODEL (Non-Negotiable)

The system produces THREE separate documents. These must NEVER be collapsed into one.

### Doc 0 — Source Ledger (Canonical Data Layer)
**Purpose**: Preserve full context. The single source of truth.

**Contains**:
- Full transcripts (verbatim when available)
- Source metadata (title, creator, date, duration)
- Transcript provenance (how transcript was acquired)
- Skim summaries (short, factual, non-interpretive)
- Extracted indexes (entities, timestamps, claims)

**Rules**:
- No interpretation
- No synthesis
- No opinions
- This is ground truth — everything traces back here

### Doc 1 — Jump-Start Research Directions
**Purpose**: Reduce activation energy. Tell the user what to do next.

**Contains**:
- Scope lock (what this research covers / doesn't cover)
- What is known (from current sources)
- What is missing (gaps)
- Research directions (where to look next)
- Suggested search queries
- **Top 3 next steps (MANDATORY)**

**Rules**:
- No new facts
- No speculation
- Directional only — this activates the human

### Doc 2 — Semantic Research Brief
**Purpose**: Externalize understanding. The "80% finished" handoff.

**Contains**:
- Semantic core (what this is really about — 2-4 sentences)
- Key themes with supporting key points
- Tensions and contradictions (surfaced, NOT resolved)
- Gaps and their impact
- Confidence assessment
- Clearly labeled speculation (optional, constrained)

**Rules**:
- Every claim must trace to Doc 0
- No new facts
- Uncertainty must be explicit
- Thin output is acceptable if honest

---

## 3. LOCKED DECISIONS (D1-D5)

These decisions are FINAL. Do not deviate.

### D1: Transcript Acquisition Order
```
1. Supadata      → transcript_grounded (primary)
2. Whisper       → transcript_grounded (if Supadata fails)
3. YouTube captions → caption_grounded (if Whisper fails)
4. If all fail   → video_only mode
```

- Gemini ALWAYS runs regardless of transcript availability
- Transcript failure NEVER fails a job
- Degradation is disclosed, not hidden

### D2: video_only Confidence Ceiling
**LOW** — categorical.

Every output from video_only mode has confidence = "low". No exceptions.
Not "up to medium." Not "low-medium." LOW.

### D3: Quotes vs Observations

**QUOTES** = verbatim 1:1 text from grounded transcripts
- Only allowed in transcript_grounded or caption_grounded modes
- Must be exact matches to source text
- Stored in `supporting_quotes` field

**OBSERVATIONS** = inferred content from video_only analysis
- Only used in video_only mode
- MUST be labeled: `type: "observation"`, `approximate: true`
- CANNOT be presented as verbatim
- Stored in `observations` field (separate from quotes)

**In video_only mode**:
- `supporting_quotes: []` — ALWAYS EMPTY
- `observations: [...]` — labeled inferences

### D4: Job Completion Semantics
Jobs complete whenever possible.

**Only infrastructure failures abort a job**:
- Database crash
- Pipeline exception
- API outage
- Zero usable sources provided

**These do NOT fail jobs**:
- Transcript unavailable → degrade + warnings
- Validation soft failures → degrade + warnings
- Thin extraction → degrade + warnings
- Missing metadata → degrade + warnings

### D5: Legacy Pipeline Status
Legacy outputs (producer_packet, clips, quotes, content_blueprint) are:
- **PRESERVED** in codebase (not deleted)
- **COMPLETELY DISABLED** in new semantic pipeline
- **NOT ACTIVE** in any stage
- **NOT CALLED** by any worker task

Treat as commented out. Do not import, invoke, or integrate.
Keep fields in models but mark deprecated. Do not populate.

---

## 4. PIPELINE ARCHITECTURE

```
USER INPUT: List of video URLs
                ↓
┌─────────────────────────────────────────────────────────┐
│ STAGE 1: SOURCE IDENTITY (pre-LLM, deterministic)       │
│ - Fetch metadata from Supadata API                      │
│ - Resolve: title, creator, date, duration, description  │
│ - Assign source_id per video (SRC_1, SRC_2, etc.)       │
│ - Output: List[SourceIdentityPackage]                   │
│ - NO AI CALLS IN THIS STAGE                             │
└─────────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ STAGE 2: TRANSCRIPT ACQUISITION (D1 fallback chain)     │
│ - For each source:                                      │
│   1. Try Supadata transcript                            │
│   2. If fail → try Whisper                              │
│   3. If fail → try YouTube captions                     │
│   4. If fail → mark video_only                          │
│ - Output: TranscriptProvenance per source               │
│   {transcript_source, analysis_mode, confidence_ceiling}│
└─────────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ STAGE 3: SEMANTIC EXTRACTION (Gemini)                   │
│ - Build prompt with analysis_mode from provenance       │
│ - Include mode-specific constraints in prompt           │
│ - Call Gemini                                           │
│ - Output: SemanticExtractionResult per source           │
│   {key_points, claims, themes, tensions,                │
│    supporting_quotes OR observations}                   │
└─────────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ STAGE 4: VALIDATION                                     │
│ - Schema: Valid JSON with required fields               │
│ - Grounding: Every KeyPoint has source_ids              │
│ - Mode rules: video_only → no quotes, only observations │
│ - Apply confidence ceiling from provenance              │
│ - If fail → retry once with constrained prompt          │
│ - If still fail → degrade + warnings, continue (D4)     │
└─────────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ STAGE 5: DOCUMENT ASSEMBLY                              │
│ - Build Doc 0: Source ledger (manifest + text + prov)   │
│ - Build Doc 1: Jump-start (gaps + directions + steps)   │
│ - Build Doc 2: Semantic brief (themes + tensions)       │
│ - Generate markdown versions of each                    │
└─────────────────────────────────────────────────────────┘
                ↓
            JOB COMPLETE
    status: "completed" or "completed_with_warnings"
    artifacts: {source_ledger, jump_start, semantic_brief}
```

---

## 5. HALLUCINATION PROTECTION (Critical)

The entire system is designed around one question: **How do I trust this output?**

### Rule 1: Source Identity Resolved Before AI
Gemini receives source identity (title, creator, date) as INPUT.
Gemini does NOT determine or guess source identity.
If Gemini's output references a different source than provided, that's a validation failure.

### Rule 2: Provenance Determines Capabilities
```python
if analysis_mode == "video_only":
    confidence_ceiling = "low"
    supporting_quotes = []  # MUST be empty
    # Use observations field instead
    
elif analysis_mode == "caption_grounded":
    confidence_ceiling = "medium"
    # Quotes allowed but marked approximate
    
elif analysis_mode == "transcript_grounded":
    confidence_ceiling = "high"
    # Verbatim quotes required
```

### Rule 3: Grounding Validation
Every KeyPoint must have `source_ids: [...]` — cannot be empty.
Every Claim must reference supporting evidence.
Every Theme must reference ≥2 KeyPoints.

If grounding is missing → retry once → if still missing → degrade, don't fail.

### Rule 4: No Invention
If information is missing, say it's missing.
If confidence is low, say it's low.
Never fill gaps with assumptions.
Never smooth over contradictions.

---

## 6. DATA MODELS

### SourceIdentityPackage
```python
source_id: str              # SRC_1, SRC_2, etc.
url: str
title: str
creator: str
published_date: Optional[str]
duration: Optional[str]
description: Optional[str]
```

### TranscriptProvenance
```python
source_id: str
transcript_source: Literal["supadata", "whisper", "youtube_captions", "none"]
transcript_text: Optional[str]
analysis_mode: Literal["transcript_grounded", "caption_grounded", "video_only"]
confidence_ceiling: Literal["low", "medium", "high"]  # Derived from mode
```

### KeyPoint
```python
key_point_id: str           # KP_1, KP_2, etc.
statement: str
source_ids: List[str]       # REQUIRED — cannot be empty
confidence: Literal["low", "medium", "high"]
supporting_claims: List[str]  # CLM_1, CLM_2, etc.
```

### Claim
```python
claim_id: str               # CLM_1, CLM_2, etc.
statement: str
source_id: str
supporting_quotes: List[str]  # Empty if video_only
```

### Theme
```python
theme_id: str               # THEME_1, THEME_2, etc.
label: str
description: str
related_key_points: List[str]  # Must have ≥2
```

### Tension
```python
tension_id: str             # TEN_1, TEN_2, etc.
description: str
involved_key_points: List[str]
```

### Observation (video_only mode only)
```python
observation_id: str         # OBS_1, OBS_2, etc.
description: str            # What was observed — NOT verbatim
source_id: str
approximate: bool = True    # Always true
type: Literal["observation"] = "observation"
timestamp_range: Optional[str]  # Approximate, e.g., "~12:30-14:00"
```

### SemanticExtractionResult
```python
source_id: str
analysis_mode: str
key_points: List[KeyPoint]
claims: List[Claim]
themes: List[Theme]
tensions: List[Tension]
supporting_quotes: List[Quote]      # Empty if video_only
observations: List[Observation]     # Used if video_only
confidence_ceiling: str             # From provenance
```

---

## 7. GEMINI PROMPT CONSTRAINTS

### For ALL modes:
```
SOURCE IDENTITY LOCK (NON-NEGOTIABLE):
- You are analyzing source: {source_id}
- Title: {title}
- Creator: {creator}
- You must NOT guess or substitute source identity
- You must NOT hallucinate metadata, quotes, or context
- If information is missing, say so. Do not invent.
```

### For video_only mode:
```
ANALYSIS MODE: video_only

CRITICAL CONSTRAINTS:
- You have NO transcript text
- You must NOT produce verbatim quotes
- supporting_quotes MUST be an empty array []
- All confidence values MUST be "low"
- Use observations field for anything you infer
- Each observation must have: type="observation", approximate=true
```

### For caption_grounded mode:
```
ANALYSIS MODE: caption_grounded

CONSTRAINTS:
- Quotes may have minor transcription errors
- Timestamps are approximate (±5 seconds)
- Maximum confidence is "medium"
- Note caption source in quote metadata
```

### For transcript_grounded mode:
```
ANALYSIS MODE: transcript_grounded

STANDARD MODE:
- Use verbatim quotes from transcript
- Provide precise timestamps
- High confidence claims allowed when well-supported
```

---

## 8. WHAT NOT TO DO

### DO NOT:
- Collapse Doc 0/1/2 into a single output
- Allow quotes in video_only mode
- Set confidence above "low" in video_only mode
- Fail jobs due to missing transcripts
- Delete legacy code (mark deprecated, don't remove)
- Call legacy pipeline functions (producer_packet, clips, quotes)
- Invent source identity or metadata
- Skip validation stage
- Catch and silence errors without adding warnings

### DO:
- Keep documents separate
- Enforce mode-based constraints
- Degrade gracefully with warnings
- Trace every claim to source material
- Surface uncertainty explicitly
- Add warnings to ctx.warnings for any degradation

---

## 9. IMPLEMENTATION CHECKLIST

Before submitting code, verify:

- [ ] Source identity resolved BEFORE any Gemini call
- [ ] Transcript acquisition follows D1 order: Supadata → Whisper → Captions → video_only
- [ ] Provenance tracked for every source
- [ ] video_only mode: quotes=[], observations used, confidence="low"
- [ ] Every KeyPoint has non-empty source_ids
- [ ] Validation runs after extraction, before assembly
- [ ] Failures degrade (add warnings), don't abort job
- [ ] Doc 0, Doc 1, Doc 2 are separate objects
- [ ] Legacy fields exist but are NOT populated
- [ ] No hardcoded confidence values that ignore provenance

---

## 10. WHEN IN DOUBT

1. Check this document first
2. If the document doesn't answer, ASK — don't guess
3. Prefer degraded output over job failure
4. Prefer explicit warnings over silent problems
5. Prefer thin honest output over padded hallucinated output

---

**END OF CONTEXT DOCUMENT**
