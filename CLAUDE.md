# CLAUDE.md — Research Agent

**Last Updated:** 2026-01-20

---

## ⭐ CURRENT WORK ITEM (2026-09-01) — Lost With Maz V1

**This repo now also hosts the LWM V1 control surface: `backend/lwm/`** (the one supported bridge
between the Research Agent and the v4 writing pipeline; CLI `python -m backend.lwm.cli`, wrapped
by `bin/lwm` in `~/.openclaw/workspace`). Tests: `backend/tests/test_lwm_*.py`.

**V1 is built and pushed. The next work item is the bounded PACKER READINESS PATCH — not a new
phase.** Doctrine: *the video is the experiment, the pipeline is not.* Build nothing that did not
stop or materially slow the last real video.

**Read before writing any LWM code — in the memory repo `~/lost-with-maz-mem`:**
1. `roadmap/PACKER-READINESS-PATCH-IMPLEMENTATION-PLAN.md` — the execution contract
2. `decisions/PROJECT-DECISION-REGISTER-ADDENDUM-2026-09-01-CREATOR-FLOW-AND-READINESS-PATCH.md`
3. `sessions/2026-09-01-v1-complete-archaeology-and-packer-readiness-patch-handoff.md`

**Hard rules:** Packer's research must NOT rerun (job `0f7e0818-5def-49dd-bec9-a16b1b534979`) ·
Packer's angle is NOT locked and no agent chooses it · implementation STOPS at the new ANGLE
touchpoint · `KNOWN-WEAK.md` is the do-not-reopen list for internal gates · model seats are
settled (writer `deepseek-v4-pro` · editor `gpt-5.6-luna` · judge/reader/10b `gpt-5.6-terra`,
`backend/lwm/routing.py`) — an unreachable seat FAILS LOUDLY, never substitutes.

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
