"""Lifecycle orchestrator -- the one function InMemoryCandidateRepository
calls to run every Candidate Intelligence engine after a write. Nothing in
memory_repository.py computes health/confidence/evidence/versions
directly; it all goes through here, so a future repository implementation
(a real database-backed one) only needs to call this same function in its
own upsert()/bootstrap path to get identical behavior.

Order of operations, every time a candidate is created or merged:
  1. Diff old vs new field values -> EvidenceEvents (evidence_timeline.py)
  2. Roll those events up per-section and update section_confidence
     (confidence_engine.py)
  3. Recompute the overall Health Score from the now-updated candidate
     (health_engine.py)
  4. Take a full-state snapshot for Profile Versioning (versioning.py)

This function mutates and returns the SAME candidate object passed in
(the caller -- memory_repository.py -- already owns it); it does not
touch the CandidateRepository interface's search()/all() contract at all.
"""
from __future__ import annotations

from app.candidate_intelligence.confidence_engine import initial_confidence, update_confidence
from app.candidate_intelligence.evidence_timeline import diff_fields
from app.candidate_intelligence.health_engine import compute_health
from app.candidate_intelligence.versioning import build_snapshot
from app.candidate_repository.models import Candidate


def apply_lifecycle(
    existing: Candidate | None,
    merged: Candidate,
    incoming_fields: dict,
    source_type: str,
    source_url: str | None,
    confidence: float,
    reason: str,
) -> Candidate:
    events_with_agreement = diff_fields(existing, incoming_fields, source_type, source_url, confidence, reason)

    sections_touched: dict[str, bool] = {}
    for event, agreement in events_with_agreement:
        merged.evidence_history.append(event)
        if agreement is None:
            continue
        # If multiple fields in the same section disagree in different
        # directions within one update, the section as a whole is treated
        # as having a conflict (conservative: any conflict signal wins).
        sections_touched[event.section] = sections_touched.get(event.section, True) and agreement

    for section, agreement in sections_touched.items():
        current = merged.section_confidence.get(section)
        if current is None:
            merged.section_confidence[section] = initial_confidence(confidence)
        else:
            merged.section_confidence[section] = update_confidence(current, confidence, agreement)

    health = compute_health(merged)
    merged.health_score = health.overall

    snapshot = build_snapshot(merged, version=merged.version, reason=reason)
    merged.version_history.append(snapshot)

    return merged
