"""Cross-query candidate deduplication -- Sprint 20C.

When a connector (GitHub) runs multiple translated searches for one
recruiter request, the same real person frequently turns up more than
once (e.g. matched by both "golang" and "backend golang"). This
deduplicates the resulting CandidateImportRequest objects BEFORE they
reach normalize_import()/upsert() -- an earlier, cheaper pass than (and
complementary to) InMemoryCandidateRepository.find_potential_duplicate(),
which still runs afterward exactly as before and handles merging against
candidates that already exist in the repository.

Per the sprint brief's "GitHub login, email, LinkedIn URL, candidate id"
list: CandidateImportRequest has no email or id field pre-import, so the
practical, available keys are `public_profile_url` (covers a GitHub
profile URL or a LinkedIn URL alike), then `resume_link`, then a
last-resort (name, current_company) pair -- in that priority order.
"""
from __future__ import annotations

from app.candidate_repository.import_schemas import CandidateImportRequest


def _dedup_key(request: CandidateImportRequest) -> str:
    if request.public_profile_url:
        return f"url:{request.public_profile_url.strip().lower()}"
    if request.resume_link:
        return f"resume:{request.resume_link.strip().lower()}"
    return f"name:{request.name.strip().lower()}|{(request.current_company or '').strip().lower()}"


def deduplicate_import_requests(
    requests: list[CandidateImportRequest],
) -> tuple[list[CandidateImportRequest], int]:
    """Returns (deduplicated_requests, duplicate_count) -- the count is
    surfaced for observability (Module "OBSERVABILITY": 'deduplicated
    count')."""
    seen: set[str] = set()
    deduped: list[CandidateImportRequest] = []
    duplicates = 0

    for request in requests:
        key = _dedup_key(request)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(request)

    return deduped, duplicates
