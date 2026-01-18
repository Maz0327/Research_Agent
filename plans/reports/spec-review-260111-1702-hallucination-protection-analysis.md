# Spec Review: Hallucination Protection & Recommended Changes

**Date**: January 11, 2026
**Scope**: All files in `Active Docs/REVIEW THESE FILES/`
**Focus**: Gemini hallucination prevention + spec improvements

---

## Executive Summary

The specs are **well-designed** with strong epistemic foundations. However, I identified **12 critical gaps** in hallucination protection and **8 recommended additions** to strengthen the system.

---

## Part 1: Hallucination Protection Analysis

### Current Strengths

| Protection | Document | Status |
|------------|----------|--------|
| Source Identity Lock | AI Research Assistant Blueprint | ✅ Excellent |
| No new facts beyond Doc 0 | RASS, Operational Definitions | ✅ Clear |
| Speculation labeling | Doc Output Format, Synthesis Prompt | ✅ Defined |
| Video-only quote prohibition | Validation Rules (12.2) | ✅ Defined |
| Grounding validation | Validation Rules (Section 3) | ✅ Hard fail |

### Critical Gaps (Must Fix)

#### 1. **Video-only mode allows "approximate quotes" - CONTRADICTION**

**Location**: Gemini Semantic Extraction Prompt Pack (Section 8)

**Problem**: The prompt says:
> "Mark all quotes as `approximate: true`" and "Extract approximate quotes (paraphrased, not verbatim)"

But Validation Rules (12.2) says:
> "Quotes MUST be marked `unverified`" and confidence ceiling is `low_confidence`

And your clarified rule says:
> "Video-only: NO quotes allowed, supporting_quotes must be empty"

**Fix Required**:
```markdown
#### If `video_only`:

IMPORTANT: You are analyzing video WITHOUT a transcript.

You MUST:
- DO NOT generate any quotes — supporting_quotes MUST be empty
- DO NOT claim verbatim or approximate accuracy
- Include an `analysis_limitations` field in your output
- Cap confidence at `low` — no `medium` or `high` claims
- Clearly label all key points as inference-based

You MAY:
- Identify themes from visual/audio cues
- Extract entities and topics
- Describe observed behavior (not quoted speech)
```

#### 2. **Transcript acquisition order is inconsistent**

**RASS Section 4.2** says: "YouTube captions → Supadata → Whisper"
**RASS Section 8.1** says: "Supadata → YouTube captions → None"
**Your locked decision** says: "Supadata → YouTube captions → video-only"

**Fix Required**: Standardize to locked order in ALL docs:
1. Supadata (primary)
2. YouTube captions (fallback)
3. Video-only (degraded)

Remove Whisper references unless explicitly adding it.

#### 3. **Missing: Source Identity Contract enforcement in extraction prompt**

**Problem**: The "Source Identity Lock" banner exists in the Blueprint file but is NOT included in the Gemini Semantic Extraction Prompt Pack.

**Fix Required**: Add to Gemini Semantic Extraction Prompt (Section 0):
```markdown
## SOURCE IDENTITY CONTRACT (BEFORE REASONING)

Before extracting ANY semantic content, you MUST verify:
1. source_id is provided
2. source metadata (title, creator, url) is resolved
3. transcript_provenance is known

If ANY of these are missing or unclear:
- DO NOT guess or infer the source identity
- Mark identity as "unresolved"
- Proceed with degraded confidence
- Add explicit warning to output

You must NEVER:
- Assume which video/article is being discussed
- Substitute a "similar" or "likely" source
- Hallucinate metadata, quotes, or context
```

#### 4. **Missing: Explicit prohibition on cross-source quote attribution**

**Problem**: Nothing prevents Gemini from attributing a quote from Source A to Source B.

**Fix Required**: Add to extraction prompt:
```markdown
QUOTE ATTRIBUTION RULE:
- Every quote MUST include exactly one source_id
- Quotes MUST NOT be merged across sources
- If a quote appears in multiple sources, create separate entries
- Never attribute a quote to a source unless the exact text appears in that source
```

#### 5. **Missing: Hallucination recovery in retry prompts**

**Problem**: Retry prompts ask for "more specific key points" but don't address hallucination specifically.

**Fix Required**: Add to Retry Prompt (Section 4):
```markdown
IMPORTANT: Your previous output may have included unsupported assertions.

Before re-extraction:
- Verify every key point traces to explicit source text
- Remove any claims not directly supported by the provided content
- If uncertain whether something was stated, mark as GAP not KEY POINT
- Prefer fewer, grounded outputs over more, speculative ones
```

#### 6. **FULL SOURCE TEXT placeholder rule missing from Doc Output Format**

**Problem**: If transcript unavailable, the spec doesn't specify what goes in the FULL SOURCE TEXT section.

**Fix Required**: Add to Document Output Format (Doc 0 section):
```markdown
#### FULL SOURCE TEXT (Canonical)

If full text is available:
<verbatim transcript or article text>

If full text is unavailable:
---
⚠️ FULL SOURCE TEXT UNAVAILABLE

Transcript Status: [supadata_failed | captions_failed | none]
Analysis Mode: [video_only]
Reason: [specific error or "both acquisition methods failed"]

This source was analyzed without transcript verification.
All extracted content should be treated as approximate.
---

NEVER invent or reconstruct missing source text.
```

#### 7. **Degraded Output Example has quotes - violates video-only rule**

**Location**: Degraded Output Example.md

**Problem**: Doc 1 says "Timeline inconsistencies suggested by repeated reframing" - this implies quote-like observations in video-only mode.

**Fix Required**: Rewrite Doc 1 section:
```markdown
## Doc 1 — Jump-Start Research Directions (Degraded)

**Observable Patterns (Visual/Audio):**
- Extended discussion of Event Y (inferred from segment length)
- Speaker posture suggests discomfort during certain segments
- Topic shifts observed at approximate timestamps

**CANNOT VERIFY:**
- Exact statements or claims made
- Timeline accuracy
- Intent or meaning of observed behaviors

**Critical Gaps:**
- No verbatim quotes available
- Cannot verify phrasing or context
- All observations are inference-based
```

#### 8. **Missing: Confidence ceiling enforcement per analysis mode**

**Problem**: Specs define confidence ceilings but don't specify HOW to enforce them.

**Fix Required**: Add to Validation Rules:
```markdown
### Confidence Ceiling Enforcement (Machine-Checked)

| Analysis Mode | Max Confidence | Validation |
|---------------|----------------|------------|
| transcript_grounded | high | No restriction |
| caption_grounded | medium | Reject if confidence = "high" |
| video_only | low | Reject if confidence ≠ "low" |

If a key point or claim exceeds its mode's ceiling:
1. Automatically downgrade to ceiling value
2. Add warning: "Confidence auto-downgraded from {original} to {ceiling}"
3. Log for review
```

### Medium Priority Gaps

#### 9. **Missing: Entity hallucination prevention**

**Problem**: Specs don't address Gemini inventing entities that don't exist in the source.

**Fix Required**: Add to extraction constraints:
```markdown
ENTITY EXTRACTION RULES:
- Extract ONLY entities explicitly named in source text
- Do NOT infer "likely" participants not mentioned
- If entity role is unclear, mark as "role: unconfirmed"
- Cross-reference entities against transcript before output
```

#### 10. **Missing: Timestamp hallucination prevention**

**Problem**: In video-only mode, Gemini might claim precise timestamps it can't verify.

**Fix Required**: Add to video-only mode instructions:
```markdown
TIMESTAMP RULES (video_only mode):
- All timestamps MUST be marked "approximate"
- Use ranges instead of precise times: "~12:00-15:00" not "12:34"
- Never claim "at timestamp X, the speaker said Y" — use "around X, topic Y was discussed"
```

#### 11. **Missing: Synthesis prompt needs Doc 0 cross-reference check**

**Problem**: Semantic Synthesis Prompt says it receives Key Points but doesn't enforce that they exist in Doc 0.

**Fix Required**: Add to Semantic Synthesis Prompt:
```markdown
BEFORE SYNTHESIZING:
1. Verify every Key Point ID exists in provided input
2. Verify every Theme references valid Key Point IDs
3. If any ID is unresolved, STOP and report the mismatch
4. Do NOT create new Key Points during synthesis
```

#### 12. **Missing: Gap Identification can't hallucinate "expected" information**

**Problem**: Gap Identification Prompt defines gaps as "information a researcher would expect" - this is subjective and could lead to hallucinated expectations.

**Fix Required**: Tighten gap definition:
```markdown
A valid Gap is:
- Information explicitly referenced but not provided (e.g., "receipts mentioned but not shown")
- Standard context missing for the topic type (e.g., opposing perspective in controversy)
- Follow-up that the sources themselves suggest

A Gap is NOT:
- Information YOU think should exist
- Information that would "strengthen" the narrative
- Speculation about what might be hidden
```

---

## Part 2: Recommended Additions

### Addition 1: Pre-Flight Source Identity Resolver

**Why**: Gemini currently receives source metadata inline. If metadata is wrong or missing, hallucination propagates.

**Recommendation**: Add a pre-extraction stage:
```python
def resolve_source_identity(source_input):
    """
    BEFORE calling Gemini, resolve and lock source identity.
    Returns: SourceIdentity or raises UnresolvedIdentityError
    """
    identity = {
        "source_id": generate_stable_id(source_input),
        "title": source_input.get("title") or "UNRESOLVED",
        "creator": source_input.get("creator") or "UNRESOLVED",
        "url": source_input.get("url") or "UNRESOLVED",
        "transcript_status": check_transcript_availability(source_input),
        "identity_confidence": "high" if all_fields_present else "degraded"
    }

    if identity["identity_confidence"] == "degraded":
        identity["warnings"] = ["Source identity partially unresolved"]

    return identity
```

### Addition 2: Quote Verification Gate

**Why**: Claims reference quotes, but nothing verifies quotes exist in source text.

**Recommendation**: Add machine validation:
```python
def verify_quote_in_source(quote: str, source_text: str, mode: str) -> QuoteVerification:
    if mode == "video_only":
        return QuoteVerification(status="prohibited", error="Quotes not allowed in video-only")

    if mode == "caption_grounded":
        # Fuzzy match with tolerance for caption errors
        match = fuzzy_match(quote, source_text, threshold=0.85)
        return QuoteVerification(status="approximate", match_score=match.score)

    # transcript_grounded
    if quote in source_text:
        return QuoteVerification(status="verified", match_score=1.0)

    return QuoteVerification(status="unverified", error="Quote not found in source")
```

### Addition 3: Hallucination Confidence Score

**Why**: Some outputs are more hallucination-prone than others. Surface this to users.

**Recommendation**: Add to job output:
```json
{
  "hallucination_risk": {
    "overall": "low | medium | high",
    "factors": [
      {"factor": "transcript_availability", "risk": "low", "note": "All sources have transcripts"},
      {"factor": "quote_verification", "risk": "medium", "note": "2 of 5 quotes unverified"},
      {"factor": "source_diversity", "risk": "high", "note": "Single perspective"}
    ]
  }
}
```

### Addition 4: Chain-of-Custody Metadata

**Why**: Track exactly how each piece of information flowed through the pipeline.

**Recommendation**: Add provenance to every semantic unit:
```json
{
  "key_point_id": "KP_3",
  "statement": "...",
  "provenance": {
    "extracted_at": "2026-01-11T12:00:00Z",
    "extraction_model": "gemini-2.5-flash",
    "extraction_mode": "transcript_grounded",
    "source_ids": ["SRC_1"],
    "verification_status": "grounded",
    "human_reviewed": false
  }
}
```

### Addition 5: Missing Examples to Create

The Missing Examples Tracker is outdated. Based on my review:

| Example | Status | Priority |
|---------|--------|----------|
| Degraded Output | Exists but needs fix (quotes in video-only) | CRITICAL |
| Thin But Acceptable | Exists, good | Done |
| Conflicting Sources | Exists but minimal | Enhance |
| Minimal API Response | Exists, good | Done |
| Artifact Index | Exists, good | Done |
| **Multi-Source Merge** | MISSING | High |
| **Quote Verification Failure** | MISSING | High |
| **Partial Ingestion Success** | MISSING | Medium |

### Addition 6: Explicit "Stealth Extraction" Prevention

**Why**: Doc 2 might introduce facts that seem like synthesis but are actually new claims.

**Recommendation**: Add to Semantic Synthesis Prompt:
```markdown
STEALTH EXTRACTION PROHIBITION:

You MUST NOT:
- State specific facts not present in the Key Points
- Add dates, names, or events not in Doc 0
- Reference external knowledge about the topic
- "Remember" context not provided in input

Every factual assertion in Doc 2 must trace to a Key Point ID.
If you find yourself writing facts without IDs, STOP.
```

### Addition 7: User-Facing Degradation Disclosure

**Why**: Users need to know when output quality is compromised.

**Recommendation**: Add standardized banner system:
```markdown
## Degradation Disclosure Banners (Mandatory)

### Banner 1: Video-Only Analysis
⚠️ VIDEO-ONLY ANALYSIS
This source was analyzed without transcript text.
Observations are approximate. No verbatim quotes available.
Confidence ceiling: LOW

### Banner 2: Limited Diversity
⚠️ LIMITED SOURCE DIVERSITY
All sources share similar perspectives.
Key gaps may exist. Additional research strongly recommended.

### Banner 3: Partial Ingestion
⚠️ PARTIAL DATA
2 of 4 sources failed to ingest completely.
Output reflects available sources only.
```

### Addition 8: Build Instructions Path Alignment

**Problem**: Claude Code Build Instructions references paths that don't exist in repo.

**Current (wrong)**:
```
backend/
  workers/
    celery_tasks.py
```

**Actual repo**:
```
backend/
  worker.py
  pipeline/
    stages.py
```

**Fix**: Update Build Instructions Section 1 to match actual repo structure.

---

## Part 3: Summary of Required Changes

### Files to Edit

| File | Changes Needed |
|------|----------------|
| Gemini Semantic Extraction Prompt Pack | Add Source Identity Contract, fix video-only quote rules, add cross-source attribution rule |
| Validation & Retry Rules | Add confidence ceiling enforcement, fix transcript order |
| Document Output Format | Add FULL SOURCE TEXT placeholder rule |
| Degraded Output Example | Remove quotes, align with video-only rules |
| RASS | Fix transcript order (Section 4.2 conflicts with 8.1) |
| Claude Code Build Instructions | Align paths to actual repo |
| Missing Examples Tracker | Update status, add missing examples |
| Gap Identification Prompt | Tighten "expected information" definition |
| Semantic Synthesis Prompt | Add stealth extraction prohibition |

### Files That Are Good

| File | Status |
|------|--------|
| Operational Definitions | Excellent, add transcript provenance definitions |
| Deep Research Booster | Good as-is |
| Producer Packet Example | Good as-is |
| Content Blueprint Example | Good as-is |
| Thin But Acceptable Example | Good as-is |
| AI Research Assistant Blueprint | Excellent - Source Identity Lock is model for others |

---

## Unresolved Questions

1. **Whisper**: Should it be added as fallback after captions, or explicitly excluded?
2. **Legacy outputs**: producer_packet/clips/quotes - keep, deprecate, or run in parallel?
3. **Multi-video handling**: Per-video extraction then merge, or batch extraction?
4. **Confidence auto-downgrade**: Silent or require user acknowledgment?

---

**End of Report**
