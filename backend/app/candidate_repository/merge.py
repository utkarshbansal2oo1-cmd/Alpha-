"""Pure search/dedup/merge functions -- Sprint 30.

Extracted verbatim from InMemoryCandidateRepository (Sprint 3/12/14) so
PostgresCandidateRepository can share the exact same retrieval-filter,
duplicate-detection, and merge-on-capture behavior without duplicating the
logic (and risking the two implementations silently diverging). Every
function here operates on a plain `list[Candidate]` the caller supplies --
these functions know nothing about where that list came from (Python list
attribute vs. a database query), which is exactly what makes them shareable
between repository implementations.

This is a pure refactor of existing, already-tested behavior -- see
app/candidate_repository/tests.py's ~30 tests, none of which changed as
part of this extraction.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.candidate_intelligence.lifecycle import apply_lifecycle
from app.candidate_repository.models import Candidate
from app.candidate_repository.seed_loader import lifecycle_fields
from app.search_planner.models import SearchPlan


def search_in(candidates: list[Candidate], plan: SearchPlan) -> list[Candidate]:
    """Retrieval-level keyword/role filter -- see
    CandidateRepository.search()'s own docstring for the exact contract
    (exact role/skill membership, not ranking or scoring)."""
    if not plan.search_terms:
        return list(candidates)

    normalized_terms = {term.strip().lower() for term in plan.search_terms if term.strip()}

    results: list[Candidate] = []
    for candidate in candidates:
        candidate_role = candidate.role.strip().lower()
        candidate_skills = {skill.strip().lower() for skill in candidate.skills}

        role_matches = candidate_role in normalized_terms
        skill_matches = bool(candidate_skills & normalized_terms)

        if role_matches or skill_matches:
            results.append(candidate)

    return results


def find_potential_duplicate_in(candidates: list[Candidate], candidate: Candidate) -> Candidate | None:
    """Conservative, signal-based duplicate detection -- see
    docs/BROWSER_EXTENSION_ARCHITECTURE.md Phase 6. Unchanged from
    InMemoryCandidateRepository.find_potential_duplicate()'s original
    docstring/behavior."""
    if candidate.public_profile_url:
        for existing in candidates:
            if existing.public_profile_url == candidate.public_profile_url:
                return existing
        return None

    normalized_name = candidate.name.strip().lower()
    normalized_company = candidate.current_company.strip().lower()
    for existing in candidates:
        if (
            existing.name.strip().lower() == normalized_name
            and existing.current_company.strip().lower() == normalized_company
            and normalized_name
            and normalized_company
        ):
            return existing

    return None


@dataclass
class UpsertResult:
    """What compute_upsert() decided, and what the caller must do about
    storage. `previous` is the exact pre-merge record that was replaced
    (None if `candidate` is a brand-new record) -- callers use this to
    decide append-vs-replace-by-identity (in-memory list) or just always
    upsert-by-id (a real database, where this distinction doesn't matter)."""

    candidate: Candidate
    previous: Candidate | None


def compute_upsert(candidates: list[Candidate], candidate: Candidate) -> UpsertResult:
    """Computes the resulting Candidate for an upsert -- new record or
    merged-with-existing -- exactly per
    InMemoryCandidateRepository.upsert()'s original merge-strategy
    docstring (skills unioned, scalar fields fill-if-empty, capture_sources
    always appended, version incremented on merge). Does NOT persist
    anything -- the caller (in-memory list mutation, or a database
    INSERT/UPDATE) owns storage.
    """
    existing = find_potential_duplicate_in(candidates, candidate)

    incoming_source_type = candidate.capture_sources[-1].source_type if candidate.capture_sources else candidate.source
    incoming_source_url = candidate.capture_sources[-1].source_url if candidate.capture_sources else None
    incoming_confidence = candidate.capture_sources[-1].confidence if candidate.capture_sources else 0.7

    if existing is None:
        new_candidate = candidate.model_copy(update={"id": candidate.id or str(uuid.uuid4())})
        apply_lifecycle(
            existing=None,
            merged=new_candidate,
            incoming_fields=lifecycle_fields(candidate),
            source_type=incoming_source_type,
            source_url=incoming_source_url,
            confidence=incoming_confidence,
            reason="New candidate created via capture",
        )
        return UpsertResult(candidate=new_candidate, previous=None)

    merged_skills = list(dict.fromkeys([*existing.skills, *candidate.skills]))

    merged_education = list(existing.education)
    existing_education_keys = {(e.degree, e.institution) for e in existing.education}
    for entry in candidate.education:
        if (entry.degree, entry.institution) not in existing_education_keys:
            merged_education.append(entry)

    merged = existing.model_copy(
        update={
            "role": existing.role or candidate.role,
            "experience": existing.experience or candidate.experience,
            "skills": merged_skills,
            "location": existing.location or candidate.location,
            "current_company": existing.current_company or candidate.current_company,
            "headline": existing.headline or candidate.headline,
            "summary": existing.summary or candidate.summary,
            "education": merged_education,
            "resume_link": existing.resume_link or candidate.resume_link,
            "capture_sources": [*existing.capture_sources, *candidate.capture_sources],
            "version": existing.version + 1,
        }
    )

    apply_lifecycle(
        existing=existing,
        merged=merged,
        incoming_fields=lifecycle_fields(candidate),
        source_type=incoming_source_type,
        source_url=incoming_source_url,
        confidence=incoming_confidence,
        reason="Merged new capture into existing candidate",
    )

    return UpsertResult(candidate=merged, previous=existing)
