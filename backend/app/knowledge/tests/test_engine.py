"""Tests for app.knowledge.engine.KnowledgeEngine: load/reload, normalize,
expand, get_entry, get_version, suggest_canonical, and the "must call
load() first" guard. Uses the minimal_valid fixture for isolated,
deterministic assertions, plus the real seed data for the exact examples
given in docs/KNOWLEDGE_ENGINE.md.
"""
from pathlib import Path

import pytest

from app.knowledge.engine import KnowledgeEngine, get_knowledge_engine
from app.knowledge.exceptions import KnowledgeEngineError

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def engine() -> KnowledgeEngine:
    eng = KnowledgeEngine(taxonomies_dir=FIXTURES / "minimal_valid", filenames=["roles.json"])
    eng.load()
    return eng


def test_engine_requires_load_before_use():
    eng = KnowledgeEngine(taxonomies_dir=FIXTURES / "minimal_valid", filenames=["roles.json"])
    with pytest.raises(KnowledgeEngineError):
        eng.normalize("Role A")


def test_normalize_canonical_value(engine):
    assert engine.normalize("Role A") == "role.a"


def test_normalize_alias_case_insensitive(engine):
    assert engine.normalize("ra") == "role.a"
    assert engine.normalize("  Role-A  ") == "role.a"


def test_normalize_unknown_term_returns_none(engine):
    assert engine.normalize("Totally Unknown Term") is None


def test_normalize_none_returns_none(engine):
    assert engine.normalize(None) is None


def test_get_entry_known_id(engine):
    entry = engine.get_entry("role.a")
    assert entry is not None
    assert entry.canonical == "Role A"


def test_get_entry_missing_id_returns_none(engine):
    assert engine.get_entry("role.does_not_exist") is None


def test_expand_by_id(engine):
    results = engine.expand("role.a")
    assert len(results) == 1
    assert results[0].entry.id == "role.b"
    assert results[0].weight == 0.5


def test_expand_by_canonical_value(engine):
    results = engine.expand("Role A")
    assert len(results) == 1
    assert results[0].entry.canonical == "Role B"


def test_expand_entry_with_no_expansions_returns_empty_list(engine):
    assert engine.expand("role.b") == []


def test_expand_unknown_term_returns_empty_list(engine):
    assert engine.expand("nonexistent") == []


def test_get_version(engine):
    versions = engine.get_version()
    assert versions == {"role": "1.0.0"}


def test_suggest_canonical_finds_close_match(engine):
    suggestions = engine.suggest_canonical("Role A", limit=5)
    assert suggestions
    assert suggestions[0].entry.id == "role.a"
    assert suggestions[0].score > 0.9


def test_suggest_canonical_empty_term_returns_empty_list(engine):
    assert engine.suggest_canonical("") == []
    assert engine.suggest_canonical("   ") == []


def test_reload_picks_up_changed_data(tmp_path):
    taxonomies_dir = tmp_path
    roles_file = taxonomies_dir / "roles.json"
    roles_file.write_text(
        '{"taxonomy_type": "role", "version": "1.0.0", "updated_at": "2026-07-01", '
        '"entries": [{"id": "role.x", "canonical": "Role X", "aliases": [], '
        '"expansions": [], "status": "active", "created_at": "2026-07-01", '
        '"updated_at": "2026-07-01"}]}',
        encoding="utf-8",
    )
    eng = KnowledgeEngine(taxonomies_dir=taxonomies_dir, filenames=["roles.json"])
    eng.load()
    assert eng.get_entry("role.x") is not None
    assert eng.get_version() == {"role": "1.0.0"}

    roles_file.write_text(
        '{"taxonomy_type": "role", "version": "1.0.1", "updated_at": "2026-07-02", '
        '"entries": [{"id": "role.y", "canonical": "Role Y", "aliases": [], '
        '"expansions": [], "status": "active", "created_at": "2026-07-02", '
        '"updated_at": "2026-07-02"}]}',
        encoding="utf-8",
    )
    eng.reload()
    assert eng.get_entry("role.x") is None  # replaced, not merged
    assert eng.get_entry("role.y") is not None
    assert eng.get_version() == {"role": "1.0.1"}


def test_singleton_returns_same_instance():
    eng1 = get_knowledge_engine()
    eng2 = get_knowledge_engine()
    assert eng1 is eng2


# --- exact examples from docs/KNOWLEDGE_ENGINE.md, against real seed data ---


@pytest.fixture()
def real_engine() -> KnowledgeEngine:
    eng = KnowledgeEngine()
    eng.load()
    return eng


def test_product_engineer_expansion_matches_design_doc_example(real_engine):
    canonical_id = real_engine.normalize("Product Engineer")
    assert canonical_id == "role.product_engineer"
    expanded_names = {r.entry.canonical for r in real_engine.expand(canonical_id)}
    assert expanded_names == {
        "Backend Engineer",
        "Platform Engineer",
        "Software Engineer",
        "API Engineer",
    }


def test_aws_expansion_matches_design_doc_example(real_engine):
    canonical_id = real_engine.normalize("AWS")
    assert canonical_id == "skill.aws"
    expanded_names = {r.entry.canonical for r in real_engine.expand(canonical_id)}
    assert expanded_names == {"EC2", "IAM", "Lambda", "S3", "EKS", "CloudFormation"}


def test_alias_resolution_for_kubernetes(real_engine):
    assert real_engine.normalize("K8s") == "skill.kubernetes"
    assert real_engine.normalize("kubernetes") == "skill.kubernetes"
