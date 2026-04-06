# Code Removal & Simplification — Quick Summary

**Exploration ID:** 260405-1304
**Full Report:** `/Users/maz/Documents/GitHub/Research_Agent/frontend/plans/reports/Explore-260405-1304-code-removal-audit.md`

---

## Top Findings

### 1. BROKEN Dependency: youtube-transcript-api
- **Status:** Known broken on cloud IPs (Railway, AWS, GCP)
- **Location:** Tier 3 of transcript fallback chain
- **File:** `backend/pipeline/transcript_acquisition.py:220-252`
- **Action:** REMOVE from requirements.txt line 55

### 2. Unused Dependencies (9 packages)
```
❌ praw               — lines 61 (never imported)
❌ tavily-python     — line 96 (never imported)
❌ exa-py            — line 44 (never imported)
❌ datasketch        — line 72 (never imported)
❌ rank-bm25         — line 75 (never imported)
❌ rapidfuzz         — line 78 (never imported)
❌ spacy             — line 82 (never imported)
❌ mutagen           — line 54 (never imported)
❌ next-themes       — frontend package.json:40 (forcedTheme=dark disables it)
```

### 3. Always-On Creator Brief (Doc 3)
- **Current:** Unconditionally generated after document assembly
- **Location:** `backend/worker.py:475`
- **Cost:** Expensive (Gemini synthesis)
- **Action:** Make on-demand, remove line 475

### 4. Already Archived (Good!)
- Backend archive: `/backend/archive/` (4 files: booster, deprecated handlers, validation)
- Frontend archive: `/frontend/archive/` (8 directories, includes theme toggle, legacy iteration)
- Status: Properly archived per Rule 14

### 5. Theme Toggle (Disabled)
- **Status:** Dark-only now (`forcedTheme="dark"`)
- **Dead Code:** `/frontend/archive/ThemeContext.tsx` (old light/dark context)
- **Active Remnant:** `frontend/app/providers.tsx:31-41` (next-themes still imported)
- **Action:** Remove next-themes from package.json

### 6. Transcript Fallback Chain
- **Tier 1:** Supadata ✅ (primary, works)
- **Tier 2:** Whisper ✅ (expensive, works)
- **Tier 3:** YouTube captions ❌ (BROKEN on cloud)
- **Action:** Remove Tier 3 entirely

### 7. Four-Step Wizard
- **Status:** Well-structured, no issues
- **Files:** Topic → Sources → Mode → Preview
- **Component:** `frontend/components/dashboard/job-creation-wizard.tsx` (lines 1-143)

### 8. Document Display (All 4 by Default)
- **Doc 0:** Source Ledger (always shown if available)
- **Doc 1:** Jump-Start (always shown)
- **Doc 2:** Semantic Brief (always shown)
- **Doc 3:** Creator Brief (always shown if exists)
- **Component:** `frontend/components/job-card/DocumentCardGrid.tsx`

### 9. Gap Analysis + Synthesis
- **Status:** Separate stages with data dependency
- **Gap Analysis:** Identifies what's missing
- **Synthesis:** Uses gap analysis output
- **Merge Possible:** Not recommended (synthesis depends on gap analysis)

### 10. Legacy Mode References
- **Topic-Based Discovery:** Removed 2026-01-19
- **Status:** Defensive code rejects these jobs (lines 110-118 in worker.py)
- **V1 Iteration:** Deprecated 2026-01-26 (archived, 410 Gone)

---

## Action Checklist

### CRITICAL (Broken Code)
- [ ] Remove `youtube-transcript-api` from requirements.txt
- [ ] Remove `_try_youtube_captions()` from transcript_acquisition.py
- [ ] Remove unused Tier 3 from fallback chain docstrings

### HIGH PRIORITY (Unused Dependencies)
- [ ] Remove 9 unused packages from requirements.txt
- [ ] Remove next-themes from package.json

### MEDIUM (Optimization)
- [ ] Make Creator Brief on-demand (worker.py line 475)
- [ ] Move generation to iteration endpoint

### LOW (Cleanup)
- [ ] Remove dead theme toggle code references
- [ ] Add comments explaining archived code

---

## Key Files Involved

**Backend:**
- `backend/pipeline/transcript_acquisition.py` — Transcript chain
- `backend/worker.py` — Pipeline orchestration
- `backend/pipeline/stages/creator_brief_stage.py` — Doc 3 generation
- `backend/pipeline/stages/gap_analysis.py` — Gap identification
- `backend/pipeline/stages/semantic_synthesis.py` — Cross-source synthesis
- `backend/archive/deprecated_route_handlers.py` — Legacy endpoints
- `requirements.txt` — Dependency list

**Frontend:**
- `frontend/components/dashboard/job-creation-wizard.tsx` — 4-step form
- `frontend/components/job-card/DocumentCardGrid.tsx` — Document display
- `frontend/app/providers.tsx` — Theme configuration
- `frontend/archive/ThemeContext.tsx` — Old theme code
- `package.json` — Frontend dependencies

---

## Estimated Impact

- **Lines of Code to Remove:** ~500 (mostly dependencies + broken transcript tier)
- **Complexity Reduction:** Medium
- **Risk Level:** Low (all dead code or unused dependencies)
- **Test Coverage:** Good (archive structure already in place)
