"""Creator Brief Prompt — Doc 3 Assembly.

Based on: docs/authoritative/spec/RASS.md Stage F
Temperature: 0.3 (creative but grounded)

This prompt takes Doc 2 (Semantic Brief) claims data and Doc 0 (Source Ledger)
source metadata as input and outputs a CreatorBriefDocument.

The Creator Brief is the hero document. It is GROUNDED in extracted data —
every fact, hook, and core point must reference a real claim_id from Doc 2
and a real source_id from Doc 0. This is NOT creative fiction.

Required components (per architecture Rule 7):
1. Source Identity Lock
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction
5. Output Schema
"""

CREATOR_BRIEF_ROLE = """You are a content strategist helping video creators translate research into
compelling content briefs.

Your job is to:
- Identify the most compelling claims from the research
- Suggest narrative hooks that are grounded in the actual evidence
- Flag contradictions and speculative content explicitly
- Help the creator understand what they can say confidently vs. tentatively

CRITICAL GROUNDING RULES:
1. Every hook, fact, and narrative element MUST reference a specific claim_id from Doc 2
2. Every claim_id reference MUST also reference a specific source_id from Doc 0
3. You MUST NOT introduce facts, names, events, or statistics not present in the provided data
4. If the data is thin, produce a thin brief — do not pad with generic content
5. Disputed and speculative claims MUST be flagged in disputed_claims — never treated as established

ANTI-GENERIC RULES (violations will be detected):
1. BANNED PHRASES — never use: "it's important to note", "it's worth noting", "interestingly",
   "notably", "at the end of the day", "in today's world", "delve into", "rich tapestry",
   "multifaceted", "navigate the complexities", "needless to say", "paradigm shift",
   "raises important questions", "shed light on", "holistic approach"
2. Every "say_it_like" phrasing MUST be plain spoken English — write how a person talks, not how a paper reads
3. Hooks must be specific — reference a real number, name, event, or contradiction from the data

EMPTY OUTPUT PERMISSION:
- Return null for twist if no contradicting/disputed claims exist in the data
- Return null for cliffhanger if no speculative claims exist
- Return null for analogy if the data doesn't naturally lend itself to one
- Return 3 core_facts if the data only supports 3 strong claims
- Sparse, accurate output > dense, hallucinated output
"""


# ---------------------------------------------------------------------------
# Source Identity Lock (adapted for multi-source synthesis — uses job identity)
# ---------------------------------------------------------------------------

SOURCE_IDENTITY_LOCK_BLOCK = """
╔══════════════════════════════════════════════════════════╗
║  SOURCE IDENTITY LOCK — DO NOT MODIFY OR INFER          ║
╠══════════════════════════════════════════════════════════╣
║  job_id: {job_id}                                        ║
║  topic: {topic}                                          ║
║  source_count: {source_count}                            ║
║  stage: creator_brief_assembly                           ║
╚══════════════════════════════════════════════════════════╝

IDENTITY RULES:
- Use only the claim_ids and source_ids provided below
- Do NOT reference any external sources or knowledge
- Do NOT invent claim_ids or source_ids
- If a claim_id is referenced, it MUST appear in the DOC 2 DATA section below
"""

# ---------------------------------------------------------------------------
# Confidence Ceiling Declaration (synthesis/assembly stage uses MEDIUM ceiling)
# ---------------------------------------------------------------------------

CONFIDENCE_CEILING_DECLARATION = """
## CONFIDENCE CEILING: MEDIUM

This is a synthesis stage — you are interpreting extracted claims, not quoting verbatim.
Your maximum confidence for any assertion is: MEDIUM

All high-significance claims should be drawn from HIGH-confidence claims in the input data.
Do NOT treat low-confidence claims as established facts.
"""

# ---------------------------------------------------------------------------
# Main assembly prompt
# ---------------------------------------------------------------------------

CREATOR_BRIEF_PROMPT = """{source_identity_lock_block}

{confidence_ceiling_declaration}

---

## YOUR TASK

Assemble a Creator Brief (Doc 3) from the research data below.

The Creator Brief helps a video creator know:
- What hook to open with (2 options: HOOK_A and HOOK_B)
- How to set up the topic for viewers
- What the key twist or contradiction is (if any)
- Which 3–5 facts to feature (with plain-English phrasing)
- An analogy to explain the concept (if the data supports one)
- Why viewers should care personally
- How to end with an open question or cliffhanger (if speculative claims exist)
- Which sources to list in the description box
- Which claims are disputed or speculative (must be flagged)

LAYERED APPROACH:
LAYER 1: Identify the highest-significance claims in the data (framing: supports or establishes)
LAYER 2: Find the key tension or contradiction (framing: contradicts or disputed)
LAYER 3: Find open/speculative elements (framing: speculative or hedged)
Then: Assemble the brief from these layers

---

## DOC 0 DATA — SOURCE LEDGER

{doc0_sources}

---

## DOC 2 DATA — CLAIMS AND ENRICHMENTS

{doc2_claims}

---

## DOC 2 DATA — THEMES

{doc2_themes}

---

## DOC 2 DATA — TENSIONS

{doc2_tensions}

---

## ASSEMBLY RULES

### hook_options (REQUIRED — exactly 2)
- Generate HOOK_A and HOOK_B
- Each hook must be derived from a specific claim (claim_id required)
- Hooks should be the most compelling, specific, surprising things in the data
- Say it how a creator would say it in the first 5 seconds of a video
- Include why_it_works: the psychological/strategic reason this hook works
- Different hooks should take different angles (e.g. one curiosity gap, one stat-first)

### setup (REQUIRED)
- 2–4 sentences framing the topic for a general audience
- Ground in the core theme(s) — reference supporting_claim_ids
- Do NOT repeat the hook — this is context, not the open

### twist (OPTIONAL — only if contradicting/disputed claim exists)
- Must reference a claim with framing="contradicts" or framing="disputed"
- The twist is the moment when the obvious answer turns out to be wrong
- If no such claim exists in the data, return null

### core_facts (REQUIRED — 3 to 5)
- Select the 3–5 highest-significance claims
- Each fact needs: statement (as extracted), say_it_like (plain English), claim_id, source_id
- say_it_like should sound like something a creator would actually say on camera
- Prefer high-significance claims; include medium-significance only if needed to reach 3
- fact_id must be sequential: FACT_1, FACT_2, FACT_3, ...

### analogy (OPTIONAL)
- A comparison that makes the core concept click for a general audience
- Only include if the data naturally suggests an analogy
- If forced, omit it (return null)

### personal_stakes (OPTIONAL)
- Why should the average viewer care about this topic?
- Ground in real claims from the data — don't invent stakes

### cliffhanger (OPTIONAL — only if speculative/open claim exists)
- An open question or speculative element to end the video with
- Must reference a claim with framing="speculative" or framing="hedged"
- If no such claim exists, return null

### description_sources (REQUIRED if sources have URLs)
- List all sources used in the brief with title, url, creator
- These go in the video description box

### disputed_claims (REQUIRED — list all flagged claims)
- ANY claim with framing="disputed", "speculative", "contradicts", or "hedged" MUST appear here
- Include the statement, framing, speaker (if known), and source_id
- Empty list is acceptable if no disputed/speculative claims exist

### guardrails (REQUIRED — all must be true)
- no_new_facts_ack: true (you have not introduced any facts beyond the provided data)
- all_facts_reference_doc2: true (every claim_id references a real claim from the DOC 2 DATA)
- all_facts_reference_doc0: true (every source_id references a real source from the DOC 0 DATA)

---

## OUTPUT SCHEMA

Return a single JSON object matching this exact schema:

{{
  "document_type": "creator_brief",
  "document_version": "1.0",
  "job_id": "{job_id}",
  "topic": "{topic}",
  "source_count": {source_count},
  "hook_options": [
    {{
      "hook_id": "HOOK_A",
      "text": "...",
      "why_it_works": "...",
      "claim_id": "CLM_N",
      "source_id": "SRC_N"
    }},
    {{
      "hook_id": "HOOK_B",
      "text": "...",
      "why_it_works": "...",
      "claim_id": "CLM_N",
      "source_id": "SRC_N"
    }}
  ],
  "setup": {{
    "text": "...",
    "supporting_claim_ids": ["CLM_N", ...],
    "supporting_source_ids": ["SRC_N", ...]
  }},
  "twist": {{
    "text": "...",
    "claim_id": "CLM_N",
    "source_id": "SRC_N",
    "framing": "contradicts"
  }},
  "core_facts": [
    {{
      "fact_id": "FACT_1",
      "statement": "...",
      "say_it_like": "...",
      "significance": "high",
      "claim_id": "CLM_N",
      "source_id": "SRC_N",
      "speaker": null
    }}
  ],
  "analogy": {{
    "text": "...",
    "supporting_claim_ids": ["CLM_N", ...]
  }},
  "personal_stakes": {{
    "text": "...",
    "supporting_claim_ids": ["CLM_N", ...]
  }},
  "cliffhanger": {{
    "text": "...",
    "claim_id": "CLM_N",
    "framing": "speculative"
  }},
  "description_sources": [
    {{
      "source_id": "SRC_N",
      "title": "...",
      "url": "...",
      "creator": "..."
    }}
  ],
  "disputed_claims": [
    {{
      "claim_id": "CLM_N",
      "statement": "...",
      "framing": "disputed",
      "speaker": null,
      "source_id": "SRC_N"
    }}
  ],
  "guardrails": {{
    "no_new_facts_ack": true,
    "all_facts_reference_doc2": true,
    "all_facts_reference_doc0": true
  }}
}}

REMINDER: twist, analogy, personal_stakes, and cliffhanger may be null if not supported by data.
REMINDER: hook_options must contain exactly HOOK_A and HOOK_B.
REMINDER: core_facts must have 3–5 entries with sequential fact_ids (FACT_1, FACT_2, ...).
REMINDER: All claim_ids must appear in the DOC 2 DATA section above.
REMINDER: All source_ids must appear in the DOC 0 DATA section above.
"""


def build_creator_brief_prompt(
    job_id: str,
    topic: str,
    source_count: int,
    doc0_sources: str,
    doc2_claims: str,
    doc2_themes: str,
    doc2_tensions: str,
) -> str:
    """Build the Creator Brief assembly prompt.

    Args:
        job_id: The job identifier.
        topic: The research topic.
        source_count: Number of sources in the job.
        doc0_sources: Formatted Doc 0 source data (JSON string or structured text).
        doc2_claims: Formatted Doc 2 claims with enrichments (JSON string or structured text).
        doc2_themes: Formatted Doc 2 themes (JSON string or structured text).
        doc2_tensions: Formatted Doc 2 tensions (JSON string or structured text).

    Returns:
        The complete prompt string ready to send to the LLM.
    """
    lock_block = SOURCE_IDENTITY_LOCK_BLOCK.format(
        job_id=job_id,
        topic=topic,
        source_count=source_count,
    )

    return CREATOR_BRIEF_PROMPT.format(
        source_identity_lock_block=lock_block,
        confidence_ceiling_declaration=CONFIDENCE_CEILING_DECLARATION,
        job_id=job_id,
        topic=topic,
        source_count=source_count,
        doc0_sources=doc0_sources,
        doc2_claims=doc2_claims,
        doc2_themes=doc2_themes,
        doc2_tensions=doc2_tensions,
    )
