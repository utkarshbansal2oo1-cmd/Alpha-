"""Tests for GroqClient -- Sprint 29.

No real Groq calls -- httpx.post is monkeypatched, mirroring how
gemini_client.py's tests (if any existed) would stub the google-genai SDK.
GroqClient's contract is identical to GeminiClient's: send a prompt, return
raw text, raise on missing API key -- these tests assert exactly that.
"""
from __future__ import annotations

import pytest

from app.query_understanding.groq_client import GroqClient


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_generate_returns_message_content(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse(
            {"choices": [{"message": {"content": '{"role": "Java Developer"}'}}]}
        )

    monkeypatch.setattr("httpx.post", fake_post)

    client = GroqClient(api_key="fake-key")
    result = client.generate("Find me a Java Developer")

    assert result == '{"role": "Java Developer"}'
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer fake-key"
    assert captured["json"]["messages"][0]["content"] == "Find me a Java Developer"
    assert captured["json"]["response_format"] == {"type": "json_object"}


def test_generate_raises_without_api_key():
    client = GroqClient(api_key="")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        client.generate("anything")
