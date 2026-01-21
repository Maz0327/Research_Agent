# Constitution Authority Audit — 2026-01-20 09:04

## Purpose
Inventory all docs claiming authority status and map conflicts with LOCKED DECISIONS.

---

## Conflict Map Table

| File Path | Claim | Conflicts With | Action |
|-----------|-------|----------------|--------|
| `docs/authoritative/context/Context_Handoff.md:5` | "single authoritative source of truth" | INDEX.md is sole constitution | **Demote**: replace with pointer to INDEX.md |
| `docs/Database_Schema.md:3-4` | "Authoritative Specification", "single source of truth" | INDEX.md is sole constitution; doc NOT in authoritative/ | **Demote**: change to "Reference: Database Schema" + add pointer |
| `Active Docs/PRD_v6.md:7,765` | "Authoritative Specification" | Legacy pipeline (NotebookLM, Blueprint); INDEX.md is sole | **Archive**: move to docs/_archive_do_not_read/ with LEGACY banner |
| `Active Docs/CLAUDE.md` | Describes 15-stage legacy pipeline | Runtime has semantic-only pipeline | **Archive**: superseded by root CLAUDE.md |
| `Active Docs/prompts-reference/CLAUDE_CODE_CONTEXT.md:5` | "AUTHORITATIVE" | Describes old decisions, INDEX.md is sole | **Archive**: move to docs/_archive_do_not_read/ |
| `Active Docs/prompts-reference/CLAUDE_CODE_MEGA_PROMPT.md` | "authoritative for orchestration" | OK for domain-specific refs, but restates system rules | **Archive**: superseded by INDEX.md + orchestration specs |
| `Active Docs/TEP_v2.md:5` | "must be followed EXACTLY" | Legacy multi-API architecture | **Archive**: superseded |
| `Celery_Task_Flow.md:3` | "Authoritative definition" | OK — domain-specific, not overall authority | **Keep** |
| `Job_State_Machine.md:3` | "Authoritative definition" | OK — domain-specific, not overall authority | **Keep** |
| `API_Endpoint_Spec.md:3` | "Authoritative definition" | OK — domain-specific, not overall authority | **Keep** |

---

## Additional Conflicts Detected

### 1. Storage Strategy Mismatch
- **docs/Database_Schema.md**: Describes `drive_folder_id`, `drive_folders` columns
- **LOCKED DECISION**: Google Drive is REMOVED; storage is Option B (artifacts JSON + Supabase Storage)
- **Resolution**: Doc describes DB schema only; Drive fields are deprecated columns (see line 654-655, 797-812)

### 2. Pipeline Description Mismatch
- **Active Docs/CLAUDE.md**: Describes 15-stage pipeline with Drive upload, Slack, Reddit
- **LOCKED DECISION**: Only semantic pipeline is reachable; legacy stages deleted
- **Resolution**: Archive the file

### 3. Mode Definition Missing Updates
- **INDEX.md current**: Has 6 modes but missing Quote vs Observation policy details
- **LOCKED DECISION**: Explicit Quote/Observation policy per mode required
- **Resolution**: Update INDEX.md with detailed mode policy table

### 4. Doc Numbering Alias Not Documented
- **INDEX.md current**: Uses Doc 0/1/2/3 naming
- **LOCKED DECISION**: Runtime uses 20/21/22/3 aliasing
- **Resolution**: Add alias mapping table to INDEX.md

---

## Documents That Correctly Defer to INDEX.md

| File Path | Behavior |
|-----------|----------|
| `Index.md` (root) | Correctly points to docs/authoritative/INDEX.md |
| `DECISIONS.md` | References INDEX.md as constitution |
| `SPEC_MANIFEST.md:31` | Identifies INDEX.md as "Repo Constitution" |
| `docs/operational-reference.md` | Points to authoritative specs |

---

## Recommended Actions Summary

1. **Demote** Context_Handoff.md, Database_Schema.md — remove authority claims
2. **Archive** entire `Active Docs/` folder → `docs/_archive_do_not_read/`
3. **Update** INDEX.md with:
   - Quote/Observation policy per mode
   - Doc alias mapping table (20/21/22 ↔ Doc 0/1/2)
   - What IS and IS NOT the system
   - Storage strategy Option B
   - Transcript chain
   - Failure semantics
   - Enforcement surfaces
4. **Create** `.claude/rules/authority.md` — ignore archives rule
5. **Slim** root CLAUDE.md to pointer-only

---

## Unresolved Questions

None — all conflicts map to clear resolutions per LOCKED DECISIONS.
