"""Tests for get_default_llm_client()'s provider/fallback selection --
Sprint 29. Patches app.config.settings directly (the same object every
provider function in this codebase reads from) rather than touching real
environment variables, so these tests are hermetic and order-independent.
"""
from __future__ import annotations

from app.query_understanding.gemini_client import GeminiClient
from app.query_understanding.groq_client import GroqClient
from app.query_understanding.provider import get_default_llm_client


def test_uses_groq_when_primary_and_key_configured(monkeypatch):
    monkeypatch.setattr("app.query_understanding.provider.settings.QUERY_PROVIDER", "groq")
    monkeypatch.setattr("app.query_understanding.provider.settings.FALLBACK_PROVIDER", "gemini")
    monkeypatch.setattr("app.query_understanding.provider.settings.GROQ_API_KEY", "groq-key")
    monkeypatch.setattr("app.query_understanding.provider.settings.GEMINI_API_KEY", "")

    client = get_default_llm_client()

    assert isinstance(client, GroqClient)


def test_falls_back_to_gemini_when_groq_key_missing(monkeypatch):
    monkeypatch.setattr("app.query_understanding.provider.settings.QUERY_PROVIDER", "groq")
    monkeypatch.setattr("app.query_understanding.provider.settings.FALLBACK_PROVIDER", "gemini")
    monkeypatch.setattr("app.query_understanding.provider.settings.GROQ_API_KEY", "")
    monkeypatch.setattr("app.query_understanding.provider.settings.GEMINI_API_KEY", "gemini-key")

    client = get_default_llm_client()

    assert isinstance(client, GeminiClient)


def test_falls_through_to_primary_when_neither_key_configured(monkeypatch):
    monkeypatch.setattr("app.query_understanding.provider.settings.QUERY_PROVIDER", "groq")
    monkeypatch.setattr("app.query_understanding.provider.settings.FALLBACK_PROVIDER", "gemini")
    monkeypatch.setattr("app.query_understanding.provider.settings.GROQ_API_KEY", "")
    monkeypatch.setattr("app.query_understanding.provider.settings.GEMINI_API_KEY", "")

    client = get_default_llm_client()

    # Neither key is configured -- falls through to the primary so the
    # existing "requires <KEY> to be set" error surfaces at generate()
    # time, same failure mode as before this module existed.
    assert isinstance(client, GroqClient)


def test_gemini_as_explicit_primary(monkeypatch):
    monkeypatch.setattr("app.query_understanding.provider.settings.QUERY_PROVIDER", "gemini")
    monkeypatch.setattr("app.query_understanding.provider.settings.FALLBACK_PROVIDER", "groq")
    monkeypatch.setattr("app.query_understanding.provider.settings.GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr("app.query_understanding.provider.settings.GROQ_API_KEY", "")

    client = get_default_llm_client()

    assert isinstance(client, GeminiClient)
