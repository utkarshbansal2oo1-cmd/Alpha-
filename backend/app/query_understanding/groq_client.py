"""Groq implementation of LLMClient -- Sprint 29.

Gemini's free tier caps Query Understanding at 20 generate_content calls a
day (see gemini_client.py and docs/TECH_DEBT.md's Sprint 29 entry) -- a
limit real recruiter testing exhausted repeatedly in a single session.
Groq's free developer tier gives 1,000 requests/day on Llama 3.3 70B, at
zero cost and with no credit card, which is why it is now the default
Query Understanding provider (see get_default_llm_client() in
provider.py).

Groq's API is OpenAI-compatible (POST /openai/v1/chat/completions), so no
new SDK dependency is introduced -- this uses `httpx`, already a direct
dependency (see requirements.txt), exactly the way GeminiClient uses
`google-genai`. Like GeminiClient, this class does exactly one thing: send
a prompt, return raw text. No parsing, no validation, no retry -- all of
that stays in parser.py / validator.py / service.py, unchanged, since both
clients satisfy the same LLMClient interface.
"""
from __future__ import annotations

from app.config import settings
from app.query_understanding.gemini_client import LLMClient

_GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqClient(LLMClient):
    """Groq implementation of LLMClient, via Groq's OpenAI-compatible REST
    API. Constructed lazily -- no network call happens until generate() is
    first invoked, mirroring GeminiClient's lazy-client pattern so importing
    this module never requires GROQ_API_KEY to be set (tests inject a fake
    LLMClient and never touch this class)."""

    def __init__(self, api_key: str | None = None, model_name: str = _DEFAULT_MODEL):
        self._api_key = api_key or settings.GROQ_API_KEY
        self._model_name = model_name

    def generate(self, prompt: str) -> str:
        if not self._api_key:
            raise RuntimeError(
                "GroqClient requires GROQ_API_KEY to be set (see backend/.env.example)"
            )

        import httpx  # local import, mirrors GeminiClient's lazy SDK import

        response = httpx.post(
            _GROQ_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model_name,
                "messages": [{"role": "user", "content": prompt}],
                # Groq's OpenAI-compatible JSON mode -- same intent as
                # GeminiClient's response_mime_type="application/json":
                # ask the provider to constrain its own output to JSON.
                # Still parsed/validated downstream, never trusted blindly.
                "response_format": {"type": "json_object"},
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
