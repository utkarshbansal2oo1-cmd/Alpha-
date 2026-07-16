"""The Discovery Orchestrator -- Sprint 18/19/20C.

Runs connected-source connectors in priority order when the Discovery
Decision Engine determines the existing Candidate Repository results
aren't good enough, imports whatever new candidates they find through the
exact same CandidateImportRequest -> normalize_import() -> upsert() seam
every other capture path already uses (browser extension, Greenhouse
sync -- see app/routers/candidate_import.py), then re-runs the search so
the recruiter gets a refreshed result set in one round trip.

Nothing here touches Query Understanding, the Knowledge Engine, the
Search Planner, the Candidate Intelligence Lifecycle, the Matching/
Ranking Engines, the DiscoveryConnector interface, or any individual
connector's own implementation -- it only calls their existing public
seams. The Candidate Intelligence Lifecycle (health/confidence/evidence/
version) already runs automatically inside repository.upsert() for every
imported candidate -- the orchestrator does not (and must not) call it
directly.

Sprint 20C addition: an optional `query_translator` (Connector
Intelligence Layer, app/discovery/query_translation/) and `raw_query`
argument to `run()`. Both default to None, which preserves the exact
Sprint 18/19/20B behavior (and every one of those sprints' tests)
unchanged: one discover(requirement) call per connector. When a
translator IS supplied, each connector's translated ConnectorQuery
decides what happens:

  - `is_passthrough` True (Greenhouse, browser extension, generic
    fallback, and any connector with no dedicated strategy) -- exactly
    one discover(requirement) call, with the ORIGINAL, untouched
    requirement, same as always.
  - `is_passthrough` False (GitHub) -- one discover() call per
    translated search expression, each against a small synthetic
    CanonicalJobRequirement built from that expression, then the
    results are deduplicated (app.discovery.query_translation.dedup)
    before import -- still through the exact same
    normalize_import()/upsert() seam as every other path.

No connector's own discover(requirement) signature or implementation is
touched by this -- the orchestrator is simply choosing how many times,
and with what requirement, to call the one method every connector has
always exposed.

Sprint 20H fix: the final candidate set used to come from a SECOND
repository.search(plan) call after every connector had already run and
imported its finds. That second search re-applies literal role/skill
matching against the ORIGINAL plan (the search terms Query Understanding
derived before any connector ran) -- so a connector-discovered candidate
whose `role`/`skills` fields don't literally match that plan's terms
(e.g. a GitHub candidate with role="Unknown", skills=["Go"] against a
plan searching for "Golang") was silently dropped from the response,
even though the connector (and Sprint 20E-20G's evidence-based relevance
checks) had already correctly identified them as a match. See
docs/SILENT_FAILURE_AUDIT.md finding #1.

The repository is storage/dedup/analytics -- not a second search stage.
Discovery happens exactly once, in each connector's own discover() call.
The orchestrator now builds the final candidate set directly from that:
seeded with `existing_candidates` (the one legitimate pre-discovery
search the caller already did), then updated in place with the exact
Candidate object `repository.upsert()` returns for every
connector-discovered import (already the correctly merged/created
record, with the right id/skills/version -- previously computed and
then thrown away). No second `repository.search()` call is made after
discovery runs.
"""
from __future__ import annotations

import logging
import time

from app.candidate_repository.interfaces import CandidateRepository
from app.candidate_repository.models import Candidate
from app.candidate_repository.normalizer import normalize_import
from app.discovery.connectors.base import DiscoveryConnector
from app.discovery.decision_engine import DiscoveryDecisionEngine
from app.discovery.models import ConnectorRunResult, DiscoveryRun, DiscoveryStage
from app.search_planner.models import CanonicalJobRequirement, SearchPlan

logger = logging.getLogger(__name__)


class DiscoveryOrchestrator:
    def __init__(
        self,
        connectors,  # list[DiscoveryConnector] | ConnectorRegistry (Sprint 19: duck-typed, see below)
        repository: CandidateRepository,
        decision_engine: DiscoveryDecisionEngine,
    ):
        # Sprint 19: `connectors` may now be a ConnectorRegistry (which
        # already returns its connectors in priority order via
        # get_all()) instead of a plain list -- kept duck-typed rather
        # than importing ConnectorRegistry here, to avoid a new import
        # cycle and to keep every Sprint 18 caller/test (which passes a
        # plain list) working unchanged.
        if hasattr(connectors, "get_all"):
            self._connectors: list[DiscoveryConnector] = connectors.get_all()
        else:
            # Lower priority number runs first, per the sprint's "Execute
            # connectors in priority order" responsibility.
            self._connectors = sorted(connectors, key=lambda c: c.priority)
        self._repository = repository
        self._decision_engine = decision_engine

    def _discover_for_connector(self, connector, requirement, raw_query, plan, query_translator):
        """Returns (found_import_requests, duplicate_count, query_log).
        Isolated so run() stays readable; the branch is purely additive --
        with no translator, this is byte-for-byte the Sprint 18 behavior."""
        if query_translator is None:
            return connector.discover(requirement), 0, [requirement.role]

        connector_query = query_translator.translate(connector.name, requirement, raw_query, plan)

        if connector_query.is_passthrough:
            return connector.discover(requirement), 0, connector_query.connector_queries

        # Non-passthrough (currently: GitHub) -- run one discover() call
        # per translated search expression, against a synthetic
        # requirement carrying that expression as its role, then merge
        # and deduplicate before returning.
        #
        # This-sprint fix: a single recruiter query like "Zig systems
        # programmer" can translate into 8+ separate GitHub search
        # expressions (see query_translation/). Each discover() call is
        # entirely I/O-bound (GitHub REST calls + Gemini embedding calls,
        # no shared mutable state -- each call builds its own GitHubClient
        # instance), so running them sequentially made total wall-clock
        # time the SUM of every sub-query (live-observed: 547s / ~9min for
        # 8 sub-queries on one search). Running them concurrently on a
        # thread pool means wall-clock time is closer to the SLOWEST
        # single sub-query instead -- same total API calls, same results,
        # much less waiting. Bounded to avoid hammering GitHub with more
        # simultaneous requests than there are sub-queries anyway.
        #
        # Known limitation: GitHubDiscoveryConnector.discover() also
        # writes self.last_discovery_stats as a side effect for the
        # orchestrator's logging/ConnectorRunResult -- with concurrent
        # calls on the same connector instance, whichever call finishes
        # last "wins" that dict, same as it already only ever reflected
        # the last of several sequential sub-queries before this change.
        # Not aggregated across sub-queries either way; harmless for its
        # only consumer (diagnostic logging), not correctness.
        from concurrent.futures import ThreadPoolExecutor

        from app.discovery.query_translation.dedup import deduplicate_import_requests

        query_texts = connector_query.connector_queries
        all_found = []
        if len(query_texts) <= 1:
            for query_text in query_texts:
                synthetic_requirement = CanonicalJobRequirement(role=query_text, skills=[])
                all_found.extend(connector.discover(synthetic_requirement))
        else:
            with ThreadPoolExecutor(max_workers=min(len(query_texts), 8)) as pool:
                futures = [
                    pool.submit(connector.discover, CanonicalJobRequirement(role=query_text, skills=[]))
                    for query_text in query_texts
                ]
                for future in futures:
                    all_found.extend(future.result())

        deduped, duplicate_count = deduplicate_import_requests(all_found)
        return deduped, duplicate_count, connector_query.connector_queries

    def run(
        self,
        requirement: CanonicalJobRequirement,
        plan: SearchPlan,
        existing_candidates: list[Candidate],
        match_results=None,  # Sprint 19: list[MatchResult] | None -- see decision_engine.evaluate()
        query_translator=None,  # Sprint 20C: ConnectorQueryTranslator | None
        raw_query: str | None = None,  # Sprint 20C: the recruiter's original search text
    ) -> tuple[DiscoveryRun, list[Candidate]]:
        decision = self._decision_engine.evaluate(existing_candidates, plan, match_results=match_results)

        stages: list[DiscoveryStage] = [
            DiscoveryStage(
                label="Searching internal talent intelligence...",
                detail=decision.reason,
                count=decision.candidate_count,
            )
        ]

        if not decision.should_discover:
            run = DiscoveryRun(triggered=False, decision=decision, stages=stages)
            return run, existing_candidates

        connector_results: list[ConnectorRunResult] = []
        total_imported = 0

        # Sprint 20H: the final result set is built directly from
        # existing_candidates + whatever each connector discovers this
        # run, keyed by id so a candidate merged by the repository (same
        # id, updated fields) overwrites its earlier entry rather than
        # duplicating it. This dict is never rebuilt from a
        # repository.search() call -- see module docstring.
        candidates_by_id: dict[str, Candidate] = {c.id: c for c in existing_candidates}

        for connector in self._connectors:
            if not connector.is_available():
                connector_results.append(
                    ConnectorRunResult(source_name=connector.name, attempted=False, configured=False)
                )
                stages.append(
                    DiscoveryStage(label=f"Skipping {connector.name} -- not connected.")
                )
                continue

            started_at = time.monotonic()
            try:
                found, duplicate_count, translated_queries = self._discover_for_connector(
                    connector, requirement, raw_query, plan, query_translator
                )
            except Exception as exc:  # noqa: BLE001 -- one connector failing must not fail the whole run
                connector_results.append(
                    ConnectorRunResult(source_name=connector.name, candidates_found=0, error=str(exc))
                )
                stages.append(
                    DiscoveryStage(label=f"Searching {connector.name}...", detail=f"error: {exc}", count=0)
                )
                continue
            elapsed_ms = round((time.monotonic() - started_at) * 1000, 1)

            logger.info(
                "discovery.connector_query",
                extra={
                    "original_query": raw_query or requirement.role,
                    "connector": connector.name,
                    "translated_queries": translated_queries,
                    "candidates_found": len(found),
                    "duplicates_removed": duplicate_count,
                    "elapsed_ms": elapsed_ms,
                },
            )

            imported = 0
            merged = 0
            for import_request in found:
                candidate = normalize_import(import_request)
                existing_match = self._repository.find_potential_duplicate(candidate)
                stored = self._repository.upsert(candidate)
                # Sprint 20H: capture the persisted record directly into
                # the final result set here -- this connector already
                # discovered and (via the evidence-based relevance checks
                # inside its own discover()) judged this candidate
                # relevant. No later re-search is allowed to un-discover
                # them.
                candidates_by_id[stored.id] = stored
                if existing_match is None:
                    imported += 1
                else:
                    merged += 1

            total_imported += imported
            # Sprint 34: a connector MAY expose a `last_discovery_stats`
            # dict (e.g. GitHubDiscoveryConnector, after a multi-page
            # fetch) with keys matching ConnectorRunResult's own optional
            # discovery-stat fields exactly. Duck-typed via getattr rather
            # than added to the DiscoveryConnector interface, so every
            # other connector (Greenhouse, the Sprint 18 stubs) is
            # completely untouched and this stays purely additive.
            discovery_stats = getattr(connector, "last_discovery_stats", None) or {}
            connector_results.append(
                ConnectorRunResult(
                    source_name=connector.name,
                    candidates_found=len(found),
                    candidates_imported=imported,
                    candidates_merged=merged,
                    **discovery_stats,
                )
            )
            detail = f"{imported} new, {merged} matched existing records" if found else "no matching candidates"
            if duplicate_count:
                detail += f" ({duplicate_count} cross-query duplicates removed)"
            stages.append(
                DiscoveryStage(
                    label=f"Searching {connector.name}...",
                    detail=detail,
                    count=len(found),
                )
            )

        stages.append(DiscoveryStage(label="Updating candidate intelligence..."))

        # Sprint 20H: no second repository.search(plan) call here anymore
        # -- see module docstring and docs/SILENT_FAILURE_AUDIT.md finding
        # #1. The final set is exactly existing_candidates unioned with
        # everything every connector discovered and this run persisted.
        refreshed_candidates = list(candidates_by_id.values())

        stages.append(
            DiscoveryStage(label="Generating final shortlist...", count=len(refreshed_candidates))
        )

        run = DiscoveryRun(
            triggered=True,
            decision=decision,
            connector_results=connector_results,
            new_candidates_imported=total_imported,
            stages=stages,
        )
        return run, refreshed_candidates
