"""Strongly typed models for the Search Planner.

The Search Planner sits between Query Understanding and Source Fan-out in
the pipeline described in docs/KNOWLEDGE_ENGINE.md section 2 ("[2] Knowledge
Engine -- Expansion"). Its job is narrow and mechanical: take a canonical
job requirement and turn it into an executable SearchPlan by asking the
Knowledge Engine (already implemented and approved) to expand every
canonical field. This module performs NO normalization logic, NO scoring,
NO searching, and NO matching itself -- it only calls the existing
KnowledgeEngine and reshapes its output into a plan object.

Scoping note (not an architecture change -- flagging for visibility only):
Query Understanding has not been implemented yet, so there is no real
JobRequirement type to import. `CanonicalJobRequirement` below is the
minimal input contract this module needs today: a role plus a list of
skills, both assumed to already be recruiter-intent extracted (not raw,
un-parsed sentences). When Query Understanding is implemented, its
JobRequirement output is expected to satisfy (or be trivially adapted to)
this same shape -- this class is deliberately small so it is easy to
replace/subsume later without reshaping the rest of this module.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Which JobRequirement field a filter/term originated from. Mirrors the
    taxonomy_type values used by the Knowledge Engine (role, skill) so a
    SearchPlan field can be traced straight back to a TaxonomyType.
    """

    ROLE = "role"
    SKILL = "skill"


class CanonicalJobRequirement(BaseModel):
    """Minimal input to the Search Planner -- see module docstring for why
    this is intentionally small and provisional pending Query
    Understanding's real JobRequirement.
    """

    role: str
    skills: list[str] = Field(default_factory=list)


class StrictFilter(BaseModel):
    """A hard filter taken directly from the recruiter's stated requirement,
    unexpanded. Per the brief's example, "Product Engineer" and "AWS" are
    both strict filters -- they are exactly what the recruiter asked for,
    not a broadened search term.
    """

    field_type: FieldType
    canonical_id: str
    canonical_value: str


class ExpandedFilter(BaseModel):
    """One searchable equivalent produced by the Knowledge Engine's
    expand(), plus the weight and notes carried over from the taxonomy
    edge. `source_canonical_id` traces this expansion back to the strict
    filter it came from, so a SearchPlan is always explainable: "this term
    is here because it's a Knowledge Engine expansion of X, at weight Y."
    """

    field_type: FieldType
    source_canonical_id: str
    expanded_id: str
    expanded_value: str
    weight: float = Field(ge=0.0, le=1.0)
    notes: str = ""


class UnresolvedTerm(BaseModel):
    """A term from the input requirement that the Knowledge Engine did not
    recognize (KnowledgeEngine.normalize() returned None). Per
    docs/KNOWLEDGE_ENGINE.md section 8, an unrecognized term is logged, not
    silently dropped and not guessed at -- this is that log entry. The term
    still becomes a strict filter (see planner.py), just with no expansion
    available and no canonical_id to point to.
    """

    field_type: FieldType
    raw_term: str


class SearchPlan(BaseModel):
    """The complete, executable output of the Search Planner for one
    JobRequirement. This is the object future connectors will consume (once
    Connectors are implemented -- explicitly out of scope for this module).

    - `strict`: exactly what the recruiter asked for, unexpanded.
    - `expanded`: every Knowledge-Engine-derived searchable equivalent,
      each retaining its expansion weight.
    - `search_terms`: a flat, de-duplicated list of every canonical string
      (strict + expanded) in one place, for connectors that just want "give
      me a list of terms to search for" without caring about the
      strict/expanded/weight structure.
    - `weights`: a flat lookup of expanded_value -> weight, matching the
      shape shown in the brief's example output (`EC2 = 0.9`, etc.) for
      convenience, alongside the fuller ExpandedFilter objects in `expanded`.
    - `unresolved`: terms from the input that the Knowledge Engine did not
      recognize at all -- surfaced rather than silently dropped.
    - `knowledge_versions`: which taxonomy versions were active when this
      plan was built (from KnowledgeEngine.get_version()), so a plan is
      always reproducible/explainable later even if taxonomies change --
      same reasoning as docs/KNOWLEDGE_ENGINE.md section 7.1.
    """

    strict: list[StrictFilter] = Field(default_factory=list)
    expanded: list[ExpandedFilter] = Field(default_factory=list)
    search_terms: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)
    unresolved: list[UnresolvedTerm] = Field(default_factory=list)
    knowledge_versions: dict[str, str] = Field(default_factory=dict)
