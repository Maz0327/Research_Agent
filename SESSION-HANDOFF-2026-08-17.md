> ⚠️ **SUPERSEDED 2026-08-18 — background reading only.** The build resumes
> from `plans/260814-claim-graph-briefing/KICKOFF-PROMPT.md` (rewritten,
> current) and executes `plans/260814-claim-graph-briefing/P3-WORK-ORDER.md`.
> The Briefing format is LOCKED as Decision 025 — this file's Section-1
> "propose first" instruction is fulfilled and closed.

# SESSION HANDOFF — 2026-08-16/17 — Claim Graph build, P0–P2, and the Section-1 pivot

**Resume file. Read this before touching anything.** The kickoff for this build
is `plans/260814-claim-graph-briefing/KICKOFF-PROMPT.md`; this doc supersedes
its "start at P0" instruction — P0–P2 are built, and the format was redirected
at the P2 gate. Repo: `~/Documents/GitHub/Research_Agent` (⚠️ NOT
`~/Research_Agent`, which is a stale `main` checkout from March). Branch:
`feature/product-viability-overhaul`. Everything is committed and pushed
through `eb7ddfb` + this handoff. venv at `venv/` (python3.11), deps installed.

---

## ⏸️ WHERE WE STOPPED — pick up EXACTLY here

Maz stepped back from all the pipeline output and asked Claude to just read
the 8 raw sources and summarize them like a person: main points, points of
contention. Claude did, in chat. **Maz: "Okay THIS is a great section 1 for
our brief."** The verbatim sample plus the analysis of what made it different
is saved at
`plans/260814-claim-graph-briefing/artifacts/APPROVED-SECTION-1-SAMPLE.md` —
that file IS the spec for the next build step.

**Maz's explicit constraint: "I don't want anything from the old briefs yet."**
Do NOT resume by polishing BRIEFING-V3 or the existing telling pass. The next
session's first task is to design/build the narrative Section-1 pass that
produces the approved sample's shape, and it was NOT yet green-lit as a build —
propose the approach, then build on his go.

Why the pipeline could not produce that sample (all confirmed with Maz):
1. It's ONE LINEAR ARGUMENT with momentum; the Shape-B self-containment law
   forbids that. Waive self-containment (and the cross-reference ban) INSIDE
   this one section — linearity replaces it.
2. Sources are a CAST with roles, and ranking their contributions ("best
   craft analysis in the pile") is allowed. Pointing at the heat ("the most
   interesting move") is allowed — it is not choosing his story. The earlier
   never-any-judgment rule over-sterilized the document.
3. Contention staged as an actual two-sided fight with holders and evidence.
4. **It must be generated from RAW SOURCE TEXT**, not the claim atoms —
   extraction destroys each source's argumentative shape (concessions,
   who-responds-to-whom), which is what enables the cast/heat/fight moves.
   Raw text for this fixture ≈ 10.5k words; fits in one call.

Likely architecture (proposed, NOT decided): hybrid brief = narrative
Section 1 ("the argument, told once, in full") from raw text + the existing
reference layer (solid-vs-thin, holes/open questions, noticings, linked
sources) underneath. The claim graph stays as the provenance layer for the
other projections (P4–P7) regardless.

---

## STATE OF THE BUILD

### Done, gate-demonstrated
- **P0** (`e1a5fc3`): working tree committed, pushed.
- **P1** (`6b3a2d1`): Claim Graph distillation.
  - `backend/models/claim_graph.py` — models + validators (claim count 8–18,
    refs resolve, holes attach, no orphan story goods, ledger check) + the
    telling-layer models (StorySection/Noticing/Landscape, D-024).
  - `backend/integrations/anthropic_client.py` — first Claude client in repo;
    env-driven `MODEL_DISTILL=claude-sonnet-5`,
    `MODEL_ESCALATION=claude-opus-5` (both verified live 08-15); structured
    outputs; refusal/truncation handling; streams >16K.
  - `backend/pipeline/stages/distillation_stage.py` — two-pass distillation
    (provenance → telling), one escalation retry then honest failure, wired
    into worker after synthesis (non-critical until P8).
  - Fixture job `51c97825-4840-44e8-b93a-593688b31a07` distills clean.
- **P2 built through six format iterations** (gate = Maz's read; superseded by
  the Section-1 pivot before sign-off). Commits: `bcb286b` claim-unit render →
  `fe06415` voice+holes rework → `22da739` Shape B (D-024) → `89761ee` plain
  register ("brief informs, never performs") → `96039db` verbatim specifics →
  `d15e7c1` repair pass → `3457666` content-first → `eb7ddfb` genre format.

### Hard-won technical facts (do not re-litigate)
- **Structured outputs grammar ceiling:** the graph schema compiles ONLY at
  zero nullable branches (measured by API bisect; 40 plain strings OK, 20
  nullable FAIL). Optionality = emptiness on wire; `normalize_wire_payload`
  restores None. Tests lock this. Also why distillation is TWO calls
  (combined schema too large; each half compiles).
- 15-claim graph truncates at 32K output tokens → `DISTILL_MAX_TOKENS=64_000`.
- Confidence ceiling rule (`confidence_ceiling_grade`): best source ceiling
  sets the cap (HIGH→5, MEDIUM→4, LOW→2) and a fully unverified corpus drops
  it one grade — the fixture runs at ceiling 4 because verification_rate=0.
- Owner approval chain: Decision 023 (DECISIONS.md) authorizes this build and
  the rule changes; Decision 024 is the Shape-B format.
- Key-point IDs collide per-source (KP_1 ×6 in fixture) → always
  `source_id:kp_id`. Doc-2 `source_coverage` is lossy for same reason (flagged,
  not fixed).
- **Prompt-only voice enforcement NEVER converges** (measured 3.3–7.1
  source-openers/1000w across identical reruns). Enforcement = short prompt +
  worked example + mechanical lint + ONE repair round of old→new pairs applied
  by code (Maz's TIC-PASS/D-24 doctrine; deletion supported for contentless
  sentences). `backend/pipeline/voice_repair.py`.
- **Fact-harvest finding (the big one):** legacy extraction starved the brief —
  10,465 source words / 85 numbers compressed to 1,165 words / 1 number.
  Harvest pass (1 structured call/source) = 258 dense facts, $0.24, and brief
  density went 1.8→7.2 numbers/1000w. Harvest is still only a scratch script;
  wiring it is P3 work. `artifacts/harvest.json` has the facts.
- **Classical ML verdicts (measured):** embeddings surface restatements, NOT
  connections (key cross-source connection ranked 63/677 by cosine sim) — no
  vector store. 8-word shingle overlap found SRC_7≈SRC_8 at 89% (syndicated
  duplicate silently inflating corroboration) — dup detector approved in
  spirit, NOT yet wired. Maz's SVM/consensus-pipeline doc reviewed: adopt the
  consensus-layer ideas (two axes = support level vs authoritative
  contradiction; misconceptions-as-content section; independence dedup;
  source-quality weighting), reject the classical classifier (it detects
  writing REGISTER, not Maz's STORY/THEORY/REALITY fact classes — conspiracy
  content is deliberately written in reality register).
- **Cold-read validation:** blind subagent scored the enriched brief 8/10
  "could now discuss the topic"; named the two defects (counting chorus,
  evidence-gesturing) that v3 then fixed.
- **Genre benchmark:** Kurzgesagt research docs + CFR Backgrounders. Adopted:
  named attribution ("according to Juan Zarate, a top…"), never counted
  ("two sources agree" banned); evidence-gesture ban ("using different films
  as examples" without naming them = lint error); chorus cap ≤3
  agreement-only sentences/document; linked Sources section. ⚠️ Fixture
  ledger has `creator=None` for all 8 sources → byline capture is a P3
  extraction requirement.

### The lint/repair stack (all in `backend/pipeline/style_enforcer.py` + `voice_repair.py`)
Hard errors: internal IDs; em-dashes; banned vocab (corpus/posits/
corroborates/…); "not just X, it's Y"; cross-references (see above/thread N);
research register; source-openers >3/1000w; evidence-gestures; consensus
narration (positional: agreement-only sentences leading a paragraph or
stacked; plus absolute cap 3/doc). Advisory: rule-of-three. 74 tests green
across claim_graph/briefing_formatter/voice_repair (last run after the genre
changes). ⚠️ HONESTY NOTE: the last FULL-suite run was at the Shape B commit
(1260 passed, 1 pre-existing unrelated failure:
`test_verify_claim_supporting_quotes`, which fails on the P0 commit too);
only the 74-test subset has run since. Re-run the full suite at next session
start before claiming green.

### Key files
- Models: `backend/models/claim_graph.py`
- Stage: `backend/pipeline/stages/distillation_stage.py`
- Prompts: `backend/pipeline/prompts/distillation_prompt.py` (provenance +
  telling passes)
- Renderer: `backend/pipeline/formatters/briefing_formatter.py` (Shape B;
  legacy fallback; source links)
- Lint: `backend/pipeline/style_enforcer.py` · Repair:
  `backend/pipeline/voice_repair.py`
- Config: `MODEL_DISTILL`, `MODEL_ESCALATION`, `LEGACY_DOCS` in
  `backend/config.py`
- Artifacts: `plans/260814-claim-graph-briefing/artifacts/` — approved
  sample, BRIEFING-V3 + ENRICHED, harvest.json, all graphs
  (original/enriched/v2/v3), the fixture inputs `doc_0.json` (source ledger
  WITH full raw text — the Section-1 pass input) and `doc_2.json`, plus the
  rejected MOCKUP-BRIEF and THREE-SHAPES for the format-decision record.
  `artifacts/scripts/` has every experiment script: `fetch_docs.py` (pull
  fixture docs from Supabase), `harvest.py` (the proven fact-harvest system
  prompt), `distill_fixture.py`, `telling_fixture.py`,
  `full_chain_enriched.py`, `retell_v3.py`, `render_briefing.py`,
  `bisect_schema.py` (the grammar-ceiling probe), `embed_test.py` (the
  embeddings verdict). ⚠️ Scripts have hardcoded scratchpad paths from the
  08-16 session — point them at this artifacts dir when reusing. Desktop
  copy: `~/Desktop/BRIEFING-V3.md`.

---

## DECISIONS LOG (this session)
- **D-024** (in DECISIONS.md): Shape B — named-story sections, details woven
  in (the Se7en rule), NO cross-references ever, connections first-class,
  document never picks the angle. *Section 1 pivot amends this: the linearity
  waiver applies inside the narrative opening section only.*
- Brief ≠ script: the brief informs, never performs (memory:
  `feedback_brief_informs_never_performs`). No hooks/`say_it_like` fed to the
  brief writer.
- Rules grow on lint+repair, never on the writer.
- Content first, consensus last: meta earns a trailing clause, never a
  paragraph/section/title.
- Named attribution replaces counted attribution (CFR register).

## OPEN ITEMS (ordered)
1. **Build the Section-1 narrative pass** per APPROVED-SECTION-1-SAMPLE.md —
   propose approach first, get Maz's go. Decide how it composes with the
   reference layer.
2. Fresh-topic test (Maz picks from backlog) — format has been tuned on one
   films example; overfitting risk is real and acknowledged.
3. **P3 before 2026-08-31** (⏰ kimi-k2.5 sunset + Sonnet 5 intro pricing
   ends). Extraction lane now has a concrete shopping list: fact-density
   harvest as a real stage (score models on facts harvested, not just quote
   faithfulness), byline/creator capture, syndication dup detector
   (shingles), raw-text preservation for the Section-1 pass. Plus the judge
   contest (Terra vs kimi-k2.6) and env-driven model sweep per
   EXECUTION-PLAN §1.
4. Flagged, awaiting Maz: constitution `docs/authoritative/INDEX.md` was
   clobbered by `bd6042b` (2026-01-20) — an 18-line ignore file sits where
   the 420-line constitution was; real one recoverable at `bd6042b~1`.
5. P2 gate formally unsigned (pivot superseded it); P2.2 polish pass moot.

## COST NOTES
Full enriched chain ≈ $1.15–1.90/job (harvest $0.24 + provenance ~$0.55 +
telling ~$0.25 + repair ~$0.04–0.08). Sonnet 5 intro pricing ends 08-31.

---

## ADDENDUM — context from the framing discussions (missed in first draft)

**The "what matters per topic" question and how it resolved.** Maz asked
whether the drafter needs per-topic rules (true crime needs exact facts;
Atlantis/conspiracy doesn't) WITHOUT building a category per topic. Arc of the
answer, in order:
- Fact classes STORY/THEORY/REALITY (his locked 07-08 doctrine,
  `reference_three_fact_classes`) are per-claim PRESENTATION rules, not
  grading rules — tell a STORY claim as the source tells it, present THEORY
  as the theory argues it, assert REALITY in your own voice. Relevant to any
  future framing work; REALITY must be the default so the classes never
  become an evidence-dodging escape hatch.
- Terrain (established events vs contested theory vs pure belief) can be
  INFERRED from which class dominates the material — no taxonomy to maintain.
- The angle question resolved as: the brief NEVER asks or locks a mode. It
  always maps, discovers, and teaches; Maz finds/guides the story. (He
  rejected both "committed vs open mode" prompts and any recommendation
  behavior.)
- ⚠️ The repo has an old niche system (`backend/config/niches/`: true_crime,
  mysteries, political, pop_culture, downfalls) — category-per-topic, search
  queries + source floors only. It is the shape Maz rejected; do not wire
  distillation to it.

**External research that named the problem (useful vocabulary, links in the
08-16 chat):**
- Information science: this is "situational relevance" (Saracevic) —
  relevance cannot be judged without the task. Give the system the situation;
  don't add topic categories.
- Stasis theory (rhetoric): what's at issue (fact/definition/quality/policy)
  determines what evidence is relevant — derived from the material, not
  selected from a menu.
- Broadcast craft answers the VFX-quote question: soundbite vs narration —
  a quote earns its place by HOW it's said (powerful/memorable/says it
  better), information goes in the track (your own voice). In true crime the
  same words flip to artifact because the words ARE the fact.
- Intelligence analysis warning (Admiralty code / ICD 203): analysts told to
  rate source reliability and info credibility separately collapse them onto
  the diagonal anyway. If a story-importance dimension is ever added next to
  confidence, make it CATEGORICAL (what job the evidence does), never a
  second 1–5 scale.

**Corpus evidence for genre-specific evidence handling** (Maz's own 19
structural analyses, `~/.openclaw/workspace/content-pipeline/analysis/`,
SYNTHESIS-v2.md): 19/19 scripts attribute contested claims in spoken
vocabulary ("said to", "some believe"); 14/19 never disclose the narrator's
own research process; explainers stamp credibility in one clause (DamiLee:
"this idea actually comes from MIT"), mysteries block-quote for texture (Why
Files/Herodotus), investigative pushes sourcing out of the script entirely
(Johnny Harris: "I'll leave my reading in the source documents"). If the
Section-1 pass ever needs evidence-role vocabulary, derive it from these 19
files, not from intuition.

**Also of record:**
- The Briefing is served in the old Semantic Brief's document slot
  (`backend/pipeline/stages/initialization.py`, `_brief_document()`);
  `LEGACY_DOCS=1` restores old docs; legacy path retires at P8.
- Memory saved this session: `feedback_brief_informs_never_performs` (+
  MEMORY.md index line).
- Interim workflow reminder (spec §6): once the brief passes Maz's gate, it
  becomes the research brief for v4 script-telling sessions — the live
  acceptance test.
