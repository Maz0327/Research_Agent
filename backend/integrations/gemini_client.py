"""Google Gemini API client for planning and vision tasks.

Research-validated stack (Dec 2025):
- Gemini 2.5 Flash: $0.30/$2.50 per M tokens - used for planning, query gen
- Gemini 2.5 Pro: $1.25/$10 per M tokens - used for vision/PDF, validation, synthesis
"""
import base64
from pathlib import Path
from typing import Optional, Any

from loguru import logger

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Install with: pip install google-generativeai")


class GeminiClient:
    """Client for Google Gemini 2.5 Flash/Pro.

    Used for:
    - Planning with thinking mode (Flash)
    - Query generation (Flash)
    - Vision/PDF analysis (Pro)
    - Validation and synthesis (Pro)
    """

    # Cost per 1M tokens (Dec 2025 verified pricing)
    COSTS = {
        "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
        "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    }

    def __init__(self):
        """Initialize Gemini client."""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai library not installed")

        from backend.config import get_settings
        settings = get_settings()

        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")

        genai.configure(api_key=settings.google_api_key)
        self._api_key = settings.google_api_key

    def generate(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash",
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate text with Gemini.

        Args:
            prompt: The prompt to send
            model: Model to use (gemini-2.5-flash or gemini-2.5-pro)
            system_instruction: Optional system instruction
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Dict with text response and cost estimate
        """
        try:
            logger.info(f"Gemini {model}: {prompt[:50]}...")

            # Configure model
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            model_instance = genai.GenerativeModel(
                model,
                system_instruction=system_instruction,
                generation_config=generation_config,
            )

            response = model_instance.generate_content(prompt)
            text = response.text

            # Estimate cost (rough approximation)
            input_tokens = len(prompt.split()) * 1.3  # ~1.3 tokens per word
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(f"Gemini response: {len(text)} chars, ~${cost:.4f}")

            return {
                "text": text,
                "model": model,
                "cost": cost,
            }

        except Exception as e:
            logger.error(f"Gemini generate failed: {e}")
            raise

    def generate_with_thinking(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash",
        thinking_budget: int = 1024,
        system_instruction: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate with thinking mode for complex reasoning.

        Args:
            prompt: The prompt to send
            model: Model to use
            thinking_budget: Token budget for thinking (default 1024)
            system_instruction: Optional system instruction

        Returns:
            Dict with text response, thinking content, and cost estimate
        """
        try:
            logger.info(f"Gemini {model} thinking: {prompt[:50]}...")

            model_instance = genai.GenerativeModel(
                model,
                system_instruction=system_instruction,
            )

            # Configure thinking mode
            generation_config = {
                "thinking_config": {"thinking_budget": thinking_budget}
            }

            response = model_instance.generate_content(
                prompt,
                generation_config=generation_config,
            )

            text = response.text

            # Extract thinking content if available
            thinking = None
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'thinking_content'):
                    thinking = candidate.thinking_content

            # Estimate cost (thinking uses more tokens)
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(text.split()) * 1.3 + thinking_budget
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(f"Gemini thinking response: {len(text)} chars, ~${cost:.4f}")

            return {
                "text": text,
                "thinking": thinking,
                "model": model,
                "cost": cost,
            }

        except Exception as e:
            logger.error(f"Gemini thinking failed: {e}")
            raise

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str = "gemini-2.5-pro",
    ) -> dict[str, Any]:
        """Analyze an image with Gemini Pro vision.

        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            model: Model to use (default: gemini-2.5-pro for best vision)

        Returns:
            Dict with analysis text and cost estimate
        """
        try:
            logger.info(f"Gemini vision: {prompt[:50]}...")

            # Read and encode image
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            with open(image_path, "rb") as f:
                image_data = f.read()

            # Determine MIME type
            suffix = image_path.suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_types.get(suffix, "image/jpeg")

            # Create image part
            image_part = {
                "mime_type": mime_type,
                "data": base64.b64encode(image_data).decode("utf-8"),
            }

            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content([prompt, image_part])
            text = response.text

            # Estimate cost (images count as ~258 tokens)
            input_tokens = len(prompt.split()) * 1.3 + 258
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(f"Gemini vision response: {len(text)} chars, ~${cost:.4f}")

            return {
                "text": text,
                "model": model,
                "cost": cost,
            }

        except Exception as e:
            logger.error(f"Gemini vision failed: {e}")
            raise

    def analyze_pdf(
        self,
        pdf_path: str,
        prompt: str,
        model: str = "gemini-2.5-pro",
    ) -> dict[str, Any]:
        """Analyze a PDF document with Gemini Pro.

        Args:
            pdf_path: Path to PDF file
            prompt: Analysis prompt
            model: Model to use

        Returns:
            Dict with analysis text and cost estimate
        """
        try:
            logger.info(f"Gemini PDF analysis: {prompt[:50]}...")

            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")

            with open(pdf_path, "rb") as f:
                pdf_data = f.read()

            # Upload file to Gemini
            uploaded_file = genai.upload_file(pdf_path, mime_type="application/pdf")

            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content([prompt, uploaded_file])
            text = response.text

            # Clean up uploaded file
            try:
                genai.delete_file(uploaded_file.name)
            except Exception:
                pass

            # Estimate cost (PDFs can be large)
            file_size_mb = len(pdf_data) / (1024 * 1024)
            input_tokens = len(prompt.split()) * 1.3 + (file_size_mb * 1000)  # rough estimate
            output_tokens = len(text.split()) * 1.3
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            logger.info(f"Gemini PDF response: {len(text)} chars, ~${cost:.4f}")

            return {
                "text": text,
                "model": model,
                "cost": cost,
            }

        except Exception as e:
            logger.error(f"Gemini PDF analysis failed: {e}")
            raise

    def _estimate_cost(self, model: str, input_tokens: float, output_tokens: float) -> float:
        """Estimate cost in dollars."""
        costs = self.COSTS.get(model, self.COSTS["gemini-2.5-flash"])
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost


# Convenience functions for pipeline use

def generate_with_gemini(
    prompt: str,
    model: str = "gemini-2.5-flash",
    **kwargs
) -> str:
    """Generate text with Gemini. Returns text only."""
    client = GeminiClient()
    response = client.generate(prompt, model=model, **kwargs)
    return response["text"]


def plan_with_gemini(
    prompt: str,
    system_instruction: Optional[str] = None,
) -> str:
    """Plan using Gemini Flash with thinking mode."""
    client = GeminiClient()
    response = client.generate_with_thinking(
        prompt,
        model="gemini-2.5-flash",
        thinking_budget=2048,
        system_instruction=system_instruction,
    )
    return response["text"]


def analyze_image_with_gemini(image_path: str, prompt: str) -> str:
    """Analyze image with Gemini Pro vision. Returns text only."""
    client = GeminiClient()
    response = client.analyze_image(image_path, prompt)
    return response["text"]


def analyze_pdf_with_gemini(pdf_path: str, prompt: str) -> str:
    """Analyze PDF with Gemini Pro. Returns text only."""
    client = GeminiClient()
    response = client.analyze_pdf(pdf_path, prompt)
    return response["text"]
