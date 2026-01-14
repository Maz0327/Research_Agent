# Research Agent — Canonical Examples

**Purpose**: These examples define CORRECT system behavior. When prose specs conflict with examples, **examples win**.

**Usage**:
1. Claude Code: Use these to understand expected output structure
2. Gemini Prompts: Include relevant examples as few-shot demonstrations
3. Validation: Use these as test fixtures to verify correct behavior

---

## EXAMPLE INDEX

| Example | When To Use | Critical Lesson |
|---------|-------------|-----------------|
| Degraded Output | video_only mode, transcript failures | No quotes, LOW confidence, explicit disclosure |
| Thin But Acceptable | Limited sources, same perspective | Don't pad, downgrade confidence, strong next steps |
| Conflicting Sources | Sources contradict each other | Surface contradiction, don't resolve it |
| Minimal API Response | API contract reference | Job status, artifacts structure, warnings |
| Producer Packet | Full successful extraction | Complete structure with all fields |
| Content Blueprint | Creative output (SOC-ready) | Angles, hooks, production notes |
| Artifact Index | Confidence summary display | How to present trust signals to user |

---

## EXAMPLE 1: DEGRADED OUTPUT (video_only mode)

**When this applies**:
- Supadata transcript failed
- Whisper failed
- YouTube captions unavailable
- Gemini ran in video_only mode

**Critical rules demonstrated**:
- No verbatim quotes (observations only)
- Confidence ceiling = LOW
- Explicit degradation disclosure
- Job still completes

```markdown
# Degraded Output Example — Transcript Unavailable

**Scenario:** Supadata transcript retrieval failed. YouTube captions unavailable. 
Gemini analysis executed in video-only mode.

**Disclosure:** This analysis is based on multimodal inference from video/audio only. 
No transcript verification was possible. Confidence is downgraded accordingly.

---

## Doc 0 — Source Ledger (Degraded)

**Source 1**
- Type: YouTube Video
- Title: Interview with Creator X
- Duration: 1:42:10
- Transcript Status: ❌ Supadata failed
- Captions: ❌ Not available
- Analysis Mode: video_only

**Skim Summary:**
- Long-form interview covering Event Y
- Speaker appears defensive during timeline discussion
- Repeated emphasis on intent over outcome

**Full Source Text:**
⚠️ TRANSCRIPT UNAVAILABLE

Reason: Supadata failed, captions unavailable
Analysis Mode: video_only
All observations below are approximate inferences, NOT verbatim quotes.

---

## Doc 1 — Jump-Start Research Directions (Degraded)

**What We Have (Approximate):**
- (Observation) Event Y discussed at length
- (Observation) Timeline inconsistencies suggested by repeated reframing

**What We Do NOT Have:**
- Verbatim quotes
- Verified timestamps
- Text-grounded claims

**Critical Gaps:**
- No transcript to verify exact phrasing
- Cannot confirm specific claims without text

**Top 3 Next Steps:**
1. Locate transcript via alternative service
2. Search for written statements by Creator X
3. Identify secondary reporting referencing this interview

---

## Doc 2 — Semantic Research Brief (Degraded)

**Overall Confidence:** LOW

**Key Points:**
- (Approximate observation) Creator X appears to reframe Event Y as unavoidable
- (Approximate observation) Accountability language shifts during interview

**Themes:**
- Intent vs Responsibility
- Narrative Control

**Tensions:**
- Early certainty vs later ambiguity (approximate — needs transcript verification)

**What This Is NOT:**
- This is NOT a quote-verified analysis
- This should NOT be treated as factual proof
- All observations are approximate inferences from video/audio

---
```

**Implementation rule**: If `analysis_mode == "video_only"`:
- `supporting_quotes: []` (empty)
- All key points prefixed with "(Approximate observation)"
- Confidence fields = "low"
- Explicit warning block in each document

---

## EXAMPLE 2: THIN BUT ACCEPTABLE OUTPUT

**When this applies**:
- Few sources (1-2)
- Sources share same perspective
- Limited depth available
- But system worked correctly

**Critical rules demonstrated**:
- Don't pad or hallucinate depth
- Downgrade confidence
- Emphasize gaps and next steps
- Thin is acceptable if honest

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

**Top 3 Next Steps:**
1. Find primary source (statement, document)
2. Locate neutral reporting
3. Identify first occurrence of claim

---

## Doc 2 — Semantic Research Brief

**Confidence:** LOW

**Key Points:**
- Event Y is framed as misconduct
- Claims rely on secondary interpretation

**Themes:**
- Group consensus
- Narrative reinforcement

**Explicit Note:**
⚠️ This output is intentionally thin due to limited source diversity. 
Additional research is required before drawing conclusions.

---
```

**Implementation rule**: Thin output does NOT fail the job. It:
- Sets confidence to LOW
- Adds warning to `ctx.warnings`
- Emphasizes gaps in Doc 1
- Includes explicit note in Doc 2

---

## EXAMPLE 3: CONFLICTING SOURCES

**When this applies**:
- Two or more sources directly contradict each other
- Cannot determine which is correct

**Critical rules demonstrated**:
- Surface the contradiction explicitly
- Do NOT resolve it
- Do NOT pick a side
- Treat contradiction as research asset

```markdown
# Conflicting Sources Example

**Scenario:** Two credible sources directly contradict each other.

---

## Doc 0 — Source Ledger

**Source A (SRC_1):**
- Claim: Event Y occurred in March

**Source B (SRC_2):**
- Claim: Event Y occurred in June

---

## Doc 2 — Semantic Research Brief

**Tension Identified:**
- TEN_1: Timing of Event Y

**Description:**
Source A (SRC_1) states Event Y occurred in March.
Source B (SRC_2) states Event Y occurred in June.
These claims are mutually exclusive.

**Evidence:**
- SRC_1: Timestamped statement at 14:32
- SRC_2: Written report paragraph 3

**System Behavior:**
- No resolution attempted
- Contradiction surfaced as research asset
- User must investigate further

**Next Steps:**
1. Verify via public records
2. Locate contemporaneous posts
3. Identify which source is primary

---
```

**Implementation rule**: When tensions are detected:
- Create Tension object with both source_ids
- Do NOT set one as "correct"
- Add to Doc 2 Tensions section
- Suggest verification paths in Doc 1

---

## EXAMPLE 4: MINIMAL API RESPONSE

**When this applies**:
- Defining API contract
- Frontend integration
- Job status handling

```json
{
  "job_id": "job_12345",
  "status": "completed_with_warnings",
  "artifacts": {
    "source_ledger": { "...": "..." },
    "source_ledger_md": "# SOURCE LEDGER\n...",
    "jump_start": { "...": "..." },
    "jump_start_md": "# JUMP-START\n...",
    "semantic_brief": { "...": "..." },
    "semantic_brief_md": "# SEMANTIC BRIEF\n..."
  },
  "transcript_provenance": {
    "SRC_1": {
      "transcript_source": "supadata",
      "analysis_mode": "transcript_grounded",
      "confidence_ceiling": "high"
    },
    "SRC_2": {
      "transcript_source": "none",
      "analysis_mode": "video_only",
      "confidence_ceiling": "low"
    }
  },
  "warnings": [
    "Transcript unavailable for SRC_2 — analyzed in video_only mode",
    "Limited source diversity — confidence downgraded"
  ]
}
```

**Implementation rule**: 
- Always return all three docs (even if thin)
- Include provenance per source
- Warnings array for any degradation
- Status = "completed_with_warnings" if warnings exist

---

## EXAMPLE 5: PRODUCER PACKET (Full Successful Output)

**When this applies**:
- Reference for complete, non-degraded output
- Shows all fields populated correctly

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
```

---

## EXAMPLE 6: ARTIFACT INDEX / CONFIDENCE SUMMARY

**When this applies**:
- Displaying job results to user
- Trust signal presentation

```markdown
# Artifact Index / Confidence Summary

⚠️ SOURCE IDENTITY LOCK — READ FIRST

This document is derived from explicitly resolved sources.
Source identity (title, creator, date, transcript availability) was determined BEFORE any analysis.

---

**Job:** Creator X Investigation

## Artifacts Generated

| Artifact | Status | Confidence |
|----------|--------|------------|
| Doc 0 — Source Ledger | ✅ Complete | High |
| Doc 1 — Jump-Start | ⚠️ Degraded | Medium |
| Doc 2 — Semantic Brief | ⚠️ Degraded | Medium |

## Source Provenance

| Source | Transcript | Mode | Ceiling |
|--------|------------|------|---------|
| SRC_1 | Supadata ✅ | transcript_grounded | High |
| SRC_2 | Failed ❌ | video_only | Low |

## Warnings

- Transcript unavailable for SRC_2 — analyzed in video_only mode
- Limited source diversity — confidence capped at Medium overall

---
```

---

## HOW TO USE THESE EXAMPLES

### For Claude Code Implementation:
1. Structure output objects to match these examples
2. Use examples as test fixtures
3. When in doubt about format, match the example

### For Gemini Prompts (Few-Shot):
Include relevant example in prompt based on mode:

```python
def build_prompt(analysis_mode: str) -> str:
    base_prompt = "..."
    
    if analysis_mode == "video_only":
        example = DEGRADED_OUTPUT_EXAMPLE
    elif source_count < 3:
        example = THIN_OUTPUT_EXAMPLE
    else:
        example = FULL_OUTPUT_EXAMPLE
    
    return f"{base_prompt}\n\nEXAMPLE OUTPUT:\n{example}"
```

### For Validation:
Check that actual output matches example structure:
- Same fields present
- Same labeling conventions
- Same warning patterns
- Same confidence logic

---

## GOLDEN RULES FROM EXAMPLES

1. **Degraded ≠ Failed** — Thin/degraded output is success with warnings
2. **Disclose, Don't Hide** — Every limitation explicitly stated
3. **Surface, Don't Resolve** — Contradictions are assets
4. **Trace Everything** — Every claim back to source_id
5. **Label Approximations** — video_only observations clearly marked
6. **Top 3 Next Steps** — Always present in Doc 1, even if thin

---

**END OF CANONICAL EXAMPLES**
