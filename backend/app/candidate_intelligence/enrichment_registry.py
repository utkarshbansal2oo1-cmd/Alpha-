"""Pluggable enrichment-source registry -- deliberately the same shape as
Sprint 13's Adapter SDK registry (adapter-sdk/core/registry.js), just on
the backend side: a source type declares which candidate fields it is
capable of supplying, and the Enrichment Planner (enrichment_planner.py)
only ever asks this registry "who can help with field X" -- it never
special-cases a source type by name.

Adding support for a brand-new connector later means one call to
register_source() (or a new module that calls it on import) -- nothing in
enrichment_planner.py, the /candidate/*/enrichment-plan endpoint, or any
other file in this package needs to change.
"""
from __future__ import annotations


class EnrichmentSourceRegistry:
    def __init__(self):
        self._sources: dict[str, set[str]] = {}

    def register_source(self, source_type: str, fields: list[str]) -> None:
        self._sources.setdefault(source_type, set()).update(fields)

    def capable_sources_for(self, field: str) -> list[str]:
        return sorted(
            source_type for source_type, fields in self._sources.items() if field in fields
        )

    def all_sources(self) -> dict[str, list[str]]:
        return {source_type: sorted(fields) for source_type, fields in self._sources.items()}


# Module-level singleton, pre-populated with the source types this project
# already has extraction logic for (the Sprint 13 Adapter SDK's adapters).
# A future connector (a real LinkedIn/Naukri/ATS integration, once
# authorized) registers itself the same way -- see
# docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md's "adding a new enrichment
# source" walkthrough.
default_registry = EnrichmentSourceRegistry()

default_registry.register_source(
    "browser_extension",
    ["name", "role", "headline", "current_company", "skills", "location", "summary", "education", "public_profile_url", "resume_link"],
)
default_registry.register_source(
    "csv_import",
    ["name", "role", "current_company", "skills", "location", "summary", "public_profile_url", "resume_link", "experience"],
)
default_registry.register_source(
    "resume_import",
    ["name", "skills", "education", "summary", "experience"],
)
default_registry.register_source(
    "career_page_listing",
    ["name", "role", "headline", "public_profile_url"],
)
default_registry.register_source(
    # Sprint 15: Greenhouse ATS connector (app/integrations/greenhouse/).
    # Registered the same way any adapter is -- the Enrichment Planner
    # needed zero code changes to know this source can help fill these
    # fields.
    "greenhouse_ats",
    ["name", "role", "current_company", "skills", "location", "education", "public_profile_url"],
)
