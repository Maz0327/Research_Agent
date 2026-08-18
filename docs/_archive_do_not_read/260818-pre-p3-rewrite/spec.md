# Claim Graph + Research Briefing — Architecture Spec

**Date:** 2026-08-14 · **Status:** APPROVED direction (Maz), pre-implementation
**Supersedes:** the per-document synthesis model for output docs. Doc 1 (Jump-Start) and Doc 2 (Semantic Brief) merge into the Briefing; all other docs become projections.
**Why:** current outputs are LLM-speak (scaffold vocabulary, ID leakage, theme-marches) and each doc is a separate synthesis pass that can drift. One canonical distillation → every doc derives from it → consistency, provenance, and anti-hallucination by construction.

---

## 1. The core idea

After extraction + synthesis, ONE distillation stage produces the **Claim Graph** (JSON, canonical) and renders the **Research Briefing** (its human-readable form). Every downstream document is a **projection** of the graph: selection + ordering + voice. Downstream stages may not introduce facts — they select claims and re-voice them, citing claim IDs. Depth-on-demand: every claim keeps pointers into the raw source ledger (quotes, timestamps), so any doc and any reader can drill claim → evidence → verbatim source.

Truth Lab parallel (the epistemology this borrows): the atom is the claim-with-receipts; the move is the climb (what sources literally say → the pattern → the researcher's judgment → confidence). One grounded read; everything else derives. Never fabricate; an honest hole beats an invented fact.

## 2. Claim Graph schema (v1)

```jsonc
{
  "graph_version": "1",
  "job_id": "…",
  "topic": "…",
  "thesis": { "text": "one-paragraph verdict", "confidence": "solid|usable|thin", "based_on": ["CLM_…"] },
  "claims": [
    {
      "id": "CLM_…",
      "title": "human headline, a sentence a person would say",   // becomes the unit's bold line
      "what_sources_say": "prose, 2-6 sentences, quotes woven in",
      "pushback": "counters/conflicts, or null",                   // tensions live HERE, not in a section
      "my_read": "researcher judgment, clearly opinionated, or null",
      "say_it_like": "one natural spoken line",
      "confidence": { "grade": 1-5, "reason": "plain sentence" },
      "evidence_status": "all_sources|multi_source|one_source|conflicted",
      "evidence": [ { "source_id": "SRC_…", "quote_ref": "…", "timestamp": "…" } ],
      "story_goods": [ "STG_…" ],          // links to §2.1
      "spine_order": 3,                     // position in the argument
      "tags": ["mechanism","case-study","legacy","money", …]
    }
  ],
  "story_goods": [                          // §2.1 — the script-texture layer
    { "id": "STG_…", "type": "scene|character|number|moment|quote",
      "text": "the concrete, visualizable detail with names/dates/numbers",
      "source_id": "SRC_…", "claim_ids": ["CLM_…"] }
  ],
  "holes": [                                // gaps become first-class negative space
    { "id": "HOLE_…", "attached_to": "CLM_… or thesis", "missing": "what evidence would fill it",
      "hurts_because": "plain sentence", "severity": 1-5, "how_to_fill": "source-type suggestion" }
  ],
  "weakest_ground": { "claim_id": "…", "why": "…" },   // the "if someone challenges you" seed
  "strongest_ground": { "claim_id": "…", "why": "…" },
  "sources_ranked": [ { "source_id": "…", "role": "backbone|confirmation|color|lead", "note": "…" } ]
}
```

**Schema addition for the Strategist Brief (2026-08-14):** optional `market_context` on claims and/or graph level — `{ "who_else_serves_this": "…", "supply_vs_demand": "…", "based_on": ["SRC_…"] }`. Only populated when sources support it; outside knowledge must be flagged as context, never presented as evidence from the input (same law as Truth Lab's Market rung).

**Positioning note (2026-08-14):** the interim workflow (§6) is a preview of the end state, not a rival to content-pipeline v4 — final ranking: v4 fed by the claim graph > interim placeholder > v4 with the old thin research. The grip gate (three blind readers) is pipeline-independent and SHOULD still be run on placeholder-era scripts.

**Rules:** ~12–15 claims per job (multiple key points restating one claim are EVIDENCE for it, not new claims). Tensions and gaps are not sections — a tension is a claim's `pushback`; a gap is a `hole` attached where the missing evidence would sit. All IDs are internal only — never rendered in any document body; rendering uses source names and plain evidence-status language.

### 2.1 Story goods (the scriptwriting layer)

Claims are abstractions; scripts need texture. At distillation, capture the concrete: scenes you can see, named people, dates, numbers, verbatim moments — each linked to claim + source. This is the fix for the known research-depth bottleneck: the Briefing teaches the argument; story goods carry the storytelling raw material. No invented detail: story goods must quote or tightly paraphrase the ledger.

## 3. The Research Briefing (human rendering)

Three altitudes, one file:

1. **Page one — the map.** Thesis + confidence; the claims as one-line bold statements with confidence marks; top 2 holes. Re-readable in 3 minutes.
2. **The body — claim units on the argument spine.** Fixed anatomy per claim, in `spine_order`, with 1–3 connective sentences between units:
   - `### {claim.title}` (bold, human)
   - **What the sources say:** … (evidence-status woven into the prose: "both essays arrive here independently", "one source only — treat as a lead")
   - **The pushback:** … (omit if none)
   - **My read:** … (always fenced as judgment)
   - **How sure:** plain sentence + ▮-scale
   - *Say it like:* "…"
   - Holes render inline: **What's missing here:** …
3. **Closers:** "If someone challenges you" (weakest/strongest ground) · sources ranked by usefulness · appendix pointer.
4. **Appendix = source ledger** (existing): verbatim quotes, timestamps, full receipts.

**Voice laws (all documents):** answer first; plain section names (no "Semantic", "SCQA", "Governing Insight", doc numbers); no internal IDs in body; no stats banners or emoji codes; no "As extracted"; no em-dashes; no "not X but Y" constructions; no rule-of-three stacks; confidence in sentences, not badges. Prose a person would say out loud.

## 4. Projections (each = selection + ordering + voice; cite claim IDs; no new facts)

| Document | Projection definition |
|---|---|
| **Creator Brief** | Hookiest high-confidence claims → hooks; spine → setup/twist; claims + say_it_like → core facts; conflicted claims → disputed section. Keep existing structure that works. |
| **Jump-Start / research directions** | The graph's negative space: all `holes` by severity, every one_source claim, every conflicted claim → directions + verification items. Fully derivable, near-zero generation. |
| **Producer Packet** | Claims × verification status, joined to clips/quotes via evidence refs. Quality gate reads confidence grades. |
| **Script support** | Spine as outline; say_it_like as narration seeds; `story_goods` as the scene/texture layer; holes = "be honest on camera here" beats (trust-is-the-engine). |
| **Blog / Social kit** | Top-N claims by punch, re-voiced per platform; hooks reused. |
| **⭐ NEW: Strategist Brief ("Truth Lab lite")** | Same graph, strategist lens, **explicit ladder anatomy per finding** (decided 2026-08-14 — strategists are the audience that wants to see the climb; deck convention = signal → receipts → opportunity): (1) what's literally there (fact, quotable) → (2) the pattern → (3) THE MARKET (who else serves this; supply vs visible demand — requires new `market_context` field on the graph, see §2 note) → (4) why it exists → (5) the human truth → (6) so-what/whitespace, where every idea carries its BECAUSE pointing at specific evidence (WHY law). Strategist-voiced generative pass constrained to claim IDs. A Research Agent doc type — NOT a fork of the actual Truth Lab product: **no cohort machinery, no learning loop** (confirmed by Maz). May ship as multiple outputs later (belief map / opportunity read); v1 = one document. |

Genuinely generative artifacts (narrative-structure suggestions, platform mechanics) remain LLM calls but must cite claim IDs from the graph.

## 5. Implementation order (incremental, test-gated per step)

1. **Distillation stage** (`pipeline/stages/distillation_stage.py` after synthesis): synthesis output + extractions → Claim Graph JSON. Prompt rewrite: produce connected prose fields (`what_sources_say`, `my_read`), not fragment sentences ("A recurring pattern where…" dies here, upstream).
2. **Briefing renderer** (formatters): graph → Briefing md per §3. Editorial voice pass (async Sonnet, per the Apr-09 engine plan §4 — cross-model rewrite ≈44% quality gain) polishes prose fields.
3. Rewire **Creator Brief** stage to consume the graph (closest to done already; mostly ID-cleanup + label softening).
4. Derive **Jump-Start** from holes (replaces its 35k-char bullet dump).
5. **Producer Packet**, then Doc 5/6/7, then **Strategist Brief** (new).
6. Retire `jump_start_md` / `semantic_brief_md` as primary outputs once the Briefing ships (keep behind a flag during transition).

Validation: Zod/pydantic-validate the graph; existing 960-test suite guards stages; add golden test = distill a fixture job → assert graph invariants (claim count bounds, no orphan evidence refs, every hole attached, no banned vocabulary in rendered output — reuse tic-lint regexes).

## 6. Interim workflow (while content-pipeline v4 is being built)

Run research in Research Agent → export Briefing md → use it as the research brief for script-telling sessions in Claude (v4 "tell it, don't build it" needs a teller who knows the material — that is the Briefing's design goal). This doubles as the live acceptance test of the format: if the Briefing can't support the telling, fix the graph before wiring more projections.

## 7. Open questions

- Claim-count ceiling for very large jobs (20+ sources): shard by sub-topic or raise the cap?
- Confidence grading: mechanical rule (source count × verification status) vs model judgment — lean mechanical with model tie-break.
- Where the editorial Sonnet pass lives (distillation vs render time) — lean render time so the graph stays model-neutral.
- Strategist Brief: which strategist questions are in v1 (belief map, tension, whitespace) vs later (personas, positioning).
