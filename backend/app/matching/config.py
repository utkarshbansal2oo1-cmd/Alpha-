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


_default_config = MatchingConfig()


def get_matching_config() -> MatchingConfig:
    """FastAPI dependency-injection provider, matching every other
    provider function's pattern in this codebase (a plain function,
    swappable via app.dependency_overrides in tests)."""
    return _default_config
