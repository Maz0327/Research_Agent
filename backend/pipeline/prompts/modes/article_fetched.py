"""Article Fetched Mode - Full article text available.

Analysis Mode: article_fetched
Confidence Ceiling: HIGH
Quotes: Yes (verbatim)

Used when: Web article fetched via Jina Reader or similar
"""

from .base import build_base_prompt


MODE_INSTRUCTIONS = """
## MODE: article_fetched

You are analyzing a FETCHED WEB ARTICLE with full text content.

### Source Characteristics
- Full article text was fetched from the web
- Content is complete (not excerpted)
- Source URL and metadata are known
- Text is authoritative (matches original publication)

### Capabilities
- Extract VERBATIM quotes from article
- Use article structure (headings, paragraphs)
- Maximum confidence: HIGH

### Quote Extraction Rules
- Quotes MUST be word-for-word from article
- Include author/speaker attribution when available
- Include section or paragraph context
- Quotes support claims which support key points

### Verification
- All quotes can be verified against fetched content
- Mismatched quotes will be flagged
- Fabricated quotes will cause validation failure

### Output Requirements
Include "quotes" array with this structure:
```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "Exact verbatim text from article",
    "speaker": "Author name or quoted person",
    "context": "Section or paragraph context",
    "location": "Section heading or paragraph description"
  }
]
```

For articles with clear structure, include:
```json
"article_structure": {
  "sections": ["Introduction", "Main Argument", "Evidence", "Conclusion"],
  "author": "Author name",
  "publication_date": "YYYY-MM-DD if available"
}
```
"""


QUOTE_SCHEMA = """
### Quote Schema (article_fetched mode)

```json
"quotes": [
  {
    "quote_id": "QT_1",
    "text": "string - EXACT verbatim text from article",
    "speaker": "string - author or quoted person",
    "context": "string - what was being discussed",
    "location": "string - section heading or paragraph"
  }
],

"article_structure": {
  "sections": ["string - section names"],
  "author": "string - author name if available",
  "publication_date": "string - YYYY-MM-DD if available"
}
```

CRITICAL: Quotes MUST be verbatim. Do NOT paraphrase or summarize.
Article text is authoritative and can be verified.
"""


def build_article_fetched_prompt(
    source_id: str,
    source_content: str,
    title: str = "Unknown",
) -> str:
    """Build prompt for article_fetched mode.

    Args:
        source_id: Stable source identifier
        source_content: Full article text
        title: Article title

    Returns:
        Complete prompt with all 5 components
    """
    return build_base_prompt(
        source_id=source_id,
        source_content=source_content,
        title=title,
        analysis_mode="article_fetched",
        confidence_ceiling="HIGH",
        mode_specific_instructions=MODE_INSTRUCTIONS,
        quote_schema_extension=QUOTE_SCHEMA,
    )
