"""Exceptions raised while loading/validating taxonomy data.

Kept as their own module (rather than nested in loader.py) so engine.py,
loader.py, and tests can all import them without a circular import.
"""
from __future__ import annotations


class KnowledgeEngineError(Exception):
    """Base class for all Knowledge Engine errors."""


class TaxonomyValidationError(KnowledgeEngineError):
    """Raised when one or more taxonomy files fail structural validation.

    Per docs/KNOWLEDGE_ENGINE.md section 6: "a failed validation should
    hard-fail application startup" -- this exception is intentionally not
    caught and swallowed anywhere in engine.py/loader.py. Carries the full
    ValidationResult so the caller can log every issue, not just the first.
    """

    def __init__(self, message: str, result=None):
        super().__init__(message)
        self.result = result
