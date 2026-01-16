"""Pass 3: Gap Analysis Prompt for cross-video critique.

Analyzes what's MISSING across all analyzed videos.
Identifies missing perspectives, unanswered questions, unexplored topics.
"""

# Gap Analysis Context Lock - prevents fabrication during gap identification
GAP_ANALYSIS_CONTEXT_LOCK = """
╔══════════════════════════════════════════════════════════╗
║  GAP ANALYSIS LOCK — ONLY IDENTIFY ABSENCES              ║
╠══════════════════════════════════════════════════════════╣
║  Videos Analyzed: {num_videos}                           ║
║  Mode: Gap identification (NOT fact creation)            ║
║  Confidence Ceiling: MEDIUM for inferred gaps            ║
╚══════════════════════════════════════════════════════════╝

RULE: You identify what is MISSING, not what might be true.
Gaps are expectations, not assertions about reality.
"""

GAP_ANALYSIS_PROMPT = """{gap_analysis_context_lock}

You are a research critic reviewing video content on a topic. Your job is to identify what's MISSING.

## CONTEXT
The user is researching a topic by analyzing {num_videos} videos. Below are the clips and quotes extracted from those videos.

Your task: Identify gaps, missing perspectives, and opportunities for the user's own content.

## EXTRACTED CONTENT

### Clips Summary:
{clips_summary}

### Key Quotes:
{quotes_summary}

### Videos Analyzed:
{videos_list}

## ANALYSIS REQUIRED

### 1. MISSING PERSPECTIVES
Who wasn't represented in these videos? Consider:
- Skeptics or critics of the main narrative
- Affected parties or victims
- Independent experts
- Alternative viewpoints
- People who disagree with the consensus

For each missing perspective:
- What perspective is missing?
- Why does it matter for a balanced view?
- What search query would help find this perspective?

### 2. UNANSWERED QUESTIONS
What would a curious viewer naturally ask that wasn't answered?
- Questions the videos raised but didn't address
- Logical follow-up questions
- "But what about...?" questions
- Timeline gaps or unexplained events

### 3. COVERAGE BLIND SPOTS
What topics were MENTIONED but not EXPLORED?
- Names dropped without context
- Events referenced without explanation
- Tangents that weren't followed
- "That's a story for another time" moments

For each blind spot:
- What topic was mentioned?
- Where was it mentioned? (video title/approximate context)
- Why might it be worth exploring?

### 4. CONTRADICTIONS (Opportunity)
Where do the sources disagree?
- Conflicting claims across videos
- Different interpretations of the same event
- Disputed facts or figures

Contradictions are OPPORTUNITIES - the user can investigate and provide clarity.

## OUTPUT FORMAT
Return valid JSON matching this schema:

```json
{{
  "missing_perspectives": [
    {{
      "perspective": "string - WHO is missing from the conversation",
      "why_important": "string - why their voice matters",
      "likelihood": "high | medium | low",
      "likelihood_reasoning": "string - why you expect this perspective exists online",
      "where_to_find": [
        "string - specific place/method to find this perspective"
      ],
      "suggested_searches": [
        {{"query": "primary search query", "platform": "youtube | reddit | google"}},
        {{"query": "alternative query", "platform": "youtube | reddit | google"}}
      ]
    }}
  ],
  "unanswered_questions": [
    "string - specific question a viewer would ask"
  ],
  "mentioned_but_unexplored": [
    {{
      "topic": "string - specific name/event/concept mentioned",
      "where_mentioned": "string - video title or timestamp context",
      "why_explore": "string - why this deserves deeper coverage"
    }}
  ],
  "contradictions": [
    {{
      "claim_a": "string - verbatim or paraphrased claim",
      "source_a": "string - video title",
      "claim_b": "string - conflicting claim",
      "source_b": "string - video title",
      "opportunity": "string - what the user can do with this"
    }}
  ]
}}
```

## EXAMPLE OUTPUT (for a topic about "Theranos scandal"):

NOTE: This example shows output for a well-documented topic with many gaps.
Your output may be shorter if the videos comprehensively covered the topic.
Match the QUALITY and SPECIFICITY, not the QUANTITY of the example.

```json
{{
  "missing_perspectives": [
    {{
      "perspective": "Former Theranos lab technicians who ran the tests",
      "why_important": "They saw firsthand how the technology worked (or didn't) - most coverage focuses on executives and investors",
      "likelihood": "high",
      "likelihood_reasoning": "Major scandal with federal trial = employees testified publicly and were interviewed by journalists",
      "where_to_find": [
        "Search for clips from the HBO documentary 'The Inventor'",
        "Check court testimony transcripts on CourtListener or PACER",
        "Look for journalist Twitter threads from reporters who covered the trial"
      ],
      "suggested_searches": [
        {{"query": "Theranos lab technician interview testimony", "platform": "youtube"}},
        {{"query": "site:reddit.com Theranos employee AMA", "platform": "reddit"}},
        {{"query": "Theranos whistleblower Erika Cheung interview", "platform": "google"}}
      ]
    }},
    {{
      "perspective": "Patients who received incorrect test results",
      "why_important": "The human cost is often abstracted - actual patients can describe real medical decisions made on bad data",
      "likelihood": "medium",
      "likelihood_reasoning": "Patient privacy may limit public interviews, but some testified in court or spoke to journalists",
      "where_to_find": [
        "Search for news articles about patient lawsuits",
        "Check if any patients were interviewed in documentaries",
        "Look for court testimony from affected patients"
      ],
      "suggested_searches": [
        {{"query": "Theranos patient wrong diagnosis interview", "platform": "youtube"}},
        {{"query": "Theranos misdiagnosis victim story", "platform": "google"}},
        {{"query": "site:reddit.com Theranos patient experience", "platform": "reddit"}}
      ]
    }}
  ],
  "unanswered_questions": [
    "How did Theranos pass Walgreens' due diligence process?",
    "What happened to the 'miniLab' device after the company collapsed?",
    "Did any investors try to visit the lab before investing?"
  ],
  "mentioned_but_unexplored": [
    {{
      "topic": "The Safeway partnership that was canceled",
      "where_mentioned": "Bad Blood documentary around 45:00",
      "why_explore": "Safeway spent $350M building clinics but pulled out - what did they discover that Walgreens missed?"
    }},
    {{
      "topic": "Tyler Shultz's grandfather George Shultz",
      "where_mentioned": "Multiple videos mention him briefly",
      "why_explore": "A former Secretary of State choosing his board seat over his grandson is a fascinating family dynamics story"
    }}
  ],
  "contradictions": [
    {{
      "claim_a": "Elizabeth Holmes was a deliberate fraudster from the start",
      "source_a": "The Inventor: Out for Blood",
      "claim_b": "Holmes genuinely believed the technology would work and got in over her head",
      "source_b": "ABC News interview with former employees",
      "opportunity": "User could explore the 'true believer vs con artist' debate with evidence from both sides"
    }}
  ]
}}
```

## IMPORTANT RULES
1. Be specific - "missing expert perspective" is too vague, "missing interview with an economist who studies this industry" is better
2. Suggested searches should be copy-pasteable queries
3. Only include contradictions if they're genuinely conflicting, not just different emphasis
4. Unanswered questions should be things a curious viewer would actually wonder

## QUALITY OVER QUANTITY (AP-001: Anti-Hallucination)
5. Return empty arrays if no genuine gaps are found - this is valid, not failure
6. Do NOT invent content to meet quotas - sparse honest output is preferred
7. Only include items you can justify from the actual extracted content above
8. Contradictions are optional - only include if genuinely conflicting claims exist
9. If videos comprehensively cover the topic, it's OK to have few gaps identified
10. If returning empty arrays, MUST include "analysis_warnings" explaining WHY each field is empty

## WARNING REQUIREMENT
If any array is empty, include "analysis_warnings" field:
```json
{{
  "missing_perspectives": [],
  "contradictions": [],
  "analysis_warnings": [
    "missing_perspectives empty: All major viewpoints appear represented across the 4 videos analyzed",
    "contradictions empty: Sources present consistent narrative without conflicting claims"
  ]
}}
```
"""


def build_gap_analysis_prompt(
    num_videos: int,
    clips_summary: str,
    quotes_summary: str,
    videos_list: str,
) -> str:
    """
    Build the complete gap analysis prompt with context lock.

    Args:
        num_videos: Number of videos analyzed
        clips_summary: Summary of extracted clips
        quotes_summary: Summary of key quotes
        videos_list: List of videos analyzed

    Returns:
        Complete prompt string ready for Gemini
    """
    # Build context lock
    context_lock = GAP_ANALYSIS_CONTEXT_LOCK.format(num_videos=num_videos)

    # Build full prompt
    return GAP_ANALYSIS_PROMPT.format(
        gap_analysis_context_lock=context_lock,
        num_videos=num_videos,
        clips_summary=clips_summary,
        quotes_summary=quotes_summary,
        videos_list=videos_list,
    )
