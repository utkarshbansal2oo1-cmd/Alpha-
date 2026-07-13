"""Tests for RepositoryAnalyzer -- Sprint 20D."""
from __future__ import annotations

from app.integrations.github.intelligence.config import GitHubIntelligenceConfig
from app.integrations.github.intelligence.repository_analyzer import RepositoryAnalyzer

_REPOS = [
    {
        "name": "fastapi-service",
        "description": "A FastAPI backend",
        "language": "Python",
        "fork": False,
        "stargazers_count": 42,
        "forks_count": 5,
        "watchers_count": 42,
        "license": {"name": "MIT License"},
        "default_branch": "main",
        "topics": ["fastapi", "backend"],
        "pushed_at": "2026-06-01T00:00:00Z",
    },
    {
        "name": "old-fork",
        "description": None,
        "language": "JavaScript",
        "fork": True,
        "stargazers_count": 100,
        "forks_count": 0,
        "watchers_count": 100,
        "license": None,
        "default_branch": "master",
        "topics": [],
        "pushed_at": "2020-01-01T00:00:00Z",
    },
    {
        "name": "go-cli",
        "description": "A CLI tool",
        "language": "Go",
        "fork": False,
        "stargazers_count": 7,
        "forks_count": 1,
        "watchers_count": 7,
        "license": {"name": "Apache License 2.0"},
        "default_branch": "main",
        "topics": ["cli", "backend"],
        "pushed_at": "2026-05-01T00:00:00Z",
    },
]


def test_analyze_counts_own_vs_forked_repos():
    analyzer = RepositoryAnalyzer(GitHubIntelligenceConfig())
    result = analyzer.analyze(_REPOS)

    assert result.repositories_analyzed == 3
    assert result.own_repositories == 2
    assert result.forked_repositories == 1


def test_analyze_aggregates_languages_topics_licenses_and_totals():
    analyzer = RepositoryAnalyzer(GitHubIntelligenceConfig())
    result = analyzer.analyze(_REPOS)

    # Fork's language (JavaScript) must not count as an "own" language.
    assert "JavaScript" not in result.languages
    assert "Python" in result.languages
    assert "Go" in result.languages
    assert "backend" in result.topics
    assert "MIT License" in result.licenses
    assert "Apache License 2.0" in result.licenses
    assert result.total_stars == 42 + 100 + 7
    assert result.total_forks == 5 + 0 + 1
    assert result.total_watchers == 42 + 100 + 7


def test_analyze_ranks_top_repositories_by_stars():
    analyzer = RepositoryAnalyzer(GitHubIntelligenceConfig())
    result = analyzer.analyze(_REPOS)

    assert result.top_repositories[0].name == "old-fork"
    assert result.top_repositories[0].stargazers_count == 100


def test_analyze_respects_max_repositories_cap():
    config = GitHubIntelligenceConfig(max_repositories=1)
    analyzer = RepositoryAnalyzer(config)
    result = analyzer.analyze(_REPOS)

    assert result.repositories_analyzed == 1


def test_analyze_handles_empty_repo_list():
    analyzer = RepositoryAnalyzer(GitHubIntelligenceConfig())
    result = analyzer.analyze([])

    assert result.repositories_analyzed == 0
    assert result.languages == []
    assert result.top_repositories == []
