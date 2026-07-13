"""Shared test doubles used across test modules.

Added during code review to remove duplication: query_understanding/tests.py
and routers/tests_search_pipeline.py each defined their own near-identical
FakeLLMClient. Both now import this one definition instead.

This module is not itself a test file (it defines no test_* functions and
is not named tests.py/tests_*.py), so pytest.ini's python_files pattern does
not collect it -- it is imported by the test modules that need it, exactly
like any other test helper/fixture module.
"""
from __future__ import annotations

from app.query_understanding.gemini_client import LLMClient


class FakeLLMClient(LLMClient):
    """Returns a fixed sequence of canned responses, one per call, so tests
    can script exactly what "the model" says on attempt 1 vs. attempt 2 (the
    retry), without any real network access or API key. Records every
    prompt it was called with (`prompts_received`) and how many times it
    was called (`call_count`), so tests can assert on retry behavior from
    either angle.
    """

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.prompts_received: list[str] = []
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        self.prompts_received.append(prompt)
        if not self._responses:
            raise AssertionError("FakeLLMClient called more times than responses were scripted")
        return self._responses.pop(0)
