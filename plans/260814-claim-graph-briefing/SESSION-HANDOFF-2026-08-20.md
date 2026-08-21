# Session handoff — 2026-08-20 (into 08-21)

**Read this to resume exactly where the session stopped.** Everything here was
measured, not estimated. Where a number is uncertain or a claim is unverified,
it says so.

Branch: `feature/product-viability-overhaul`, all work pushed.
Suite at close: **1692 passed, 3 skipped**.
Decisions added this session: **D-031 through D-036**.

---

## 1. Where the build stands

P3 of the Claim Graph + Research Briefing work order.

| Section | State |
|---|---|
| §A–§D | Complete (previous session) |
| §H | Complete (previous session) |
| **§I** | **Complete this session** — I24, I25, I26, I29, I30 built; I27, I28 already done |
| §E17 judge contest | Complete (D-028, previous session). Re-opened and re-run this session against new candidates — incumbent held |
| §E18 Exa | Not started. Work order marks it optional |
| §J pass 8 repair round | **Wired this session** (was the last unwired piece) |

**The one gate still open: Maz's read of the published Briefing.** Not done,
deliberately — see §7.

---

## 2. The model lineup, and why each seat is filled that way

Live config as of session close:

```
model_harvest      gpt-5.4-mini        D-034
model_extraction   gemini-3.6-flash    D-030 (previous session)
model_distill      gemini-3.6-flash    D-034  ← the Briefing prose / the Read
model_escalation   gpt-5.4-mini        D-034
model_reasoning    gpt-5.4-mini        D-031
model_judge        gpt-5.6-terra       D-028 (previous session)
model_vision       gemini-2.5-pro      unchanged
model_read         (empty)             D-035 — bridge built, deliberately off
```

### Why harvest is gpt-5.4-mini (D-034)

Measured on three sources spanning 284 → 8,924 words, same chunked prompt, same
length-scaled quota:

| | SRC_8 (284w) | SRC_1 (3,124w) | SRC_16 (8,924w) |
|---|---|---|---|
| gemini-3.6-flash | 31.7 /1k | 10.2 /1k | **10.8 /1k** |
| gpt-5.4-mini | 45.8 /1k | 11.2 /1k | **31.3 /1k** |

gemini does not honour a length quota on a long source — it holds ~10 facts per
1,000 words whatever it is handed. On SRC_16 that is **291 facts vs 111**, and
the extra volume is not padding: hard-atom grounding was **0.6% ungrounded for
gpt-5.4-mini vs 1.2% for gemini** (both effectively clean; most flagged atoms
are word-splits on "Synthetic Aperture Radar").

**Important nuance:** this does NOT contradict D-030, where gemini responded
well to a quota. That was the *extraction* prompt at extraction rates. **Quota
compliance is per-model AND per-prompt, not a property of the model.** Do not
generalise either result.

### Why reasoning is gpt-5.4-mini (D-031)

Three runs each of the fixture's gap analysis, hard atoms scored by the span
verifier:

| | gaps | ungrounded | words | time |
|---|---|---|---|---|
| **gpt-5.4-mini** | 7, 7, 7 | 0%, 0%, 0% | 262 | 8s |
| gemini-3.1-pro | 4, 3, 3 | 4.3%, 3.6%, 3.0% | 97 | 15s |
| gemini-3.6-flash | 4, 3, 4 | 11.4%, 13.3%, 13.7% | 99 | 5s |

3.1-pro invented something in **every** run and is retired from the slot.

### Why prose is gemini-3.6-flash — and why that is weakly held

This is the least settled seat. See §5 for the full writer bake-off. Short
version: every writer scores about the same on coverage and grounding, gemini is
the fastest, and it was originally chosen for vendor independence from the judge
— **an argument that turned out to be wrong** (see §3, the D-034 correction).

---

## 3. Two errors I made and corrected — read these, they change conclusions

### 3.1 The false "Anthropic is better" claim (corrected in D-035)

D-034 originally reported the Read's grounding falling "from 0% to ~5%" when
leaving Anthropic, and framed it as a real quality cost.

**That was two different instruments in one column.** The 0% was the *cold
reader's answers about* the Sonnet Read; the ~5% was the substitutes' *own
atoms*. Scored consistently — every Read by its own hard atoms:

| | coverage | ungrounded |
|---|---|---|
| gemini-3.6-flash | 0.785 | 5.8% |
| gpt-5.4-mini | 0.785 | 4.9% |
| claude-code:sonnet (fresh) | 0.785 | 4.0% |
| claude-sonnet-5 (published Read, re-scored) | — | **4.1%** |

**There is no measurable Anthropic advantage on grounding.** D-034's quality
caveat is withdrawn. The error surfaced only because the bridge was built and
its result failed to reproduce the claim.

### 3.2 The vendor-independence argument was pointed at the wrong stage

D-034 kept gemini in the writer seat to avoid "an OpenAI judge auditing
OpenAI-written prose."

**The judge never reads the writer's output.** `_run_llm_judge` audits
*extraction* results and mutates `extraction.claims`. Extraction is gemini. The
Briefing prose is checked by the grounding and coverage gates, which are **code**.

So there is **no vendor-independence constraint on the writer seat**. The
extraction↔judge pairing (gemini ↔ OpenAI) is the one that was doing real work,
and it is already clean.

**Where independence WOULD apply:** the semantic check (§6), because that
reads the writer's prose. If the writer were an OpenAI model and the semantic
checker were Terra, that is genuine self-grading. **This was tested — see §6.**

---

## 4. Everything built this session

### §I items

**I24 corpus balance** — `backend/pipeline/corpus_balance.py`. Domain/date
spread and network overlap by code; per-source stance (believer / skeptic /
neutral / institutional) by one small LLM call. Advisory: a failed stance call
empties the tally and leaves the block standing. Live on the fixture:

```
domains:  youtube.com (5), en.wikipedia.org (2), + 9 others
dates:    2022-2026, 11 of 16 undated
network:  no note (no host carries half, no repeated byline)
stance:   believer 9, skeptic 2, neutral 1-2, institutional 3-4
```

Bug found and fixed: `youtu.be` and `youtube.com` counted as two outlets,
splitting five YouTube sources into three-and-two.

**I25 harvest recall audit** — `backend/pipeline/harvest_audit.py`. Code
stratified-samples raw blocks front/middle/back, a model re-extracts from the
sample only, code fuzzy-matches against the harvest inventory.

```
pooled recall  0.796   |   macro (one vote per source)  0.673
by position (macro):  front 0.673   middle 0.690   back 0.557
truncated:  SRC_3, 36,823 chars vs a 24,000 cap = 34.8% never harvested
```

Three findings, each fixed rather than noted:
1. **Supadata transcripts carry no punctuation and no newlines** — SRC_2 is
   4,019 words with zero full stops. Paragraph AND sentence splitting both
   collapse to one block; a word-window fallback is the only splitter that
   works. Any future paragraph-based tooling hits this same trap.
2. **Pooling hid the finding.** Weighted by fact count, back-of-source recall
   read 0.822 — the *best* position. One vote per source puts it at 0.557, the
   worst. Both are reported; `by_position_macro` is the one to read.
3. SRC_3's back-of-source recall of 0.0 is its truncation, reported as unread
   text rather than as a recall miss.

**I26 staleness pass** — `backend/pipeline/freshness.py`. The Briefing's own
Info Gaps (`go_get`) become the search guidance. Results split newer / older /
**undated** — an undated page is surfaced for a human, never counted as new.

**I29 update mechanism** — `check_updates` iterate mode registered and
dispatched from the worker; `Addendum` model + `_render_addendum` above Section
1 (verified on the real Briefing: addendum at char 11,282, the Read at 11,725);
`backend/pipeline/briefing_diff.py` answers "what changed and what can I skip".

Bug noted, not fixed (out of scope): `PipelineContext` takes `topic`
positionally and the existing `deep_dive` worker branch omits it — it would
raise on the same call.

**I30 read regression** — `backend/pipeline/read_regression.py`. A blind reader
gets Section 1 and nothing else, answers five fixed questions, code scores two
ways: coverage (what the reader retained) and grounding (whether what they say
traces to the corpus). Never an LLM grading comprehension.

⚠️ **This instrument has a known blind spot, discovered late — see §5.**

### D-032 — the harvest chunks, it does not truncate

Owner decision: "coverage gate integrity outranks harvest cost."

```
previously unread:  44,602 chars
  SRC_16  55,779 chars, 57.0% never sent to a model
  SRC_3   36,823 chars, 34.8% never sent
cost delta:  16 calls -> 19,  input chars 214,879 -> 263,981 (+22.9%)
```

The real damage was to **coverage gate 13**, which checked the Briefing against
an inventory built from 43% of a source and reported full coverage of a corpus
it had half-read.

Overlap 1,500 chars; merge dedups with the conservative matcher (the one place
a false match DELETES a fact); identity lock and ceiling rebuilt per chunk.

### D-033 — the pre-rerun sweep

Owner instruction: fix what surfaced AND confirm nothing else needs fixing
before the next full run. D-032 turned out to be one instance of a family. Three
more found:

1. **The harvest asked for a fixed count.** "Extract 10 to 40 facts" produced
   40.1 facts/1k words on short sources and 12.0 on long — a 3.3x decline that
   is entirely an artefact of the instruction. Now a length-scaled quota
   (`HARVEST_FACTS_PER_1000=25-40`).
2. **The Read cut every source at 40,000 chars.** SRC_16 lost 15,779 chars (28%)
   from Section 1 while the call sat far inside its context limit. Now
   `read_budget()` — a total budget (700,000 chars), water-filled, 20k floor.
   On the fixture **nothing is trimmed at all**.
3. **The extraction truncation-retry halved the SOURCE and continued**, so the
   back half was never extracted — under a comment claiming the remainder was
   covered. Truncation is an OUTPUT ceiling problem, so the retry now halves the
   *quota* and keeps the whole source.
4. **The production judge read the first 15,000 chars.** A claim whose evidence
   sat at char 30,000 was marked unsupported on text the judge never saw — in
   the component whose whole purpose is checking the others. Now
   `relevant_source()` scores ~500-word windows against the extraction and marks
   elisions. Verified with evidence at char 44,000: it survives.

Cleared: all other text slicing is display truncation; the only other
fixed-count prompts are the optional Producer packet's bounded lists.
Guard: `backend/tests/test_no_silent_text_loss.py`, 18 tests.

### §J pass 8 — the inline-introduction repair round

`backend/pipeline/intro_repair.py`. **23–25 lint errors → 0.** Pairs applied by
code (D-024): the model writes a four-word gloss, code splices it, the model
never sees the document back.

Five defects found getting there, each of which would have survived review:

1. **A double-wrapped schema.** `_array_of` already calls `_object`; passing a
   built object made the model echo the schema's own scaffolding back as data.
   That read as "no name is a person" and **cleared 25 real lint findings** — a
   number that improved because a check had been switched off.
2. **The gloss writer was shown the wrong passage** — the section's first 600
   chars, so a name appearing 3,000 chars in produced a passage that never
   mentioned them. Six of ten came back empty. Now a window around the name.
3. **The splice was ungrammatical** — `Akers the researcher,,` and
   `Lloyd, the geologist,'s argument`. Now "Name, gloss, rest", with the gloss
   placed in FRONT when every appearance is possessive.
4. **The lint rejected its own valid output** — the appositive pattern matched a
   fixed word list, so "Timothy Akers, one of the Hawara researchers," did not
   count. Now matches the shape.
5. ⚠️ **Names were splitting in two.** "Then Robert Schoch" ranked as a
   different person from "Robert Schoch"; "Researchers Corrado Malanga" from
   "Corrado Malanga". A name in two sections counted as two names in one section
   each and **fell below the card threshold invisibly**. This was distorting the
   cast list, not just the lint. Leading adverbs and job titles now stripped.

Also: the person filter now covers `check_player_cards`, which had been
demanding Players cards for "Historic Mysteries" and "Why Files" — a website and
a section heading.

### D-036 — the grounding gate repairs, it does not only report

`backend/pipeline/grounding_repair.py`, wired after the strip. Invented atoms in
long prose used to be reported and left. Now one narrow question per atom,
answer spliced by code.

⚠️ **The first working version DELETED TRUE STATEMENTS.** The corpus says "the
Tomb of the Pharaoh **King Tut**" where the prose said "Tutankhamun", and spells
"Rosæ" where the prose said "Rosae". The text matcher called both invented and
the repair cut them. **A repair that trusts a text-matching checker blindly is
worse than reporting**, because it converts a false alarm into lost content.

Fixed with a third action: the model gets the source window and may answer
`keep` — the checker was wrong. The prompt makes `keep` the safe answer under
uncertainty. Re-run: Tutankhamun kept twice, Commentator kept, Rosae corrected
to Rosæ, nothing true deleted.

**A `keep` does NOT clear the gate.** The finding stands, annotated. D-026's
rule holds: code decides, a model advises, a model never gates.

---

## 5. The writer bake-off — and the measure that changed the answer

All four candidates, three runs each, same instruments:

| | coverage | ungrounded (median) | time | failures |
|---|---|---|---|---|
| gemini-3.6-flash | 0.750 | 5.2% | 10–13s | 0 |
| gpt-5.4-mini | 0.785 | 4.9% | 20s | 0 |
| deepseek-v4-pro | 0.750 | 6.5% | 34s | 0 |
| qwen3.8-max | 0.750 | **10.3%** | 24–40s | **1 empty Read** |

Qwen is **disqualified**: it invented at roughly twice everyone else's rate AND
one of three runs returned a completely empty Read — the same failure family
that disqualified Kimi.

### ⚠️ Then the owner asked whether the longer outputs carried more value

Measuring fact *density* — distinct names and numbers delivered — changed the
picture entirely:

```
                    words    facts delivered
sonnet              1,102         101
gpt-5.6-luna        1,180          89
qwen3.8-max           873          74
gpt-5.4-mini        1,269          64
deepseek              776          61
gemini-3.6-flash      788          58
```

**gpt-5.4-mini writes the most words and delivers almost the fewest facts** —
5.0 facts per 100 words against gemini's 9.2. Its extra length is genuinely
padding.

**Sonnet delivers ~70% more content than gemini. Luna delivers ~50% more.**

**Why this was missed for most of the session:** the I30 coverage instrument
asks "did a cold reader retain the cast and the disputes?" — a fixed checklist
of about twenty items. Every model covers the checklist, so every model ties.
**It never asked how much the reader actually learned.** That is where the real
spread is.

**This is an open decision.** Luna trades content for accuracy: ~89 facts with
~7 wrong, against gemini's ~58 with ~3 wrong. More right AND more wrong. The
grounding repair (D-036) now fixes or cuts those wrong ones, which weakens the
argument against Luna considerably — but Luna has NOT been re-tested with the
repair pass in place.

---

## 6. The judge contest, round 2, and the DashScope wiring

### New provider wired

DashScope (Alibaba, international) serves **Qwen, DeepSeek and GLM on one
OpenAI-compatible endpoint** — one key covers three vendors.
`QWEN_API_KEY` / `QWEN_BASE_URL`, also stored at
`~/.openclaw/service-env/qwen.env` (mode 600).

⚠️ **The key was pasted in chat — treat as EXPOSED and rotate before it is
load-bearing.** The same note already applies to the DeepSeek key.

⚠️ **All DashScope models think by default and it breaks structured output.**
`enable_thinking: False` must be passed via `extra_body` (the SDK rejects
unknown top-level kwargs). Measured: deepseek-v4-pro produced empty or truncated
JSON on **25 consecutive judge calls** with thinking on, and answered cleanly in
3.2s with it off. Qwen went from 59s to 2s. This is wired into
`OpenAIStructuredClient` for any model matching `deepseek|qwen|glm|zhipu/`.

### Contest results

| | kappa | accuracy | test-retest | position | failures |
|---|---|---|---|---|---|
| gpt-5.6-terra (incumbent) | **0.900** | 95% | 100% | 100% | 0 |
| qwen3.8-max | 0.800 | 90% | 80% | 100% | 0 |
| deepseek-v4-pro | — | — | — | — | **killed mid-run** |

Qwen's plumbing is clean — zero failures, no position bias — but it is a step
down on judgement and changes its mind on one repeat in five.

**DeepSeek's run is void, not a loss.** It was killed after 25 structured-output
failures caused by thinking being on — the fix was found *after* the kill. A
fair re-run is now cheap and has not been done.

**Kimi excluded by owner decision.** Its D-028 loss already ran on the
OpenAI-compatible endpoint, so re-running it changes nothing, and a judge that
fails 38% of calls is unusable whatever its true accuracy.

**GLM dropped by owner decision** before testing.

**Terra keeps the judge seat.**

### Models available and untested

`gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.4-pro` all exist
on the account. Luna was tested as a *writer* only, never as a judge.

---

## 7. The Claude Code bridge — built, measured, DISABLED

`backend/integrations/claude_code_client.py`. `claude -p` as a structured-output
provider, so a slot reading `claude-code:sonnet` runs on the **subscription**
rather than the API. Works end to end on the real 42,000-word corpus.

**Owner decision: not practical, do not use.**

```
one Read call:  179s and ~$1.25   vs 14-20s and cents for the alternatives
session tax:    ~45,000 tokens per invocation, measured across 3 consecutive
                calls — it does NOT amortize (14,636 / 14,633 / 14,634 created)
```

Two traps recorded:
- **`ANTHROPIC_API_KEY` in the environment kills the call.** The CLI prefers an
  API key over the subscription login. The subprocess env is now scrubbed.
- **`--bare` cannot be used** — it would cut the session tax but forces
  API-key auth and never reads the subscription.

`MODEL_READ` is now **empty** in `.env`; the Read uses `MODEL_DISTILL`. Setting
it to `claude-code:sonnet` switches it back on for that one call, with automatic
fallback if the CLI cannot be reached.

---

## 8. The unsolved problem — the semantic check

**Full brief: `plans/260814-claim-graph-briefing/SEMANTIC-CHECK-PROBLEM.md`.**
Read that file; this is the summary.

Code catches facts the sources do NOT contain. It cannot catch a fact the
sources DO contain that has been misused — reversed meaning, wrong attribution,
stripped hedges, shifted tense.

D-026 deferred this as "an advisory pass" and **it was never given a work-order
item** — it existed only as prose in a decision record. That is why it kept
evaporating.

Three attempts, 16 sentences from a real Read (8 corrupted, 8 untouched):

| approach | planted errors caught | true sentences kept |
|---|---|---|
| 1. "is this supported?" vs retrieved passage | Terra 8/8, Qwen 7/8 | **2/8** |
| 2. "does this contradict?" vs harvest facts, permissive prompt | Terra 2/8, Qwen 3/8 | 8/8 |
| 3. calibrated prompt + factual-sentence filter | Terra 4/8, **Qwen 6/8** | 6/8 |

**The crux, diagnosed:** a Read sentence is a *synthesis* across several
sources. Ask "is this supported by this passage?" and the honest answer is
always no. The sentence is not wrong; the question is. Widening the passage from
260 words to 12,000 chars moved true-sentences-kept from 1/8 to 4/8 — confirming
retrieval, not judgement, as the cause.

**Two caveats on attempt 3, both important:**
- The "true" sentences are model-written prose known to carry ~7 invented facts.
  **Some of the 2 flags may be genuine catches, not false alarms.** Not
  hand-checked.
- The factual-sentence filter leaked: framing sentences mentioning a year were
  classified as factual, and those account for the persistent misses.

**Correlated-blindness test (this answered the independence question):** Terra
caught **8/8** errors planted in Luna's own prose, against independent Qwen's
7/8. **No same-vendor blindness is visible.** Terra can check OpenAI-written
prose.

**What the literature says** (searched this session): the standard is decompose
into atomic claims, then check each with a small **NLI entailment model**
(DeBERTa-v3-large-MNLI), 50–200ms per claim, local, deterministic, free. The
attraction is that NLI's **neutral** label is exactly the answer attempt 1
needed and could not express.

**Objections to NLI, which is why it was not adopted on the spot:**
- **Misattribution is not a logical contradiction** — "Petrie said X" and
  "Herodotus said X" can both be true. NLI likely returns neutral. That is half
  the target, unaddressed.
- Contradiction is NLI's weakest label, and it is our target.
- Decomposition still needs a generative model — the LLM moves, it does not go.
- Scores are uncalibrated; thresholds do not transfer between corpora.
- Adds PyTorch to a pipeline that is currently pure API calls.

**Where it stopped:** the owner wanted to discuss before building. The standing
recommendation is advisory-only over factual sentences, producing a short
"look at these sentences" list — 3–5 flagged sentences, each with the fact it
appears to clash with and one line of why, appended to the Briefing. **Nothing
edited, nothing deleted.**

Open: whether a hybrid (NLI for reversal, LLM for attribution) is worth the
machinery, and which model does the generative half — Qwen led 6–4 over Terra
but on 8 items, which is not decision-grade.

---

## 9. Decisions taken NOT to do something, and why

- **Do not use the Claude Code bridge.** 179s and ~$1.25 per call for no
  measured gain (§7).
- **Do not act on the corpus skew.** The fixture reads 9 believer to 2 skeptic
  with 11 of 16 undated. Owner decision: that is a real property of this topic's
  source landscape, the I24 header block is the designed behaviour, and
  skeptic-hunting belongs to the expand pass. **Recorded so nobody "fixes" it.**
- **Do not re-test Kimi** (owner).
- **Do not test GLM** (owner).
- **Do not raise `HARVEST_MAX_CHARS` instead of chunking** — D-029 measured that
  a bigger window does not buy more output from a model returning a roughly
  fixed count; the source would be read and then summarized.
- **Do not swap the judge.** Neither Qwen nor DeepSeek beat Terra.
- **Do not fix the `deep_dive` PipelineContext bug** — real, but outside this
  work order. Noted in a comment beside the new `check_updates` branch.

---

## 10. Resume here — the open queue

1. **[MAZ GATE] Read the published Briefing.**
   https://claude.ai/code/artifact/29e925f6-6dc5-4599-9e8f-a7c33530ba7d
   (Vault: https://claude.ai/code/artifact/43df2b24-66c8-4d33-900c-5f66bfc8d0a0)
   ⚠️ That artifact is the existing Briefing with repairs and the balance header
   applied — **NOT a fresh end-to-end run.** It predates chunked harvest, the
   quota fix, the Read budget fix and the judge-window fix, so the two truncated
   sources still contribute what the old harvest gave them.

2. **Decide the writer seat.** gemini-3.6-flash (58 facts, 3 wrong, fast) vs
   gpt-5.6-luna (89 facts, 7 wrong). The independence objection is dead (§3.2).
   The grounding repair now fixes wrong facts, which was not true when the
   objection was raised. **Luna has not been re-tested with the repair in place
   — that is the missing number.**

3. **The semantic check.** Discuss the design (§8), then build. File it as a
   real work-order item first — it has evaporated once already for lack of one.

4. **The full re-run.** Everything is ready. It will produce a materially
   different Briefing: more facts per source, two sources read completely for
   the first time, a judge that can see the evidence it rules on.

5. Optional: re-run DeepSeek as judge with thinking off (its result is void, not
   a loss); test `gpt-5.6-luna` / `sol` as judges; §E18 Exa.

**Deadlines:** ⏰ Aug 31 (kimi-k2.5 sunset, Sonnet 5 intro pricing ends)
· ⏰ Oct 16 (Gemini 2.5 line retires — `model_vision` is still on 2.5-pro).

---

## 11. Operating notes learned this session

- **Do not block the user watching a background job.** Launch it, leave it,
  report when it lands. Sitting in a foreground `sleep` loop is what a
  background task is for.
- **Ask before starting work when a discussion is in progress.** The owner asked
  for this explicitly: finish the conversation, confirm, then act.
- **Plain English in replies.** Technical is fine; jargon like "overruns the
  word band" is not.
- ⚠️ **Redact keys before printing.** An `ANTHROPIC_API_KEY` was echoed in full
  to the terminal by a `grep` whose redaction pattern missed. It is in scrollback
  and should be rotated.
- **A number that improves for the wrong reason is the main hazard here.** It
  happened twice: a double-wrapped schema cleared 25 lint findings by disabling
  the check, and a metric mismatch invented an Anthropic quality advantage that
  did not exist. **When a comparison decides something, every column must come
  from the same instrument.**
