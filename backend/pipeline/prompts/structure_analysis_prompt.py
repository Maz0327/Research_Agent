"""Pass 2: Structure Analysis Prompt for video reverse-engineering.

Analyzes a single video's structure, hook, narrative arc, and production techniques.
Outputs a ContentBlueprint per video.
"""

STRUCTURE_ANALYSIS_PROMPT = """You are a video production analyst reverse-engineering a YouTube video's structure and technique.

Analyze this video and identify what makes it effective. Your goal is to help a content creator understand the video's "formula" so they can create similar content.

## VIDEO TO ANALYZE
URL: {video_url}
Title: {video_title}

## ANALYSIS REQUIRED

### 1. HOOK ANALYSIS (First 10-30 seconds)
Identify how the video grabs attention:
- What technique is used? (pattern interrupt, provocative question, shocking statement, etc.)
- Why does it work?
- What's the timestamp when the hook ends?

### 2. NARRATIVE STRUCTURE
Identify the framework used:
- 3-Act Structure (Setup → Conflict → Resolution)
- Story Circle (You → Need → Go → Search → Find → Take → Return → Change)
- Problem-Solution-Benefit
- Chronological/Timeline
- Villain Origin Story
- Investigation/Mystery reveal
- Other (describe)

For each major section/act, provide:
- Name of the section
- Start timestamp (MM:SS)
- End timestamp (MM:SS)
- Brief description of what happens

### 3. RE-ENGAGEMENT POINTS (Open Loops)
Identify moments where the creator plants questions or teases to keep viewers watching:
- What timestamp?
- What technique? (question, tease, cliffhanger, "but first...")
- What does it make the viewer wonder?

### 4. VISUAL/STYLE
Describe the production approach:
- Pacing: high-energy (fast cuts) / medium (balanced) / lo-fi (relaxed)
- Editing style: documentary / vlog / essay / entertainment

### 5. SOURCE TRACING
What primary sources did they likely use?
- Books, articles, documentaries referenced
- Interviews or clips from other sources
- Any explicitly mentioned sources

## OUTPUT FORMAT
Return valid JSON:
```json
{{
  "video_url": "{video_url}",
  "title": "{video_title}",
  "hook": {{
    "timestamp_end": "MM:SS",
    "technique": "pattern interrupt | provocative question | shocking statement | etc.",
    "description": "Brief explanation of what the hook does"
  }},
  "narrative": {{
    "structure_type": "3-act | story circle | problem-solution | investigation | etc.",
    "acts": [
      {{
        "name": "Section name",
        "timestamp_start": "MM:SS",
        "timestamp_end": "MM:SS",
        "description": "What happens in this section"
      }}
    ]
  }},
  "open_loops": [
    {{
      "timestamp": "MM:SS",
      "technique": "question | tease | cliffhanger | callback",
      "description": "What it makes the viewer wonder"
    }}
  ],
  "style": {{
    "pacing": "high-energy | medium | lo-fi",
    "editing_style": "documentary | vlog | essay | entertainment"
  }},
  "sources": {{
    "likely_primary_sources": ["List of probable main sources"],
    "referenced_materials": ["Explicitly mentioned books, articles, etc."]
  }},
  "analysis_warnings": ["Required if any field returned empty - explain WHY"]
}}
```

## EXAMPLE OUTPUT (for a video about "The Rise and Fall of WeWork"):

NOTE: This example shows a video with clear structure and multiple open loops.
Some videos may have simpler structures or fewer hooks. Match the QUALITY
and SPECIFICITY of analysis, not the QUANTITY of items.

```json
{{
  "video_url": "https://youtube.com/watch?v=example",
  "title": "WeWork: How a $47 Billion Company Lost Everything",
  "hook": {{
    "timestamp_end": "0:42",
    "technique": "shocking statement",
    "description": "Opens with 'In 2019, WeWork was worth $47 billion. Six weeks later, it was nearly bankrupt.' Uses extreme contrast to create immediate curiosity about how such a dramatic fall happened."
  }},
  "narrative": {{
    "structure_type": "villain-origin-story",
    "acts": [
      {{
        "name": "The Vision",
        "timestamp_start": "0:42",
        "timestamp_end": "8:30",
        "description": "Introduces Adam Neumann's charisma and the 'community company' pitch. Shows early success and how investors bought in."
      }},
      {{
        "name": "The Cracks",
        "timestamp_start": "8:30",
        "timestamp_end": "18:15",
        "description": "Reveals self-dealing, bizarre spending, and governance issues. Introduces Masayoshi Son and SoftBank's $100B fund."
      }},
      {{
        "name": "The IPO Disaster",
        "timestamp_start": "18:15",
        "timestamp_end": "26:40",
        "description": "The S-1 filing exposes the problems. Valuation collapses from $47B to $8B. Neumann ousted."
      }},
      {{
        "name": "The Aftermath",
        "timestamp_start": "26:40",
        "timestamp_end": "31:20",
        "description": "Layoffs, Neumann's $1.7B exit package controversy, and questions about startup culture."
      }}
    ]
  }},
  "open_loops": [
    {{
      "timestamp": "3:15",
      "technique": "tease",
      "description": "Mentions 'But there's one investor who would change everything' then cuts away - makes viewer wonder who."
    }},
    {{
      "timestamp": "12:45",
      "technique": "question",
      "description": "Asks 'How did no one notice?' after showing accounting issues - promises answer later."
    }},
    {{
      "timestamp": "22:10",
      "technique": "cliffhanger",
      "description": "Shows Neumann's face during IPO prep and says 'What the public didn't know yet...' - creates suspense."
    }}
  ],
  "style": {{
    "pacing": "medium",
    "editing_style": "documentary"
  }},
  "sources": {{
    "likely_primary_sources": ["The Wall Street Journal's WeWork reporting", "Billion Dollar Loser by Reeves Wiedeman", "WeWork S-1 filing"],
    "referenced_materials": ["Interview clips from CNBC", "We Crashed podcast mentioned at 15:20"]
  }},
  "analysis_warnings": []
}}
```

**Example with warnings (sparse video):**
```json
{{
  "open_loops": [],
  "analysis_warnings": [
    "open_loops empty: Video uses straightforward chronological structure without explicit re-engagement hooks",
    "referenced_materials empty: No specific sources mentioned by name in video"
  ]
}}
```

## IMPORTANT RULES
1. Timestamps must be in MM:SS format for videos under 1 hour, or HH:MM:SS for longer videos (M-001)
2. Be specific about techniques - don't just say "good hook", explain WHY it works
3. Include at least 2-4 acts in the structure
4. Identify at least 2-3 open loops if present
5. If video lacks certain elements (e.g., no clear open loops), return empty array for that field - don't invent them
6. If the video structure is unconventional, describe it in detail rather than forcing it into standard categories

## ANTI-HALLUCINATION RULES (SA-001)

You MUST NOT:
- Invent timestamps you didn't observe in the video
- Speculate about creator intent beyond what's explicitly stated or shown
- Add open loops that weren't explicitly planted by the creator
- Guess sources the creator didn't mention or clearly reference
- Fabricate act boundaries that aren't clearly signaled in the video

If uncertain about any element:
- Return empty array for that field
- Add explanation to "analysis_warnings" array (REQUIRED if any field is empty)
- Do NOT guess or approximate
- Prefer honest sparsity over false specificity

Every timestamp must be:
- Observed directly in the video content
- Formatted as MM:SS (or HH:MM:SS for videos over 1 hour)
- Within the video's actual duration

Sources must be:
- Explicitly mentioned OR clearly visible (on-screen text, logos)
- Categorized as "likely_primary_sources" only if strongly implied
- Listed in "referenced_materials" only if explicitly named
"""
