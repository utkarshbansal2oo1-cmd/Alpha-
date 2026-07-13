"""Placeholder Discovery Connectors -- Sprint 18.

Covers the sources the sprint brief lists as in-scope but that don't yet
have a live, requirement-filterable intake queue to read from: Resume
uploads, CSV imports, and an internal HRMS/Talent Database. Each
implements the same DiscoveryConnector interface as
GreenhouseDiscoveryConnector, so wiring a real one in later (e.g. once a
resume-upload endpoint exists) is a drop-in replacement, not a redesign
of the Discovery Engine itself.

Honesty note: these intentionally report themselves as not-yet-connected
(is_available() -> False) rather than silently returning an empty list
that looks identical to "searched and found nothing" -- the Discovery
Orchestrator surfaces this distinction to the recruiter (see
ConnectorRunResult.configured), which matters because "we haven't
connected your resume inbox yet" and "we checked and there's nothing
there" are very different, actionable pieces of information.

The Browser Extension is a special case, not a future connector: any
candidate captured through it is already written straight into the
Candidate Repository via POST /candidate/import (see
app/routers/candidate_import.py), and is therefore already part of the
very first repository.search() call this pipeline makes -- there is no
separate "pending browser capture" queue sitting outside the repository
for a connector to go discover. BrowserExtensionDiscoveryConnector exists
for interface completeness (so the sprint's priority-ordering example has
something concrete to point at in the UI's progress list) and reports
zero *new* candidates by design, since nothing is actually queued up
outside the repository already searched in step one.
"""
from __future__ import annotations

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.search_planner.models import CanonicalJobRequirement


class _NotYetConnectedConnector:
    name = "unset"
    priority = 100

    def is_available(self) -> bool:
        return False

    def discover(self, requirement: CanonicalJobRequirement) -> list[CandidateImportRequest]:
        return []


class BrowserExtensionDiscoveryConnector(_NotYetConnectedConnector):
    """See module docstring: browser-captured candidates are already in
    the Candidate Repository by the time discovery runs, so this
    connector's discover() is a documented no-op, not an unfinished
    integration -- hence is_available() is True (the source is real and
    already flowing data in) even though there is nothing left for this
    specific connector to fetch."""

    name = "browser_extension"
    priority = 20

    def is_available(self) -> bool:
        return True


class CsvImportDiscoveryConnector(_NotYetConnectedConnector):
    name = "csv_import"
    priority = 30


class ResumeImportDiscoveryConnector(_NotYetConnectedConnector):
    name = "resume_import"
    priority = 40


class HrmsDiscoveryConnector(_NotYetConnectedConnector):
    name = "internal_hrms"
    priority = 50


# --- Sprint 20A: expose these stub connectors to the new Universal
# Connector Framework, purely additive (the classes above are untouched).
# Their honesty principle (is_available()/status() report the real
# not-yet-connected state) flows straight through the legacy adapter.
from app.discovery.connectors.framework import ConnectorMetadata  # noqa: E402
from app.discovery.connectors.legacy_adapter import LegacyConnectorAdapter  # noqa: E402

_BROWSER_EXTENSION = BrowserExtensionDiscoveryConnector()
_CSV_IMPORT = CsvImportDiscoveryConnector()
_RESUME_IMPORT = ResumeImportDiscoveryConnector()
_HRMS = HrmsDiscoveryConnector()

MANAGED_CONNECTOR = LegacyConnectorAdapter(
    wrapped=_BROWSER_EXTENSION,
    metadata=ConnectorMetadata(
        name="browser_extension",
        version="1.0.0",
        capabilities=["candidate_capture"],
        requires_auth=False,
        supported_roles=[],
        enabled=True,
    ),
)

MANAGED_CSV_IMPORT_CONNECTOR = LegacyConnectorAdapter(
    wrapped=_CSV_IMPORT,
    metadata=ConnectorMetadata(
        name="csv_import",
        version="0.1.0",
        capabilities=["bulk_import"],
        requires_auth=False,
        supported_roles=[],
        enabled=True,
    ),
)

MANAGED_RESUME_IMPORT_CONNECTOR = LegacyConnectorAdapter(
    wrapped=_RESUME_IMPORT,
    metadata=ConnectorMetadata(
        name="resume_import",
        version="0.1.0",
        capabilities=["resume_parsing"],
        requires_auth=False,
        supported_roles=[],
        enabled=True,
    ),
)

MANAGED_HRMS_CONNECTOR = LegacyConnectorAdapter(
    wrapped=_HRMS,
    metadata=ConnectorMetadata(
        name="internal_hrms",
        version="0.1.0",
        capabilities=["candidate_search"],
        requires_auth=True,
        supported_roles=[],
        enabled=True,
    ),
)
