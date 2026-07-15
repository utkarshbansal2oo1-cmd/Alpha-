"""Configuration for the GitHub Candidate Intelligence Engine -- Sprint 20D.

Same injectable-dataclass pattern as app.matching.config.MatchingConfig
and app.discovery.query_translation.models.ConnectorTranslationConfig --
every tunable lives here, not buried as a magic number in analyzer code.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings

# GitHub's own hard cap on README size is much larger than this; this is
# a deliberately conservative "safe limit" so a single oversized README
# can't make one candidate's enrichment noticeably slower than the rest
# of a discovery pass -- per the sprint brief's "Maximum README size:
# safe limit" requirement.
DEFAULT_MAX_README_BYTES = 20_000


@dataclass
class GitHubIntelligenceConfig:
    max_repositories: int = 20
    max_readme_bytes: int = DEFAULT_MAX_README_BYTES
    enable_repository_analysis: bool = True
    enable_activity_scoring: bool = True
    enable_organization_analysis: bool = True
    enable_skill_extraction: bool = True

    # Sprint 20H: was a hardcoded module constant (`_DISCOVERY_USER_LIMIT`) in
    # github_connector.py. GitHub's Search Users API can return thousands of
    # matches (live-confirmed: total_count 1729 for "golang") -- how many of
    # those results the connector actually fetches/inspects is a
    # connector-imposed choice, not a GitHub API limitation, so it belongs
    # here as a tunable rather than a magic number. Default of 10 preserves
    # the exact behavior every existing test and live run assumed.
    #
    # Sprint 34: superseded as the knob that drives discovery volume --
    # github_connector.py's discover() no longer reads this field at all.
    # Its two jobs (how many results per GitHub search page, and how many
    # total raw candidates to collect) are now separate, dedicated fields
    # below (`search_page_size`, `max_raw_candidates`), each independently
    # configurable, because "results per page" and "total candidates
    # collected across many pages" are genuinely different knobs once
    # pagination exists. Left defined here (default unchanged) purely so
    # any existing code constructing `GitHubIntelligenceConfig(max_search_results=N)`
    # still works -- it's just inert now.
    max_search_results: int = 10

    # Sprint 34: multi-page GitHub Search Users discovery. Sourced from
    # app/config.py's GITHUB_SEARCH_PAGE_SIZE / GITHUB_MAX_SEARCH_PAGES /
    # GITHUB_MAX_RAW_CANDIDATES by get_github_intelligence_config() below
    # -- kept as plain dataclass fields (rather than reading `settings`
    # directly in github_connector.py) so tests can override them per
    # case, same pattern as every other field on this dataclass.
    search_page_size: int = 100
    max_search_pages: int = 5
    max_raw_candidates: int = 500

    # Sprint 35: Phase 6 (auto-expand GitHub discovery). Once discover()
    # has accumulated this many RELEVANT (post-filter, not just raw)
    # candidates, it stops requesting further pages -- see
    # github_connector.py's discover() docstring for the full page-by-page
    # fetch+filter interleaving this enables.
    target_relevant_candidates: int = 20


_default_config = GitHubIntelligenceConfig(
    search_page_size=settings.GITHUB_SEARCH_PAGE_SIZE,
    max_search_pages=settings.GITHUB_MAX_SEARCH_PAGES,
    max_raw_candidates=settings.GITHUB_MAX_RAW_CANDIDATES,
    target_relevant_candidates=settings.GITHUB_TARGET_RELEVANT_CANDIDATES,
)


def get_github_intelligence_config() -> GitHubIntelligenceConfig:
    """FastAPI dependency-injection provider, same pattern as every other
    provider function in this codebase."""
    return _default_config
