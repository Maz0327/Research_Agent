# Research Agent System — Complete Context + Canonical Examples

**Purpose**: This is the SINGLE AUTHORITATIVE document for Claude Code. Contains system context AND verbatim canonical examples.

**Rule**: When prose conflicts with examples, EXAMPLES WIN.

---

# PART 1: SYSTEM CONTEXT

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

### Rule 4: No Invention
If information is missing, say it's missing.
If confidence is low, say it's low.
Never fill gaps with assumptions.
Never smooth over contradictions.

---

## 6. WHAT NOT TO DO

### DO NOT:
- Collapse Doc 0/1/2 into a single output
- Allow quotes in video_only mode
- Set confidence above "low" in video_only mode
- Fail jobs due to missing transcripts
- Delete legacy code (mark deprecated, don't remove)
- Call legacy pipeline functions (producer_packet, clips, quotes)
- Invent source identity or metadata
- Skip validation stage

### DO:
- Keep documents separate
- Enforce mode-based constraints
- Degrade gracefully with warnings
- Trace every claim to source material
- Surface uncertainty explicitly

---

# PART 2: CANONICAL EXAMPLES (VERBATIM)

**These examples are AUTHORITATIVE. When specs conflict with examples, EXAMPLES WIN.**

---

## EXAMPLE 1: DEGRADED OUTPUT (Transcript Unavailable)

```markdown
# Degraded Output Example — Transcript Unavailable

**Scenario:** Supadata transcript retrieval failed. YouTube captions unavailable. Gemini analysis executed in video-only mode.

**Disclosure:** This analysis is based on multimodal inference from video/audio only. No transcript verification was possible. Confidence is downgraded accordingly.

---

## Doc 0 — Source Ledger (Degraded)

**Source 1**
- Type: YouTube Video
- Title: Interview with Creator X
- Duration: 1:42:10
- Transcript Status: ❌ Supadata failed
- Captions: ❌ Not available
- Analysis Mode: Gemini video-only

**Skim Summary:**
- Long-form interview covering Event Y
- Speaker appears defensive during timeline discussion
- Repeated emphasis on intent over outcome

**Full Context Data:**
- ⚠️ Full transcript unavailable
- Video timestamps referenced are approximate

---

## Doc 1 — Jump-Start Research Directions (Degraded)

**High-Confidence Observations:**
- Event Y discussed at length
- Timeline inconsistencies suggested by repeated reframing

**Low-Confidence Inferences:**
- Emotional cues suggest discomfort during specific segments
- Possible contradiction between early and late statements

**Critical Gaps:**
- No verbatim quotes available
- Cannot verify exact phrasing or timestamps

**Next Research Directions:**
1. Locate transcript via alternative service
2. Search for written statements by Creator X
3. Identify secondary reporting referencing this interview

---

## Doc 2 — Semantic Research Brief (Degraded)

**Overall Confidence:** Low

**Key Points:**
- Creator X repeatedly reframes Event Y as unavoidable
- Accountability language shifts over course of interview

**Themes:**
- Intent vs Responsibility
- Narrative Control

**Tensions:**
- Early certainty vs later ambiguity

**What This Is NOT:**
- This is not a quote-verified analysis
- This should not be treated as factual proof

---

**End of Degraded Output Example**
```

---

## EXAMPLE 2: THIN BUT ACCEPTABLE OUTPUT

```markdown
# Thin-but-Acceptable Output Example

**Scenario:** User provided only two sources from similar perspectives. Limited depth available.

---

## Doc 0 — Source Ledger

**Sources Provided:**
- 2 YouTube commentary videos
- Same creator community

**Skim Summary:**
- Both videos cover Event Y
- Arguments largely overlap
- No primary evidence cited

---

## Doc 1 — Jump-Start Research Directions

**What We Have:**
- Consistent narrative framing
- Shared assumptions

**What We Do NOT Have:**
- Opposing viewpoints
- Primary documentation
- Direct statements from involved parties

**Suggested Next Steps:**
1. Find primary source (statement, document)
2. Locate neutral reporting
3. Identify first occurrence of claim

---

## Doc 2 — Semantic Research Brief

**Confidence:** Low

**Key Points:**
- Event Y is framed as misconduct
- Claims rely on secondary interpretation

**Themes:**
- Group consensus
- Narrative reinforcement

**Explicit Note:**
This output is intentionally thin due to limited source diversity. Additional research is required before drawing conclusions.

---

**End of Thin-but-Acceptable Output Example**
```

---

## EXAMPLE 3: CONFLICTING SOURCES

```markdown
# Conflicting Sources Example

**Scenario:** Two credible sources directly contradict each other.

---

## Doc 0 — Source Ledger

**Source A:**
- Claim: Event Y occurred in March

**Source B:**
- Claim: Event Y occurred in June

---

## Doc 2 — Semantic Research Brief

**Contradiction Identified:**
- Timing of Event Y

**Evidence:**
- Source A timestamped statement
- Source B written report

**System Behavior:**
- No resolution attempted
- Contradiction surfaced as research asset

**Next Steps:**
1. Verify via public records
2. Locate contemporaneous posts

---

**End of Conflicting Sources Example**
```

---

## EXAMPLE 4: MINIMAL API RESPONSE

```markdown
# Minimal API Response Example

```json
{
  "job_id": "job_12345",
  "status": "completed_with_warnings",
  "artifacts": [
    {"type": "doc0", "confidence": "high"},
    {"type": "doc1", "confidence": "medium"},
    {"type": "doc2", "confidence": "medium"},
    {"type": "producer_packet"},
    {"type": "content_blueprint"}
  ],
  "warnings": [
    "Transcript unavailable for Source 2",
    "Limited source diversity"
  ]
}
```

---

**End of Minimal API Response Example**


---

## Canonical Example Artifacts (Authoritative References)

The following example artifacts are **canonical**. They define correct system behavior and MUST be used as reference patterns during implementation, testing, and future iteration. These examples are not illustrative — they are normative.

### Core Creative Outputs
- **Producer Packet — Example Output**
  - Defines creative activation without collapsing research layers
  - Demonstrates safe semi-creative reasoning grounded in prior docs

- **Content Blueprint — Example Output**
  - Defines SOC-ready execution framing
  - Shows how research activates strategy without becoming prescriptive

### Trust & Failure-Mode Outputs (Critical)
- **Degraded Output Example**
  - Supadata transcript failure
  - No captions available
  - Gemini video-only analysis
  - Explicit confidence downgrade and user disclosure

- **Thin-but-Acceptable Output Example**
  - Limited and one-sided sources
  - Intentionally sparse output
  - No padding, no hallucinated depth

- **Conflicting Sources Example**
  - Direct contradiction surfaced
  - No forced resolution
  - Contradiction treated as research asset

### System & UX Anchors
- **Artifact Index / Confidence Summary Example**
  - Defines how artifacts are surfaced to users
  - Establishes confidence signaling and warnings

- **Minimal API Response Example**
  - Anchors frontend/backend contract
  - Defines job status, artifacts, and warning surfaces

### Implementation Rule
If an implementation decision conflicts with one of the above examples, **the example wins**. Update the spec only after updating or replacing the example artifact.

---

**End of Context Handoff Update**
```

---

## EXAMPLE 5: PRODUCER PACKET

```markdown
# Producer Packet — Example Output

**TOPIC:** Creator X controversy: what changed, what's claimed, what's provable

**MODE:** Investigation

**CONFIDENCE:** Medium (sources skew one-sided; missing primary documentation)

---

## 1. Quick Take
- This topic centers on **inconsistent timelines and disputed intent** surrounding Event Y.
- Coverage splits into two camps: pattern-of-behavior vs context-removed defenses.
- Strongest material: first-person statements repeated across multiple sources.
- Weakest material: missing primary records (messages, dates, agreements).

**Top 3 next steps:**
1. Locate original posts or archived pages around Event Y.
2. Identify one credible opposing perspective (non-fan, non-reactive).
3. Build a verified timeline with claimed vs confirmed labels.

---

## 2. What We Know vs What's Claimed

### Verified / Strongly Supported
- Event Y occurred within a specific time window referenced by three sources.
- Creator X provides a direct explanation of rationale A.
- Outcome Z confirmed by publication date.

### Claimed / Unverified
- Claims of coercion lack primary evidence.
- References to "receipts" are made without production.
- Motive-based explanations are speculative.

---

## 3. Timeline Overview
- T0: Pre-event context
- T1: Event Y occurs
- T2: Public reaction phase
- T3: Creator response statement
- T4: Aftermath and consequences

**Timeline conflict:** Source A and Source C disagree on T1 timing.

---

## 4. Core Themes
1. Accountability vs Context
2. Incentives and Pressure
3. Narrative Drift Over Time
4. Audience Polarization

---

## 5. Tensions / Contradictions
- Timeline mismatch between early and later statements.
- Responsibility framing shifts ("I chose" vs "I had to").
- Evidence referenced but not shown.

---

## 6. Evidence Handles
- Video 1: Direct explanation of rationale A
- Video 2: Accusation summary
- Article: Outcome confirmation
- Thread: Opposing arguments

---

## 7. Gaps & Research Directions

### Missing Perspectives
- Direct response from collaborator
- Neutral third-party reporting

### Primary Sources Needed
- Archived original posts
- Public contract references (if available)

---

## 8. Landmines
- Defamation risk from motive claims
- Bias due to one-sided sources
- Misleading certainty from timeline conflicts

---

## 9. Suggested Structures

### Structure A — What We Can Prove
- Act 1: Present contradiction
- Act 2: Timeline comparison
- Act 3: Unresolved gap

### Structure B — Narrative Drift
- Act 1: Initial framing
- Act 2: Shifts over time
- Act 3: Why audiences split

---

**End of Producer Packet Example**
```

---

## EXAMPLE 6: CONTENT BLUEPRINT

```markdown
# Content Blueprint — Example Output

**GOAL:** Provide executable content angles without starting from zero

**TARGET:** Long-form video, livestream, and short-form SOC

---

## A. Angle Library

### Angle 1 — The Timeline Doesn't Match
- Hook: Two versions of the story can't both be true
- Core Question: What changed—facts or framing?
- Proof Needed: Verified dates and archives

### Angle 2 — Accountability vs Context
- Hook: Is context explanation or excuse?
- Core Question: Where is the line?
- Proof Needed: Direct statements from both camps

### Angle 3 — How Stories Mutate Online
- Hook: By the time it hits your feed, it's a different story
- Core Question: Where did distortion happen?
- Proof Needed: Earliest repost chain

### Angle 4 — Incentives Shape Behavior
- Hook: Nobody acts in a vacuum
- Core Question: What pressures mattered most?
- Proof Needed: Public brand relationships

---

## B. Short-Form SOC Hooks
- "This timeline gap changes everything"
- "Everyone says receipts—where are they?"
- "Two camps, one missing document"

---

## C. Livestream Segments

### Segment 1 — Build the Timeline Together
- Audience submits sources
- Claims categorized live

### Segment 2 — Debunk vs Confirm
- Criteria-based evaluation
- No opinion until evidence

---

## D. Production Notes
- Lead with tension, not background
- Label speculation clearly
- End with research directions

---

**End of Content Blueprint Example**
```

---

## EXAMPLE 7: ARTIFACT INDEX / CONFIDENCE SUMMARY

```markdown
⚠️ SOURCE IDENTITY LOCK — READ FIRST

This document is derived from explicitly resolved sources.
Source identity (title, creator, date, transcript availability) was determined BEFORE any analysis.

You must NOT:
- infer which video/article is being discussed
- substitute a similar or "likely" source
- hallucinate metadata, quotes, or context
- assume completeness or accuracy beyond what is explicitly present

If source identity is unclear or degraded, that uncertainty MUST be stated.
When in doubt: downgrade confidence, surface the gap, and stop.

# Artifact Index / Confidence Summary Example

**Job:** Creator X Investigation

---

## Artifacts Generated

- ✅ Doc 0 — Source Ledger (High Confidence)
- ⚠️ Doc 1 — Jump-Start Research Directions (Medium Confidence)
- ⚠️ Doc 2 — Semantic Research Brief (Medium Confidence)
- ✅ Producer Packet
- ✅ Content Blueprint

---

## Warnings

- Transcript unavailable for Source 2
- Limited source diversity

---

**End of Artifact Index Example**
```

---

# PART 3: IMPLEMENTATION CHECKLIST

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

# WHEN IN DOUBT

1. Check this document first
2. If the document doesn't answer, ASK — don't guess
3. Prefer degraded output over job failure
4. Prefer explicit warnings over silent problems
5. Prefer thin honest output over padded hallucinated output

---

**END OF DOCUMENT**
