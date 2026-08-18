# Opus Kickoff Prompt — paste this verbatim to start the P3 build session

> Maz: open a Claude Code session in `~/Documents/GitHub/Research_Agent` (Opus model), paste everything below the line.

---

You are executing **P3** of the Claim Graph + Research Briefing build for the Research Agent. You are the sole builder — no subagent handoffs for implementation work.

**Current state (true as of 2026-08-18 — do not rediscover it):**
- P0–P2 are DONE and pushed on `feature/product-viability-overhaul` (the working branch).
- The Briefing format is LOCKED as **Decision 025** in root `DECISIONS.md` — validated with the owner on two topics. Do not redesign it.
- The generation-pass layout is ALREADY APPROVED by the owner (recorded in the work order §J). Do not re-propose it.
- Doc 3 (Creator Brief) is retired from the default run by config flag (work order item 16).

**Read these files first, in this order, before touching any code:**
1. `plans/260814-claim-graph-briefing/P3-WORK-ORDER.md` — **your complete scope. Execute from THIS.** Every item, gate, and ops fact you need is in it.
2. `plans/260814-claim-graph-briefing/EXECUTION-PLAN.md` — operating contract (§0) and YOUR known failure modes (§0b — read as law, not advice), model lineup (§1), phase history and what comes after P3.
3. `plans/260814-claim-graph-briefing/spec.md` — the architecture (claim graph schema, projections, voice laws).
4. Root `DECISIONS.md`, Decisions **023, 024, 025** — the owner approvals that amend the constitution.
5. `plans/260814-claim-graph-briefing/MODEL-DOSSIER.md` — evidence behind the §1 lineup and the deadlines.

**Authority:** the repo constitution (`docs/authoritative/INDEX.md` + `.claude/rules/`) remains law — source isolation, confidence ceilings, prompt guardrails, provenance chain, implementation/commit discipline all bind you — except where Decisions 023/024/025 explicitly changed a rule. A conflict those three don't cover: stop and ask me. Never read anything under `docs/_archive_do_not_read/`, `Archive Docs/`, or `Active Docs/`.

**Working discipline (this is where your model family slips — see §0b for the full list):**
- First action of the session: copy the work-order items into `PROGRESS.md` as a checklist. An item is checked ONLY with the demonstrating command's output pasted next to it.
- Re-read the current work-order section before each work block. Re-open a file before editing it — never edit from memory of its contents.
- Run `pre-commit run --all-files` before every commit (codespell is wired in — typos in code, prompts, or docs are defects, not noise).

**Then start at work order §A** and proceed in order (§A → §B → §C → §D → §E; §H/§I items slot where their subsystem is touched). Do not re-plan, do not re-litigate anything marked locked. Stop only at the **[MAZ]** gates and for anything the operating contract reserves for the owner.

Key facts you don't need to rediscover:
- Supabase alive and authenticated via `.env`. Anthropic/Gemini/OpenAI keys in `.env` are LIVE (verified 08-17). Repo Kimi key DEAD — use `~/.openclaw/service-env/kimi-coding.env` against `api.moonshot.ai` (work order §F).
- ⚠️ Shell-env vars SHADOW `.env` (pydantic precedence). If an API inexplicably 400s with "invalid key," check `printenv` before debugging code — this exact bug cost a full pipeline run on 08-17.
- Golden fixtures: job `51c97825-…` (films, original) and job `c5d32615-…` (Hawara labyrinth — fresh-topic fixture with 42k raw words in doc_0; the locked format's mockups were built from it).
- Local pipeline runs need no Redis/Celery: `create_job()` then call `run_research_job()` directly.
- Node 20 via nvm; python3.11; venv at `venv/`.
- ⏰ **Aug 31**: kimi-k2.5 sunset + Sonnet 5 intro pricing ends. ⏰ **Oct 16**: Gemini 2.5 line retires.

Report progress in `PROGRESS.md` at each gate. When a gate needs me, bring a concrete artifact I can react to (a rendered doc, a diff, numbers) — never "does the code look right."
