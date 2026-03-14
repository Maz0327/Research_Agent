# Sandcastles UX Deep Dive & Competitive Strategy
*Written: 2026-03-11 | Based on live exploration of app.sandcastles.ai*

---

## 1. What Sandcastles Actually Is

Sandcastles is a short-form video script generator for creators. Their positioning is "from idea to script in minutes." The core value prop: you don't need to do research, write hooks, or structure a script — Sandcastles does all of it from a topic input.

**Target user:** Entertainment/volume creators. People who post daily or multiple times a week. People optimizing for virality over accuracy. The UX assumes the user doesn't care where the info comes from — they just want something they can shoot.

**What Sandcastles is NOT:** A research tool. A fact-checking tool. A credibility tool. Sources are used internally and then discarded — they are never shown to the user.

---

## 2. Full App Structure (Explored Live)

### 2.1 Videos Feed
- Shows a feed of trending/viral short-form videos
- **Outlier Score**: A proprietary virality metric shown on every video (e.g., "8.2x outlier")
- **Engagement filters**: Can filter by views, engagement rate, topic category
- Purpose: Inspire creators, show what's performing

### 2.2 Ideas
- Topic suggestion engine
- Generates video ideas based on trends or a niche/channel description
- Ideas come pre-labeled with outlier scores and estimated engagement

### 2.3 Scripts (Main Product)
The core creation flow. 5 discrete steps:

**Step 1 — Topic**
- Free text input describing the video subject
- No source input, no URL input, no document upload
- Just: what do you want to make a video about?

**Step 2 — Research**
The most impressive part of Sandcastles. After entering a topic, the system:
- Runs internal research (takes ~30-36 seconds)
- Shows loading states that reveal the internal pipeline steps:
  - "Finding sources"
  - "Explaining how it works" (ELIS — Explain Like I'm...)
  - "Identifying trends"
  - "Explaining why it matters"
  - "Noting unanswered questions"
  - "Finalizing research report"

**The research output sections (observed live on dollar reserve currency topic):**
1. **Executive Summary** — 3-4 sentence overview with the "thesis"
2. **Key Context** — Historical background, why it matters now
3. **Key Facts** — Each fact formatted as: *Stat ▸ Analogy (Shock Score: X/10)*
4. **Interesting Stats And Findings** — Supplementary data points with shock scores
5. **Common Misconceptions Vs Reality** — Contrarian framing, each with shock score
6. **Analogies And Simple Comparisons** — Named concept → vivid plain-English comparison
7. **How It Works** — Process explanation in simple terms
8. **Real World Use Cases** — Named examples with specificity
9. **Major Trends** — Forward-looking bullet points
10. **Future Implications** — Optimistic / Realistic / Skeptical framings
11. **Potential Concerns And Downsides** — Counter-arguments
12. **Why It Matters** — Personal stakes, ties to viewer's life
13. **Video Angles** — 4-5 alternative titles/angles with shock scores
14. **Contrast Moments** — "Most believe X, the twist is Y" framings — these are gold for hooks
15. **Open Questions** — Unanswered threads that create curiosity/cliffhangers

**CRITICAL OBSERVATION:** The research brief is genuinely rich. But very little of this material makes it into the final script. The analogies, shock scores, contrast moments, and video angles all stay in the research view — the script generator largely ignores them.

**Step 3 — Hook**
- Shows 20+ hook templates, each labeled with:
  - Category (Question, Education, Secret Reveal, Contrarian, List, Personal Experience, Comparison)
  - Template format (e.g., "Have you ever wondered [X]?")
  - View count social proof (e.g., "233K views")
- Sandcastles fills in the template with the topic's specific content
- User picks their favorite — typically 2 options are pre-filled for the chosen topic
- This is template-driven, not organic. The "233K views" refers to the template format's performance, not this specific hook.

**Step 4 — Style**
9 video format options, each showing view count:
- Day In The Life (991K)
- Listicle 5 Steps (2M)
- Long Tutorial (1.2M)
- Rapid Tutorial (296K)
- Simple Tip (78K)
- Problem & Solution (626K)
- Case Study (1.4M)
- Personal Update (122K)
- Breakdown (1.4M)

Visual card selection with view counts as social proof. No description of what each style actually means structurally.

**Step 5 — Script**
- Generates in seconds after style selection
- Shows word count
- Has an "Apply edits" feature — you can highlight lines and request targeted changes
- Output is a continuous prose script (no shot notes, no B-roll suggestions, no timestamps)

### 2.4 Projects
- Organizes scripts into projects/collections
- Basic folder management

### 2.5 Exports
- Export scripts to various formats
- Can push to teleprompter apps

### 2.6 Channels (Followed Creators)
- Follow specific creators to track their content
- Used for the Videos feed inspiration

### 2.7 Settings
- Channel/niche setup
- API key management for integrations

---

## 3. The Full Example Run (Dollar Reserve Currency)

**Topic entered:** "Why the US dollar is losing its status as the world's reserve currency and what replaces it"

**Research generation time:** ~36 seconds

**Hook selected:** "Have you ever wondered what currency takes over when the dollar finally falls?" (Question | Have You Ever Wondered? template, 233K views)

**Style selected:** Breakdown (1.4M views)

**Final script output (174 words, complete):**

> "Have you ever wondered what currency takes over when the dollar finally falls? Well, it's already happening. The dollar's share of global reserves just hit a 25 year low at 56%. That's down from over 70% just two decades ago. And here's the thing, countries aren't just holding less dollars. They're actively building systems to avoid them entirely. There's this project called mBridge that lets countries trade directly with each other. No dollars, no US banks, nothing. And it's not some small experiment either. It's already processed 55 billion dollars worth of trade. So what's actually replacing the dollar? Well, it's not just one thing. Central banks are stocking up on gold like crazy, buying 863 tonnes last year alone. That's almost breaking records. But the real shift is happening in digital currencies and direct trade agreements. Countries are creating their own payment networks that completely bypass the dollar system. And honestly, once that infrastructure is built, there's no going back. The craziest part? Most people in the US have no idea this is even happening. But in 10 years, we might look back and realize the dollar's dominance ended without anyone noticing."

---

## 4. Script Analysis

### 4.1 How Human Does It Sound? **7.5/10**

**What works:**
- Natural spoken transitions: "Well," "And here's the thing," "honestly," "The craziest part?" — reads like a real person talking
- The three-word fragment — *"No dollars, no US banks, nothing."* — punchy and authentic
- "Well, it's not just one thing" avoids the AI move of immediately listing everything; mimics thinking out loud
- Hook-answer pattern (question → "Well, it's already happening") is clean and pulls you in

**AI tells / weak spots:**
- *"Most people in the US have no idea this is even happening"* — this exact pattern is in thousands of AI-generated finance scripts. Exhausted phrase.
- *"once that infrastructure is built, there's no going back"* — vague, slightly fatalistic, sounds templated
- The ending ("we might look back and realize...") is a good instinct but borrowed from a well-worn script format

### 4.2 How Good Is It as a Script? **6.5/10**

**Structure:**
Hook → Problem established → Specific example (mBridge) → Broader pattern (gold, digital currencies) → Cliffhanger ending. Clean and correct.

**The fatal flaw: it doesn't answer its own hook.**

The hook is *"what currency takes over?"* — and the script never answers this. It says "it's not just one thing" and gestures at gold and digital currencies, then ends on a cliffhanger. The viewer learns that something is happening but not what specifically replaces the dollar, what it means for their life, or what to do about it.

**Data density:** 5 data points in 174 words:
- 56% reserve share (25-year low)
- 70%+ two decades ago
- $55B processed by mBridge
- 863 tonnes of gold bought
- "In 10 years" timeline

Reasonable for short-form but much weaker than the research brief which had: mBridge 2,500x growth, gold at $4,600/oz, Poland as top public buyer, Digital Yuan at $2.4T, 89% of FX still USD, BRICS Unit 40% gold-backed — none of it made the script.

**What's missing entirely:**
- No story. No protagonist.
- No "here's what this means for your life" moment (the research brief had an excellent one about gas and iPhone prices)
- The mBridge-as-Discord-server analogy — in the research, not the script
- The "star athlete" comparison — in the research, not the script
- Any of the "Contrast Moments" from the research brief
- An actual answer to what replaces the dollar

**Best line in the script:**
*"The dollar's dominance ended without anyone noticing."* — cinematic, creates FOMO, genuinely memorable.

### 4.3 Key Structural Observation
Sandcastles generates a rich research brief with shock scores, analogies, contrast moments, and video angles — and then the script generator largely ignores them. The research view is better content than the script. This is a significant product weakness.

---

## 5. Sandcastles' Structural Weaknesses (Things We Can Exploit)

1. **Sources are invisible and discarded.** They're used internally, never shown to the user. No links, no credibility signals, no ability to verify. The user cannot cite anything.

2. **Scripts ignore the best research material.** The analogies, contrast moments, and shock-score facts from the research brief rarely appear in the final script.

3. **No fact verification.** The user has no way to know if any claim in the script is accurate. For serious creators, this is a liability.

4. **Template-driven hooks.** Every hook comes from a template library. Experienced viewers of short-form content recognize these patterns — they're increasingly stale.

5. **No control over sources.** Users can't bring their own sources, can't exclude unreliable ones, can't see where anything came from.

6. **Tone only, no structure.** The script is flat prose. No shot suggestions, no B-roll callouts, no section markers. You get words — not a production brief.

7. **Volume optimization, not quality.** Everything is designed for speed and daily volume. There's no path for a creator who wants to make one excellent, defensible, researched video per week.

---

## 6. Research Agent Competitive Positioning

**Sandcastles:** Ideas to scripts at volume, for entertainment creators, with no source visibility
**Research Agent:** Verified research to structured creator briefs, for serious/investigative creators, with full source traceability

**The user who chooses Research Agent** isn't trying to post every day. They're trying to build a reputation. They want to make a video about mBridge and not get destroyed in the comments by someone who actually knows the topic.

**Our core promise:** Everything in your script can be cited. Nothing you say on camera will embarrass you.

---

## 7. The Six Requirements Before Rebuilding Search

The user specified these before any search rebuild work begins:

1. **Clean codebase** — Audit for legacy/contaminating code before adding new functionality
2. **Keep skip-to-sources option** — Some users want to provide their own sources from the start, bypassing the search step entirely
3. **Relevance validation** — Search results must pass a quality/relevance check before being shown to the user. Not everything the search returns should flow through.
4. **Auto-flow approved sources into pipeline** — Once the user approves sources, they should automatically enter the current pipeline. No copy-pasting, no manual re-entry.
5. **Maintain data quality throughout** — Quality must be enforced at every stage, not just the beginning
6. **More polished output** — Current output is not intuitive or presentation-ready. This is a major problem.

---

## 8. The Target Output Format: Creator Brief

The output Research Agent produces should be a **Creator Brief** — structured like a shooting brief, not an academic document or a flat research dump.

### 8.1 Proposed Creator Brief Structure

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATOR BRIEF: [Topic]
Generated: [Date] | Sources: [N verified]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOOK OPTIONS (A/B)
  A) [Hook option 1] — why it works: [1 sentence]
  B) [Hook option 2] — why it works: [1 sentence]

THE SETUP
  [1-2 sentences: what problem you're solving for the viewer]

THE TWIST / CONTRAST MOMENT
  [The unexpected angle — derived from claim framing, contradiction analysis]
  "Most believe X. The reality is Y."

CORE FACTS (verified, cited)
  • [Fact 1] — say it like: "[plain English phrasing]" | Source: [link]
  • [Fact 2] — say it like: "[plain English phrasing]" | Source: [link]
  • [Fact 3] — say it like: "[plain English phrasing]" | Source: [link]
  (3-5 facts max — enough to be credible, not enough to overwhelm)

THE ANALOGY
  [One memorable comparison to make the core concept stick]
  e.g., "mBridge is like a private Discord server where countries trade money
  without the US watching."

WHAT THIS MEANS FOR YOU
  [Personal stakes — ties abstract topic to viewer's daily life]
  e.g., "If fewer countries need dollars, the US has to pay higher interest
  to borrow money. That hits gas prices, mortgage rates, everything."

CLIFFHANGER / OPEN LOOP ENDING
  [An unanswered question or forward-looking tension that keeps viewers
  thinking after the video ends]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCES (for your description box — not for on-screen)
  [1] [Title] — [URL] — Verified: [date]
  [2] [Title] — [URL] — Verified: [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CLAIMS FLAGGED AS DISPUTED OR SPECULATIVE
  ⚠ [Claim] — framing: speculative | speaker: [attribution]
  ⚠ [Claim] — framing: disputed | sources disagree on...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 8.2 Why This Format Wins

- Every fact is verified and cited — creator can defend every claim on camera
- Claims flagged as disputed are explicitly labeled — no accidental misinformation
- The brief is structured for production, not for reading — each section maps to a video section
- Sources go in the description box — credibility without cluttering the script
- The analogy and twist sections pull from the claim extraction enrichments (framing, significance, rhetorical type)
- Hooks are grounded in actual content, not templates

### 8.3 How v3 Claim Enrichments Power This

The claim extraction v3 enrichments (implemented and deployed) directly feed the Creator Brief:

| Brief Section | Powered By |
|---|---|
| Core Facts | `significance` field on each claim |
| The Twist | `framing: contradicts` + `related_claims` |
| Claimed by / attributed | `speaker` field |
| Disputed flags | `framing: disputed` or `framing: speculative` |
| Hook options | `tags`, high-significance claims |
| Cliffhanger | Claims with `framing: speculative` or open questions |

---

## 9. The "Best of Both Worlds" Summary

**Sandcastles gives you:** Narrative packaging, punchy structure, conversational voice, production-ready flow
**Sandcastles fails at:** Using its own best material, answering the hook it sets, connecting to viewer's life, source transparency

**Research Agent gives you:** Verified claims, citations, speaker attribution, rhetorical framing, disputed claim flags
**Research Agent fails at (currently):** Making output feel like content you can actually shoot

**The synthesis:**
Take Research Agent's data quality and source traceability. Wrap it in Sandcastles' presentation instincts. Produce a Creator Brief where every element that sounds engaging is also verifiably true — and the creator knows exactly which parts are solid and which parts are contested.

Sandcastles is producing content at scale for creators who want volume.
We should be producing briefs that make creators feel like they did actual research — because they did.

---

## 10. What We're Taking From Sandcastles (And Making Better)

### 10.1 Things We're Adopting

**1. Progressive Disclosure Flow**
- Sandcastles: Topic → Research → Hook → Style → Script (each step reveals the next)
- **Ours, better:** Topic → Source Discovery → User Approval → Pipeline → Creator Brief → (optional) Script. We add a **skip-to-sources entry point** — power users jump straight to providing their own URLs. Sandcastles forces everyone through the same funnel. We give two entry points depending on what the user already has.

**2. Narrated Loading States**
- Sandcastles: "Finding sources... Explaining how it works... Identifying trends..." instead of a spinner
- **Ours, better:** Same concept but we show **real pipeline stage names** with actual progress. "Extracting claims from 4 sources... 23 claims found... Detecting relationships..." — ours is honest because we actually have discrete pipeline stages (INGESTION → EXTRACTION → VALIDATION → SYNTHESIS → ASSEMBLY). Theirs is performative staging. Ours is real.

**3. Research Brief Sections (Shock Scores, Contrast Moments, Analogies, Video Angles)**
- Sandcastles: Generates these in the research view with engagement-scored facts
- **Ours, better:** We take the *concept* of these sections but ground them in verified claims. Their "Shock Score 9/10" is vibes — an LLM guessing what's surprising. Our significance scores and rhetorical framing come from actual source analysis via v3 claim enrichments. Their contrast moments are AI-generated fiction. Ours come from claims that genuinely contradict each other (`framing: disputed`, `related_claims: contradicts`). The difference: ours are real contradictions found in sources, not manufactured drama.

**4. Hook Options as Visual Cards**
- Sandcastles: 20+ hook templates with view-count social proof (e.g., "Have you ever wondered [X]?" — 233K views)
- **Ours, better:** Instead of templates, we generate hooks **from the actual high-significance claims**. "The hook writes itself when the data is shocking enough." We don't need a "Question | Have You Ever Wondered?" template library — we surface the most compelling verified fact and frame it as a question or statement. The hook options are unique to the content, not recycled formats.

**5. The "Why It Matters" / Personal Stakes Section**
- Sandcastles: Has it in the research view but drops it from the script (their script about dollar decline never mentions gas prices or mortgages even though the research brief did)
- **Ours, better:** This becomes a mandatory section in the Creator Brief — and it flows through to the script. We actually use the best material instead of generating it and throwing it away.

**6. Inline Edit / Targeted Changes**
- Sandcastles: Highlight lines of script and request targeted changes via "Apply edits"
- **Ours, later:** Same concept applied to the Creator Brief and eventually the Script. Highlight a fact and say "make this punchier" or "I want a different analogy here." This is a v2/v3 feature, not launch.

### 10.2 Things We're NOT Taking

1. **Template-driven hooks** — Their hook library is recognizable and getting stale. Experienced short-form viewers recognize "Have you ever wondered..." as a formula. We generate organically from claims.

2. **Style/format selection** — They offer 9 video styles (Listicle, Breakdown, Day In The Life, etc.). We don't dictate shooting format. The Creator Brief works regardless of how the creator chooses to shoot. The script writer (v2) will offer tone/length controls, not format templates.

3. **Invisible sources** — Their defining structural weakness. Sources are used internally and discarded. Users can't cite anything, can't verify anything, can't put links in their description box. We keep sources front and center — verified, dated, clickable.

4. **Flat prose script output** — They output a wall of continuous text. No section markers, no B-roll suggestions, no production cues. We output a structured Creator Brief with clear sections that map to video sections.

5. **Volume-first mentality** — Everything in Sandcastles optimizes for "make more videos faster." We optimize for "make one video you're proud of." Different user, different promise.

6. **Black box pipeline** — Users have zero control over sources, can't exclude unreliable ones, can't bring their own. Our pipeline gives the user control at the source approval step and offers skip-to-sources for power users.

### 10.3 Core Differentiators Table

| Dimension | Sandcastles | Research Agent |
|---|---|---|
| Sources | Hidden, disposable, unverifiable | Visible, verified, citeable, description-box ready |
| Claims | Unverified, AI-generated, no attribution | Extracted from sources, speaker-attributed, rhetorically framed |
| Output | Flat prose script | Structured Creator Brief (v1) → Script (v2) |
| Hooks | Template library with recycled formats | Generated from strongest verified claims |
| Disputed info | No awareness — presents everything as fact | Explicitly flagged with framing type and speaker |
| User control | Zero (black box, no source visibility) | Full (approve/reject sources, skip-to-sources, see everything) |
| Speed | ~2 min topic-to-script | Slower, but every claim is defensible |
| Best material usage | Research brief is rich; script ignores most of it | Creator Brief is built FROM the richest claims and relationships |
| Target user | Daily posters optimizing for volume | Weekly creators building reputation and authority |
| Core promise | "Ideas to scripts fast" | "Everything you say on camera can be cited" |

---

## 11. Document Architecture: Reconciling Doc 0/1/2 With the Layer Model

### 11.0 The Problem: Two Systems That Don't Map Cleanly

The existing pipeline produces three documents with internal names:
- **Doc 0: Source Ledger** — list of sources with metadata, quality scores, URLs
- **Doc 1: Jump-Start Directions** — quick actionable summary for the creator
- **Doc 2: Semantic Brief** — deep research document with key points, themes, tensions, claims

The new layer model proposes: Script (Layer 1), Creator Brief (Layer 2), Claims Document (Layer 3), Sources (Layer 4).

These need to be reconciled. The user also pointed out that the journey looks different depending on entry point — someone who comes through the search/research tool has a different document experience than someone who self-sources.

### 11.0.1 The Mapping: Old → New

**CORRECTION: Jump-Start Directions is NOT the Creator Brief.** Jump-Start is a *research navigation document* — it guides the user toward deeper research by providing search queries, topic directions, angles to explore, and what to look for next. It's a compass for further investigation, NOT a production document.

The Creator Brief is an entirely NEW document — a narrative content blueprint (like Sandcastles' output with Shock Scores, Contrast Moments, Video Angles, etc.) but grounded in verified Research Agent data.

| Document | Layer | Purpose | Status |
|---|---|---|---|
| Doc 0: Source Ledger | Layer 5: Sources | Raw receipts — URLs, verification dates, quality scores, processing status | **Stays as-is** |
| Doc 1: Jump-Start Directions | Layer 4: Research Navigation | Guides deeper research — search queries, topics to explore, angles, directions | **Stays as-is** |
| Doc 2: Semantic Brief | Layer 3: Claims/Research | Full research backbone — claims, themes, tensions, key points with enrichments | **Stays as-is** |
| **NEW — Doc 3: Creator Brief** | **Layer 2: Production Blueprint (HERO)** | **Narrative content blueprint — hook options, core facts phrased for delivery, the twist, analogies, personal stakes, cliffhanger. The production-ready document the creator actually uses to make their video.** | **NEW — must be built** |
| **NEW — Script** | **Layer 1: Spoken Word (v2)** | **Teleprompter-ready script generated FROM the Creator Brief. Includes tone/length/style controls. v2 feature.** | **v2 — future** |

**The key decision: The pipeline grows from 3 documents to 4.** Jump-Start keeps its role as a research compass. The Creator Brief is a new document that sits on top as the hero view — the thing the creator actually opens to plan their video. The pipeline now produces: Source Ledger → Jump-Start → Semantic Brief → Creator Brief.

### 11.0.2 How Entry Point Changes the Journey

The two entry points produce the same 4 documents, but the user's relationship with each document differs based on how they started.

**Entry Point A: Topic-First (Search/Research Tool)**

The user doesn't have sources. The system finds them. Jump-Start is HIGHLY relevant here because it can guide additional research rounds.

```
1. User enters topic
2. System searches & discovers sources
3. USER SEES: Source approval UI (card-based, approve/reject each)
   └─ This is a UI interaction, NOT a document
   └─ The user is actively curating before the pipeline runs
4. Approved sources enter pipeline
5. Pipeline runs (narrated loading states)
6. Pipeline produces:
   ├─ Doc 0 (Source Ledger) → Layer 5: receipts
   ├─ Doc 1 (Jump-Start Directions) → Layer 4: research compass
   ├─ Doc 2 (Semantic Brief) → Layer 3: deep research
   └─ Doc 3 (Creator Brief) → Layer 2: HERO
7. User lands on: Creator Brief (HERO VIEW)
```

In this flow, Jump-Start has extra value — if the user isn't satisfied with the research depth, they can open Jump-Start to see "here's what else to search for, here are angles you haven't covered yet." They can then run another research round, add sources, and re-enrich the pipeline. The Creator Brief is still the hero landing, but Jump-Start is the "go deeper" escape hatch.

**Entry Point B: Sources-First (Current Flow / Skip-to-Sources)**

The user already has their URLs or documents. Jump-Start is less critical here because the user already knows their sources — but it still has value for identifying gaps.

```
1. User pastes URLs / uploads documents
2. Sources auto-validated for accessibility (can we reach them? are they readable?)
3. NO approval step — the user brought their own, they trust them
4. Pipeline runs immediately (narrated loading states)
5. Pipeline produces:
   ├─ Doc 0 (Source Ledger) → Layer 5: receipts
   ├─ Doc 1 (Jump-Start Directions) → Layer 4: research compass
   ├─ Doc 2 (Semantic Brief) → Layer 3: deep research
   └─ Doc 3 (Creator Brief) → Layer 2: HERO
6. User lands on: Creator Brief (HERO VIEW)
```

In this flow, the user skips source approval (they trust their own sources). Jump-Start could still suggest "your sources cover X but not Y — here are queries to fill the gap." But it's secondary. The Creator Brief is the hero.

**After the pipeline completes, both paths converge to the same hero view.** The Creator Brief is the landing page regardless of how you got there.

### 11.0.3 Document Access From the Hero View (Both Entry Points)

Once the user is looking at the Creator Brief, the navigation is identical regardless of entry point:

```
┌──────────────────────────────────────────────────────┐
│              CREATOR BRIEF (hero view)                │
│              Doc 3 / Layer 2 — Production Blueprint   │
│                                                       │
│  ┌─────────────┐  ┌───────────────┐  ┌────────────┐ │
│  │View Research │  │  Go Deeper    │  │View Sources│ │
│  │  (Layer 3)   │  │  (Layer 4)    │  │ (Layer 5)  │ │
│  │  Semantic    │  │  Jump-Start   │  │  Source    │ │
│  │  Brief       │  │  Directions   │  │  Ledger   │ │
│  └─────────────┘  └───────────────┘  └────────────┘ │
│                                                       │
│  Hook Options...                                      │
│  Core Facts (click any → see claim detail)...         │
│  The Twist...                                         │
│  The Analogy...                                       │
│  What This Means For You...                           │
│  Cliffhanger...                                       │
│                                                       │
│              ┌──────────────────┐                     │
│              │ Generate Script  │  (v2)               │
│              │    (Layer 1)     │                      │
│              └──────────────────┘                     │
└──────────────────────────────────────────────────────┘

"View Research" → Semantic Brief (Doc 2 / Layer 3)
  └─ All claims with enrichments, themes, tensions, key points
  └─ The full research backbone
  └─ Click any source reference → jumps to Source Ledger

"Go Deeper" → Jump-Start Directions (Doc 1 / Layer 4)
  └─ Search queries to run for more depth
  └─ Topic angles not yet covered
  └─ Directions for further investigation
  └─ Gap analysis: "your sources cover X but not Y"
  └─ For Entry Point A: especially valuable — guides additional research rounds
  └─ For Entry Point B: still useful for identifying blind spots

"View Sources" → Source Ledger (Doc 0 / Layer 5)
  └─ All URLs, verification dates, quality scores
  └─ For Entry Point A: shows which sources were approved/rejected
  └─ For Entry Point B: shows what was provided and processing status

Click any fact in the Brief → inline expansion or slide-over
  └─ Shows the specific claim from Layer 3
  └─ Speaker attribution, rhetorical framing, significance
  └─ Related claims (supports, contradicts, qualifies)
  └─ Direct link to the source in Layer 5

"Generate Script" → v2 feature
  └─ Tone/length/style picker → spoken-word output (Layer 1)
```

### 11.0.4 What the User NEVER Sees

- The internal names "Doc 0", "Doc 1", "Doc 2", "Doc 3" — these are pipeline internals
- A tab bar with 4-5 tabs — documents are accessed through contextual navigation from the hero view, not a tab picker
- All documents at once — one layer at a time, always
- A document they didn't ask for — the Creator Brief is the default landing, everything else is opt-in drill-down
- Raw JSON, claim IDs, or pipeline metadata — all of that stays in the backend

### 11.0.5 The Document Hierarchy (Corrected)

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Script (what you say on camera)            │  ← Top layer, simplest, v2
├─────────────────────────────────────────────────────┤
│  Layer 2: Creator Brief (narrative production guide) │  ← HERO document (NEW Doc 3)
├─────────────────────────────────────────────────────┤
│  Layer 3: Semantic Brief (verified facts + context)  │  ← Deep research (Doc 2)
├─────────────────────────────────────────────────────┤
│  Layer 4: Jump-Start (research compass)              │  ← Go deeper guide (Doc 1)
├─────────────────────────────────────────────────────┤
│  Layer 5: Source Ledger (raw material + links)       │  ← Receipts (Doc 0)
└─────────────────────────────────────────────────────┘
```

**Important distinction:**
- Layers 3-5 are RESEARCH documents (they serve the investigation)
- Layer 2 is a PRODUCTION document (it serves the video)
- Layer 1 is a DELIVERY document (it IS the video, spoken)

The Creator Brief is the bridge between research and production. Everything below it is "show your work." Everything above it is "do your work."

---

## 11.1 The Visual Layer Model

### 11.1.1 The Problem
The pipeline now generates 4 documents (5 with the v2 script). If we dump all of these on the user, it's overwhelming and confusing. A tab bar with 4-5 tabs is a wall of information that kills the progressive disclosure UX we're trying to build.

### 11.1.2 The Solution: Layers, Not Tabs

Think of it like Google Maps. You see the map (the Creator Brief). You can zoom into street view (the Semantic Brief). You can check directions for more exploration (Jump-Start). You can toggle satellite (the Sources). But you never see all layers at once.

```
┌─────────────────────────────────────────────────┐
│  LAYER 1: Script (what you say on camera)       │  ← Top layer, simplest, spoken-word prose
│           Generated FROM the Creator Brief      │
│           v2 feature — not in initial build      │
├─────────────────────────────────────────────────┤
│  LAYER 2: Creator Brief (production blueprint)  │  ← HERO DOCUMENT — user lands here
│           Hook options, core facts for delivery, │
│           the twist, analogy, personal stakes,   │
│           cliffhanger. Narrative-first format.   │
│           Every element clickable → Layer 3      │
│           NEW Doc 3 — must be built              │
├─────────────────────────────────────────────────┤
│  LAYER 3: Semantic Brief (verified research)    │  ← Deep research — the backbone (Doc 2)
│           All extracted claims with enrichments  │
│           Speaker, framing, significance, tags   │
│           Relationships between claims           │
│           Themes, tensions, key points           │
├─────────────────────────────────────────────────┤
│  LAYER 4: Jump-Start Directions (go deeper)     │  ← Research compass (Doc 1)
│           Search queries for more depth          │
│           Topic angles not yet covered           │
│           Gap analysis and directions            │
│           Especially useful for Entry Point A    │
├─────────────────────────────────────────────────┤
│  LAYER 5: Source Ledger (raw material + links)  │  ← Receipts — proves everything (Doc 0)
│           URLs, verified dates, quality scores   │
│           What was approved, what was rejected    │
└─────────────────────────────────────────────────┘
```

**How the user experiences this:**
- After pipeline completes → user lands on **Layer 2 (Creator Brief)** by default
- From the Creator Brief:
  - **Up / "Generate Script"** → Layer 1 (v2 feature, requires tone/length/style selection)
  - **Click any fact** → Layer 3 inline (shows the specific claim, its source, its framing, its speaker)
  - **"View Research"** → Layer 3 full view (complete Semantic Brief with all claims, themes, tensions)
  - **"Go Deeper"** → Layer 4 (Jump-Start Directions — search queries, angles, gaps to explore)
  - **"View Sources"** → Layer 5 (full source ledger with URLs and verification dates)
- The user sees ONE document at a time with clear navigation to go deeper or move forward
- No tab overload, no sidebar clutter, no document picker confusion
- Jump-Start lives in the "research" zone — it's the tool for going back to investigate more, not for producing content

### 11.1.3 Two Access Models: Contextual Navigation vs. Document Drawer

**IMPORTANT: The layer navigation is NOT a restriction. It's the recommended path.** The user always has direct access to every document the pipeline produced.

There are two ways to access documents:

**A. Contextual Navigation (from the hero view)**
This is the guided path described above — "View Research," "Go Deeper," "View Sources," "Generate Script." It's designed for progressive disclosure, leading the user naturally from production → research → sources.

**B. Document Drawer (always available)**
A persistent, collapsible sidebar or drawer that lists ALL pipeline documents by their actual names. The user can jump directly to any document at any time, regardless of which layer they're currently viewing.

```
┌──────────────────────────────┐
│  📄 Documents                 │
│  ──────────────────────────── │
│  CORE (auto-generated)        │
│  ★ Creator Brief  (Doc 3)    │  ← hero badge / default
│    Semantic Brief (Doc 2)    │
│    Jump-Start     (Doc 1)    │
│    Source Ledger   (Doc 0)    │
│  ──────────────────────────── │
│  OPTIONAL                     │
│    Producer Packet (Doc 4)   │  ← greyed if not generated
│  🔒 Script         (Doc 5)   │  ← locked until v2
└──────────────────────────────┘
```

**Why both access models matter:**
- **New users** follow the contextual navigation — it teaches them the system through progressive disclosure
- **Power users** go straight to the document drawer — they know what they want and don't need guided pathways
- **Returning users** might jump to Jump-Start first (to check what research gaps remain) or go straight to Source Ledger (to verify a specific URL)
- **No document is hidden** — everything the pipeline produces is always one click away

**The document drawer is NOT a tab bar.** It's a list in a collapsible sidebar. It doesn't clutter the main view. The hero (Creator Brief) always occupies the full content area. The drawer is supplementary navigation, not primary UI.

### 11.1.4 Everything Stays Grounded in the Doc 0/1/2/3 System

**CRITICAL PRINCIPLE: The Doc 0, 1, 2, 3 numbering system is the backbone. The layer model, contextual navigation, and document drawer are all PRESENTATION layers on top of this system — they do not replace it.**

The pipeline produces documents in a fixed order with fixed internal identifiers:

```
Pipeline Stage Output:

CORE (auto-generated, every job):
  INGESTION    → Doc 0: Source Ledger
  SYNTHESIS    → Doc 1: Jump-Start Directions
  SYNTHESIS    → Doc 2: Semantic Brief
  ASSEMBLY     → Doc 3: Creator Brief (NEW)

OPTIONAL (user-triggered, gated):
  PRODUCER     → Doc 4: Producer Packet (requires 4+ sources, 1 HIGH confidence)
  (v2: SCRIPT) → Doc 5: Script (generated from Doc 3)

ITERATE SYSTEM (post-pipeline refinement, all modes under one umbrella):
  deep_dive        → Appends to Doc 1 (creates new version)
  expand_sources   → Re-runs pipeline with new sources (new versions of Doc 0-3)
  deeper           → Re-extracts with deeper prompts (new versions of Doc 0-3)
  different_angle  → Re-synthesizes with angle focus (new versions of Doc 1-3)
  custom           → Re-synthesizes with user instructions (new versions of Doc 1-3)
```

**Why this matters:**
- **Backend code** always references Doc 0, Doc 1, Doc 2, Doc 3. These are the canonical identifiers in the database, the API responses, and the storage layer. The frontend can call them whatever it wants in the UI — "Source Ledger," "Research Compass," "Deep Research," "Creator Brief" — but the underlying system always knows them as Doc 0/1/2/3.
- **Provenance chain is unbroken.** Every fact in Doc 3 (Creator Brief) traces back to a claim in Doc 2 (Semantic Brief), which traces back to a source in Doc 0 (Source Ledger). The Doc numbering IS the provenance order — lower numbers are closer to the raw source material, higher numbers are closer to the production output.
- **The layer model is a VIEW, not a data model.** Layer 2 (Creator Brief) doesn't store its own copy of claims — it references claims from Doc 2. Layer 4 (Jump-Start) doesn't store its own copy of sources — it references sources from Doc 0. The documents are interconnected, not independent silos.
- **New documents always get the next Doc number.** The system is extensible. The numbering grows linearly with the pipeline.
- **API and database schema stays clean.** A job has `documents: [Doc0, Doc1, Doc2, Doc3]` for core docs. Optional docs (Doc 4+) are stored separately under optional/user-triggered artifacts.

#### The Complete Document Registry

**CORE DOCUMENTS (Doc 0–3) — Auto-generated, every job gets them:**

| Doc # | Name | Purpose | Generated By |
|---|---|---|---|
| Doc 0 | Source Ledger | Raw receipts — URLs, quality scores, verification dates, processing status | INGESTION stage |
| Doc 1 | Jump-Start Directions | Research compass — search queries, topic angles, gaps, directions for deeper investigation | SYNTHESIS stage |
| Doc 2 | Semantic Brief | Full research backbone — claims, key points, themes, tensions with enrichments | SYNTHESIS stage |
| Doc 3 | Creator Brief | Narrative content blueprint — hook options, core facts for delivery, twist, analogies, personal stakes, cliffhanger. The hero document. | ASSEMBLY stage (NEW) |

**OPTIONAL DOCUMENTS (Doc 4+) — User-triggered, require gating:**

| Doc # | Name | Purpose | Trigger |
|---|---|---|---|
| Doc 4 | Producer Packet | Production planning — narrative angles, structure options, act breakdowns, B-roll suggestions, interview targets, thumbnail concepts, risk assessment. For serious filmmakers/documentary producers. | User-triggered, requires 4+ sources and 1 HIGH confidence source |
| (future) Doc 5 | Script | Teleprompter-ready spoken-word prose generated from Doc 3. Tone/length/style controls. Voice mimicry option. | User-triggered from Creator Brief (v2 feature) |
| (future) Doc 6+ | TBD | Social Media Kit, Blog Post, Thread Writer, etc. | TBD |

**ITERATE SYSTEM (post-pipeline refinement — all modes consolidated under one system):**

Iterate is the single umbrella for ALL post-pipeline refinement. No more separate Booster/Addendum/Iterate concepts — they're all modes within one system, one API endpoint, one storage pattern.

| Mode | Old Name | What It Does | Documents Affected |
|---|---|---|---|
| `deep_dive` | Booster | Gap analysis → research directions → appends to Doc 1 | Doc 1 only (new version) |
| `expand_sources` | Addendum + old more_sources | Add new sources → re-run pipeline → new doc versions | Doc 0, 1, 2, 3 (new versions) |
| `deeper` | Iterate: deeper | Re-extract existing sources with deeper, more granular prompts → re-synthesize | Doc 0, 1, 2, 3 (new versions) |
| `different_angle` | Iterate: different_angle | Re-synthesize same data with a specific angle/perspective focus | Doc 1, 2, 3 (new versions, Doc 0 unchanged) |
| `custom` | Iterate: custom | Re-synthesize with user's custom instructions/prompt | Doc 1, 2, 3 (new versions, Doc 0 unchanged) |

**Why consolidation matters:**
- One API endpoint: `POST /{job_id}/iterate` with a `mode` field
- One storage pattern: `jobs/{job_id}/iterations/{iteration_id}/`
- One versioning system: each iteration creates new doc versions (see 11.2.4)
- One mental model for the user: "I want to improve my research" → pick a mode
- Backend code: one task dispatcher, mode-specific handlers

**The split is clean:**
- **Doc 0–3 are the foundation.** Every user gets them. They're auto-generated by the pipeline. No gating, no extra cost decision.
- **Doc 4+ are premium/optional layers.** They require user intent, may have gating requirements, and add cost. The user chooses to generate them.
- **Iterate modes are not documents — they're refinement operations.** They create new versions of existing docs rather than new document types.

```
Data flow (grounding chain):

Doc 0 (Source Ledger)
  │ URLs, quality scores, verification dates
  │
  ├──▶ Doc 1 (Jump-Start Directions)
  │     References Doc 0 sources to identify gaps
  │     "You have coverage on X from SRC_1, SRC_3 but nothing on Y"
  │
  ├──▶ Doc 2 (Semantic Brief)
  │     Every claim, key point, theme traces to source_ids in Doc 0
  │     Full enrichments: speaker, framing, significance, relationships
  │
  └──▶ Doc 3 (Creator Brief)  ← NEW, auto-generated
  │     Every hook option, core fact, twist, analogy traces to
  │     specific claims in Doc 2, which trace to sources in Doc 0
  │     THE CHAIN IS NEVER BROKEN
  │
  └──▶ Doc 4 (Producer Packet)  ← OPTIONAL, user-triggered
  │     Story angles, structure, B-roll, risk — all reference Doc 2 claims
  │     and Doc 0 sources. Creative layer on top of research.
  │
  └──▶ Doc 5 (Script)  ← FUTURE v2, user-triggered
        Every sentence traces to a section in Doc 3,
        which traces to Doc 2, which traces to Doc 0
```

**The rule: No document can contain a fact that doesn't trace back through the chain to Doc 0.** If it can't be sourced, it doesn't belong in the output. This is what separates us from Sandcastles — their script has no chain at all. Ours has an unbroken one from spoken word all the way back to the original URL.

**NOTE: This changes the existing architecture rules.** The current `architecture.md` defines Doc 0/1/2 as core, Doc 3 as Producer Packet (optional), and Booster/Addendum as separate concepts. The new architecture is:
- Rule 12 update: Four Core Documents (Doc 0–3), with Doc 3 now being Creator Brief (auto-generated)
- Rule 13 update: Optional Documents start at Doc 4 (Producer Packet moves from Doc 3 → Doc 4). Booster and Addendum are retired as separate concepts — they become `deep_dive` and `expand_sources` modes within the consolidated Iterate system.
- This requires updating `architecture.md`, `Document_Output_Format.md`, and any backend code that references Doc 3 as Producer Packet or Booster/Addendum as standalone systems

### 11.2 The Iterate System: Consolidated Post-Pipeline Refinement

#### 11.2.1 What Iterate Is

Iterate is the **single umbrella system** for all post-pipeline refinement. Previously, the codebase had three separate concepts (Booster, Addendum, Iterate modes) doing overlapping things. They are now consolidated into one system with 5 modes.

**One API endpoint.** `POST /{job_id}/iterate` with a `mode` field.
**One storage pattern.** `jobs/{job_id}/iterations/{iteration_id}/`
**One versioning system.** Each iteration creates new doc versions (see 11.2.4).
**One mental model.** "I want to improve my research" → pick a mode.

#### 11.2.2 The Five Iterate Modes

**Mode 1: `deep_dive`** (formerly Booster)
- **Purpose:** Find research gaps and generate directions for deeper investigation
- **Action:** Analyzes existing Doc 0/1/2, identifies blind spots, generates search queries/directions
- **Output:** Appends "Deep Research Expansion" section to Doc 1 (Jump-Start)
- **Docs affected:** Doc 1 only (new version)
- **Key constraint:** Produces DIRECTIONS, never FACTS. Tells you WHERE to look, not WHAT you'll find. Enforced by prompt rules and post-generation validation.
- **Input is constrained:** Context Bundle from Doc 0/1/2 contains only labels, summaries, and gap descriptions — no raw text, no quotes, no source URLs. Prevents hallucinating facts.
- **Output is grounded:** Every suggestion must reference a valid `gap_id` or `theme_id`. Ungrounded suggestions rejected.
- **Failure is safe:** If deep_dive fails, all docs remain unchanged. User sees "unavailable" and can retry.

**Mode 2: `expand_sources`** (formerly Addendum + old more_sources)
- **Purpose:** Add new sources and re-run the full pipeline
- **Action:** New sources (discovered via search or provided by user) enter the pipeline. Full re-extraction, re-synthesis, re-assembly.
- **Output:** New versions of Doc 0, 1, 2, 3
- **Docs affected:** All core docs (new versions)
- **Key point:** This is the mode triggered when a user follows deep_dive suggestions, finds new sources, and approves them. Also triggered when a user manually adds sources to an existing job.

**Mode 3: `deeper`** (unchanged from old Iterate)
- **Purpose:** Re-extract existing sources with deeper, more granular prompts
- **Action:** Reconstructs source packages from baseline Doc 0. Re-extracts each source focusing on examples, statistics, named entities, causal relationships, counterarguments. Re-synthesizes.
- **Output:** New versions of Doc 0, 1, 2, 3
- **Docs affected:** All core docs (new versions)
- **Key point:** Same sources, deeper extraction. Good when the user feels the data is there but the pipeline didn't dig deep enough the first time.

**Mode 4: `different_angle`** (unchanged from old Iterate)
- **Purpose:** Re-synthesize baseline data with a specific angle/perspective
- **Action:** Does NOT re-extract. Uses baseline extractions. Re-runs gap analysis and synthesis with angle context.
- **Output:** New versions of Doc 1, 2, 3 (Doc 0 unchanged — same sources)
- **Docs affected:** Doc 1, 2, 3 (new versions)
- **Key point:** Same data, different lens. "Show me this from an economic perspective" or "Focus on the environmental angle."

**Mode 5: `custom`** (unchanged from old Iterate)
- **Purpose:** Re-synthesize with user's custom instructions
- **Action:** Does NOT re-extract. Appends user prompt to topic context. Re-runs synthesis.
- **Output:** New versions of Doc 1, 2, 3 (Doc 0 unchanged)
- **Docs affected:** Doc 1, 2, 3 (new versions)
- **Key point:** Freeform user control. "Focus more on the historical context" or "Emphasize the counter-arguments."

#### 11.2.3 How Iterate Fits the User Journey

The Iterate system is a **feedback loop**, not a linear pipeline step:

```
INITIAL RUN:
  Topic/Sources → Pipeline → Doc 0, Doc 1, Doc 2, Doc 3 (v1.0)
                                                    │
  User reviews Creator Brief (Doc 3)                │
  Decides they want to refine                       │
                                                    ▼
ITERATE MENU (one system, pick a mode):
  ┌─────────────────────────────────────────────────┐
  │  How would you like to improve your research?   │
  │                                                  │
  │  🔍 Deep Dive — Find gaps, get search directions │
  │  ➕ Expand Sources — Add more sources            │
  │  🔬 Go Deeper — Re-extract with more detail      │
  │  🔄 Different Angle — Same data, new perspective  │
  │  ✏️  Custom — Your own instructions               │
  └─────────────────────────────────────────────────┘
                        │
         (user picks a mode)
                        │
                        ▼
  Iteration runs → New doc versions created
  User lands on updated Creator Brief
  Previous versions preserved (see 11.2.4)
  Cycle can repeat as many times as needed
```

**The deep_dive → expand_sources loop (the most common flow):**

```
Step 1: User triggers deep_dive
  → Doc 1 gets new version with research directions
  → User sees suggested queries and gap analysis

Step 2: User follows suggestions, discovers new sources
  → Sources go through approval (Entry Point A)
  → OR user pastes new URLs directly (Entry Point B)

Step 3: User triggers expand_sources with the new sources
  → Full pipeline re-run with expanded source set
  → Doc 0, 1, 2, 3 all get new versions
  → Creator Brief is now richer and deeper

Step 4: User reviews, decides if they want another round
  → Can deep_dive again, go deeper, try a different angle, etc.
```

#### 11.2.4 Document Versioning (4-Version Rolling Window)

**When documents get re-generated (via any Iterate mode), the system retains up to 4 versions: the latest + 3 previous.**

```
Version retention per document:

Doc 0 (Source Ledger):
  v1.0 — initial sources (3 approved)
  v2.0 — after expand_sources (5 approved, 2 new)          ← kept
  v3.0 — after deeper re-extraction (same 5 sources)       ← kept
  v4.0 — after expand_sources round 2 (7 approved, 2 new)  ← kept
  v5.0 — after expand_sources round 3 (9 approved, 2 new)  ← LATEST
  v1.0 → DROPPED (exceeded 4-version window)

Same pattern for Doc 1, Doc 2, Doc 3 independently.
```

**Versioning rules:**

1. **Each document is versioned independently.** Doc 0 might be on v3.0 while Doc 3 is on v2.0 (if the Creator Brief was only regenerated twice).

2. **Rolling window: latest + 3 previous = 4 total.** When a 5th version is created, the oldest is dropped. This caps storage and prevents infinite accumulation.

3. **Versions are immutable.** Once a version is created, it's never modified. If Doc 1 gets a Booster expansion, that creates v2.0 of Doc 1 — v1.0 remains untouched.

4. **The user always sees the latest version by default.** Previous versions are accessible via a version selector in the document viewer.

5. **Version metadata is stored per version:**
   ```
   {
     "version": "2.0",
     "created_at": "2026-03-11T14:30:00Z",
     "trigger": "iterate:expand_sources",  // or "iterate:deep_dive", "iterate:deeper", "iterate:different_angle", "iterate:custom", "initial"
     "source_count": 5,
     "claim_count": 34,
     "diff_summary": "+2 sources, +11 claims, +1 theme"
   }
   ```

6. **Diff summaries between versions.** Each version stores a brief summary of what changed from the previous version. This lets the user understand WHY a new version exists without reading both.

**How versioning appears in the UI:**

```
┌──────────────────────────────────────────────────────┐
│  CREATOR BRIEF                          v3.0 ▾      │
│  ──────────────────────────────────────────────────── │
│  Topic: Why the US dollar is losing...               │
│  Sources: 7 | Claims: 45 | Updated: Mar 11, 2026    │
│                                                       │
│  [Document content...]                                │
│                                                       │
└──────────────────────────────────────────────────────┘

Version dropdown (v3.0 ▾):
┌────────────────────────────────────────┐
│  ● v3.0 (latest) — Mar 11, 2:30 PM    │
│    Re-run: +2 sources, +11 claims      │
│  ○ v2.0 — Mar 11, 1:15 PM             │
│    Booster: +2 sources, +8 claims      │
│  ○ v1.0 — Mar 11, 12:00 PM            │
│    Initial run: 3 sources, 26 claims   │
└────────────────────────────────────────┘
```

**What triggers a new version:**

| Trigger (Iterate Mode) | Which Docs Get New Version | Description |
|---|---|---|
| Initial pipeline run | Doc 0, 1, 2, 3 | All docs created at v1.0 |
| `deep_dive` | Doc 1 only | Appends research directions to Jump-Start; Doc 0/2/3 unchanged |
| `expand_sources` | Doc 0, 1, 2, 3 | Full re-run with new sources added |
| `deeper` | Doc 0, 1, 2, 3 | Re-extract with deeper prompts, re-synthesize |
| `different_angle` | Doc 1, 2, 3 | Re-synthesize with angle focus; Doc 0 unchanged (same sources) |
| `custom` | Doc 1, 2, 3 | Re-synthesize with user instructions; Doc 0 unchanged |
| User edits (future) | The edited doc only | Manual edits create a new version of that doc |

**Important: `deep_dive` only versions Doc 1.** It appends research directions to Jump-Start — it doesn't trigger a full pipeline re-run. Only when the user acts on the suggestions and triggers `expand_sources` with new sources do all docs get new versions.

#### 11.2.5 The Full Iteration Cycle With Versioning

```
Step 1: Initial run
  Doc 0 v1.0, Doc 1 v1.0, Doc 2 v1.0, Doc 3 v1.0
  User lands on Creator Brief (Doc 3 v1.0)

Step 2: User triggers iterate:deep_dive
  Doc 1 v1.0 → Doc 1 v2.0 (with Deep Research Expansion appended)
  All other docs unchanged

Step 3: User follows deep_dive suggestions, finds 3 new sources
  User triggers iterate:expand_sources with the new sources
  Doc 0 v1.0 → Doc 0 v2.0 (now includes original + new sources)
  Doc 1 v2.0 → Doc 1 v3.0 (fresh Jump-Start from expanded source set)
  Doc 2 v1.0 → Doc 2 v2.0 (richer claims from more sources)
  Doc 3 v1.0 → Doc 3 v2.0 (richer Creator Brief)
  User lands on Creator Brief (Doc 3 v2.0)

Step 4: User wants to compare
  Opens version dropdown on Doc 3
  Sees v2.0 (latest) and v1.0 (initial)
  Can switch between them to see how the Brief improved
  Diff summary: "+3 sources, +15 claims, +2 themes"

Step 5: User triggers iterate:different_angle ("economic impact focus")
  Doc 1 v3.0 → Doc 1 v4.0
  Doc 2 v2.0 → Doc 2 v3.0
  Doc 3 v2.0 → Doc 3 v3.0 (Creator Brief now has economic angle)
  Doc 0 unchanged (same sources, v2.0)

Step 6: User triggers iterate:deeper
  All docs get new versions — deeper extraction from same sources
  Cycle continues...
```

**The version window ensures the user can always go back and see how their research evolved, without infinite storage accumulation.** 4 versions (latest + 3 previous) is enough to cover a typical research session (initial + 2-3 iteration rounds).

---

### 11.3 Why Output Format Consistency Matters

This layer model only works if every document shares a **consistent design language.** If the Claims Document looks like a JSON dump, the Creator Brief looks like a blog post, and the Script looks like a Google Doc — it's three different products stapled together.

**Every document must share:**
- **Consistent header** — document type badge, topic, date, source count, version
- **Consistent typography** — same heading hierarchy, same emphasis patterns across all layers
- **Consistent interaction model** — if you can click a fact in the Brief to see its source, you should be able to do the same in the Script. The "click to drill down" pattern works everywhere.
- **Consistent density controls** — every document should have a "show more / show less" toggle. Some users want the 3-fact summary. Some want all 47 claims. Same document, different density.
- **Consistent visual language** — disputed claims look the same everywhere (warning icon + framing label). Verified facts look the same everywhere. Sources are always formatted the same way.

### 11.4 Document Rendering Priority

**v1 (Creator Brief focus — current build):**
- Creator Brief is the hero document
- Claims Document accessible via drill-down
- Source Ledger accessible via "View Sources"
- Script writer does NOT exist yet
- All three documents share the same markdown rendering pipeline and visual language

**v2 (Script writer addition — future build):**
- Script writer added as Layer 1
- Generated FROM the Creator Brief, not from raw claims
- Every sentence in the script traces back to a claim → traces back to a source
- The provenance chain is never broken: Script Line → Claim → Source

---

## 12. The Script Writer Vision (v2 — Not Built Yet, Documented for Future Context)

### 12.1 What It Does
Takes the Creator Brief and converts it into spoken-word prose — a script the creator can read off a teleprompter or use as talking points for a video.

### 12.2 How It Differs From Sandcastles' Script
- **Input:** Our script is generated from a verified Creator Brief, not from raw AI research. Every line has a provenance chain.
- **Traceability:** Every sentence in the script maps to a claim in the Brief, which maps to a source. Click any line → see where it came from.
- **Structure:** Not flat prose. The script has section markers that correspond to the Brief sections (Hook → Setup → Twist → Facts → Analogy → Personal Stakes → Cliffhanger).

### 12.3 Controls the User Gets
- **Tone:** Conversational / Authoritative / Urgent / Casual
- **Length:** 60s (~150 words) / 90s (~225 words) / 3min (~450 words) / 5min+ (~750 words)
- **Style:** Monologue / Narration / Interview Prep

### 12.4 Voice Mimicry Feature (v2+ — Requires Separate Design)
The user wants the script writer to have the ability to **analyze a creator's existing videos and mimic their voice, tone, and cadence** as an option when generating scripts.

**What this requires:**
- Ingesting 3-5 of the creator's existing videos (YouTube URLs or uploaded scripts)
- Analyzing speech patterns: sentence length distribution, vocabulary level, transition phrases, rhetorical questions frequency, personal anecdote usage, data density per minute
- Building a "voice profile" — a structured representation of how this creator talks
- Using that voice profile as a style guide when generating the script
- This is NOT simple text style transfer — it needs to capture cadence (short punchy sentences vs. long flowing ones), catchphrases or recurring structures, how they introduce data (casually vs. formally), how they address the viewer (direct "you" vs. general "people")

**What this does NOT mean:**
- Not deepfake voice cloning — this is writing style only
- Not copying another creator's voice — this is for mimicking YOUR OWN voice
- The creator provides their own videos as reference

**Design considerations:**
- Voice profile should be saveable and reusable across multiple scripts
- Should support "blend" — e.g., "my voice but 20% more authoritative"
- Needs a clear UX for uploading reference videos and reviewing the generated voice profile before using it
- Could integrate with the existing YouTube transcript extraction pipeline (Supadata → Whisper → youtube-transcript-api fallback chain)

**This is a v2+ feature.** It requires its own design cycle. Documented here so the vision isn't lost when this conversation compacts.

---

## 13. The Full User Journey (End State Vision)

```
ENTRY POINT A: Topic-First
  └─ Enter topic ("Why is the US dollar losing reserve status?")
  └─ System discovers sources (narrated loading: "Finding sources...")
  └─ User reviews & approves/rejects sources
  └─ Pipeline runs (narrated loading: "Extracting claims from 6 sources... 34 claims found...")
  └─ Creator Brief appears (HERO VIEW)

ENTRY POINT B: Sources-First (Skip-to-Sources)
  └─ User pastes URLs / uploads documents directly
  └─ Sources auto-validated for accessibility
  └─ Pipeline runs (same narrated loading)
  └─ Creator Brief appears (HERO VIEW)

FROM CREATOR BRIEF (HERO VIEW):
  ├─ Click any fact → drill into claim detail (Layer 3)
  │    └─ See: speaker attribution, rhetorical framing, significance, related claims
  │    └─ Click source → see full source ledger entry (Layer 4)
  │
  ├─ "View All Sources" → full source ledger (Layer 4)
  │    └─ URLs, verification dates, what was approved/rejected
  │
  └─ "Generate Script" → tone/length/style picker → Script (Layer 1) [v2]
       └─ Every line clickable → traces back to claim → traces back to source
       └─ Inline edit: highlight lines, request targeted changes
       └─ Voice mimicry toggle: use creator's voice profile [v2+]
```

**Key principle: the user is never overwhelmed.** They see one layer at a time. They can always go deeper. They can always go back up. The Creator Brief is always the center of gravity.

---

## 14. Sandcastles UI Patterns Worth Adopting

- **Progressive disclosure:** Only show the next step after completing the current one. Topic → Sources → Pipeline → Brief → Script. Each step is a reveal. This creates momentum and prevents overwhelm.
- **Card-based visual selection:** Hooks and styles shown as cards with engagement metrics. Scannable, fast decisions. We apply this to source approval (source cards with quality indicators) and hook selection in the Brief.
- **Loading states that narrate the process:** Instead of a spinner, show what's actually happening. Sandcastles shows "Finding sources... Identifying trends..." — ours shows real pipeline stages with real counts. This builds trust and perceived sophistication.
- **Inline edit requests:** Highlighting a section and requesting a targeted change. Sandcastles applies this to scripts. We apply it to the Creator Brief and eventually the Script.
- **Significance as visual hierarchy:** Sandcastles uses Shock Scores to surface engaging facts. We use `significance` from claim enrichments to rank and surface the most compelling verified facts in the Brief.

---

## 15. Next Steps (Prioritized)

1. **Legacy code audit** — Before building anything new, clean the codebase of any contaminating search-related legacy code
2. **Read & validate sandcastles-analysis.md** — Ground all competitive claims with objective data research
3. **Build the Creator Brief renderer** — New output format (Layer 2) using v3 claim enrichments. This is the v1 hero document.
4. **Ensure consistent output format** — All documents (Brief, Claims, Sources) share the same visual language and interaction patterns
5. **Design search UX flow** — Topic entry → source discovery → relevance validation → user approval → auto-pipeline injection
6. **Rebuild search with 6 requirements** — Skip-to-sources, relevance validation, auto-flow, quality maintenance, polished output
7. **UI overhaul** — Progressive disclosure, card-based selection, narrated loading states
8. **Script writer (v2)** — Generate spoken-word scripts from Creator Brief with tone/length/style controls
9. **Voice mimicry (v2+)** — Analyze creator's existing videos to build reusable voice profile for script generation

---

---

## 16. Rule Enforcement Audit (2026-03-11)

### 16.1 Prompt → Code Enforcement Map

The pipeline has two enforcement layers: **prompts** (tell the LLM what to do) and **code** (validate the LLM actually did it). Rules that only exist in prompts are suggestions. Rules enforced in code are guarantees.

#### 16.1.1 Prompt Files Inventory

All prompts live in `backend/pipeline/prompts/`:

| File | Stage | Purpose |
|---|---|---|
| `modes/base.py` | Extraction | 5 required components (Source Identity Lock, Confidence Ceiling, Empty Output Permission, Layered Extraction, Output Schema) — inherited by all 6 mode prompts |
| `modes/transcript_grounded.py` | Extraction | HIGH ceiling, verbatim quotes, timestamps required |
| `modes/caption_grounded.py` | Extraction | MEDIUM ceiling, approximate quotes |
| `modes/article_fetched.py` | Extraction | HIGH ceiling, verbatim quotes |
| `modes/video_only.py` | Extraction | LOW ceiling, NO quotes, observations only |
| `modes/text_provided.py` | Extraction | MEDIUM ceiling, unverified quotes |
| `modes/ocr_extracted.py` | Extraction | MEDIUM ceiling, OCR-flagged quotes |
| `semantic_extraction_prompt.py` | Extraction | Mode-agnostic dispatcher + inline fallback |
| `structure_analysis_prompt.py` | Pass 2 | Video reverse-engineering (hooks, narrative arc, production) |
| `gap_analysis_prompt.py` | Pass 3 | Cross-video critique (missing perspectives, blind spots) |
| `research_starter_prompt.py` | Pass 4 | Gap analysis → search directions (feeds Doc 1) |
| `semantic_synthesis_prompt.py` | Synthesis | Cross-source themes, tensions, gaps + gap identification |
| `cross_reference_prompt.py` | Phase 5 | New source comparison (supports, contradicts, new tensions) |
| `booster_prompt.py` | Deep Dive | Research directions generator (DIRECTIONS not FACTS) |
| `producer_prompt.py` | Producer | 4-stage creative pipeline (story core, structure, creative, risk) |
| `llm_judge_prompt.py` | Validation | Cross-model hallucination detection (GPT-4o validates Gemini) |

#### 16.1.2 Code Enforcement Files

| File | What It Enforces |
|---|---|
| `backend/pipeline/mode_selector.py` | **Single source of truth** for confidence ceilings, quote permissions, degraded/no-quote mode sets. All other code imports from here. |
| `backend/pipeline/semantic_validation.py` | Level 1 (schema), Level 2 (grounding), Level 2.5 (confidence ceiling), Level 3 (structural sufficiency), Level 4 (calibration) |
| `backend/pipeline/quote_verification.py` | Fuzzy-match quotes against source text. ≥0.7 = verified, <0.5 = likely hallucinated |
| `backend/pipeline/stages/semantic_validation_stage.py` | Orchestrates per-extraction validation, runs quote verification |
| `backend/pipeline/stages/document_assembly.py` | Provenance chain validation (Theme→KP→Source refs) |
| `backend/pipeline/stages/booster_stage.py` | Validates booster output: gap_id/theme_id refs must exist, detects generic queries |
| `backend/pipeline/producer/gating.py` | Producer Packet gating: 4+ sources, 1+ HIGH confidence, job completed |
| `backend/pipeline/stages/producer_stage.py` | Producer cardinality validation (min/max items per field) |
| `backend/models/source.py` | TranscriptProvenance @model_validator: auto-caps based on transcript source |
| `backend/models/job.py` | Pydantic validators: prompt injection, URL validation, source count limits |
| `backend/models/job_record.py` | Iteration constraints: mode enum, max_new_sources 0-10 |
| `backend/models/claims.py` | Confidence 0-1 range, min 1 evidence per entity, min 1 instance per cluster |

### 16.2 What's ENFORCED in Code (Guaranteed)

| Rule | Enforcement Location | Mechanism | Severity |
|---|---|---|---|
| Confidence ceiling auto-downgrade | `semantic_validation.py:658-704` | Auto-corrects KPs/Claims above ceiling | SOFT (auto-fix) |
| No quotes in video_only | `semantic_validation.py:605-619` | Hard fail if quotes found | HARD |
| Quote fuzzy-match verification | `quote_verification.py:93-150` | Fuzzy ratio ≥0.7 required | SOFT (flag) |
| Key Point must have ≥1 source_id | `semantic_validation.py:348-355` | Hard fail if missing | HARD |
| Theme must reference ≥2 KPs | `semantic_validation.py:394-401` | Soft fail if <2 | SOFT |
| Provenance chain (Theme→KP→Source) | `document_assembly.py:754-812` | Validates all refs exist | WARNING |
| Booster gap/theme ref validation | `booster_stage.py:185-258` | All refs must exist in bundle | WARNING |
| Booster anti-generic detection | `booster_stage.py:228-241` | Warns on generic patterns | WARNING |
| Producer gating (4+ sources, 1 HIGH) | `producer/gating.py:85-137` | Prevents generation if unmet | HARD |
| Producer cardinality ranges | `producer_stage.py:627-661` | Min/max items per field | WARNING |
| Transcript provenance auto-caps | `source.py:86-102` | @model_validator auto-sets | SOFT (auto-fix) |
| Prompt injection rejection | `job.py:43-66` | @field_validator rejects HTML/JS | HARD |
| URL validation (no channels/playlists) | `job.py:209-222` | @field_validator | HARD |
| Iteration max_new_sources 0-10 | `job_record.py:20` | Pydantic Field constraint | HARD |
| Timestamp bounds clamping | `semantic_validation.py:712-771` | Auto-clamps to video duration | SOFT (auto-fix) |

### 16.3 GAPS: Rules in Prompts But NOT Enforced in Code

These are rules declared in prompts or architecture docs that are NOT validated by code. They rely entirely on the LLM following instructions.

| # | Gap | Risk | Where It Should Be | Priority |
|---|---|---|---|---|
| 1 | **Claim source_id NOT enforced at model level** | Claims can have empty/missing source_id while KeyPoints cannot. Breaks provenance asymmetrically. | `claims.py` — add `min_length=1` on source_ids field | HIGH |
| 2 | **Tensions have NO source_id field** | Tensions extracted but have no grounding to specific sources. Violates provenance rules. | `semantic_units.py` or claims model — add source_ids to Tension | HIGH |
| 3 | **Confidence ceiling only enforces for KPs/Claims, NOT Themes/Gaps/Tensions** | High-level units inherit ceiling implicitly but can be HIGH confidence from LOW sources | `semantic_validation.py` — extend ceiling check to themes/tensions | MEDIUM |
| 4 | **Layered Extraction (Layer 1/2/3) NOT validated** | Prompt says extract in 3 layers but no code checks claims are explicit vs inferred | Would need a `layer` field on extraction items — complex to add | LOW |
| 5 | **Source Identity Lock NOT validated** | Prompts include source_id lock but no code verifies LLM returned matching source_id | `semantic_validation.py` — compare returned source_id to extraction context | MEDIUM |
| 6 | **Video-only timestamp requirement is SOFT fail** | Architecture says MUST have timestamp_range but code only warns | `semantic_validation.py:368` — change from warning to hard fail | LOW |
| 7 | **based_on field mismatch** | `validate_based_on_references()` expects based_on field but Pydantic models don't define it | Either add to models or remove dead validation code | LOW |
| 8 | **V1/V2 artifact mixing not guarded** | Job model allows both `booster_output` (V1) and `runs[].booster_expansion` (V2) simultaneously | Add version lock or migration check | MEDIUM |

### 16.4 Authoritative Docs vs. New Architecture: Conflicts Found

The authoritative spec docs (`docs/authoritative/spec/`) are **still on the OLD architecture**. They need updating when we implement:

| Document | Conflict | What Needs Changing |
|---|---|---|
| **RASS.md** | Defines Doc 0/1/2 as core, Doc 3 as Producer Packet (optional). No mention of Creator Brief, Iterate system, or consolidated modes. | Add Doc 3 as Creator Brief (core), move Producer Packet to Doc 4, add Iterate system with 5 modes |
| **Document_Output_Format.md** | `document_type` enum is `source_ledger | jump_start | semantic_brief | producer_packet`. No `creator_brief` type. | Add `creator_brief` type, update Doc 3 schema, add Doc 4 for Producer Packet |
| **Validation_and_Retry_Rules.md** | **CONFLICT: V5 lists text_provided and ocr_extracted as FORBIDDEN for quotes.** This contradicts Operational_Definitions.md AND architecture.md Rule 6 which ALLOW quotes for these modes (marked unverified). | Fix V5 table to match the Owner Decision (2026-01-15): text_provided and ocr_extracted ALLOW quotes with unverified flag |
| **Operational_Definitions.md** | Lists Doc 3 as Producer Packet. No mention of Creator Brief or Iterate modes. | Update document set definition |
| **architecture.md (.claude/rules/)** | Rule 12: "Three Core Documents" — needs to be Four. Rule 13: "Doc 3: Producer Packet" — needs to move to Doc 4. Still references "Booster" and "Addendum" as separate concepts. | Update Rules 12 & 13. Replace Booster/Addendum references with Iterate system modes. |

### 16.5 Naming Audit: Old → New

These old names appear in code and docs. When we implement, they need systematic renaming:

| Old Name | New Name | Where It Appears |
|---|---|---|
| Booster | Iterate: `deep_dive` mode | `booster_prompt.py`, `booster_stage.py`, `job_record.py:125` (`booster_output` field), `architecture.md` Rule 13, RASS.md Stage F |
| Addendum | Iterate: `expand_sources` mode | `architecture.md` Rule 13, cross_reference_prompt.py (Phase 5 logic) |
| Doc 3 = Producer Packet | Doc 3 = Creator Brief (NEW), Doc 4 = Producer Packet | `producer_prompt.py`, `producer/gating.py`, `producer_stage.py`, `Document_Output_Format.md`, RASS.md Section 3.4, architecture.md Rule 13 |
| more_sources (iterate mode) | `expand_sources` | `job_record.py:18` (mode enum), `iteration/modes/more_sources.py`, worker.py |
| `booster_output` (job field) | Deprecated — use iterations[] | `job_record.py:125` |

### 16.6 Temperature Settings Audit

Per architecture Rule 16, these are locked:

| Stage | Required | Current in Code | Status |
|---|---|---|---|
| Extraction | 0.1 | 0.1 | ✅ |
| Validation | N/A (code) | N/A | ✅ |
| Synthesis | 0.2 | 0.2 | ✅ |
| Booster/Deep Dive | 0.4 | 0.4 | ✅ |
| Producer | 0.3-0.5 | 0.3 (stage 1-3), 0.5 (stage 4) | ✅ |
| Creator Brief | TBD | Does not exist yet | ⬜ Needs defining |
| Script Writer | TBD | Does not exist yet | ⬜ Needs defining |

### 16.7 What "Enforced by Code" Should Mean Going Forward

For the Creator Brief (Doc 3) and any future documents, the rule is:

**Every constraint that can be checked programmatically MUST be checked programmatically.**

1. **Pydantic model validation** — field types, ranges, required fields, regex patterns
2. **Post-LLM validation** — provenance chain, confidence ceilings, quote permissions, reference integrity
3. **Gating checks** — prerequisites for optional documents (e.g., Producer Packet requires 4+ sources)
4. **Cross-document consistency** — Doc 3 facts must trace to Doc 2 claims which trace to Doc 0 sources

Prompts tell the LLM what to do. Code FORCES it. If a rule only exists in a prompt, it's a suggestion. If a rule exists in code, it's a guarantee.

---

*Document status: Complete as of 2026-03-11. Do not compact — this is strategic context.*
*Updated: Added document layer model, Iterate system consolidation, script writer vision, voice mimicry feature, full user journey, rule enforcement audit, and competitive adoption/differentiation details.*
