"""Tests for the Source Group registry -- Sprint 36."""
from __future__ import annotations

from app.discovery.source_groups import get_source_group_info


def test_github_is_a_known_live_non_fallback_source():
    info = get_source_group_info("github")
    assert info.display_name == "GitHub Matches"
    assert info.is_live is True
    assert info.is_fallback is False


def test_seed_data_display_name_never_contains_the_word_seed():
    """Sprint 36's core product requirement: seed data must never be
    labeled "Seed" to a recruiter, even though Candidate.source stays
    exactly "seed_data" internally."""
    info = get_source_group_info("seed_data")
    assert "seed" not in info.display_name.lower()
    assert info.display_name == "Suggested Profiles"
    assert info.is_fallback is True
    assert info.is_live is False


def test_every_future_connector_stub_has_a_curated_entry():
    for source in ["browser_extension", "csv_import", "resume_import", "hrms"]:
        info = get_source_group_info(source)
        assert info.is_fallback is False
        assert info.is_live is True
        assert info.display_name


def test_unknown_source_gets_a_safe_generic_fallback_not_an_error():
    info = get_source_group_info("some_brand_new_ats")
    assert info.display_name == "Some Brand New Ats"
    assert info.is_fallback is False
    assert info.is_live is True
    assert info.trust_level == "unknown"
    assert info.icon == "database"
