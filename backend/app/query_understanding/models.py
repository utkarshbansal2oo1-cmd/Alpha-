"""Typed contracts for the Query Understanding Engine.

This module reuses CanonicalJobRequirement from app.search_planner.models
rather than redefining it -- Query Understanding's job is to PRODUCE that
exact object (see docs/KNOWLEDGE_ENGINE.md's pipeline: Query Understanding
-> Knowledge Engine expansion -> ... ; Search Planner already consumes
CanonicalJobRequirement, so Query Understanding must emit the same type,
not a parallel/duplicate one).

Only three small exception classes live here (not a separate exceptions.py,
per the file list given for this module) -- they are typed data about a
failure the same way the other models here are typed data about success.
"""
from __future__ import annotations

from app.search_planner.models import CanonicalJobRequirement

__all__ = [
    "CanonicalJobRequirement",
    "ResponseParseError",
    "QueryValidationError",
    "LLMClientError",
]


class ResponseParseError(Exception):
    """Raised by parser.py when the raw LLM output cannot be parsed into a
    JSON object at all (e.g. not valid JSON even after stripping markdown
    fences). Distinct from QueryValidationError -- this is "the text isn't
    JSON", not "the JSON doesn't match the expected shape".
    """


class QueryValidationError(Exception):
    """Raised by validator.py when the parsed JSON IS valid JSON but does
    not satisfy the CanonicalJobRequirement contract (missing/blank role,
    skills not a list of strings, unexpected types, etc.). Carries a
    human-readable message that service.py feeds back into the retry
    prompt, so the single retry attempt has a concrete reason to correct.
    """


class LLMClientError(Exception):
    """Raised by service.py when the underlying LLMClient.generate() call
    itself fails -- e.g. GeminiClient's RuntimeError for a missing API key,
    or any provider/SDK-level exception (network failure, auth error, rate
    limit, etc). This is distinct from ResponseParseError/QueryValidationError,
    which both assume the call succeeded and something came back to parse or
    validate: LLMClientError means no usable response was produced at all.

    Added during code review: previously an arbitrary exception from
    generate() propagated uncaught past QueryUnderstandingService, giving
    routers no typed error to map to a clean HTTP response. Wrapping it here
    lets routers/search_pipeline.py catch one specific type and return a
    502, instead of leaking a raw 500.
    """
