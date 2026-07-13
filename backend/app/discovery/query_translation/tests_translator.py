"""Tests for ConnectorQueryTranslator -- Sprint 20C.

Covers the sprint brief's own example queries: Senior Golang Developer,
Senior Python FastAPI Developer, React TypeScript Engineer, Machine
Learning Engineer PyTorch, DevOps Kubernetes AWS, AI Engineer LangChain.
"""
from __future__ import annotations

import pytest

from app.discovery.query_translation.models import ConnectorTranslationConfig
from app.discovery.query_translation.translator import ConnectorQueryTranslator
from app.search_planner.models import CanonicalJobRequirement, SearchPlan


def _plan():
    return SearchPlan(strict=[], expanded=[], search_terms=[], weights={}, unresolved=[])


@pytest.mark.parametrize(
    "role,skills,raw_query,expected_terms",
    [
        ("Senior Golang Developer", [], "Senior Golang Developer", {"golang", "language:Go"}),
        ("Senior Python FastAPI Developer", ["FastAPI"], "Senior Python FastAPI Developer", {"python", "fastapi"}),
        ("React TypeScript Engineer", ["TypeScript"], "React TypeScript Engineer", {"react", "typescript"}),
        ("Machine Learning Engineer", ["PyTorch"], "Machine Learning Engineer PyTorch", {"pytorch"}),
        ("DevOps Engineer", ["Kubernetes", "AWS"], "DevOps Kubernetes AWS", {"kubernetes", "aws"}),
        ("AI Engineer", ["LangChain"], "AI Engineer LangChain", {"langchain"}),
    ],
)
def test_github_translation_covers_sprint_brief_examples(role, skills, raw_query, expected_terms):
    translator = ConnectorQueryTranslator()
    requirement = CanonicalJobRequirement(role=role, skills=skills)
    result = translator.translate("github", requirement, raw_query, _plan())

    assert result.connector_name == "github"
    assert result.is_passthrough is False
    produced = {q.lower() for q in result.connector_queries}
    assert {t.lower() for t in expected_terms} <= produced


def test_github_translation_never_exceeds_max_queries():
    config = ConnectorTranslationConfig(max_queries_per_connector=8)
    translator = ConnectorQueryTranslator(config=config)
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=[])
    result = translator.translate("github", requirement, "Senior Golang Developer", _plan())
    assert len(result.connector_queries) <= 8


def test_github_translation_respects_lower_max_queries_config():
    config = ConnectorTranslationConfig(max_queries_per_connector=2)
    translator = ConnectorQueryTranslator(config=config)
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=[])
    result = translator.translate("github", requirement, "Senior Golang Developer", _plan())
    assert len(result.connector_queries) <= 2


def test_greenhouse_translation_is_passthrough_single_search():
    translator = ConnectorQueryTranslator()
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=["Go"])
    result = translator.translate("greenhouse_ats", requirement, "Backend Engineer with Go", _plan())
    assert result.is_passthrough is True
    assert "Backend Engineer with Go" in result.connector_queries
    assert "Backend Engineer" in result.connector_queries
    assert "Go" in result.connector_queries


def test_browser_extension_translation_returns_canonical_query_only():
    translator = ConnectorQueryTranslator()
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=["Go"])
    result = translator.translate("browser_extension", requirement, "Backend Engineer with Go", _plan())
    assert result.is_passthrough is True
    assert result.connector_queries == ["Backend Engineer"]


def test_unknown_connector_falls_back_to_generic_passthrough():
    translator = ConnectorQueryTranslator()
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=[])
    result = translator.translate("some_future_ats", requirement, "Backend Engineer", _plan())
    assert result.is_passthrough is True
    assert result.connector_queries == ["Backend Engineer"]


def test_disabling_a_connector_forces_generic_passthrough():
    config = ConnectorTranslationConfig(connector_enabled={"github": False})
    translator = ConnectorQueryTranslator(config=config)
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=[])
    result = translator.translate("github", requirement, "Senior Golang Developer", _plan())
    assert result.is_passthrough is True
    assert result.connector_queries == ["Senior Golang Developer"]


def test_github_filters_extracted_from_qualifier_style_terms():
    translator = ConnectorQueryTranslator()
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=[])
    result = translator.translate("github", requirement, "Senior Golang Developer", _plan())
    assert result.filters.get("language") == "Go"
