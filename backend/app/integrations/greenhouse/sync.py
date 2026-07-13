"""Pull sync (Greenhouse -> AlphaSource) and push-back (AlphaSource ->
Greenhouse). Both reuse the existing, unmodified capture pipeline:

    Greenhouse candidate JSON
      -> normalize_greenhouse_candidate()      (normalizer.py)
      -> CandidateImportRequest
      -> normalize_import()                    (candidate_repository/normalizer.py, Sprint 12)
      -> Candidate
      -> repository.find_potential_duplicate() + repository.upsert()  (Sprint 12/14)

This is the same path POST /candidate/import already uses for browser
-extension captures -- the Greenhouse connector is just a second way of
producing a CandidateImportRequest, not a second write path into the
repository. Every Greenhouse-sourced candidate gets the same dedup,
health scoring, confidence tracking, and evidence timeline as a browser
capture, for free.
"""
from __future__ import annotations

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.models import Candidate
from app.candidate_repository.normalizer import normalize_import
from app.integrations.greenhouse.client import GreenhouseAPIError, GreenhouseClient
from app.integrations.greenhouse.models import SyncRun
from app.integrations.greenhouse.normalizer import normalize_greenhouse_candidate
from datetime import datetime, timezone


def pull_sync(client: GreenhouseClient, repository: CandidateRepository) -> SyncRun:
    """Pulls every candidate from Greenhouse and upserts each into the
    AlphaSource candidate pool. A single malformed record or a single
    Greenhouse API error on one candidate is recorded in `errors` and
    skipped -- it does not abort the rest of the sync, since a partial
    successful sync is strictly more useful to a recruiter than none.
    """
    run = SyncRun()

    try:
        raw_candidates = client.list_candidates()
    except GreenhouseAPIError as e:
        run.status = "failed"
        run.errors.append(f"Failed to list candidates from Greenhouse: {e}")
        run.finished_at = datetime.now(timezone.utc)
        return run

    for raw in raw_candidates:
        run.candidates_pulled += 1
        try:
            import_request = normalize_greenhouse_candidate(raw)
            candidate = normalize_import(import_request)

            existing = repository.find_potential_duplicate(candidate)
            repository.upsert(candidate)

            if existing is None:
                run.candidates_created += 1
            else:
                run.candidates_merged += 1
        except Exception as e:  # noqa: BLE001 -- one bad record must not abort the sync
            candidate_id = raw.get("id", "unknown")
            run.errors.append(f"Candidate {candidate_id}: {e}")

    run.status = "completed" if not run.errors else "completed_with_errors"
    run.finished_at = datetime.now(timezone.utc)
    return run


def push_candidate(client: GreenhouseClient, candidate: Candidate, note: str | None = None) -> dict:
    """Pushes one AlphaSource candidate into Greenhouse as a new candidate
    record, optionally attaching a note (e.g. the recruiter's shortlist
    reasoning / "why matched" explanation) via a follow-up API call.
    Returns the created Greenhouse candidate record (including its
    Greenhouse-assigned id).
    """
    name_parts = candidate.name.strip().split(" ", 1)
    first_name = name_parts[0] if name_parts else candidate.name
    last_name = name_parts[1] if len(name_parts) > 1 else "(unknown)"

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "company": candidate.current_company or None,
        "title": candidate.role or None,
        "social_media_addresses": (
            [{"value": candidate.public_profile_url}] if candidate.public_profile_url else []
        ),
        "educations": [
            {"school_name": e.institution, "degree": e.degree}
            for e in candidate.education
            if e.institution or e.degree
        ],
        "tags": candidate.skills,
    }
    # Greenhouse's create-candidate endpoint rejects explicit nulls for
    # some fields rather than treating them as "omit" -- strip them here
    # instead of asking every caller to remember to.
    payload = {k: v for k, v in payload.items() if v not in (None, [], "")}

    created = client.create_candidate(payload)

    if note:
        client.add_candidate_note(created["id"], note)

    return created
