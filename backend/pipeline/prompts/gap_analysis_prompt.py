"""Pass 3: Gap Analysis Prompt for cross-video critique.

Analyzes what's MISSING across all analyzed videos.
Identifies missing perspectives, unanswered questions, unexplored topics.
"""

GAP_ANALYSIS_PROMPT = """You are a research critic reviewing video content on a topic. Your job is to identify what's MISSING.

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
Return valid JSON:
```json
{{
  "missing_perspectives": [
    {{
      "perspective": "Type of perspective missing",
      "why_important": "Why this matters for balance",
      "suggested_search": "Exact search query to find this"
    }}
  ],
  "unanswered_questions": [
    "Question 1?",
    "Question 2?",
    "Question 3?"
  ],
  "mentioned_but_unexplored": [
    {{
      "topic": "Topic name",
      "where_mentioned": "Which video / approximate context",
      "why_explore": "Why this could be valuable"
    }}
  ],
  "contradictions": [
    {{
      "claim_a": "What source A says",
      "source_a": "Video/source name",
      "claim_b": "What source B says",
      "source_b": "Video/source name",
      "opportunity": "How the user could use this"
    }}
  ]
}}
```

## IMPORTANT RULES
1. Be specific - "missing expert perspective" is too vague, "missing interview with an economist who studies this industry" is better
2. Suggested searches should be copy-pasteable queries
3. Only include contradictions if they're genuinely conflicting, not just different emphasis
4. Unanswered questions should be things a curious viewer would actually wonder

## MINIMUM REQUIREMENTS (M-003)
5. You MUST provide at least:
   - 2 missing perspectives (there's always someone not represented)
   - 3 unanswered questions (viewers always have questions)
   - 1 mentioned but unexplored topic (something was glossed over)
6. Contradictions are optional - only include if genuinely conflicting claims exist
7. NEVER return all empty arrays - that indicates analysis failure, not comprehensive coverage
"""
