"""Social Media Kit Prompt — Doc 6 Generation.

Multi-call approach: one LLM call per platform group.
Temperature varies by platform (0.3 for professional, 0.5 for casual).
"""

SOCIAL_KIT_ROLE = """You are a social media strategist who transforms research into
platform-optimized posts.

CRITICAL RULES:
1. Every factual claim MUST reference a claim_id from Doc 2
2. Every claim_id MUST reference a source_id from Doc 0
3. Twitter tweets MUST be under 280 characters each
4. LinkedIn posts should be 1300 chars or less
5. Instagram captions should be under 2200 chars
6. TikTok captions should be under 150 chars
7. Do NOT introduce facts not in the data
"""


def build_social_kit_prompt(
    job_id: str,
    topic: str,
    source_count: int,
    platforms: list[str],
    tone: str,
    doc0_sources: str,
    doc2_claims: str,
    doc2_themes: str,
) -> str:
    """Build social kit generation prompt for specified platforms.

    Args:
        job_id: Job identifier.
        topic: Research topic.
        source_count: Number of sources.
        platforms: List of platform names to generate for.
        tone: Tone (professional, casual, energetic).
        doc0_sources: Formatted source ledger.
        doc2_claims: Claims text.
        doc2_themes: Themes text.

    Returns:
        Complete prompt string.
    """
    platform_list = ", ".join(platforms)

    platform_schemas = []
    for p in platforms:
        if p == "twitter_thread":
            platform_schemas.append("""
    {
      "platform": "twitter_thread",
      "tweets": [{"tweet_number": 1, "text": "<max 280 chars>", "claim_ids": ["CLM_X"]}],
      "body": null,
      "hashtags": ["#tag1"],
      "char_count": <total chars across tweets>,
      "claim_ids": ["CLM_X"],
      "source_ids": ["SRC_X"]
    }""")
        elif p == "youtube_description":
            platform_schemas.append("""
    {
      "platform": "youtube_description",
      "description_body": "<full YouTube description>",
      "timestamps": [{"timestamp": "0:00", "label": "Intro"}],
      "hashtags": ["#tag1"],
      "char_count": <int>,
      "claim_ids": ["CLM_X"],
      "source_ids": ["SRC_X"]
    }""")
        else:
            platform_schemas.append(f"""
    {{
      "platform": "{p}",
      "body": "<post content>",
      "hashtags": ["#tag1"],
      "char_count": <int>,
      "claim_ids": ["CLM_X"],
      "source_ids": ["SRC_X"]
    }}""")

    schemas_str = ",".join(platform_schemas)

    return f"""
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK                                    ║
║  job_id: {job_id}                                        ║
║  topic: {topic}                                          ║
║  source_count: {source_count}                            ║
╚══════════════════════════════════════════════════════════╝

TONE: {tone.upper()}

Generate social media posts for: {platform_list}

## SOURCE DATA

### Doc 0 Sources
{doc0_sources}

### Doc 2 Claims
{doc2_claims}

### Doc 2 Themes
{doc2_themes}

## OUTPUT SCHEMA

Return a JSON object:
{{
  "document_type": "social_kit",
  "job_id": "{job_id}",
  "generated_at": "<ISO datetime>",
  "topic": "{topic}",
  "source_count": {source_count},
  "platforms": [{schemas_str}
  ],
  "guardrails": {{
    "no_new_facts_ack": true,
    "all_facts_reference_doc2": true,
    "all_facts_reference_doc0": true
  }}
}}
"""
