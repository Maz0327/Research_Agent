# Analysis Mode: article_fetched

**Status:** AUTHORITATIVE
**Version:** 1.0
**Last Updated:** 2026-01-14

---

## 1. Mode Definition

`article_fetched` is a **high fidelity** analysis mode for web articles. It applies when the system successfully fetches and extracts the full text content from a non-video URL.

### 1.1 When This Mode Applies

| Source Type | Extraction Method | Mode Assignment |
|-------------|-------------------|-----------------|
| News article | Jina Reader / Trafilatura | `article_fetched` |
| Blog post | Content extraction | `article_fetched` |
| Press release | Content extraction | `article_fetched` |
| Documentation | Content extraction | `article_fetched` |
| PDF | PDF text extraction | `article_fetched` |

### 1.2 Mode Characteristics

| Property | Value |
|----------|-------|
| Confidence Ceiling | **HIGH** |
| Quotes Allowed | **YES** — verbatim from extracted text |
| Quote Verification | **REQUIRED** — string matching |
| Timestamp Grounding | **N/A** — articles don't have timestamps |
| Semantic Precision | **HIGH** |
| Provenance | **SYSTEM_EXTRACTED** — verified |

---

## 2. Confidence Rules

### 2.1 Ceiling Enforcement

```
MAXIMUM ALLOWED CONFIDENCE: HIGH

Extraction may assign:
- high: Clear, explicit statements with verbatim quote support
- medium: Statements with some ambiguity
- low: Inferred or weakly supported statements
```

### 2.2 Confidence Assignment Criteria

| Confidence | Criteria |
|------------|----------|
| HIGH | Direct statement with exact quote match from article |
| MEDIUM | Clear statement but context-dependent interpretation |
| LOW | Implied or requires inference |

---

## 3. Quote Extraction Rules

### 3.1 Requirements

- **Verbatim text required** — exact words from article
- **Paragraph/section reference** — location in article
- **Speaker attribution** — if quoting a person cited in article

### 3.2 Quote Selection Criteria

Prioritize quotes that:
1. Support key points with direct evidence
2. Contain significant claims or revelations
3. Attribution to specific sources/speakers
4. Provide specific facts, dates, numbers
5. Are likely to be controversial or contested

### 3.3 Quote Format

```json
{
  "quote_id": "QT_1",
  "text": "The company reported a 40% decline in quarterly revenue",
  "speaker": "Company spokesperson",
  "location": "paragraph 3",
  "context": "Discussing financial results"
}
```

### 3.4 Quote Prohibitions

- **NO paraphrasing** — exact words from article
- **NO combining** — each quote is atomic
- **NO invention** — quote must exist in extracted text
- **NO headline quotes** — prefer body content

---

## 4. Article Extraction

### 4.1 Extraction Service Options

| Service | Priority | Notes |
|---------|----------|-------|
| Jina Reader | Primary | Free, good quality |
| Trafilatura | Secondary | Good for news sites |
| Diffbot | Tertiary | Higher quality, costs |
| Readability | Fallback | Basic extraction |

### 4.2 Extraction Failure Handling

| Scenario | Mode Assignment |
|----------|-----------------|
| Full text extracted | `article_fetched` |
| Partial extraction | `article_fetched` with warning |
| Paywall detected | Fail with helpful message |
| Extraction failed | Source excluded, job continues |

### 4.3 Paywall Detection

```python
def detect_paywall(extracted_text: str, response: Response) -> bool:
    indicators = [
        len(extracted_text) < 200,              # Very short content
        "subscribe" in extracted_text.lower(),  # Common paywall word
        "sign in" in extracted_text.lower(),
        response.status_code == 403,
        response.headers.get("X-Paywall") == "true"
    ]
    return sum(indicators) >= 2
```

**On Paywall Detection:**
```
Error: This content appears to be paywalled.
Suggestion: Use text input mode to paste accessible content.
Action: Source marked as extraction_failed, job continues.
```

---

## 5. Validation Requirements

### 5.1 Mandatory Checks

| Check | Description | On Failure |
|-------|-------------|------------|
| V1 | Valid JSON matching schema | Hard fail, retry once |
| V2 | source_id matches input exactly | Hard fail, retry once |
| V3 | No confidence exceeds HIGH | Auto-downgrade, warn |
| V4 | Quote verification via string match | Soft fail, warn |
| V8 | Article metadata present | Soft warning |

### 5.2 Quote Verification Process

```python
def verify_article_quote(quote_text: str, article_text: str) -> VerificationResult:
    """Verify quote exists in article text."""
    normalized_quote = normalize_whitespace(quote_text.lower())
    normalized_article = normalize_whitespace(article_text.lower())

    if normalized_quote in normalized_article:
        return VerificationResult(status="verified", confidence=1.0)

    # Fuzzy match for minor extraction variations
    similarity = fuzzy_match(normalized_quote, normalized_article)
    if similarity >= 0.90:  # Higher threshold than video
        return VerificationResult(status="partially_verified", confidence=similarity)

    return VerificationResult(status="unverified", confidence=0.0)
```

---

## 6. Provenance Requirements

### 6.1 Required Metadata

```python
@dataclass
class ArticleFetchedProvenance:
    source_id: str                    # SRC_X format
    source_type: str = "article"
    input_mode: str = "url"
    analysis_mode: str = "article_fetched"

    # Extraction details
    extraction_service: str           # "jina_reader" | "trafilatura" | etc.
    extraction_success: bool = True
    extracted_length: int             # Character count

    # Verification status
    provenance: str = "system_extracted"
    system_verified: bool = True      # System fetched and extracted

    # Confidence
    confidence_ceiling: str = "high"

    # Metadata (system-extracted)
    title: str                        # From page or extraction
    creator: Optional[str]            # Author if detected
    url: str                          # Original URL
    date: Optional[str]               # Published date if detected
    site_name: Optional[str]          # Source publication
```

### 6.2 Provenance Display

```
Source: SRC_1
Mode: article_fetched (HIGH confidence)
URL: https://example.com/article
Extraction: Jina Reader (verified)
Quotes: Verbatim from article text

Site: Example News
Author: Jane Doe
Published: 2026-01-10
```

---

## 7. Output Schema

```json
{
  "source_id": "SRC_1",
  "analysis_mode": "article_fetched",
  "extraction_metadata": {
    "extracted_at": "2026-01-14T10:30:00Z",
    "model": "gemini-2.5-pro",
    "confidence_ceiling": "high",
    "provenance": "system_extracted",
    "system_verified": true,
    "extraction_service": "jina_reader"
  },
  "key_points": [
    {
      "key_point_id": "KP_1",
      "statement": "string",
      "confidence": "high",
      "supporting_quote_ids": ["QT_1"]
    }
  ],
  "claims": [
    {
      "claim_id": "CLM_1",
      "statement": "string",
      "speaker": "string or null",
      "confidence": "high",
      "verifiable": true
    }
  ],
  "quotes": [
    {
      "quote_id": "QT_1",
      "text": "verbatim quote from article",
      "speaker": "string or null",
      "location": "paragraph reference",
      "context": "brief context"
    }
  ],
  "themes": [...],
  "tensions": [...],
  "entities": [...],
  "gaps": [...]
}
```

---

## 8. Edge Cases

### 8.1 Article Is Very Long

**Scenario:** Article exceeds token limits (50,000+ words).

**Handling:**
- Truncate with clear boundary note
- Add warning: "Article truncated due to length"
- Focus extraction on lead paragraphs
- Note what was excluded

### 8.2 Article Has Embedded Media

**Scenario:** Article contains videos, images, embedded tweets.

**Handling:**
- Extract text content only
- Note presence of media: "Article contains embedded video"
- Do NOT attempt to extract media content
- Media should be separate sources if relevant

### 8.3 Article Is A Listicle/Slideshow

**Scenario:** Article is structured as slides or paginated list.

**Handling:**
- Extract all accessible pages/slides
- Note format: "Multi-page article"
- If only first page accessible, add warning
- Combine pages into single extraction

### 8.4 Article Is Actually A PDF

**Scenario:** URL points to a PDF document.

**Handling:**
- Use PDF text extraction
- Mode remains `article_fetched`
- Note in provenance: "PDF document"
- Add warning if extraction quality is poor

### 8.5 Extraction Returns Mainly Navigation/Ads

**Scenario:** Content extraction captured sidebar, not main article.

**Handling:**
- Detect low content quality
- Retry with different extraction service
- If still poor, mark as `extraction_failed`
- Return helpful error message

---

## 9. Prompt Template Reference

Use `Gemini_Semantic_Extraction.md` with:
- Quote Instructions template
- Schema WITH quotes
- Confidence ceiling: HIGH
- Additional context: Article metadata (title, author, date)

---

## 10. Invariants (Always True)

1. **Quotes are verbatim** — from extracted article text
2. **Confidence ceiling is HIGH** — extraction may use high/medium/low
3. **Quote verification runs** — all quotes checked against article
4. **system_verified is TRUE** — system fetched the content
5. **URL is the source of truth** — content came from this URL
6. **Extraction service recorded** — provenance shows how content was obtained

---

## 11. Comparison to Similar Modes

| Aspect | article_fetched | text_provided |
|--------|-----------------|---------------|
| Text source | System fetched | User paste |
| Confidence ceiling | HIGH | MEDIUM |
| Quotes allowed | YES | NO |
| system_verified | TRUE | FALSE |
| URL verified | YES | NO |

| Aspect | article_fetched | transcript_grounded |
|--------|-----------------|---------------------|
| Source type | Web article | Video |
| Confidence ceiling | HIGH | HIGH |
| Quotes allowed | YES | YES |
| Timestamps | N/A | Required |
| Content format | Paragraphs | Timeline |

---

## 12. Integration with Transcript Modes

When a URL points to a page with embedded video:
- Article text → `article_fetched`
- Video transcript → separate source, `transcript_grounded`
- Both can coexist in same job as separate sources

---

**END OF MODE SPECIFICATION**
