"""LLM output validation and repair utility.

Validates LLM-generated JSON against Pydantic schemas and requests
repairs when validation fails. Implements a retry loop with fallback
to degraded defaults.
"""
import json
from typing import Any, Optional, Type, TypeVar

from loguru import logger
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ValidationResult:
    """Result of LLM output validation."""

    def __init__(
        self,
        success: bool,
        data: Optional[BaseModel] = None,
        used_fallback: bool = False,
        repair_attempts: int = 0,
        errors: Optional[list] = None,
    ):
        self.success = success
        self.data = data
        self.used_fallback = used_fallback
        self.repair_attempts = repair_attempts
        self.errors = errors or []


def validate_and_repair(
    llm_output: dict | str,
    schema: Type[T],
    repair_fn: Optional[Any] = None,
    repair_prompt: Optional[str] = None,
    max_retries: int = 2,
    fallback_factory: Optional[Any] = None,
) -> ValidationResult:
    """
    Validate LLM output against a Pydantic schema, repair if invalid.

    The repair loop:
    1. Try to validate the output
    2. If validation fails, send errors back to LLM for repair
    3. Retry up to max_retries times
    4. If still invalid, return fallback/degraded object

    Args:
        llm_output: Dict or JSON string from LLM
        schema: Pydantic model class to validate against
        repair_fn: Optional function(output, errors, prompt) -> repaired_output
        repair_prompt: Context for repair (passed to repair_fn)
        max_retries: Maximum repair attempts (default: 2)
        fallback_factory: Factory function() -> default object if all fails

    Returns:
        ValidationResult with validated data or fallback

    Example:
        result = validate_and_repair(
            llm_output={"mode": "invalid_mode"},
            schema=JobConfig,
            repair_fn=request_llm_repair,
            repair_prompt="Fix the JobConfig to have valid mode",
            fallback_factory=lambda: JobConfig(topic="fallback")
        )
    """
    # Parse JSON string if needed
    if isinstance(llm_output, str):
        try:
            llm_output = json.loads(llm_output)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM output as JSON: {e}")
            if fallback_factory:
                return ValidationResult(
                    success=False,
                    data=fallback_factory(),
                    used_fallback=True,
                    errors=[f"JSON parse error: {str(e)}"],
                )
            return ValidationResult(
                success=False,
                errors=[f"JSON parse error: {str(e)}"],
            )

    current_output = llm_output
    all_errors = []

    for attempt in range(max_retries + 1):
        try:
            validated = schema.model_validate(current_output)
            return ValidationResult(
                success=True,
                data=validated,
                repair_attempts=attempt,
            )
        except ValidationError as e:
            errors = e.errors()
            all_errors.extend(errors)

            if attempt == max_retries:
                logger.warning(
                    f"Validation failed after {max_retries} retries, "
                    f"errors: {_format_errors(errors)}"
                )
                break

            # Attempt repair if repair function is available
            if repair_fn and repair_prompt:
                logger.info(f"Validation attempt {attempt + 1} failed, requesting repair")
                try:
                    current_output = repair_fn(
                        current_output,
                        errors,
                        repair_prompt,
                    )
                except Exception as repair_error:
                    logger.warning(f"Repair request failed: {repair_error}")
                    break
            else:
                # No repair function, break early
                break

    # All retries exhausted, use fallback
    if fallback_factory:
        try:
            fallback = fallback_factory()
            return ValidationResult(
                success=False,
                data=fallback,
                used_fallback=True,
                repair_attempts=max_retries + 1,
                errors=all_errors,
            )
        except Exception as fallback_error:
            logger.error(f"Fallback factory failed: {fallback_error}")

    return ValidationResult(
        success=False,
        repair_attempts=max_retries + 1,
        errors=all_errors,
    )


def _format_errors(errors: list) -> str:
    """Format Pydantic validation errors for logging/LLM."""
    formatted = []
    for error in errors:
        loc = ".".join(str(l) for l in error.get("loc", []))
        msg = error.get("msg", "unknown error")
        formatted.append(f"{loc}: {msg}")
    return "; ".join(formatted)


def format_errors_for_llm(errors: list) -> str:
    """
    Format validation errors as a prompt for LLM repair.

    Returns a human-readable description of what needs to be fixed.
    """
    lines = ["The following validation errors need to be fixed:"]
    for error in errors:
        loc = ".".join(str(l) for l in error.get("loc", []))
        msg = error.get("msg", "unknown error")
        input_val = error.get("input")
        lines.append(f"- Field '{loc}': {msg}")
        if input_val is not None:
            lines.append(f"  Current value: {input_val}")
    lines.append("\nPlease return the corrected JSON.")
    return "\n".join(lines)


def request_openai_repair(
    output: dict,
    errors: list,
    context_prompt: str,
) -> dict:
    """
    Request OpenAI to repair invalid JSON output.

    Args:
        output: The invalid output dict
        errors: List of Pydantic validation errors
        context_prompt: Original context for the repair

    Returns:
        Repaired output dict
    """
    from backend.config import require_openai, MissingRequiredSettingError

    try:
        settings = require_openai()
    except MissingRequiredSettingError:
        logger.warning("OpenAI not available for repair")
        return output

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)

    error_desc = format_errors_for_llm(errors)

    repair_prompt = f"""You previously generated this JSON output:

```json
{json.dumps(output, indent=2)}
```

{error_desc}

Context: {context_prompt}

Return ONLY the corrected JSON object, no explanation."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a JSON repair assistant. Fix validation errors and return valid JSON.",
                },
                {"role": "user", "content": repair_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        return output
    except Exception as e:
        logger.warning(f"OpenAI repair request failed: {e}")
        return output


def create_partial_object(
    schema: Type[T],
    partial_data: dict,
    required_defaults: Optional[dict] = None,
) -> Optional[T]:
    """
    Create a partial object from incomplete data by filling required fields.

    Useful as a fallback when validation fails but some data is salvageable.

    Args:
        schema: Pydantic model class
        partial_data: Incomplete data dict
        required_defaults: Dict of field_name -> default_value for required fields

    Returns:
        Validated object or None if creation fails
    """
    required_defaults = required_defaults or {}

    # Merge partial data with defaults
    merged = {**required_defaults, **partial_data}

    try:
        return schema.model_validate(merged)
    except ValidationError as e:
        logger.warning(f"Failed to create partial object: {_format_errors(e.errors())}")
        return None
