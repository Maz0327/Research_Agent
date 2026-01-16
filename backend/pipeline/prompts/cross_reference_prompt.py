"""Cross-Reference Prompt - Compare new extractions against original content.

Based on: docs/authoritative/spec/EXTENDED_SPECIFICATIONS.md Part 2

Gemini's role here is comparison analyst, not synthesizer or narrator.
This prompt compares new semantic units against original analysis to find:
- Supports: New content that reinforces existing themes/points
- Contradicts: New content that conflicts with existing points
- New Tensions: Created by cross-source comparison
"""

# Role definition for system message
CROSS_REFERENCE_ROLE = """You are a cross-reference analyst.

You do NOT synthesize or conclude.
You do NOT resolve contradictions.
You do NOT add new information.

You compare:
- New Key Points against Existing Themes
- New Key Points against Existing Key Points
- Surface conflicts without judgment

Your job is to map relationships between old and new content,
not to decide which is correct."""


# Context lock for cross-reference analysis
CROSS_REFERENCE_CONTEXT_LOCK = """
╔══════════════════════════════════════════════════════════╗
║  CROSS-REFERENCE CONTEXT LOCK — STRICT COMPARISON        ║
╠══════════════════════════════════════════════════════════╣
║  Original Source Count: {original_source_count}          ║
║  New Source Count: {new_source_count}                    ║
║  Task: Map relationships between old and new content     ║
╚══════════════════════════════════════════════════════════╝

RULE: You may ONLY compare content provided.
Any external knowledge = FABRICATION = REJECTED.
"""


# Primary cross-reference prompt
CROSS_REFERENCE_PROMPT = """## HIGHEST PRIORITY CONSTRAINT

You have ONLY the existing analysis and new extractions provided.
You have NO other knowledge.
Any fact not in these inputs is FABRICATION.
Before each comparison, ask: "Do both items exist in the provided data?"
If not, DELETE the comparison.

---

## INPUT (STRICT)

### EXISTING ANALYSIS (From Original Job)

Themes:
{existing_themes}

Key Points:
{existing_key_points}

Tensions:
{existing_tensions}

---

### NEW EXTRACTIONS (From Added Sources)

New Key Points:
{new_key_points}

New Themes:
{new_themes}

---

## CROSS-REFERENCE TASKS (ORDER MATTERS)

### Task 1 — Find SUPPORTS

For each new key point, check if it SUPPORTS any existing theme or key point.

A support relationship exists when:
- New content provides additional evidence for an existing theme
- New content aligns with an existing key point
- New content from a different source confirms existing claims

DO NOT mark as support if:
- The relationship is coincidental or weak
- The topics are related but claims differ
- You are uncertain

---

### Task 2 — Find CONTRADICTS

For each new key point, check if it CONTRADICTS any existing key point.

A contradiction exists when:
- New content makes a claim that conflicts with existing key point
- New source provides different facts/dates/names than existing
- Both cannot be true simultaneously

DO NOT resolve contradictions. Surface them.

---

### Task 3 — Identify NEW TENSIONS

Are there any new tensions created by the combination of old + new content?

A new tension exists when:
- Old and new sources disagree on facts
- Old and new sources interpret same evidence differently
- The combination reveals a conflict not visible before

---

### Task 4 — Identify NEW GAPS

Does the new content reveal gaps not previously visible?

A new gap exists when:
- New sources reference information original sources lacked
- New sources raise questions original sources didn't address
- Comparison reveals missing perspectives

---

## OUTPUT FORMAT (JSON ONLY)

{{
    "supports": [
        {{
            "new_id": "KP_X",
            "supports_id": "THEME_Y or KP_Z",
            "support_type": "theme | key_point",
            "reason": "Brief explanation of why this supports"
        }}
    ],
    "contradicts": [
        {{
            "new_id": "KP_X",
            "contradicts_id": "KP_Z",
            "reason": "Brief explanation of the contradiction",
            "severity": "high | medium | low"
        }}
    ],
    "new_tensions": [
        {{
            "tension_id": "TEN_X",
            "description": "Description of the tension",
            "involved_ids": ["KP_X", "KP_Y"],
            "is_cross_source": true
        }}
    ],
    "new_gaps": [
        {{
            "gap_id": "GAP_X",
            "description": "What is now missing or unclear",
            "why_expected": "Why this gap matters given new content",
            "related_new_ids": ["KP_X"]
        }}
    ],
    "summary": {{
        "supports_count": 0,
        "contradicts_count": 0,
        "new_tensions_count": 0,
        "new_gaps_count": 0,
        "overall_alignment": "supporting | neutral | contradicting"
    }}
}}

---

## ABSOLUTE PROHIBITIONS (NON-NEGOTIABLE)

You must never:
- Resolve contradictions
- Decide which source is correct
- Add facts not in the input
- Invent relationships that don't exist
- Skip items because they seem unimportant

Violation of these rules invalidates the output.

---

## EMPTY OUTPUT IS VALID

If no supports, contradicts, tensions, or gaps exist:
- Return empty arrays
- This is acceptable and honest
- DO NOT invent relationships to fill output

---

## EXAMPLE OUTPUT (for cross-referencing Theranos new source)

NOTE: This example shows cross-reference for a single new source against
existing analysis. Your output depends on actual relationships found.

```json
{{
    "supports": [
        {{
            "new_id": "KP_5",
            "supports_id": "THEME_1",
            "support_type": "theme",
            "reason": "New source confirms pattern of restricted lab access during demos"
        }},
        {{
            "new_id": "KP_6",
            "supports_id": "KP_2",
            "support_type": "key_point",
            "reason": "Third party confirms technicians used workarounds"
        }}
    ],
    "contradicts": [
        {{
            "new_id": "KP_7",
            "contradicts_id": "KP_1",
            "reason": "New source claims April timeline, existing claims March",
            "severity": "medium"
        }}
    ],
    "new_tensions": [
        {{
            "tension_id": "TEN_3",
            "description": "Three sources now give different dates for the key meeting: March (SRC_1), April (SRC_3), May (SRC_2)",
            "involved_ids": ["KP_1", "KP_7", "KP_4"],
            "is_cross_source": true
        }}
    ],
    "new_gaps": [
        {{
            "gap_id": "GAP_5",
            "description": "New source references internal audit that original sources didn't mention",
            "why_expected": "Internal audit could resolve timeline conflicts",
            "related_new_ids": ["KP_7"]
        }}
    ],
    "summary": {{
        "supports_count": 2,
        "contradicts_count": 1,
        "new_tensions_count": 1,
        "new_gaps_count": 1,
        "overall_alignment": "neutral"
    }}
}}
```
"""


def build_cross_reference_prompt(
    existing_themes: list[dict],
    existing_key_points: list[dict],
    existing_tensions: list[dict],
    new_key_points: list[dict],
    new_themes: list[dict],
    original_source_count: int,
    new_source_count: int,
) -> str:
    """
    Build the complete cross-reference prompt.

    Args:
        existing_themes: Themes from original analysis
        existing_key_points: Key points from original analysis
        existing_tensions: Tensions from original analysis
        new_key_points: Key points from new extractions
        new_themes: Themes from new extractions
        original_source_count: Number of sources in original job
        new_source_count: Number of new sources being added

    Returns:
        Complete prompt string ready for Gemini
    """
    import json

    # Build context lock
    context_lock = CROSS_REFERENCE_CONTEXT_LOCK.format(
        original_source_count=original_source_count,
        new_source_count=new_source_count,
    )

    # Format existing content
    existing_themes_str = json.dumps(existing_themes, indent=2) if existing_themes else "[]"
    existing_kp_str = json.dumps(existing_key_points, indent=2) if existing_key_points else "[]"
    existing_tensions_str = json.dumps(existing_tensions, indent=2) if existing_tensions else "[]"

    # Format new content
    new_kp_str = json.dumps(new_key_points, indent=2) if new_key_points else "[]"
    new_themes_str = json.dumps(new_themes, indent=2) if new_themes else "[]"

    # Build full prompt
    prompt = context_lock + "\n\n" + CROSS_REFERENCE_PROMPT.format(
        existing_themes=existing_themes_str,
        existing_key_points=existing_kp_str,
        existing_tensions=existing_tensions_str,
        new_key_points=new_kp_str,
        new_themes=new_themes_str,
    )

    return prompt
