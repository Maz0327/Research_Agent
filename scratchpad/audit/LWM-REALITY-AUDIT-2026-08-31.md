# LOST WITH MAZ — FULL REALITY AUDIT
**Date:** 2026-08-31 · **Method:** direct inspection of files, git state, runtime processes, and artifact history on this Mac. Nothing was modified. Where I could not verify, I say so in §16.
**Written for a reader with zero prior context.** All paths are absolute or relative to `~` = `/Users/mazbot`.

---

## 1. EXECUTIVE VERDICT

**The system is mostly good but disconnected — and over-gated.** The research half (Research Agent) is real, tested, and produced its best-ever output two days ago. The writing half has a coherent doctrine but no automation and eleven owner-gated checkpoints. The two halves are joined by hand-run adapter scripts. The command layer (Telegram `/yt_*`) points at a pipeline that was abandoned in August and was used exactly once, ever — a smoke test logged 2024-07-28.

**You did not design the wrong pipeline.** An independent blank-slate research agent, told only "solo creator wants topic→script with verification," converged on your exact architecture (planner → parallel research → one cited brief → constrained draft → final verification). The Research Agent's Packer run is proof the front half works: from one vague seed video, 11 sources, 989 facts, 119 claims, 99% quote verification, 94% coverage of the source video plus 47 names it never mentioned, and two places where it correctly contradicts the video.

**The reason you have no videos is not quality machinery failing — it is that no project has ever crossed the draft→record line, and the system is structured so that crossing it requires you at eleven separate moments.** Vela produced a finished 5,460-word script that passed cold readers on July 29. It was never recorded; it is now administratively frozen as a "baseline." Freemasons v4 reached ear check #3 on one movement and stopped. Hawara's test read has been "PENDING" since August 15. Packer is at your reading stage now. Four projects, four stalls, all at the same kind of gate: a moment reserved for you.

**The second reason: every real project has been converted into a test of the pipeline instead of a video.** The evidence is in the names — Hawara is literally `99-hawara-grip-test`, Packer's runner script is titled "Clean-run test." Five distinct pipeline generations exist on disk (Telegram v2, content-pipeline v3, v4 RUNBOOK, plus Scriptly and the youtube-system snapshot). Each time a project surfaced a defect, work pivoted to fixing the system and the video died as collateral.

**Third: state fragmentation is severe.** Three Research Agent clones (only one current), the live workspace repo has 325 uncommitted files and hasn't had a push since Aug 7, today's five Research Agent commits are unpushed, and the canonical memory repo's "current state" file describes a blocker that was resolved yesterday. Any fresh session that follows the documented resume points lands in the wrong place.

**What actually works unattended today:** the Research Agent (one Python command, ~40 min, self-recovering per stage) and an hourly dashboard sync. Everything else is Claude Code sessions doing manual orchestration against markdown runbooks.

**The shortest path to a video is Packer, using only what exists.** Research is done. The briefing is rendered and live. The steps that remain are: your one read+structure session, an outline, a draft under the already-locked model config, the existing edit/gate machinery run once each instead of iterated, and recording. The single genuinely missing build is the final script fact-check — and its spec is already written and independently reviewed.

**Verdict in one line:** stop building, run Packer through stages 4b→12 exactly once, tolerate imperfection at every gate, and ship. The system is close; the bottleneck is that it was never allowed to finish.

---

## 2. CURRENT SYSTEM MAP

```
                                   IDEA / SEED (topic, URL, video)
                                          │
        ┌─────────────────────────────────┼──────────────────────────────────┐
        │ PATH A (DEAD)                   │ PATH B (LIVE, manual)            │ PATH C (HISTORICAL)
        │ Telegram /yt_* skills           │ v4 RUNBOOK pipeline              │ old content-pipeline v3
        │ 21 skills in ~/.openclaw/skills │ ~/.openclaw/workspace/pipeline/  │ THE-PIPELINE.md (Jul 29)
        │ → skill_dispatch                │ 14 stages, 11 ★ Maz gates        │ produced Vela script
        │ → ACTIVE-PROJECT.txt            │ operated from Claude Code        │ (best output to date)
        │   = CLEARED 08-07               │ sessions, no runner              │ superseded by v4
        │ Used once ever (smoke test)     │                                  │
        └─────────────────────────────────┼──────────────────────────────────┘
                                          ▼
   Stage 3: RESEARCH AGENT  (~/Research_Agent-v3work — AUTOMATED, WORKS)
   dup-detect → extraction → validation → harvest → gap analysis → synthesis
   → distillation → Doc 0/1 assembly → 9-section Briefing (Doc 2) → Creator Brief (Doc 3)
   state: Supabase · started by: python script (no service) · gap loop: manual re-feed round 2
                                          │
                              [MANUAL ADAPTER SCRIPTS]  ← integration gap
                              scratchpad/e2e_films/*.py → episode 04b files
                                          ▼
   Stage 4b: 04b-briefing.md/.html  → ★ MAZ READS + STRUCTURE SESSION   ← PACKER IS HERE
                                          ▼
   5 outline → 6 ★gate A → 7 draft (DeepSeek per D-23) → 8 edit (Sonnet pairs, TIC-PASS)
   → 9 ★gate B (3 blind readers) → 9b pace → 10 ★ear loop → [MISSING: script fact-check]
   → 11 production package (STUB) / ammo-cards skill (built for old layout)
   → 12 ★record → 13 ★assemble (PRODUCTION-ASSEMBLY-PIPELINE, proven once on Atlantis P1)
   → 14 harvest
                                          ▼
                                   PUBLISH: never reached (0 videos)
```

---

## 3. REPO / RUNTIME TRUTH TABLE

| Path | Branch@HEAD | Last commit | vs origin | Dirty | Verdict |
|---|---|---|---|---|---|
| `~/Research_Agent-v3work` | main@`3da2a4e` | 2026-08-31 | **5 AHEAD (unpushed)** | 0 | **AUTHORITATIVE Research Agent.** All recent runs + fixes here |
| `~/Documents/GitHub/Research_Agent` | main@`51532e4` | 2026-08-27 | synced | 2 | STALE — superseded by v3work; memory docs still name it as "build here" |
| `~/Research_Agent` | main@`d6752ef` | 2026-03-15 | synced | 0 | OBSOLETE clone |
| `~/Documents/GitHub/Research_Agent-RECOVERY-2026-08-27` | not git | — | — | — | Recovery snapshot. ARCHIVE |
| `~/.openclaw/workspace` (= repo `Maz0327/lwm-pipeline`) | main@`441981c` | **2026-08-07** | **3 AHEAD (unpushed)** | **325** | **AUTHORITATIVE writing pipeline — but 3+ weeks of work uncommitted** (RUNBOOK, DECISIONS, TIC-PASS, both episodes, 303 quarantined P2 files) |
| `~/lost-with-maz-mem` | main@`60debc8` | 2026-08-31 | synced | 0 | Canonical memory. **Content ~1 day behind**: START-HERE says correction round "BLOCKED on OPENAI key" (resolved); knows nothing of today's cast/dispute/polarity fixes, two audits, or the plan pivot to script-level fact-check |
| `~/lost-with-maz-youtube-system` | main@`10a9122` | 2026-07-30 | synced | 0 | Read-only snapshot made *for* a redesign. Historical. ARCHIVE |
| `~/dashboard-deploy` (= `lwm-pipeline-dashboard`) | @ | 2026-08-31 | auto | — | Status dashboard, auto-pushed hourly to Railway via launchd. Contains a THIRD copy of old content-pipeline projects |
| `~/lwm-answer-key-P2` | not git | Aug 5-7 | — | — | Freemasons v4 clean-room episode + ground truth. Stalled at ear check #3 |
| `~/lwm-cleanroom*`, `~/lwm-openclaw-newtest` | not git | Aug 7-10 | — | — | Test scaffolding from the clean-room experiments. ARCHIVE |

**Runtime processes actually running:** OpenClaw gateway (launchd `ai.openclaw.gateway`), hourly `dashpush.sh` (dashboard→Railway), Ollama. Night-shift cron job exists but `enabled: false`. No other automation is live.

**Model routing, actual (verified `.env` + `backend/config.py` defaults):** briefing prose/distill `gpt-5.6-luna` (env), Read = same (env empty by D-035), harvest `gpt-5.4-mini`, extraction `gemini-3.6-flash`, judge `gpt-5.6-terra`, escalation `gpt-5.4-mini`, vision `gemini-2.5-pro`. Writing side per D-23 (docs, not code): DeepSeek-v4-pro drafts, Sonnet edits, kimi-k3 judges. The old yt_* skills still hardcode `gemini-2.5-pro` orchestrators — docs/runtime disagreement, moot because that path is dead.

---

## 4. END-TO-END STAGE TABLE (Path B — the only live path)

| Stage | Input | What actually executes | Model/tool | Output | Human needed | Working? | Failure modes |
|---|---|---|---|---|---|---|---|
| 0 bootstrap | slug | Claude session copies `_TEMPLATE` | — | episode folder | trivial | ✅ | template lacks 4b ledger row |
| 1 ★ angle+packaging | idea | Maz + Claude session | any | 01 file | YES + kill gate | ✅ process | **kill gate skipped on Packer** (ledger: "not run") |
| 2 ★ feasibility/format | angle | Maz decision | — | 02 file | YES | ✅ | ran after research on Packer (order violated) |
| 3 research | topic/URLs | `python scratchpad/run_*.py` → `run_research_job` | per §3 routing | Supabase docs 0-3 | start it; re-feed gap round manually | ✅ **proven on Packer** | synthesis crash (fixed), judge 429s, Anthropic seat (fixed); gap round 2 is a manual re-run |
| 4 fact-check brief | doc/registry | nothing defined for RA input | — | 04 registry | YES | ⚠️ **undefined** | registry format drifted (6 vs 7 vs 8 cols); Anchor column missing from template |
| 4b ★ briefing+structure | Doc 2 | **hand-run adapter scripts** render 04b | gpt-5.6-luna passes | 04b .md/.html/.json | YES (the read) | ✅ rendered, live at `http://192.168.1.175:8737/packer-briefing.html` | 3 copies can drift (JSON now copied into episode — fixed today) |
| 5 outline | 4b + structure | Claude session, manual | per session | 05 + outline.txt | review | ✅ process (Hawara) | thread ledger not carried to dispatches (caused Freemasons defect) |
| 6 ★ grip gate A | outline | 3 blind readers, improvised | 3 fresh models | verdict | YES reads verdict | ⚠️ | **no protocol file**; blind A/B position bias voided one gate design (08-04) |
| 7 draft | dispatch cargo | Claude session builds dispatch → drafter | DeepSeek-v4-pro (D-23) | 07 draft | ear check @700w | ✅ process (Hawara 825w, Freemasons M1 v9) | cargo leaks (P-265); one-redraft cap |
| 8 edit | draft+flags | delta-scan, TIC-PASS pairs-by-code | Sonnet + code | edit log | no | ✅ tested | — |
| 9 ★ grip gate B | full prose | 3 blind readers + register Q | 3 models + kimi | verdict+grip map | YES | ⚠️ same as 6 | kimi judge accuracy 0.58 |
| 9b pace edit | prose | code+model pass | — | 09b | no | ✅ | — |
| 10 ★ ear loop | pairs | Maz listens line-by-line | — | locks | **YES, heaviest** | ✅ but **stall point** (Freemasons ×3, Hawara pending 16 days) | never-batch vs D-14 contradiction unresolved |
| — script fact-check | final script | **DOES NOT EXIST** | — | — | reads report | ❌ NOT BUILT | spec written + reviewed; 1-2 days build |
| 11 production package | script+format | template stub only | — | stub | — | ❌ never produced | `ammo-cards` skill exists but reads OLD layout (`outputs/narrative-guide.txt`, old project paths) |
| 12 ★ record | package | Maz + booth diff | — | VO | YES | untested in v4 | — |
| 13 ★ assemble | VO+assets | PRODUCTION-ASSEMBLY-PIPELINE.md | ffmpeg/Resolve API | cut | YES | ⚠️ proven once (Atlantis P1, per docs; media not found on this Mac — §16) | — |
| 14 harvest | all | doctrine review | — | 14 file | no | ✅ process | — |

---

## 5. WHAT IS ACTUALLY WORKING (built + working + used)

- **Research Agent end-to-end** (`~/Research_Agent-v3work`): one command → 9-section briefing. Packer evidence: 11 sources, 989 facts, 119 claims, 99% quotes verified, gap analysis correctly named the missing record (victims, trial, forensics, parole campaign), round 2 filled it. Suite: 1,815 tests passing.
- **The gap loop** — the single most impressive result in the artifact history: from one vague seed, it identified exactly what a researcher would ask for next.
- **The 04b briefing as a read surface**: 10 sections, collapsible HTML, Players/Organisations/Places split, disputes staged only when two sides actually disagree (fixed today), chronology deduped with outvoted numbers dropped (fixed today).
- **Edit machinery**: TIC-PASS pairs-applied-by-code, delta-scan, lint `pipeline/lint/regression-tier1.mjs`, typed flags with dispositions. Tested on Hawara and Freemasons M1.
- **The v4 documentation discipline**: DOCTRINE ladder, tombstones, DECISION-LOGs, lineage headers. Unusually honest; the audits repeatedly verified claims *against* it successfully.
- **Memory repo mechanism** (`lost-with-maz-mem` + `/memory-sync` skill): works; content currently one day stale.
- **Dashboard auto-sync**: hourly, has run reliably (log shows continuous pushes).

## 6. WHAT IS BROKEN

- **Grounding/coverage/quote gates in RA are weak instruments** — demonstrated: invented names ground via substring, fabricated quotes pass bag-of-words at 0.85, coverage passes atoms found anywhere in the document. Accepted + documented in `~/Research_Agent-v3work/KNOWN-WEAK.md`; superseded by the planned script-level check. (Polarity blindness — "not guilty" ≡ "guilty" at 1.000 — was fixed today in `text_similarity.py`.)
- **Blind-reader gates have no protocol** and one gate design (comparative A/B) was proven invalid by position bias (Freemasons DECISION-LOG 08-04). Single-specimen reads unvalidated.
- **RA lint/intro-repair still run on the retired regex name-ranker** — cannot demand a card for the briefing's own subject ("Alferd Packer" merges into a cookbook title).
- **Stage 4 (fact-check the brief) has no defined input/output** for what RA now hands over; registry column formats drifted across episodes; provenance IDs die at the handoff.
- **START-HERE.md resume point is wrong** (says blocked on OpenAI key; that round completed 08-30/31).

## 7. WHAT EXISTS BUT IS NOT CONNECTED

- **Semantic advisory** (`backend/pipeline/semantic_advisory.py` + runner): built, doctrine-clean, ~3 min fast after optimization — **zero callers** in the worker. Decision made (advisory at stage 12, transcript) but never wired. Standalone scratchpad scripts only.
- **RA → episode handoff**: works only via hand-written adapter scripts in `scratchpad/e2e_films/` (`briefing_to_04b.py`, `rebuild_packer_*.py`). Nothing in either repo owns this.
- **`ammo-cards` skill** (claims ledger + asset checklist + shotlist from a finalized script): real, detailed — but reads the OLD project layout and paths. ~30-min adaptation from being stage 11's engine.
- **Creator Brief (Doc 3)** stage runs in the worker but nothing downstream consumes it (04b consumes Doc 2).
- **`watch` skill** (frame-level YouTube viewing) exists in Claude Code and was used on the Packer seed — not connected to RA's asset identification (which doesn't exist).
- **FastAPI app + Next.js frontend** exist in Research_Agent — recent runs bypass them entirely (direct Python invocation). Deployment status unverified (§16).
- **Google Drive**: env vars set in RA (`GOOGLE_DRIVE_ROOT_FOLDER_ID` etc.), no integration code found in `backend/integrations/`. Planned only.

## 8. WHAT IS PLANNED BUT NOT BUILT

- **Final script fact-check pass** — the one missing load-bearing piece. Spec exists (claims → grounded web search → URL + verbatim quote-in-page check → 4-way verdict report, never auto-edit), independently reviewed, research report grounds it in SAFE/VERISCORE/Claimify/AVeriTeC. Estimated $3-8 and 5-10 min per script.
- **Production packet generation** (stage 11) for v4 episodes.
- **Asset identification during research** (interview detection, timestamps, asset packet): nothing in RA does this.
- **Claim-graph → auto-generated Briefing** (D-26's eventual form): briefing exists; claim-graph generation of it does not.
- **Archival-source retrieval** (newspapers, court records, archive.org): flagged by research as the biggest open gap for documentary topics.

## 9. WHAT IS DUPLICATED / OBSOLETE

| Component | Copies | Verdict |
|---|---|---|
| Research Agent clones | v3work / Documents/GitHub / ~/Research_Agent / RECOVERY | **KEEP v3work** (push it!) · ARCHIVE the other three |
| Content-pipeline project trees | workspace/content-pipeline · dashboard-deploy/content-pipeline · youtube-system/projects · Desktop workspace | KEEP workspace · others REMOVE FROM ACTIVE PATH |
| Writing pipelines | v4 RUNBOOK · v3 THE-PIPELINE.md · 21 yt_* skills · Scriptly (×2 locations) · Desktop PIPELINE | **KEEP v4 only** · yt_* skills REMOVE FROM ACTIVE PATH (they mislead any orchestrator that finds them) · rest ARCHIVE |
| Fact-checking mechanisms | RA gates · registry stage 4 · planned script check · ammo-cards claims ledger | Converge on script check + registry; RA gates stay advisory (KNOWN-WEAK) |
| Source ledgers | RA Doc 0 · 04-sources-registry.md · SOURCES-REGISTRY.md (old) | Doc 0 = truth; registry derives from it (decided, not wired) |
| State systems | STAGE-LEDGER · PIPELINE-STATUS.md · dashboard.html · mem repo · Claude auto-memory | KEEP ledger + mem repo · PIPELINE-STATUS/dashboard = passive, fine · UNCLEAR: dashboard's production value |
| Model configs | .env (live) · RUNBOOK D-23 (docs) · yt_* skill headers (dead) · openclaw.json | KEEP .env + D-23 · yt_* headers obsolete |
| Backups/quarantines | _ORIGINALS-2026-07-27, -08-03, _BACKUPS, templates-backup, skills-backup, openclaw.json.bak×9, clobbered×8 | ARCHIVE (offline), they add noise to every search |

## 10. REAL PRODUCTION HISTORY

**Videos published through this system: 0** (stated in youtube-system README 07-30: "zero videos in four months"; no publish artifact found since).

| Project | Furthest artifact | Stall point |
|---|---|---|
| **Vela** (10) | **Finished script** `told-v2.md` 5,460w, passed cold readers 07-29 + extemp delivery doc | Delivery A/B "frozen"; never recorded; now a frozen baseline (Maz ruling 08-30) |
| **Atlantis** (07) | P1 voiced + production assembly proven (per docs/memory) | 07-20 delivery pivot; frozen baseline; production media not located on this Mac |
| **Freemasons old** | Full script (control arm) | Frozen baseline |
| **Freemasons v4** (P2) | 210KB brief, 113KB registry, 37KB outline, M1 drafted ×9 versions through full gauntlet | **Ear check #3, 08-06** — then quarantine 08-07, never resumed |
| **Hawara** (99) | 825w TIC-passed front half | **"GATE: Maz cold read … PENDING"** since 08-15 (16 days) |
| **Packer** (12) | Research complete, 04b briefing rendered+fixed | **At 4b: your read** — freshest, cleanest runway |
| Bermuda, Karahan Tepe, AI-IPO | research-stage artifacts | shelved/abandoned |

**Where projects stall: never in research. Always at an owner-gated stage after prose exists** (ear check, cold read, delivery decision) — or when the project is converted into a system test.

## 11. TOP 10 ACTUAL BOTTLENECKS (ranked)

1. **Every project becomes a pipeline test** — OVERENGINEERING/WORKFLOW · Evidence: `99-hawara-grip-test`, Packer's "Clean-run test" docstring, 5 pipeline generations, the 30hr teardown, frozen-baseline ruling · Consequence: no project has "ship" as its terminal state · SEVERE · blocks production · workaround: declare Packer a video, not a test.
2. **11 ★ owner gates, serialized** — HUMAN BOTTLENECK/PRODUCT DESIGN · Evidence: stall table above; every stall is at a ★ · SEVERE · blocks · workaround: batch your touchpoints (one structure session, one ear pass, one final read).
3. **No script-level fact verification** — INTEGRATION GAP · The one missing build; internal gates proven weak (KNOWN-WEAK.md) · HIGH · blocks *trusting* a script, not producing one · workaround: manual spot-check for video #1.
4. **RA→writing handoff is hand-run scripts** — INTEGRATION GAP · Evidence: `scratchpad/e2e_films/*.py` are the only bridge; stage 4 undefined for RA input · HIGH · slows every episode · workaround exists (the scripts work).
5. **Instrument distrust cascade** — TECHNICAL+MODEL LIMITATION · Blind A/B voided by position bias (08-04), kimi 0.58, tic "cannot be linted" → only trusted instrument is your ear → feeds #2 · HIGH · workaround: accept single-specimen gates as advisory.
6. **State fragmentation + unpushed work** — STALE STATE · 325 dirty files, workspace unpushed since 08-07, RA 5 commits unpushed, mem repo pointing at a resolved blocker and the wrong build clone · HIGH RISK (one disk failure loses the v4 pipeline's last 3 weeks) · fix: three `git push`es and one mem-repo commit.
7. **Dead command layer still installed** — STALE CONFIG · 21 yt_* skills route to gemini-2.5-pro + cleared ACTIVE-PROJECT; one lifetime use · MEDIUM (misleads agents; costs maintenance attention) · not blocking.
8. **Verification effort spent on the wrong layer** — OVERENGINEERING · Weeks on semantic v3 + gate hardening while scripts sat unrecorded; the pivot to script-level checking (08-31) is the correction · MEDIUM (sunk) · advisory lanes salvage value.
9. **Frozen baselines lock the nearest-to-done work** — WORKFLOW · Vela/Atlantis/Freemasons scripts administratively unrecordable pending a future head-to-head · MEDIUM · workaround: Packer doesn't touch them.
10. **Production/asset layer unbuilt for v4** — INTEGRATION GAP · Stage 11 stub; ammo-cards points at old layout; no asset packet from research · MEDIUM · blocks *editing* comfort, not recording · workaround: adapt ammo-cards (~30 min) + manual asset pull for video #1.

## 12. PRESERVE (genuinely excellent)

Research Agent whole (esp. gap analysis, harvest, the Briefing, provenance discipline) · the 04b read surface + structure-session concept (D-26) · TIC-PASS/pairs-applied-by-code + delta-scan + lint · the dispatch-cargo discipline and RULES v2 as *editor/lint* material · three-blind-readers as an instrument (needs a protocol file, 30 min) · ear loop as the taste stage (as ONE pass, not a loop) · DOCTRINE/tombstone/ledger honesty · mem repo + /memory-sync · PRODUCTION-ASSEMBLY-PIPELINE.md · KNOWN-WEAK.md pattern.

## 13. FREEZE UNTIL 3 VIDEOS SHIP

All model bake-offs and seat changes · semantic-advisory wiring (it's advisory; wire later) · RA gate hardening beyond KNOWN-WEAK · registry-of-document-surface refactor · dashboard features · memory re-architecture · any new instrument, law, or rule intake (RULE-GROWTH already says growth goes to reviewers/lint) · head-to-head baseline experiments · cleanroom experiments · yt_* skill repair · Drive integration · claim-graph briefing generation · AI-OS and every non-LWM project during production weeks.

## 14. MINIMUM VIABLE PRODUCTION PATH (existing pieces only)

`RA job (works) → adapter script → 04b (works) → Maz structure session (1 sitting) → outline (session) → draft via D-23 dispatch (process proven) → delta-scan+TIC-PASS+lint (works) → grip gate B once, advisory (works) → ear pass ONCE (works) → manual spot fact-check of load-bearing claims (until the script checker is built) → ammo-cards adapted (30 min) → record → PRODUCTION-ASSEMBLY → publish`

Distance labels: research **already working** · handoff **small integration** · outline/draft/edit **already working as process** · script fact-check **moderate work (1-2 days)** · production packet **small integration** · assembly **already proven once** · full no-human automation **major missing system — and deliberately so; do not build now**.

## 15. EXACT NEXT-VIDEO WORKFLOW (Packer, starting tomorrow)

1. **Push everything first** (10 min): `cd ~/Research_Agent-v3work && git push` · `cd ~/.openclaw/workspace && git add -A && git commit -m "v4 state through Packer 4b" && git push` · commit mem-repo checkpoint.
2. **Read the briefing**: `http://192.168.1.175:8737/packer-briefing.html` (or `~/.openclaw/workspace/pipeline/episodes/12-packer-colorado-cannibal/04b-briefing.html`). One sitting. Build structure Atlantis-method; log picks in `DECISION-LOG.md`; retro-fill stage 1 (title/thumbnail kill gate) in the same sitting.
3. **Outline** (Claude Code session): write `05-outline.md` + `outputs/outline.txt` from your structure; carry thread rows (the Freemasons lesson).
4. **Gate A** once, advisory: 3 fresh readers on the outline; log in ledger.
5. **Draft M1**: build dispatch per RUNBOOK §DISPATCH PROTOCOL (RULES.md whole + Tier-1 exemplars + movement events + registry rows); DeepSeek-v4-pro, thinking disabled; your 700w ear check; then remaining movements.
6. **Edit**: delta-scan → TIC-PASS ×2 → `node pipeline/lint/regression-tier1.mjs`.
7. **Gate B + ONE ear pass** with locks. No iteration loops — flag, fix, move.
8. **Fact spot-check**: until the script checker ships, verify the ~20 load-bearing claims by hand against the briefing's Source Trail (SRC links resolve in Doc 0).
9. **Production packet**: run adapted ammo-cards on the final script → claims ledger + asset checklist + shotlist into `11-production-package.md` + `editing/`.
10. **Record** (booth diff per stage 12) → **assemble** per `content-pipeline/PRODUCTION-ASSEMBLY-PIPELINE.md` → publish.

If development is frozen today, this workflow is executable tomorrow; the only degraded step is #8 (manual instead of automated).

## 16. OPEN QUESTIONS I COULD NOT RESOLVE

1. **Where Atlantis P1's actual production media lives** (VO, Resolve project, renders). Searched `~/Desktop/YT-Lost_With_Maz-WORKSPACE` and `~/Movies` to depth 4: no .wav/.mp4/.drp found. Docs assert production was proven; the media may be on an external drive or another Mac. Unverified.
2. **Supabase-side state** (job records, stored docs for job `0f7e0818`, the deployed frontend/API if any). I did not query the cloud; local artifacts (scratchpad JSONs + episode 04b) are complete copies of the docs, so nothing blocks production on this.
3. **Whether the second OpenClaw cron job is enabled** (first is `enabled:false`; file listing was truncated).
4. **Google Drive desktop sync scope** — a `.tmp.driveupload` dir exists in content-pipeline, implying the Drive client syncs that folder; I didn't verify its configuration.
5. **`lwm-pipeline-dashboard` remote contents** beyond the local deploy clone; and whether Railway is still serving it (log says pushes succeed; I didn't hit the URL).
6. **The other Mac's checkouts** (memory flags them STALE for CRT; likely also for LWM repos). Not on this machine to inspect.
