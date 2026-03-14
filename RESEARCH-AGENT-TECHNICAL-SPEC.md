# Research Agent Output Redesign — TECHNICAL SPECIFICATION
## Concrete Implementation Details for Claude Code

**Status:** IMPLEMENTATION READY  
**Created:** March 6, 2026  
**Scope:** Complete rewrite of Docs 1-3 + Visual Analysis Pipeline  

---

## SECTION 1: IMMEDIATE CHANGES — DOC 1 PROMPT

### File to Modify
`backend/pipeline/prompts/jumpstart_prompt.py` (NEW FILE)

### Current Problem
Doc 1 uses tables with IDs (KP_1, TEN_1, GAP_1) and source-by-source breakdown. Need thematic threads.

### New Prompt Template

```python
JUMPSTART_PROMPT = """
You are a research assistant briefing a documentary creator.

## INPUT DATA
Topic: {topic}
Scope In: {scope_in}
Scope Out: {scope_out}

Sources Analyzed: {source_count}

Key Claims:
{claims}

Themes Identified:
{themes}

Gaps Found:
{gaps}

Tensions:
{tensions}

## YOUR TASK

Create a RESEARCH BRIEF that helps the creator understand:
1. What research threads emerge across sources (NOT source-by-source)
2. What gaps need filling before filming
3. Exactly what to search for next

## OUTPUT FORMAT — RESEARCH BRIEF

```
RESEARCH BRIEF: {topic}
Sources: {source_count} | Generated: [current date]

═══════════════════════════════════════════════════

EXECUTIVE SUMMARY

[2-3 sentences on the central tension/theme]

═══════════════════════════════════════════════════

RESEARCH THREADS

Thread 1: [Descriptive Name] (Sources X, Y, Z)
├─ What the Sources Say:
│  • Source X: "[specific claim — verbatim if possible]"
│  • Source Y: "[specific claim]"
│  • Source Z: "[specific claim]"
│
├─ The Gap:
│  [What's missing — be specific]
│
└─ Next Research Move:
   Search: "[exact search query]"
   Why: [what this fills]
   Where: [specific platform/site]
   Verify: [how to confirm]

[Repeat for 3-7 threads]

═══════════════════════════════════════════════════

CROSS-CUTTING ISSUES

Confirmed by Multiple Sources:
• "[Claim]" — Sources: X, Y, Z

Claims in Conflict:
• Source X: "[Claim A]" vs Source Y: "[Claim B]"
  └─ Resolution: [how to verify]

Single-Source (High Risk):
• "[Claim]" — Only in Source X
  └─ Risk: [defamation/error if wrong]

═══════════════════════════════════════════════════

PRIORITY RESEARCH QUEUE

Priority 1 (Do Today):
□ [Task] — Time: [X min/hours]
  Search: "[query]"

Priority 2 (This Week):
□ [Task] — Time: [X min/hours]
  Search: "[query]"
```

## RULES

1. NO TABLES — use the tree structure shown above
2. NO IDs — reference sources naturally ("Source 1", not "SRC_1")
3. GROUP BY THREAD — combine sources discussing same topic
4. SPECIFIC QUERIES — every "Next Research Move" must have exact search terms
5. EVERY CLAIM CITED — every statement traces to a source

## EXAMPLE OUTPUT

Thread 1: Environmental Hypocrisy (Sources 1, 3)
├─ What the Sources Say:
│  • Source 1: "The WEF claims to fight climate change"
│  • Source 3: "1,500 private jets flew to Davos 2023"
│
├─ The Gap:
│  No official WEF response to this contradiction
│
└─ Next Research Move:
   Search: "WEF response private jets Davos 2023"
   Why: Get their side of the story
   Where: weforum.org press releases
   Verify: Look for official statements, not third-party coverage
```
"""
```

### Code Change in document_assembly.py

```python
def build_jump_start(
    scope_lock: tuple[list[str], list[str]],
    extractions: list[SemanticExtractionResult],
    gaps: list[Gap],
) -> JumpStartDirections:
    """Build Doc 1: Research Brief with thematic threads."""
    
    # Aggregate by theme instead of by source
    threads = aggregate_by_theme(extractions, gaps)
    
    # Build cross-cutting analysis
    confirmed, conflicts, single_source = analyze_cross_cutting(extractions)
    
    # Generate priority queue
    queue = build_priority_queue(gaps)
    
    return JumpStartDirections(
        scope_in=scope_in,
        scope_out=scope_out,
        research_threads=threads,
        cross_cutting=CrossCuttingIssues(
            confirmed=confirmed,
            conflicts=conflicts,
            single_source=single_source,
        ),
        priority_queue=queue,
    )
```

---

## SECTION 2: IMMEDIATE CHANGES — DOC 2 PROMPT

### File to Modify
`backend/pipeline/prompts/semantic_brief_prompt.py` (NEW FILE)

### New Prompt Template

```python
SEMANTIC_BRIEF_PROMPT = """
You are a story consultant helping a documentary creator choose their angle.

## INPUT DATA

Research Threads from Doc 1:
{research_threads}

Cross-Cutting Issues:
{cross_cutting_issues}

Gaps Still Open:
{gaps}

## YOUR TASK

Help the creator decide what story to tell. Provide:
1. What angles are common (avoid these)
2. What angles are fresh (consider these)
3. A clear recommendation with reasoning

## OUTPUT FORMAT — STORY BRIEF

```
STORY BRIEF: {topic}
Based on: {source_count} sources | Generated: [date]

═══════════════════════════════════════════════════

THE CENTRAL STORY

[2-3 sentence pitch]

═══════════════════════════════════════════════════

STORY LANDSCAPE

Common Angles (Avoid — Saturated):
• "[Angle]" — Done by: [channels] — Risk: [why avoid]

Untold Angles (Fresh — Consider):
• "[Angle]" — Source basis: [threads] — Why fresh: [difference]

═══════════════════════════════════════════════════

STORY ANGLE OPTIONS

Angle A: [Name] — Confidence: [High/Med/Low]
├─ The Story: [2-3 sentences]
├─ Why It Works: [evidence from threads]
├─ Risks: [what could go wrong]
└─ If This Angle: [what changes]

Angle B: [Name] — Confidence: [High/Med/Low]
[Same structure]

Angle C: [Name] — Confidence: [High/Med/Low]
[Same structure]

═══════════════════════════════════════════════════

RECOMMENDED ANGLE

Go with Angle [B] because: [2-3 sentences of reasoning]

Next Step: [specific action]
```

## RULES

1. BE DECISIVE — give a clear recommendation, not "here are options"
2. GROUND IN THREADS — every angle must reference Doc 1 threads
3. ACKNOWLEDGE GAPS — note which gaps affect which angles
4. SPECIFIC NEXT STEP — not "do more research" but "find X to verify Y"
"""
```

---

## SECTION 3: IMMEDIATE CHANGES — DOC 3 PROMPT

### File to Modify
`backend/pipeline/prompts/producer_prompt.py` (COMPLETE REWRITE)

### New Prompt Template

```python
PRODUCER_PROMPT = """
You are a producer creating a shooting script from research.

## INPUT DATA

Selected Angle: {selected_angle}
Research Threads: {threads}
Visual Research: {visual_research}

## YOUR TASK

Create a PRODUCTION BLUEPRINT — a shooting script + production guide.

## OUTPUT FORMAT — PRODUCTION BLUEPRINT

```
PRODUCTION BLUEPRINT: {topic}
Angle: {angle_name} | Target: {length} min | Generated: [date]

═══════════════════════════════════════════════════

ACT STRUCTURE

ACT I: SETUP [0:00 - 2:00]
├─ Hook (0:00 - 0:30)
│  • Visual: [what opens]
│  • Audio: [opening line]
│  • Source: [specific clip]
│
├─ Context (0:30 - 1:30)
│  • Key facts: [from research]
│
└─ Inciting Incident (1:30 - 2:00)
   • Moment: [what launches story]

ACT II: EXPLORATION [2:00 - 45:00]
├─ Beat 1: [Topic] (2:00 - 10:00)
│  • Visual: [sequence]
│  • Narration: [key points]
│  • Clips: [timestamps]
│  • B-roll: [what to source]
│
[Beats 2-4...]

ACT III: RESOLUTION [45:00 - 55:00]
[Climax, Fallout, Outro]

═══════════════════════════════════════════════════

CLIP SHEET

Timecode | Source | Type | Description | Original Source | Use In
---------|--------|------|-------------|-----------------|-------
0:00:45 | Vid 1 | ✅ Movie | [desc] | [studio] | Act I
0:02:30 | Vid 1 | ❌ Skip | Creator | N/A | SKIP

═══════════════════════════════════════════════════

B-ROLL SHOPPING LIST

Must Source:
• [Description] — Search: "[query]"

═══════════════════════════════════════════════════

PRODUCTION NOTES

Audio: [music mood, pacing]
Visual: [color grade, style]
Legal: [claims needing review]
```

## RULES

1. EVERY BEAT TIMED — specific minute marks
2. CLIP TYPES MARKED — ✅ third-party / ❌ original / ⚠️ review
3. SPECIFIC QUERIES — every B-roll has search terms
4. GROUNDED IN RESEARCH — every claim traces to Doc 0/1
"""
```

---

## SECTION 4: VISUAL ANALYSIS PIPELINE

### New File: backend/services/frame_extraction.py

```python
"""Frame extraction service for visual analysis."""

import subprocess
from pathlib import Path
from typing import List


def extract_keyframes(
    video_path: str,
    output_dir: str,
    interval_seconds: int = 5,
) -> List[str]:
    """
    Extract keyframes from video at specified interval.
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save frames  
        interval_seconds: Seconds between frames
        
    Returns:
        List of frame file paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"fps=1/{interval_seconds},scale=1920:-1",
        "-q:v", "2",
        str(output_path / "frame_%04d.jpg")
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return sorted([str(f) for f in output_path.glob("*.jpg")])
```

### New File: backend/integrations/kimi_vision_client.py

```python
"""Kimi K2.5 Vision client for visual analysis."""

import base64
import os
from typing import List, Dict, Any
import requests


class KimiVisionClient:
    """Client for Kimi K2.5 Vision API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MOONSHOT_API_KEY")
        self.base_url = "https://api.moonshot.ai/v1"
        
    def analyze_video_frames(
        self,
        frame_paths: List[str],
        video_title: str,
        research_topic: str,
    ) -> Dict[str, Any]:
        """Analyze video frames with Kimi K2.5."""
        
        # Prepare frames (limit to 20 for API)
        frames_base64 = []
        for path in frame_paths[:20]:
            with open(path, "rb") as f:
                frames_base64.append(base64.b64encode(f.read()).decode())
        
        # Build messages with images
        messages = [
            {
                "role": "system",
                "content": "You analyze video frames for documentary research."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyze these frames from '{video_title}' for research on: {research_topic}\n\nIdentify visual moments, classify clip types (third-party vs original), and suggest B-roll."
                    },
                    *[
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
                        }
                        for frame in frames_base64
                    ]
                ]
            }
        ]
        
        # Call API
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "kimi-k2.5",
                "messages": messages,
                "response_format": {"type": "json_object"}
            }
        )
        
        return response.json()["choices"][0]["message"]["content"]
```

---

## SECTION 5: MODEL UPDATES

### Update: backend/models/document_outputs.py

Add to JumpStartDirections:

```python
@dataclass
class ResearchThread:
    """A thematic thread combining multiple sources."""
    name: str
    sources: List[str]  # Source IDs
    claims: List[str]   # Claim statements
    gap: str            # What's missing
    next_search: str    # Exact query
    search_purpose: str # Why this search
    search_where: str   # Where to search
    verify_how: str     # How to confirm

@dataclass
class CrossCuttingIssues:
    """Issues that cut across multiple sources."""
    confirmed: List[ConfirmedClaim]
    conflicts: List[ClaimConflict]
    single_source: List[RiskyClaim]

@dataclass
class JumpStartDirections:
    """Doc 1: Research Brief with threads."""
    scope_in: List[str]
    scope_out: List[str]
    research_threads: List[ResearchThread]
    cross_cutting: CrossCuttingIssues
    priority_queue: List[ResearchTask]
    # Remove: key_points table, tensions table, gaps table
```

---

## SECTION 6: IMPLEMENTATION ORDER

### Week 1: Doc 1
1. Create `jumpstart_prompt.py` with new template
2. Update `document_assembly.py` to use threads
3. Update `JumpStartDirections` model
4. Test with sample research job

### Week 2: Docs 2 & 3  
1. Create `semantic_brief_prompt.py`
2. Create `producer_prompt.py` (rewrite)
3. Update synthesis and producer stages
4. Update models
5. Test end-to-end

### Week 3: Visual Pipeline
1. Create `frame_extraction.py`
2. Create `kimi_vision_client.py`
3. Add visual section to Doc 0
4. Integrate into pipeline

### Week 4: Integration
1. Update clip export to use visual analysis
2. End-to-end testing
3. Performance optimization

---

## SECTION 7: TESTING CHECKLIST

### Doc 1 Tests
- [ ] Output has NO tables
- [ ] Sources referenced naturally ("Source 1", not "SRC_1")
- [ ] Every thread has specific search query
- [ ] Every gap has actionable next step
- [ ] Cross-cutting issues identified

### Doc 2 Tests
- [ ] Clear angle recommendation given
- [ ] All angles grounded in Doc 1 threads
- [ ] Visual storytelling guidance included
- [ ] Risks have mitigation plans

### Doc 3 Tests
- [ ] Complete act structure with timing
- [ ] Clip sheet distinguishes ✅/❌/⚠️
- [ ] B-roll has specific search queries
- [ ] Every beat grounded in research

### Visual Pipeline Tests
- [ ] Frames extract successfully
- [ ] Kimi K2.5 returns valid JSON
- [ ] Clip types correctly classified
- [ ] Processing time < 2x video duration

---

**This specification is ready for Claude Code implementation.**
