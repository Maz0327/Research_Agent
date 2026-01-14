# Example: Producer Packet (Doc 3)

**Purpose:** Canonical example of a complete Producer Packet output.
**Context:** This example is based on a hypothetical 5-source investigation into a tech company controversy.

---

## Example Scenario

**Topic:** Investigation into "NovaTech" data privacy practices
**Sources:**
- SRC_1: YouTube interview with former employee (transcript_grounded, HIGH)
- SRC_2: YouTube news segment (caption_grounded, MEDIUM)
- SRC_3: Company blog post (article_fetched, HIGH)
- SRC_4: Industry analyst video (transcript_grounded, HIGH)
- SRC_5: User complaint thread screenshot (ocr_extracted, MEDIUM)

**Gating Check:** ✅ 5 sources, 3 high-confidence — eligible for Doc 3

---

## Complete Producer Packet Output

```json
{
  "document_type": "producer_packet",
  "document_version": "2.0",
  "job_id": "job_abc123",
  "generated_at": "2026-01-13T14:30:00Z",
  "creative_interpretation_notice": "This document contains creative interpretation and narrative suggestions. It is not factual research output. All content should be verified against Doc 0/1/2.",
  "story_core": {
    "central_question": "Did NovaTech knowingly sacrifice user privacy for growth, and what does this reveal about Silicon Valley's accountability gap?",
    "one_sentence_pitch": "A former insider's revelations expose how a rising tech darling built its empire on broken privacy promises.",
    "why_this_matters": "NovaTech has 40 million users who trusted the company with sensitive health data. If the allegations are true, this represents one of the largest privacy betrayals in the wellness tech sector.",
    "target_audience": "Tech-savvy viewers interested in privacy, corporate accountability, and Silicon Valley culture. Secondary: NovaTech users who want to understand what happened to their data.",
    "emotional_arc": "Trust → Suspicion → Betrayal → Accountability question"
  },
  "narrative_angles": [
    {
      "angle_id": "ANG_1",
      "title": "The Insider",
      "description": "Lead with the former employee's journey from true believer to whistleblower. Personal story anchors abstract privacy concerns.",
      "strengths": [
        "Human element creates emotional connection",
        "First-hand account adds credibility",
        "Natural narrative arc (joined hopeful, left disillusioned)"
      ],
      "weaknesses": [
        "Single source perspective could seem biased",
        "Viewer might question whistleblower motives"
      ],
      "best_for": "Documentary-style deep dive, 15-25 minutes",
      "key_sources": ["SRC_1"]
    },
    {
      "angle_id": "ANG_2",
      "title": "Follow the Data",
      "description": "Technical investigation approach. Trace what happens to user data from collection to alleged misuse.",
      "strengths": [
        "Evidence-based, harder to dismiss",
        "Appeals to technically-minded viewers",
        "Can include visual data flow diagrams"
      ],
      "weaknesses": [
        "Risk of being dry without human element",
        "Technical details may lose casual viewers"
      ],
      "best_for": "Explainer format, 10-15 minutes",
      "key_sources": ["SRC_1", "SRC_3", "SRC_4"]
    },
    {
      "angle_id": "ANG_3",
      "title": "The Pattern",
      "description": "Zoom out to show NovaTech as one example of a broader Silicon Valley accountability problem.",
      "strengths": [
        "Broader relevance beyond single company",
        "Can reference other known cases",
        "Positions you as industry analyst, not just critic"
      ],
      "weaknesses": [
        "May dilute focus on NovaTech specifics",
        "Requires additional research beyond current corpus"
      ],
      "best_for": "Essay-style commentary, 12-18 minutes",
      "key_sources": ["SRC_2", "SRC_4"]
    }
  ],
  "opening_hooks": [
    {
      "hook_type": "cold_open",
      "content": "Open with the former employee's voice: 'I watched them delete the audit logs. That's when I knew I had to leave.' Cut to NovaTech's cheerful marketing video promising 'Your data stays yours. Always.'",
      "tone": "Dramatic contrast, tension-building",
      "source_basis": ["SRC_1", "SRC_3"]
    },
    {
      "hook_type": "provocative_question",
      "content": "Your fitness app knows your heart rate, your sleep patterns, your location every morning. But do you know who else has access to that data? For 40 million NovaTech users, the answer might be more disturbing than they imagined.",
      "tone": "Direct address, personal stakes",
      "source_basis": ["SRC_4", "SRC_5"]
    },
    {
      "hook_type": "surprising_fact",
      "content": "NovaTech's privacy policy is 47 pages long. Buried on page 38 is a single sentence that, according to one former employee, 'basically gives them permission to do whatever they want.'",
      "tone": "Investigative, revelation-style",
      "source_basis": ["SRC_1", "SRC_3"]
    },
    {
      "hook_type": "scene_setting",
      "content": "San Francisco, 2024. In a glass tower overlooking the Bay, a wellness tech startup celebrated reaching 40 million users. Six floors down, in a windowless server room, a senior engineer was asking questions that would end his career.",
      "tone": "Cinematic, narrative journalism",
      "source_basis": ["SRC_1"]
    }
  ],
  "structure_options": [
    {
      "structure_type": "mystery_reveal",
      "description": "Start with the allegations, then work backward to reveal how we got here. Save the most damning evidence for the final act.",
      "section_breakdown": [
        "1. The Accusation (2 min) - What's being claimed",
        "2. The Company (4 min) - NovaTech's rise and promises",
        "3. The Cracks (5 min) - Early warning signs",
        "4. The Insider (6 min) - Former employee's account",
        "5. The Evidence (5 min) - Technical deep-dive",
        "6. The Response (3 min) - Company's defense",
        "7. The Question (2 min) - What happens next"
      ],
      "pros": [
        "Maintains tension throughout",
        "Rewards viewers who watch to end",
        "Natural cliffhangers for retention"
      ],
      "cons": [
        "May frustrate viewers who want facts upfront",
        "Risk of feeling manipulative if overdone"
      ]
    },
    {
      "structure_type": "chronological",
      "description": "Tell the story in order: founding, growth, problems emerge, whistleblower, current state.",
      "section_breakdown": [
        "1. The Beginning (3 min) - NovaTech founded",
        "2. The Promise (3 min) - Privacy-first marketing",
        "3. The Growth (4 min) - Rapid expansion",
        "4. The Pressure (4 min) - Monetization challenges",
        "5. The Compromise (5 min) - Alleged policy changes",
        "6. The Fallout (4 min) - Insider leaves, speaks out",
        "7. The Now (3 min) - Current status and implications"
      ],
      "pros": [
        "Easy to follow",
        "Shows cause and effect clearly",
        "Feels fair and journalistic"
      ],
      "cons": [
        "Can feel slow at the start",
        "Less dramatic tension"
      ]
    },
    {
      "structure_type": "compare_contrast",
      "description": "Alternate between NovaTech's public statements and alleged internal reality.",
      "section_breakdown": [
        "1. What They Said (2 min) - Marketing claims",
        "2. What They Did (3 min) - Alleged practices",
        "3. What They Promised (2 min) - Privacy policy highlights",
        "4. What Actually Happened (4 min) - Insider account",
        "5. What They Claim Now (2 min) - Company response",
        "6. What the Evidence Shows (4 min) - Analysis",
        "7. What This Means (3 min) - Implications"
      ],
      "pros": [
        "Visual contrast is compelling",
        "Lets viewers draw own conclusions",
        "Strong for video format"
      ],
      "cons": [
        "Can feel repetitive",
        "May come across as biased if not balanced"
      ]
    }
  ],
  "key_moments": [
    {
      "moment": "Former employee describes watching audit logs being deleted",
      "source_id": "SRC_1",
      "timestamp": "14:32",
      "why_compelling": "Specific, visual, suggests cover-up",
      "potential_use": "Cold open or key revelation moment"
    },
    {
      "moment": "Company CEO on stage: 'Privacy isn't a feature, it's our foundation'",
      "source_id": "SRC_3",
      "timestamp": null,
      "why_compelling": "Direct contrast to allegations, his own words",
      "potential_use": "Juxtaposition with insider claims"
    },
    {
      "moment": "Industry analyst explains third-party data sharing model",
      "source_id": "SRC_4",
      "timestamp": "08:15",
      "why_compelling": "Expert credibility, explains technical mechanism",
      "potential_use": "Educational segment, builds understanding"
    },
    {
      "moment": "User describes discovering their data on broker site",
      "source_id": "SRC_5",
      "timestamp": null,
      "why_compelling": "Real victim, tangible harm",
      "potential_use": "Humanize the impact, closing segment"
    },
    {
      "moment": "Former employee: 'I believed in the mission. That's what made it so hard.'",
      "source_id": "SRC_1",
      "timestamp": "22:45",
      "why_compelling": "Emotional, relatable, not bitter—sad",
      "potential_use": "Character moment, builds sympathy"
    }
  ],
  "title_options": [
    {
      "title": "The Privacy Lie",
      "subtitle": "Inside NovaTech's Broken Promises",
      "tone": "provocative",
      "seo_considerations": "Strong keywords: privacy, lie, tech company"
    },
    {
      "title": "They Promised Your Data Was Safe",
      "subtitle": null,
      "tone": "urgent",
      "seo_considerations": "Direct address performs well in thumbnails"
    },
    {
      "title": "NovaTech: The Insider Story",
      "subtitle": "A Former Employee Speaks Out",
      "tone": "serious",
      "seo_considerations": "Company name for search, 'insider' signals exclusive"
    },
    {
      "title": "40 Million Users. One Devastating Secret.",
      "subtitle": null,
      "tone": "provocative",
      "seo_considerations": "Numbers perform well, mystery element"
    },
    {
      "title": "I Worked at NovaTech. Here's What They Don't Want You to Know.",
      "subtitle": null,
      "tone": "curious",
      "seo_considerations": "First-person hooks, 'secret' framing"
    }
  ],
  "thumbnail_concepts": [
    {
      "concept": "Split screen: Happy NovaTech marketing image on left, shadowy figure (whistleblower silhouette) on right",
      "visual_elements": ["Brand colors (teal/white)", "Silhouette", "Split composition"],
      "text_overlay": "THE TRUTH",
      "emotional_appeal": "Contrast, mystery, revelation promised"
    },
    {
      "concept": "Close-up of smartphone with health app, red 'EXPOSED' stamp across it",
      "visual_elements": ["Phone screen", "Health data visualization", "Red stamp"],
      "text_overlay": "YOUR DATA",
      "emotional_appeal": "Personal relevance, alarm, direct stakes"
    },
    {
      "concept": "Former employee face (if available) with concerned expression, NovaTech logo faded behind",
      "visual_elements": ["Human face", "Corporate logo", "Muted colors"],
      "text_overlay": "INSIDER",
      "emotional_appeal": "Human connection, credibility, exclusive access"
    }
  ],
  "risk_assessment": {
    "sensitivity_level": "high",
    "potential_issues": [
      "Defamation risk if claims can't be substantiated",
      "NovaTech may issue takedown request or legal threat",
      "Former employee could face retaliation, may request anonymity",
      "Technical claims need verification by independent expert"
    ],
    "mitigation_suggestions": [
      "Use 'allegedly' and 'according to' for unverified claims",
      "Include NovaTech's official response prominently",
      "Have lawyer review before publication",
      "Offer anonymity options to former employee",
      "Document all sources thoroughly"
    ],
    "legal_considerations": [
      "Fair comment/opinion defense applies to analysis",
      "Verify all factual claims have source documentation",
      "Screenshots of public statements are generally safe",
      "Avoid implying criminal conduct without strong evidence"
    ],
    "ethical_considerations": [
      "Users affected by alleged breach deserve to know",
      "Former employee's livelihood could be affected",
      "Balance public interest against individual privacy",
      "Consider reaching out to NovaTech for comment before publishing"
    ]
  },
  "interview_suggestions": {
    "people_to_contact": [
      {
        "name": "Dr. Sarah Chen (hypothetical)",
        "role": "Privacy researcher, Stanford",
        "why_relevant": "Can provide independent expert analysis of data practices",
        "potential_questions": [
          "Is what NovaTech allegedly did illegal?",
          "How common are these practices in the industry?",
          "What should affected users do?"
        ]
      },
      {
        "name": "NovaTech PR/Communications",
        "role": "Official company response",
        "why_relevant": "Journalistic fairness requires right of reply",
        "potential_questions": [
          "How do you respond to these allegations?",
          "What is your current data sharing policy?",
          "Will affected users be notified?"
        ]
      }
    ],
    "expert_perspectives_needed": [
      "Data privacy lawyer for legal analysis",
      "Cybersecurity expert for technical verification",
      "Consumer rights advocate for user perspective"
    ]
  },
  "b_roll_suggestions": [
    {
      "description": "NovaTech office exterior, logo signage",
      "purpose": "Establish company as real entity",
      "source_options": ["Stock footage", "Google Street View", "News footage"]
    },
    {
      "description": "Generic data center footage, server racks with blinking lights",
      "purpose": "Visualize abstract 'data' concept",
      "source_options": ["Stock footage", "Creative Commons"]
    },
    {
      "description": "Person using health/fitness app on phone",
      "purpose": "Relatable user experience",
      "source_options": ["Film original", "Stock footage"]
    },
    {
      "description": "Screen recording of NovaTech privacy policy, scrolling",
      "purpose": "Show length/complexity of policy",
      "source_options": ["Capture directly from site"]
    }
  ]
}
```

---

## Markdown Rendered Version

# Producer Packet: NovaTech Investigation

> ⚠️ **Creative Interpretation Notice:** This document contains creative interpretation and narrative suggestions. It is not factual research output. All content should be verified against Doc 0/1/2.

---

## Story Core

**Central Question:** Did NovaTech knowingly sacrifice user privacy for growth, and what does this reveal about Silicon Valley's accountability gap?

**One-Sentence Pitch:** A former insider's revelations expose how a rising tech darling built its empire on broken privacy promises.

**Why This Matters:** NovaTech has 40 million users who trusted the company with sensitive health data. If the allegations are true, this represents one of the largest privacy betrayals in the wellness tech sector.

**Target Audience:** Tech-savvy viewers interested in privacy, corporate accountability, and Silicon Valley culture.

**Emotional Arc:** Trust → Suspicion → Betrayal → Accountability question

---

## Narrative Angles

### ANG_1: The Insider
Lead with the former employee's journey from true believer to whistleblower.

| Strengths | Weaknesses |
|-----------|------------|
| Human element creates emotional connection | Single source could seem biased |
| First-hand account adds credibility | Viewer might question motives |
| Natural narrative arc | |

**Best for:** Documentary-style deep dive, 15-25 minutes

### ANG_2: Follow the Data
Technical investigation tracing data from collection to alleged misuse.

**Best for:** Explainer format, 10-15 minutes

### ANG_3: The Pattern
Position NovaTech as one example of broader Silicon Valley accountability issues.

**Best for:** Essay-style commentary, 12-18 minutes

---

## Opening Hooks

**Cold Open:**
> Open with the former employee's voice: "I watched them delete the audit logs. That's when I knew I had to leave." Cut to NovaTech's cheerful marketing video promising "Your data stays yours. Always."

**Provocative Question:**
> Your fitness app knows your heart rate, your sleep patterns, your location every morning. But do you know who else has access to that data?

---

## Structure Options

| Type | Best For | Risk |
|------|----------|------|
| Mystery Reveal | Maintaining tension, retention | May frustrate impatient viewers |
| Chronological | Clarity, fairness | Can start slow |
| Compare/Contrast | Visual impact | Can feel repetitive |

---

## Key Moments to Feature

1. **"I watched them delete the audit logs"** (SRC_1, 14:32) — Cold open material
2. **CEO: "Privacy isn't a feature, it's our foundation"** (SRC_3) — Juxtaposition
3. **Analyst explains data sharing model** (SRC_4, 08:15) — Education
4. **User discovers data on broker site** (SRC_5) — Human impact
5. **"I believed in the mission"** (SRC_1, 22:45) — Emotional anchor

---

## Title Options

1. **The Privacy Lie** — Provocative, strong SEO
2. **They Promised Your Data Was Safe** — Direct, urgent
3. **NovaTech: The Insider Story** — Serious, exclusive feel
4. **40 Million Users. One Devastating Secret.** — Mystery, numbers

---

## Risk Assessment

**Sensitivity Level:** HIGH

**Key Risks:**
- Defamation if claims unsubstantiated
- Potential takedown request
- Source retaliation concerns

**Mitigations:**
- Use "allegedly" for unverified claims
- Include official response
- Legal review before publication

---

**END OF EXAMPLE**
