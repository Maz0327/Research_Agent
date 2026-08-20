"""
LLM Judge Prompt - Cross-Model Validation for Hallucination Detection.

Purpose: A DIFFERENT AI model (GPT-4o) validates extractions made by Gemini.
Cross-model validation eliminates self-bias and catches errors that the
extracting model might miss.

Key Principle: GPT-4o has different training data and tendencies than Gemini,
providing true independence in validation.
"""

LLM_JUDGE_SYSTEM_PROMPT = """You are a strict validation judge for AI-extracted content.

Your role is to verify that another AI's extraction is accurate and grounded in source text.
You are NOT the AI that did the extraction - you are an independent validator.

Your job:
1. Check that every extracted item actually exists in the source
2. Verify quotes are verbatim (not paraphrased or invented)
3. Assess if confidence levels match evidence strength
4. Flag any likely hallucinations

Be STRICT. It is better to flag a valid item as questionable than to miss a hallucination.
The goal is to catch errors, not to be lenient."""


LLM_JUDGE_PROMPT = """You are validating an extraction made by a DIFFERENT AI model.

## SOURCE TEXT (Ground Truth)
This is what the AI was given to extract from:

{source_text}

---

## EXTRACTION OUTPUT (To Validate)
This is what the AI extracted:

{extraction_json}

---

## YOUR TASK

For EACH extracted item (key_points, claims, quotes), evaluate:

### 1. GROUNDING
Is this claim/statement actually present in the source text?
- "grounded": Text clearly supports this
- "partially_grounded": Text somewhat supports but with interpretation
- "ungrounded": Cannot find supporting text

### 2. ACCURACY (for quotes)
Does the extracted quote appear VERBATIM in the source?
- "verbatim": Exact match found
- "paraphrased": Similar but not exact
- "fabricated": Quote not found in source

### 3. CONFIDENCE APPROPRIATENESS
Is the assigned confidence level appropriate for the evidence?
- "appropriate": Confidence matches evidence strength
- "overconfident": Claims high confidence without strong evidence
- "underconfident": Claims low confidence despite strong evidence

---

## OUTPUT FORMAT

Return JSON:
```json
{{
  "items_reviewed": [
    {{
      "item_id": "KP_1",
      "item_type": "key_point",
      "verdict": "valid | questionable | invalid",
      "grounding": "grounded | partially_grounded | ungrounded",
      "issues": ["list of specific issues found"],
      "evidence_found": "text from source that supports/refutes this",
      "suggested_confidence": "high | medium | low | null",
      "explanation": "brief explanation of verdict"
    }}
  ],
  "quotes_reviewed": [
    {{
      "quote_id": "QT_1",
      "verdict": "valid | questionable | invalid",
      "accuracy": "verbatim | paraphrased | fabricated",
      "matched_text": "actual text found in source (if any)",
      "issues": []
    }}
  ],
  "overall_quality": "high | medium | low",
  "hallucination_flags": ["list of item IDs likely hallucinated"],
  "confidence_overrides": [
    {{
      "item_id": "KP_1",
      "original": "high",
      "suggested": "medium",
      "reason": "Evidence is circumstantial"
    }}
  ],
  "summary": "Brief overall assessment"
}}
```

---

## VALIDATION RULES

1. **Quote Verification**
   - Search for EXACT text matches
   - A few changed words = paraphrased (not verbatim)
   - Invented quotes are CRITICAL errors

2. **Claim Verification**
   - Claims must have textual support in source
   - Inferences must be reasonable from explicit content
   - External knowledge injection = hallucination

3. **Confidence Check**
   - HIGH: Requires verbatim quotes or explicit statements
   - MEDIUM: Requires paraphrased content or strong inference
   - LOW: Acceptable for weak inference from context

4. **Hallucination Detection**
   - Specific numbers/dates not in source = likely hallucinated
   - Named entities not mentioned = likely hallucinated
   - Detailed quotes without source match = likely hallucinated

BE THOROUGH. Check every item. Do not skip any."""


def relevant_source(source_text: str, extraction_json: str, budget: int) -> str:
    """Select the parts of a source the extraction is actually about.

    Taking the FIRST `budget` characters is the wrong cut for this job. The
    judge's verdict is "is this claim supported by the source", so a claim
    whose evidence sits at character 30,000 of a 40,000-character transcript
    was being marked unsupported on the strength of text the judge never saw —
    a false negative manufactured by the prompt builder, in the one component
    whose whole purpose is checking the others.

    Instead the source is cut into windows and the windows that share content
    words with the extraction are kept, best first, until the budget is spent.

    Args:
        source_text: The original source content.
        extraction_json: The extraction being judged.
        budget: Characters of source the prompt may carry.

    Returns:
        The selected source text, in document order, with elisions marked.
    """
    if len(source_text) <= budget:
        return source_text

    from backend.pipeline.text_similarity import content_tokens

    wanted = content_tokens(extraction_json)
    words = source_text.split()
    # ~500-word windows: big enough to hold a claim and its context.
    windows = [" ".join(words[i : i + 500]) for i in range(0, len(words), 500)]

    scored = sorted(
        (
            (len(wanted & content_tokens(window)) / (len(content_tokens(window)) or 1), i)
            for i, window in enumerate(windows)
        ),
        reverse=True,
    )

    kept: set[int] = set()
    spent = 0
    for _score, index in scored:
        size = len(windows[index])
        if spent + size > budget:
            continue
        kept.add(index)
        spent += size

    if not kept:
        return source_text[:budget] + "\n\n[SOURCE TRUNCATED FOR LENGTH]"

    out, gap = [], False
    for index, window in enumerate(windows):
        if index in kept:
            if gap:
                out.append("[... unrelated passage omitted ...]")
            out.append(window)
            gap = False
        else:
            gap = True
    return "\n\n".join(out)


def build_judge_prompt(
    source_text: str,
    extraction_json: str,
    max_source_chars: int = 15000,
) -> str:
    """Build the complete judge prompt with source and extraction.

    Args:
        source_text: The original source content
        extraction_json: JSON string of the extraction result
        max_source_chars: Maximum characters to include from source (cost control)

    Returns:
        Formatted prompt for the judge
    """
    return LLM_JUDGE_PROMPT.format(
        source_text=relevant_source(source_text, extraction_json, max_source_chars),
        extraction_json=extraction_json,
    )
