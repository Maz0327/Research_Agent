# Claim Graph + Briefing — EXECUTION PLAN (for Opus to build)

**Date:** 2026-08-15 · **PRD:** `spec.md` in this folder (read it first — this plan is the HOW, the spec is the WHAT/WHY)
**Repo state at write time:** branch `feature/product-viability-overhaul` (the tip — 31 ahead of main), Railway revived (API/Worker/Redis online), Supabase alive, local `.env` valid for Supabase (external API keys unverified since 2026-05-07 rotation).

---

## DECISIONS LOCKED 2026-08-15 (Maz)
- **Builder: Opus, start to finish.** No worker/night-shift handoffs on this build.
- **V1 = P0–P6** (everything creator-side; usable at the P2 gate). **V2 = P7 (Strategist Brief)** — built AFTER Maz has lived with the Briefing. Grounded reason: strategist doc shares only the schema + distillation prompt with V1; both are future-proofed in P1 (full schema incl. `market_context`, prompt captures it from day one), so V2 is purely additive — simultaneous build saves nothing.
- **Priority: this project first**, ahead of content-pipeline v4 and Truth Lab resumption — Maz needs a usable research tool without rushing the other two.
- Model lineup below is DEFAULT pending the model dossier (metrics + practitioner-experience research, session 08-15) — dossier findings may amend defaults before P3.

## 0. OPERATING CONTRACT (read every session)

1. **Don't re-plan.** The spec + this plan are decided. Changes require Maz saying so in-session; log them in `DECISIONS.md`.
2. **Autonomy:** minor choices (naming, file placement, equivalent implementations) — pick and note. Ask Maz ONLY at **[MAZ]** markers, scope changes, destructive actions, or money/accounts. Max 2–3 questions at a time.
3. **Verify by behavior.** Each phase has a gate; "done" = the gate passes, demonstrated (test run, rendered doc, curl), never "code looks right."
4. **The prime law transfers from Truth Lab: NEVER fabricate.** No mock fallbacks that produce research-shaped output. Missing key/config → throw. Downstream docs may not introduce facts — projections cite claim IDs only.
5. **Voice laws are enforceable, not aspirational:** rendered docs must pass the tic-lint (see P2.3). No internal IDs in any document body.
6. **Session hygiene:** work on this branch, commit at coherent stopping points (repo is private on GitHub — that's the backup), update `PROGRESS.md` when a phase lands.
7. Machine facts: python3.11 at `~/.local/bin/python3.11`; Node 20 via nvm; local Redis NOT installed (use Railway stack or Docker for integration tests; unit tests need neither); `.env` is local-dev (REDIS_URL=localhost).


## 0b. OPUS CAUTIONS — the mistakes you are prone to make (read as seriously as §0)

These are documented behaviors of your model family plus failures proven in this project's own
sessions. Each has cost real time somewhere. Treat violations as defects.

1. **Scope stays inside the phase.** You will be tempted to refactor adjacent code, add abstractions,
   improve things you pass by. Don't. Deliver exactly the phase gate. A bug fix doesn't need
   surrounding cleanup. Nothing in P9-spirit ("parked") gets touched "while you're in there."
   The 960-test suite is the fence — if tests unrelated to your phase start changing, stop.
2. **Don't build extra verification.** The gates ARE the verification. No additional harnesses,
   double-check scaffolds, or verify-subagents beyond what a phase names. (Your family over-verifies
   by default; the plan already accounts for it.)
3. **Do the work directly; subagents are rare.** Your family delegates too readily. Max 2–3
   concurrent, only for genuinely independent sizeable tracks, never for review/verification, never
   for work you could finish in a handful of tool calls.
4. **Never have a model re-emit a document to edit it.** Pairs only (OLD>>>x<<<NEW>>>y<<<), code
   applies, entity-invariant checked. Re-emission drops content, leaks editor notes, and logs
   changes it didn't make — proven three ways on 2026-08-15.
5. **Thinking budgets are a real failure mode.** DeepSeek calls MUST carry `thinking:{type:disabled}`.
   Sonnet whole-document jobs blow the thinking budget and return empty — run per-section with
   thinking disabled, generous max_tokens.
6. **No silent model substitutions.** Model ID explicit in every call site and dispatch header.
   Verify IDs live before wiring. If a locked ID 400s, that's a research task, not a swap-and-move-on.
7. **DONE means demonstrated.** A gate passes when the command/behavior ran and its output is in
   PROGRESS.md — never "the code looks right." Docs never claim ahead of what code provably does
   (this exact failure cost a sister project a month of false confidence).
8. **Extend, don't rebuild.** This is a working codebase. Smallest credible diffs. No framework
   swaps, no "cleaner rewrite" of anything currently passing tests. If a draft/prompt result is
   wrong, fix the cargo (inputs, prompt, dispatch) before blaming or swapping the model.
9. **Ask-rate:** minor choices — pick one, note it, keep moving. Stop only at [MAZ] markers, scope
   changes, destructive actions, or money. When you do ask, bring a concrete artifact to react to.
10. **Key facts (verified 2026-08-15):** repo `.env` ANTHROPIC / GEMINI / OPENAI keys are LIVE.
    Repo's KIMI key is DEAD (401) — for the judge contest use the key in
    `~/.openclaw/service-env/kimi-coding.env` against `https://api.moonshot.ai/v1` (the .cn endpoint
    401s that key). Search keys (Exa/Serper/Supadata) present but unverified — first live call tells.

## 1. MODEL LINEUP (default = the LWM content-pipeline stack, adopted 2026-08-15)

All model IDs move to env/config — **no hardcoded model strings anywhere** (today `gemini_client.py` hardcodes `gemini-2.5-flash` defaults; that dies in P3). Forcing function: gemini-2.5-pro retires ~Oct 2026.

**⭐ Amended 2026-08-15 per `MODEL-DOSSIER.md` (read it — it carries the evidence and the forcing clocks).**

| Env | Role | Default | Notes |
|---|---|---|---|
| `MODEL_EXTRACTION` | per-source bulk extraction | `gemini-3.6-flash` **+ `thinking_level: "minimal"`** | CONFIRMED GA (07-21). Prefer over 3.7 Flash (3.7 removed `minimal`, regressed hallucination). `minimal` = 73.6% cheaper, identical extraction accuracy (independent 406-call eval). Challenger at P3: `gemini-3.1-flash-lite` (best measured 3.x grounding, 8.2% HHEM). Budget at post-intro $1.50/$7.50. ⚠️ Gemini 3.x: NO response prefilling (400), `thinking_level` enum not `thinking_budget`, temperature dead |
| `MODEL_REASONING` | gap analysis / cross-source | `gemini-3.1-pro` | verify callable ID (`-preview` vs stable). Defensible ONLY because quote-verification wraps it (HHEM 10.4% vs 2.5 Pro's 7.0% — grounding REGRESSED in 3.x). **Constraints: working set <200k tokens; single-pass, never iterative** (self-contradiction ~round 8) |
| `MODEL_DISTILL` | claim-graph distillation + Briefing prose | `claude-sonnet-5` | best-evidenced fit (multi-doc synthesis + contradiction reconciliation = its documented strengths; "safe path" prose bias = ideal for no-embellishment briefing). **Distillation prompt MUST carry a scope-discipline block** (documented scope-expansion risk). Schema: no recursion/numeric/string-length constraints; `additionalProperties: false`. Tokenizer +30% — re-baseline max_tokens. Intro $2/$10 ends 08-31 → $3/$15 |
| `MODEL_JUDGE` | independent audit | **contest: `gpt-5.6-terra` vs `kimi-k2.6`** | **`kimi-k2.5` SUNSETS 2026-08-31 — migration forced.** K2.5 was rank-4/21 on JudgeBench (κ 0.720, position bias 0.004); NEITHER successor has judge data. P3 decides by local validation: Cohen's κ on a labeled fixture faithfulness set (never raw agreement — flatters ~38pp), A/B+B/A position swaps, test-retest ×3. **LAW: judge must never be a Claude model while Claude does synthesis (self-preference bias).** Terra ID is `gpt-5.6-terra` — bare `gpt-5.6` routes to Sol |
| `MODEL_ESCALATION` | retry tier | `claude-opus-5` | triggered on schema-invalid distillation or judge-flagged jobs, never default |
| Orchestration | — | none | deterministic Celery code; not a model slot in this system |

**Rules: exact IDs, verified live at wiring time, never from memory. ⏰ Run P3 BEFORE 2026-08-31** (K2.5 dies; Sonnet intro pricing ends). Gemini 2.5 line retires 2026-10-16 — the migration is forced regardless.

## 2. PHASES

### P0 — Stabilize [S]
Commit loose working-tree changes (`RA-Convo.md`, plan.md edits, untracked `.github/workflows/ci.yml`, `.pre-commit-config.yaml`) as-is on the branch. Gate: `git status` clean; pushed.

### P1 — Claim Graph distillation stage [M-L]
- `backend/models/claim_graph.py`: pydantic models per spec §2 (claims, story_goods, holes, market_context, weakest/strongest ground, sources_ranked). **HARD REQUIREMENT (V2 future-proofing): the FULL schema ships in V1 — `market_context` included as optional — and the distillation prompt populates it from day one when sources support it (null otherwise). This is what makes V2 purely additive.** Validation: claim count 8–18; every evidence ref resolves to a ledger source; every hole attached; no orphan story_goods.
- `backend/pipeline/stages/distillation_stage.py`: consumes existing synthesis + extractions + gap analysis → produces the graph via `MODEL_DISTILL`. Prompt lives in `backend/pipeline/prompts/` — it must produce connected prose fields (kills "A recurring pattern where…" at the source), fold duplicate key points into evidence, write `my_read` as fenced judgment, `say_it_like` as spoken lines.
- On schema-invalid output: ONE retry via `MODEL_ESCALATION`, then fail honestly (contract §0.4 — no repair-by-invention).
- Wire into worker after synthesis; persist graph to `outputs.claim_graph`.
**Gate:** fixture job (use the stored "films don't look like films" job, id `51c97825…`, as the golden fixture — its raw synthesis/extractions are in Supabase) distills to a schema-valid graph; pytest unit tests for validators green.

### P2 — Briefing renderer [M]
- `backend/pipeline/formatters/briefing_formatter.py`: graph → Briefing md per spec §3 (map page → claim units on spine with inline holes → challenges/sources → appendix pointer). Pure code, no LLM.
- P2.2 optional polish pass (`MODEL_DISTILL`, async): only if fixture output reads stiff — decide by reading, not by default.
- P2.3 **tic-lint** (`backend/pipeline/style_enforcer.py` exists — extend): regex bans in rendered docs: em-dashes in prose, "delve/tapestry/testament/landscape(metaphor)", "not just X, it's Y", rule-of-three stacks, internal IDs (`CLM_|SRC_|KP_|TEN_|GAP_|STG_`) in body text, "As extracted", "Governing Insight", "Semantic". Lint violations fail the render test.
- Persist as `outputs.briefing_md`; API/frontend serve it wherever `semantic_brief_md` is served (keep old fields behind `LEGACY_DOCS=1` during transition).
**Gate:** fixture Briefing renders, passes lint, and **[MAZ] reads it** — his sign-off is the gate. → **Interim workflow unblocked here.**

### P3 — Model swap + head-to-head [M] — ⏰ complete BEFORE 2026-08-31
- Kill hardcoded model defaults; env-drive everything per §1. Verify each ID live; fall back per table.
- **Extraction three-way** on the fixture, judged by OUR quote-verifier (verified-quote rate = the score — this is a Vectara-style faithfulness test on our real workload): `gemini-3.6-flash` (thinking minimal) vs `gemini-3.1-flash-lite` vs `gpt-5.4-mini` (post-2.5-retirement insurance: 5.5% HHEM, better than 2.5 Pro's 7.0%; nano at 3.1% is the cost-floor option if Mini wins).
- **Judge contest: Terra vs `kimi-k2.6`** per §1 protocol (κ, position swaps, test-retest on a labeled fixture faithfulness set).
- **VENDOR-PAIRING RULE:** the judge must not share a vendor with the extraction OR synthesis model. Valid configs: Gemini-extracts + Terra-judges, or OpenAI-extracts + K2.6-judges. (Synthesis is Claude either way; judge is never Claude.)
- Lineup head-to-head: fixture × old vs new lineup → mechanical compare + **[MAZ] blind-reads both Briefings**.
**Gate:** winners + numbers logged in `DECISIONS.md`; `.env.example` updated.

### P4 — Creator Brief as projection [M]
Rewire `creator_brief_stage.py` to consume the graph: hooks from top-curiosity claims, core facts = claims + say_it_like, disputed = conflicted claims. Kill `CLM_/SRC_` IDs and "As extracted" from the rendering; keep the structure that works (hooks, setup/twist, say-it-like).
**Gate:** fixture creator brief diffs clean of banned vocabulary; every fact traces to a claim ID in the data layer; existing creator-brief tests updated + green.

### P5 — Jump-Start derived from holes [S-M]
Replace the 35k-char dump: render research directions from `holes` (by severity) + one_source claims + conflicted claims. Mostly code, minimal LLM.
**Gate:** fixture jump-start ≤ ~1/4 previous length, covers every hole, passes lint.

### P6 — Producer Packet, blog, social as projections [M]
Per spec §4. Claims × verification for producer; top-N re-voiced for social/blog.
**Gate:** fixture renders + lint + updated tests.

### P7 — Strategist Brief (NEW) [M]
Per spec §4 ladder anatomy (fact → pattern → market → why → human truth → so-what+BECAUSE). Needs `market_context` populated at P1 (field exists from the start; populate when sources support it). Generative pass constrained to claim IDs. No cohorts, no learning loop.
**Gate:** fixture strategist brief renders; **[MAZ] reads** — he IS the target user.

### P8 — Cleanup [S]
Retire legacy doc fields (flag off), delete dead synthesis-to-doc paths, update `README.md`/`CLAUDE.md`/`PROGRESS.md`, full test suite green.

### POST-P8 OPTIONAL EXPERIMENTS (do not build during V1)
- **Supadata `/extract` scoring:** run their extraction on the fixture sources, pass output through our quote-verifier, compare verified-quote rate vs our extraction stage. No independent data exists anywhere (verified 08-15) — we'd be first. Curiosity + possible cost lever for the simple-fact tier; NOT a replacement for in-house extraction (architecture reasons stand regardless).
- **Supadata `/web/scrape` as unified article fetcher** — likely better than generic fetching on JS-heavy pages; consolidates fetch on a vendor we already pay.

## 3. SEQUENCE & ESTIMATE

P0 → P1 → P2 (**value unlocked: ~day 2–3**) → P3 → P4 → P5 → P6 → P7 → P8. P5/P6 parallelizable after P3. Total ≈ **5–7 focused days**.

## 4. KNOWN TRAPS

- External API keys unverified since 2026-05-07 — first live extraction call will tell; fix keys, don't debug code first.
- `.env` REDIS_URL is localhost — worker integration tests need local Redis/Docker or run against Railway.
- The 40 key points contain duplicate/inconsistent IDs (`KP_1` appears per-source; `kp1` vs `KP_1`) — the distillation must treat key-point IDs as per-source, never global.
- Railway services may build from an older branch than local tip — check service source config before assuming deployed = latest.
- `railway redeploy` fails when a service has no deployments (post-pause) — use the GraphQL `serviceInstanceDeployV2` mutation (see memory `project_research_agent_state.md` for service IDs).
- Frontend is NOT on Railway — local `npm run dev` against the live API.

## 5. [MAZ] DECISION POINTS (all pre-marked above)

1. P2 gate: Briefing sign-off (his read = the acceptance test).
2. P3: blind read of old-vs-new lineup Briefings; judge winner ratification.
3. P7 gate: Strategist Brief read.
4. Anytime: whether P2.2 polish pass ships (decided by reading fixture output).
