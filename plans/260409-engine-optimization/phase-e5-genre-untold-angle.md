---
phase: E-5
title: "Genre Prompts + Untold Angle Hero"
status: pending
effort: 2-3h
risk: low
depends_on: [E-3]
---

# E-5: Genre Prompts + Untold Angle as Hero

**What:** Wire OpenClaw's genre-specific narrative structures into the synthesis prompt. Surface the "untold angle" (gap analysis) as the first section of the Research Brief, not buried at the bottom.
**Why:** This is what differentiates from NotebookLM. A conspiracy brief should feel different from a history brief. The untold angle is the unique value prop — it needs to be the first thing creators see.

## Part 1: Genre-Aware Synthesis Prompt

### Source: OpenClaw Genre System
Already built in `/Users/mazbot/.openclaw/workspace/shared/genres/`:
- `conspiracy.md` → Crack and Reveal + Contradiction Drop hook
- `history.md` / `pre-history.md` → Freytag (adapted) + In Medias Res
- `fan-theory.md` → Kishōtenketsu + Missed Detail hook
- `corporate.md` → Harmon's Story Circle + Contradiction Drop
- `science.md` / `geography.md` → Revelation Structure + Implication First
- `pop-culture.md` / `news-politics.md` → Inverted Pyramid + Zeitgeist Question
- `true-crime.md` → Investigation Structure + False Floor hook
- `religion.md` → Mythology Structure + Mythology Cold hook

### Changes

#### 1. New file: `backend/pipeline/genre_system.py`
```python
GENRE_PROMPTS = {
    "conspiracy": """Structure this brief using the Crack and Reveal pattern:
        - Open with the accepted narrative
        - Introduce the crack (the contradiction or hidden connection)
        - Build evidence layer by layer
        - Reveal the full picture""",
    "history": """Structure this brief using adapted Freytag structure:
        - Open In Medias Res (drop into the pivotal moment)
        - Backfill context
        - Build to the turning point
        - Show consequences""",
    # ... etc for each genre
}

def get_genre_prompt(content_type: str) -> str:
    """Get genre-specific synthesis instructions."""
    return GENRE_PROMPTS.get(content_type, GENRE_PROMPTS.get("default", ""))
```

#### 2. Modify merged gap+synthesis stage (from E-3)
Inject genre prompt into the synthesis portion of the merged prompt:

```python
genre_instructions = get_genre_prompt(ctx.content_type)
prompt = f"""
{base_prompt}

## GENRE-SPECIFIC STRUCTURE
{genre_instructions}
"""
```

#### 3. `backend/pipeline/context.py` — ensure content_type is available
Check that `PipelineContext` carries `content_type` from the job config. If not, add it.

## Part 2: Untold Angle as Hero Section

### Current: gaps buried
Gap analysis results stored in `ctx.identified_gaps` and rendered as a separate section at the bottom of Doc 2.

### New: gaps lead the brief
In the merged gap+synthesis prompt, instruct the model:

```
## UNTOLD ANGLE (LEAD WITH THIS)
Before the main synthesis, identify THE single most compelling angle
that no existing source has fully explored. This becomes the opening
section of the brief.

Format:
"THE UNTOLD ANGLE: [one sentence]"
[2-3 sentences explaining why this angle matters and what evidence supports it]
[Which sources partially touch it but don't go deep enough]
```

### Changes

#### 4. Modify document assembly template
In `backend/pipeline/stages/document_assembly.py`, restructure Doc 2 template so "Untold Angle" is the first section, followed by the genre-structured synthesis, followed by detailed gaps.

## Tests
- Test genre prompt selection for each content type
- Test that untold angle appears as first section in Doc 2
- Test fallback for unknown content types (default generic structure)

## Success Criteria
- Brief structure varies by content type
- Conspiracy brief feels different from history brief
- "Untold angle" is the first thing creators read
- Genre prompt doesn't override fact accuracy
