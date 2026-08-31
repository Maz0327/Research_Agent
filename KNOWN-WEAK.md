# Known weaknesses — accepted, not scheduled

Written 2026-08-31, after a two-agent design audit (23 findings, record at
`scratchpad/audit/AUDIT-2026-08-31.md`) and an independent review of the fix
plan. The decision: verification moves to a final fact-check pass over the
finished SCRIPT (claims → grounded web search → URL + supporting quote →
human rules). Everything below is superseded by that pass or does not put a
wrong sentence in a video. It is listed so nobody rediscovers it as a
surprise, and none of it is scheduled work.

## Superseded by the final script check
These gates become advisory once verification happens at the script:
- Grounding gate matches names by substring ("Ted" grounds via "reported");
  invented names can pass. `briefing_gates.py`
- Quote check is bag-of-words at 0.85; fabricated quotes built from corpus
  vocabulary pass. Any future quote verification must be verbatim/ordered
  shingles, never a port of `_quote_is_present`.
- Coverage gate passes a fact when its atoms appear anywhere in the document,
  in unrelated passages. Its "0 findings" is a weak instrument reporting.
- Intro repair splices model-written glosses after the final grounding gate.
- `evidence_chip` labels a zero-source claim "single source".

## Advisory-quality issues, left as-is
- Lint / below-the-line / intro repair still rank names with the retired
  regex heuristic; the enforcement name-set should someday come from the cast
  pass. Until then the lint cannot demand a card for a briefing's subject.
- `corpus_balance` runs without url/skim_summary on the briefing path
  (domain spread empty) and its stance vocabulary is fringe-topic-shaped.
- `cap_subjects` folds overflow subjects into a near-arbitrary file.
- `run_file_pass` lets the model rewrite the subject title the map chose.
- Grounding repair judges from a 2,000-char window over the whole corpus.
- `audit_harvest_recall` has zero callers; treat as archived.
- Residual in disputes/synthesis: corroboration LANGUAGE ("several sources
  agree") is not verified by the final check — it verifies claims, not counts.

## Writing-side (pipeline v4 docs, not this repo)
- RUNBOOK ordering laws vs. day-one practice: with research nearly free, the
  packaging kill gate should protect the owner's 4b read, not research
  budget. Doc change, decided but not written.
- Stage 4b has no STAGE-LEDGER row; contested-claims ballot has no artifact.
- RULES #27 references thread rows nothing produces; stage-3 contract
  describes the manual flow the RA replaced.
- Blind readers (the validated instrument) have no protocol file; worth 30
  minutes someday.
- On each new episode: copy the canonical briefing JSON into the episode
  folder at stage 4b so renders and JSON cannot drift apart.

## Fixed, for the record (2026-08-31)
Cast read from the finished brief with three sections; organisations gated;
strip no longer doubles card identities; disputes only stage two-sided fights
with named holders and a model opposition check; decades parse; the Record
collapses restatements and settles outvoted numbers; source voice stripped at
the inventory; polarity veto in `says_the_same_thing` (negation ≠ restatement,
protects harvest dedup and synthesis corroboration); shared-surname material
ties go to the most-mentioned holder (the "James Packer" phantom); harvest
fails loudly on zero facts instead of shipping an empty briefing.
