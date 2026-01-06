# Vision: Full Research Assistant Pipeline

**Date:** January 6, 2026
**Status:** Vision Document - Pre-Implementation
**Context:** Extending Video Analysis Mode to deliver what a human research assistant actually provides

---

## Executive Summary

Research Agent should not just extract clips and quotes from videos. It should function as a **complete research assistant** that helps content creators at every stage of their workflow:

1. **Extract** usable content (clips, quotes, timestamps)
2. **Analyze** what makes the source content work (structure, style, sources)
3. **Critique** what's missing (gaps, perspectives, unanswered questions)
4. **Guide** further research (queries, source types, rabbit holes)

---

## The Problem We're Solving

Content creators (especially solo/small teams) spend the majority of their time on:

| Task | Time Spent | Pain Level |
|------|------------|------------|
| Finding sources | High | Medium (Google works) |
| Watching/analyzing sources | **Very High** | **High** |
| Breaking down what makes sources work | High | High |
| Identifying gaps in coverage | Medium | High |
| Finding structure for their own content | High | Very High |
| Doing additional research to fill gaps | High | Medium |

**The bottleneck is not finding sources.** Users can find videos on their topic. The bottleneck is:
- Processing those sources efficiently
- Understanding what makes them effective
- Identifying what's missing
- Knowing where to dig deeper

---

## The Human Research Assistant Model

When a content creator hires a human research assistant, they don't just get transcripts. They get:

| Deliverable | Description |
|-------------|-------------|
| **Raw Notes** | Key quotes, timestamps, usable clips |
| **Analysis** | "This video uses a villain origin story structure" |
| **Critique** | "They didn't interview any skeptics" |
| **Guidance** | "You should look into the 1982 Atlantic article they referenced" |

Our system should deliver the same.

---

## The Output Stack

### 1. ProducerPacket (Existing)
**Purpose:** Raw material for production

Contents:
- Clips with MM:SS timestamps
- Quotes with speaker attribution
- Claims with verification status
- Quality gate results

### 2. Content Blueprint (New)
**Purpose:** Understand what makes the source content work

Per video:
- **Hook Analysis:** How they grabbed attention (first 10-30 seconds)
- **Narrative Structure:** 3-act breakdown, story circle, or other framework
- **Re-engagement Points:** Where they placed "open loops" to retain viewers
- **Visual/Style Notes:** Pacing, editing style, tone
- **Source Tracing:** What primary sources they likely used
- **Key Techniques:** What makes this video effective

### 3. Gap Analysis (New)
**Purpose:** Identify what's missing across all provided videos

Cross-video analysis:
- **Missing Perspectives:** Who wasn't represented? (skeptics, victims, experts)
- **Unanswered Questions:** What would the audience naturally ask?
- **Coverage Blind Spots:** Topics mentioned but not explored
- **Contradictions:** Where sources disagree (opportunity for your content)

### 4. Research Starter (New)
**Purpose:** Actionable starting points for additional research

Contents:
- **Search Queries:** Exact terms to put into Google, Reddit, academic databases
- **Source Type Suggestions:** "Look for academic papers on X", "Find Reddit discussions about Y"
- **Rabbit Holes:** Interesting tangents mentioned in the videos worth exploring
- **Content Gaps to Fill:** What you could include that these videos missed

---

## Multi-Pass Architecture

```
User provides 3-5 YouTube URLs
         │
         ▼
┌─────────────────────────────────────┐
│  PASS 1: Extraction                 │
│  (Existing ProducerPacket flow)     │
│                                     │
│  Per video:                         │
│  - Extract clips with timestamps    │
│  - Extract quotes with speakers     │
│  - Extract claims                   │
│  - Verify against transcript        │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  PASS 2: Structure Analysis         │
│  (New - Content Blueprint)          │
│                                     │
│  Per video:                         │
│  - Analyze hook (first 30 sec)      │
│  - Identify narrative structure     │
│  - Note re-engagement techniques    │
│  - Trace likely primary sources     │
│  - Describe visual/editing style    │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  PASS 3: Gap Analysis               │
│  (New - Cross-Video Critique)       │
│                                     │
│  Across all videos:                 │
│  - Missing perspectives             │
│  - Unanswered questions             │
│  - Topics mentioned but unexplored  │
│  - Contradictions between sources   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  PASS 4: Research Starter           │
│  (New - Guidance for User)          │
│                                     │
│  Based on gaps:                     │
│  - Generate search queries          │
│  - Suggest source types             │
│  - Identify rabbit holes            │
│  - Recommend content angles         │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  FINAL OUTPUT                       │
│                                     │
│  - ProducerPacket (clips, quotes)   │
│  - Content Blueprint (per video)    │
│  - Gap Analysis (cross-video)       │
│  - Research Starter (action items)  │
└─────────────────────────────────────┘
```

---

## User Workflow Transformation

### Before (Creator Alone)
```
Watch 5 videos (10+ hours)
    ↓
Take notes manually
    ↓
Try to identify patterns/structure
    ↓
Realize you're missing perspectives
    ↓
Search for more sources
    ↓
Repeat
    ↓
= DAYS of work
```

### After (With Full Pipeline)
```
Provide 5 YouTube URLs
    ↓
Receive complete output in ~15-30 minutes
    ↓
Review ProducerPacket (clips you can use)
    ↓
Study Content Blueprint (understand what works)
    ↓
Check Gap Analysis (know what's missing)
    ↓
Follow Research Starter (targeted deep dives)
    ↓
= HOURS, not days
```

---

## Key Design Principles

### 1. Not Doing the Work FOR Them
We're not writing their script. We're:
- Extracting raw material
- Providing analysis and insight
- Identifying gaps
- Suggesting directions

The creative decisions remain with the creator.

### 2. Subjective Analysis is Okay
Structure analysis (3-act, story circle, etc.) is interpretive, not factual. That's fine because:
- It's a starting point for understanding, not a definitive answer
- Creators can disagree and form their own view
- The value is in prompting thinking, not being "correct"

### 3. LLMs Do What LLMs Do Best
- Processing large amounts of content quickly
- Identifying patterns across multiple sources
- Generating variations (search queries, angles)
- Summarizing and structuring information

Humans do what humans do best:
- Creative direction
- Final editorial judgment
- Unique perspective and voice

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time saved per project | 60-80% reduction in research phase |
| User satisfaction with gap analysis | "Found something I wouldn't have thought of" |
| Research Starter actionability | User follows at least 2-3 suggested queries |
| Content Blueprint usefulness | User references structure notes when outlining |

---

## What This Is NOT

- ❌ AI that writes the script for you
- ❌ Guaranteed "correct" analysis
- ❌ Replacement for creative judgment
- ❌ Automated video production

---

## Related Documents

- Gemini Pivot Implementation: `docs/gemini-pivot-implementation.md`
- Source Discovery Decision: `plans/reports/decision-260106-1006-source-discovery-architecture-evaluation.md`
- Strategic Pivot v3: `plans/strategic-pivot-jan-2026-v3-recalibrated.md`

---

## Next Steps

1. Explore current codebase structure
2. Design data models for new outputs
3. Design Gemini prompts for each pass
4. Plan API endpoints and frontend display
5. Implementation phases

---

*Vision document created: January 6, 2026*
