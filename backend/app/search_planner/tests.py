"""Tests for the Search Planner: models.py and planner.py.

Named tests.py (singular file, not a tests/ package) per the brief's
explicit file list (models.py, planner.py, tests.py). Uses the real,
already-approved Knowledge Engine seed taxonomies -- no mocking of
KnowledgeEngine, since the whole point of this module is that it correctly
delegates to the real thing.
"""
import pytest

from app.knowledge.engine import KnowledgeEngine
from app.search_planner.models import CanonicalJobRequirement, FieldType
from app.search_planner.planner import SearchPlanner


@pytest.fixture()
def engine() -> KnowledgeEngine:
    eng = KnowledgeEngine()
    eng.load()
    return eng


@pytest.fixture()
def planner(engine) -> SearchPlanner:
    return SearchPlanner(knowledge_engine=engine)


# --- the exact example from the brief ---------------------------------


def test_brief_example_product_engineer_aws(planner):
    plan = planner.build_plan(
        CanonicalJobRequirement(role="Product Engineer", skills=["AWS"])
    )

    strict_values = {f.canonical_value for f in plan.strict}
    assert strict_values == {"Product Engineer", "AWS"}

    expanded_values = {f.expanded_value for f in plan.expanded}
    assert expanded_values == {
        "Backend Engineer",
        "Platform Engineer",
        "Software Engineer",
        "API Engineer",
        "EC2",
        "IAM",
        "Lambda",
        "S3",
        "EKS",
        "CloudFormation",
    }

    assert plan.weights["EC2"] == 0.9
    assert plan.weights["IAM"] == 0.7
    assert plan.weights["Lambda"] == 0.8
    assert plan.weights["S3"] == 0.9
    assert plan.weights["EKS"] == 0.75
    assert plan.weights["CloudFormation"] == 0.6

    assert plan.unresolved == []


# --- strict vs expanded separation --------------------------------------


def test_strict_and_expanded_are_kept_separate(planner):
    plan = planner.build_plan(CanonicalJobRequirement(role="Product Engineer", skills=["AWS"]))
    strict_values = {f.canonical_value for f in plan.strict}
    expanded_values = {f.expanded_value for f in plan.expanded}
    # No overlap: a strict filter never also appears as an expansion of itself.
    assert strict_values.isdisjoint(expanded_values)


def test_strict_filters_carry_field_type(planner):
    plan = planner.build_plan(CanonicalJobRequirement(role="Product Engineer", skills=["AWS"]))
    role_filters = [f for f in plan.strict if f.field_type == FieldType.ROLE]
    skill_filters = [f for f in plan.strict if f.field_type == FieldType.SKILL]
    assert len(role_filters) == 1
    assert len(skill_filters) == 1
    assert role_filters[0].canonical_value == "Product Engineer"
    assert skill_filters[0].canonical_value == "AWS"


# --- weight preservation -------------------------------------------------


def test_expansion_weights_match_knowledge_engine_exactly(planner, engine):
    plan = planner.build_plan(CanonicalJobRequirement(role="", skills=["AWS"]))
    direct = {r.entry.canonical: r.weight for r in engine.expand("skill.aws")}
    for f in plan.expanded:
        assert f.weight == direct[f.expanded_value]


def test_expanded_filters_trace_back_to_source(planner):
    plan = planner.build_plan(CanonicalJobRequirement(role="", skills=["AWS"]))
    for f in plan.expanded:
        assert f.source_canonical_id == "skill.aws"


# --- alias input still resolves correctly --------------------------------


def test_alias_input_resolves_to_canonical(planner):
    plan = planner.build_plan(CanonicalJobRequirement(role="", skills=["K8s"]))
    strict_values = {f.canonical_value for f in plan.strict}
    assert strict_values == {"Kubernetes"}


# --- unresolved / unknown terms ------------------------------------------


def test_unknown_skill_becomes_strict_with_no_expansion_and_is_flagged(planner):
    plan = planner.build_plan(
        CanonicalJobRequirement(role="Product Engineer", skills=["SomeMadeUpSkillXYZ"])
    )
    strict_values = {f.canonical_value for f in plan.strict}
    assert "SomeMadeUpSkillXYZ" in strict_values

    unresolved_terms = {u.raw_term for u in plan.unresolved}
    assert "SomeMadeUpSkillXYZ" in unresolved_terms

    # No expansion should exist for the unresolved term.
    assert all(f.expanded_value != "SomeMadeUpSkillXYZ" for f in plan.expanded)


def test_entry_with_no_expansions_produces_no_expanded_filters(planner):
    # EC2 (an alias-resolvable skill) has no expansions of its own in the
    # seed taxonomy.
    plan = planner.build_plan(CanonicalJobRequirement(role="", skills=["EC2"]))
    assert plan.expanded == []
    assert {f.canonical_value for f in plan.strict} == {"EC2"}


# --- search_terms flattening ----------------------------------------------


def test_search_terms_are_deduplicated_and_ordered(planner):
    plan = planner.build_plan(CanonicalJobRequirement(role="Product Engineer", skills=["AWS"]))
    assert plan.search_terms[0] == "Product Engineer"
    assert plan.search_terms[1] == "AWS"
    assert len(plan.search_terms) == len(set(plan.search_terms))  # no duplicates
    assert "EC2" in plan.search_terms


def test_search_terms_deduplicate_overlap_between_strict_and_expanded(planner):
    # role.software_engineer is both a strict skill AND an expansion target
    # of Product Engineer -- should appear exactly once in search_terms.
    plan = planner.build_plan(
        CanonicalJobRequirement(role="Product Engineer", skills=["Software Engineer"])
    )
    assert plan.search_terms.count("Software Engineer") == 1


# --- empty / minimal input -------------------------------------------------


def test_empty_skills_list_produces_only_role_filters(planner):
    plan = planner.build_plan(CanonicalJobRequirement(role="AWS", skills=[]))
    # role field resolves against the role taxonomy only if it matches --
    # here "AWS" is not a role, so it's unresolved as a role but still a
    # strict filter (raw term preserved).
    assert len(plan.strict) == 1
    assert plan.strict[0].field_type == FieldType.ROLE


def test_blank_skill_strings_are_skipped(planner):
    plan = planner.build_plan(CanonicalJobRequirement(role="", skills=["AWS", "", "   "]))
    assert len([f for f in plan.strict if f.field_type == FieldType.SKILL]) == 1


# --- knowledge_versions provenance ----------------------------------------


def test_plan_records_knowledge_versions(planner, engine):
    plan = planner.build_plan(CanonicalJobRequirement(role="Product Engineer", skills=["AWS"]))
    assert plan.knowledge_versions == engine.get_version()


# --- planner defaults to the shared singleton -----------------------------


def test_planner_defaults_to_singleton_knowledge_engine():
    from app.knowledge.engine import get_knowledge_engine

    default_planner = SearchPlanner()
    assert default_planner._knowledge_engine is get_knowledge_engine()
