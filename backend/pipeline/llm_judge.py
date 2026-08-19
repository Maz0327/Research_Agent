"""
LLM Judge - Cross-Model Validation using GPT-4o.

Purpose: Validate Gemini extractions using GPT-4o for independent verification.
Cross-model validation eliminates self-bias where the same model validates its own output.

Key Benefits:
- Different training data catches different errors
- True independence in validation
- Higher confidence in results

Cost: ~$0.003-0.005 per extraction (GPT-4o input/output tokens)
"""

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Module-level circuit breaker for quota-exhausted providers
# Prevents wasting ~4-6s per source on 3 retries that will never succeed.
# Resets on worker restart.
# ---------------------------------------------------------------------------
_PROVIDER_DISABLED: dict[str, str] = {}  # provider_name -> reason


class JudgeVerdict(str, Enum):
    """Verdict for an individual item."""
    VALID = "valid"
    QUESTIONABLE = "questionable"
    INVALID = "invalid"


class OverallQuality(str, Enum):
    """Overall extraction quality assessment."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ItemReview:
    """Review result for a single extracted item."""
    item_id: str
    item_type: str  # key_point, claim, quote
    verdict: JudgeVerdict
    grounding: str  # grounded, partially_grounded, ungrounded
    issues: list[str] = field(default_factory=list)
    evidence_found: Optional[str] = None
    suggested_confidence: Optional[str] = None
    explanation: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "verdict": self.verdict.value,
            "grounding": self.grounding,
            "issues": self.issues,
            "evidence_found": self.evidence_found,
            "suggested_confidence": self.suggested_confidence,
            "explanation": self.explanation,
        }


@dataclass
class QuoteReview:
    """Review result for a quote."""
    quote_id: str
    verdict: JudgeVerdict
    accuracy: str  # verbatim, paraphrased, fabricated
    matched_text: Optional[str] = None
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "quote_id": self.quote_id,
            "verdict": self.verdict.value,
            "accuracy": self.accuracy,
            "matched_text": self.matched_text,
            "issues": self.issues,
        }


@dataclass
class ConfidenceOverride:
    """Suggested confidence override."""
    item_id: str
    original: str
    suggested: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "original": self.original,
            "suggested": self.suggested,
            "reason": self.reason,
        }


@dataclass
class JudgeResult:
    """Complete result from LLM judge validation."""
    items_reviewed: list[ItemReview] = field(default_factory=list)
    quotes_reviewed: list[QuoteReview] = field(default_factory=list)
    overall_quality: OverallQuality = OverallQuality.MEDIUM
    hallucination_flags: list[str] = field(default_factory=list)
    confidence_overrides: list[ConfidenceOverride] = field(default_factory=list)
    summary: str = ""
    cost: float = 0.0
    error: Optional[str] = None
    provider: str = "unknown"

    @property
    def valid_count(self) -> int:
        return sum(1 for item in self.items_reviewed if item.verdict == JudgeVerdict.VALID)

    @property
    def questionable_count(self) -> int:
        return sum(1 for item in self.items_reviewed if item.verdict == JudgeVerdict.QUESTIONABLE)

    @property
    def invalid_count(self) -> int:
        return sum(1 for item in self.items_reviewed if item.verdict == JudgeVerdict.INVALID)

    @property
    def verdict_by_item(self) -> dict:
        """Map item ID to the verdict the judge gave it."""
        return {item.item_id: item.verdict for item in self.items_reviewed}

    @property
    def confirmed_hallucination_flags(self) -> list[str]:
        """Flags the judge's own verdicts support.

        Judges have returned every reviewed item in `hallucination_flags` while
        marking all of them VALID, which then downgraded a whole clean
        extraction to LOW confidence. A per-item verdict is the more explicit
        statement, so a flag that contradicts a VALID verdict is not acted on.
        Flags for items the judge did not review are kept: there is no verdict
        to contradict them.
        """
        verdicts = self.verdict_by_item
        return [
            flag_id
            for flag_id in self.hallucination_flags
            if verdicts.get(flag_id) is not JudgeVerdict.VALID
        ]

    @property
    def contradictory_hallucination_flags(self) -> list[str]:
        """Flags the judge marked VALID in the same response.

        Reported rather than acted on, so the contradiction stays visible.
        """
        verdicts = self.verdict_by_item
        return [
            flag_id
            for flag_id in self.hallucination_flags
            if verdicts.get(flag_id) is JudgeVerdict.VALID
        ]

    @property
    def validation_rate(self) -> float:
        total = len(self.items_reviewed)
        if total == 0:
            return 1.0
        return self.valid_count / total

    def to_dict(self) -> dict:
        return {
            "items_reviewed": [item.to_dict() for item in self.items_reviewed],
            "quotes_reviewed": [quote.to_dict() for quote in self.quotes_reviewed],
            "overall_quality": self.overall_quality.value,
            "hallucination_flags": self.hallucination_flags,
            "confidence_overrides": [co.to_dict() for co in self.confidence_overrides],
            "summary": self.summary,
            "stats": {
                "items_reviewed": len(self.items_reviewed),
                "valid": self.valid_count,
                "questionable": self.questionable_count,
                "invalid": self.invalid_count,
                "validation_rate": round(self.validation_rate, 3),
                "hallucination_flags": len(self.confirmed_hallucination_flags),
                "contradictory_flags": len(self.contradictory_hallucination_flags),
            },
            "cost": round(self.cost, 5),
            "error": self.error,
        }


def parse_judge_response(response_data: dict) -> JudgeResult:
    """Parse GPT-4o judge response into JudgeResult.

    Args:
        response_data: Parsed JSON from GPT-4o

    Returns:
        JudgeResult object
    """
    result = JudgeResult()

    # Parse items_reviewed
    for item_data in response_data.get("items_reviewed", []):
        try:
            verdict_str = item_data.get("verdict", "questionable").lower()
            verdict = JudgeVerdict(verdict_str) if verdict_str in ["valid", "questionable", "invalid"] else JudgeVerdict.QUESTIONABLE

            item = ItemReview(
                item_id=item_data.get("item_id", "UNKNOWN"),
                item_type=item_data.get("item_type", "unknown"),
                verdict=verdict,
                grounding=item_data.get("grounding", "ungrounded"),
                issues=item_data.get("issues", []),
                evidence_found=item_data.get("evidence_found"),
                suggested_confidence=item_data.get("suggested_confidence"),
                explanation=item_data.get("explanation"),
            )
            result.items_reviewed.append(item)
        except Exception as e:
            logger.warning(f"Failed to parse item review: {e}")

    # Parse quotes_reviewed
    for quote_data in response_data.get("quotes_reviewed", []):
        try:
            verdict_str = quote_data.get("verdict", "questionable").lower()
            verdict = JudgeVerdict(verdict_str) if verdict_str in ["valid", "questionable", "invalid"] else JudgeVerdict.QUESTIONABLE

            quote = QuoteReview(
                quote_id=quote_data.get("quote_id", "UNKNOWN"),
                verdict=verdict,
                accuracy=quote_data.get("accuracy", "paraphrased"),
                matched_text=quote_data.get("matched_text"),
                issues=quote_data.get("issues", []),
            )
            result.quotes_reviewed.append(quote)
        except Exception as e:
            logger.warning(f"Failed to parse quote review: {e}")

    # Parse overall quality
    quality_str = response_data.get("overall_quality", "medium").lower()
    if quality_str in ["high", "medium", "low"]:
        result.overall_quality = OverallQuality(quality_str)

    # Parse hallucination flags
    result.hallucination_flags = response_data.get("hallucination_flags", [])

    # Parse confidence overrides
    for override_data in response_data.get("confidence_overrides", []):
        try:
            override = ConfidenceOverride(
                item_id=override_data.get("item_id", ""),
                original=override_data.get("original", ""),
                suggested=override_data.get("suggested", ""),
                reason=override_data.get("reason", ""),
            )
            result.confidence_overrides.append(override)
        except Exception as e:
            logger.warning(f"Failed to parse confidence override: {e}")

    # Parse summary
    result.summary = response_data.get("summary", "")

    return result


def _try_openai_judge(
    prompt: str,
    system_prompt: str,
    source_id: str,
    model: str = "gpt-4o",
) -> Optional[JudgeResult]:
    """Try GPT-4o as cross-model judge. Returns None on failure.

    Uses a module-level circuit breaker to skip immediately when
    quota is exhausted, avoiding 3× retry waste (~4-6s per source).
    """
    # Circuit breaker: skip if provider was disabled this worker session
    if "GPT-4o" in _PROVIDER_DISABLED:
        logger.debug(
            f"[{source_id}] GPT-4o skipped (circuit breaker: "
            f"{_PROVIDER_DISABLED['GPT-4o']})"
        )
        return None

    from backend.config import require_openai, MissingRequiredSettingError

    try:
        settings = require_openai()
    except MissingRequiredSettingError:
        logger.debug(f"[{source_id}] OpenAI not configured, skipping")
        return None

    logger.info(f"[{source_id}] Running GPT-4o cross-model validation")
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4000,
        )

        resp_content = response.choices[0].message.content
        if not resp_content:
            raise ValueError("Empty response from GPT-4o")

        response_data = json.loads(resp_content)
        result = parse_judge_response(response_data)
        result.provider = "GPT-4o"

        # GPT-4o: ~$2.50/1M input, ~$10/1M output
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        result.cost = (input_tokens * 2.5 / 1_000_000) + (output_tokens * 10 / 1_000_000)

        logger.info(
            f"[{source_id}] Judge result (GPT-4o): quality={result.overall_quality.value}, "
            f"valid={result.valid_count}, questionable={result.questionable_count}, "
            f"invalid={result.invalid_count}, "
            f"hallucination_flags={len(result.confirmed_hallucination_flags)}, "
            f"cost=${result.cost:.4f}"
        )
        return result

    except Exception as e:
        error_str = str(e)
        # Detect quota exhaustion and trip circuit breaker
        if "insufficient_quota" in error_str or "exceeded your current quota" in error_str:
            _PROVIDER_DISABLED["GPT-4o"] = "insufficient_quota"
            logger.warning(
                f"[{source_id}] GPT-4o quota exhausted — circuit breaker tripped, "
                f"skipping for remaining sources this worker session"
            )
        else:
            logger.warning(f"[{source_id}] GPT-4o judge failed: {e}")
        return None


def _repair_truncated_json(text: str) -> Optional[str]:
    """Attempt to repair truncated JSON from LLM responses.

    Kimi K2.5 sometimes hits max_tokens mid-string, producing valid JSON
    except for an unterminated string at the end. This function closes
    open strings, arrays, and objects to salvage partial results.

    Args:
        text: Potentially truncated JSON string

    Returns:
        Repaired JSON string, or None if repair is not possible.
    """
    if not text or not text.strip():
        return None

    text = text.rstrip()

    # Track nesting to know what closers we need
    closers_needed: list[str] = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            closers_needed.append("}")
        elif ch == "[":
            closers_needed.append("]")
        elif ch in ("}", "]"):
            if closers_needed and closers_needed[-1] == ch:
                closers_needed.pop()

    # If we're inside a string, close it
    if in_string:
        text += '"'

    # Close any open arrays/objects
    while closers_needed:
        text += closers_needed.pop()

    return text


def _try_kimi_judge(
    prompt: str,
    system_prompt: str,
    source_id: str,
) -> Optional[JudgeResult]:
    """Try Kimi K2.5 as cross-model judge. Returns None on failure.

    Includes JSON repair for truncated responses (unterminated strings)
    which are common when Kimi hits max_tokens.
    """
    kimi_api_key = os.getenv("KIMI_API_KEY")
    if not kimi_api_key:
        logger.debug(f"[{source_id}] Kimi K2.5 not configured (KIMI_API_KEY missing)")
        return None

    logger.info(f"[{source_id}] Running Kimi K2.5 cross-model validation")
    try:
        import httpx

        with httpx.Client(timeout=120) as http_client:
            response = http_client.post(
                "https://api.moonshot.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {kimi_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 1,  # Kimi K2.5 only allows temperature=1
                    "max_tokens": 8000,  # Increased from 4000 to avoid truncation
                },
            )

        if response.status_code != 200:
            raise ValueError(
                f"Kimi API error {response.status_code}: {response.text[:500]}"
            )

        resp_json = response.json()
        resp_content = resp_json["choices"][0]["message"]["content"]

        # Check for empty or whitespace-only response
        if not resp_content or not resp_content.strip():
            # Check if finish_reason indicates truncation
            finish_reason = resp_json["choices"][0].get("finish_reason", "")
            raise ValueError(
                f"Empty response from Kimi K2.5 (finish_reason={finish_reason})"
            )

        # Strip markdown code fences if present
        resp_content = resp_content.strip()
        if resp_content.startswith("```"):
            first_newline = resp_content.find("\n")
            if first_newline != -1:
                resp_content = resp_content[first_newline + 1:]
            if resp_content.endswith("```"):
                resp_content = resp_content[:-3]
        resp_content = resp_content.strip()

        # Try parsing JSON, with repair fallback for truncated responses
        try:
            response_data = json.loads(resp_content)
        except json.JSONDecodeError as json_err:
            # Attempt JSON repair for truncated responses
            logger.info(
                f"[{source_id}] Kimi JSON parse failed, attempting repair: "
                f"{str(json_err)[:80]}"
            )
            repaired = _repair_truncated_json(resp_content)
            if repaired:
                try:
                    response_data = json.loads(repaired)
                    logger.info(
                        f"[{source_id}] Kimi JSON repair successful "
                        f"({len(resp_content)} → {len(repaired)} chars)"
                    )
                except json.JSONDecodeError:
                    raise json_err  # Re-raise original error
            else:
                raise

        result = parse_judge_response(response_data)
        result.provider = "Kimi K2.5"

        # Kimi K2.5 cost estimate: ~$0.002/1K input, $0.006/1K output tokens
        usage = resp_json.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        result.cost = (input_tokens * 0.002 + output_tokens * 0.006) / 1000

        logger.info(
            f"[{source_id}] Judge result (Kimi K2.5): quality={result.overall_quality.value}, "
            f"valid={result.valid_count}, questionable={result.questionable_count}, "
            f"invalid={result.invalid_count}, "
            f"hallucination_flags={len(result.confirmed_hallucination_flags)}, "
            f"cost=${result.cost:.4f}"
        )
        return result

    except Exception as e:
        logger.warning(f"[{source_id}] Kimi K2.5 judge failed: {e}")
        return None


def validate_extraction_with_judge(
    source_text: str,
    extraction_result: dict,
    source_id: str = "UNKNOWN",
    model: str = "gpt-4o",
) -> JudgeResult:
    """Validate extraction using cross-model judge.

    Provider order is controlled by LLM_JUDGE_PRIMARY env var (default: kimi).
    Falls back to the other provider if the primary fails.

    Args:
        source_text: Original source content
        extraction_result: Extraction result dict to validate
        source_id: Source identifier for logging
        model: OpenAI model to use when GPT-4o is selected

    Returns:
        JudgeResult with validation assessment
    """
    from backend.config import get_settings
    from backend.pipeline.prompts.llm_judge_prompt import (
        build_judge_prompt,
        LLM_JUDGE_SYSTEM_PROMPT,
    )

    # Build prompt (shared by both providers)
    extraction_json = json.dumps(extraction_result, indent=2)
    prompt = build_judge_prompt(source_text, extraction_json)

    # Determine provider order from config
    settings = get_settings()
    primary = getattr(settings, "llm_judge_primary", "kimi").lower()

    if primary == "kimi":
        providers = [
            ("Kimi K2.5", lambda: _try_kimi_judge(prompt, LLM_JUDGE_SYSTEM_PROMPT, source_id)),
            ("GPT-4o", lambda: _try_openai_judge(prompt, LLM_JUDGE_SYSTEM_PROMPT, source_id, model)),
        ]
    else:
        providers = [
            ("GPT-4o", lambda: _try_openai_judge(prompt, LLM_JUDGE_SYSTEM_PROMPT, source_id, model)),
            ("Kimi K2.5", lambda: _try_kimi_judge(prompt, LLM_JUDGE_SYSTEM_PROMPT, source_id)),
        ]

    errors = []
    for name, try_fn in providers:
        result = try_fn()
        if result is not None:
            return result
        errors.append(name)

    # Both failed
    logger.error(f"[{source_id}] All judge providers failed: {errors}")
    return JudgeResult(
        error=f"All judge providers failed: {', '.join(errors)}",
        summary="Cross-model validation failed (all providers unavailable)",
        provider="none",
    )


def apply_judge_verdicts(
    extraction_result: Any,
    judge_result: JudgeResult,
) -> tuple[Any, list[str]]:
    """Apply judge verdicts to extraction result.

    Applies:
    - Confidence overrides
    - Hallucination flags (as warnings)
    - Quote accuracy adjustments

    Works with both SemanticExtractionResult objects and dicts.

    Args:
        extraction_result: Original extraction (SemanticExtractionResult or dict)
        judge_result: Validation result from judge

    Returns:
        Tuple of (updated_extraction, warnings)
    """
    from backend.models.semantic_units import ConfidenceLevel

    warnings = []

    # Check if we have a SemanticExtractionResult object or dict
    is_object = hasattr(extraction_result, "key_points") and not isinstance(extraction_result, dict)

    # Build override lookup
    override_lookup = {co.item_id: co for co in judge_result.confidence_overrides}

    if is_object:
        # Handle SemanticExtractionResult object
        for kp in extraction_result.key_points:
            kp_id = kp.key_point_id
            if kp_id in override_lookup:
                override = override_lookup[kp_id]
                old_conf = kp.confidence.value if hasattr(kp.confidence, "value") else str(kp.confidence)
                try:
                    kp.confidence = ConfidenceLevel(override.suggested.lower())
                except ValueError:
                    kp.confidence = ConfidenceLevel.LOW
                warnings.append(
                    f"Key point {kp_id}: confidence {old_conf} -> {override.suggested} "
                    f"({override.reason})"
                )

        for claim in extraction_result.claims:
            claim_id = claim.claim_id
            if claim_id in override_lookup:
                override = override_lookup[claim_id]
                old_conf = claim.confidence.value if hasattr(claim.confidence, "value") else str(claim.confidence)
                try:
                    claim.confidence = ConfidenceLevel(override.suggested.lower())
                except ValueError:
                    claim.confidence = ConfidenceLevel.LOW
                warnings.append(
                    f"Claim {claim_id}: confidence {old_conf} -> {override.suggested} "
                    f"({override.reason})"
                )

        # Mark hallucination flags the judge's own verdicts support
        for flag_id in judge_result.contradictory_hallucination_flags:
            warnings.append(
                f"Judge flagged {flag_id} as fabricated but also marked it VALID; "
                f"the verdict wins and the flag is not applied"
            )
        for flag_id in judge_result.confirmed_hallucination_flags:
            warnings.append(f"HALLUCINATION FLAG: {flag_id} - likely fabricated content")
            for kp in extraction_result.key_points:
                if kp.key_point_id == flag_id:
                    kp.confidence = ConfidenceLevel.LOW
            for claim in extraction_result.claims:
                if claim.claim_id == flag_id:
                    claim.confidence = ConfidenceLevel.LOW

        # Mark quotes by accuracy
        quote_accuracy = {q.quote_id: q.accuracy for q in judge_result.quotes_reviewed}
        for quote in extraction_result.quotes:
            if quote.quote_id in quote_accuracy:
                accuracy = quote_accuracy[quote.quote_id]
                if accuracy == "fabricated":
                    warnings.append(f"Quote {quote.quote_id}: FABRICATED - not found in source")
                    # Remove fabricated quotes
                    extraction_result.quotes = [q for q in extraction_result.quotes if q.quote_id != quote.quote_id]
                elif accuracy == "paraphrased":
                    quote.approximate = True
                    warnings.append(f"Quote {quote.quote_id}: paraphrased (not verbatim)")

    else:
        # Handle dict (original implementation)
        for kp in extraction_result.get("key_points", []):
            kp_id = kp.get("key_point_id", "")
            if kp_id in override_lookup:
                override = override_lookup[kp_id]
                kp["confidence"] = override.suggested
                kp["_judge_override"] = True
                kp["_judge_reason"] = override.reason
                warnings.append(
                    f"Key point {kp_id}: confidence {override.original} -> {override.suggested} "
                    f"({override.reason})"
                )

        for claim in extraction_result.get("claims", []):
            claim_id = claim.get("claim_id", "")
            if claim_id in override_lookup:
                override = override_lookup[claim_id]
                claim["confidence"] = override.suggested
                claim["_judge_override"] = True
                claim["_judge_reason"] = override.reason
                warnings.append(
                    f"Claim {claim_id}: confidence {override.original} -> {override.suggested} "
                    f"({override.reason})"
                )

        # Mark hallucination flags the judge's own verdicts support
        for flag_id in judge_result.contradictory_hallucination_flags:
            warnings.append(
                f"Judge flagged {flag_id} as fabricated but also marked it VALID; "
                f"the verdict wins and the flag is not applied"
            )
        for flag_id in judge_result.confirmed_hallucination_flags:
            warnings.append(f"HALLUCINATION FLAG: {flag_id} - likely fabricated content")
            for kp in extraction_result.get("key_points", []):
                if kp.get("key_point_id") == flag_id:
                    kp["_hallucination_flag"] = True
                    kp["confidence"] = "low"
            for claim in extraction_result.get("claims", []):
                if claim.get("claim_id") == flag_id:
                    claim["_hallucination_flag"] = True
                    claim["confidence"] = "low"

        # Mark quotes by accuracy
        quote_accuracy = {q.quote_id: q.accuracy for q in judge_result.quotes_reviewed}
        for quote in extraction_result.get("quotes", []):
            quote_id = quote.get("quote_id", "")
            if quote_id in quote_accuracy:
                accuracy = quote_accuracy[quote_id]
                quote["_judge_accuracy"] = accuracy
                if accuracy == "fabricated":
                    quote["_hallucination_flag"] = True
                    warnings.append(f"Quote {quote_id}: FABRICATED - not found in source")
                elif accuracy == "paraphrased":
                    quote["approximate"] = True
                    warnings.append(f"Quote {quote_id}: paraphrased (not verbatim)")

        # Add judge summary to dict
        extraction_result["_judge_validation"] = {
            "overall_quality": judge_result.overall_quality.value,
            "validation_rate": judge_result.validation_rate,
            "hallucination_flags": judge_result.hallucination_flags,
            "summary": judge_result.summary,
            "cost": judge_result.cost,
        }

    return extraction_result, warnings
