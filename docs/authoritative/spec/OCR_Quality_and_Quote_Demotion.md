# docs/authoritative/spec/OCR_Quality_and_Quote_Demotion.md

**Purpose:** Make OCR behavior machine-enforceable so the system cannot “guess” how to treat messy OCR.

---

## 1) Required outputs for screenshot sources

For every screenshot source (`source_type=screenshot`, `analysis_mode=ocr_extracted`) the system MUST produce:
- `ocr_provenance.method`
- `ocr_provenance.ocr_quality` (high|medium|low)
- `full_text` (or blob reference)
- `degradation_notes` when quality != high

---

## 2) OCR Quality grading (authoritative requirements)

The system MUST compute `ocr_quality` using deterministic heuristics.

### 2.1 Required signals
At minimum, compute all these signals:
- `alnum_ratio` = (# letters+digits) / (total chars)
- `symbol_ratio` = (# non-whitespace, non-alnum symbols) / (total chars)
- `short_token_ratio` = (# tokens length <= 2) / (total tokens)
- `avg_token_len`
- `repeated_char_runs` = count of sequences like `aaaa`, `1111`, `----` length >= 4
- `line_noise_ratio` = proportion of lines that are mostly symbols/garbage

### 2.2 Required classification
The system MUST classify using thresholds. Exact thresholds may be tuned, but MUST be explicit in code.

A safe default baseline (allowed):
- **high** if:
  - alnum_ratio >= 0.70 AND
  - symbol_ratio <= 0.12 AND
  - short_token_ratio <= 0.25 AND
  - repeated_char_runs <= 2

- **medium** if not high and:
  - alnum_ratio >= 0.50 AND
  - symbol_ratio <= 0.20

- **low** otherwise

### 2.3 Storage
Store the chosen `ocr_quality` in:
- Doc 0 `sources[].ocr_provenance.ocr_quality`

---

## 3) Quote demotion rule (non-negotiable)

### 3.1 Low quality (messy OCR)
If `ocr_quality == low`:
- The system MUST NOT emit quotes for this source.
- Any quote-like strings MUST be converted into observations.
- The system MUST append a warning string (exact text recommended):
  - `OCR messy: treated quote-like lines as observations; wording is not reliable.`

### 3.2 Medium quality
If `ocr_quality == medium`:
- Quotes MAY be emitted.
- Any emitted quote MUST include:
  - `accuracy_unverified=true`
  - `verbatim_confidence=medium`
  - `provenance=user_provided`

### 3.3 High quality
If `ocr_quality == high`:
- Quotes MAY be emitted.
- Any emitted quote MUST include:
  - `accuracy_unverified=true`
  - `verbatim_confidence=high`
  - `provenance=user_provided`

---

## 4) What counts as “quote-like” (authoritative)

A string is quote-like if ANY is true:
- it appears in extraction output under a “quotes” field
- it contains quotation marks with a multi-word phrase
- it is formatted as dialogue (e.g., `NAME: ...`)
- it is a short line that attempts exact wording (e.g., slogan, headline)

When in doubt, treat as quote-like.

---

## 5) Validation rules (authoritative)

During semantic validation:
- If `analysis_mode==ocr_extracted` AND `ocr_quality==low` AND any quote exists for that source:
  - HARD FAIL **unless** the system demotes them to observations before validation.

---

## 6) Output examples

### 6.1 High-quality OCR (quotes allowed)
- quote: `accuracy_unverified=true`, `verbatim_confidence=high`, `provenance=user_provided`

### 6.2 Low-quality OCR (quotes forbidden)
- observations only + warning

---

**END**

