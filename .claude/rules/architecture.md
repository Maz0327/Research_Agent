# Architecture Rules

**Priority:** CRITICAL — These architectural decisions are FINAL. Do NOT violate without explicit owner approval.

---

## Pipeline Architecture

### Rule 1: Source Isolation
Each source is extracted in a **SEPARATE, ISOLATED LLM call**.

```
✅ CORRECT:
Source 1 → LLM Call 1 → Extraction 1
Source 2 → LLM Call 2 → Extraction 2
Source 3 → LLM Call 3 → Extraction 3
[Extraction 1, 2, 3] → Synthesis Call

❌ WRONG:
[Source 1, Source 2, Source 3] → Single LLM Call
```

**Rationale:** Prevents cross-source hallucination, guarantees provenance accuracy.

### Rule 2: Synthesis is Cross-Source Only
Cross-source analysis (themes, tensions) happens ONLY in synthesis stage, AFTER all extractions complete.

### Rule 3: Pipeline Order
```
INGESTION → EXTRACTION → VALIDATION → SYNTHESIS → ASSEMBLY
```
Never skip stages. Never reorder stages.

---

## Confidence Rules

### Rule 4: Confidence Ceilings by Mode

| Mode | Ceiling | Quotes |
|------|---------|--------|
| `transcript_grounded` | HIGH | Yes (verbatim) |
| `caption_grounded` | MEDIUM | Yes (approximate) |
| `video_only` | LOW | **NO** |
| `text_provided` | MEDIUM | Yes (unverified)* |
| `ocr_extracted` | MEDIUM | Yes (unverified)* |
| `article_fetched` | HIGH | Yes (verbatim) |

> *\*Owner Decision (2026-01-15): TEXT_PROVIDED and OCR_EXTRACTED allow quotes but marked as unverified. System cannot verify authenticity of user-provided content, but extracting quotes provides better UX than omitting them entirely.*

### Rule 5: Ceiling Enforcement
If extraction returns confidence higher than ceiling:
1. Validation catches it
2. Auto-correct to ceiling value
3. Log warning

```python
# Validation must enforce:
if key_point.confidence > ceiling:
    key_point.confidence = ceiling
    warnings.append(f"Confidence exceeded ceiling for {key_point.id}")
```

### Rule 6: No Quotes in No-Quote Modes
For `video_only` mode only:
- Prompt must NOT have quotes field
- Schema must NOT have quotes field
- Validation must reject if quotes present
- Use `approximate_observations` instead

For `text_provided` and `ocr_extracted` modes:
- Quotes ARE allowed (per owner decision)
- All quotes must be marked with `unverified: true`
- Validation adds warning: "Quote accuracy unconfirmed by system"

---

## Prompt Requirements

### Rule 7: Five Required Components
ALL LLM prompts must include:

#### 1. Source Identity Lock
```
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  source_id: {source_id}                                  ║
║  title: {title}                                          ║
║  analysis_mode: {mode}                                   ║
║  confidence_ceiling: {ceiling}                           ║
╚══════════════════════════════════════════════════════════╝
```

#### 2. Confidence Ceiling Declaration
```
CONFIDENCE CEILING: {ceiling}
Your maximum allowed confidence is: {ceiling}
Any output exceeding this will be rejected.
```

#### 3. Empty Output Permission
```
EMPTY OUTPUT PERMISSION
Return empty arrays if no content found.
DO NOT invent content to fill arrays.
Sparse, accurate > dense, hallucinated.
```

#### 4. Layered Extraction (extraction prompts only)
```
LAYER 1: Explicit statements only
LAYER 2: Patterns from Layer 1
LAYER 3: Themes from Layer 2
```

#### 5. Output Schema
```json
{
  "key_points": [...],
  "claims": [...],
  ...
}
```

### Rule 8: No Prompt Without Guardrails
Never send a prompt to Gemini without all 5 components present.

---

## Data Models

### Rule 9: Source ID Required
Every extracted item must have `source_id`:

```python
class KeyPoint(BaseModel):
    key_point_id: str
    statement: str
    source_ids: List[str]  # REQUIRED, cannot be empty
    confidence: ConfidenceLevel
```

### Rule 10: Provenance Chain
```
Theme → references → KeyPoints → reference → source_ids
Tension → references → KeyPoints → reference → source_ids
KeyPoint → references → Quotes/Observations → reference → source_id
```

Broken chain = validation failure.

### Rule 11: ID Naming Convention
```
source_id: SRC_1, SRC_2, SRC_3, ...
key_point_id: KP_1, KP_2, KP_3, ...
claim_id: CLM_1, CLM_2, CLM_3, ...
quote_id: QT_1, QT_2, QT_3, ...
observation_id: OBS_1, OBS_2, OBS_3, ...
theme_id: THEME_1, THEME_2, ...
tension_id: TEN_1, TEN_2, ...
gap_id: GAP_1, GAP_2, ...
```

---

## Output Documents

### Rule 12: Three Core Documents
Every completed job produces:
- **Doc 0:** Source Ledger
- **Doc 1:** Jump-Start Directions
- **Doc 2:** Semantic Brief

### Rule 13: Optional Documents
- **Doc 3:** Producer Packet (user-triggered)
- **Addendum:** When sources added to existing job
- **Booster:** When deep research triggered

### Rule 14: Document Independence
Each document is self-contained. Reader should not need other docs to understand.

---

## LLM Configuration

### Rule 15: Gemini JSON Mode Always
All Gemini calls must use:
```python
generation_config={
    "response_mime_type": "application/json",
    "response_schema": PydanticModel
}
```

### Rule 16: Temperature by Stage
```
Extraction: 0.1 (deterministic)
Validation: N/A (code, not LLM)
Synthesis: 0.2 (slight flexibility)
Booster: 0.4 (variety wanted)
Producer: 0.3-0.5 (creative layer)
```

---

## Prohibited Architecture Changes

### DO NOT:
- Combine extraction calls for multiple sources
- Remove source isolation
- Allow confidence above ceiling
- Skip validation stage
- Add quotes to no-quote modes
- Remove prompt guardrails
- Change document structure without approval
- Use different LLM without approval
- Change temperature settings without approval

---

## When in Doubt

1. Check DECISIONS.md for rationale
2. Default to stricter interpretation
3. Ask owner before proceeding
