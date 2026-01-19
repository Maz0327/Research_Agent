# Model Selection Decision: Gemini 2.5 Pro vs 3 Pro
**Decision Date:** 2026-01-18
**Decider:** Research Agent (Researcher)
**Status:** RECOMMENDATION READY FOR APPROVAL

---

## Quick Summary

**KEEP Gemini 2.5 Pro** unless synthesis quality degrades.
**OPTIONAL upgrade to Gemini 3 Pro** if reasoning depth becomes critical.
**DO NOT use separate models** for text vs vision.

---

## The Numbers

### Cost per Research Job (3 sources)
- **Gemini 2.5 Pro:** $0.045 per job
- **Gemini 3 Pro:** $0.072 per job (+60%)

### Annual (1000 jobs/month)
- **2.5 Pro:** $540/year
- **3 Pro:** $864/year (+$324)

### Quality
- **Extraction (explicit content):** Tie (both use temp=0.1)
- **Synthesis (themes/tensions):** Gemini 3 Pro wins (+35% reasoning performance)
- **Vision/OCR:** Gemini 2.5 Pro native advantage (no external deps)
- **Structured JSON:** Both excellent (2.5 Pro: 48% faster with schema)

---

## When to Switch to Gemini 3 Pro

Trigger **ONE of these** conditions:

1. **Synthesis quality drops** → Automated QA detects low-confidence themes/tensions
2. **Deep visual reasoning needed** → Analyzing complex charts, diagrams, video
3. **Long-context recall matters** → Analyzing 100+ sources in single context (Gemini 3 +9.9% recall at 1M tokens)

Otherwise: **Stay on 2.5 Pro** (proven, cost-optimal, stable).

---

## Implementation (if needed)

**Upgrade is trivial:**
```python
# Current
model_id = "gemini-2-5-pro"

# Upgraded
model_id = "gemini-3-pro-preview"  # API-compatible, no schema changes needed
```

Optional enhancement for synthesis stage:
```python
# Only for synthesis (optional)
generation_config = {
    "response_schema": SynthesisOutput,
    "response_mime_type": "application/json",
    "thinking_level": "high"  # Deeper reasoning, slower, ~5-10% cost increase
}
```

---

## NOT Recommended: Separate Models

Considered but rejected:
- **Separate OCR model** (RolmOCR, GOT-OCR 2.0) → Requires custom hosting, no API, adds complexity
- **Separate semantic extraction model** → Unified VLM better than specialized (no coordination overhead)
- **GPT-4o for vision + Gemini for text** → Actually more expensive, loses multimodal context

**Verdict:** Unified Gemini model is simplest + cheapest + best for your use case.

---

## Testing Checklist

**Before recommending Gemini 3 Pro:**

- [ ] Run current 948 test suite against Gemini 3 Pro
- [ ] A/B test synthesis output quality (10-20 jobs)
- [ ] Benchmark structured output speed (should be similar or faster)
- [ ] Confirm pricing doesn't change before GA
- [ ] Measure first-token latency impact (if critical for UX)

---

## Unresolved Questions for Owner

1. Is current extraction quality acceptable? (If yes, stay on 2.5 Pro)
2. Do synthesis results need improvement? (If yes, Gemini 3 Pro justified)
3. Will you analyze 100+ sources per job? (If yes, Gemini 3 Pro better recall)
4. Is budget flexible for 60% cost increase? (If no, stay on 2.5 Pro)
5. Should extended thinking be enabled for synthesis? (Need A/B test before deciding)

---

## Next Steps

1. **Owner Review:** Approve staying on Gemini 2.5 Pro OR trigger testing for Gemini 3 Pro
2. **If Gemini 3 Pro test approved:** Run benchmarks in staging environment
3. **Document decision** in DECISIONS.md for future reference

