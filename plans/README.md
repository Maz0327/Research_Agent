# Plans Directory

> **Authoritative spec lives at `docs/authoritative/INDEX.md`.**
> Plans are **non-authoritative** implementation guides.

---

## Policy

1. **CURRENT_PLAN.md** is the only active plan.
2. Completed/abandoned plans must be archived to `plans/_archive/`.
3. Only `CURRENT_PLAN.md` should be referenced during execution.
4. Templates in `plans/templates/` are reusable starting points.

## Structure

```
plans/
├── README.md           # This file
├── CURRENT_PLAN.md     # Active plan (if any)
├── templates/          # Plan templates
└── _archive/           # Completed/abandoned plans
    ├── reports/        # Archived agent reports
    ├── misc/           # Archived misc plans
    └── 260*/251*/      # Archived dated plans
```

## Creating a New Plan

1. Copy a template from `plans/templates/`
2. Rename to `CURRENT_PLAN.md`
3. Fill in details
4. When complete, move to `_archive/YYYY-MM-DD_<name>.md`

---

**END**
