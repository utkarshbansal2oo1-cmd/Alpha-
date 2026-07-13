"""Parses raw LLM text output into a plain JSON-decoded dict.

Deliberately separate from validator.py: this module answers "is this text
valid JSON at all", not "does this JSON satisfy the CanonicalJobRequirement
shape" -- that second question is validator.py's job. Keeping them apart
means a malformed-JSON failure and a wrong-shape failure are distinguishable
error cases (see app.query_understanding.models.ResponseParseError vs.
QueryValidationError), which matters for building a useful retry hint in
service.py.
"""
from __future__ import annotations

import json
import re

from app.query_understanding.models import ResponseParseError

# Gemini (and most LLMs) sometimes wrap JSON in a markdown code fence even
# when explicitly asked not to. Stripped defensively rather than trusting
# "force JSON output" alone -- see gemini_client.py's docstring for why that
# request is a hint to the API, not a hard guarantee.
_CODE_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class JSONResponseParser:
    """Turns raw LLM text into a dict, or raises ResponseParseError."""

    def parse(self, raw_text: str) -> dict:
        if raw_text is None:
            raise ResponseParseError("LLM response was empty (None)")

        cleaned = _CODE_FENCE_PATTERN.sub("", raw_text).strip()

        if not cleaned:
            raise ResponseParseError("LLM response was empty after stripping formatting")

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ResponseParseError(f"LLM response was not valid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ResponseParseError(
                f"LLM response was valid JSON but not a JSON object (got {type(data).__name__})"
            )

        return data
