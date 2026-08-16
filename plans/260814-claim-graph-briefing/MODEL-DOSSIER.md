# Model Dossier — metrics + practitioner evidence per slot

**Date:** 2026-08-15 · Two parallel research agents, ~28 searches, sources at bottom of each section's origin report (full reports in session transcript 08-15).
**Read this with:** `EXECUTION-PLAN.md` §1 (the lineup this dossier amends).

## ⏰ FORCING CLOCKS (drive the schedule)

| Date | Event | Consequence |
|---|---|---|
| **2026-08-31** | `kimi-k2.5` full platform sunset (Moonshot's own docs) | Incumbent judge DIES in ~2 weeks — judge migration is forced, not optional |
| **2026-08-31** | Sonnet 5 intro pricing ($2/$10) ends → $3/$15 | Synthesis stage +50% cost after this date |
| **2026-10-16** | Gemini 2.5 Pro/Flash/Flash-Lite retire | Current extraction/synthesis models die in 8 weeks; migration forced |
| **2027-01-01** | Gemini 3.6 Flash intro pricing doubles → $1.50/$7.50 | Budget at post-intro prices from day one |

## SLOT VERDICTS

### Extraction — ✅ `gemini-3.6-flash` with `thinking_level: "minimal"` (CONFIRMED, sharpened)
- Model is real, GA 07-21. Already superseded by 3.7 Flash (08-13) — **3.6 is still the right pick**: 3.7 REMOVED `minimal` and regressed on hallucination (AA-Omniscience 64.5% vs 55.6% confab-when-wrong); Google published zero grounding data for 3.7 (Flash line now tuned for coding agents).
- The decisive independent finding (406-call eval, evolink.ai): on extraction tasks, accuracy was IDENTICAL across all thinking levels; `minimal` = 73.6% cheaper, 2.8s latency, zero thinking tokens. Thinking tokens bill at output rates and were 75% of the bill at default `medium`. **Set `thinking_level: minimal` for extraction — this is most of the cost story.**
- Grounding: NO Vectara HHEM data exists for any Flash 3.5+ (leaderboard predates them) — Flash-tier faithfulness is independently unmeasured. Mechanical quote-verification downstream covers this.
- **Challenger for the head-to-head: `gemini-3.1-flash-lite`** — 8.2% HHEM (better than 3.1 Pro, best measured 3.x grounding), cheap.
- ⚠️ Gemini 3.x breaking changes: response prefilling REMOVED (HTTP 400 — kill any `{`-forcing code; use `response_schema`), `thinking_budget`→`thinking_level` enum, temperature/top_p dead (sources conflict on 400-vs-ignored — verify empirically), `FunctionResponse` needs `call_id`+`name`.
- Google Flash cadence is ~3 weeks — pin exact IDs, re-validate quarterly. The durable asset is the verification gate, not the model choice.

### Cross-source reasoning — ⚠️ `gemini-3.1-pro` (DEFENSIBLE ONLY WITH THE VERIFICATION GATE)
- Still Google's flagship (3.5 Pro delayed indefinitely — Bloomberg 07-16, 08-13). Callable ID ambiguous: pricing page bills `gemini-3.1-pro-preview`; verify at wiring.
- The July trust verdict RE-CONFIRMED with fresh data: **every Gemini 3.x is worse at faithfulness-to-supplied-docs than every 2.5** (HHEM: 3.1 Pro 10.4% vs 2.5 Pro 7.0% — ~49% more grounding failures). The celebrated 88%→50% improvement is CLOSED-BOOK knowledge calibration — the wrong axis for this pipeline. Its real strengths fit gap analysis: best-in-class abstention, best long-context reasoning (AA-LCR 72.7%).
- **Operating constraints (write into the stage):** working set <200k tokens (2× price above; MRCR collapses 84.9%@128k → 26.3%@1M); single-pass analysis, not iterative (consistent practitioner reports of self-contradiction by ~round 8). No independent data exists on contradiction-detection specifically — unevaluated by anyone outside Google.

### Distillation + Briefing prose — ✅ `claude-sonnet-5` (BEST-EVIDENCED FIT)
- Directly on-point: multi-document synthesis, cross-source contradiction reconciliation, and agree/disagree distinction called out as its strengths vs prior checkpoints; "better-than-Opus quality at a fraction of the cost" for research synthesis.
- Blind writing test: ranked below Opus 4.8/Fable for FICTION because it "takes the safe path, resolves too cleanly" — **the ideal failure direction for a no-embellishment briefing.** Fast (36s vs Opus 75s at same length).
- Structured outputs engine-enforced (schema conformance guaranteed; facts NOT guaranteed — the judge exists for that). Schema limits for `claim_graph.py`: NO recursive schemas, no numeric/string-length constraints (pydantic validates those client-side), `additionalProperties: false` everywhere, incompatible with the Citations feature (irrelevant — we run our own provenance).
- **The documented risk: scope expansion.** Multiple independent reports + Anthropic's own migration guidance: does more than asked despite strict instructions. For a "distill these claims, add NOTHING" stage this is THE failure mode to design against — explicit scope-discipline block in the distillation prompt + the no-new-facts validator + judge audit. Prompt-mitigable, must be tested not assumed.
- Ops: new tokenizer = ~30% more tokens for same text (re-baseline max_tokens + cost); non-default temperature/top_p/top_k = 400.

### Judge — ⚖️ FORCED CONTEST: `gpt-5.6-terra` vs `kimi-k2.6` (K2.5 is dying; neither successor has judge data)
- **K2.5 was a genuinely excellent choice** — independent judge study (arXiv 2606.19544, ~541k judgments): JudgeBench κ 0.720 (rank 4/21), position bias 0.004 (joint-lowest non-Gemini). And it **sunsets 2026-08-31.**
- **Terra** (`gpt-5.6-terra` — note bare `gpt-5.6` routes to Sol): mechanically ideal judge — $2/$12, terse (24M output tokens vs 71M cohort median across evals), guaranteed-schema output, disciplined instruction-following per every reviewer, cross-vendor independence. **Zero independent judge/hallucination data.** Nearest proxy (GPT-5.4): mid-pack JudgeBench, 4th-worst position bias — weak evidence, not forecast.
- **K2.6**: drop-in successor (same API/context; $0.95/$4.00, still ~3x cheaper than Terra), open weights — but its documented gains are coding/agentic; **no judge data either.** Migrating to it means losing the thing that made K2.5 defensible.
- **Resolution = local validation on the fixture** (no external data can settle this): label a claim-faithfulness set from the fixture job; score both judges with the study's protocol — **Cohen's κ, never raw agreement** (raw flatters by ~38pp), A/B+B/A position swaps, test-retest ×3, and never use reproducibility as a proxy for correctness. Winner takes the slot; loser is fallback config.
- **Standing law: the judge must never be a Claude model** while Sonnet 5 does synthesis — self-preference bias is documented (Claude judges favor Claude output; GPT judges show 10–25% self-preference margins). Independence is the point of the slot.

### Escalation — ✅ `claude-opus-5` (unchanged; failure-triggered only)

## AMENDMENTS APPLIED TO EXECUTION-PLAN §1
1. `MODEL_EXTRACTION=gemini-3.6-flash` + `thinking_level: minimal` hardwired for extraction calls; challenger `gemini-3.1-flash-lite` added to P3 head-to-head.
2. `MODEL_JUDGE` contest is now **Terra vs K2.6** (not K2.5), decided at P3 by the κ/position-swap/test-retest protocol; judge-≠-Claude law recorded.
3. 3.1 Pro constraints (<200k, single-pass) written into the reasoning stage requirements.
4. Distillation prompt must carry an explicit scope-discipline block (Sonnet 5 scope-expansion mitigation).
5. Schedule note: **run P3 before 2026-08-31** (K2.5 dies; Sonnet intro pricing ends) — comfortably inside the 5–7 day build.
