"""Organization Analyzer -- Sprint 20D.

Reads the user profile's own `company` field (free text, self-reported
-- per https://docs.github.com/en/rest/users/users#get-a-user) and,
when available, the user's public GitHub organization memberships (per
https://docs.github.com/en/rest/orgs/members -- GET /users/{username}/orgs,
which only ever returns PUBLIC memberships; private org memberships are
invisible to this API and are honestly reported as absent, never
guessed at).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class OrganizationAnalysis(BaseModel):
    company: str | None = None
    organizations: list[str] = Field(default_factory=list)
    organization_count: int = 0
    verified_organization: bool = False


class OrganizationAnalyzer:
    def __init__(self, config):
        self._config = config

    def analyze(self, user: dict, raw_orgs: list[dict] | None) -> OrganizationAnalysis:
        company = user.get("company")
        orgs = raw_orgs or []
        org_names = [o.get("login") for o in orgs if o.get("login")]

        # GitHub's public-membership API has no per-org "verified" flag
        # for this endpoint; the only real, documented signal available
        # without extra scopes/API calls is whether the org account
        # itself is of type "Organization" (vs "User") -- treated as a
        # conservative proxy for "a real, distinct organization exists,"
        # never asserted as an authenticity/verification guarantee.
        verified = any(o.get("type") == "Organization" for o in orgs)

        return OrganizationAnalysis(
            company=company,
            organizations=org_names,
            organization_count=len(org_names),
            verified_organization=verified,
        )
