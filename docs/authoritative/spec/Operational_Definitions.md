# Operational Definitions

**Purpose:** Authoritative vocabulary for the Research Agent system.
**Rule:** All documents inherit definitions from this file. Terms MUST NOT be redefined elsewhere.

---

## Source & Identity Terms

### Source
A discrete unit of input content provided by the user for analysis. Each source has exactly one `source_id` and exactly one `analysis_mode`.

**Types:**
- YouTube video (URL)
- Article (URL)
- User-provided text (copy-paste)
- Screenshot (image file)

### source_id
A stable, unique identifier for a source within a job. Format: `SRC_1`, `SRC_2`, etc. Assigned during Source Identity stage, before any LLM call.

### Source Identity Package
The complete metadata bundle for a source, resolved BEFORE any LLM processing:
- `source_id`
- `title`
- `creator` (if available)
- `date` (if available)
- `duration` (for video)
- `analysis_mode`
- `confidence_ceiling`
- `transcript_provenance` (for video)

---

## Analysis Mode Terms

### Analysis Mode
The method used to analyze a source, determined by source type and content availability. Affects confidence ceiling and extraction capabilities.

| Mode | Definition |
|------|------------|
| `transcript_grounded` | YouTube video with full transcript (Supadata or Whisper) |
| `caption_grounded` | YouTube video with YouTube captions only |
| `video_only` | YouTube video with no text available |
| `text_provided` | User-pasted text content |
| `ocr_extracted` | Screenshot processed with OCR |
| `article_fetched` | Article URL with full text retrieved |

### Confidence Ceiling
The maximum confidence level any extraction from a source can claim, determined by analysis mode:

| Mode | Ceiling |
|------|---------|
| `transcript_grounded` | HIGH |
| `caption_grounded` | MEDIUM |
| `video_only` | LOW |
| `text_provided` | MEDIUM |
| `ocr_extracted` | MEDIUM |
| `article_fetched` | HIGH |

### Transcript Provenance
Metadata recording how a video's transcript was obtained:
- `method`: supadata | whisper | youtube_captions | none
- `quality`: high | medium | low | unavailable
- `timestamp_reliability`: precise | approximate | unavailable

---

## Confidence Terms

### Confidence Level
A categorical assessment of certainty. Three levels only:

| Level | Definition |
|-------|------------|
| `HIGH` | Directly verifiable in source text; verbatim or near-verbatim |
| `MEDIUM` | Reasonable interpretation of source content; paraphrased |
| `LOW` | Inferred or uncertain; limited source support |

### Confidence Calibration
The practice of ensuring confidence levels accurately reflect certainty. Extraction cannot exceed the source's confidence ceiling.

---

## Extraction Terms

### Semantic Extraction
The process of identifying meaningful content from a source: key points, claims, themes, tensions, quotes (if allowed), and gaps.

### Key Point
A significant statement or idea from a source. Must reference `source_id`.

Fields:
- `key_point_id`: Unique ID (format: `KP_1`, `KP_2`)
- `statement`: The key point in clear language
- `source_ids`: List of supporting source IDs
- `confidence`: Confidence level
- `timestamp`: If from video (optional)

### Claim
A factual assertion made within a source that could be verified or disputed. Descriptive only — no judgment on truth.

Fields:
- `claim_id`: Unique ID (format: `CLM_1`, `CLM_2`)
- `statement`: The claim as stated
- `source_id`: Single source ID
- `speaker`: Who made the claim (if identifiable)
- `confidence`: Confidence level
- `verifiable`: Boolean — can this be fact-checked?

### Quote
Verbatim or near-verbatim text from a source. Only allowed for modes with text available.

Fields:
- `quote_id`: Unique ID (format: `QT_1`, `QT_2`)
- `text`: The quoted text
- `source_id`: Single source ID
- `speaker`: Who said it (if identifiable)
- `timestamp`: When in video (if applicable)
- `verification_status`: verified | partial | unverified

### Approximate Observation
A semantic description of content for sources without verifiable text (`video_only`, `text_provided`, `ocr_extracted`). NOT a quote.

Fields:
- `observation_id`: Unique ID (format: `OBS_1`, `OBS_2`)
- `description`: What was observed (semantic description)
- `source_id`: Single source ID
- `timestamp`: Approximate time (if video)
- `approximate`: Always `true`
- `type`: Always `observation`

**Critical distinction:** Quotes are verbatim text. Observations are descriptions of content. Never call an observation a quote.

### Theme
A recurring idea, topic, or pattern identified within or across sources.

Fields:
- `theme_id`: Unique ID (format: `THEME_1`, `THEME_2`)
- `name`: Short theme name
- `description`: What this theme represents
- `source_ids`: Sources where this theme appears
- `supporting_key_points`: Key point IDs that support this theme

### Tension
A contradiction, disagreement, or unresolved conflict between sources or within a source.

Fields:
- `tension_id`: Unique ID (format: `TEN_1`, `TEN_2`)
- `description`: What the tension is
- `sources_involved`: Source IDs involved
- `nature`: factual_dispute | perspective_difference | timeline_conflict | other
- `resolution_status`: unresolved | partially_resolved | resolved

### Gap
Missing information, unanswered questions, or areas needing further research.

Fields:
- `gap_id`: Unique ID (format: `GAP_1`, `GAP_2`)
- `description`: What's missing
- `importance`: high | medium | low
- `suggested_sources`: Potential places to find this information
- `research_queries`: Suggested search queries

---

## Pipeline Terms

### Source Isolation
The requirement that each source be extracted in a separate, isolated LLM call. The model never sees other sources during extraction. Cross-source analysis only happens in synthesis.

### Layered Extraction
The required extraction approach:
- **Layer 1:** Explicit content — what the source directly states
- **Layer 2:** Patterns — what patterns exist in Layer 1 content
- **Layer 3:** Structure — themes, tensions, gaps derived from Layer 2

### Synthesis
The stage where extracted content from multiple sources is analyzed together to identify cross-source themes, tensions, and patterns. This is the ONLY stage where sources "see" each other.

### Validation
The stage where extractions are verified:
- Quote verification (does quote exist in source text?)
- Confidence ceiling enforcement
- Timestamp validation
- Source ID consistency

### Assembly
The stage where validated extractions and synthesis results are formatted into output documents (Doc 0, Doc 1, Doc 2).

---

## Document Terms

### Doc 0 — Source Ledger
The canonical data layer. Contains full source text, metadata, provenance, and indexes. No interpretation. Single source of truth.

### Doc 1 — Jump-Start Directions
The research direction layer. Answers: "What do I have, what's missing, where do I go next?" Contains gaps, research directions, suggested queries, next steps.

### Doc 2 — Semantic Research Brief
The analysis layer. Contains themes, key points, tensions, confidence calibration. The "80% finished" semantic understanding of the corpus.

### Doc 3 — Producer Packet
The optional creative layer. Contains story angles, hooks, structure options, creative interpretation. Gated: requires 4+ sources, 1+ high-confidence, explicit user request.

### Addendum
Content added to existing documents when new sources are added to a completed job. Clearly marked as additions, preserves original analysis.

---

## Quality Terms

### Degraded Output
Output produced when ideal conditions aren't met (e.g., no transcript available). Still valid, but with:
- Lower confidence ceiling
- Explicit disclosure of limitations
- Emphasis on gaps

### Thin Output
Output with minimal content due to source limitations. Acceptable if honest about limitations. Preferred over hallucinated dense output.

### Hallucination
Content generated by LLM that has no basis in source material. System is designed to prevent this through:
- Source isolation
- Confidence ceilings
- Quote verification
- Empty output permission

---

## Job Terms

### Job
A single analysis request containing one or more sources. Has a `job_id`, status, and produces Doc 0/1/2 (and optionally Doc 3).

### Job Status
- `pending`: Created, not started
- `running`: Pipeline executing
- `completed`: Successfully finished
- `completed_with_warnings`: Finished with degradation
- `failed`: Unrecoverable error
- `cancelled`: User cancelled

### Evolving Job
A job that has new sources added after initial completion. Uses addendum pattern to preserve original analysis.

---

## Booster Terms

### Deep Research Booster
Optional 4-stage pipeline that expands research directions beyond the current corpus. Augments Doc 1 only. Does not modify canonical data.

**Stages:**
1. Gap Analysis — deep analysis of missing information
2. Research Directions — prioritized next steps
3. Search Queries — concrete queries to run
4. Context Bundle — package for continued research

---

## Producer Packet Terms

### Story Core
The central narrative question or angle for a documentary.

### Hook
An attention-grabbing opening element (cold open, provocative question, surprising fact).

### Structure Options
Different ways to organize the narrative (chronological, thematic, mystery-reveal, etc.).

### Creative Interpretation
Content in Doc 3 that goes beyond factual extraction into narrative territory. Always explicitly labeled as interpretation.

---

## Validation Terms

### Quote Verification
Checking that extracted quotes actually exist in source text. Uses fuzzy matching to account for minor transcription differences.

Statuses:
- `verified`: Exact or near-exact match found
- `partial`: Partial match found
- `unverified`: No match found (flagged, not removed)

### Confidence Enforcement
Automatic downgrade of confidence levels that exceed the source's ceiling. Logged as warning.

### Source ID Consistency
Verification that all extracted items reference valid source IDs from the job.

---

## ID Format Reference

| Entity | Format | Example |
|--------|--------|---------|
| Source | `SRC_N` | `SRC_1`, `SRC_2` |
| Key Point | `KP_N` | `KP_1`, `KP_2` |
| Claim | `CLM_N` | `CLM_1`, `CLM_2` |
| Quote | `QT_N` | `QT_1`, `QT_2` |
| Observation | `OBS_N` | `OBS_1`, `OBS_2` |
| Theme | `THEME_N` | `THEME_1`, `THEME_2` |
| Tension | `TEN_N` | `TEN_1`, `TEN_2` |
| Gap | `GAP_N` | `GAP_1`, `GAP_2` |

---

**END OF OPERATIONAL DEFINITIONS**
