# Pipeline Stages Reference

## Stage List

| # | Stage Name | Function | Output |
|---|------------|----------|--------|
| 1 | initialize | Set up context | PipelineContext |
| 2 | planning | AI generates config | JobConfig, short_title |
| 3 | research_mapping | Find angles & terms | angles, key_terms |
| 4 | source_discovery | Find URLs | web_sources |
| 5 | youtube_enumeration | Find videos | youtube_videos |
| 6 | transcript_extraction | Get transcripts | transcripts |
| 7 | web_capture | Capture pages | sources with content |
| 8 | reddit_collection | Get discussions | reddit_posts |
| 9 | extraction | Claims/Timeline/Entities | claims, timeline_events, entities |
| 10 | validation_analysis | Validate + Analyze | evidence_records, documentary_analysis |
| 11 | output_upload | Generate + Upload | folder_url, doc_urls |

## Stage Dependencies

```
1 → 2 → 3 → 4 ─┬→ 5 → 6 ─┐
               └→ 7 ────┤
               └→ 8 ────┴→ 9 → 10 → 11
```

- Stages 5-8 can run in parallel (future optimization)
- Stages 9-11 must be sequential

## Stage Context Fields

### After Stage 2 (Planning)
```python
ctx.job_config: JobConfig
ctx.short_title: str
ctx.niche_config: Optional[dict]
```

### After Stage 3-4 (Research Mapping + Discovery)
```python
ctx.angles: List[str]
ctx.key_terms: List[str]
ctx.web_sources: List[dict]
```

### After Stage 5-8 (Collection)
```python
ctx.youtube_videos: List[dict]
ctx.transcripts: List[dict]
ctx.reddit_posts: List[dict]
```

### After Stage 9 (Extraction)
```python
ctx.claims: List[dict]
ctx.timeline_events: List[dict]
ctx.entities: dict
```

### After Stage 10 (Analysis)
```python
ctx.evidence_records: List[dict]
ctx.discovered_angles: dict
ctx.documentary_analysis: dict
```

### After Stage 11 (Output)
```python
ctx.folder_url: str
ctx.doc_urls: dict
ctx.outputs: dict  # Markdown documents
```

## Error Handling Per Stage

Each stage should:
1. Wrap main logic in try/except
2. Use `ctx.add_warning()` for non-fatal errors
3. Continue with partial results when possible
4. Only raise exceptions for truly fatal errors

Example:
```python
async def stage_extraction(ctx: PipelineContext) -> None:
    try:
        claims = await extract_claims(ctx.transcripts, ctx.web_sources)
        ctx.claims = claims
    except OpenAIError as e:
        ctx.add_warning(f"Claim extraction failed: {e}")
        ctx.claims = []  # Continue with empty claims
```
