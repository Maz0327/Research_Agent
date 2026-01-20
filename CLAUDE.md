# CLAUDE.md — Research Agent

**Last Updated:** 2026-01-20

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
