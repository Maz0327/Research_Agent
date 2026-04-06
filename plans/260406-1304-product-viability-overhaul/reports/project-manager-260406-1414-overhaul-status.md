# Product Viability Overhaul — Initiative Status

**Date:** 2026-04-06 14:14
**Initiative:** Product Viability Overhaul (11 phases)
**Status:** 🟡 Pre-Implementation Phase Complete. Ready for core MVP work.

---

## Initiative Overview

**Goal:** Transform Research Agent from prototype to market-ready product with single-screen UX, hero document, editorial polish, paywall, and advanced features.

**Positioning:** "Turn any collection of videos and articles into a verified, source-cited script — with the angle nobody else covered."

**Differentiators:**
- Verified facts (confidence scores + validation)
- Source citations (pills linking to sources)
- Untold angle (story angles generator)

**MVP Scope:** Single-screen input → Hero document → Sonnet editorial → Paywall
**Timeline:** 10-14 weeks total
**Current Phase:** Pre-Prep UX Foundation (prerequisite work)

---

## Prerequisite Work Status

### Pre-Prep UX Foundation Plan
**Location:** `plans/260406-1337-pre-prep-ux-foundation/`
**Purpose:** Fix design system debt before building new features
**Progress:** 3/7 complete (42.8%)

| Phase | Name | Status | Effort | Ready Next? |
|-------|------|--------|--------|-------------|
| PP-1 | Design Token Migration | ✅ Complete | 3-5d | — |
| PP-2 | Font & Type Scale | ✅ Complete | 1-2d | — |
| PP-3 | Creator Copy Rewrite | ✅ Complete | 2-3d | — |
| PP-4 | Citation Pills | ⏳ Pending | 1-2d | ✅ YES |
| PP-5 | Progress UX Polish | ⏳ Pending | 1-2d | ✅ YES |
| PP-6 | Iteration UX Redesign | ⏳ Pending | 2-3d | ✅ YES |
| PP-7 | First Impressions | ⏳ Pending | 2-3d | ✅ YES |

**Estimated Completion:** 1 week at current velocity
**Blocker Status:** Four remaining phases are dependency-free. Can execute in parallel if desired.

---

## Main Initiative Phases (Pending)

| Phase | Name | Status | Dependencies |
|-------|------|--------|---|
| 00 | Cleanup & Removals | ⏳ Pending | Pre-Prep complete |
| 01 | Single-Screen Input | ⏳ Pending | Phase 00 |
| 02 | Hero Document UX | ⏳ Pending | Phase 00 |
| 03 | Sonnet Editorial Pass | ⏳ Pending | Phase 00 |
| 04 | Paywall + Stripe | ⏳ Pending | Phases 01, 02 |
| 05 | SSE Streaming | ⏳ Pending | Phase 00 |
| 06 | Chat with Research | ⏳ Pending | Phase 02 |
| 07 | Quick Mode | ⏳ Pending | Phase 00 |
| 08 | Source Discovery | ⏳ Pending | Phase 07 |
| 09 | Gemini Multimodal Fallback | ⏳ Pending | Phase 00 |
| 10 | Credit System | ⏳ Pending | Phase 04 |

**MVP Scope (Phases 00-04):** ~2-3 weeks
**Full Scope (Phases 00-10):** ~10-14 weeks

---

## Research & Validation Completed

All key strategic decisions have been validated through dedicated research:

### ✅ Brainstorm Validation
**Report:** `plans/reports/researcher-260406-1233-brainstorm-validation.md`
- Technical feasibility confirmed
- Architecture decisions sound
- Cost projections validated

### ✅ Business Viability Analysis
**Report:** `plans/reports/researcher-260406-1252-business-viability-analysis.md`
- Market demand evidence
- Competitor analysis
- Pricing strategy validated ($19/mo sustainable)
- Breakeven at 6 paid users
- 65-70% gross margin at scale

### ✅ UX Patterns Research
**Report:** `plans/reports/researcher-260405-1552-ai-research-product-ux-patterns.md`
- Streaming UI patterns
- Progress feedback patterns
- Document viewer best practices
- Creator product UX benchmarks

### ✅ Pipeline Optimization Research
**Report:** `plans/reports/researcher-260405-1533-multi-model-pipeline-optimization.md`
- Multi-model strategy
- Quick mode cost justification
- Full mode architecture preservation

### ✅ Current State Audit
**Report:** `plans/reports/ui-ux-audit-260406-1329-current-state.md`
- Baseline UX score: 5.2/10
- 998 hardcoded colors identified and eliminated
- Engineer-speak terminology mapped to creator language
- Citation system identified as broken

---

## Key Decisions Locked In

### Product & Positioning
- **Tagline:** "Turn any collection of videos and articles into a verified, source-cited script — with the angle nobody else covered"
- **Differentiators:** Verified, source-cited, untold angle
- **MVP Value Prop:** Ship fast with core strength (narrative angle finding) + editorial polish
- **Theme:** Dark-only (no light mode in MVP)

### Pricing & Economics
- **Price Point:** $19/mo after 3 free jobs
- **Cost per Editorial Pass:** ~$0.045 (Sonnet 4.6)
- **Breakeven User Count:** ~6 users at $19/mo
- **Target Margin:** 65-70% at scale

### Architecture Invariants
- **Full Mode:** Per-source isolation PRESERVED (no breaking change to validated extraction method)
- **Quick Mode:** Single Gemini call with source labels (new, cost-optimized, not isolated)
- **Streaming:** Redis pub/sub between Celery and FastAPI (EventSource compatible)
- **Editorial Stage:** Sonnet 4.6 on Doc 2 (Research Brief) + Doc 5/6 (Script/Blog)

### MVP Feature List
1. Single-screen input wizard (topic + sources + mode)
2. Hero document (single combined view of all 4 core docs)
3. Sonnet editorial pass (story angle finding + prose improvement)
4. Paywall + Stripe integration ($19/mo)
5. SSE streaming for long-running jobs (already partially in place)

### Deferred Features
- Research Library (user knowledge base) — 2-3w
- Audio/podcast output (TTS) — 1-2w
- Collaboration/sharing — 2w
- Horizontal scaling — 1w
- Cross-user source caching — 3-5d
- Title/thumbnail suggestions — 3-5d

---

## Implementation Sequence

### Critical Path (MVP)
```
Pre-Prep (PP-4,5,6,7)  [1w]
    ↓
Phase 00: Cleanup [2-3d]
    ↓
Phases 01-03: Input/Docs/Editorial [10-15d] — Can run parallel
    ↓
Phase 04: Paywall/Stripe [2-3d]
    ↓
MVP LAUNCH
```

**Total MVP Timeline:** ~3-4 weeks after current session

### Extended Features (Post-MVP)
```
Phase 05: SSE Streaming [2-3w]
Phase 06: Chat [5-7d]
Phase 07-08: Quick Mode + Discovery [3w]
Phase 09: Gemini Multimodal [3-5d]
Phase 10: Credit System [1-2w]
```

---

## Team Context

**Main Agent:** Needs to complete Pre-Prep phases and orchestrate MVP phases.
**Subagents:** Ready to parallelize PP-4/5 or PP-6/7 simultaneously.
**Blockers:** None. All research done. Implementation ready to proceed.

---

## Success Criteria for Session 260406

✅ **ACHIEVED**
- Three Pre-Prep phases implemented (PP-1, PP-2, PP-3)
- Four remaining Pre-Prep phases unblocked
- All strategic research completed and validated
- Design system debt eliminated
- Creator language deployed
- Plan documents updated

✅ **READY FOR NEXT SESSION**
- PP-4, PP-5, PP-6, PP-7 (can start immediately)
- Phase 00 (Cleanup) — can start after Pre-Prep
- MVP phases — research locked in, ready to design

---

**Initiative Status:** 🟢 All prerequisites satisfied. Core MVP implementation ready to begin immediately after Pre-Prep completion.
