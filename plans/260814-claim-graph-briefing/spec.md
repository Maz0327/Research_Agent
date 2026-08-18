# Claim Graph + Research Briefing — Architecture Spec

**Date:** 2026-08-14 · **Rewritten 2026-08-18** to match Decisions 023/024/025 (pre-rewrite version archived; git history holds all states).
**Status:** claim graph = implemented (P1). Briefing format = LOCKED (D-025). Generation passes = approved (work order §J).
**Supersedes:** the per-document synthesis model. Doc 1 (Jump-Start) and Doc 2 (Semantic Brief) merge into the Briefing; Doc 3 (Creator Brief) is retired from the default run by flag; remaining docs become projections.
**Why:** the old outputs were LLM-speak (scaffold vocabulary, ID leakage, theme-marches) and each doc was a separate synthesis pass that could drift. One canonical distillation → every doc derives from it → consistency, provenance, and anti-hallucination by construction.

---

## 1. The core idea

After extraction + synthesis, ONE distillation stage produces the **Claim Graph** (JSON, canonical provenance layer). The human reading surface is the **Research Briefing** (D-025), whose Section 1 is generated from RAW source text and whose reference sections are checked mechanically against the harvest inventory. Every downstream document is a **projection** of the graph: selection + ordering + voice. Downstream stages may not introduce facts — they select claims and re-voice them, citing claim IDs. Depth-on-demand: every claim keeps pointers into the raw source ledger, so any doc and any reader can drill claim → evidence → verbatim source (the Source Vault is the human face of that bottom layer).

Truth Lab parallel (the epistemology this borrows): the atom is the claim-with-receipts; the move is the climb (what sources literally say → the pattern → the researcher's judgment → confidence). One grounded read; everything else derives. Never fabricate; an honest hole beats an invented fact.

## 2. Claim Graph schema (v1) — implemented in `backend/models/claim_graph.py`

```jsonc
{
  "graph_version": "1",
  "job_id": "…",
  "topic": "…",
  "thesis": { "text": "one-paragraph verdict", "confidence": "solid|usable|thin", "based_on": ["CLM_…"] },
  "claims": [
    {
      "id": "CLM_…",
      "title": "human headline, a sentence a person would say",
      "what_sources_say": "prose, 2-6 sentences, quotes woven in",
      "pushback": "counters/conflicts, or null",                   // tensions live HERE, not in a section
      "my_read": "researcher judgment, clearly opinionated, or null",
      "say_it_like": "one natural spoken line",
      "confidence": { "grade": 1-5, "reason": "plain sentence" },
      "evidence_status": "all_sources|multi_source|one_source|conflicted",
      "evidence": [ { "source_id": "SRC_…", "quote_ref": "…", "timestamp": "…" } ],
      "story_goods": [ "STG_…" ],
      "spine_order": 3,
      "tags": ["mechanism","case-study","legacy","money", …]
    }
  ],
  "story_goods": [
    { "id": "STG_…", "type": "scene|character|number|moment|quote",
      "text": "the concrete, visualizable detail with names/dates/numbers",
      "source_id": "SRC_…", "claim_ids": ["CLM_…"] }
  ],
  "holes": [
    { "id": "HOLE_…", "attached_to": "CLM_… or thesis", "missing": "what evidence would fill it",
      "hurts_because": "plain sentence", "severity": 1-5, "how_to_fill": "source-type suggestion" }
  ],
  "weakest_ground": { "claim_id": "…", "why": "…" },
  "strongest_ground": { "claim_id": "…", "why": "…" },
  "sources_ranked": [ { "source_id": "…", "role": "backbone|confirmation|color|lead", "note": "…" } ]
}
```

**Schema notes (implementation-proven):** optional `market_context` ships in v1 for the Strategist Brief (populated only when sources support it; outside knowledge flagged as context, never as evidence). Structured-outputs grammar ceiling: ZERO nullable branches per compiled schema — optionality = emptiness on wire, `normalize_wire_payload` restores None; distillation is TWO calls because the combined schema doesn't compile. `thesis.based_on` must cite CLM ids — SRC ids there are the known model error; the code reference normalizer (work order item 11) repairs it deterministically.

**Rules:** ~12–15 claims per job (restatements are EVIDENCE, not new claims). Tensions are a claim's `pushback`; gaps are `holes` attached where the missing evidence would sit. Internal IDs never render in any document body.

### 2.1 Story goods (the scriptwriting layer)

Claims are abstractions; scripts need texture. At distillation, capture the concrete: scenes you can see, named people, dates, numbers, verbatim moments — each linked to claim + source. The Briefing's Details & Anecdotes section is the human rendering of this layer. No invented detail: story goods must quote or tightly paraphrase the ledger.

## 3. The Research Briefing (human rendering) — LOCKED as Decision 025

**The full format definition is D-025 in root `DECISIONS.md`; the approved pass layout is work order §J; the visual spec is the mockup pair (`hawara-briefing-mockup.html` + the generated Source Vault). Summary:**

Eight sections: **The Read** (the argument told once, linear, from RAW source text — judgment allowed; the only read-through section) · **The Players** (collapsible cast cards; 2+-section names get cards, one-offs introduced inline) · **The Record** (cited chronology + context dropdowns) · **The Files** (lossless subject-merged layer; mechanical coverage gate vs the harvest inventory) · **Disputed & Uncertain** (holders + code-computed status chips + full for/against dropdowns) · **Details & Anecdotes** (texture bin + context dropdowns) · **Info Gaps** (what the corpus lacks, phrased as go-get instructions; feeds the expand pass) · **Source Trail** (each source's one unique contribution; every SRC id links into the **Source Vault** — full raw texts, generated 100% by code from doc_0).

Canonical artifact = structured JSON; HTML rendered by deterministic code; Drive/Markdown are lossy secondary exports. Two directions of trust, both mechanical: the coverage gate (nothing lost vs harvest) and the grounding gate (no hard atom in the Briefing without a match in doc_0).

**Voice laws (all documents; enforced by the lint stack, never the writer prompt):** answer first; plain section names; no internal IDs in body; no stats banners; no "As extracted"; no em-dashes; no "not X but Y"; no rule-of-three stacks; confidence in sentences, not badges; named citations in prose ("Johanna's video (SRC_4)…"); staging disclosure when a source performs a fact; one-hearing clarity; no cross-references outside Section 1. Prose a person would say out loud.

## 4. Projections (each = selection + ordering + voice; cite claim IDs; no new facts)

| Document | Status | Projection definition |
|---|---|---|
| **Research Briefing** | LOCKED (D-025) | THE reading surface. Absorbs Doc 1 (Jump-Start → Info Gaps) and Doc 2 (Semantic Brief → Files/Disputed). |
| **Creator Brief (Doc 3)** | RETIRED by flag | Violates "brief informs, never performs." Description source list moved to the content-pipeline publish builder (pure code from doc_0). Re-enable only for product experiments. |
| **Producer Packet** | P6 | Claims × verification status, joined to clips/quotes via evidence refs. Quality gate reads confidence grades. |
| **Script support** | via content pipeline | Spine as outline; say_it_like as narration seeds; `story_goods` as texture; holes = "be honest on camera here" beats. Outline artifact carries per-beat fact IDs into doc_0 (content-pipeline CODE-ONLY-LANE item 9). |
| **Blog / Social kit** | P6 | Top-N claims by punch, re-voiced per platform. |
| **Strategist Brief** | P7 (V2) | Ladder anatomy per finding: fact → pattern → market (`market_context`) → why → human truth → so-what+BECAUSE. Strategist-voiced pass constrained to claim IDs. No cohorts, no learning loop. |

Genuinely generative artifacts remain LLM calls but must cite claim IDs from the graph.

## 5. Implementation state & order

1. ✅ Distillation stage (P1) — two-pass, escalation-then-honest-failure, fixture-proven.
2. ▶ **P3 = `P3-WORK-ORDER.md`**: ingestion/validation fixes, harvest stage, reference normalizer, the Briefing build (schema → passes → gates → renderer → vault), lint upgrades, model swap + judge contest, blind-spot items.
3. Then P4 (Doc 3 flag verification) → P6 (projections) → P7 (Strategist) → P8 (cleanup; legacy fields retired).

Validation: pydantic-validate the graph; golden tests distill the fixtures (films `51c97825…`, Hawara `c5d32615…`) and assert graph invariants + lint-clean renders + coverage/grounding gates green.

## 6. Interim workflow (while content-pipeline v4 is being built)

Run research in Research Agent → the Briefing becomes the research brief for script-telling sessions (v4 "tell it, don't build it" needs a teller who knows the material — that is the Briefing's design goal). This doubles as the live acceptance test of the format; the Hawara job is the natural first case since it overlaps the active Hawara episode work. If the Briefing can't support the telling, fix the graph before wiring more projections.

## 7. Resolved & open questions

- ~~Claim-count ceiling for very large jobs~~ → RESOLVED: 20-source cap per job (owner, 08-18); keeps the Read single-call.
- ~~Confidence grading: mechanical vs model~~ → RESOLVED: mechanical (chips computed by code from the graph; owner, 08-18).
- ~~Where the editorial polish pass lives~~ → RESOLVED: no re-emission polish passes anywhere (pairs-only law); voice is enforced by lint + code-applied repair pairs.
- OPEN: Strategist Brief v1 scope (belief map, tension, whitespace) vs later (personas, positioning) — decide at P7.
- OPEN (flagged, §I): vault copyright posture if the product lane wakes; Exa in grounded search.
