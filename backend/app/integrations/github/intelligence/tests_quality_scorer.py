"""Tests for QualityScorer -- Sprint 20D."""
from __future__ import annotations

from app.integrations.github.intelligence.activity_analyzer import ActivityAnalysis
from app.integrations.github.intelligence.organization_analyzer import OrganizationAnalysis
from app.integrations.github.intelligence.quality_scorer import QualityScorer
from app.integrations.github.intelligence.repository_analyzer import RepositoryAnalysis, RepositorySummary


def test_score_is_zero_for_empty_profile():
    scorer = QualityScorer()
    result = scorer.score(
        user={},
        repo_analysis=RepositoryAnalysis(),
        activity_analysis=ActivityAnalysis(),
        org_analysis=OrganizationAnalysis(),
    )

    assert result.overall == 0.0
    assert result.repository_quality == 0.0
    assert result.profile_completeness == 0.0


def test_score_rewards_repos_activity_followers_and_orgs():
    scorer = QualityScorer()
    repo_analysis = RepositoryAnalysis(
        own_repositories=5,
        total_stars=50,
        total_forks=10,
        top_repositories=[
            RepositorySummary(name="a", description="A project", license_name="MIT"),
            RepositorySummary(name="b"),
        ],
    )
    activity_analysis = ActivityAnalysis(activity_score=80.0)
    org_analysis = OrganizationAnalysis(organization_count=1, verified_organization=True)
    user = {"bio": "x", "company": "x", "location": "x", "blog": "x", "avatar_url": "x", "name": "x", "followers": 30}

    result = scorer.score(user, repo_analysis, activity_analysis, org_analysis)

    assert result.overall > 0
    assert result.profile_completeness == 100.0
    assert result.followers_score == 30.0
    assert result.organization_quality == 45.0  # 20 (1 org) + 25 (verified)
    assert result.activity == 80.0


def test_score_caps_all_subscores_at_100():
    scorer = QualityScorer()
    repo_analysis = RepositoryAnalysis(own_repositories=1000, total_stars=10000, total_forks=10000)
    activity_analysis = ActivityAnalysis(activity_score=100.0)
    org_analysis = OrganizationAnalysis(organization_count=50, verified_organization=True)
    user = {"followers": 999999}

    result = scorer.score(user, repo_analysis, activity_analysis, org_analysis)

    assert result.overall <= 100.0
    assert result.repository_quality <= 100.0
    assert result.popularity <= 100.0
    assert result.followers_score <= 100.0
    assert result.organization_quality <= 100.0
