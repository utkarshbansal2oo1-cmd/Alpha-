"""The Discovery Connector contract -- Sprint 18.

Every connected/authorized source the Discovery Orchestrator can pull
candidates from implements this one interface. The Discovery Engine knows
nothing about connector internals: it only calls discover(requirement)
and gets back CandidateImportRequest objects -- the same permissive shape
the browser extension and Greenhouse connector already produce (see
app/candidate_repository/import_schemas.py). This is the seam that keeps
every connector's implementation detail (an HTTP client, a file parser, a
database query) fully swappable and testable in isolation, and is what
lets the Discovery Engine stay 100% connector-driven rather than knowing
about Greenhouse, CSV files, or anything else specifically.

Per the sprint's explicit rules, a connector must ONLY read from a source
it already has legitimate, authorized access to -- it must never scrape a
website directly, bypass authentication, or attempt to defeat anti-bot
systems. Nothing in this interface makes that possible: discover() takes
a requirement and returns structured candidate data, nothing else.
"""
from __future__ import annotations

from typing import Protocol

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.search_planner.models import CanonicalJobRequirement


class DiscoveryConnector(Protocol):
    """Structural interface (a Protocol, not an ABC) -- a connector only
    needs to match this shape, with no import-time coupling to this
    module required."""

    name: str
    priority: int

    def is_available(self) -> bool:
        """Whether this connector is actually configured/reachable right
        now (e.g. a Greenhouse API key is set). The orchestrator records
        unavailable connectors as 'not connected' rather than treating
        them as errors, and does not call discover() on them."""
        ...

    def discover(self, requirement: CanonicalJobRequirement) -> list[CandidateImportRequest]:
        """Returns candidates from this connector's source that plausibly
        match the requirement. An empty list is a valid, expected
        outcome -- 'this source has nothing new to offer' -- not an
        error."""
        ...
