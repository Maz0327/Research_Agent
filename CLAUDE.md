# CLAUDE.md — Research Agent

**Last Updated:** 2026-01-20

---

## ⭐ CURRENT WORK ITEM (2026-09-01) — Lost With Maz V1

**This repo hosts the LWM V1 control surface: `backend/lwm/`** (the one supported bridge between
the Research Agent and the v4 writing pipeline; CLI `python -m backend.lwm.cli`, wrapped by
`bin/lwm` in `~/.openclaw/workspace`). Tests: `backend/tests/test_lwm_*.py`.

**The PACKER READINESS PATCH is IMPLEMENTED, tested and pushed (`eda1667`). It is NOT the next
work item — do not rebuild it.** 1,933 tests passed / 3 skipped. Doctrine: *the video is the
experiment, the pipeline is not.* Build nothing that did not stop or materially slow the last real
video. There is no Phase 3.

**The next action is MAZ CHOOSING THE PACKER ANGLE — not more pipeline implementation.** Packer
sits at the new ANGLE creator touchpoint with the baseline, three story-level alternatives, his
previous idea and the custom path. No angle has been chosen and no agent chooses one.

**Read before writing any LWM code — in the memory repo `~/lost-with-maz-mem`:**
1. `reference/SESSION-HANDOFF-2026-09-01-PACKER-AT-THE-ANGLE-TOUCHPOINT.md` — the current checkpoint
2. `sessions/2026-09-01-packer-readiness-patch-implemented.md` — what was built and why
3. `decisions/PROJECT-DECISION-REGISTER-ADDENDUM-2026-09-01-READINESS-PATCH-IMPLEMENTATION.md` —
   D-V1-15…21
4. `decisions/PROJECT-DECISION-REGISTER-ADDENDUM-2026-09-01-CREATOR-FLOW-AND-READINESS-PATCH.md` —
   D-V1-5…14, the WHY

**Hard rules:** Packer's research must NOT rerun (job `0f7e0818-5def-49dd-bec9-a16b1b534979`) — a
THIN movement gets `lwm backfill`, which appends rows · Packer's angle is NOT chosen and no agent
chooses it · `KNOWN-WEAK.md` is the do-not-reopen list for internal gates · model seats are settled
(writer `deepseek-v4-pro` · editor `gpt-5.6-luna` · judge/reader/10b `gpt-5.6-terra`,
`backend/lwm/routing.py`) — an unreachable seat FAILS LOUDLY, never substitutes · ledger stage keys
keep their historical numbers (D-V1-15): the running order is `backend/lwm/ledger.py:STAGES` and
`lwm-pipeline:pipeline/STATE-MAP.md`, never the number inside a key.

---

## ⚠️ READ THIS FIRST

**Authority flows from:** [`docs/authoritative/INDEX.md`](docs/authoritative/INDEX.md) — the Repo Constitution.

**If ANY document conflicts with INDEX.md, INDEX.md wins.**

**Ignore all files in:**
- `docs/_archive_do_not_read/`
- `Archive Docs/`
- `Active Docs/`

---

## Quick Reference

| Resource | Location |
|----------|----------|
| **Constitution** | `docs/authoritative/INDEX.md` |
| **System Spec** | `docs/authoritative/spec/RASS.md` |
| **Progress** | `PROGRESS.md` |
| **Decisions** | `DECISIONS.md` |
| **Operations** | `docs/operational-reference.md` |

---

## Session Checklist

```
[ ] Read PROGRESS.md — know where we are
[ ] Check INDEX.md if architectural questions arise
[ ] Get approval before code changes
[ ] Update PROGRESS.md when done
```

---

## Development Commands

```bash
# Backend
source venv/bin/activate
uvicorn backend.app.main:app --reload
celery -A backend.worker worker --loglevel=INFO
pytest backend/tests/ -v

# Frontend
cd frontend && npm run dev
```

---

**Never guess. Always ask. INDEX.md is the authority.**
