"""Shared pieces for the GLM-5.3-flash seat bake-off (owner-ordered, 2026-08-30)."""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.integrations.structured_client import OpenAIStructuredClient, get_structured_client  # noqa: E402
from backend.pipeline.briefing_gates import names_in, numbers_in, normalize  # noqa: E402

GLM_KEY = None
for line in open("/Users/mazbot/.openclaw/service-env/glm-coding.env"):
    if line.startswith("GLM_API_KEY="):
        GLM_KEY = line.strip().split("=", 1)[1]

class ZaiGLMClient(OpenAIStructuredClient):
    """GLM via z.ai: default (mandatory) thinking, json_object mode, schema by instruction."""
    def generate_structured(self, prompt, schema, system="", max_tokens=8000):
        max_tokens = max(max_tokens, 16000)  # GLM thinking shares the budget
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system + "\nReturn ONLY a JSON object matching this schema: " + json.dumps(schema)},
                      {"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            extra_body={"reasoning_effort": "low"},
        )
        usage = {"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens}
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.S).strip()
        try:
            return json.loads(content), usage
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if match:
                return json.loads(match.group(0)), usage
            raise RuntimeError(
                f"GLM unusable output (finish={response.choices[0].finish_reason}, "
                f"len={len(content)}): {content[:200]!r}")

def glm_client():
    return ZaiGLMClient("glm-5.3-flash", api_key=GLM_KEY, base_url="https://api.z.ai/api/paas/v4")

def atom_grounding(texts, corpus):
    """Fraction of hard atoms (names + numbers) not present in the corpus.

    Case-insensitive: Supadata transcripts are lowercase, so literal-case
    matching falsely flags every proper noun (found 2026-08-30, SRC_1)."""
    corpus_norm = normalize(corpus).casefold()
    corpus_nums = numbers_in(corpus)
    total = missing = 0
    missing_atoms = []
    for text in texts:
        for atom in numbers_in(text):
            total += 1
            if atom not in corpus_nums:
                missing += 1; missing_atoms.append(atom)
        for atom in names_in(text):
            total += 1
            if normalize(atom).casefold() not in corpus_norm:
                missing += 1; missing_atoms.append(atom)
    return total, missing, missing_atoms

def density(text):
    """Distinct hard atoms delivered (the decisive writer measure)."""
    return len(numbers_in(text) | {normalize(n) for n in names_in(text)})
