"""Tests for the GitHub normalizer -- Sprint 20B, extended in Sprint 20D."""
from __future__ import annotations

from datetime import datetime, timezone

from app.integrations.github.intelligence.enrichment import GitHubEnrichment
from app.integrations.github.normalizer import infer_languages, normalize_github_candidate


def test_infer_languages_excludes_forks_and_ranks_by_frequency():
    repos = [
        {"language": "Python", "fork": False},
        {"language": "Python", "fork": False},
        {"language": "Go", "fork": False},
        {"language": "Rust", "fork": True},  # forked -- excluded
        {"language": None, "fork": False},  # no language -- excluded
    ]
    assert infer_languages(repos) == ["Python", "Go"]


def test_infer_languages_empty_when_no_repos():
    assert infer_languages([]) == []


def test_normalize_github_candidate_maps_profile_fields():
    user = {
        "login": "octocat",
        "name": "The Octocat",
        "bio": "Building things",
        "company": "@github",
        "location": "San Francisco",
        "html_url": "https://github.com/octocat",
    }
    repos = [{"language": "Python", "fork": False}, {"language": "JavaScript", "fork": False}]

    request = normalize_github_candidate(user, repos)

    assert request.name == "The Octocat"
    assert request.headline == "Building things"
    assert request.current_company == "@github"
    assert request.location == "San Francisco"
    assert set(request.skills) == {"Python", "JavaScript"}
    assert request.public_profile_url == "https://github.com/octocat"
    assert request.source_type == "github"
    assert request.source_url == "https://github.com/octocat"


def test_normalize_github_candidate_falls_back_to_login_when_no_name():
    user = {"login": "octocat"}
    request = normalize_github_candidate(user, [])
    assert request.name == "octocat"


# --- Sprint 20D additions: optional `enrichment` parameter ------------------


def test_normalize_github_candidate_leaves_enrichment_fields_empty_when_omitted():
    """Every pre-Sprint-20D caller (including the tests above) doesn't pass
    `enrichment` at all -- confirms the new parameter is fully backward
    compatible and defaults to None/empty, never breaking an existing
    caller's expectations."""
    user = {"login": "octocat", "name": "The Octocat"}
    request = normalize_github_candidate(user, [])

    assert request.github_quality_score is None
    assert request.github_activity_score is None
    assert request.github_repositories_analyzed is None
    assert request.github_languages == []
    assert request.github_topics == []
    assert request.github_organizations == []
    assert request.github_skills_inferred == []
    assert request.github_last_activity is None
    assert request.github_profile_completeness is None


def test_normalize_github_candidate_populates_fields_when_enrichment_provided():
    user = {"login": "octocat", "name": "The Octocat"}
    repos = [{"language": "Python", "fork": False}]
    enrichment = GitHubEnrichment(
        github_quality_score=72.5,
        activity_score=60.0,
        repositories_analyzed=3,
        languages=["Python", "Go"],
        topics=["backend"],
        organizations=["octo-org"],
        skills_inferred=["FastAPI", "Docker"],
        last_activity=datetime(2026, 6, 1, tzinfo=timezone.utc),
        profile_completeness=83.3,
    )

    request = normalize_github_candidate(user, repos, enrichment=enrichment)

    assert request.github_quality_score == 72.5
    assert request.github_activity_score == 60.0
    assert request.github_repositories_analyzed == 3
    assert request.github_languages == ["Python", "Go"]
    assert request.github_topics == ["backend"]
    assert request.github_organizations == ["octo-org"]
    assert request.github_skills_inferred == ["FastAPI", "Docker"]
    assert request.github_last_activity == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert request.github_profile_completeness == 83.3
    # Existing, pre-Sprint-20D fields are still populated the same way.
    assert request.name == "The Octocat"
    assert request.skills == ["Python"]
