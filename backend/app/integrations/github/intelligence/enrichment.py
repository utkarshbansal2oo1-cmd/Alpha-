"""GitHub Candidate Enrichment -- Sprint 20D.

Orchestrates the four analyzers + quality scorer above into one
GitHubEnrichment result per candidate. This is the one function the
GitHub connector calls; it owns no HTTP/API-calling logic itself (that
stays in app.integrations.github.client.GitHubClient) and does not touch
Candidate Intelligence Lifecycle, Matching, Ranking, or the Repository --
its output is attached to a CandidateImportRequest by the connector, and
flows through the existing normalize_import()/upsert() seam exactly like
every other captured field.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from pydantic import BaseModel, Field

from app.integrations.github.intelligence.activity_analyzer import ActivityAnalyzer
from app.integrations.github.intelligence.config import GitHubIntelligenceConfig
from app.integrations.github.intelligence.organization_analyzer import OrganizationAnalyzer
from app.integrations.github.intelligence.quality_scorer import QualityScorer
from app.integrations.github.intelligence.repository_analyzer import RepositoryAnalyzer
from app.integrations.github.intelligence.skill_extractor import SkillExtractor

logger = logging.getLogger(__name__)


class GitHubEnrichment(BaseModel):
    """Exactly the fields the sprint brief's ENRICHMENT section lists."""

    github_quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    activity_score: float = Field(default=0.0, ge=0.0, le=100.0)
    repositories_analyzed: int = 0
    languages: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    skills_inferred: list[str] = Field(default_factory=list)
    last_activity: datetime | None = None
    profile_completeness: float = Field(default=0.0, ge=0.0, le=100.0)


class GitHubEnrichmentEngine:
    """Wires the analyzers together behind one call, respecting the
    config's per-stage enable/disable flags -- disabling a stage yields
    that stage's default (empty/zero) values honestly, never a
    fabricated substitute."""

    def __init__(self, config: GitHubIntelligenceConfig | None = None):
        self._config = config or GitHubIntelligenceConfig()
        self._repository_analyzer = RepositoryAnalyzer(self._config)
        self._activity_analyzer = ActivityAnalyzer(self._config)
        self._organization_analyzer = OrganizationAnalyzer(self._config)
        self._skill_extractor = SkillExtractor(self._config)
        self._quality_scorer = QualityScorer()

    def enrich(
        self,
        user: dict,
        repos: list[dict],
        orgs: list[dict] | None = None,
        readmes: dict[str, str] | None = None,
    ) -> GitHubEnrichment:
        started_at = time.monotonic()

        repo_analysis = (
            self._repository_analyzer.analyze(repos)
            if self._config.enable_repository_analysis
            else self._repository_analyzer.analyze([])
        )
        activity_analysis = (
            self._activity_analyzer.analyze(repos)
            if self._config.enable_activity_scoring
            else self._activity_analyzer.analyze([])
        )
        org_analysis = (
            self._organization_analyzer.analyze(user, orgs)
            if self._config.enable_organization_analysis
            else self._organization_analyzer.analyze(user, None)
        )
        skill_result = self._skill_extractor.extract(repos, readmes)
        quality = self._quality_scorer.score(user, repo_analysis, activity_analysis, org_analysis)

        elapsed_ms = round((time.monotonic() - started_at) * 1000, 1)
        logger.info(
            "github.candidate_enrichment",
            extra={
                "username": user.get("login"),
                "repositories_analyzed": repo_analysis.repositories_analyzed,
                "skills_inferred": skill_result.skills,
                "quality_score": quality.overall,
                "activity_score": activity_analysis.activity_score,
                "elapsed_ms": elapsed_ms,
            },
        )

        return GitHubEnrichment(
            github_quality_score=quality.overall,
            activity_score=activity_analysis.activity_score,
            repositories_analyzed=repo_analysis.repositories_analyzed,
            languages=repo_analysis.languages,
            topics=repo_analysis.topics,
            organizations=org_analysis.organizations,
            skills_inferred=skill_result.skills,
            last_activity=activity_analysis.last_push_at,
            profile_completeness=quality.profile_completeness,
        )
