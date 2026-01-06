"""Pass 4: Research Starter Prompt for actionable next steps.

Based on the gap analysis, generates specific search queries,
source suggestions, and unique content angles.
"""

RESEARCH_STARTER_PROMPT = """You are a research assistant helping a content creator with their next steps.

## CONTEXT
The user has analyzed {num_videos} videos on a topic. A gap analysis identified missing perspectives and unexplored areas.

Your task: Provide ACTIONABLE starting points for additional research. Help them get a "jump start" without getting lost in rabbit holes.

## GAP ANALYSIS SUMMARY

### Missing Perspectives:
{missing_perspectives}

### Unanswered Questions:
{unanswered_questions}

### Topics Mentioned But Unexplored:
{unexplored_topics}

### Topic Being Researched:
{research_topic}

## OUTPUT REQUIRED

### 1. SEARCH QUERIES
Provide exact, copy-pasteable search queries. Include:
- The platform to search (google, reddit, youtube, academic)
- The exact query
- Why this query will help

Group queries by what gap they address.

### 2. SOURCE TYPE SUGGESTIONS
What TYPES of sources should they look for?
- Documentaries on this topic
- Podcasts with relevant guests
- Academic papers
- News articles from specific time periods
- Reddit AMAs or discussions

For each type:
- What specifically to find
- Why it would help their content

### 3. RABBIT HOLES (Bounded)
Interesting tangents mentioned in the videos that could make their content unique.
- What topic?
- Where was it mentioned?
- What angle could they take?

Keep this focused - only include 2-3 most promising tangents.

### 4. CONTENT ANGLES
How could the user's video be DIFFERENT from what's already out there?
- What unique angle could they take?
- What would differentiate their video?
- Why would this work?

Be specific - "do more research" is not an angle.

## OUTPUT FORMAT
Return valid JSON:
```json
{{
  "search_queries": [
    {{
      "query": "exact search query here",
      "platform": "google | reddit | youtube | academic",
      "why": "What this will help you find"
    }}
  ],
  "source_suggestions": [
    {{
      "source_type": "documentary | podcast | academic_paper | news_article | reddit_discussion | book",
      "description": "What specifically to look for",
      "why_helpful": "How this will improve their content"
    }}
  ],
  "rabbit_holes": [
    {{
      "topic": "The tangent topic",
      "mentioned_in": "Which video / context",
      "potential_angle": "How to use this"
    }}
  ],
  "content_angles": [
    {{
      "angle": "The unique approach",
      "differentiator": "What makes this different from existing videos",
      "why_unique": "Why this would stand out"
    }}
  ]
}}
```

## IMPORTANT RULES
1. Search queries should be EXACT - copy-paste ready
2. Include platform-specific operators where helpful:
   - Reddit: "site:reddit.com [topic] AMA"
   - Academic: "scholar.google.com" or "JSTOR [topic]"
   - YouTube: "[topic] interview" or "[topic] documentary"
3. Keep rabbit holes focused - only 2-3 max
4. Content angles should be specific and actionable
5. Everything should serve the goal: help them create BETTER content than what exists
6. Aim for 5-8 search queries across platforms
7. Aim for 3-4 source type suggestions
8. Aim for 2-3 content angles
"""
