"""GitHub Quality Score -- Sprint 20D.

Combines repository quality/popularity, activity, follower signal, and
organization/profile completeness into one 0-100 overall score. Every
sub-score is a bounded, documented heuristic over real GitHub API
fields -- there is no ground truth for "developer quality," so this is
explicitly a proxy signal for ranking/triage, not a certification.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.integrations.github.intelligence.activity_analyzer import ActivityAnalysis
from app.integrations.github.intelligence.organization_analyzer import OrganizationAnalysis
from app.integrations.github.intelligence.repository_analyzer import RepositoryAnalysis

_PROFILE_FIELDS = ("bio", "company", "location", "blog", "avatar_url", "name")


class GitHubQualityScore(BaseModel):
    overall: float = Field(default=0.0, ge=0.0, le=100.0)
    repository_quality: float = Field(default=0.0, ge=0.0, le=100.0)
    popularity: float = Field(default=0.0, ge=0.0, le=100.0)
    activity: float = Field(default=0.0, ge=0.0, le=100.0)
    followers_score: float = Field(default=0.0, ge=0.0, le=100.0)
    organization_quality: float = Field(default=0.0, ge=0.0, le=100.0)
    profile_completeness: float = Field(default=0.0, ge=0.0, le=100.0)


def _profile_completeness(user: dict) -> float:
    present = sum(1 for field in _PROFILE_FIELDS if user.get(field))
    return round(100.0 * present / len(_PROFILE_FIELDS), 2)


class QualityScorer:
    def score(
        self,
        user: dict,
        repo_analysis: RepositoryAnalysis,
        activity_analysis: ActivityAnalysis,
        org_analysis: OrganizationAnalysis,
    ) -> GitHubQualityScore:
        # Repository quality: rewards owning real (non-fork) repos with
        # some documentation signal (a license or a description), capped.
        documented = 0
        for repo in repo_analysis.top_repositories:
            if repo.description or repo.license_name:
                documented += 1
        repository_quality = min(100.0, repo_analysis.own_repositories * 8.0 + documented * 4.0)

        popularity = min(100.0, repo_analysis.total_stars * 2.0 + repo_analysis.total_forks * 1.0)

        followers = user.get("followers", 0) or 0
        followers_score = min(100.0, float(followers))

        organization_quality = min(
            100.0, org_analysis.organization_count * 20.0 + (25.0 if org_analysis.verified_organization else 0.0)
        )

        profile_completeness = _profile_completeness(user)

        overall = round(
            repository_quality * 0.30
            + popularity * 0.20
            + activity_analysis.activity_score * 0.25
            + followers_score * 0.10
            + organization_quality * 0.10
            + profile_completeness * 0.05,
            2,
        )

        return GitHubQualityScore(
            overall=min(100.0, overall),
            repository_quality=round(repository_quality, 2),
            popularity=round(popularity, 2),
            activity=activity_analysis.activity_score,
            followers_score=round(followers_score, 2),
            organization_quality=round(organization_quality, 2),
            profile_completeness=profile_completeness,
        )
