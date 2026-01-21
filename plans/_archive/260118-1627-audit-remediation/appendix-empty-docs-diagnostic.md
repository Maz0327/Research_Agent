# Appendix: Empty Document Diagnostic Guide

**Related to:** Pipeline debugging, not audit remediation
**Purpose:** Quick reference for diagnosing empty Doc 0/1/2

---

## Root Cause: Pipeline Data Flow

Empty docs almost always = upstream stages didn't produce inputs.

```
Discovery → Capture → Identity → Extraction → Synthesis → Assembly
    ↓           ↓         ↓           ↓            ↓          ↓
 sources    content   packages   extractions  synthesis   Doc 0/1/2
```

If any stage produces zero output → downstream stages have nothing to process.

---

## Document Dependencies

| Document | Data Source | Empty If |
|----------|-------------|----------|
| **Doc 0** (Source Ledger) | `ctx.source_identity_packages` | No packages or all inaccessible |
| **Doc 1** (Jump-Start) | `ctx.semantic_extractions` | extraction count = 0 |
| **Doc 2** (Semantic Brief) | `ctx.synthesis` | Falls back to generic if nothing synthesized |

---

## Common Failure Points

### 1. No Sources Found (Discovery)

**Stage:** `stage_3_source_shortlist`
**Location:** `backend/pipeline/stages/discovery.py:15-100`

**Causes:**
- Missing `EXA_API_KEY` → Exa search fails
- Missing `PERPLEXITY_API_KEY` → Perplexity fallback fails
- Quality Gate filters all sources (`approved_count = 0`)

**Warnings to look for:**
```
"No sources found in shortlist"
"Perplexity API key required"
"Exa search failed"
```

### 2. Web Content Missing (Capture)

**Stage:** `stage_6_web_capture`
**Location:** `backend/pipeline/stages/web_capture.py`

**Causes:**
- Jina/Trafilatura extraction fails
- Playwright unavailable (no Chrome on cloud)
- Blocked egress
- Articles return empty text → marked inaccessible

**Warnings to look for:**
```
"V2 extraction failed, using Playwright"
"Web capture failed"
"No content extracted"
```

### 3. YouTube Path Issues

**Stages:** `stage_4_youtube_enumeration`, `stage_5_transcripts`
**Location:** `backend/pipeline/stages/` (enumeration + transcripts)

**Causes:**
- Missing `YOUTUBE_API_KEY` → zero videos enumerated
- Missing `SUPADATA_API_KEY` → transcript fallback to Whisper
- Whisper fails → `video_only` mode
- Missing `GOOGLE_API_KEY` → Gemini video analysis fails
- Gemini video analysis fails → zero observations

**Warnings to look for:**
```
"Transcript missing for video ..."
"Video analysis failed"
"YouTube API key required"
```

### 4. Semantic Extraction/Synthesis Skipped

**Stages:** `stage_semantic_extraction`, `stage_semantic_synthesis`
**Location:** `backend/pipeline/stages/semantic_extraction.py`

**Causes:**
- `source_identity_packages` is empty → extraction skipped
- `semantic_extractions` is empty → synthesis skipped

**Warnings to look for:**
```
"No source identity packages - skipping extraction"
"No extractions available - skipping synthesis"
```

---

## Quick Diagnostic via API

### Check Job Status
```bash
GET /jobs/{job_id}
```

**Inspect these fields:**
```json
{
  "artifacts": {
    "doc_0_path": "...",  // null if empty
    "doc_1_path": "...",
    "doc_2_path": "..."
  },
  "documents_ready": {
    "doc_0": { "inline": true, "storage": false },
    "doc_1": { "inline": true, "storage": false },
    "doc_2": { "inline": true, "storage": false }
  },
  "outputs": {
    "source_identity_summary": {
      "total_sources": 0,  // ← Problem indicator
      "accessible": 0,
      "per_source": [...]
    },
    "semantic_extraction_summary": {
      "sources_processed": 0,  // ← Problem indicator
      "sources_failed": 0,
      "sources_skipped": 5  // ← Why skipped?
    },
    "semantic_synthesis_summary": null,  // ← Missing = no extractions
    "document_assembly_summary": {...}
  },
  "warnings": [
    "Perplexity API key required",  // ← Root cause
    "No sources found"
  ]
}
```

---

## Two Most Common Culprits

1. **No EXA_API_KEY and no PERPLEXITY_API_KEY**
   - Result: "No sources found in shortlist"
   - Fix: Set at least one API key

2. **SUPADATA/Gemini missing**
   - Result: Video extraction produces nothing
   - Summary shows: `processed=0`, `skipped>0`
   - Fix: Set `SUPADATA_API_KEY` and `GOOGLE_API_KEY`

---

## Required API Keys Checklist

| Key | Purpose | Impact if Missing |
|-----|---------|-------------------|
| `EXA_API_KEY` | Source discovery (primary) | Falls back to Perplexity |
| `PERPLEXITY_API_KEY` | Source discovery (fallback) | No sources if Exa also fails |
| `GOOGLE_API_KEY` | Gemini extraction/synthesis/video | Pipeline fails |
| `SUPADATA_API_KEY` | Transcripts (primary) | Falls back to Whisper |
| `YOUTUBE_API_KEY` | Video enumeration | No YouTube sources |

---

## Quick Fixes

### 1. Ensure Core Keys Set
```bash
# .env
EXA_API_KEY=...
PERPLEXITY_API_KEY=...
GOOGLE_API_KEY=...
SUPADATA_API_KEY=...
YOUTUBE_API_KEY=...
```

### 2. Loosen Quality Gate Temporarily
If `quality_gate_stats.approved_count == 0`:
- Reduce thresholds
- Or disable quality gate to confirm it's the blocker

### 3. Verify Web Capture Environment
- Playwright needs Chromium installed
- Cloud: confirm sandbox allows network egress

### 4. Increase Budgets
Low `max_web_urls` and `transcription_minutes` can starve inputs.

### 5. Check Synthesis Runs
If `semantic_synthesis_summary` is missing:
- Fix discovery/capture/transcripts first
- Synthesis only runs if extractions exist

---

## Inline Stub Diagnostics

When using Supabase Storage, inline stubs now include:
- Job ID and topic
- Note about cloud storage
- **Top 10 warnings** from the run

If you open a doc card and see only the stub, read the warnings—they usually state the root cause.

---

## Related Files

| File | Purpose |
|------|---------|
| `backend/pipeline/stages/discovery.py` | Source shortlist (Exa/Perplexity) |
| `backend/pipeline/stages/web_capture.py` | Web content extraction |
| `backend/pipeline/stages/source_identity.py` | Identity resolution |
| `backend/pipeline/stages/semantic_extraction.py` | Semantic extraction |
| `backend/pipeline/stages/semantic_synthesis.py` | Cross-source synthesis |
| `backend/pipeline/stages/document_assembly.py` | Doc 0/1/2 assembly |
