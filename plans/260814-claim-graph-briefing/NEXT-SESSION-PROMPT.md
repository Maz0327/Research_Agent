You are picking up the Research Agent build in `~/Documents/GitHub/Research_Agent`
(⚠️ NOT `~/Research_Agent` — that is a stale March checkout). Branch
`feature/product-viability-overhaul`; `main` is fast-forwarded to the same tip.
venv at `venv/`, python3.11. Suite currently: **1692 passed, 3 skipped**.

**Read these three files before touching anything, in this order:**

1. `plans/260814-claim-graph-briefing/SESSION-HANDOFF-2026-08-20.md` — the
   complete previous session. Every test with its numbers, every decision
   including the ones taken NOT to act, two errors that were made and corrected
   mid-session, ten open flags, and the queue below in full detail.
2. `plans/260814-claim-graph-briefing/SEMANTIC-CHECK-PROBLEM.md` — the one
   unsolved problem, with three attempts and their results.
3. Root `DECISIONS.md`, decisions **D-023 through D-038**. These are owner
   approvals that amend the constitution and are not open for re-litigation.

Authority: `docs/authoritative/INDEX.md` + `.claude/rules/` remain law — source
isolation, confidence ceilings, prompt guardrails, provenance, commit
discipline. Never read anything under `docs/_archive_do_not_read/`,
`Archive Docs/`, or `Active Docs/`.

⚠️ **The repo is shared.** ChatGPT and Codex also write into it — `.agents/` and
`.codex/` are theirs. Leave unexplained files alone rather than tidying or
committing them.

---

## The queue, in order

**1. [OWNER GATE] Maz reads the full Briefing.** He has read and approved
Section 1 (the Read) — see handoff §10c. He has NOT read sections 2-8 as
rebuilt. That is the gate.

**2. Finish the 15-sentence labelling task.** Paused deliberately: the sentences
came from a Read that has since been replaced, and labels on a retired document
are wasted. Regenerate the sheet from the CURRENT Read first. One question only
— is this sentence repeating a source, or is it the writer's own point? He has
not read the 42,000 words of sources and cannot answer anything that requires
it. Two earlier drafts failed by asking exactly that.

**3. The semantic check.** Architecture settled and retrieval measured working
(embeddings find the true source fact at rank 1 even when the sentence is
corrupted). The referee is not built. File it as a numbered work-order item
before writing code — it has evaporated once already for lack of one. Full
detail in `SEMANTIC-CHECK-PROBLEM.md` and handoff §8.

**4. A TRUE end-to-end run.** Everything so far used
`scratchpad/full_rerun.py`, which skips extraction, synthesis and gap analysis —
so disputes and info_gaps come out empty. Nothing has gone through
`run_research_job()` since the session's fixes landed.

**5. Resize the sections for the doubled harvest.** The record section now
carries 203 entries and anecdotes 16-48, because they were tuned when the
harvest produced 633 facts and it now produces 1,253. Nothing is broken; the
proportions are wrong.

Optional: re-run DeepSeek as a judge with thinking disabled (its result is void,
not a loss), test `gpt-5.6-luna`/`sol` as judges, §E18 Exa.

## Facts you do not need to rediscover

- **Model lineup:** harvest `gpt-5.4-mini` · extraction `gemini-3.6-flash` ·
  **distill/prose `gpt-5.6-luna`** · escalation `gpt-5.4-mini` · reasoning
  `gpt-5.4-mini` · judge `gpt-5.6-terra` · vision `gemini-2.5-pro` ·
  `MODEL_READ` empty on purpose.
- **The Read is THREE passes** (D-038): write → restructure (PER PARAGRAPH) →
  densify. Every part of that order was learned by getting it wrong — do not
  "simplify" it without reading handoff §10c. The hard word band was removed on
  purpose.
- **Already fixed this session, do not redo:** `LLM_JUDGE_PRIMARY` now defaults
  to `openai` so D-028's choice of Terra is actually wired (it had only been
  running because the Kimi key was absent); `paragraphs_for_fact()` now uses
  `blocks_of()` so transcripts yield a real window instead of the whole source.
- ⚠️ **Ceilings were sized for 633 harvested facts and the harvest now produces
  1,253.** Three broke this session (file sections, the whole-Briefing failure
  path, name introductions) and each had passed its own tests in isolation.
  Expect more. A pipeline of individually-verified stages is not a verified
  pipeline.
- ⚠️ **Quota compliance is per-model AND per-prompt, not a model property.**
  Gemini obeys a length quota in extraction (D-030) and ignores it in the
  harvest (D-034). Never generalise one result to another prompt.
- ⚠️ **All DashScope models (Qwen, DeepSeek, GLM) think by default and it breaks
  structured output.** `enable_thinking: False` via `extra_body` — already wired.
  DeepSeek failed 25 consecutive judge calls before this was found, so **its
  judge result is void, not a loss**; a fair re-run is cheap and undone.
- ⚠️ **Shell env vars shadow `.env`** (pydantic precedence). A stale
  `GOOGLE_API_KEY` cost a full pipeline run on 08-17 and recurred this session.
  If an API 400s with "invalid key", check `printenv` before debugging code.
- ⚠️ **Keys pasted in chat are EXPOSED and need rotating** before they are
  load-bearing: the DashScope/Qwen key, the DeepSeek key, and an
  `ANTHROPIC_API_KEY` that was accidentally echoed to the terminal in full.
- **Railway auto-deploys `main`.** Whatever env vars are set there override code
  defaults — if production still has `MODEL_DISTILL=claude-sonnet-5` it will call
  an Anthropic account with no credits and fail. New vars this session:
  `HARVEST_FACTS_PER_1000`, `HARVEST_CHUNK_OVERLAP`, `MODEL_READ`.
- **The Claude Code bridge is built and deliberately OFF** (D-035): 179s and
  ~$1.25 per call, ~45k-token session tax that does not amortize, for no
  measured quality gain. `MODEL_READ=claude-code:sonnet` switches it on.
- **`pre-commit run --all-files` is unusable** as configured (no secrets
  baseline, 2,227 mypy errors, ruff-format rewrites ~300 files including the
  law-barred archives). Working practice: `codespell` and `ruff check` on
  touched files only.
- Local runs need no Redis/Celery: `create_job()` then call `run_research_job()`.
- Fixtures: films `51c97825`, Hawara `c5d32615` (42k raw words).
- ⏰ **Aug 31** kimi-k2.5 sunset · ⏰ **Oct 16** Gemini 2.5 retires
  (`model_vision` is still on 2.5-pro).

---

## How the owner wants you to work

- **Answer first, plain English.** No jargon he would have to decode. He has
  ADHD; the thing he asked for goes in the first sentence.
- **Ask before starting work while a discussion is open.** Finish the
  conversation, confirm, then act. Mid-discussion tool calls break his train of
  thought — he asked for this explicitly.
- **Never block him watching a background job.** Launch it, leave it, report
  when it lands.
- **Decide on numbers, not argument.** Every model choice in this project was
  settled by measurement. When something cannot be measured cheaply, say so.
- **Redact keys before printing anything.**

⚠️ **The characteristic failure mode here is a number that improves for the
wrong reason.** It happened twice in one session: a malformed schema cleared 25
lint findings by silently disabling the check, and a metric mismatch invented a
model quality advantage that did not exist. Both looked like progress. **When a
comparison decides something, every column must come from the same instrument.**

⚠️ **And no instrument in this repo can tell whether writing is good.** They
measure whether it is dense, grounded and covered — all necessary, none
sufficient. The metrics scored a paragraph the owner called worthless as fine,
and preferred a version that had collapsed into one 1,762-word block. When the
question is quality of prose, put it in front of him and let him read it.
