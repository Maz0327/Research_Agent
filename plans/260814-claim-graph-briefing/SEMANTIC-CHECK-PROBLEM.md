# Problem brief: the semantic check

Paste this to open a session on the one unsolved verification problem in the
Research Agent. Everything below was measured on 2026-08-20, not estimated.

---

## What the system is

A research pipeline. It ingests sources (YouTube transcripts, articles), extracts
facts from each source in isolation, and assembles a **Research Briefing** — an
8-section document whose Section 1 ("the Read") is written prose and whose
Sections 2–8 are a reference layer built by code from extracted facts.

The governing rule throughout: **code decides, a model advises, a model never
gates.** Every number in the document is counted by code. Models write prose into
slots code already chose.

## The verification stack that already works

Three checks run over the finished Briefing. All three are pure code, so they
have no vendor and no shared blind spots with whichever model wrote the text:

1. **Grounding gate** — every hard atom the document asserts (name, number,
   quoted span) is matched against the raw source text. On the reference corpus
   it checks ~2,650 atoms and flags ~4.
2. **Quote verification** — quotes must match a contiguous span of the source,
   not merely score high on fuzzy similarity. Fuzzy scoring previously passed
   18 of 144 fabricated quotes; span matching passes none.
3. **Coverage gate** — everything harvested must be represented somewhere in the
   document, so silent omission is caught.

**Grounding repair** was added on 2026-08-20: invented atoms in long prose used
to be reported and left. Now one narrow question is asked per atom ("the source
says X, you wrote Y, which is it?") and code splices the answer in. The model
never receives the document back, so it cannot rewrite anything while fixing one
number.

That repair pass shipped with an important lesson attached. Its first working
version **deleted true statements**: the corpus said "King Tut" where the prose
said "Tutankhamun", and the text matcher called it invented. A repair that trusts
a text-matching checker blindly is worse than reporting. The fix was giving the
model the source and a third possible answer — `keep`, meaning the checker was
wrong — with the instruction that `keep` is the safe answer under uncertainty.

## The unsolved problem

The code checks catch facts **the sources do not contain**. They cannot catch a
fact the sources **do** contain that has been misused. Two failure modes:

- **Reversal.** Source: "I do not believe the labyrinth is intact." Document:
  "the labyrinth is intact." Every word is genuinely present.
- **Misattribution.** Source says Herodotus described it. Document says Petrie
  found it. Both men are real and both appear in the corpus.

Also in scope: hedges silently stripped ("may indicate a cavity" → "shows a
cavity") and tense shifts ("planned for 2027" → "happened in 2027").

This check has never been built. It must be **advisory** — it may flag, it may
never edit or delete.

## What was tried, and what happened

Test material throughout: 16 sentences taken from a real generated Read. 8 left
untouched, 8 corrupted by machine (negation flipped, or a name swapped for
another name from the same corpus). Checkers: `gpt-5.6-terra` (the incumbent
judge, scores kappa 0.900 on a separate constructed-corruption benchmark) and
`qwen3.8-max` (kappa 0.800 on the same benchmark, and an independent vendor).

### Attempt 1 — ask "is this sentence supported by the source?"

Retrieve a ~260-word passage per sentence, ask the judge for a verdict.

| | planted errors caught | true sentences kept |
|---|---|---|
| gpt-5.6-terra | 8 / 8 | **2 / 8** |
| qwen3.8-max | 7 / 8 | **2 / 8** |

Detection was perfect. **75% of true sentences were rejected**, which makes it
unusable.

**Diagnosed cause — this is the crux of the problem.** A Read sentence is a
*synthesis*: it takes a fact from source 3, a date from source 9 and a framing
from source 12 and combines them. Show any single passage and "is this
supported?" is correctly answered *no*. The sentence is not wrong. The question
is wrong. Widening the passage from 260 words to 12,000 characters moved true
sentences kept from 1/8 to 4/8 — better, still unusable, and it confirms
retrieval as the cause rather than judgement.

### Attempt 2 — ask "does this contradict?" against pre-extracted facts

Stop asking for support. Ask only whether the sentence contradicts, or
misattributes, relative to the ~630 atomic facts already harvested from the
sources (each tagged with its source ID). This sidesteps retrieval, because the
facts are already atomised. Prompt said to assume anything uncheckable was fine.

| | planted errors caught | true sentences kept |
|---|---|---|
| gpt-5.6-terra | 2 / 8 | 8 / 8 |
| qwen3.8-max | 3 / 8 | 8 / 8 |

False alarms eliminated entirely. **Detection collapsed.** The "assume it's fine"
instruction was too permissive.

### Attempt 3 — calibrate the instruction, and only check factual sentences

Removed "consistent is the default when unsure". Added a filter so only
sentences carrying a checkable claim (a number, or an actor doing something) are
tested — a reversal in a framing sentence contradicts nothing, because no
extracted fact asserts the framing.

| | planted errors caught | true sentences kept | flagged |
|---|---|---|---|
| gpt-5.6-terra | 4 / 8 | 6 / 8 | 2 |
| qwen3.8-max | **6 / 8** | 6 / 8 | 2 |

Two caveats that matter for interpreting this:

- The "true" sentences are model-written prose already known to contain roughly
  7 invented facts per document. **Some of the 2 flags may be genuine catches,
  not false alarms.** They were not hand-checked.
- The sentence filter leaked: framing sentences that happened to mention a year
  were classified as factual, and those account for the persistent misses.

## What the literature says

Standard practice is **decompose into atomic claims, then check each claim
separately** (RAGAS and successors). Most implementations use a small **NLI
entailment model** (e.g. DeBERTa-v3-large-MNLI) rather than a generative judge:
50–200ms per claim, deterministic, local, free.

The attractive property: NLI outputs three labels — entailment, **contradiction**,
neutral. The *neutral* label is exactly the answer that Attempt 1 needed and
could not express. A synthesised sentence with no single supporting passage is
neutral, not unsupported.

Known objections, from the same literature and from reasoning about this corpus:

- **Misattribution is not a logical contradiction.** "Petrie said X" and
  "Herodotus said X" can both be true. NLI will likely return neutral. That is
  half the target failure mode, unaddressed.
- **Contradiction is NLI's weakest label** — it depends on negation and antonymy,
  where small models are brittle. It is also precisely the target.
- **Decomposition still requires a generative model**, so the LLM is moved, not
  removed, and decomposition errors are silent.
- **Scores are uncalibrated** — a threshold giving 90% recall on one dataset
  gives 60% on another. Calibration on this corpus would be required.
- Adds a PyTorch dependency to a pipeline that is currently pure API calls.

## The open questions

1. Is a hybrid right — NLI for reversal, a generative judge for misattribution —
   or is the added machinery worse than one imperfect advisory pass?
2. Which model should do the generative half? Qwen led 6–4 over Terra, but on 8
   items, which is not a decision-grade sample. Terra wins the *general* judge
   benchmark (0.900 vs 0.800); Qwen won this *specific* task. They disagree.
3. Is there a better framing than "contradicts?" that keeps detection high and
   false alarms near zero — the two attempts traded one for the other almost
   perfectly.
4. Can the atomic-fact inventory be used as the premise set directly, avoiding
   both retrieval and decomposition?

## Constraints on any solution

- Advisory only. It may flag; it may never edit or delete.
- Must not flag synthesised-but-true sentences at any material rate. The failure
  that killed Attempt 1 is the one to avoid.
- Deleting or discrediting a true statement is worse than missing a false one.
- Must be measurable against constructed corruptions before adoption, because
  every model choice in this project is decided on numbers rather than argument.
