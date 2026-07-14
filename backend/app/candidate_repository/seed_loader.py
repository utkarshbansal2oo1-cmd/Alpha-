"""Shared seed-data loading -- Sprint 30.

Extracted verbatim from InMemoryCandidateRepository._load() (Sprint 3-14)
so a second repository implementation (PostgresCandidateRepository) can
bootstrap from the exact same seed file, with the exact same validation
and initial-lifecycle-bootstrap behavior, without duplicating the logic.
Behavior is byte-for-byte unchanged from before this extraction -- this is
a pure refactor, not a behavior change.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from app.candidate_intelligence.lifecycle import apply_lifecycle
from app.candidate_repository.models import Candidate

DEFAULT_SEED_PATH = Path(__file__).resolve().parent / "data" / "candidates.json"

# Fields the lifecycle engines treat as "the candidate's data" -- same list
# app/candidate_intelligence/evidence_timeline.py diffs against.
LIFECYCLE_FIELDS = [
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


def lifecycle_fields(candidate: Candidate) -> dict:
    return {field: getattr(candidate, field) for field in LIFECYCLE_FIELDS}


class CandidateSeedDataError(Exception):
    """Raised when the seed data file exists but its contents are unusable --
    either not valid JSON, or valid JSON that doesn't conform to the
    Candidate model. Distinct from FileNotFoundError (the file simply isn't
    there): this means the file IS there but is corrupted or was hand-edited
    incorrectly."""


def load_seed_candidates(seed_path: Path | None = None) -> list[Candidate]:
    """Loads, validates, and lifecycle-bootstraps the seed candidate pool.
    Every caller (InMemoryCandidateRepository, PostgresCandidateRepository)
    gets the identical set of Candidate objects, each already carrying an
    initial health score / confidence / evidence entry, exactly as before
    this was extracted into a shared function."""
    seed_path = seed_path or DEFAULT_SEED_PATH

    if not seed_path.exists():
        raise FileNotFoundError(f"Candidate seed data file not found: {seed_path}")

    raw_text = seed_path.read_text(encoding="utf-8")
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise CandidateSeedDataError(
            f"Candidate seed data file is not valid JSON: {seed_path} ({e})"
        ) from e

    try:
        candidates = [Candidate.model_validate(item) for item in raw]
    except ValidationError as e:
        raise CandidateSeedDataError(
            f"Candidate seed data file contains a record that does not match "
            f"the Candidate schema: {seed_path} ({e})"
        ) from e

    for candidate in candidates:
        apply_lifecycle(
            existing=None,
            merged=candidate,
            incoming_fields=lifecycle_fields(candidate),
            source_type="seed_data",
            source_url=None,
            confidence=0.9,
            reason="Initial seed data load",
        )

    return candidates
