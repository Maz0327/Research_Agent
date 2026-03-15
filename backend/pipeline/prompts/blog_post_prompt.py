"""Blog Post Prompt — Doc 7 Generation.

Temperature: 0.4 (creative writing, fact-grounded)

This prompt takes Doc 2 (Semantic Brief) claims data and Doc 0 (Source Ledger)
source metadata as input and outputs a BlogPostDocument.

Required components (per architecture Rule 7):
1. Source Identity Lock
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction
5. Output Schema
"""

BLOG_POST_ROLE = """You are an expert blog writer who transforms research into compelling,
SEO-optimized long-form articles.

Your job is to:
- Write a structured, engaging blog post grounded in the research data
- Every factual claim must reference a specific claim_id from Doc 2
- Every claim_id reference must also reference a specific source_id from Doc 0
- Optimize for SEO with a meta description (max 160 chars) and keywords
- Write in clear, accessible prose — not academic, not clickbait

CRITICAL GROUNDING RULES:
1. Every factual statement MUST reference a specific claim_id from Doc 2
2. Every claim_id MUST also reference a specific source_id from Doc 0
3. You MUST NOT introduce facts, statistics, or claims not present in the data
4. If the data is thin, write a shorter post — do not pad with generic filler
5. Disputed/speculative claims must be clearly qualified in prose

ANTI-GENERIC RULES:
1. BANNED PHRASES — never use: "in today's world", "it's important to note",
   "delve into", "rich tapestry", "paradigm shift", "raises important questions",
   "at the end of the day", "needless to say", "in conclusion"
2. Write in active voice. Avoid passive constructions.
3. Use specific examples from the data, not vague generalizations.
4. Each section heading should be descriptive and keyword-rich.

EMPTY OUTPUT PERMISSION:
- Return null for subtitle if the title is self-sufficient
- Return null for call_to_action if no natural CTA emerges
- Use 3 sections if the data only supports 3 strong sections
- Sparse, accurate output > dense, hallucinated output
"""

SOURCE_IDENTITY_LOCK = """
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  job_id: {job_id}                                        ║
║  topic: {topic}                                          ║
║  source_count: {source_count}                            ║
║  stage: blog_post_generation                             ║
╚══════════════════════════════════════════════════════════╝

IDENTITY RULES:
- These fields are LOCKED. Copy them exactly into your output.
- Do NOT infer, modify, or generate new values for these fields.
"""

CONFIDENCE_CEILING = """
CONFIDENCE CEILING: MEDIUM
This is a synthesis-stage document. Maximum confidence is MEDIUM.
Do not present any claim with higher certainty than the source data supports.
"""


def build_blog_post_prompt(
    job_id: str,
    topic: str,
    source_count: int,
    doc0_sources: str,
    doc2_claims: str,
    doc2_themes: str,
    doc2_tensions: str,
    doc3_hooks: str = "",
    doc3_setup: str = "",
) -> str:
    """Build the blog post generation prompt.

    Args:
        job_id: Job identifier.
        topic: Research topic.
        source_count: Number of sources.
        doc0_sources: Formatted source ledger.
        doc2_claims: Claims with enrichments.
        doc2_themes: Themes.
        doc2_tensions: Tensions.
        doc3_hooks: Optional hook text from Creator Brief.
        doc3_setup: Optional setup text from Creator Brief.

    Returns:
        Complete prompt string.
    """
    identity = SOURCE_IDENTITY_LOCK.format(
        job_id=job_id,
        topic=topic,
        source_count=source_count,
    )

    doc3_context = ""
    if doc3_hooks or doc3_setup:
        doc3_context = f"""
## CREATOR BRIEF CONTEXT (Doc 3 — use for framing guidance)

### Hooks
{doc3_hooks or "(No hooks available)"}

### Setup / Framing
{doc3_setup or "(No setup available)"}
"""

    return f"""{identity}

{CONFIDENCE_CEILING}

## YOUR TASK

Write a long-form, SEO-optimized blog post about "{topic}" using ONLY the data below.
The post should have 3-12 sections (typically 5-8), each with a descriptive heading.
Use fewer sections if the data is thin; use more if the data is rich.

## SOURCE DATA

### Doc 0 — Source Ledger ({source_count} sources)
{doc0_sources}

### Doc 2 — Claims (with enrichments)
{doc2_claims}

### Doc 2 — Themes
{doc2_themes}

### Doc 2 — Tensions
{doc2_tensions}

{doc3_context}

## EXTRACTION LAYERS

LAYER 1: Use the highest-significance claims as the backbone of the article.
LAYER 2: Use themes to organize sections and create narrative flow.
LAYER 3: Use tensions to add nuance and counterpoints.

## OUTPUT SCHEMA

Return a JSON object matching this schema exactly:
{{
  "document_type": "blog_post",
  "job_id": "{job_id}",
  "generated_at": "<ISO datetime>",
  "topic": "{topic}",
  "source_count": {source_count},
  "title": "<compelling, keyword-rich title>",
  "subtitle": "<optional subtitle or null>",
  "meta_description": "<max 160 chars, SEO-optimized>",
  "estimated_reading_time": "<e.g. '5 min read'>",
  "sections": [
    {{
      "section_id": "SECT_1",
      "heading": "<section heading>",
      "body": "<markdown body with factual claims grounded in data>",
      "claim_ids": ["CLM_1", "CLM_3"],
      "source_ids": ["SRC_1", "SRC_2"]
    }}
  ],
  "conclusion": "<concluding paragraph>",
  "call_to_action": "<optional CTA or null>",
  "seo_keywords": ["keyword1", "keyword2"],
  "description_sources": [
    {{"source_id": "SRC_1", "title": "...", "url": "...", "creator": "..."}}
  ],
  "guardrails": {{
    "no_new_facts_ack": true,
    "all_facts_reference_doc2": true,
    "all_facts_reference_doc0": true
  }}
}}
"""
