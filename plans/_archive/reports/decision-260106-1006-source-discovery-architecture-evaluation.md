# Source Discovery Architecture Evaluation

**Date:** January 6, 2026
**Status:** Decision Made - Option C Selected
**Context:** Evaluating multi-agent vs simpler approaches for human-quality source discovery

---

## Background

Following the Gemini Pivot (Jan 2026), user feedback indicated dissatisfaction with AI-discovered sources:
- "Sources wrong/irrelevant"
- "I already have my sources"
- "Stop finding sources for me"

The pivot addressed this by switching to URL-first video analysis. However, a question remained: **Could we build source discovery that matches human quality?**

---

## Original Proposal: Agentic Swarm

Proposed architecture using LangGraph/AutoGen:

```
┌─────────────────────────────────────────────────────────────┐
│                    DISCOVERY SWARM                          │
├─────────────────────────────────────────────────────────────┤
│  Scout Agent ──▶ Quality Assessor ──▶ Gap Finder ──┐       │
│       ▲                                             │       │
│       └─────────────────────────────────────────────┘       │
│                    (iterate until coverage)                  │
└─────────────────────────────────────────────────────────────┘
```

**Claimed benefits:**
- Iterative discovery (find gap → search → assess → repeat)
- Multi-perspective coverage (skeptic, expert, mainstream)
- Quality scoring with multiple signals
- Citation chain following

---

## Why Human Source Discovery is Better

| Human Capability | AI Limitation |
|------------------|---------------|
| "This YouTuber does deep dives" | Search API returns by keyword match |
| Follow citation chains | One-shot search, no iteration |
| Recognize expertise markers | Can't distinguish expert from amateur |
| Community validation | No social proof signals |
| Iterate based on findings | Static search, no follow-up |

---

## What Multi-Agent Would Actually Require

### APIs & Accounts

| Service | Purpose | Cost | Status |
|---------|---------|------|--------|
| YouTube Data API | Channel stats | Free | Have |
| Reddit API | Community mentions | Free | Have |
| SocialBlade API | Creator reputation | $20/mo | Need |
| Exa | Semantic search | ~$50/mo | Planned |
| Perplexity | Research queries | ~$20/mo | Have |

### Curated Data (Manual Work)

| Data Type | Volume | Maintenance |
|-----------|--------|-------------|
| Seed channels/niche | 10-20 per category | Quarterly |
| Seed subreddits/niche | 5-10 per category | Quarterly |
| Quality domains/niche | 10-15 per category | Quarterly |
| Blacklist | Ongoing | As discovered |

**Initial curation:** ~5 niches × ~30 seeds = 150 items
**Ongoing:** Quarterly reviews + blacklist updates

### Infrastructure Changes

| Component | Current | Needed |
|-----------|---------|--------|
| LangGraph | None | Add dependency |
| State persistence | Redis | Works |
| Checkpointing | None | Add for long jobs |
| Multi-agent orchestration | None | New code (~500-800 LOC) |

---

## Maintenance Burden Analysis

### What Goes Stale

| Item | Decay Rate | Impact |
|------|------------|--------|
| YouTube channels | Quarterly | Medium - bad recommendations |
| Subreddits | Years | Low |
| Quality domains | Years | Low |
| API rate limits | Unpredictable | High - breaks pipeline |
| LLM prompts | Per model update | Medium |

### Complexity Multipliers

| Aspect | Current (Linear Pipeline) | With Discovery Swarm |
|--------|---------------------------|---------------------|
| Code paths | 11 stages, predictable | 11 stages + 3 agents with loops |
| Error handling | Stage fails → skip | Agent fails → retry? abort? |
| Debugging | "Stage 6 failed" | "Agent B iteration 3 disagreed" |
| Testing | Mock stages | Mock agent interactions + state |
| Tuning | Adjust thresholds | Iteration limits, prompts, arbitration |

---

## Three Options Evaluated

### Option A: Build Discovery Swarm

**Implementation:**
- LangGraph state machine with Scout, Assessor, Gap Finder agents
- Iterative loops with convergence criteria
- Quality scoring model with multiple signals

**Pros:**
- Could match human discovery quality
- Handles edge cases dynamically
- Self-improving with iteration

**Cons:**
- 2-3 weeks development
- Ongoing maintenance (seed lists, prompt tuning, arbitration logic)
- Complex debugging
- High testing surface area
- Outcome uncertain ("might" match human quality)

**Verdict:** Technically feasible but high maintenance burden relative to uncertain value.

---

### Option B: Help Users Discover Better

**Implementation:**
- Chrome extension for source capture while browsing
- Better URL input UX (paste multiple, auto-metadata)
- Surface gaps ("no Reddit discussion found for this topic")
- Let users be Scout, we be Extractor

**Pros:**
- Leverages human judgment (proven superior)
- Low maintenance
- Clear value proposition

**Cons:**
- Chrome extension adds distribution complexity (Web Store approval)
- Users still do discovery work
- Doesn't solve "I don't know where to look"

**Verdict:** Good UX improvement but doesn't address discovery problem.

---

### Option C: Curated Source Packs ✅ SELECTED

**Implementation:**
- Pre-built "starter sources" per niche (50-100 total)
- User selects niche → system suggests 5-10 known-good sources
- User adds/removes before running
- Simple JSON config, no orchestration

**Pros:**
- Human-curated quality (guaranteed good)
- Minimal code (~100 LOC)
- Easy maintenance (quarterly JSON updates)
- Users can still add their own sources
- Solves "I don't know where to look" without complexity

**Cons:**
- Not dynamic (won't find breaking news sources)
- Limited to curated niches
- Requires initial curation effort

**Verdict:** 80% of value with 10% of complexity.

---

## Decision Matrix

| Criteria | Weight | Option A | Option B | Option C |
|----------|--------|----------|----------|----------|
| Development effort | 20% | 2 | 8 | 9 |
| Maintenance burden | 25% | 2 | 7 | 9 |
| Source quality | 30% | 7 | 8 | 8 |
| User experience | 15% | 6 | 7 | 8 |
| Risk/uncertainty | 10% | 3 | 7 | 9 |
| **Weighted Score** | | **4.4** | **7.5** | **8.6** |

---

## Why Option C Wins

### 1. Matches User Mental Model
Users think: "For true crime, I go to JCS, That Chapter, etc."
Option C: "Here are the best true crime sources. Pick which ones."

### 2. Guaranteed Quality
- Human-curated = known good
- No false positives from AI scoring
- No iteration needed

### 3. Minimal Maintenance
- JSON file with source lists
- Quarterly review (~2 hours)
- No API dependencies beyond existing
- No multi-agent debugging

### 4. Composable with URL-First
- User gets suggestions
- User adds their own sources
- System extracts from final list
- Best of both worlds

### 5. Reversible Decision
- If users want dynamic discovery later, Option C data becomes seed data for Option A
- No wasted work

---

## Implementation Sketch (Future)

```python
# backend/config/source_packs.py
SOURCE_PACKS = {
    "true_crime": {
        "name": "True Crime",
        "description": "Criminal cases, investigations, court proceedings",
        "youtube": [
            {"channel": "JCS - Criminal Psychology", "url": "...", "strength": "interrogation analysis"},
            {"channel": "That Chapter", "url": "...", "strength": "case summaries"},
            # ...
        ],
        "subreddits": ["UnresolvedMysteries", "TrueCrime", "TrueCrimeDiscussion"],
        "sites": ["longform.org/crime", "theintercept.com/series/"]
    },
    # ... other niches
}
```

```typescript
// Frontend: Niche selector with source suggestions
<NicheSelector
  onSelect={(niche) => {
    setSuggestedSources(SOURCE_PACKS[niche]);
    // User can toggle sources on/off
  }}
/>
```

---

## What We're NOT Building

- ❌ LangGraph multi-agent orchestration
- ❌ Dynamic quality scoring model
- ❌ Iterative gap detection loops
- ❌ SocialBlade integration
- ❌ Citation chain following
- ❌ Chrome extension (for now)

---

## Next Steps (When Ready)

1. **Curate initial source packs** - 5 niches, 10-15 sources each
2. **Add niche selector to dashboard** - Dropdown with suggestions
3. **Allow source toggle** - User enables/disables suggested sources
4. **Merge with URL input** - Suggestions + custom URLs combined

**Estimated effort:** 1-2 days (vs 2-3 weeks for Option A)

---

## Conclusion

The Agentic Swarm architecture is intellectually interesting but operationally burdensome. The core insight from the Gemini Pivot remains valid: **users know their sources better than AI can discover them.**

Option C (Curated Source Packs) delivers 80% of the value with 10% of the complexity by:
- Providing human-curated starting points
- Letting users customize before running
- Avoiding multi-agent orchestration entirely

This is the recommended path forward when source discovery features are prioritized.

---

## References

- Gemini Pivot Documentation: `docs/gemini-pivot-implementation.md`
- Strategic Pivot v3: `plans/strategic-pivot-jan-2026-v3-recalibrated.md`
- User Feedback Analysis: Referenced in pivot documentation
