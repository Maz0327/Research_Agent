# Claim Graph + Briefing — EXECUTION PLAN

**Rewritten 2026-08-18** (pre-rewrite version archived per owner instruction; git history holds all prior states). **PRD:** `spec.md` (the WHAT/WHY — updated same day). **P3 scope:** `P3-WORK-ORDER.md` (the complete item list — execute P3 from there, not from here).
**Repo state:** branch `feature/product-viability-overhaul` (the tip). P0–P2 done and pushed. Supabase alive. Railway live but may build from an older branch — local-first; deploy at the end.

---

## DECISIONS LOCKED (owner)

- **2026-08-15:** Builder = Opus, start to finish, no worker handoffs. V1 = P0–P6; V2 = P7 (Strategist Brief), built after Maz has lived with the Briefing. This project outranks content-pipeline v4 and Truth Lab until usable.
- **2026-08-16 (D-024):** named-story format principles — no cross-references, details woven in, connections first-class, the document never picks the angle. The telling-layer models and these laws survive inside D-025.
- **2026-08-18 (D-025):** the Briefing format is FINAL — 8-section Hybrid Briefing + code-built Source Vault, validated with the owner on two topics (films, Hawara). Canonical artifact = structured JSON; HTML via deterministic code renderer; Drive/Markdown = lossy secondary exports.
- **2026-08-18:** generation-pass layout APPROVED (work order §J): Read locked to `claude-sonnet-5` for V1; 20-source cap per job; no mid-generation human gate — the owner's read of the finished Briefing is the acceptance.
- **2026-08-18:** Doc 3 (Creator Brief) retired from the default run via config flag (work order item 16). Code kept until P8.
- **Standing doctrine (owner, 08-17):** pure code for every step that doesn't need an LLM. Models write content fields; code moves, checks, links, counts, renders.

## 0. OPERATING CONTRACT (read every session)

1. **Don't re-plan.** The spec, this plan, and the work order are decided. Changes require Maz saying so in-session; log them in `DECISIONS.md`.
2. **Autonomy:** minor choices (naming, file placement, equivalent implementations) — pick and note. Ask Maz ONLY at **[MAZ]** markers, scope changes, destructive actions, or money/accounts. Max 2–3 questions at a time.
3. **Verify by behavior.** Each phase has a gate; "done" = the gate passes, demonstrated (test run, rendered doc, curl), never "code looks right."
4. **The prime law: NEVER fabricate.** No mock fallbacks that produce research-shaped output. Missing key/config → throw. Downstream docs may not introduce facts — projections cite claim IDs only.
5. **Voice laws are enforceable, not aspirational:** rendered docs must pass the lint stack. No internal IDs in any document body.
6. **Session hygiene:** work on this branch, commit at coherent stopping points (private GitHub repo = the backup), update `PROGRESS.md` when a phase lands.
7. **Machine facts:** python3.11; Node 20 via nvm; local Redis NOT installed (unit tests need none; local pipeline runs bypass Celery — call `run_research_job()` directly); `.env` is local-dev. ⚠️ **Shell env vars SHADOW `.env`** (pydantic precedence) — on any "invalid key" error, `printenv` first, debug code second.

## 0b. OPUS CAUTIONS — the mistakes you are prone to make (read as seriously as §0)

Documented behaviors of your model family plus failures proven in this project's own sessions. Each has cost real time somewhere. Treat violations as defects.

1. **Scope stays inside the phase.** No refactoring adjacent code, no abstractions added in passing, nothing "parked" touched "while you're in there." The test suite is the fence — if tests unrelated to your item start changing, stop.
2. **Don't build extra verification.** The gates ARE the verification. No additional harnesses or verify-subagents beyond what an item names.
3. **Do the work directly; subagents are rare.** Max 2–3 concurrent, only for genuinely independent sizeable tracks, never for review/verification.
4. **Never have a model re-emit a document to edit it.** Pairs only (OLD>>>x<<<NEW>>>y<<<), code applies, entity-invariant checked. Re-emission drops content — proven three ways on 2026-08-15.
5. **Thinking budgets are a real failure mode.** DeepSeek calls MUST carry `thinking:{type:disabled}`. Sonnet whole-document jobs blow the thinking budget and return empty — per-section, thinking disabled, generous max_tokens.
6. **No silent model substitutions.** Model ID explicit in every call site. Verify IDs live before wiring. A locked ID that 400s is a research task, not a swap-and-move-on.
7. **DONE means demonstrated.** Output in PROGRESS.md or it didn't happen. Docs never claim ahead of what code provably does.
8. **Extend, don't rebuild.** Smallest credible diffs. If a prompt result is wrong, fix the inputs/prompt/dispatch before blaming or swapping the model.
9. **Ask-rate:** minor choices — pick one, note it, keep moving. When you ask, bring a concrete artifact.
10. **Key facts (verified 2026-08-17):** `.env` ANTHROPIC/GEMINI/OPENAI keys LIVE. Repo KIMI key DEAD (401) — judge contest uses `~/.openclaw/service-env/kimi-coding.env` against `https://api.moonshot.ai/v1` (the `.cn` endpoint 401s it). Search keys (Exa/Serper/Supadata) present; Supadata proven live 08-17 (and rate-limits at 5 parallel pulls — work order item 2).
11. **Checklist discipline (anti-forgetting).** First action of the session: copy the work-order items into `PROGRESS.md` as checkboxes. Check an item ONLY with the demonstrating command's output pasted beside it. Re-read the current work-order section before each work block — your family loses held details across long sessions; the file is the memory, not you.
12. **A permanently red test is a finding, not noise — root-cause it before
    labeling it unrelated.** The suite carried one failure across this whole
    build, described in three handoffs as "pre-existing, unrelated". It was
    neither: it was a real defect that made every claim-level quote
    verification meaningless (D-026). A test that has always failed is a
    question nobody has answered yet.
13. **Spelling and small mistakes are defects.** `codespell` runs in pre-commit — run `pre-commit run --all-files` before every commit and fix what it finds. User-facing strings, prompts, and docs get the same care as code; "minor typo" is not a category.
14. **Re-open before editing.** Never edit a file from memory of its contents — read the region first, every time. Stale-memory edits are how content silently vanishes.

## 1. MODEL LINEUP (env-driven; no hardcoded model strings anywhere)

**Forcing clocks: ⏰ Aug 31** (kimi-k2.5 sunset; Sonnet 5 intro pricing ends) · **⏰ Oct 16** (entire Gemini 2.5 line retires — today's hardcoded `gemini-2.5-flash` defaults die; work order kills them). Evidence: `MODEL-DOSSIER.md`.

| Env | Role | Default | Notes |
|---|---|---|---|
| `MODEL_EXTRACTION` | per-source bulk extraction | `gemini-3.6-flash` **+ `thinking_level: "minimal"`** | GA-confirmed. Prefer over 3.7 Flash (removed `minimal`, regressed hallucination). `minimal` = 73.6% cheaper, identical extraction accuracy (independent 406-call eval). Challenger at P3: `gemini-3.1-flash-lite` (best measured 3.x grounding, 8.2% HHEM). ⚠️ Gemini 3.x: NO response prefilling (400s), `thinking_level` enum not `thinking_budget`, temperature dead |
| `MODEL_REASONING` | gap analysis / cross-source | `gemini-3.1-pro` | verify callable ID (`-preview` vs stable). Defensible ONLY because quote-verification wraps it (HHEM 10.4% vs 2.5 Pro's 7.0% — grounding REGRESSED in 3.x). Constraints: working set <200k tokens; single-pass, never iterative (self-contradiction ~round 8) |
| `MODEL_DISTILL` | claim-graph distillation + Briefing prose (incl. the Section-1 Read — LOCKED for V1) | `claude-sonnet-5` | best-evidenced fit (multi-doc synthesis + contradiction reconciliation). Distillation prompt MUST carry a scope-discipline block. Schema: no recursion/numeric/string-length constraints; `additionalProperties: false`; ZERO nullable branches (measured grammar ceiling — split calls if a schema won't compile). Tokenizer +30% — re-baseline max_tokens. Intro $2/$10 ends Aug 31 → $3/$15 |
| `MODEL_JUDGE` | independent audit | **contest: `gpt-5.6-terra` vs `kimi-k2.6`** | decided by local validation: Cohen's κ on a labeled fixture faithfulness set (never raw agreement — flatters ~38pp), A/B+B/A position swaps, test-retest ×3. **LAW: judge is never a Claude model while Claude does synthesis** (self-preference bias). Terra ID is `gpt-5.6-terra` — bare `gpt-5.6` routes to Sol |
| `MODEL_ESCALATION` | retry tier | `claude-opus-5` | triggered on schema-invalid distillation or judge-flagged jobs, never default. NOTE: the SRC-vs-CLM reference error class is fixed by the code normalizer (work order item 11), NOT by escalation — don't burn Opus calls on it |
| Orchestration | — | none | deterministic Celery/direct code; not a model slot |

**VENDOR-PAIRING RULE:** the judge must not share a vendor with extraction OR synthesis. Valid: Gemini-extracts + Terra-judges, or OpenAI-extracts + K2.6-judges. (Synthesis is Claude either way; judge never Claude.)
**Rules: exact IDs, verified live at wiring time, never from memory.**

## 2. PHASES

### ✅ P0 — Stabilize — DONE (08-16)
Working tree committed and pushed.

### ✅ P1 — Claim Graph distillation stage — DONE (08-16, gate-demonstrated)
`backend/models/claim_graph.py` (models + validators, telling-layer models included), `backend/integrations/anthropic_client.py`, `backend/pipeline/stages/distillation_stage.py` (two-pass: provenance → telling; one escalation retry then honest failure). Films fixture distills clean. Hard-won facts live in the work order and D-023/024.

### ✅ P2 — Briefing format — RESOLVED BY D-025 (08-18)
Six renderer iterations ran at the owner's gate (08-16/17), were superseded by the Section-1 pivot, and the format question is now CLOSED: the 8-section Hybrid Briefing + Source Vault of Decision 025, validated on two topics. The old Shape-B renderer (`briefing_formatter.py`) and its lint stack survive as code to extend, not a format to keep. **P2 needs no further work — the format ships as part of P3's Briefing build.**

### ▶ P3 — EXECUTE `P3-WORK-ORDER.md` — ⏰ complete BEFORE Aug 31
The complete scope (items 1–30 + §J pass layout): ingestion fixes → extraction/validation fixes → distillation reference normalizer → the Briefing build (schema, coverage + grounding gates, generation passes, renderer + vault, lint upgrades) → model swap + judge contest (§E) → blind-spot items (§I). Gates inside: extraction three-way judged by verified-quote rate; judge contest by κ/position-swap/test-retest; **[MAZ]** blind-reads old-vs-new lineup Briefings; winners + numbers logged in `DECISIONS.md`; `.env.example` updated.

### P4 — Doc 3 disposition — REDUCED (was: Creator Brief as projection)
Doc 3 is retired from the default run by flag (work order item 16). P4 is now just: verify the flag works, move the description-source-list function to where the publish builder can import it, and confirm nothing else consumes creator-brief output. Full projection rebuild happens only if the product lane revives it (owner decision).

### P5 — Jump-Start — SUPERSEDED
Doc 1 merged into the Briefing (D-023); its job is done by the Info Gaps section, derived from holes + gap analysis by code. No standalone document. Legacy field stays behind `LEGACY_DOCS=1` until P8.

### P6 — Producer Packet, blog, social as projections [M]
Per spec §4: claims × verification for producer; top-N re-voiced for social/blog. Gate: fixture renders + lint + updated tests.

### P7 — Strategist Brief (V2) [M]
Per spec §4 ladder anatomy. `market_context` has existed in the schema since P1. Generative pass constrained to claim IDs. Gate: fixture renders; **[MAZ] reads** — he IS the target user.

### P8 — Cleanup [S]
Retire legacy doc fields (flag off), delete dead paths and the retired Doc 3 code (owner confirms first), update `README.md`/`CLAUDE.md`/`PROGRESS.md`, full test suite green. ⚠️ Last FULL-suite run was at the Shape-B commit (1260 passed, 1 pre-existing unrelated failure); re-run full suite at P3 start before claiming green anywhere.

### POST-P8 OPTIONAL (do not build during V1)
Supadata `/extract` scoring vs our extraction (verified-quote rate as the score); Supadata `/web/scrape` as unified article fetcher.

## 3. SEQUENCE & ESTIMATE

P3 (§A–§C ≈ 1–2 days; §D ≈ 2–3 days; §E ≈ 1 day) → P4 (hours) → P6 → P7 → P8. P6 parallelizable after P3. Total ≈ **5–7 focused days**; the Aug 31 clock binds only P3 §E.

## 4. KNOWN TRAPS (each has already fired once)

- **Shell env shadows `.env`** (pydantic precedence): a stale `GOOGLE_API_KEY` in `~/.zshrc` produced a full run of empty extractions on 08-17 before anyone suspected the environment. `printenv` first.
- Supadata 429s at 5 parallel transcript pulls (work order item 2). Whisper client crashes on SDK objects (item 1) — until fixed, transcript tier-2 is dead.
- Key-point IDs collide per-source (`KP_1` × N) — never treat them as global (item 6 fixes).
- Article fetches can return navigation chrome as content (Perseus 503 did on 08-17) — item 5.
- Railway may build from an older branch; `railway redeploy` fails on no-deployment services — GraphQL `serviceInstanceDeployV2`, order Redis→API→Worker (walkthrough: content-pipeline `SESSION-HANDOFF-2026-08-15.md` §2). Worker Copy is OFF on purpose. Old RAILWAY_TOKEN dead.
- Frontend is NOT on Railway — local `npm run dev` against the live API.
- Google Drive OAuth refresh token in `.env` is dead; `push_docs_to_drive.py` (08-17 scratchpad) is the delivery path once re-minted.

## 5. [MAZ] DECISION POINTS

1. P3: blind read of old-vs-new lineup Briefings; judge winner ratification.
2. P3: his read of the first D-025-format Briefing generated end-to-end (Hawara job `c5d32615` is the natural fixture — it doubles as the live acceptance test feeding his stage-4b workflow).
3. P7 gate: Strategist Brief read.
4. P8: confirm deletion list before any code is removed.
