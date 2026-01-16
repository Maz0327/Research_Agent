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
Return valid JSON with citation tracking and ACTIONABLE guidance:
```json
{{
  "search_queries": [
    {{
      "query_primary": "exact primary search query",
      "query_alternatives": ["variation 1 phrasing", "variation 2 phrasing"],
      "query_fallback": "fallback query if others return nothing",
      "platform": "google | reddit | youtube | academic",
      "why": "What this will help you find",
      "if_no_results": "What to try next if these don't work",
      "based_on": ["CLIP_3", "QUOTE_7"],
      "confidence": "high | medium | speculative"
    }}
  ],
  "source_suggestions": [
    {{
      "source_type": "documentary | podcast | academic_paper | news_article | reddit_discussion | book",
      "hunting_strategy": [
        "Step 1: Where to start looking",
        "Step 2: What to search for",
        "Step 3: How to verify you found the right thing"
      ],
      "known_sources_for_genre": ["Known podcast/channel that covers this type of topic"],
      "why_helpful": "How this will improve their content"
    }}
  ],
  "rabbit_holes": [
    {{
      "topic": "The tangent topic",
      "mentioned_in": "Which video / context",
      "potential_angle": "How to use this",
      "based_on": ["CLIP_5"],
      "confidence": "speculative"
    }}
  ],
  "content_angles": [
    {{
      "angle": "The unique approach",
      "differentiator": "What makes this different from existing videos",
      "why_unique": "Why this would stand out",
      "based_on": ["CLIP_2", "QUOTE_4"],
      "confidence": "high | medium | speculative"
    }}
  ]
}}
```

## EXAMPLE OUTPUT (for research on "FTX collapse"):

NOTE: This example shows output for a topic with many research opportunities.
Your output may be shorter if the gap analysis found fewer issues.
Match the QUALITY and SPECIFICITY, not the QUANTITY of the example.

```json
{{
  "search_queries": [
    {{
      "query_primary": "site:reddit.com FTX AMA Sam Bankman-Fried",
      "query_alternatives": [
        "site:reddit.com SBF ask me anything crypto",
        "reddit Sam Bankman-Fried Q&A before collapse"
      ],
      "query_fallback": "site:twitter.com SBF thread 2021 2022",
      "platform": "reddit",
      "why": "Find any AMAs SBF did before the collapse - his own words will be valuable primary source material",
      "if_no_results": "Check Twitter threads from 2021-2022, or his Bloomberg/podcast appearances",
      "based_on": ["CLIP_4"],
      "confidence": "high"
    }},
    {{
      "query_primary": "Caroline Ellison Alameda Research interview",
      "query_alternatives": [
        "Caroline Ellison podcast appearance",
        "Alameda Research CEO interview youtube"
      ],
      "query_fallback": "Caroline Ellison twitter threads trading",
      "platform": "youtube",
      "why": "Find any public appearances by Alameda's CEO to understand their trading strategy claims",
      "if_no_results": "She was media-shy - try her deleted tweets via archive.org or court testimony clips",
      "based_on": ["QUOTE_12", "CLIP_8"],
      "confidence": "high"
    }},
    {{
      "query_primary": "FTX bankruptcy court filing customer funds",
      "query_alternatives": [
        "FTX Chapter 11 filing PDF",
        "John Ray III FTX declaration court"
      ],
      "query_fallback": "site:courtlistener.com FTX bankruptcy",
      "platform": "google",
      "why": "Court filings will have exact figures on missing customer funds - more reliable than media estimates",
      "if_no_results": "Try PACER database or search for journalist summaries of the filings",
      "based_on": ["CLIP_15"],
      "confidence": "medium"
    }}
  ],
  "source_suggestions": [
    {{
      "source_type": "podcast",
      "hunting_strategy": [
        "Search Spotify/Apple Podcasts for 'Sam Bankman-Fried interview 2021 2022'",
        "Check Odd Lots, Lex Fridman, and Bloomberg Odd Lots archives",
        "Look for appearances BEFORE Nov 2022 - those show his pre-collapse persona"
      ],
      "known_sources_for_genre": ["Odd Lots (Bloomberg)", "Bankless", "Unchained", "What Bitcoin Did"],
      "why_helpful": "Shows how SBF presented himself when things seemed fine - contrast with reality"
    }},
    {{
      "source_type": "academic_paper",
      "hunting_strategy": [
        "Search Google Scholar for 'cryptocurrency exchange proof of reserves'",
        "Check SSRN for working papers on crypto auditing",
        "Look for Chainalysis or similar blockchain analytics reports"
      ],
      "known_sources_for_genre": ["SSRN", "NBER Working Papers", "Journal of Financial Economics"],
      "why_helpful": "Technical background on what proper exchange reserves should look like"
    }},
    {{
      "source_type": "news_article",
      "hunting_strategy": [
        "Search CoinDesk archives for November 2-8 2022",
        "Look for Ian Allison's original reporting",
        "Find the actual leaked balance sheet document"
      ],
      "known_sources_for_genre": ["CoinDesk", "The Block", "Wall Street Journal crypto coverage"],
      "why_helpful": "The primary source that started the collapse - most videos cite it secondhand"
    }}
  ],
  "rabbit_holes": [
    {{
      "topic": "The Bahamas regulatory environment",
      "mentioned_in": "Video 2 briefly mentioned FTX's Bahamas HQ at 8:45",
      "potential_angle": "Why did FTX choose Bahamas? What oversight existed? Could be unique angle most creators skip",
      "based_on": ["CLIP_6"],
      "confidence": "speculative"
    }},
    {{
      "topic": "Effective altruism connection",
      "mentioned_in": "Multiple videos mention EA briefly but don't explore",
      "potential_angle": "The EA community's response and soul-searching after FTX collapse - unexplored human interest angle",
      "based_on": ["QUOTE_3", "CLIP_11"],
      "confidence": "medium"
    }}
  ],
  "content_angles": [
    {{
      "angle": "Focus on the 8 days from CoinDesk article to bankruptcy",
      "differentiator": "Most videos cover the whole FTX story. Zooming into just the collapse week would be more focused and dramatic",
      "why_unique": "Allows deeper detail on each day's events rather than surface-level overview of years",
      "based_on": ["CLIP_14", "CLIP_15", "QUOTE_8"],
      "confidence": "high"
    }},
    {{
      "angle": "Interview format with an actual FTX customer who lost funds",
      "differentiator": "All existing videos are narrator-driven. Real victim perspective is missing",
      "why_unique": "Humanizes the story - viewer connects emotionally rather than just intellectually",
      "based_on": [],
      "confidence": "speculative"
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
9. CITATIONS ARE REQUIRED: Every search_query, rabbit_hole, and content_angle MUST include:
   - "based_on": array of clip/quote IDs from the input that support this suggestion
   - "confidence": "high" (directly supported), "medium" (inferred), or "speculative" (intuition)
   - If you cannot cite evidence, set confidence to "speculative"
10. Return empty arrays if no genuine suggestions exist - don't invent to meet quotas
11. If returning empty arrays, MUST include "analysis_warnings" explaining WHY

## WARNING REQUIREMENT
If any array is empty, include "analysis_warnings" field:
```json
{{
  "rabbit_holes": [],
  "analysis_warnings": [
    "rabbit_holes empty: Gap analysis identified no tangential topics worth exploring - main topic well-covered"
  ]
}}
```
"""
