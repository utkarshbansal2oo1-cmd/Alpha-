"""Repository Analyzer -- Sprint 20D.

Reads GitHub's own documented repo-list shape (per
https://docs.github.com/en/rest/repos/repos#list-repositories-for-a-user)
and aggregates the fields the sprint brief asks for: languages, topics,
description, fork status, stars, forks, watchers, license, default
branch, last update. Forks are counted separately from a user's own
repos throughout -- a fork's stars/language/topics reflect the original
project, not necessarily this user's own work, same reasoning already
established in app/integrations/github/normalizer.py's infer_languages().
"""
from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field


class RepositorySummary(BaseModel):
    """One repo's extracted facts -- kept small and flat rather than
    passing GitHub's full raw repo JSON around."""

    name: str
    description: str | None = None
    language: str | None = None
    fork: bool = False
    stargazers_count: int = 0
    forks_count: int = 0
    watchers_count: int = 0
    license_name: str | None = None
    default_branch: str | None = None
    topics: list[str] = Field(default_factory=list)
    pushed_at: str | None = None
    updated_at: str | None = None


class RepositoryAnalysis(BaseModel):
    repositories_analyzed: int = 0
    own_repositories: int = 0
    forked_repositories: int = 0
    languages: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    licenses: list[str] = Field(default_factory=list)
    total_stars: int = 0
    total_forks: int = 0
    total_watchers: int = 0
    top_repositories: list[RepositorySummary] = Field(default_factory=list)


def _to_summary(raw_repo: dict) -> RepositorySummary:
    license_info = raw_repo.get("license") or {}
    return RepositorySummary(
        name=raw_repo.get("name", ""),
        description=raw_repo.get("description"),
        language=raw_repo.get("language"),
        fork=bool(raw_repo.get("fork", False)),
        stargazers_count=raw_repo.get("stargazers_count", 0) or 0,
        forks_count=raw_repo.get("forks_count", 0) or 0,
        watchers_count=raw_repo.get("watchers_count", 0) or 0,
        license_name=license_info.get("name") if isinstance(license_info, dict) else None,
        default_branch=raw_repo.get("default_branch"),
        topics=list(raw_repo.get("topics") or []),
        pushed_at=raw_repo.get("pushed_at"),
        updated_at=raw_repo.get("updated_at"),
    )


class RepositoryAnalyzer:
    def __init__(self, config):
        self._config = config

    def analyze(self, raw_repos: list[dict]) -> RepositoryAnalysis:
        capped = raw_repos[: self._config.max_repositories]
        summaries = [_to_summary(r) for r in capped]

        own = [s for s in summaries if not s.fork]
        forked = [s for s in summaries if s.fork]

        language_counts = Counter(s.language for s in own if s.language)
        languages = [lang for lang, _ in language_counts.most_common()]

        topic_counts: Counter[str] = Counter()
        for s in summaries:
            topic_counts.update(s.topics)
        topics = [topic for topic, _ in topic_counts.most_common()]

        licenses = sorted({s.license_name for s in summaries if s.license_name})

        top_repositories = sorted(summaries, key=lambda s: s.stargazers_count, reverse=True)[:5]

        return RepositoryAnalysis(
            repositories_analyzed=len(summaries),
            own_repositories=len(own),
            forked_repositories=len(forked),
            languages=languages,
            topics=topics,
            licenses=licenses,
            total_stars=sum(s.stargazers_count for s in summaries),
            total_forks=sum(s.forks_count for s in summaries),
            total_watchers=sum(s.watchers_count for s in summaries),
            top_repositories=top_repositories,
        )
