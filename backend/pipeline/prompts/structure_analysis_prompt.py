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
  }}
}}
```

## IMPORTANT RULES
1. Timestamps must be in MM:SS format for videos under 1 hour, or HH:MM:SS for longer videos (M-001)
2. Be specific about techniques - don't just say "good hook", explain WHY
3. Include at least 2-4 acts in the structure
4. Identify at least 2-3 open loops if present
5. NEVER use "unclear" or empty values. Always make your best assessment based on available information (M-002)
6. If the video structure is unconventional, describe it in detail rather than forcing it into standard categories
"""
