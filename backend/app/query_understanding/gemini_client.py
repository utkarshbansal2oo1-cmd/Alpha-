"""LLM client boundary for Query Understanding.

Defines `LLMClient`, the abstract interface every provider (Gemini today,
OpenAI/Claude/anything else tomorrow) must implement, and `GeminiClient`,
the concrete Gemini implementation using Google's current `google-genai`
SDK (the older `google-generativeai` package is deprecated upstream as of
this writing -- deliberately not used here to avoid building on a dead
package on day one).

No business logic lives here -- per the brief, this client does exactly one
thing: send a prompt string, return the raw text response. It does not
parse JSON, does not validate anything, does not know about
CanonicalJobRequirement, and does not retry. All of that lives in
parser.py / validator.py / service.py, which depend only on the abstract
`LLMClient` interface -- never on `GeminiClient` directly -- so swapping in
an OpenAIClient or ClaudeClient later means adding one new class here and
changing what service.py is constructed with, nothing else in this module
or in Search Planner.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import settings


class LLMClient(ABC):
    """Provider-agnostic interface: send a prompt, get raw text back."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Sends `prompt` to the underlying LLM and returns its raw text
        response, unparsed and unvalidated."""
        raise NotImplementedError


class GeminiClient(LLMClient):
    """Google Gemini implementation of LLMClient, via the `google-genai` SDK.

    The SDK is imported lazily inside `_ensure_client`, not at module import
    time -- this keeps `import app.query_understanding.gemini_client` (and
    everything that transitively imports it, e.g. service.py) working even
    in environments where the SDK isn't installed, such as unit tests that
    inject a fake LLMClient and never touch this class at all.
    """

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.5-flash"):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model_name = model_name
        self._client = None  # constructed lazily on first generate() call

    def _ensure_client(self):
        if self._client is None:
            from google import genai  # local import, see class docstring

            if not self._api_key:
                raise RuntimeError(
                    "GeminiClient requires GEMINI_API_KEY to be set (see backend/.env.example)"
                )
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def generate(self, prompt: str) -> str:
        client = self._ensure_client()
        # response_mime_type="application/json" asks Gemini to constrain its
        # own output to JSON at the API level -- this is what "force JSON
        # output" (requirement 4) means at the client layer. It is still
        # parsed and validated downstream (parser.py / validator.py) rather
        # than trusted blindly, because "asked for JSON" is not the same
        # guarantee as "validated against our schema".
        response = client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return response.text
