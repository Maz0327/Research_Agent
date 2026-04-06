# Exploration Reports Index

## Latest Explorations

### Explore-260405-1304: Code Removal & Simplification Audit
- **Date:** 2026-04-05
- **Scope:** Full codebase (backend + frontend)
- **Focus:** Dead code, broken dependencies, unused features
- **Files:**
  - `Explore-260405-1304-code-removal-audit.md` — Full detailed report (17KB)
  - `Explore-260405-1304-code-removal-audit-SUMMARY.md` — Quick summary (2KB)

### Contents of Full Report

1. **youtube-transcript-api (BROKEN)**
   - Known broken on cloud IPs
   - Still in requirements.txt but disabled
   - Location: `backend/pipeline/transcript_acquisition.py:220-252`
   - Status: Tier 3 of fallback chain (REMOVE)

2. **Transcript Fallback Chain**
   - Tier 1: Supadata ✅ (works)
   - Tier 2: Whisper ✅ (works, expensive)
   - Tier 3: YouTube captions ❌ (broken on cloud)
   - Files: `transcript_acquisition.py`, `transcripts.py`, `transcript_service.py`

3. **Four-Step Wizard**
   - Topic → Sources → Mode → Preview
   - Well-structured, no issues
   - File: `frontend/components/dashboard/job-creation-wizard.tsx`

4. **Document Display**
   - All 4 documents shown by default (Doc 0, 1, 2, 3)
   - File: `frontend/components/job-card/DocumentCardGrid.tsx`
   - Doc 3 (Creator Brief) always rendered if available

5. **Dead/Unused Code**
   - Backend archive: 4 files (booster, deprecated handlers, validation)
   - Frontend archive: 8 directories (theme toggle, legacy iteration, pages router)
   - All properly archived per Rule 14

6. **Unused Dependencies (9 packages)**
   - praw, tavily-python, exa-py, datasketch, rank-bm25, rapidfuzz, spacy, mutagen
   - next-themes (disabled with forcedTheme="dark")
   - All REMOVE candidates

7. **Theme Toggle Code (Disabled)**
   - Dark-only now (forcedTheme="dark" in providers.tsx)
   - Old code archived: `frontend/archive/ThemeContext.tsx`
   - Active remnant: `frontend/app/providers.tsx:31-41`
   - Action: Remove next-themes dependency

8. **Gap Analysis + Synthesis**
   - Both present as separate stages
   - Synthesis depends on Gap Analysis output
   - Cannot merge directly without refactor
   - Files: `gap_analysis.py`, `semantic_synthesis.py`

9. **Creator Brief (Doc 3) Generation**
   - Currently ALWAYS ON (unconditional execution)
   - Location: `backend/worker.py:475`
   - Cost: Expensive (Gemini synthesis)
   - Action: Make on-demand, remove line 475

10. **Legacy Mode References**
    - Topic-based discovery removed 2026-01-19
    - Defensive code rejects these jobs
    - V1 iteration deprecated 2026-01-26
    - Status: Code is defensive, not dead

---

## Quick Action Summary

### CRITICAL
- [ ] Remove `youtube-transcript-api` from requirements.txt
- [ ] Remove Tier 3 from transcript fallback chain

### HIGH
- [ ] Remove 9 unused packages from requirements.txt
- [ ] Remove next-themes from package.json

### MEDIUM
- [ ] Make Creator Brief on-demand
- [ ] Move generation to iteration endpoint

### LOW
- [ ] Cleanup theme toggle references
- [ ] Update archived code comments

---

## Related Documentation

- Architecture Rules: `.claude/rules/architecture.md`
- Implementation Rules: `.claude/rules/implementation.md`
- API Integration Rules: `.claude/rules/api-integrations.md`
- Authority Rules: `.claude/rules/authority.md`

---

## File Locations Summary

**Full Report Path:**
```
/Users/maz/Documents/GitHub/Research_Agent/frontend/plans/reports/
  Explore-260405-1304-code-removal-audit.md
  Explore-260405-1304-code-removal-audit-SUMMARY.md
```

**Key Codebase Files Referenced:**
- Backend: `backend/pipeline/`, `backend/integrations/`, `backend/archive/`
- Frontend: `frontend/components/`, `frontend/app/`, `frontend/archive/`
- Config: `requirements.txt`, `frontend/package.json`

---

**Report Generated:** 2026-04-05 13:04 UTC
**Exploration Agent:** Specialized code search & analysis
**Thoroughness Level:** Comprehensive with line numbers and file paths
