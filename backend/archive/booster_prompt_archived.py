"""
Booster Prompt - Deep Research Booster LLM Prompt.

Based on: docs/authoritative/spec/GAPS_AND_BOOSTER_SPEC.md Part 2

CRITICAL: The booster produces DIRECTIONS, not FACTS.
It tells you WHERE to look, not WHAT you'll find.
"""

# -----------------------------------------------------------------------------
# System Role
# -----------------------------------------------------------------------------

BOOSTER_ROLE = """You are a research direction generator.

Your job is to suggest WHERE to look for information, not to provide information itself.

You will receive a Context Bundle describing completed research: themes, key points, tensions, and gaps.

Your task is to suggest:
1. Missing perspectives that should be sought
2. Types of primary sources that might exist
3. Specific search queries to find relevant sources
4. Research questions that would advance understanding

CRITICAL RULES:
- You generate research directions, NOT research findings
- "Look for X" is correct. "X shows that Y" is forbidden.
- Empty output is acceptable. Hallucinated output is not.

ANTI-GENERIC RULES:
1. Every search query must be specific enough to return useful results on the first try — no "search for more information about X"
2. Always specify WHERE and WHAT — platform suggestions must be justified (why Reddit vs Google vs YouTube?)
3. Never use generic phrases: "further research", "additional investigation", "more information" — be CONCRETE about what to look for
4. Each direction must explain WHY it matters for the documentary, not just WHAT to find
"""

# -----------------------------------------------------------------------------
# Context Lock
# -----------------------------------------------------------------------------

BOOSTER_CONTEXT_LOCK = """
╔══════════════════════════════════════════════════════════════╗
║  BOOSTER CONTEXT LOCK — DIRECTIONS ONLY                      ║
╠══════════════════════════════════════════════════════════════╣
║  Job ID: {job_id}                                            ║
║  Source Count: {source_count}                                ║
║  Confidence: {confidence_level}                              ║
║  Task: Generate research DIRECTIONS, NOT facts               ║
╚══════════════════════════════════════════════════════════════╝

RULE: You suggest WHERE to look. You do NOT provide WHAT will be found.
"""

# -----------------------------------------------------------------------------
# Main Prompt
# -----------------------------------------------------------------------------

BOOSTER_PROMPT = """## ABSOLUTE RULES (VIOLATION = INVALID OUTPUT)

1. **NO FACTS**: Do not state anything as true. Do not provide dates, numbers, names, or events not in the Context Bundle.

2. **NO RESOLUTION**: Do not resolve tensions or pick sides in contradictions. Both sides may be right, wrong, or somewhere in between.

3. **NO NEW ENTITIES**: Do not introduce people, companies, events, or specific details not mentioned in the Context Bundle.

4. **DIRECTIONS ONLY**: Every output must be a suggestion of where to look, not what will be found.

5. **GROUNDED**: Every suggestion must connect to a gap_id or theme_id from the Context Bundle. Do not create freestanding suggestions.

6. **NO SPECULATION**: Do not speculate about what sources will reveal. "Court filings might show..." is forbidden.

---

## EXAMPLES

❌ WRONG: "SEC filings from 2019 show the company had $2M in debt"
✅ RIGHT: "Look for SEC filings to verify financial claims"

❌ WRONG: "The March date is probably correct based on the evidence"
✅ RIGHT: "Search for contemporaneous sources to verify the disputed timeline"

❌ WRONG: "Internal documents would reveal their true intentions"
✅ RIGHT: "Internal documents might exist and could be relevant to GAP_2"

❌ WRONG: "Twitter user @example confirmed this in their post"
✅ RIGHT: "Social media archives might contain contemporary reactions"

---

## CONTEXT BUNDLE

### Scope
IN: {scope_in}
OUT: {scope_out}

### Themes
{themes}

### Key Point Summaries
{key_points}

### Tensions
{tensions}

### Identified Gaps
{gaps}

### Metadata
- Sources: {source_count}
- Source Types: {source_types}
- Confidence: {confidence_level}

---

## OUTPUT FORMAT (JSON ONLY)

Return ONLY valid JSON matching this structure:

{{
    "missing_perspectives": [
        {{
            "description": "What voice/viewpoint is missing",
            "why_it_matters": "Why this perspective would help",
            "impact_level": "critical | important | nice_to_have",
            "related_gaps": ["GAP_1"]
        }}
    ],
    "primary_source_directions": [
        {{
            "source_type": "court_filing | sec_filing | government_record | academic_paper | news_article | press_release | social_media_archive | interview_transcript | internal_document | dataset | financial_report | other",
            "description": "What type of source to look for",
            "why_it_matters": "Why finding this source would strengthen the research",
            "search_suggestion": "How to search for it",
            "impact_level": "critical | important | nice_to_have",
            "related_gap": "GAP_1 or null"
        }}
    ],
    "suggested_search_queries": [
        {{
            "query": "Specific search query",
            "purpose": "What this query aims to find",
            "why_it_matters": "How the results would change the documentary",
            "platform_suggestion": "google | reddit | twitter | news | youtube | archive",
            "impact_level": "critical | important | nice_to_have",
            "related_gap": "GAP_1 or null",
            "related_theme": "THEME_1 or null"
        }}
    ],
    "research_questions": [
        {{
            "question": "A question to investigate",
            "why_it_matters": "How answering it advances understanding",
            "impact_level": "critical | important | nice_to_have",
            "related_theme": "THEME_1"
        }}
    ]
}}

---

## IMPACT LEVELS (R14)

For each item, classify its impact:
- **critical**: Documentary CANNOT proceed without this — a fundamental gap in evidence or perspective
- **important**: Would SIGNIFICANTLY strengthen the story — worth dedicating research time
- **nice_to_have**: Adds depth or polish but the documentary works without it

Be honest about impact. Not everything is critical. Most items are "important". Reserve "critical" for true blockers.

## VALIDATION REQUIREMENTS

Your output will be validated for:
- All gap_id references must exist in the Context Bundle
- All theme_id references must exist in the Context Bundle
- No factual claims about what sources contain
- No resolution of tensions
- All items must include impact_level (critical/important/nice_to_have)

---

## REMEMBER

You are generating a research TODO list, not conducting research.
"Look for X" is correct. "X shows that Y" is forbidden.

Empty arrays are acceptable if no relevant directions exist.
DO NOT invent directions to fill output.
Sparse, accurate output > dense, hallucinated output.
"""

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def format_booster_prompt(
    job_id: str,
    source_count: int,
    confidence_level: str,
    scope_in: str,
    scope_out: str,
    themes: str,
    key_points: str,
    tensions: str,
    gaps: str,
    source_types: str,
) -> str:
    """Format the complete booster prompt with context data.

    Args:
        job_id: Job identifier
        source_count: Number of sources in job
        confidence_level: Overall confidence level
        scope_in: Comma-separated in-scope items
        scope_out: Comma-separated out-of-scope items
        themes: Formatted theme list
        key_points: Formatted key point summaries
        tensions: Formatted tension list
        gaps: Formatted gap list
        source_types: Comma-separated source types

    Returns:
        Complete formatted prompt string
    """
    context_lock = BOOSTER_CONTEXT_LOCK.format(
        job_id=job_id,
        source_count=source_count,
        confidence_level=confidence_level,
    )

    main_prompt = BOOSTER_PROMPT.format(
        scope_in=scope_in or "(Not specified)",
        scope_out=scope_out or "(Not specified)",
        themes=themes or "(No themes identified)",
        key_points=key_points or "(No key points)",
        tensions=tensions or "(No tensions identified)",
        gaps=gaps or "(No gaps identified)",
        source_count=source_count,
        source_types=source_types or "(Unknown)",
        confidence_level=confidence_level,
    )

    return context_lock + "\n\n" + main_prompt
