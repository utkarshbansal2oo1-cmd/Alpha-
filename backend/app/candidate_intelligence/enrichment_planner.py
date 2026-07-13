"""Enrichment Planner -- turns a Health Score's missing fields into a
prioritized, actionable EnrichmentPlan. Priority weighting reuses the same
SECTION_WEIGHTS the Health Engine scores against, so "the field that would
move the health score the most" and "the field the planner recommends
first" are always the same answer -- no separate priority scheme to keep
in sync.
"""
from __future__ import annotations

from app.candidate_intelligence.enrichment_registry import (
    EnrichmentSourceRegistry,
    default_registry,
)
from app.candidate_intelligence.sections import FIELD_TO_SECTION, SECTION_WEIGHTS
from app.candidate_repository.models import Candidate, EnrichmentPlan, EnrichmentPlanItem, HealthScore

_FIELD_LABELS = {
    "name": "full name",
    "location": "location",
    "role": "current role/title",
    "current_company": "current employer",
    "experience": "years of experience",
    "skills": "skills",
    "education": "education history",
    "public_profile_url": "a public profile link",
    "resume_link": "a resume link",
    "summary": "a profile summary",
}


def plan_enrichment(
    candidate: Candidate,
    health: HealthScore,
    registry: EnrichmentSourceRegistry = default_registry,
) -> EnrichmentPlan:
    """Builds an EnrichmentPlan for one candidate from its already-computed
    HealthScore. Missing fields are weighted by their section's
    contribution to the overall score, split evenly across however many
    fields are missing in that section -- a section with only one missing
    field gets a bigger priority bump per-field than a section missing
    three, since filling the single gap closes that whole section.
    """
    missing_by_section: dict[str, list[str]] = {}
    for field in health.missing_fields:
        section = FIELD_TO_SECTION.get(field, "unknown")
        missing_by_section.setdefault(section, []).append(field)

    items: list[EnrichmentPlanItem] = []
    max_weight = max(SECTION_WEIGHTS.values()) if SECTION_WEIGHTS else 1

    for section, fields in missing_by_section.items():
        section_weight = SECTION_WEIGHTS.get(section, 0)
        per_field_priority = (section_weight / max_weight) / len(fields)

        for field in fields:
            sources = registry.capable_sources_for(field)
            label = _FIELD_LABELS.get(field, field)
            reason = (
                f"Missing {label}; would improve the '{section}' section"
                + (f" -- known enrichable via {', '.join(sources)}" if sources else " -- no registered source can supply this yet")
            )
            items.append(
                EnrichmentPlanItem(
                    field=field,
                    section=section,
                    priority=round(min(1.0, per_field_priority), 3),
                    candidate_source_types=sources,
                    reason=reason,
                )
            )

    items.sort(key=lambda item: item.priority, reverse=True)

    return EnrichmentPlan(candidate_id=candidate.id, items=items)
