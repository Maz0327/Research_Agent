# Brainstorm Report: ADHD Creative Co-pilot Moat Strategy

**Date:** 2026-01-21
**Updated:** 2026-01-21 12:03 (added web research gaps + owner feedback)
**Session:** Product positioning & differentiation vs NotebookLM

---

## Problem Statement

Research Agent risks becoming obsolete as NotebookLM and competitors (Gistr, Ventress) expand capabilities. Need to identify defensible moat that doesn't over-complicate the product.

---

## Key Discovery: The Real User Problem

**Target user:** YouTube/podcast creators, especially those with ADHD

**Core pain points identified:**
- Paralysis — don't know where to start
- Overwhelm — too much info, can't process
- Distrust — don't trust summaries without raw access
- Missing spark — tools give info but not creative triggers
- Knowledge disconnection — "know things but need triggers to remind us"
- Narrative structure blindness — know 3-act structure exists but don't think to apply it

**Critical insight:**
> "We need a research assistant that does all the things our brains DON'T want to do... but we DO want to do the creative part and the learning about stuff part."

---

## Competitive Landscape

| Tool | Focus | Threat |
|------|-------|--------|
| [NotebookLM](https://paperguide.ai/blog/notebooklm-alternatives/) | General research + podcast generation | Medium |
| [Gistr](https://www.xda-developers.com/gistr-better-than-notebooklm-for-youtube-videos/) | YouTube highlights/moments (FREE) | High |
| [Ventress](https://ventress.app/blog/best-youtube-tools-2025/) | All-in-one YouTube workflow | High |
| [VidIQ/Subscribr](https://subscribr.ai/p/ai-youtube-script-writing) | AI scriptwriting + optimization | Medium |
| [LilysAI](https://lilys.ai/blog/en/best-10-notebooklm-alternatives-in-2025-100-personally-tested/) | Citation accuracy, source viewer | Low |

**Key competitive gap:** None are optimized for ADHD creators or offer narrative structure suggestions.

---

## Proposed Positioning

### From: "Research Tool"
### To: "Second Brain Without Executive Dysfunction"

**NotebookLM says:** "Here's everything about your sources"
**Research Agent says:** "Here's where to start, here's what nobody covered, and have you considered THIS narrative structure?"

---

## The Moat: Topic-Aware Creative Co-pilot

| ADHD Brain Weakness | System Compensates |
|---------------------|-------------------|
| Can't start (paralysis) | "Here's where to start" + one clear sentence |
| Doesn't trust summaries | Raw sources preserved (Doc 0) |
| Overwhelmed by processing | Does boring synthesis work |
| Wants creative control | Sparks ideas via triggers, doesn't dictate |
| Needs grounding | Everything traceable to source |
| Knows narrative structures but doesn't apply | Suggests "this could be a hero's journey" |

**Unique value:** System detects topic TYPE and suggests appropriate narrative structure:
- People stories → Hero's journey / character arc
- Mysteries/investigations → Tension/reveal structure
- Educational → Problem/solution/transformation
- Finance/complex → Teaching through storytelling

---

## Current System Assessment (Code Review)

### Strengths (Keep)
- Raw preservation (Doc 0) — Excellent
- Source attribution — Every claim traceable
- Gap detection — Exists, functional
- Jump Start (Doc 1) — Has "top 3 next steps"
- Cross-source analysis — Tensions, themes detected
- Validation — LLM Judge catches hallucinations
- 960 tests passing, mature error handling

### Gaps (Build)
| Missing | Impact | Priority |
|---------|--------|----------|
| No topic TYPE detection | Can't suggest narrative structures | **P1** |
| No narrative structure mapping | No 3-act, Dan Harmon suggestions | **P1** |
| Thin results (unknown cause) | Quality inconsistency | **P2** |
| Sequential processing (2-5 min) | Momentum killer | **P3** |
| No visual/spatial output | Text walls overwhelm | **P4 (defer)** |

### Technical Verdict
> **Foundation: 8/10** — Research synthesis is production-ready
> **ADHD-specific: 3/10** — Needs personalization layer ON TOP

**Recommendation:** Don't rebuild. Add creative co-pilot layer on top of solid core.

---

## Prioritized Roadmap

### Priority 1: Narrative Structure Detection + Suggestions
**Goal:** "This looks like a hero's journey — here's how your sources map to the 8 stages"

**Implementation approach:**
1. Add topic type classifier in synthesis stage
2. Map topic types to narrative structure templates
3. Add narrative suggestion field to Jump Start (Doc 1) or new section
4. Include "what if" prompts based on structure

**Narrative structures to support:**
- 3-Act (Setup/Conflict/Resolution)
- Dan Harmon's Story Circle (8 steps)
- Mystery/Reveal (tension → payoff)
- Problem/Solution/Transformation (educational)
- Character Arc (for people stories)

### Priority 2: Investigate Thin Results
**Goal:** Understand why some jobs produce sparse output

**Investigation approach:**
1. Review recent job logs for thin results
2. Correlate with source characteristics (length, type, count)
3. Review extraction prompts for edge cases
4. Test with controlled source sets

### Priority 3: Speed Optimization
**Goal:** Reduce 2-5 min to ~60s

**Implementation approach:**
1. Parallelize Gemini calls (currently sequential per architecture rule)
2. Keep isolation guarantee (separate calls, just concurrent)
3. Batch validation where possible

### Priority 4: Visual Output (Deferred)
**Goal:** Mind map / spatial view instead of text walls

**Note:** Can defer — text output acceptable for MVP if other priorities land.

---

## Additional Opportunities (Web Research — 2026-01-21)

### Approved for Implementation

| Feature | Description | Priority | Notes |
|---------|-------------|----------|-------|
| **Confidence Badges** | Surface existing confidence data in UI | Quick Win | Data already exists, UI-only change |
| **Batch Import** | Paste 10+ URLs, playlist URL support | Medium | NotebookLM pain point we can exploit |
| **Timestamp Surfacing** | Make Doc 0 timestamps more prominent | Quick Win | Already have data, better presentation |
| **Coverage Analysis** | "What's been covered vs gaps" | Medium | Partially exists, needs strengthening |

### Requires Design Work

| Feature | Description | Complexity | Notes |
|---------|-------------|------------|-------|
| **Script Export Booster** | New booster that synthesizes Doc 1 + Doc 3 → video script format | High | Must define exact output format, prompt, JSON schema. Cannot be thin. User-triggered post-job. |
| **External Fact-Check** | Button to verify claims via external service | Medium | Secondary process, user-triggered AFTER job success. No added time to main pipeline. |

### Deferred (Future)

| Feature | Reason |
|---------|--------|
| Progress celebrations | Low priority unless trivial to implement |
| Cross-project insights | Complicates system; defer until core moat lands |

### Rejected

| Feature | Reason |
|---------|--------|
| Modify Doc 0/1/2 format | Core documents are stable; add new outputs instead |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time to "I know where to start" | Unknown | < 60 seconds after job completes |
| User trust in output | Unknown | 80%+ say "I can verify this" |
| Creative spark triggered | Unknown | 70%+ say "this gave me an idea" |
| Processing time | 2-5 min | ~60s (with parallelization) |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Narrative suggestions feel forced | Make optional, show reasoning |
| Topic classification wrong | Provide override, show detected type |
| Over-engineering for niche | Start minimal, validate with real users |
| NotebookLM adds same features | Speed to market, ADHD-specific UX |

---

## Consolidated Next Steps

### Immediate (This Week)
1. **Investigate thin results** — Root cause before adding features
2. **Confidence badges** — Quick win, UI-only, data exists
3. **Timestamp surfacing** — Quick win, better Doc 0 presentation

### Design Phase
4. **Narrative structure module** — Schema, prompts, output format
5. **Script Export Booster spec** — Exact output format, prompt, JSON schema
6. **Coverage analysis strengthening** — Review current implementation, identify gaps

### Build Phase
7. **Topic type detection** — Prototype classifier accuracy
8. **Batch import** — Multi-URL paste, playlist support
9. **External fact-check integration** — Research providers, design trigger flow

### Validation
10. **User testing** — Validate with 3-5 ADHD creators before full build

---

## Unresolved Questions

### Original
1. How accurate can topic type detection be with limited context?
2. Should narrative suggestions be in Doc 1 (Jump Start) or new Doc 4?
3. What's the minimum viable "creative trigger" that feels valuable?
4. Is 60s processing fast enough, or do users need instant (~10s)?

### New (from additional features)
5. Script Export Booster: What sections? What tone? How detailed?
6. External fact-check: Which provider? ClaimBuster API? Google Fact Check API?
7. Batch import: Max URL count? How to handle mixed source types?
8. Coverage analysis: How do we determine "what's been covered" without web search?

---

## Decision Record

**ADR-017 (Proposed):** Pivot positioning from "research tool" to "ADHD creative co-pilot"

**Rationale:**
- NotebookLM/Gistr own generic research space
- ADHD creator niche is underserved
- Current architecture supports pivot (add layer, don't rebuild)
- Differentiation through narrative structure suggestions is unique

**Status:** Pending implementation planning

---

*Report generated from brainstorm session 2026-01-21*
