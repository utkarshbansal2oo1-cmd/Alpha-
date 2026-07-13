"""The Ranking Engine -- Sprint 19 (Module 2).

Sorts candidates by overall match score, then confidence, then candidate
health, then recency, with a final deterministic tie-break on candidate
id (so ranking is stable and reproducible in tests). Every candidate
passed in is ranked -- no exact-match or first-match shortcut.
"""
from __future__ import annotations

import logging

from app.candidate_repository.models import Candidate
from app.matching.models import MatchResult, RankedCandidate

logger = logging.getLogger(__name__)


def _recency_key(candidate: Candidate) -> float:
    # Most recent capture_source timestamp, as a sortable epoch float.
    # Candidates with no capture history (e.g. plain seed data) sort last
    # on this dimension only -- it is the lowest-priority tie-breaker.
    if not candidate.capture_sources:
        return 0.0
    return max(cs.capture_time.timestamp() for cs in candidate.capture_sources)


class RankingEngine:
    def rank(
        self,
        candidates: list[Candidate],
        matches: list[MatchResult],
    ) -> list[RankedCandidate]:
        by_id = {c.id: c for c in candidates}

        def sort_key(match: MatchResult):
            candidate = by_id[match.candidate_id]
            confidence = match.component_scores.get("confidence", 0.0)
            health = match.component_scores.get("health", 0.0)
            return (
                -match.overall_score,
                -confidence,
                -health,
                -_recency_key(candidate),
                candidate.id,
            )

        ordered = sorted(matches, key=sort_key)

        return [
            RankedCandidate(candidate_id=m.candidate_id, match=m, rank=i + 1)
            for i, m in enumerate(ordered)
        ]

    def rank_candidates_by_id(self, ranked: list[RankedCandidate], candidates: list[Candidate]) -> list[Candidate]:
        """Convenience: reorders the original Candidate objects to match a
        RankedCandidate list's order, for callers (like the API response)
        that want plain Candidate objects back in ranked order."""
        by_id = {c.id: c for c in candidates}
        result = [by_id[r.candidate_id] for r in ranked if r.candidate_id in by_id]

        # This is the ONE place in the whole pipeline with an implicit
        # filter -- `if r.candidate_id in by_id`. It silently drops a
        # ranked candidate whose id isn't present in `candidates`. That
        # should never happen if `candidates` and `matches`/`ranked` were
        # built from the same list; a mismatch here always indicates a
        # caller bug, never expected behavior -- logged at warning so a
        # real production regression (like the Sprint 23 10-vs-2
        # candidate loss) surfaces immediately instead of silently
        # returning fewer candidates than were actually ranked.
        dropped = len(ranked) - len(result)
        if dropped > 0:
            logger.warning(
                "ranking_engine.rank_candidates_by_id dropped %d of %d ranked candidates "
                "(candidates_available=%d) -- ranked candidate ids not found in the "
                "candidates list passed in; this indicates a caller bug upstream.",
                dropped,
                len(ranked),
                len(candidates),
            )
        return result
