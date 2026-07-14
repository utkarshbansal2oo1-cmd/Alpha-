"""Provider selection for Query Understanding's LLMClient -- Sprint 29.

QueryUnderstandingService (service.py) depends only on the abstract
LLMClient interface -- it has never known or cared which concrete provider
it's talking to. This module is the one new piece that decides, at
construction time, which concrete client that ends up being, based on
settings.QUERY_PROVIDER (default "groq") with settings.FALLBACK_PROVIDER
(default "gemini") as a safety net if the primary provider's API key isn't
configured.

This is deliberately a plain function, not a class -- same
dependency-injection-friendly pattern as get_matching_config() and every
other provider function in this codebase. Nothing here prevents a caller
(or a test) from constructing GeminiClient() or GroqClient() directly and
passing it to QueryUnderstandingService -- this factory only decides the
*default* when no explicit llm_client is given.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.query_understanding.gemini_client import GeminiClient, LLMClient
from app.query_understanding.groq_client import GroqClient

logger = logging.getLogger(__name__)

_PROVIDER_KEY_SETTING = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def _build_client(provider: str) -> LLMClient:
    provider = provider.strip().lower()
    if provider == "groq":
        return GroqClient()
    if provider == "gemini":
        return GeminiClient()
    raise ValueError(f"Unknown QUERY_PROVIDER/FALLBACK_PROVIDER: {provider!r}")


def _has_key_configured(provider: str) -> bool:
    setting_name = _PROVIDER_KEY_SETTING.get(provider.strip().lower())
    return bool(setting_name and getattr(settings, setting_name, ""))


def get_default_llm_client() -> LLMClient:
    """Returns the LLMClient QueryUnderstandingService should use when no
    explicit one is injected -- settings.QUERY_PROVIDER if its API key is
    configured, otherwise settings.FALLBACK_PROVIDER, logged either way so
    a "why is it using Gemini/Groq" question is always answerable from the
    logs (same principle as Sprint 28's logging fix)."""
    primary = settings.QUERY_PROVIDER
    fallback = settings.FALLBACK_PROVIDER

    if _has_key_configured(primary):
        logger.info("query_understanding.provider_selected", extra={"provider": primary})
        return _build_client(primary)

    if _has_key_configured(fallback):
        logger.warning(
            "query_understanding.provider_fallback",
            extra={
                "requested_provider": primary,
                "reason": f"{_PROVIDER_KEY_SETTING.get(primary.strip().lower())} not set",
                "fallback_provider": fallback,
            },
        )
        return _build_client(fallback)

    # Neither has a key configured -- fall through to the primary anyway so
    # the existing "GroqClient/GeminiClient requires <KEY> to be set" error
    # surfaces at generate() time, exactly as before this module existed,
    # rather than this factory inventing a new failure mode.
    logger.warning(
        "query_understanding.provider_unconfigured",
        extra={"requested_provider": primary, "fallback_provider": fallback},
    )
    return _build_client(primary)
