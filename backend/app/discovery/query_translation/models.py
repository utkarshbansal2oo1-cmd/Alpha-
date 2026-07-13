"""Models for the Connector Intelligence Layer -- Sprint 20C."""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class ConnectorQuery(BaseModel):
    """One connector's translated view of a single recruiter search.

    `connector_queries` is the ordered list of connector-native search
    expressions to actually run (capped at
    ConnectorTranslationConfig.max_queries_per_connector). `filters` pulls
    out any qualifier-style term (e.g. "language:Go") into a structured
    key/value for connectors that want it separately from the free-text
    list. `metadata` carries the strategy name and any passthrough flag;
    `confidence` reflects how much the translation relied on an explicit,
    known skill mapping (1.0) versus a generic fallback (lower).
    """

    connector_name: str
    original_query: str
    connector_queries: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @property
    def is_passthrough(self) -> bool:
        """True for strategies (Greenhouse, browser extension, generic)
        that explicitly do not want the Discovery Orchestrator to run
        more than one discover() call -- connector_queries still carries
        the recruiter-facing strings for observability/logging, but the
        orchestrator must call discover() with the ORIGINAL, untouched
        requirement exactly once, per each strategy's own stated
        contract ("No API changes" / "single search")."""
        return bool(self.metadata.get("passthrough"))


@dataclass
class ConnectorTranslationConfig:
    """Module 10-style configuration, same pattern as
    app.matching.config.MatchingConfig: one injectable dataclass, no
    hardcoded constants buried in strategy code."""

    max_queries_per_connector: int = 8
    max_depth: int = 2  # how many rounds of domain-term combination to generate (see strategies/github.py)
    expansion_enabled: bool = True
    connector_enabled: dict[str, bool] = field(default_factory=dict)

    def is_enabled_for(self, connector_name: str) -> bool:
        return self.connector_enabled.get(connector_name, True)


_default_config = ConnectorTranslationConfig()


def get_connector_translation_config() -> ConnectorTranslationConfig:
    """FastAPI dependency-injection provider, same pattern as every other
    provider function in this codebase."""
    return _default_config
