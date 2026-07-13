"""Maps GitHub REST API responses onto the existing CandidateImportRequest
shape (app/candidate_repository/import_schemas.py) -- same reasoning as
app/integrations/greenhouse/normalizer.py: reuse normalize_import() and
the rest of the capture pipeline unchanged rather than inventing a second
normalization path.

GitHub's real user profile shape (per
https://docs.github.com/en/rest/users/users#get-a-user):

    {
      "login": "octocat", "name": "The Octocat", "company": "@github",
      "location": "San Francisco", "bio": "...", "html_url": "...",
      "blog": "https://github.blog", ...
    }

Repos (per
https://docs.github.com/en/rest/repos/repos#list-repositories-for-a-user):

    [{"name": "...", "language": "Python", "fork": false, ...}, ...]

Language inference/skills extraction: GitHub's user search API has no
"skills" field -- `language` on each of a user's repos is the one real,
documented signal available, so skills are inferred from the distinct,
non-null languages across a user's own (non-fork) repositories, ranked by
how many repos use each language. This is a heuristic, exactly like
Greenhouse's `tags` field, and is documented as such rather than treated
as an authoritative skills list.
"""
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from app.candidate_repository.import_schemas import CandidateImportRequest

if TYPE_CHECKING:
    from app.integrations.github.intelligence.enrichment import GitHubEnrichment


def infer_languages(repos: list[dict]) -> list[str]:
    """Distinct languages across a user's own repositories (forks
    excluded -- a fork's language reflects the original author's code,
    not necessarily a skill of the forking user), most-used first."""
    counts = Counter(
        repo["language"] for repo in repos if repo.get("language") and not repo.get("fork", False)
    )
    return [language for language, _ in counts.most_common()]


def normalize_github_candidate(
    user: dict,
    repos: list[dict],
    enrichment: "GitHubEnrichment | None" = None,
) -> CandidateImportRequest:
    """Converts one GitHub user profile + their repo list into a
    CandidateImportRequest, ready for normalize_import() ->
    CandidateRepository.upsert() -- the exact same downstream path every
    other capture path (browser extension, Greenhouse) already goes
    through.

    Sprint 20D addition: an optional `enrichment` (from
    app.integrations.github.intelligence.enrichment.GitHubEnrichmentEngine)
    populates the additive github_* fields on CandidateImportRequest.
    Omitting it (every pre-Sprint-20D caller/test) leaves those fields at
    their default None/empty values -- this parameter is purely additive.
    """

    name = user.get("name") or user.get("login") or "Unknown Candidate"
    skills = infer_languages(repos)

    enrichment_fields = {}
    if enrichment is not None:
        enrichment_fields = {
            "github_quality_score": enrichment.github_quality_score,
            "github_activity_score": enrichment.activity_score,
            "github_repositories_analyzed": enrichment.repositories_analyzed,
            "github_languages": enrichment.languages,
            "github_topics": enrichment.topics,
            "github_organizations": enrichment.organizations,
            "github_skills_inferred": enrichment.skills_inferred,
            "github_last_activity": enrichment.last_activity,
            "github_profile_completeness": enrichment.profile_completeness,
        }

    return CandidateImportRequest(
        name=name,
        headline=user.get("bio"),
        current_company=user.get("company"),
        skills=skills,
        location=user.get("location"),
        summary=user.get("bio"),
        public_profile_url=user.get("html_url"),
        source_type="github",
        source_url=user.get("html_url"),
        **enrichment_fields,
    )
