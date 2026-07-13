"""The Discovery Decision Engine -- Sprint 18/19.

Decides whether the candidates CandidateRepository.search() already
returned are good enough, or whether the Discovery Orchestrator should be
invoked to pull in new candidates from connected sources. Either signal
below is independently sufficient to trigger discovery:

- candidate_count < min_result_threshold
- average_match_confidence < min_confidence_threshold

Both thresholds are constructor parameters, not hardcoded, so callers
(and tests) can tune them without touching this module's logic.

Sprint 19 addition: `evaluate()` accepts an optional `match_results`
argument -- when the caller has already run the new Matching Engine
(app/matching/engine.py) over these candidates, its per-candidate
`overall_score` is used as the confidence signal (Module 3's "Average
Score" check) instead of the older, Sprint-18 requirement-term-overlap
heuristic in app/discovery/scoring.py. Omitting it preserves the exact
Sprint 18 behavior (and all of Sprint 18's tests), so this is additive,
not a breaking change.
"""
from __future__ import annotations

from app.candidate_repository.models import Candidate
from app.discovery.models import DiscoveryDecision
from app.discovery.scoring import average_match_confidence
from app.matching.models import MatchResult
from app.search_planner.models import SearchPlan

DEFAULT_MIN_RESULT_THRESHOLD = 5
DEFAULT_MIN_CONFIDENCE_THRESHOLD = 70.0


class DiscoveryDecisionEngine:
    def __init__(
        self,
        min_result_threshold: int = DEFAULT_MIN_RESULT_THRESHOLD,
        min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE_THRESHOLD,
    ):
        self._min_result_threshold = min_result_threshold
        self._min_confidence_threshold = min_confidence_threshold

    def evaluate(
        self,
        candidates: list[Candidate],
        plan: SearchPlan,
        match_results: list[MatchResult] | None = None,
    ) -> DiscoveryDecision:
        count = len(candidates)
        if match_results is not None:
            confidence = (
                round(sum(m.overall_score for m in match_results) / len(match_results), 2)
                if match_results
                else 0.0
            )
        else:
            confidence = average_match_confidence(candidates, plan)

        insufficient_count = count < self._min_result_threshold
        low_confidence = confidence < self._min_confidence_threshold
        should_discover = insufficient_count or low_confidence

        if should_discover:
            reasons = []
            if insufficient_count:
                reasons.append(f"only {count} candidate(s) found (minimum {self._min_result_threshold})")
            if low_confidence:
                reasons.append(
                    f"average match confidence {confidence}% is below the {self._min_confidence_threshold}% threshold"
                )
            reason = "Triggering discovery: " + " and ".join(reasons) + "."
        else:
            reason = (
                f"{count} candidate(s) found with {confidence}% average match confidence "
                "-- sufficient, no discovery needed."
            )

        return DiscoveryDecision(
            should_discover=should_discover,
            reason=reason,
            candidate_count=count,
            average_match_confidence=confidence,
            min_result_threshold=self._min_result_threshold,
            min_confidence_threshold=self._min_confidence_threshold,
        )
