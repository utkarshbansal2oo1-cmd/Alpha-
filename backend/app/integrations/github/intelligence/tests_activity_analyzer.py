"""Tests for ActivityAnalyzer -- Sprint 20D."""
from __future__ import annotations

from datetime import datetime, timezone

from app.integrations.github.intelligence.activity_analyzer import ActivityAnalyzer
from app.integrations.github.intelligence.config import GitHubIntelligenceConfig

_NOW = datetime(2026, 7, 10, tzinfo=timezone.utc)


def test_analyze_reports_no_activity_when_no_pushed_at_present():
    analyzer = ActivityAnalyzer(GitHubIntelligenceConfig())
    result = analyzer.analyze([{"name": "no-timestamp"}], now=_NOW)

    assert result.last_push_at is None
    assert result.activity_score == 0.0
    assert result.active_repositories == 0


def test_analyze_recent_activity_yields_high_score():
    analyzer = ActivityAnalyzer(GitHubIntelligenceConfig())
    repos = [{"name": "hot-repo", "pushed_at": "2026-07-01T00:00:00Z"}]
    result = analyzer.analyze(repos, now=_NOW)

    assert result.last_push_at is not None
    assert result.months_since_last_activity < 1
    assert result.active_repositories == 1
    assert result.inactive_repositories == 0
    assert result.activity_score > 50


def test_analyze_stale_activity_yields_low_score():
    analyzer = ActivityAnalyzer(GitHubIntelligenceConfig())
    repos = [{"name": "stale-repo", "pushed_at": "2018-01-01T00:00:00Z"}]
    result = analyzer.analyze(repos, now=_NOW)

    assert result.inactive_repositories == 1
    assert result.active_repositories == 0
    assert result.activity_score < 20


def test_analyze_uses_most_recent_push_across_repos():
    analyzer = ActivityAnalyzer(GitHubIntelligenceConfig())
    repos = [
        {"name": "old", "pushed_at": "2019-01-01T00:00:00Z"},
        {"name": "new", "pushed_at": "2026-06-15T00:00:00Z"},
    ]
    result = analyzer.analyze(repos, now=_NOW)

    assert result.last_push_at.year == 2026
    assert result.active_repositories == 1
    assert result.inactive_repositories == 1


def test_analyze_respects_max_repositories_cap():
    config = GitHubIntelligenceConfig(max_repositories=1)
    analyzer = ActivityAnalyzer(config)
    repos = [
        {"name": "a", "pushed_at": "2026-07-01T00:00:00Z"},
        {"name": "b", "pushed_at": "2026-07-01T00:00:00Z"},
    ]
    result = analyzer.analyze(repos, now=_NOW)

    assert result.active_repositories == 1
