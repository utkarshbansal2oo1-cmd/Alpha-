"""Profile Versioning -- takes a full-state snapshot of a candidate's
current field values. Snapshots are append-only (candidate.version_history
is never rewritten) and self-contained: a CandidateSnapshot stores plain
field values, not a nested Candidate, so it never recursively carries its
own version_history/evidence_history (which would grow unboundedly).

At real scale (docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md's scaling
section), this snapshot-per-change approach is the thing that would move
to a separate, indexed `candidate_versions` table rather than an inline
list -- this function's signature (candidate + version + reason ->
snapshot) is unchanged either way, only where the result gets stored.
"""
from __future__ import annotations

from app.candidate_repository.models import Candidate, CandidateSnapshot

# Fields captured in a snapshot -- everything that represents "the
# candidate's data", explicitly excluding the lifecycle bookkeeping fields
# themselves (version, version_history, evidence_history, section_confidence,
# health_score) since a snapshot is a snapshot of the DATA at a point in
# time, not of the lifecycle machinery that produced it.
_SNAPSHOT_FIELDS = [
    "name",
    "role",
    "experience",
    "skills",
    "location",
    "current_company",
    "source",
    "headline",
    "summary",
    "education",
    "public_profile_url",
    "resume_link",
]


def build_snapshot(candidate: Candidate, version: int, reason: str) -> CandidateSnapshot:
    fields = {}
    for field_name in _SNAPSHOT_FIELDS:
        value = getattr(candidate, field_name)
        if isinstance(value, list):
            fields[field_name] = [
                item if isinstance(item, str) else item.model_dump() for item in value
            ]
        else:
            fields[field_name] = value

    return CandidateSnapshot(version=version, reason=reason, fields=fields)
