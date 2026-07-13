"""Maps a Greenhouse Harvest API candidate record onto the existing
CandidateImportRequest shape (app/candidate_repository/import_schemas.py)
-- the same permissive intermediate shape the browser extension's
extraction layer already produces, so this connector reuses
normalize_import() and the rest of the capture pipeline unchanged rather
than inventing a second normalization path.

Greenhouse's real candidate JSON shape (per
https://developers.greenhouse.io/harvest.html#get-retrieve-candidates):

    {
      "id": 123,
      "first_name": "Jane",
      "last_name": "Doe",
      "company": "Acme Corp",       # current employer, free text
      "title": "Senior Engineer",   # current title, free text
      "phone_numbers": [{"value": "...", "type": "mobile"}],
      "email_addresses": [{"value": "...", "type": "personal"}],
      "addresses": [{"value": "San Francisco, CA", "type": "home"}],
      "social_media_addresses": [{"value": "https://linkedin.com/in/..."}],
      "educations": [{"school_name": "...", "degree": "...", ...}],
      "employments": [{"company_name": "...", "title": "...", ...}],
      "tags": ["python", "backend"],
      ...
    }

`tags` (a real Greenhouse field, typically used for recruiter-applied
labels) is read as a best-effort skills signal -- most Greenhouse
accounts don't populate it with technical skills specifically, so this is
documented as a heuristic, not treated as authoritative.
"""
from __future__ import annotations

from app.candidate_repository.import_schemas import CandidateImportRequest, ImportEducationEntry


def _first_value(entries: list[dict] | None) -> str | None:
    if not entries:
        return None
    return entries[0].get("value")


def normalize_greenhouse_candidate(raw: dict) -> CandidateImportRequest:
    """Converts one Greenhouse candidate JSON record into a
    CandidateImportRequest, ready for normalize_import() ->
    CandidateRepository.upsert() -- the exact same downstream path the
    browser extension's captures already go through."""

    name_parts = [raw.get("first_name"), raw.get("last_name")]
    name = " ".join(p for p in name_parts if p) or "Unknown Candidate"

    education = [
        ImportEducationEntry(
            degree=edu.get("degree"),
            institution=edu.get("school_name"),
            year=str(edu.get("end_date")) if edu.get("end_date") else None,
        )
        for edu in raw.get("educations", [])
    ]

    return CandidateImportRequest(
        name=name,
        role=raw.get("title"),
        current_company=raw.get("company"),
        skills=[t for t in raw.get("tags", []) if isinstance(t, str)],
        location=_first_value(raw.get("addresses")),
        education=education,
        public_profile_url=_first_value(raw.get("social_media_addresses")),
        source_type="greenhouse_ats",
        source_url=f"https://app.greenhouse.io/people/{raw['id']}" if raw.get("id") else None,
    )
