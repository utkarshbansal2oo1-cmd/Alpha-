"""Configuration for the GitHub Candidate Intelligence Engine -- Sprint 20D.

Same injectable-dataclass pattern as app.matching.config.MatchingConfig
and app.discovery.query_translation.models.ConnectorTranslationConfig --
every tunable lives here, not buried as a magic number in analyzer code.
"""
from __future__ import annotations

from dataclasses import dataclass

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
    max_search_results: int = 10


_default_config = GitHubIntelligenceConfig()


def get_github_intelligence_config() -> GitHubIntelligenceConfig:
    """FastAPI dependency-injection provider, same pattern as every other
    provider function in this codebase."""
    return _default_config
