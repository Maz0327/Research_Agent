# Product Viability Overhaul — Complete Plan Index

**Initiative:** Transform Research Agent from prototype to market-ready product
**Started:** 2026-04-05 (brainstorm & research)
**Implementation Started:** 2026-04-06 (Pre-Prep prerequisite)
**Status:** 🔄 IN PROGRESS — Pre-Prep 3/7 complete, ready for continuation
**Branch:** `feature/product-viability-overhaul`

---

## Quick Navigation

### Start Here
1. **Main Plan:** `plan.md` — Overview, phase map, key decisions
2. **Session Summary:** `reports/project-manager-260406-1414-session-completion.md` — What's done, what's next
3. **Status Dashboard:** `reports/project-manager-260406-1414-overhaul-status.md` — Initiative progress
4. **Plan Index:** `reports/project-manager-260406-1414-plan-summary.md` — Folder structure & dependencies

### Phase Files (Pending Implementation)
- `phase-00-cleanup-and-removals.md` — Remove youtube-transcript-api, merge gap+synthesis
- `phase-01-single-screen-input.md` — Unified input wizard (topic + sources + mode)
- `phase-02-hero-document-ux.md` — Single document view with all 4 core docs
- `phase-03-sonnet-editorial-pass.md` — Editorial AI on Doc 2, 5, 6
- `phase-04-paywall-stripe.md` — $19/mo subscription + Stripe integration
- `phase-05-sse-streaming.md` — Real-time progress via Redis pub/sub
- `phase-06-chat-with-research.md` — Chat interface for research documents
- `phase-07-quick-mode.md` — Fast mode (single Gemini call with source labels)
- `phase-08-source-discovery.md` — Auto-find relevant sources
- `phase-09-gemini-multimodal-fallback.md` — Video/audio analysis fallback
- `phase-10-credit-system.md` — Usage-based credit system

### Research & Validation
- `reports/brainstorm-260405-1617-product-viability-overhaul.md` — Initial brainstorm (validated)
- `reports/researcher-260406-1233-brainstorm-validation.md` — Technical feasibility
- `reports/researcher-260406-1252-business-viability-analysis.md` — Market, pricing, margin analysis
- `reports/researcher-260405-1552-ai-research-product-ux-patterns.md` — UX best practices
- `reports/researcher-260405-1533-multi-model-pipeline-optimization.md` — Cost optimization strategy
- `reports/ui-ux-audit-260406-1329-current-state.md` — Baseline UX score (5.2/10)

### Prerequisite Plan (Pre-Prep UX Foundation)
**Location:** `../260406-1337-pre-prep-ux-foundation/`

Must complete before phases 01-10:
- ✅ PP-1: Design Token Migration (COMPLETE)
- ✅ PP-2: Font & Type Scale (COMPLETE)
- ✅ PP-3: Creator Copy Rewrite (COMPLETE)
- ⏳ PP-4: Citation Pills (ready)
- ⏳ PP-5: Progress UX Polish (ready)
- ⏳ PP-6: Iteration UX Redesign (ready)
- ⏳ PP-7: First Impressions (ready)

---

## Initiative At a Glance

| Aspect | Details |
|--------|---------|
| **Goal** | Market-ready product with verified, source-cited, single-screen UX |
| **Positioning** | "Turn any collection of videos and articles into a verified, source-cited script — with the angle nobody else covered" |
| **MVP Price** | $19/mo after 3 free jobs |
| **Breakeven** | 6 users @ $19/mo |
| **Gross Margin** | 65-70% at scale |
| **MVP Timeline** | 3-4 weeks (after Pre-Prep) |
| **Full Timeline** | 10-14 weeks |
| **Status** | Pre-Prep 42.8% complete |
| **Next Step** | PP-4, PP-5, PP-6, PP-7 (all unblocked) |

---

## Key Decisions (Locked In)

### Product & Strategy
- [x] Positioning statement finalized
- [x] Differentiators locked: verified + source-cited + untold angle
- [x] MVP scope: input → hero doc → editorial → paywall
- [x] Price: $19/mo (vs. credit system or per-use)
- [x] Theme: Dark-only in MVP (CSS vars ready for light mode later)

### Architecture
- [x] Full mode: Per-source isolation PRESERVED (no breaking change)
- [x] Quick mode: Single Gemini call with source labels (new, cost-optimized)
- [x] Streaming: Redis pub/sub (Celery → FastAPI → EventSource)
- [x] Editorial: Sonnet 4.6 on Doc 2 (Research Brief) + Doc 5/6 (Script/Blog)

### Design System
- [x] Font: Plus Jakarta Sans (primary), Mono 821 (code)
- [x] Type scale: caption, body-sm, body, body-lg
- [x] Colors: 1464 hardcoded colors replaced with semantic tokens
- [x] Icons: Lucide only (no emoji)

---

## Session 260406 Accomplishments

### Code Implemented
- **PP-1:** 1464 color replacements, emoji→Lucide (100 files, commit `a2e3b63`)
- **PP-2:** Font migration, type scale defined (66 files, commit `a2e3b63`)
- **PP-3:** Copy rewrite to creator language (22 files, commit `d51cc18`)

### Documentation
- Updated main plan with Pre-Prep progress
- Updated Pre-Prep plan with completion status
- Updated PP-3 phase file with completion checklist
- Updated PROGRESS.md with session summary
- Created 3 project manager reports

### Unblocked
- PP-4, PP-5, PP-6, PP-7 ready to execute immediately
- Phase 00 ready after Pre-Prep completes
- Phases 01-04 ready for design phase after Phase 00

---

## How to Use This Plan

### For Next Session
1. Start with `reports/project-manager-260406-1414-session-completion.md` for context
2. Review Pre-Prep plan: `../260406-1337-pre-prep-ux-foundation/plan.md`
3. Execute PP-4, PP-5, PP-6, PP-7 in order
4. After Pre-Prep: start Phase 00 (Cleanup & Removals)

### For Future Phase Planning
1. Check `phase-XX-name.md` for detailed spec
2. Review dependencies in main `plan.md`
3. Read relevant research reports
4. Plan in order; don't skip phases

### For Context on Decisions
1. Why this positioning? → See `reports/researcher-260406-1252-business-viability-analysis.md`
2. Why quick mode? → See `reports/researcher-260405-1533-multi-model-pipeline-optimization.md`
3. Why this UX approach? → See `reports/researcher-260405-1552-ai-research-product-ux-patterns.md`

---

## Success Criteria

### Phase Completion
- [x] All phases documented with detailed specs
- [x] All dependencies mapped
- [x] All research validated
- [x] All design decisions locked in
- [x] Pre-Prep 3/7 complete

### Readiness for Next Work
- [x] Four unblocked phases ready
- [x] Phase 00 scoped and ready
- [x] MVP phases scoped and ready
- [x] No blockers, no unknowns
- [x] Team has complete context

---

## Team Context

**Main Agent Role:**
- Resume Pre-Prep phases PP-4 through PP-7 next session
- Orchestrate Phase 00 after Pre-Prep
- Plan parallel execution of Phases 01-03

**Blocker Status:**
- ✅ All research complete
- ✅ All assumptions validated
- ✅ All design decisions locked
- ✅ All dependencies mapped

**Recommended Next Actions:**
1. Complete Pre-Prep in ~1 week
2. Execute Phase 00 in 2-3 days
3. Parallelize Phases 01-03 (10-15 days)
4. Execute Phase 04 (2-3 days)
5. MVP Launch

---

**Last Updated:** 2026-04-06 14:14
**Status:** ✅ All session deliverables complete. Ready for continuation.
