---
phase: E-4
title: "Sonnet Editorial Pass"
status: pending
effort: 3-4h
risk: medium
depends_on: [E-3]
---

# E-4: Sonnet Editorial Pass

**What:** After synthesis produces the Research Brief (Doc 2), send it through Claude Sonnet 4.6 for an editorial pass. Runs as a background Celery task — user sees raw brief immediately, polished version replaces it.
**Why:** Cross-model rewriting scores 44% better than self-editing. Sonnet excels at tightening prose, improving readability, and reshaping structure. Gemini is faithful but dense — Sonnet makes it readable.
**Risk:** Medium — new dependency (Anthropic SDK), needs API key configuration, must preserve all facts/citations.

## Architecture

```
Synthesis (Gemini Pro) → Raw Doc 2 stored → User sees it immediately
                      → Background: Sonnet editorial pass
                      → Polished Doc 2 replaces raw version
                      → User notified "Enhanced version ready"
```

## Changes

### 1. `requirements.txt` — add Anthropic SDK
```
anthropic>=0.40.0
```

### 2. `backend/config.py` — Sonnet configuration
```python
# Sonnet Editorial Pass
anthropic_api_key: Optional[str] = Field(
    default=None, alias="ANTHROPIC_API_KEY",
    description="Anthropic API key for Sonnet editorial pass (optional)"
)
sonnet_editorial_enabled: bool = Field(
    default=True, alias="SONNET_EDITORIAL_ENABLED",
    description="Enable Sonnet editorial pass on Research Brief"
)
sonnet_editorial_model: str = Field(
    default="claude-sonnet-4-6", alias="SONNET_EDITORIAL_MODEL",
    description="Sonnet model for editorial pass"
)
```

### 3. New file: `backend/integrations/anthropic_client.py`
```python
class AnthropicClient:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def editorial_pass(self, content: str, genre: Optional[str] = None) -> dict:
        """Run editorial pass on research brief content."""
        # Returns: {"content": "polished text", "cost": float}
```

### 4. New file: `backend/pipeline/stages/editorial_pass.py`
```python
def run_editorial_pass(ctx: PipelineContext, doc_content: str) -> str:
    """Send Research Brief through Sonnet for editorial polish."""
```

**Editorial prompt (critical — this is the make-or-break):**
```
You are a creative editor for documentary content creators. Your job is to reshape
this research brief for maximum readability and impact.

RULES:
- PRESERVE every fact, claim, citation, source reference, and quote exactly
- PRESERVE all [SRC_X] references and [CLM_X] markers
- DO NOT add any information not in the original
- DO NOT remove any factual content

RESHAPE:
- Lead with the most surprising or compelling finding
- Cut redundant phrasing — say it once, say it well
- Break long paragraphs into scannable chunks
- Use direct, active voice — address the creator as "you"
- Add transitions between sections that build narrative momentum
- Flag the "untold angle" prominently if gaps were identified

The creator should finish reading this and think: "I know exactly what video to make."
```

### 5. `backend/worker.py` — new Celery task
```python
@celery_app.task(name="backend.worker.run_editorial_task")
def run_editorial_task(job_id: str) -> dict:
    """Run Sonnet editorial pass on Research Brief (Doc 2)."""
    # 1. Load job and Doc 2 content
    # 2. Run editorial pass via AnthropicClient
    # 3. Store polished version (new version of Doc 2)
    # 4. Update job metadata: editorial_status = "complete"
```

### 6. `backend/worker.py` — trigger after document assembly
After `stage_document_assembly` completes, fire the editorial task:

```python
# After document assembly (line ~472):
if settings.sonnet_editorial_enabled and settings.anthropic_api_key:
    run_editorial_task.delay(job_id)
```

### 7. `.env.example` — document new settings
```
ANTHROPIC_API_KEY=sk-ant-...
SONNET_EDITORIAL_ENABLED=true
SONNET_EDITORIAL_MODEL=claude-sonnet-4-6
```

## Cost
- ~$0.04-0.08 per editorial pass (Research Brief is ~2-5K tokens input, ~2-5K output)
- Prompt caching available for the editorial system prompt (90% savings on repeated calls)

## Tests
- Test editorial pass preserves all citations (regex check for [SRC_X] markers)
- Test editorial pass doesn't add content (word count shouldn't increase significantly)
- Test graceful degradation when Anthropic key not configured
- Test background task runs independently

## Success Criteria
- Raw brief available immediately after synthesis
- Polished brief replaces raw version within 15-30s
- All facts, citations, source references preserved exactly
- Output reads like a creator brief, not a research paper
- Graceful fallback when Anthropic key not set (raw brief stays)
