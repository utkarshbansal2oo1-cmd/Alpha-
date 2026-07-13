"""Candidate Health Engine -- computes a per-section confidence/
completeness breakdown and one overall 0-100 score for a Candidate.

Deliberately a pure function of (candidate, section_confidence): it never
mutates the candidate and never talks to the repository, the backend, or
any connector. That keeps it trivially unit-testable and, per
docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md's scaling section, safe to run as
a batch/async job over millions of records later without touching this
file.
"""
from __future__ import annotations

from app.candidate_intelligence.sections import (
    SECTION_FIELDS,
    SECTION_WEIGHTS,
    field_present,
)
from app.candidate_repository.models import Candidate, HealthScore, SectionScore

# A section with no recorded confidence yet (never touched by the
# Confidence Engine) gets this neutral baseline rather than 0 -- a field
# being present at all is itself weak evidence it's roughly right, per the
# same "some signal beats no signal" reasoning as
# docs/EVIDENCE_GRAPH_ARCHITECTURE.md's confidence-by-source-type table.
DEFAULT_SECTION_CONFIDENCE = 0.5


def compute_health(candidate: Candidate) -> HealthScore:
    """Computes the Health Score for one candidate, using whatever
    section_confidence the Confidence Engine has already recorded on it
    (falling back to DEFAULT_SECTION_CONFIDENCE for a section with no
    recorded confidence yet, e.g. a freshly-created candidate that hasn't
    been through the lifecycle orchestrator).
    """
    sections: list[SectionScore] = []
    missing_fields: list[str] = []
    weighted_total = 0.0

    for section, fields in SECTION_FIELDS.items():
        present_fields = [f for f in fields if field_present(candidate, f)]
        missing = [f for f in fields if f not in present_fields]
        completeness = len(present_fields) / len(fields) if fields else 1.0
        confidence = candidate.section_confidence.get(section, DEFAULT_SECTION_CONFIDENCE)

        sections.append(
            SectionScore(
                section=section,
                confidence=confidence,
                complete=(len(missing) == 0),
                missing_fields=missing,
                evidence_count=sum(
                    1 for e in candidate.evidence_history if e.section == section
                ),
            )
        )
        missing_fields.extend(missing)

        weight = SECTION_WEIGHTS[section]
        weighted_total += weight * completeness * confidence

    return HealthScore(
        overall=round(min(100.0, max(0.0, weighted_total)), 1),
        sections=sections,
        missing_fields=missing_fields,
    )
