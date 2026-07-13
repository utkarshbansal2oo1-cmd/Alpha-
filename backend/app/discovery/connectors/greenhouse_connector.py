"""Greenhouse-backed Discovery Connector -- Sprint 18.

Wraps the existing, unmodified GreenhouseClient
(app/integrations/greenhouse/client.py) and normalize_greenhouse_candidate
(app/integrations/greenhouse/normalizer.py) -- this connector adds
requirement-driven filtering on top of them, but does not change either
module. It only runs if a Greenhouse API key has already been configured
via POST /integrations/greenhouse/configure (see
app/integrations/greenhouse/config.py): every candidate this connector
returns came from a real Greenhouse Harvest API response the recruiter's
own connected account is authorized to read. This is connected-source
discovery, not scraping.
"""
from __future__ import annotations

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.integrations.greenhouse.client import GreenhouseAPIError, GreenhouseClient
from app.integrations.greenhouse.config import GreenhouseConfigStore
from app.integrations.greenhouse.normalizer import normalize_greenhouse_candidate
from app.search_planner.models import CanonicalJobRequirement

# This is a live-search feature, not a bulk sync (that's pull_sync's job
# in app/integrations/greenhouse/sync.py) -- cap how many raw candidates
# we page through per discovery call so it stays fast.
_DISCOVERY_PAGE_LIMIT = 100


class GreenhouseDiscoveryConnector:
    name = "greenhouse_ats"
    priority = 10  # Runs before the lower-priority connectors in connectors/future_connectors.py.

    def __init__(self, config_store: GreenhouseConfigStore):
        self._config_store = config_store

    def is_available(self) -> bool:
        return self._config_store.is_configured()

    def discover(self, requirement: CanonicalJobRequirement) -> list[CandidateImportRequest]:
        if not self.is_available():
            return []

        config = self._config_store.get()
        client = GreenhouseClient(config)
        try:
            raw_candidates = client.list_candidates(per_page=_DISCOVERY_PAGE_LIMIT)
        finally:
            client.close()

        terms = {requirement.role.strip().lower()} | {s.strip().lower() for s in requirement.skills}
        terms = {t for t in terms if t}

        matches: list[CandidateImportRequest] = []
        for raw in raw_candidates:
            haystack = " ".join(
                str(v) for v in [raw.get("title"), raw.get("company"), *raw.get("tags", [])] if v
            ).lower()
            if any(term in haystack for term in terms):
                matches.append(normalize_greenhouse_candidate(raw))

        return matches


# --- Sprint 20A: expose this connector to the new Universal Connector
# Framework (app/discovery/connectors/framework.py) via the legacy
# adapter, so it shows up in GET /connectors alongside any future
# connector built directly against the new interface -- purely additive,
# the class above is completely untouched. Uses the same module-level
# config store singleton get_greenhouse_config_store() already provides.
from app.discovery.connectors.framework import ConnectorMetadata  # noqa: E402
from app.discovery.connectors.legacy_adapter import LegacyConnectorAdapter  # noqa: E402
from app.integrations.greenhouse.config import get_greenhouse_config_store  # noqa: E402

MANAGED_CONNECTOR = LegacyConnectorAdapter(
    wrapped=GreenhouseDiscoveryConnector(get_greenhouse_config_store()),
    metadata=ConnectorMetadata(
        name="greenhouse_ats",
        version="1.0.0",
        capabilities=["candidate_search"],
        requires_auth=True,
        supported_roles=[],
        enabled=True,
    ),
)
