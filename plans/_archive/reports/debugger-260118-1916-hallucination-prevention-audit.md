# Hallucination Prevention System Audit (2026 Best Practices)

**Auditor:** debugger subagent
**Date:** 2026-01-18
**Scope:** Full hallucination prevention system vs. 2026 best practices
**Files Audited:** 7 core files + 2 mode-specific prompts

---

## Executive Summary

**Overall Status:** STRONG with targeted gaps

The Research Agent implements a sophisticated, multi-layered hallucination prevention system that exceeds many 2026 best practices. Key strengths include confidence ceilings, quote verification, source isolation, and empty output permission. Critical gaps exist in chain-of-thought prompting, output verification loops, and RAG/grounding.

**Priority Gaps:**
1. HIGH: No chain-of-thought in prompts (limits reasoning transparency)
2. HIGH: Limited output verification loops (only 1 retry attempt)
3. MEDIUM: No external grounding (RAG or search verification)
4. MEDIUM: Uncertainty not penalized less than confident errors

---

## Best Practice Comparison Matrix

| Best Practice | Status | Implementation | Gap | Priority |
|--------------|--------|----------------|-----|----------|
| **1. Confidence Scoring** | ✅ EXCELLENT | Mode-based ceilings (HIGH/MEDIUM/LOW), auto-downgrade on ceiling violation | None | - |
| **2. Hybrid Approach** | 🟡 PARTIAL | Prompting + confidence + verification, NO RAG | Missing RAG/search grounding | MED |
| **3. Citation Requirements** | ✅ EXCELLENT | Provenance chain: quotes→claims→key_points, source_id required everywhere | None | - |
| **4. Penalize Confident Errors** | 🔴 MISSING | System treats all errors equally | No penalty differentiation | MED |
| **5. Chain-of-Thought** | 🔴 MISSING | Direct extraction prompts, no reasoning steps exposed | No CoT in prompts | HIGH |
| **6. Output Verification** | 🟡 PARTIAL | 1 retry on validation failure, quote verification post-extraction | Limited retry budget | HIGH |
| **7. Source Attribution** | ✅ EXCELLENT | Source Identity Lock Block, pre-LLM resolution, no inference allowed | None | - |
| **8. Grounding (RAG/Search)** | 🔴 MISSING | No external knowledge retrieval, only source content | No RAG or search grounding | MED |
| **9. Consistency Analysis** | 🟡 PARTIAL | Tension detection across key points, no multi-extraction consistency | Single extraction per source | LOW |
| **10. LLM-as-Judge** | 🔴 MISSING | No secondary LLM validation | No judge verification | LOW |

**Legend:** ✅ Implemented well | 🟡 Partial | 🔴 Not implemented

---

## Current Implementation Analysis

### 1. Confidence Ceiling System (EXCELLENT)

**Files:** `semantic_units.py`, `semantic_validation.py`, `mode_selector.py`

**What Exists:**
- Categorical confidence levels (HIGH/MEDIUM/LOW) instead of numeric scores
- Mode-based ceilings enforced at multiple layers:
  - `transcript_grounded`, `article_fetched`: HIGH
  - `caption_grounded`, `text_provided`, `ocr_extracted`: MEDIUM
  - `video_only`: LOW (always)
- Auto-downgrade on ceiling violation with warnings
- Validation checks confidence against ceiling in `validate_confidence_ceiling()`
- Enforcement in `SemanticExtractionResult.enforce_confidence_ceiling()`

**Code Example:**
```python
# semantic_validation.py:522-542
if kp_idx > ceiling_idx:
    # Auto-downgrade
    kp["confidence"] = ceiling.value
    kp["_confidence_downgraded"] = True
    results.append(ValidationResult(
        level=ValidationLevel.WARNING,
        message=(f"Key point {kp.get('key_point_id')} confidence downgraded "
                 f"from {kp_confidence} to {ceiling.value} (mode ceiling)")
    ))
```

**Gap:** None. This is best-in-class.

---

### 2. Quote Verification (EXCELLENT)

**Files:** `quote_verification.py`, `semantic_extraction.py`

**What Exists:**
- RapidFuzz-based fuzzy matching against source transcript
- Three-tier verification:
  - `VERIFIED`: match ratio ≥0.7
  - `UNCERTAIN`: 0.5-0.7 (flagged but kept)
  - `LIKELY_HALLUCINATED`: <0.5 (removed)
- Post-extraction verification in `verify_quotes_in_extraction()`
- Hallucinated quotes auto-removed before downstream processing
- Works on both standalone quotes and claim supporting_quotes

**Code Example:**
```python
# quote_verification.py:100-112
def verify_quote(quote_text: str, transcript: str, threshold: float = 0.7):
    # Exact substring match first
    if quote_norm in transcript_norm:
        return {"verified": True, "score": 1.0, "status": "VERIFIED"}

    # Fuzzy matching for approximate quotes
    score = _fuzzy_token_set_ratio(quote_norm, window)
    return {
        "verified": best_score >= threshold,
        "score": best_score,
        "status": _get_status(best_score, threshold, strict_threshold),
    }
```

**Gap:** None for text-based sources. Video-only mode correctly prohibits quotes entirely.

---

### 3. Source Isolation (EXCELLENT)

**Files:** `semantic_extraction.py`, Architecture rules

**What Exists:**
- Each source extracted in separate LLM call (stage loop in `stage_semantic_extraction`)
- Sources never see each other during extraction
- Synthesis stage combines extractions AFTER all complete
- Pre-LLM source identity resolution prevents model guessing
- Source Identity Lock Block in prompts (boxed format)

**Code Example:**
```python
# semantic_extraction.py:508-580
for package in packages:
    # Isolated extraction per source
    result, validation_report, cost = extract_semantic_structure(
        gemini_client=gemini_client,
        source_id=source_id,
        source_content=content,
        analysis_mode=analysis_mode,  # Pre-resolved, no LLM inference
        title=package.title,
    )
    ctx.semantic_extractions.append(result)
```

**Prompt Lock Block:**
```
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  source_id: {source_id}                                  ║
║  title: {title}                                          ║
║  analysis_mode: {mode}                                   ║
║  confidence_ceiling: {ceiling}                           ║
╚══════════════════════════════════════════════════════════╝
```

**Gap:** None. Prevents cross-source hallucination.

---

### 4. Empty Output Permission (EXCELLENT)

**Files:** Mode-specific prompts, base prompt templates

**What Exists:**
- Prompts explicitly allow empty arrays for themes, tensions, gaps
- Recovery prompt instructs sparse output over padding
- Validation uses soft-fail for thin output (warns but continues)
- `extraction_warnings` field for explaining limited output

**Code Example:**
```python
# semantic_extraction_prompt.py:484-504
SEMANTIC_EXTRACTION_RECOVERY_PROMPT = """Extract ONLY what is clearly present.

If meaning is sparse:
- extract fewer but precise key points
- explicitly surface uncertainty
- identify what cannot be determined
- MUST include "extraction_warnings" explaining why fields are limited

Do NOT pad output.
"""
```

**Gap:** None. Prevents forced hallucination.

---

### 5. Provenance Tracking (EXCELLENT)

**Files:** `semantic_units.py`, `semantic_validation.py`

**What Exists:**
- Every semantic unit requires source attribution:
  - `KeyPoint.source_ids`: list[str] (REQUIRED, validated)
  - `Claim.source_id`: str
  - `Quote.source_id`: str
  - `Theme.sources_supporting`: list[str] (Phase 5)
  - `Tension.sources_position_a/b`: list[str] (Phase 5)
- Validation hard-fails if provenance broken:
  - `validate_grounding()` checks key points have source_ids
  - `validate_based_on_references()` validates citation IDs exist
- ID naming convention enforced (SRC_*, KP_*, CLM_*, QT_*)

**Code Example:**
```python
# semantic_validation.py:210-218
for kp in data.get("key_points", []):
    source_ids = kp.get("source_ids", [])
    if not source_ids:
        results.append(ValidationResult(
            level=ValidationLevel.HARD_FAIL,
            message=f"Key point {kp.get('key_point_id')} has no source references",
            field="key_points",
        ))
```

**Gap:** None. Full chain-of-custody for claims.

---

### 6. Mode-Specific Quote Handling (EXCELLENT)

**Files:** `mode_selector.py`, mode prompts, `semantic_validation.py`

**What Exists:**
- Three quote permission tiers:
  - **QUOTE_REQUIRED:** `transcript_grounded`, `caption_grounded`, `article_fetched`
  - **DEGRADED_QUOTES:** `text_provided`, `ocr_extracted` (quotes allowed with warnings)
  - **NO_QUOTES:** `video_only` (hard fail if quotes present)
- Degraded quotes marked with `_accuracy_unverified: true`
- Validation enforces quote rules per mode
- `video_only` uses `approximate_observations` instead

**Code Example:**
```python
# semantic_validation.py:468-482
if analysis_mode in NO_QUOTE_MODES:
    if quote_count > 0:
        results.append(ValidationResult(
            level=ValidationLevel.HARD_FAIL,
            message=(f"QUOTES NOT ALLOWED in {analysis_mode.value} mode. "
                     f"Found {quote_count} quote(s). Use approximate_observations instead."),
        ))
```

**Gap:** None. Prevents inappropriate quoting.

---

## Identified Gaps (Prioritized)

### GAP 1: No Chain-of-Thought Prompting (HIGH PRIORITY)

**Current State:**
- Prompts request direct extraction output (JSON schema)
- No reasoning steps exposed
- Model jumps straight to conclusions
- Cannot trace how model arrived at themes/tensions

**2026 Best Practice:**
Chain-of-thought prompting shows intermediate reasoning:
```
"First, identify all explicit claims in the source.
Then, group related claims by topic.
Finally, identify patterns across claim groups."
```

**Impact:**
- Cannot audit LLM reasoning
- Harder to catch logical errors
- Less transparency for researchers
- Missed opportunity for self-correction

**Recommendation:**
Add reasoning steps to prompts:
```python
LAYERED_EXTRACTION_PROMPT = """
STEP 1: IDENTIFY CLAIMS
List all explicit claims in the source. For each claim, note:
- What is being asserted
- Who is making the assertion
- Supporting evidence (quote or observation)

STEP 2: GROUP CLAIMS
Group related claims by topic or subject.

STEP 3: IDENTIFY PATTERNS
For each group, identify:
- What pattern emerges
- Which claims support this pattern
- Any contradictions within the group

STEP 4: FORMULATE KEY POINTS
For each pattern, write a neutral key point statement.

OUTPUT: {json_schema}
"""
```

**Effort:** Medium (requires prompt rewrites + testing)

---

### GAP 2: Limited Output Verification Loops (HIGH PRIORITY)

**Current State:**
- Single retry attempt on validation failure (`max_retries = 1`)
- Retry uses generic recovery prompt
- No iterative refinement based on specific errors
- No verification against original source after synthesis

**Code:**
```python
# semantic_extraction.py:401-402
retry_count = 0
max_retries = 1
```

**2026 Best Practice:**
Multi-pass verification with error-specific retries:
- Pass 1: Extract
- Pass 2: Validate extraction against source
- Pass 3: If errors, retry with error-specific feedback
- Pass 4: Cross-validate synthesized output

**Impact:**
- Some hallucinations slip through after single retry
- No feedback loop for specific error types
- Validation warnings may not trigger corrective action

**Recommendation:**
Implement tiered retry strategy:
```python
MAX_RETRIES = 2
RETRY_STRATEGIES = {
    "thin_output": SEMANTIC_EXTRACTION_RETRY_PROMPT,
    "missing_quotes": QUOTE_REQUIREMENT_RETRY_PROMPT,
    "ceiling_violations": CONFIDENCE_CEILING_RETRY_PROMPT,
    "broken_provenance": PROVENANCE_RETRY_PROMPT,
}

# semantic_extraction.py enhancement
if should_retry(validation_report) and retry_count < MAX_RETRIES:
    retry_reason = get_retry_reason(validation_report)
    retry_prompt = RETRY_STRATEGIES.get(retry_reason, DEFAULT_RETRY)
    logger.warning(f"Retrying ({retry_reason}): {source_id}")
    retry_count += 1
    continue
```

**Effort:** Medium (requires retry strategy logic + testing)

---

### GAP 3: No External Grounding (RAG/Search) (MEDIUM PRIORITY)

**Current State:**
- Extraction limited to provided source content
- No external fact-checking
- No retrieval of supporting/contradicting evidence
- Cannot verify claims against external knowledge

**2026 Best Practice:**
Hybrid RAG + extraction:
- Extract claims from source
- For HIGH-confidence claims, verify against external knowledge base
- For factual claims (dates, names, events), check against reference DB
- Flag claims that contradict established facts

**Impact:**
- System cannot catch factually incorrect claims
- Limited to errors detectable within source material
- No cross-reference validation for facts

**Recommendation:**
Add optional verification pass for high-stakes claims:
```python
# After extraction, before synthesis
def verify_claims_externally(claims: list[Claim], budget: float) -> list[Claim]:
    """Verify high-confidence factual claims against external sources."""
    for claim in claims:
        if claim.confidence == ConfidenceLevel.HIGH and is_factual(claim):
            verification = check_against_knowledge_base(claim)
            if verification.contradicts:
                claim.confidence = ConfidenceLevel.LOW
                claim.verification_warning = verification.reason
    return claims
```

**Effort:** High (requires integration with search/RAG system)

---

### GAP 4: No Penalty for Confident Errors (MEDIUM PRIORITY)

**Current State:**
- Validation treats all errors equally
- Confident hallucinations not penalized more than uncertain ones
- No differentiation in retry logic based on confidence+error combination

**2026 Best Practice:**
Penalize confident errors more heavily:
- High-confidence error → hard fail (forces retry)
- Low-confidence error → soft warning (acceptable uncertainty)
- Adjust confidence downward for repeated validation failures

**Impact:**
- System may keep high-confidence hallucinations if they pass schema validation
- No incentive structure to prefer uncertainty over confident errors

**Recommendation:**
Add confidence-aware validation severity:
```python
# semantic_validation.py enhancement
def validate_with_confidence_penalty(result: ValidationResult, confidence: str):
    if result.level == ValidationLevel.WARNING and confidence == "high":
        # Upgrade warning to hard fail if claim is high-confidence
        result.level = ValidationLevel.HARD_FAIL
        result.message += " (upgraded due to high confidence)"
    return result
```

**Effort:** Low (validation logic enhancement)

---

### GAP 5: Single-Pass Extraction (No Consistency Checks) (LOW PRIORITY)

**Current State:**
- Each source extracted once
- No multiple extractions to check consistency
- No ensemble approach

**2026 Best Practice:**
Extract same source multiple times (different temperature/seeds), compare outputs:
- High agreement → high confidence
- Low agreement → flag uncertainty

**Impact:**
- Limited to single extraction per source
- Cannot detect model instability
- No confidence calibration based on extraction variance

**Recommendation:**
For critical sources, run dual extraction:
```python
# Two extractions with different temperatures
extraction_a = extract_semantic_structure(gemini, source, temp=0.0)
extraction_b = extract_semantic_structure(gemini, source, temp=0.2)

# Compare key points
agreement = calculate_agreement(extraction_a, extraction_b)
if agreement < 0.7:
    logger.warning(f"Low extraction agreement ({agreement:.2f}) for {source_id}")
    # Downgrade confidence or flag for review
```

**Effort:** Medium (doubles API cost for critical sources)

---

### GAP 6: No LLM-as-Judge Verification (LOW PRIORITY)

**Current State:**
- No secondary LLM validates extraction quality
- No independent fact-checking pass
- Validation is rule-based only

**2026 Best Practice:**
Use secondary LLM to judge extraction quality:
- "Does this key point accurately represent the source?"
- "Are these quotes verbatim?"
- "Is this theme supported by the cited key points?"

**Impact:**
- Cannot catch subtle semantic drift
- Rule-based validation may miss context errors
- No adversarial verification

**Recommendation:**
Add optional LLM-judge validation pass:
```python
def llm_judge_extraction(extraction: SemanticExtractionResult, source: str):
    judge_prompt = f"""
    Original source: {source}

    Extracted key point: "{extraction.key_points[0].statement}"

    Does this key point accurately represent the source?
    Answer: Yes/No + explanation
    """
    judgment = gemini_client.generate(judge_prompt, temp=0.0)
    return parse_judgment(judgment)
```

**Effort:** High (requires additional LLM calls + cost)

---

## Answers to Specific Questions

### Q1: Do we enforce confidence ceilings per analysis mode?

**YES - EXCELLENT IMPLEMENTATION**

Ceilings enforced at 3 layers:
1. Prompt declaration (tells model the ceiling)
2. Auto-downgrade post-extraction (`enforce_confidence_ceiling()`)
3. Validation check (`validate_confidence_ceiling()`)

Enforcement is categorical (HIGH/MEDIUM/LOW) not numeric, preventing gaming.

---

### Q2: Is quote verification comparing against actual source text?

**YES - VERIFIED AGAINST TRANSCRIPT**

`quote_verification.py` uses fuzzy matching (RapidFuzz or difflib) to compare extracted quotes against source transcript. Three-tier scoring:
- Exact match or ≥70% similarity → VERIFIED
- 50-70% → UNCERTAIN (flagged)
- <50% → LIKELY_HALLUCINATED (removed)

Verification happens post-extraction in `verify_quotes_in_extraction()` before downstream stages.

---

### Q3: Do prompts include empty output permission?

**YES - EXPLICIT PERMISSION**

Recovery prompt explicitly states:
```
"If meaning is sparse:
- extract fewer but precise key points
- explicitly surface uncertainty
- identify what cannot be determined

Do NOT pad output."
```

Validation uses soft-fail for thin output (warns but doesn't reject).

---

### Q4: Is there any RAG or external grounding?

**NO - SOURCE-ONLY ANALYSIS**

System extracts only from provided source content. No external knowledge retrieval, no fact-checking against reference databases, no cross-source verification beyond synthesis stage.

**Rationale (per architecture):** Prevents external bias, ensures provenance, avoids introducing unattributed information.

**Gap:** Cannot catch factually incorrect claims that sound plausible within source context.

---

### Q5: Do we use chain-of-thought in prompts?

**NO - DIRECT EXTRACTION**

Prompts request direct JSON output without intermediate reasoning steps. Model jumps from source to extraction without showing work.

**Example:**
```
TASKS:
1. Identify KEY POINTS
2. Identify CLAIMS
3. Identify THEMES

OUTPUT JSON ONLY
```

No "explain your reasoning" or "first list all claims, then group by topic" steps.

---

### Q6: Are there output verification loops?

**LIMITED - SINGLE RETRY**

One retry attempt on validation failure using generic recovery prompt. No:
- Multi-pass verification
- Error-specific retry strategies
- Iterative refinement based on validation results
- Post-synthesis back-check against source

---

### Q7: Do we track provenance (every claim → source)?

**YES - COMPREHENSIVE CHAIN**

Full provenance chain enforced:
- `Quote` → `source_id`
- `Claim` → `source_id` + `supporting_quotes`
- `KeyPoint` → `source_ids` + `supporting_claims`
- `Theme` → `related_key_points` + `sources_supporting`
- `Tension` → `involved_key_points` + `sources_position_a/b`

Validation hard-fails if any link broken. Source Identity Lock Block prevents LLM from guessing source.

---

### Q8: Is there consistency checking across extractions?

**PARTIAL - TENSION DETECTION ONLY**

System detects tensions (contradictions) within and across sources during synthesis. NO:
- Multiple extractions of same source for consistency
- Ensemble extraction with agreement scoring
- Cross-source fact reconciliation

---

## Recommendations Summary

### Immediate Actions (HIGH Priority)

1. **Add Chain-of-Thought to Prompts**
   - Implement layered extraction steps
   - Expose reasoning for key points/themes
   - Test on sample sources
   - **Effort:** 2-3 days

2. **Enhance Retry Strategy**
   - Increase max_retries to 2-3
   - Add error-specific retry prompts
   - Implement retry reason classification
   - **Effort:** 2-3 days

3. **Implement Confidence-Error Penalty**
   - Upgrade high-confidence validation warnings to hard fails
   - Add confidence-aware severity logic
   - **Effort:** 1 day

### Medium-Term (6-8 weeks)

4. **External Grounding (Optional)**
   - Add RAG verification for high-stakes claims
   - Integrate search-based fact-checking
   - **Effort:** 2-3 weeks

5. **Consistency Checking for Critical Sources**
   - Dual extraction for important sources
   - Agreement scoring
   - **Effort:** 1 week

### Low Priority (Future)

6. **LLM-as-Judge Validation**
   - Secondary verification pass
   - Adversarial checking
   - **Effort:** 2-3 weeks

---

## Unresolved Questions

1. **Cost-Benefit of RAG:** Would external grounding improve accuracy enough to justify API costs and complexity? Need metrics on current factual error rate.

2. **Chain-of-Thought Format:** Should CoT be in JSON (structured reasoning) or natural language before JSON output?

3. **Retry Budget:** What's the optimal max_retries before diminishing returns? Need A/B testing.

4. **Confidence Calibration:** Are current confidence levels well-calibrated? Need ground truth comparison on sample extractions.

5. **Multi-Pass Cost:** Is dual extraction worth 2x API cost for critical sources? Need to define "critical source" criteria.

---

## Strengths to Preserve

The following hallucination prevention mechanisms are best-in-class and should NOT be modified:

1. **Confidence Ceiling System** - Categorical limits prevent gaming
2. **Quote Verification** - Fuzzy matching catches paraphrased hallucinations
3. **Source Isolation** - Prevents cross-contamination
4. **Empty Output Permission** - Prevents forced hallucination
5. **Provenance Tracking** - Full chain-of-custody for claims
6. **Mode-Specific Quote Rules** - Prevents inappropriate quoting
7. **Pre-LLM Identity Resolution** - Model cannot guess source metadata

These are stronger than typical 2026 implementations and align with research best practices.

---

## Conclusion

Research Agent's hallucination prevention system is **production-grade** with targeted improvement opportunities. The system excels at:
- Confidence management
- Quote verification
- Source attribution
- Preventing cross-source hallucination

Critical gaps are in reasoning transparency (CoT), verification depth (limited retries), and external grounding (no RAG). Addressing the HIGH-priority gaps would bring the system to state-of-the-art for 2026.

**Overall Grade:** A- (85/100)
- Excellent fundamentals
- Strong architectural discipline
- Needs deeper verification loops and reasoning exposure
