"""The Candidate Matching Engine -- Sprint 19 (Module 1).

Scores every candidate a search returns across the fixed set of
dimensions in matching/config.py's DIMENSIONS. Every candidate is
evaluated -- there is no exact-match or first-match shortcut (Module 2's
explicit rule). Dimensions the requirement doesn't carry enough
information to score (industry, education, certifications, company
preference -- CanonicalJobRequirement only has role + skills, and that
contract is frozen; also experience/location when no such hint exists in
the raw query, and health/confidence when the candidate has none yet)
are reported at a neutral score (50.0) in `component_scores` and listed
honestly in `missing_fields` -- but are excluded from the *overall*
weighted average, so a candidate is never penalized (or flattered) by
data the requirement simply didn't specify. Only dimensions the engine
actually had something to compare move the overall score.

`raw_query`, when supplied, is used only for two lightweight, best-effort
heuristics (a plain "N+ years" experience pattern and a location-name
substring match) that live entirely in this new module -- they do not
change, extend, or duplicate Query Understanding's own parsing.
"""
from __future__ import annotations

import re

from app.candidate_repository.models import Candidate
from app.matching.config import DIMENSIONS, MatchingConfig
from app.matching.models import MatchResult
from app.search_planner.models import CanonicalJobRequirement, SearchPlan

_NEUTRAL = 50.0
_EXPERIENCE_PATTERN = re.compile(r"(\d+)\s*\+?\s*years?", re.IGNORECASE)


def _tokens(*values: str | None) -> set[str]:
    out: set[str] = set()
    for value in values:
        if not value:
            continue
        out.add(value.strip().lower())
    return out


def _candidate_text_blob(candidate: Candidate) -> str:
    parts = [candidate.role, candidate.headline, candidate.summary, candidate.current_company]
    parts += candidate.skills
    return " ".join(p for p in parts if p).lower()


# Each scorer returns (score, matched, applicable). `applicable=False`
# means there was nothing in the requirement/candidate/query to compare
# for this candidate -- the dimension is still reported (neutrally) but
# excluded from the overall weighted average.


def _score_role(candidate: Candidate, requirement: CanonicalJobRequirement) -> tuple[float, bool, bool]:
    if not requirement.role.strip():
        return _NEUTRAL, False, False
    req_tokens = set(requirement.role.strip().lower().split())
    cand_tokens = set(candidate.role.strip().lower().split())
    if candidate.role.strip().lower() == requirement.role.strip().lower():
        return 100.0, True, True
    overlap = req_tokens & cand_tokens
    score = round(100.0 * len(overlap) / len(req_tokens), 2) if req_tokens else _NEUTRAL
    return score, bool(overlap), True


def _score_skills(candidate: Candidate, requirement: CanonicalJobRequirement) -> tuple[float, bool, bool]:
    req_skills = _tokens(*requirement.skills)
    if not req_skills:
        return _NEUTRAL, False, False
    cand_skills = _tokens(*candidate.skills)
    matched = req_skills & cand_skills
    return round(100.0 * len(matched) / len(req_skills), 2), bool(matched), True


def _score_keyword_similarity(candidate: Candidate, plan: SearchPlan) -> tuple[float, bool, bool]:
    terms = _tokens(*plan.search_terms)
    if not terms:
        return _NEUTRAL, False, False
    blob = _candidate_text_blob(candidate)
    matched = {t for t in terms if t in blob}
    return round(100.0 * len(matched) / len(terms), 2), bool(matched), True


def _score_knowledge_expansion(candidate: Candidate, plan: SearchPlan) -> tuple[float, bool, bool]:
    if not plan.weights:
        return _NEUTRAL, False, False
    blob = _candidate_text_blob(candidate)
    total_weight = sum(plan.weights.values())
    if total_weight <= 0:
        return _NEUTRAL, False, False
    matched_weight = sum(w for term, w in plan.weights.items() if term.strip().lower() in blob)
    return round(100.0 * matched_weight / total_weight, 2), matched_weight > 0, True


def _score_experience(candidate: Candidate, raw_query: str | None) -> tuple[float, bool, bool]:
    if not raw_query:
        return _NEUTRAL, False, False
    match = _EXPERIENCE_PATTERN.search(raw_query)
    if not match:
        return _NEUTRAL, False, False
    required_years = float(match.group(1))
    if required_years <= 0:
        return _NEUTRAL, False, False
    if candidate.experience >= required_years:
        return 100.0, True, True
    return round(max(0.0, 100.0 * candidate.experience / required_years), 2), False, True


def _score_location(candidate: Candidate, raw_query: str | None) -> tuple[float, bool, bool]:
    if not raw_query or not candidate.location:
        return _NEUTRAL, False, False
    if candidate.location.strip().lower() in raw_query.strip().lower():
        return 100.0, True, True
    return _NEUTRAL, False, False


def _score_health(candidate: Candidate) -> tuple[float, bool, bool]:
    if candidate.health_score is None:
        return _NEUTRAL, False, False
    return round(candidate.health_score, 2), True, True


def _score_confidence(candidate: Candidate) -> tuple[float, bool, bool]:
    if not candidate.section_confidence:
        return _NEUTRAL, False, False
    values = list(candidate.section_confidence.values())
    return round(100.0 * sum(values) / len(values), 2), True, True


class MatchingEngine:
    def __init__(self, config: MatchingConfig | None = None):
        self._config = config or MatchingConfig()

    def score(
        self,
        candidate: Candidate,
        requirement: CanonicalJobRequirement,
        plan: SearchPlan,
        raw_query: str | None = None,
    ) -> MatchResult:
        component_scores: dict[str, float] = {}
        matched_fields: list[str] = []
        missing_fields: list[str] = []
        reasons: list[str] = []

        scorers = {
            "role": lambda: _score_role(candidate, requirement),
            "skills": lambda: _score_skills(candidate, requirement),
            "keyword_similarity": lambda: _score_keyword_similarity(candidate, plan),
            "knowledge_expansion_similarity": lambda: _score_knowledge_expansion(candidate, plan),
            "experience": lambda: _score_experience(candidate, raw_query),
            "location": lambda: _score_location(candidate, raw_query),
            "health": lambda: _score_health(candidate),
            "confidence": lambda: _score_confidence(candidate),
        }
        # Dimensions with no signal available anywhere in the current,
        # frozen upstream contracts (CanonicalJobRequirement has no
        # industry/education/certification/company-preference fields).
        unscored_dimensions = set(DIMENSIONS) - set(scorers)

        weighted_sum = 0.0
        weighted_total = 0.0

        for dimension in DIMENSIONS:
            if dimension in unscored_dimensions:
                component_scores[dimension] = _NEUTRAL
                missing_fields.append(dimension)
                continue

            value, matched, applicable = scorers[dimension]()
            component_scores[dimension] = value

            if not applicable:
                missing_fields.append(dimension)
                continue

            weight = self._config.weight_for(dimension)
            weighted_sum += value * weight
            weighted_total += weight

            if matched:
                matched_fields.append(dimension)
                reasons.append(f"{dimension.replace('_', ' ')} matched ({value}%)")

        overall = round(weighted_sum / weighted_total, 2) if weighted_total > 0 else _NEUTRAL

        if not reasons:
            reasons.append("No requirement fields matched this candidate's profile.")

        return MatchResult(
            candidate_id=candidate.id,
            overall_score=overall,
            component_scores=component_scores,
            matched_fields=matched_fields,
            missing_fields=missing_fields,
            reasons=reasons,
        )

    def score_all(
        self,
        candidates: list[Candidate],
        requirement: CanonicalJobRequirement,
        plan: SearchPlan,
        raw_query: str | None = None,
    ) -> list[MatchResult]:
        return [self.score(c, requirement, plan, raw_query) for c in candidates]
