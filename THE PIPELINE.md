# THE PIPELINE

**Last Updated:** 2026-01-18
**Purpose:** Quick reference for the actual active pipeline flow

---

## NEW Pipeline (User-Provided Sources)

Users provide sources directly. No automatic discovery.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     USER-PROVIDED SOURCES PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 1: USER INPUT                                                 ║  │
│  ╠══════════════════════════════════════════════════════════════════════╣  │
│  ║  User provides:                                                      ║  │
│  ║  • YouTube URLs ────────────────> video_urls[]                       ║  │
│  ║  • Article URLs ────────────────> article_urls[]                     ║  │
│  ║  • Screenshots (base64) ────────> screenshots[]                      ║  │
│  ║  • Copy-paste text ─────────────> text_inputs[]                      ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                                    ▼                                        │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 2: SOURCE IDENTITY                                            ║  │
│  ╠══════════════════════════════════════════════════════════════════════╣  │
│  ║  For each source, build identity package:                            ║  │
│  ║  • YouTube ──────> fetch transcript (Supadata) → analysis_mode       ║  │
│  ║  • Article ──────> fetch content (Trafilatura) → analysis_mode       ║  │
│  ║  • Screenshot ───> OCR (Gemini Vision) → analysis_mode               ║  │
│  ║  • Text ─────────> use directly → analysis_mode                      ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                                    ▼                                        │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 3: SEMANTIC EXTRACTION (Gemini)                               ║  │
│  ╠══════════════════════════════════════════════════════════════════════╣  │
│  ║  For EACH source (isolated LLM calls):                               ║  │
│  ║  • Extract key points, claims, quotes ──────> Gemini 2.5-pro         ║  │
│  ║  • Confidence ceiling enforced per analysis_mode                     ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                                    ▼                                        │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 4: VALIDATION                                                 ║  │
│  ╠══════════════════════════════════════════════════════════════════════╣  │
│  ║  • Semantic Validation ─────────> Code (confidence penalties)        ║  │
│  ║  • LLM Judge ───────────────────> GPT-4o cross-model validation      ║  │
│  ║  • RAG Grounding (optional) ────> Verify claims against source text  ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                                    ▼                                        │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 5: SYNTHESIS (Gemini)                                         ║  │
│  ╠══════════════════════════════════════════════════════════════════════╣  │
│  ║  • Gap Analysis ────────────────> Gemini 2.5-pro                     ║  │
│  ║  • Semantic Synthesis ──────────> Gemini 2.5-pro (cross-source)      ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                        │
│                                    ▼                                        │
│  ╔══════════════════════════════════════════════════════════════════════╗  │
│  ║  PHASE 6: OUTPUT                                                     ║  │
│  ╠══════════════════════════════════════════════════════════════════════╣  │
│  ║  • Document Assembly ───────────> Builds Doc 0/1/2                   ║  │
│  ║  • Drive Upload ────────────────> Google Drive API                   ║  │
│  ╚══════════════════════════════════════════════════════════════════════╝  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Source Types & Analysis Modes

| Source Type | How Processed | Analysis Mode | Confidence Ceiling |
|-------------|---------------|---------------|-------------------|
| YouTube URL | Fetch transcript (Supadata) | `transcript_grounded` | HIGH |
| YouTube URL | Fetch captions (fallback) | `caption_grounded` | MEDIUM |
| YouTube URL | No transcript available | `video_only` | LOW (no quotes) |
| Article URL | Fetch content (Trafilatura) | `article_fetched` | HIGH |
| Screenshot | OCR via Gemini Vision | `ocr_extracted` | MEDIUM |
| Copy-paste text | Use directly | `text_provided` | MEDIUM |

---

## Stage Reference (NEW Pipeline)

| Stage | Name | What It Does | API Used |
|-------|------|--------------|----------|
| - | User Input | User provides sources via API/UI | None |
| A | Source Identity | Builds identity package for each source | Supadata, Trafilatura, Gemini Vision |
| B | Semantic Extraction | Extracts key points, claims, quotes (per source, isolated) | **Gemini 2.5-pro** |
| B.5 | Semantic Validation | Validates extraction, confidence penalties | Code only |
| C | Gap Analysis | Identifies missing info in current sources | **Gemini 2.5-pro** |
| D | Semantic Synthesis | Cross-source themes, tensions | **Gemini 2.5-pro** |
| E | Document Assembly | Builds Doc 0/1/2 from extractions | Code only |
| 9 | Drive Upload | Uploads documents to Google Drive | **Google Drive API** |

---

## What's NOT Used in New Pipeline

These stages from the OLD discovery pipeline are **SKIPPED**:

| Stage | Name | Status |
|-------|------|--------|
| 0 | Initialize | Skipped (no job config generation) |
| 1 | Planning | Skipped (no OpenAI disambiguation) |
| 2 | Research Mapping | Skipped (no Perplexity discovery) |
| 3 | Source Shortlist | Skipped (no Perplexity filtering) |
| 3.5 | Quality Gate | Skipped (user provides trusted sources) |
| 4 | YouTube Enumeration | Skipped (user provides exact URLs) |
| 5 | Transcripts | Moved to Source Identity |
| 6 | Web Capture | Moved to Source Identity |
| 6.5 | Reddit | Skipped (no automatic Reddit search) |

---

## Hallucination Prevention Status

### Active (Wired & Working)

| Feature | Location | Config Flag | Status |
|---------|----------|-------------|--------|
| Chain-of-Thought prompting | `pipeline/prompts/modes/base.py` | Always ON | **ACTIVE** |
| Anti-hallucination examples | `pipeline/prompts/modes/base.py` | Always ON | **ACTIVE** |
| Layer checkpoints | `pipeline/prompts/modes/base.py` | Always ON | **ACTIVE** |
| Enhanced retries (max=2) | `pipeline/stages/semantic_extraction.py` | Always ON | **ACTIVE** |
| Error-specific retry prompts | `pipeline/prompts/semantic_extraction_prompt.py` | Always ON | **ACTIVE** |
| Confidence penalties | `pipeline/semantic_validation.py` | Always ON | **ACTIVE** |
| Confidence rationale requirement | Schema + validation | Always ON | **ACTIVE** |
| **LLM Judge (GPT-4o)** | `pipeline/llm_judge.py` | `enable_llm_judge=True` | **ACTIVE** (default ON) |
| **RAG Grounding** | `pipeline/rag_grounding.py` | `enable_rag_grounding=False` | **ACTIVE** (default OFF) |

---

## Output Documents

| Doc | Name | Content |
|-----|------|---------|
| Doc 0 | Source Ledger | What was analyzed (sources, modes, ceilings) |
| Doc 1 | Jump-Start Directions | Where to go next (gaps, research directions) |
| Doc 2 | Semantic Brief | What sources reveal (key points, themes, tensions) |
| Doc 3 | Producer Packet | Creative interpretation (optional, user-triggered) |

---

## Key Files (NEW Pipeline)

| File | Purpose |
|------|---------|
| `backend/worker.py` → `_run_mixed_input_job()` | New pipeline orchestration |
| `backend/pipeline/stages/source_identity.py` | Builds identity packages |
| `backend/pipeline/stages/semantic_extraction.py` | Gemini extraction calls |
| `backend/pipeline/semantic_validation.py` | Validation logic |
| `backend/pipeline/prompts/modes/base.py` | Prompt templates |
| `backend/models/job_config.py` | HallucinationConfig flags |

---

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /jobs/mixed` | Submit job with user-provided sources |
| `GET /jobs/{id}` | Get job status |
| `GET /jobs/{id}/documents` | Get output documents |
| `POST /jobs/{id}/booster` | Trigger deep research booster |
| `POST /jobs/{id}/producer` | Trigger producer packet (Doc 3) |

---

## LEGACY Pipeline (Topic-Based Discovery)

The OLD pipeline where user provides a TOPIC and system finds sources:

```
User Topic → OpenAI Planning → Perplexity Discovery → Collection → Semantic Pipeline
```

This is still in `run_research_job()` but is the **OLD** approach.
The **NEW** approach is `_run_mixed_input_job()` where users provide sources directly.
