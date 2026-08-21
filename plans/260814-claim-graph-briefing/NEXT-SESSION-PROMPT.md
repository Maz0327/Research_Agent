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
3. Root `DECISIONS.md`, decisions **D-023 through D-036**. These are owner
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

**1. [OWNER GATE] Maz reads the published Briefing.**
https://claude.ai/code/artifact/29e925f6-6dc5-4599-9e8f-a7c33530ba7d
Do not proceed past this without his read, and tell him plainly what that
artifact is: the existing Briefing with the repair round and corpus-balance
header applied, **not a fresh end-to-end run**. It predates chunked harvest, the
harvest quota, the Read budget fix and the judge-window fix.

**2. Decide the writer seat — one number is missing.**
Every writer ties on coverage and grounding, but they differ hugely on *facts
delivered*: sonnet 101, gpt-5.6-luna 89, gemini-3.6-flash 58. Luna gives ~50%
more content at ~7 wrong facts against gemini's ~3. The grounding repair
(D-036) now corrects or cuts wrong facts, which was **not true when that
comparison was run** — so re-test Luna with the repair in place. That is the
missing number, and it likely decides the seat.
Note: the vendor-independence objection to an OpenAI writer is **dead** — the
judge audits extraction, never the writer's prose. See handoff §3.2.

**3. The semantic check — design first, then build.**
File it as a real numbered work-order item before writing code; it has already
evaporated once for lack of one (D-026 deferred it in prose only). Owner wants
the design discussed before building. Standing recommendation: advisory only —
a short "look at these sentences" list appended to the Briefing, nothing edited
or deleted, because a wrongly deleted true statement costs more than a flagged
false one.

**4. The full re-run.** Everything is ready. Expect a materially different
Briefing: more facts per source, two sources read completely for the first time,
and a judge that can actually see the evidence it rules on.

---

## Fix this early — a real defect, one line

**The judge that actually runs is Kimi, not Terra.** `LLM_JUDGE_PRIMARY`
defaults to `"kimi"` and `backend/pipeline/llm_judge.py` tries Kimi first with
OpenAI (carrying `MODEL_JUDGE`) only as fallback. D-028 chose Terra on
measurement and that decision was never wired. It works today **by accident** —
the Kimi key is absent, so every call fails over to Terra. Adding a Kimi key
would silently install the judge that scored kappa 0.550 and failed 38% of its
calls.

---

## Facts you do not need to rediscover

- **Model lineup:** harvest `gpt-5.4-mini` · extraction `gemini-3.6-flash` ·
  distill/prose `gemini-3.6-flash` · escalation `gpt-5.4-mini` · reasoning
  `gpt-5.4-mini` · judge `gpt-5.6-terra` · vision `gemini-2.5-pro` ·
  `MODEL_READ` empty on purpose.
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
