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
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from loguru import logger


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
                "valid": self.valid_count,
                "questionable": self.questionable_count,
                "invalid": self.invalid_count,
                "validation_rate": round(self.validation_rate, 3),
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


def validate_extraction_with_judge(
    source_text: str,
    extraction_result: dict,
    source_id: str = "UNKNOWN",
    model: str = "gpt-4o",
) -> JudgeResult:
    """Validate extraction using cross-model judge (GPT-4o with Kimi K2.5 fallback).

    Attempts GPT-4o first; falls back to Kimi K2.5 (Moonshot) if OpenAI is
    unavailable or fails (e.g. quota exhausted, insufficient_quota error).

    Args:
        source_text: Original source content
        extraction_result: Extraction result dict to validate
        source_id: Source identifier for logging
        model: OpenAI model to use (default gpt-4o)

    Returns:
        JudgeResult with validation assessment
    """
    from backend.config import require_openai, MissingRequiredSettingError
    from backend.pipeline.prompts.llm_judge_prompt import (
        build_judge_prompt,
        LLM_JUDGE_SYSTEM_PROMPT,
    )

    # Build prompt (shared by both providers)
    extraction_json = json.dumps(extraction_result, indent=2)
    prompt = build_judge_prompt(source_text, extraction_json)

    # --- Attempt 1: OpenAI GPT-4o ---
    openai_error: Optional[str] = None
    try:
        settings = require_openai()
    except MissingRequiredSettingError:
        openai_error = "OpenAI not configured"
        logger.warning(f"[{source_id}] OpenAI not configured, trying Kimi K2.5 fallback")

    if openai_error is None:
        logger.info(f"[{source_id}] Running GPT-4o cross-model validation")
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": LLM_JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4000,
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from GPT-4o")

            response_data = json.loads(content)
            result = parse_judge_response(response_data)

            # GPT-4o: ~$2.50/1M input, ~$10/1M output
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            result.cost = (input_tokens * 2.5 / 1_000_000) + (output_tokens * 10 / 1_000_000)

            logger.info(
                f"[{source_id}] Judge result (GPT-4o): quality={result.overall_quality.value}, "
                f"valid={result.valid_count}, questionable={result.questionable_count}, "
                f"invalid={result.invalid_count}, hallucination_flags={len(result.hallucination_flags)}, "
                f"cost=${result.cost:.4f}"
            )
            return result

        except Exception as e:
            openai_error = str(e)
            logger.warning(
                f"[{source_id}] GPT-4o judge failed ({e}) — trying Kimi K2.5 fallback"
            )

    # --- Attempt 2: Kimi K2.5 (Moonshot) fallback ---
    kimi_api_key = os.getenv("KIMI_API_KEY")
    if not kimi_api_key:
        logger.error(f"[{source_id}] Kimi K2.5 not configured (KIMI_API_KEY missing)")
        return JudgeResult(
            error=f"OpenAI failed ({openai_error}); Kimi K2.5 not configured",
            summary="Cross-model validation skipped (both providers unavailable)",
        )

    logger.info(f"[{source_id}] Running Kimi K2.5 cross-model validation (fallback)")
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
                        {"role": "system", "content": LLM_JUDGE_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 1,  # Kimi K2.5 only allows temperature=1
                    "max_tokens": 4000,
                },
            )

        if response.status_code != 200:
            raise ValueError(
                f"Kimi API error {response.status_code}: {response.text[:500]}"
            )

        resp_json = response.json()
        content = resp_json["choices"][0]["message"]["content"]
        if not content:
            raise ValueError("Empty response from Kimi K2.5")

        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1:]
            if content.endswith("```"):
                content = content[:-3]
        content = content.strip()

        response_data = json.loads(content)
        result = parse_judge_response(response_data)

        # Kimi K2.5 cost estimate: ~$0.002/1K input, $0.006/1K output tokens
        usage = resp_json.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        result.cost = (input_tokens * 0.002 + output_tokens * 0.006) / 1000

        logger.info(
            f"[{source_id}] Judge result (Kimi K2.5 fallback): quality={result.overall_quality.value}, "
            f"valid={result.valid_count}, questionable={result.questionable_count}, "
            f"invalid={result.invalid_count}, hallucination_flags={len(result.hallucination_flags)}, "
            f"cost=${result.cost:.4f}"
        )
        return result

    except Exception as e:
        logger.error(f"[{source_id}] Kimi K2.5 judge fallback also failed: {e}")
        return JudgeResult(
            error=f"Both providers failed. OpenAI: {openai_error}; Kimi: {str(e)}",
            summary="Cross-model validation failed (all providers unavailable)",
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

        # Mark hallucination flags
        for flag_id in judge_result.hallucination_flags:
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

        # Mark hallucination flags
        for flag_id in judge_result.hallucination_flags:
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
