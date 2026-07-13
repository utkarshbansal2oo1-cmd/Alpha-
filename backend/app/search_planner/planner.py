"""SearchPlanner: converts a canonical JobRequirement into an executable
SearchPlan by delegating all expansion to the already-approved
KnowledgeEngine (backend/app/knowledge/). This module adds no normalization
logic, no scoring logic, and no vocabulary of its own -- it is purely an
orchestration/reshaping layer over KnowledgeEngine.normalize()/.expand().

Per the brief: no search, no connectors, no matching, no database. This
module's only output is a SearchPlan object.
"""
from __future__ import annotations

from app.knowledge.engine import KnowledgeEngine, get_knowledge_engine
from app.search_planner.models import (
    CanonicalJobRequirement,
    ExpandedFilter,
    FieldType,
    SearchPlan,
    StrictFilter,
    UnresolvedTerm,
)


class SearchPlanner:
    """Builds a SearchPlan from a CanonicalJobRequirement.

    Takes a KnowledgeEngine instance (defaulting to the shared singleton via
    get_knowledge_engine(), the same pattern used elsewhere in the codebase)
    rather than constructing its own -- the Knowledge Engine is loaded once
    at application startup and reused; the Search Planner must never load or
    reload taxonomy data itself.
    """

    def __init__(self, knowledge_engine: KnowledgeEngine | None = None):
        self._knowledge_engine = knowledge_engine or get_knowledge_engine()

    def build_plan(self, requirement: CanonicalJobRequirement) -> SearchPlan:
        """Produces one SearchPlan for the given requirement.

        For each field (role, skills):
          1. Resolve the raw term to a canonical entry via
             KnowledgeEngine.normalize(). If it resolves, the canonical
             value becomes a StrictFilter. If it does NOT resolve, the raw
             term still becomes a StrictFilter (the recruiter's stated
             requirement is preserved even if the Knowledge Engine doesn't
             recognize it), and it is additionally recorded as an
             UnresolvedTerm so it can be reviewed and added to the taxonomy
             later (docs/KNOWLEDGE_ENGINE.md section 8).
          2. If it resolved, call KnowledgeEngine.expand() on the canonical
             id and turn every result into an ExpandedFilter, preserving the
             weight and notes from the taxonomy edge untouched.

        Strict and expanded filters are kept in two separate lists (never
        merged into one undifferentiated list) per the brief's explicit
        requirement to separate them.
        """
        strict: list[StrictFilter] = []
        expanded: list[ExpandedFilter] = []
        unresolved: list[UnresolvedTerm] = []

        self._process_field(FieldType.ROLE, [requirement.role], strict, expanded, unresolved)
        self._process_field(FieldType.SKILL, requirement.skills, strict, expanded, unresolved)

        search_terms = self._build_search_terms(strict, expanded)
        weights = {f.expanded_value: f.weight for f in expanded}

        return SearchPlan(
            strict=strict,
            expanded=expanded,
            search_terms=search_terms,
            weights=weights,
            unresolved=unresolved,
            knowledge_versions=self._knowledge_engine.get_version(),
        )

    def _process_field(
        self,
        field_type: FieldType,
        raw_terms: list[str],
        strict: list[StrictFilter],
        expanded: list[ExpandedFilter],
        unresolved: list[UnresolvedTerm],
    ) -> None:
        for raw_term in raw_terms:
            if not raw_term or not raw_term.strip():
                continue

            canonical_id = self._knowledge_engine.normalize(raw_term)

            if canonical_id is None:
                # Unrecognized by the Knowledge Engine: preserve the
                # recruiter's raw term as a strict filter (never silently
                # dropped), and record it as unresolved -- no expansion is
                # possible for a term the engine doesn't know.
                strict.append(
                    StrictFilter(field_type=field_type, canonical_id="", canonical_value=raw_term)
                )
                unresolved.append(UnresolvedTerm(field_type=field_type, raw_term=raw_term))
                continue

            entry = self._knowledge_engine.get_entry(canonical_id)
            # entry cannot be None here: normalize() only ever returns ids
            # that resolve via get_entry() -- both are backed by the same
            # loaded index in KnowledgeEngine.
            strict.append(
                StrictFilter(
                    field_type=field_type, canonical_id=entry.id, canonical_value=entry.canonical
                )
            )

            for expansion_result in self._knowledge_engine.expand(canonical_id):
                expanded.append(
                    ExpandedFilter(
                        field_type=field_type,
                        source_canonical_id=entry.id,
                        expanded_id=expansion_result.entry.id,
                        expanded_value=expansion_result.entry.canonical,
                        weight=expansion_result.weight,
                        notes=expansion_result.notes,
                    )
                )

    @staticmethod
    def _build_search_terms(
        strict: list[StrictFilter], expanded: list[ExpandedFilter]
    ) -> list[str]:
        """Flat, de-duplicated, order-preserving list of every canonical
        string in the plan (strict first, then expanded) -- the shape a
        future connector would want if it just needs "what do I search
        for", without caring about strict/expanded/weight structure.
        """
        seen: set[str] = set()
        terms: list[str] = []
        for f in strict:
            if f.canonical_value not in seen:
                seen.add(f.canonical_value)
                terms.append(f.canonical_value)
        for f in expanded:
            if f.expanded_value not in seen:
                seen.add(f.expanded_value)
                terms.append(f.expanded_value)
        return terms
