"""Evidence Timeline -- diffs a candidate's current field values against an
incoming set of fields (from a new capture, CSV row, resume parse, etc.)
and produces one EvidenceEvent per field that's informative, answering
exactly what recruiters need per docs/CANDIDATE_INTELLIGENCE_LIFECYCLE.md:
what changed, when, why, from which source, and at what confidence.

Returns (event, agreement) pairs rather than bare events -- `agreement`
(True/False/None) is what the Confidence Engine needs to decide whether a
change corroborates or conflicts with what's already known; None means
"nothing to compare" (the field was empty before and after, or wasn't
part of this update at all) and produces no event.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.candidate_intelligence.sections import FIELD_TO_SECTION
from app.candidate_repository.models import Candidate, EvidenceEvent

_DIFFABLE_FIELDS = [
    "name",
    "role",
    "headline",
    "current_company",
    "experience",
    "skills",
    "location",
    "summary",
    "education",
    "public_profile_url",
    "resume_link",
]

# List-shaped fields grow monotonically under this project's merge
# strategy (memory_repository.py's upsert() only ever unions/appends,
# never removes) -- so a changed list value is enrichment, not a
# conflict, and always corroborates rather than contests what was there
# before.
_LIST_FIELDS = {"skills", "education"}


def _stringify(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        if len(value) == 0:
            return None
        return ", ".join(
            item if isinstance(item, str) else getattr(item, "degree", None) or str(item)
            for item in value
        )
    if isinstance(value, str):
        return value if value.strip() and value != "Unknown" else None
    if isinstance(value, (int, float)):
        return str(value) if value else None
    return str(value)


def diff_fields(
    existing: Candidate | None,
    incoming_fields: dict,
    source_type: str,
    source_url: str | None,
    confidence: float,
    reason: str,
) -> list[tuple[EvidenceEvent, bool | None]]:
    """Compares `existing` (None for a brand-new candidate) against
    `incoming_fields` (a plain dict, e.g. the normalized import payload)
    field by field and returns one (EvidenceEvent, agreement) pair per
    field that changed or was newly filled. Fields absent from
    `incoming_fields`, or unchanged and already empty, produce nothing.
    """
    results: list[tuple[EvidenceEvent, bool | None]] = []

    for field in _DIFFABLE_FIELDS:
        if field not in incoming_fields:
            continue

        old_raw = getattr(existing, field, None) if existing else None
        new_raw = incoming_fields[field]

        old_str = _stringify(old_raw)
        new_str = _stringify(new_raw)

        if old_str is None and new_str is None:
            continue  # nothing informative happened to this field

        if old_str is None and new_str is not None:
            change_type = "created"
            agreement: bool | None = True  # filling a gap is never a conflict
        elif old_str is not None and new_str is None:
            continue  # we never let a merge blank out a previously-known value
        elif old_str == new_str:
            change_type = "corroborated"
            agreement = True
        elif field in _LIST_FIELDS:
            # List values only grow (union/append), never overwrite --
            # a differing list value means new items were added, which is
            # enrichment, not a disagreement with what was already known.
            change_type = "updated"
            agreement = True
        else:
            change_type = "updated"
            agreement = False  # differing scalar value = a genuine conflict signal

        results.append(
            (
                EvidenceEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    field=field,
                    section=FIELD_TO_SECTION.get(field, "unknown"),
                    old_value=old_str,
                    new_value=new_str,
                    change_type=change_type,
                    source_type=source_type,
                    source_url=source_url,
                    confidence=confidence,
                    reason=reason,
                ),
                agreement,
            )
        )

    return results
