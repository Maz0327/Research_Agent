# Opus Kickoff Prompt — paste this verbatim to start the build session

> Maz: open a Claude Code session in `~/Documents/GitHub/Research_Agent` (Opus model), paste everything below the line.

---

You are building the Claim Graph + Research Briefing architecture for the Research Agent, start to finish. You are the sole builder — no subagent handoffs for implementation work.

**Read these three files first, in this order, before touching any code:**
1. `plans/260814-claim-graph-briefing/EXECUTION-PLAN.md` — your phase plan, operating contract, and gates. Execute from THIS. Its §0 operating contract AND §0b Opus cautions govern the whole build — §0b lists your model family's known failure modes; read it as law, not advice.
2. `plans/260814-claim-graph-briefing/spec.md` — the architecture (claim graph schema, Briefing format, projections, voice laws).
3. `plans/260814-claim-graph-briefing/MODEL-DOSSIER.md` — the model evidence behind the §1 lineup and the two 2026-08-31 deadlines.

**Authority reconciliation — read before P0:** this repo has its own constitution
(`docs/authoritative/INDEX.md` + `.claude/rules/`). It REMAINS law — source isolation, confidence
ceilings, prompt guardrails, provenance chain, implementation/commit discipline all bind you —
EXCEPT where the EXECUTION-PLAN explicitly changes a rule, and those changes are owner-approved in
root `DECISIONS.md` **Decision 023** (document structure: Docs 1/2 → Briefing; model lineup/config;
stale cost guidance). If you find a conflict Decision 023 doesn't cover, stop and ask me — do not
improvise a resolution either direction.

**Then start at P0** (commit the loose working tree) and proceed phase by phase. Do not re-plan, do not re-litigate decisions marked as locked. Stop only at the **[MAZ]** gates and for anything the operating contract reserves for me.

Key context you don't need to rediscover:
- Branch `feature/product-viability-overhaul` is the tip (31 ahead of main). Work there.
- Supabase is alive and authenticated via `.env`.
- The golden fixture is job `51c97825-4840-44e8-b93a-593688b31a07` ("films don't look like films") — its synthesis, extractions, and source ledger are in Supabase.
- Node 20 via nvm; python3.11 at `~/.local/bin/python3.11`; no local Redis (unit tests don't need it; integration via Docker or Railway).
- The Railway deployment (API/Worker/Redis) is live but may build from an older branch — local-first for this build; deploy at the end.
- API keys verified 2026-08-15: Anthropic/Gemini/OpenAI live in `.env`; repo's Kimi key DEAD — use `~/.openclaw/service-env/kimi-coding.env` against `api.moonshot.ai` (details §0b.10).
- ⏰ P3 must complete before 2026-08-31 (kimi-k2.5 sunset + Sonnet 5 intro pricing ends).

Report progress in `PROGRESS.md` at each phase gate. When a gate needs me, ask in plain language with a concrete artifact I can react to (a rendered doc, a diff, numbers) — never "does the code look right."
