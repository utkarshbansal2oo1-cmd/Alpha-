"""Configuration for the Matching, Ranking, and Discovery Decision Engines
-- Sprint 19 (Module 10).

Everything the sprint brief lists as "must be configurable" lives here as
plain constructor defaults on one dataclass: minimum candidate threshold,
minimum score, connector priority overrides, discovery timeout, and
ranking weights. A single MatchingConfig instance is threaded through the
matching/ranking/decision engines via dependency injection (see
app/routers/discovery_search.py), so tests and future admin UI can supply
a different instance without touching engine code.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# The fixed dimension vocabulary the Matching Engine always scores against
# (Module 1 of the sprint brief). Order is preserved for the UI/explanation
# output but is not itself meaningful to scoring.
DIMENSIONS: tuple[str, ...] = (
    "role",
    "skills",
    "industry",
    "experience",
    "location",
    "education",
    "certifications",
    "company_preference",
    "keyword_similarity",
    "knowledge_expansion_similarity",
    "health",
    "confidence",
)

DEFAULT_RANKING_WEIGHTS: dict[str, float] = {dim: 1.0 for dim in DIMENSIONS}


@dataclass
class MatchingConfig:
    # Module 3: Discovery Decision Engine thresholds.
    min_candidate_threshold: int = 5
    min_score: float = 70.0

    # Module 6: per-connector priority override (connector name -> priority).
    # Empty by default -- connectors fall back to their own declared
    # `priority` attribute; entries here take precedence.
    connector_priority: dict[str, int] = field(default_factory=dict)

    # Module 4/5: seconds the Discovery Orchestrator allows a single
    # connector's discover() call to run before treating it as failed
    # (Module 12: connector execution must not block the whole request
    # indefinitely).
    discovery_timeout: float = 15.0

    # Module 1: weight per scoring dimension. Missing dimensions default to
    # 1.0 (equal weight); values are normalized at scoring time so callers
    # don't need to pre-normalize a partial override.
    ranking_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_RANKING_WEIGHTS))

    def weight_for(self, dimension: str) -> float:
        return self.ranking_weights.get(dimension, 1.0)

    def priority_for(self, connector_name: str, declared_priority: int) -> int:
        return self.connector_priority.get(connector_name, declared_priority)

    # --- Sprint 35: relevance visibility threshold (Solution 2/7) ----------
    #
    # min_visible_relevance_score is the flat fallback used when
    # adaptive_relevance_threshold()'s pool-size tiers don't apply. The
    # method itself implements Solution 7's adaptive tiers: a huge result
    # pool gets a stricter cutoff (keeps common searches clean), a tiny
    # pool gets a looser one (a niche search shouldn't hide every result
    # it found), and everything in between uses the configured flat
    # default. This threshold is used for two independent purposes in
    # discovery_search.py's smart_search(): (1) deciding whether live
    # (non-seed) candidates are sufficient on their own, and (2) splitting
    # the final ranked pool into "visible by default" vs. "weaker matches,
    # shown on request" for the API response.
    min_visible_relevance_score: float = 60.0

    def adaptive_relevance_threshold(self, total_candidates: int) -> float:
        if total_candidates > 100:
            return 70.0
        if total_candidates < 20:
            return 45.0
        return self.min_visible_relevance_score


_default_config = MatchingConfig()


def get_matching_config() -> MatchingConfig:
    """FastAPI dependency-injection provider, matching every other
    provider function's pattern in this codebase (a plain function,
    swappable via app.dependency_overrides in tests)."""
    return _default_config
