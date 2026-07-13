"""Tests for app.knowledge.loader: loading, validation, duplicate IDs,
broken references, version loading. Uses the real seed taxonomies (the
ones shipped in taxonomies/) for the "happy path", and small fixture
files under tests/fixtures/ for each failure mode.
"""
from pathlib import Path

import pytest

from app.knowledge.exceptions import TaxonomyValidationError
from app.knowledge.loader import load_all_taxonomies

FIXTURES = Path(__file__).parent / "fixtures"


def test_loads_real_seed_taxonomies_without_error():
    taxonomies = load_all_taxonomies()
    assert len(taxonomies) == 4
    types = {t.taxonomy_type.value for t in taxonomies}
    assert types == {"role", "skill", "industry", "company_category"}


def test_loads_minimal_valid_fixture():
    taxonomies = load_all_taxonomies(
        taxonomies_dir=FIXTURES / "minimal_valid", filenames=["roles.json"]
    )
    assert len(taxonomies) == 1
    role_taxonomy = taxonomies[0]
    assert role_taxonomy.version == "1.0.0"
    assert len(role_taxonomy.entries) == 2


def test_duplicate_ids_across_files_raise():
    with pytest.raises(TaxonomyValidationError) as exc_info:
        load_all_taxonomies(
            taxonomies_dir=FIXTURES / "duplicate_ids",
            filenames=["roles.json", "skills.json"],
        )
    assert "Duplicate id" in str(exc_info.value.result.issues[0].message)


def test_broken_reference_raises():
    with pytest.raises(TaxonomyValidationError) as exc_info:
        load_all_taxonomies(
            taxonomies_dir=FIXTURES / "broken_reference", filenames=["roles.json"]
        )
    messages = [i.message for i in exc_info.value.result.issues]
    assert any("does not resolve" in m for m in messages)


def test_schema_violation_raises():
    with pytest.raises(TaxonomyValidationError) as exc_info:
        load_all_taxonomies(
            taxonomies_dir=FIXTURES / "schema_violation", filenames=["skills.json"]
        )
    messages = [i.message for i in exc_info.value.result.issues]
    assert any("JSON Schema violation" in m for m in messages)


def test_missing_file_raises():
    with pytest.raises(TaxonomyValidationError) as exc_info:
        load_all_taxonomies(
            taxonomies_dir=FIXTURES / "minimal_valid", filenames=["does_not_exist.json"]
        )
    assert "not found" in exc_info.value.result.issues[0].message


def test_invalid_json_raises(tmp_path):
    bad_file = tmp_path / "roles.json"
    bad_file.write_text("{ not valid json ", encoding="utf-8")
    with pytest.raises(TaxonomyValidationError) as exc_info:
        load_all_taxonomies(taxonomies_dir=tmp_path, filenames=["roles.json"])
    assert "invalid JSON" in exc_info.value.result.issues[0].message
