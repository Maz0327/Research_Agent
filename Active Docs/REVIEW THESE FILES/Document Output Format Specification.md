# Document Output Format Specification

**Research Agent System Specification — Addendum**

This document defines the **required structure, formatting, ordering, and content rules** for all three canonical documents produced by the Research Agent.

All outputs must be renderable as **Markdown** and serializable as **JSON** without loss of meaning.

---

# GLOBAL FORMATTING RULES (APPLY TO ALL DOCS)

### G1. Skimmable First

* Every document must be readable at a glance
* Headings precede detail
* Long content must be collapsible in UI

### G2. Stable Identifiers

* All references use stable IDs:

  * `SRC_1`, `KP_3`, `THEME_2`, `GAP_1`
* IDs are required for traceability

### G3. Explicit Labels

* Interpretation and speculation must be labeled
* Confidence must be visible where applicable

### G4. No Narrative Voice

* Neutral, research-oriented language
* No persuasive framing
* No conclusions unless explicitly marked speculative

---

# DOC 0 — SOURCE LEDGER

**(Canonical Data Layer)**

---

## Purpose (Reminder)

Preserve **full context + raw extracted structure**.
This document is **the foundation** for all others.

---

## DOC 0 — REQUIRED STRUCTURE

```
# SOURCE LEDGER
Topic: <Scope Lock Sentence>

## SOURCE MANIFEST
| Source ID | Type | Title | Creator/Author | Length | Status |
|----------|------|-------|----------------|--------|--------|
| SRC_1 | YouTube | ... | ... | 1:42:33 | Ingested |
| SRC_2 | Article | ... | ... | 3,200 words | Ingested |

---

## SOURCES
```

---

### Per-Source Section (REQUIRED)

```
### SOURCE: SRC_1
Type: YouTube
Title:
Creator:
Published:
Duration:
URL:

#### Skim Summary (3–6 bullets)
- What this source is about
- Who is speaking / perspective
- What it contributes
- Notable limitations or bias

#### Extracted Index
**Key Claims**
- CLAIM_1: <short description>
- CLAIM_2: <short description>

**Entities**
- Person:
- Organization:
- Event:

**Themes Touched**
- THEME_1
- THEME_3

#### FULL SOURCE TEXT (Canonical)
<verbatim transcript or article text>
```

---

### Transcript Provenance (Per Video Source)

For video sources (YouTube, etc.), each source MUST include transcript provenance metadata:

```json
"transcript_provenance": {
  "transcript_source": "supadata | youtube_captions | none",
  "transcript_status": "success | failed",
  "captions_status": "success | missing | failed",
  "gemini_analysis_mode": "transcript_grounded | caption_grounded | video_only",
  "verification_capabilities": {
    "quote_verification": true,
    "timestamp_grounding": true,
    "semantic_precision": "high | medium | low"
  },
  "notes": "Human-readable explanation of fallbacks or failures"
}
```

**Provenance Rules:**

| Condition | Enforcement |
|-----------|-------------|
| `transcript_source = none` | `quote_verification` MUST be `false` |
| `transcript_source = youtube_captions` | `semantic_precision` = `medium` maximum |
| Any video source | This block MUST appear |

**Display in Markdown:**

```
#### Transcript Provenance
Source: Supadata ✅ | Captions: N/A | Mode: transcript_grounded
Verification: Full quote verification available
```

---

## Rules for DOC 0

* FULL SOURCE TEXT is mandatory
* No interpretation beyond skim summaries
* Skim summaries describe content, not meaning
* This document may be long — that is intentional

---

# DOC 1 — JUMP-START

**(Research Direction Layer)**

---

## Purpose (Reminder)

Answer:

* What do I have?
* What’s missing?
* Where do I go next?

This is the **activation trigger** for the user.

---

## DOC 1 — REQUIRED STRUCTURE

```
# JUMP-START RESEARCH BRIEF

## SCOPE LOCK
This research covers:
- IN: …
- OUT: …

---

## CURRENT CORPUS OVERVIEW
- Number of sources:
- Perspectives represented:
- Time span covered:

---

## WHAT WE KNOW (From Current Sources)
- KP_1: <one-line description>
- KP_2:
- KP_3:

---

## WHAT IS UNCLEAR OR DISPUTED
- TENSION_1:
- TENSION_2:

---

## GAPS (What’s Missing)
- GAP_1: <description + why it matters>
- GAP_2:

---

## SUGGESTED RESEARCH DIRECTIONS
### Priority 1
- What to look for
- Example queries
- Why this matters

### Priority 2
…

---

## TOP 3 NEXT STEPS (MANDATORY)
1. …
2. …
3. …
```

---

## Rules for DOC 1

* Must always be produced
* May exist without Deep Research Booster
* Booster adds sections, never replaces content
* Language must be directive, not speculative

---

# DOC 2 — SEMANTIC RESEARCH BRIEF

**(80% Finished Output)**

---

## Purpose (Reminder)

Deliver **deep understanding**, not conclusions.
This is what a strong human researcher would hand off.

---

## DOC 2 — REQUIRED STRUCTURE

```
# SEMANTIC RESEARCH BRIEF

## SEMANTIC CORE (What This Is Really About)
<2–4 sentences describing the underlying issue, not a summary>

---

## KEY THEMES
### THEME_1: <Theme Name>
Description:
- What this theme represents

Supporting Key Points:
- KP_1
- KP_4
- KP_7

---

### THEME_2: …
```

---

### Key Points Section (MANDATORY)

```
## KEY POINTS
- KP_1: <neutral assertion>
  Sources: SRC_1, SRC_2

- KP_2:
  Sources: SRC_3
```

---

### Tensions & Contradictions (If Present)

```
## TENSIONS & CONTRADICTIONS
- TENSION_1:
  Description:
  Involved Points: KP_3, KP_6
  Notes:
```

---

### Gaps & Weaknesses

```
## GAPS & WEAKNESSES
- GAP_1:
  Why it matters:
  What would help resolve it:
```

---

### Confidence Calibration

```
## CONFIDENCE ASSESSMENT
Overall Confidence: Medium

Reasoning:
- Source diversity:
- Verification rate:
- Presence of contradictions:
```

---

### Optional: Speculative Directions (Explicitly Labeled)

```
## SPECULATIVE OBSERVATIONS (OPTIONAL)
⚠️ These are hypotheses, not conclusions.

- One possible interpretation is…
  Based on: KP_2, KP_5
```

---

## Rules for DOC 2

* Every section must reference earlier units
* No new facts allowed
* Speculation must be isolated and labeled
* This document should *feel* complete but never authoritative

---

# FAILURE & DEGRADATION DISPLAY (ALL DOCS)

If output is thin or sources are weak:

* Add visible warning banner:

  > “This brief is based on limited or one-sided sources.”
* Increase emphasis on:

  * Gaps
  * Next steps
* Never pad content to appear complete

---

## End of Document Output Format Specification (Draft v1)

---

