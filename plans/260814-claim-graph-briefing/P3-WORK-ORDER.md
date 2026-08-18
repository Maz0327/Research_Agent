# P3 WORK ORDER — locked 2026-08-18 (deadline ⏰ 2026-08-31)

The format is locked (Decision 025). This file is the complete P3 scope for the
build session. Read D-025 and SESSION-HANDOFF-2026-08-17.md first. Governing
principle (owner directive, 08-17): **pure code for every step that doesn't
need an LLM; LLM calls only where they add advantage.** Models write content
fields; code moves, checks, links, counts, and renders.

## A. Ingestion-lane fixes (all pure code, all bugs observed live on job c5d32615)

1. **Whisper client fix** — `backend/integrations/whisper_client.py:150-152`
   treats SDK `TranscriptionSegment` objects as dicts (`.get`) → crashes every
   retry. Attribute access.
2. **Supadata stagger** — 5 parallel transcript pulls → 429 rate limit. Add
   stagger/backoff-aware queueing.
3. **Byline capture** — parse creator from meta tags / JSON-LD / oEmbed first;
   LLM fallback only. Every source in both runs has `creator=None`.
4. **Raw-text preservation** — worked in c5d32615; formalize as a guaranteed
   contract (doc_0 `full_text` is the Section-1 input; never optional).
5. **Fetch fallbacks** — Perseus 503 (page chrome saved as content),
   substack thin fetch. Add archive.org/jina fallback + a "content looks like
   navigation chrome" heuristic (code).

## B. Extraction/validation fixes (pure code)

6. **KP-ID namespacing + source attribution** — the "everything is Source 16 /
   100% single-source" bug. Always `source_id:kp_id`; fix supported_by
   tracking so corroboration is measurable again.
7. **Syndication dup detector** — wire the proven 8-word shingle overlap
   (caught SRC_7≈SRC_8 at 89% on the films corpus) so merged "true
   duplicates" are code-decided, never model-decided.
8. **Theme dedup** — near-identical theme statements merged by shingle/string
   similarity (labyrinth Doc 2 had ~5 restatements of "suppression").
9. **Judge counter fix** — `llm_judge` logs "N hallucinations flagged" when N
   items are all VALID; counts items, not flags.
10. **Harvest as a real stage** — the proven fact-harvest pass (1 structured
    call/source; 85→258 dense facts on films corpus) becomes a pipeline stage;
    its output IS the coverage inventory for gate 13.

## C. Distillation fix (code repair, no model retry needed)

11. **Reference normalizer** — distillation failed BOTH models on c5d32615
    with the same validator error: thesis `based_on` cites SRC ids instead of
    CLM ids. Deterministic repair: rewrite `SRC_n` refs to the claims citing
    that source. Same family as `normalize_wire_payload`. Kills the $0.94
    Opus escalation for a solved-by-code error class.

## D. The Briefing build (D-025 format)

12. **JSON schema** for the Briefing: read, players (recurrence-threshold
    cards), record (entries + context), files (subject-merged, status chips),
    disputes (title/holders/chip + for/against bodies), info gaps, source
    trail. Respect the structured-outputs grammar ceiling (zero nullable
    branches; split calls if the schema won't compile).
13. **Coverage gate (code)** — harvest inventory vs. Briefing content;
    mechanical check, model never grades itself. No "omitted as unimportant"
    state.
14. **Generation passes (LLM, content fields only)** — Section 1 from RAW
    doc_0 text (the two approved samples are the spec: films +
    APPROVED-SECTION-1 sample; Hawara read in the mockup); dispute
    both-sides; context blurbs; file prose. Propose pass layout before
    wiring (owner gate).
15. **Renderer (pure code)** — Briefing JSON → HTML (mockup
    `hawara-briefing-mockup.html` is the visual spec) + Source Vault
    generator from doc_0 (script exists from 08-18 session, generalize it).
    Lint additions: players-card threshold (name in 2+ sections without a
    card = error), named-citations-in-prose, staging-disclosure presence
    check where a source performs a fact.
16. **Doc 3 (Creator Brief)** — retired from the default run via config flag
    (owner discussion 08-18: hooks/twist/say-it-like violate "brief informs,
    never performs"; useful remainder is the description source list, which
    moves to the publish builder as code). Keep code until P8; flag can
    re-enable for product experiments.

## E. Existing P3 scope (unchanged from EXECUTION-PLAN)

17. Judge contest (per EXECUTION-PLAN §1) + env-driven model sweep.
18. Exa into grounded search providers (currently Tavily+Serper only) —
    optional, time permitting.

## F. Ops notes

- GOOGLE_API_KEY: repo .env is VALID; the stale shadow was in ~/.zshrc
  (fixed 08-17). pydantic prefers real env vars over .env — watch for this
  class of bug.
- Google Drive OAuth refresh token in .env is DEAD (400). `push_docs_to_drive.py`
  (session scratchpad, 08-17) is the code path once a token is re-minted.
- Local runs need no Redis/Celery: `create_job()` + call `run_research_job()`
  directly (proven on c5d32615).
- **Kimi (judge contest, item 17):** repo `.env` KIMI_API_KEY is DEAD (401).
  Use the key in `~/.openclaw/service-env/kimi-coding.env` against
  `https://api.moonshot.ai/v1` — the `.cn` endpoint rejects that key.
- **Railway:** if services pause again, `railway redeploy` fails on
  no-deployment services — GraphQL `serviceInstanceDeployV2`, order
  Redis→API→Worker; walkthrough + service IDs in
  `content-pipeline/SESSION-HANDOFF-2026-08-15.md` §2. Worker Copy is OFF on
  purpose. Old RAILWAY_TOKEN dead.
- ⏰ Aug 31: kimi-k2.5 sunset + Sonnet 5 intro pricing ends.
- ⏰ **Oct 16: the entire Gemini 2.5 line retires** — hits RA
  extraction/reasoning defaults; the env-driven model sweep (item 17) must
  land successors before then (evidence: MODEL-DOSSIER.md; 3.x regressed on
  grounding — the swap is a decision, not a find-replace).

## G. Considered, not yet scheduled (owner-aware, from the 08-17 IFF research-brief analysis)

- **Ask decomposition + coverage tie-back.** The pipeline's entire
  situation-capture is one typed topic line; the Briefing never reports
  against the original ask. Cheap version: decompose the topic into 2–4
  explicit research questions at intake (LLM), carry them through, and have
  the Briefing account for each — answered / partly / "the sources don't go
  there" (code check against the questions). Catches the failure where a
  brief is excellent on its own terms but quietly dropped half the request.
  Fits naturally as a small block in the Briefing header or Info Gaps.
- **Structured intake** (purpose / how findings will be used) — the fuller
  version of the above; deferred, revisit if the product lane wakes up.

## H. Lint upgrades (from the 08-18 slop-detector survey; owner-approved)

Surveyed: TypeTruth (dead — wraps OpenAI's discontinued classifier),
distil-ai-slop-detector (local 270M binary classifier — rejected: no
positional findings, self-evaluated accuracy), avoid-ai-writing (harvest the
pattern tables + preservation-validator idea; REJECT its architecture —
rules-in-the-rewrite-prompt is the measured-nonconvergent pattern),
ai-writing-detector (harvest the statistical analyzers). Decision: NO
integration/dependency — port ideas into our closed system.

19. **Statistical module** in `style_enforcer.py` (pure code, advisory tier):
    sentence-length variance (the mechanical detector for enumerate-and-march
    — currently invisible to phrase-based lint), lexical diversity,
    passive-voice rate, transition-word density.
20. **Document slop score (0–100)** aggregated from all lint signals — used
    for repair-convergence tracking across rounds and as a regression metric
    in writer-model contests. Never a gate by itself; a trend instrument.
21. **Vocabulary expansion** — curate patterns from avoid-ai-writing's tiered
    tables against OUR voice laws (their casual-register substitutions would
    fight spoken-register rules): copula avoidance ("serves as"→"is"),
    synonym cycling / elegant variation, significance inflation, false
    ranges, false hedging.
22. **Post-repair invariant validator (code)**: quotes, numbers, dates, and
    citation ids byte-identical before/after the repair pass. Repair may fix
    voice; it may never touch a fact. Complements the content-pipeline
    fact-drift gate.
23. **AI-fingerprint pre-flight** (for the publish builder, content-pipeline
    side, noted here for the shared lint lib): unfilled placeholders,
    citation markup tokens, UTM parameters in outbound text.
