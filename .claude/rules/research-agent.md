# Research Agent Development Rules

## Architecture Rules

### Pipeline Development
- All pipeline stages are in `backend/pipeline/stages.py`
- Use `PipelineContext` for passing data between stages
- Wrap stage logic in try/except with `ctx.add_warning()` for non-fatal errors
- Update job progress with `update_job()` after each stage

### Integration Development
- All external API clients go in `backend/integrations/`
- Add configuration to `backend/config.py` with validation helper
- Implement graceful degradation with fallback chains
- Log all API calls with `loguru`

### Cost Awareness
- Track API costs per job (see `backend/pipeline/cost_tracker.py`)
- Respect budget limits in `JobConfig.budgets`
- Use cost-effective models for extraction (GPT-4o-mini)
- Reserve expensive models for synthesis only

## Code Patterns

### Error Handling
```python
try:
    result = external_api_call()
except ExternalAPIError as e:
    ctx.add_warning(f"API failed: {e}")
    result = fallback_strategy()
```

### Job State Updates
```python
await update_job(job_id, {
    "status": "running",
    "stage": "stage_name",
    "progress": 50,
    "updated_at": datetime.utcnow().isoformat()
})
```

## Quality Standards

### Sources
- Always run Quality Gate filtering on collected sources
- Deduplicate URLs with canonicalization
- Filter junk patterns (ads, paywalls, login walls)
- Score sources and apply mode-specific floors

### Transcripts
- Fallback chain: Supadata → Whisper → youtube-transcript-api
- Note: youtube-transcript-api fails on cloud IPs (Railway, AWS)
- Always store transcript source for debugging

### Claims
- Extract claims with confidence scores
- Validate high-confidence claims only
- Cross-reference against multiple sources
