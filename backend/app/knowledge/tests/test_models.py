"""Tests for app.knowledge.models: field-level validation on the Pydantic
models themselves (independent of file loading).
"""
from datetime import date

import pytest
from pydantic import ValidationError

from app.knowledge.models import Expansion, Taxonomy, TaxonomyEntry, TaxonomyType


def test_expansion_weight_must_be_between_0_and_1():
    with pytest.raises(ValidationError):
        Expansion(target_id="x", weight=1.5, notes="")
    with pytest.raises(ValidationError):
        Expansion(target_id="x", weight=-0.1, notes="")
    Expansion(target_id="x", weight=0.0, notes="")
    Expansion(target_id="x", weight=1.0, notes="")


def test_expansion_target_id_must_not_be_blank():
    with pytest.raises(ValidationError):
        Expansion(target_id="", weight=0.5, notes="")
    with pytest.raises(ValidationError):
        Expansion(target_id="   ", weight=0.5, notes="")


def test_entry_id_and_canonical_must_not_be_blank():
    with pytest.raises(ValidationError):
        TaxonomyEntry(
            id="",
            canonical="Something",
            created_at=date(2026, 7, 1),
            updated_at=date(2026, 7, 1),
        )
    with pytest.raises(ValidationError):
        TaxonomyEntry(
            id="x.y",
            canonical="",
            created_at=date(2026, 7, 1),
            updated_at=date(2026, 7, 1),
        )


def test_entry_defaults():
    entry = TaxonomyEntry(
        id="x.y", canonical="X", created_at=date(2026, 7, 1), updated_at=date(2026, 7, 1)
    )
    assert entry.aliases == []
    assert entry.expansions == []
    assert entry.status.value == "active"


def test_taxonomy_version_must_not_be_blank():
    with pytest.raises(ValidationError):
        Taxonomy(taxonomy_type=TaxonomyType.SKILL, version="", updated_at=date(2026, 7, 1), entries=[])


def test_taxonomy_type_must_be_known_enum_value():
    with pytest.raises(ValidationError):
        Taxonomy(
            taxonomy_type="not_a_real_type",
            version="1.0.0",
            updated_at=date(2026, 7, 1),
            entries=[],
        )
