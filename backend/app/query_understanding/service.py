"""QueryUnderstandingService: the single entry point for turning recruiter
free-text into a CanonicalJobRequirement.

Pipeline per attempt: PromptBuilder.build() -> LLMClient.generate() ->
JSONResponseParser.parse() -> QueryValidator.validate(). On a
ResponseParseError or QueryValidationError, exactly one retry is made, with
the failure fed back into the prompt as a correction hint. Any other
exception (the LLM call itself failing) is wrapped in LLMClientError -- see
that class's docstring in models.py -- and is NOT retried, since a
provider-level failure (bad API key, network error, rate limit) is very
unlikely to succeed on an immediate second attempt the way a malformed
response might.

All collaborators are constructor-injected with sensible defaults, so
callers needing a fake LLM (tests) or an alternate provider (OpenAI/Claude
later) can substitute one without changing this class.
"""
from __future__ import annotations

from app.query_understanding.gemini_client import LLMClient
from app.query_understanding.models import (
    CanonicalJobRequirement,
    LLMClientError,
    QueryValidationError,
    ResponseParseError,
)
from app.query_understanding.parser import JSONResponseParser
from app.query_understanding.prompt_builder import PromptBuilder
from app.query_understanding.provider import get_default_llm_client
from app.query_understanding.validator import QueryValidator


class QueryUnderstandingService:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        response_parser: JSONResponseParser | None = None,
        validator: QueryValidator | None = None,
    ):
        # Sprint 29: was `GeminiClient()` unconditionally -- now resolved via
        # settings.QUERY_PROVIDER/FALLBACK_PROVIDER (see provider.py) so the
        # provider is a config change, not a code change. An explicitly
        # passed llm_client (every existing test uses FakeLLMClient this
        # way) always wins, unchanged.
        self._llm_client = llm_client or get_default_llm_client()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._response_parser = response_parser or JSONResponseParser()
        self._validator = validator or QueryValidator()

    def parse(self, raw_query: str) -> CanonicalJobRequirement:
        if not raw_query or not raw_query.strip():
            raise QueryValidationError("Recruiter query must not be empty")

        try:
            return self._attempt(raw_query, retry_hint=None)
        except (ResponseParseError, QueryValidationError) as first_error:
            return self._attempt(raw_query, retry_hint=str(first_error))

    def _attempt(self, raw_query: str, retry_hint: str | None) -> CanonicalJobRequirement:
        prompt = self._prompt_builder.build(raw_query, retry_hint=retry_hint)
        raw_output = self._call_llm(prompt)
        data = self._response_parser.parse(raw_output)
        return self._validator.validate(data)

    def _call_llm(self, prompt: str) -> str:
        """Isolates the one call in this pipeline that talks to an external
        provider. Any exception here (missing API key, network failure, SDK
        error, rate limit, etc.) is converted to LLMClientError so callers
        have exactly one typed exception to handle for "the LLM call
        itself failed", distinct from ResponseParseError/QueryValidationError
        which mean the call succeeded but its content was unusable.
        """
        try:
            return self._llm_client.generate(prompt)
        except Exception as e:
            raise LLMClientError(f"LLM provider call failed: {e}") from e
