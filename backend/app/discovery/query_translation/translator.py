"""ConnectorQueryTranslator -- Sprint 20C.

Dispatches to a per-connector strategy module (strategies/github.py,
strategies/greenhouse.py, strategies/browser_extension.py) by connector
name, falling back to strategies/generic.py (untouched passthrough) for
any connector without a dedicated strategy -- including future connectors
(CSV/resume/HRMS) and any connector added later. Per-connector translation
can be disabled via ConnectorTranslationConfig.connector_enabled, which
also routes to the generic passthrough.
"""
from __future__ import annotations

from app.discovery.query_translation.models import ConnectorQuery, ConnectorTranslationConfig
from app.discovery.query_translation.strategies import browser_extension, generic, github, greenhouse
from app.search_planner.models import CanonicalJobRequirement, SearchPlan

_STRATEGIES = {
    "github": github.translate,
    "greenhouse_ats": greenhouse.translate,
    "browser_extension": browser_extension.translate,
}


class ConnectorQueryTranslator:
    def __init__(self, config: ConnectorTranslationConfig | None = None):
        self._config = config or ConnectorTranslationConfig()

    def translate(
        self,
        connector_name: str,
        requirement: CanonicalJobRequirement,
        raw_query: str | None,
        plan: SearchPlan,
    ) -> ConnectorQuery:
        if not self._config.is_enabled_for(connector_name):
            return generic.translate(connector_name, requirement, raw_query, plan, self._config)

        strategy = _STRATEGIES.get(connector_name, generic.translate)
        return strategy(connector_name, requirement, raw_query, plan, self._config)
