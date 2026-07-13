"""Tests for GitHubEnrichmentEngine -- Sprint 20D.

No internet, no mocked HTTP here -- enrich() takes already-fetched raw
dicts (as the connector fetches them via GitHubClient), so these tests
exercise the orchestration/config-flag logic directly.
"""
from __future__ import annotations

from app.integrations.github.intelligence.config import GitHubIntelligenceConfig
from app.integrations.github.intelligence.enrichment import GitHubEnrichmentEngine

_USER = {"login": "octocat", "name": "The Octocat", "bio": "x", "company": "@github", "followers": 10}
_REPOS = [
    {
        "name": "fastapi-service",
        "description": "A FastAPI backend",
        "language": "Python",
        "fork": False,
        "stargazers_count": 5,
        "topics": ["fastapi", "docker"],
        "pushed_at": "2026-06-01T00:00:00Z",
    }
]
_ORGS = [{"login": "octo-org", "type": "Organization"}]


def test_enrich_returns_full_result_with_default_config():
    engine = GitHubEnrichmentEngine()
    result = engine.enrich(_USER, _REPOS, orgs=_ORGS)

    assert result.repositories_analyzed == 1
    assert "Python" in result.languages
    assert "FastAPI" in result.skills_inferred
    assert "Docker" in result.skills_inferred
    assert result.organizations == ["octo-org"]
    assert result.github_quality_score > 0
    assert result.activity_score > 0
    assert result.last_activity is not None
    assert result.profile_completeness > 0


def test_enrich_never_raises_on_empty_inputs():
    engine = GitHubEnrichmentEngine()
    result = engine.enrich({}, [], orgs=None, readmes=None)

    assert result.repositories_analyzed == 0
    assert result.skills_inferred == []
    assert result.github_quality_score == 0.0


def test_enrich_respects_disabled_repository_analysis():
    config = GitHubIntelligenceConfig(enable_repository_analysis=False)
    engine = GitHubEnrichmentEngine(config)
    result = engine.enrich(_USER, _REPOS, orgs=_ORGS)

    assert result.repositories_analyzed == 0
    assert result.languages == []


def test_enrich_respects_disabled_activity_scoring():
    config = GitHubIntelligenceConfig(enable_activity_scoring=False)
    engine = GitHubEnrichmentEngine(config)
    result = engine.enrich(_USER, _REPOS, orgs=_ORGS)

    assert result.activity_score == 0.0
    assert result.last_activity is None


def test_enrich_respects_disabled_organization_analysis():
    config = GitHubIntelligenceConfig(enable_organization_analysis=False)
    engine = GitHubEnrichmentEngine(config)
    result = engine.enrich(_USER, _REPOS, orgs=_ORGS)

    assert result.organizations == []


def test_enrich_uses_readme_evidence_when_provided():
    engine = GitHubEnrichmentEngine()
    readmes = {"fastapi-service": "Built with LangChain and a PostgreSQL backend."}
    result = engine.enrich(_USER, _REPOS, orgs=_ORGS, readmes=readmes)

    assert "LangChain" in result.skills_inferred
    assert "PostgreSQL" in result.skills_inferred
