# Authority Rules

**Priority:** CRITICAL — These rules prevent documentation drift and confusion.

---

## Single Source of Authority

**The Repo Constitution is:** `docs/authoritative/INDEX.md`

No other document may claim:
- "authoritative"
- "single source of truth"
- "canonical" (unless listed by INDEX.md)
- "non-negotiable" (unless within INDEX.md or files it references)

---

## Archive Ignore Rules

**NEVER read or implement from these folders:**

1. `docs/_archive_do_not_read/**` — Superseded documentation
2. `Archive Docs/**` — Historical documents
3. `Active Docs/**` — Legacy documents (to be fully archived)

**If you encounter a file in these folders:**
- Do NOT treat it as authoritative
- Do NOT implement from it
- Refer to `docs/authoritative/INDEX.md` for current truth

---

## Conflict Resolution

If ANY document conflicts with `docs/authoritative/INDEX.md`:

1. **INDEX.md wins**
2. The conflicting document is either outdated or incorrect
3. Flag the conflict and defer to INDEX.md

---

## Authority Validation

Before treating any document as authoritative, check:

1. Is it listed in `docs/authoritative/INDEX.md`?
2. Is it located under `docs/authoritative/`?
3. Does it NOT contain a LEGACY or SUPERSEDED banner?

If all three are true → Document is authoritative.
Otherwise → Document is reference only.

---

## Prohibited Actions

**DO NOT:**
- Add "authoritative" claims to documents outside `docs/authoritative/`
- Implement from archived or legacy folders
- Treat historical context docs as specifications
- Override INDEX.md decisions without explicit owner approval

---

## Quick Reference

| Authoritative | Location |
|---------------|----------|
| Constitution | `docs/authoritative/INDEX.md` |
| System Spec | `docs/authoritative/spec/RASS.md` |
| Vocabulary | `docs/authoritative/spec/Operational_Definitions.md` |
| Output Format | `docs/authoritative/spec/Document_Output_Format.md` |
| Validation | `docs/authoritative/spec/Validation_and_Retry_Rules.md` |

| NOT Authoritative | Location |
|-------------------|----------|
| Archived docs | `docs/_archive_do_not_read/` |
| Historical docs | `Archive Docs/` |
| Legacy docs | `Active Docs/` |
