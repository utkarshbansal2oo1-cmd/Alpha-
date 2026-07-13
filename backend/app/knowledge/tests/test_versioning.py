"""Tests for app.knowledge.versioning: version snapshotting and changelog
diffing between two versions of the same taxonomy.
"""
from datetime import date

import pytest

from app.knowledge.models import Expansion, Taxonomy, TaxonomyEntry, TaxonomyType
from app.knowledge.versioning import diff_taxonomies, snapshot_versions


def _entry(id_, canonical, aliases=None, expansions=None, status="active"):
    return TaxonomyEntry(
        id=id_,
        canonical=canonical,
        aliases=aliases or [],
        expansions=expansions or [],
        status=status,
        created_at=date(2026, 7, 1),
        updated_at=date(2026, 7, 1),
    )


def _taxonomy(version, entries):
    return Taxonomy(
        taxonomy_type=TaxonomyType.SKILL,
        version=version,
        updated_at=date(2026, 7, 1),
        entries=entries,
    )


def test_snapshot_versions():
    role_tax = Taxonomy(
        taxonomy_type=TaxonomyType.ROLE, version="1.0.0", updated_at=date(2026, 7, 1), entries=[]
    )
    skill_tax = Taxonomy(
        taxonomy_type=TaxonomyType.SKILL, version="2.0.0", updated_at=date(2026, 7, 1), entries=[]
    )
    snapshot = snapshot_versions([role_tax, skill_tax])
    assert snapshot.versions == {"role": "1.0.0", "skill": "2.0.0"}


def test_diff_detects_added_entry():
    old = _taxonomy("1.0.0", [_entry("skill.a", "A")])
    new = _taxonomy("1.0.1", [_entry("skill.a", "A"), _entry("skill.b", "B")])
    changes = diff_taxonomies(old, new)
    kinds = [c.kind for c in changes]
    assert "entry_added" in kinds


def test_diff_detects_removed_entry():
    old = _taxonomy("1.0.0", [_entry("skill.a", "A"), _entry("skill.b", "B")])
    new = _taxonomy("1.0.1", [_entry("skill.a", "A")])
    changes = diff_taxonomies(old, new)
    kinds = [c.kind for c in changes]
    assert "entry_removed" in kinds


def test_diff_detects_deprecation():
    old = _taxonomy("1.0.0", [_entry("skill.a", "A", status="active")])
    new = _taxonomy("1.0.1", [_entry("skill.a", "A", status="deprecated")])
    changes = diff_taxonomies(old, new)
    kinds = [c.kind for c in changes]
    assert "entry_deprecated" in kinds


def test_diff_detects_alias_added_and_removed():
    old = _taxonomy("1.0.0", [_entry("skill.a", "A", aliases=["Alpha"])])
    new = _taxonomy("1.0.1", [_entry("skill.a", "A", aliases=["A1"])])
    changes = diff_taxonomies(old, new)
    kinds = [c.kind for c in changes]
    assert "alias_added" in kinds
    assert "alias_removed" in kinds


def test_diff_detects_expansion_added_removed_and_weight_changed():
    old = _taxonomy(
        "1.0.0",
        [
            _entry(
                "skill.a",
                "A",
                expansions=[
                    Expansion(target_id="skill.b", weight=0.5, notes=""),
                    Expansion(target_id="skill.c", weight=0.4, notes=""),
                ],
            )
        ],
    )
    new = _taxonomy(
        "1.0.1",
        [
            _entry(
                "skill.a",
                "A",
                expansions=[
                    Expansion(target_id="skill.b", weight=0.9, notes=""),  # weight changed
                    Expansion(target_id="skill.d", weight=0.3, notes=""),  # added
                    # skill.c removed
                ],
            )
        ],
    )
    changes = diff_taxonomies(old, new)
    kinds = {c.kind for c in changes}
    assert kinds == {"expansion_weight_changed", "expansion_added", "expansion_removed"}


def test_diff_rejects_mismatched_taxonomy_types():
    skill_tax = _taxonomy("1.0.0", [])
    role_tax = Taxonomy(
        taxonomy_type=TaxonomyType.ROLE, version="1.0.0", updated_at=date(2026, 7, 1), entries=[]
    )
    with pytest.raises(ValueError):
        diff_taxonomies(skill_tax, role_tax)


def test_diff_no_changes_returns_empty_list():
    tax = _taxonomy("1.0.0", [_entry("skill.a", "A")])
    assert diff_taxonomies(tax, tax) == []
