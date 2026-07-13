"""Tests for cross-query candidate deduplication -- Sprint 20C."""
from __future__ import annotations

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.discovery.query_translation.dedup import deduplicate_import_requests


def test_dedupes_by_public_profile_url():
    requests = [
        CandidateImportRequest(name="Jane Doe", public_profile_url="https://github.com/janedoe"),
        CandidateImportRequest(name="Jane Doe", public_profile_url="https://github.com/janedoe"),
    ]
    deduped, duplicate_count = deduplicate_import_requests(requests)
    assert len(deduped) == 1
    assert duplicate_count == 1


def test_public_profile_url_match_is_case_insensitive():
    requests = [
        CandidateImportRequest(name="Jane Doe", public_profile_url="https://GitHub.com/JaneDoe"),
        CandidateImportRequest(name="Jane Doe", public_profile_url="https://github.com/janedoe"),
    ]
    deduped, duplicate_count = deduplicate_import_requests(requests)
    assert len(deduped) == 1
    assert duplicate_count == 1


def test_falls_back_to_name_and_company_when_no_url():
    requests = [
        CandidateImportRequest(name="Jane Doe", current_company="Acme"),
        CandidateImportRequest(name="Jane Doe", current_company="Acme"),
        CandidateImportRequest(name="Jane Doe", current_company="Other Co"),
    ]
    deduped, duplicate_count = deduplicate_import_requests(requests)
    assert len(deduped) == 2
    assert duplicate_count == 1


def test_no_duplicates_returns_everything_unchanged():
    requests = [
        CandidateImportRequest(name="A", public_profile_url="https://github.com/a"),
        CandidateImportRequest(name="B", public_profile_url="https://github.com/b"),
    ]
    deduped, duplicate_count = deduplicate_import_requests(requests)
    assert len(deduped) == 2
    assert duplicate_count == 0


def test_empty_list_returns_empty():
    deduped, duplicate_count = deduplicate_import_requests([])
    assert deduped == []
    assert duplicate_count == 0
