"""Tests for the Discovery Orchestrator -- Sprint 18."""
from __future__ import annotations

from app.candidate_repository.import_schemas import CandidateImportRequest
from app.candidate_repository.memory_repository import InMemoryCandidateRepository
from app.candidate_repository.normalizer import normalize_import
from app.discovery.decision_engine import DiscoveryDecisionEngine
from app.discovery.orchestrator import DiscoveryOrchestrator
from app.search_planner.models import CanonicalJobRequirement, SearchPlan


def _plan(search_terms: list[str]) -> SearchPlan:
    return SearchPlan(strict=[], expanded=[], search_terms=search_terms, weights={}, unresolved=[])


def _repo(tmp_path):
    seed = tmp_path / "candidates.json"
    seed.write_text("[]", encoding="utf-8")
    return InMemoryCandidateRepository(seed_path=seed)


class FakeConnector:
    def __init__(self, name, priority, available, results):
        self.name = name
        self.priority = priority
        self._available = available
        self._results = results
        self.discover_calls = 0

    def is_available(self):
        return self._available

    def discover(self, requirement):
        self.discover_calls += 1
        return self._results


class FailingConnector:
    name = "broken_source"
    priority = 5

    def is_available(self):
        return True

    def discover(self, requirement):
        raise RuntimeError("upstream is down")


def test_orchestrator_skips_discovery_when_decision_engine_says_sufficient(tmp_path):
    repo = _repo(tmp_path)
    connector = FakeConnector("ats", 10, True, [])
    orchestrator = DiscoveryOrchestrator(
        connectors=[connector],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=0, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="Product Engineer", skills=[])
    run, candidates = orchestrator.run(requirement, _plan([]), existing_candidates=[])

    assert run.triggered is False
    assert connector.discover_calls == 0
    assert candidates == []


def test_orchestrator_runs_connectors_in_priority_order_and_imports_candidates(tmp_path):
    repo = _repo(tmp_path)
    call_order = []

    class OrderTrackingConnector(FakeConnector):
        def discover(self, requirement):
            call_order.append(self.name)
            return super().discover(requirement)

    low_priority = OrderTrackingConnector(
        "slow_source",
        50,
        True,
        [CandidateImportRequest(name="Late Bloomer", role="Product Engineer", skills=["AWS"], source_type="slow_source")],
    )
    high_priority = OrderTrackingConnector(
        "fast_source",
        10,
        True,
        [CandidateImportRequest(name="Early Bird", role="Product Engineer", skills=["AWS"], source_type="fast_source")],
    )

    orchestrator = DiscoveryOrchestrator(
        connectors=[low_priority, high_priority],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="Product Engineer", skills=["AWS"])
    plan = _plan(["Product Engineer", "AWS"])

    run, candidates = orchestrator.run(requirement, plan, existing_candidates=[])

    assert call_order == ["fast_source", "slow_source"]
    assert run.triggered is True
    assert run.new_candidates_imported == 2
    names = {c.name for c in candidates}
    assert names == {"Early Bird", "Late Bloomer"}


def test_orchestrator_records_unavailable_connectors_without_calling_discover(tmp_path):
    repo = _repo(tmp_path)
    connector = FakeConnector("not_configured", 10, False, [])
    orchestrator = DiscoveryOrchestrator(
        connectors=[connector],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="X", skills=[])
    run, _ = orchestrator.run(requirement, _plan([]), existing_candidates=[])

    assert connector.discover_calls == 0
    result = next(r for r in run.connector_results if r.source_name == "not_configured")
    assert result.configured is False
    assert result.attempted is False


def test_orchestrator_isolates_a_failing_connector(tmp_path):
    repo = _repo(tmp_path)
    working = FakeConnector(
        "backup_source",
        20,
        True,
        [CandidateImportRequest(name="Survivor", role="X", skills=[], source_type="backup_source")],
    )
    orchestrator = DiscoveryOrchestrator(
        connectors=[FailingConnector(), working],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="X", skills=[])
    run, candidates = orchestrator.run(requirement, _plan([]), existing_candidates=[])

    broken_result = next(r for r in run.connector_results if r.source_name == "broken_source")
    assert broken_result.error == "upstream is down"
    assert any(c.name == "Survivor" for c in candidates)


def test_orchestrator_deduplicates_against_existing_candidates(tmp_path):
    repo = _repo(tmp_path)
    existing_request = CandidateImportRequest(
        name="Priya Singh",
        current_company="Acme Cloud",
        role="Backend Engineer",
        skills=["Go"],
        source_type="seed_data",
    )
    repo.upsert(normalize_import(existing_request))

    connector = FakeConnector(
        "ats",
        10,
        True,
        [
            CandidateImportRequest(
                name="Priya Singh",
                current_company="Acme Cloud",
                role="Backend Engineer",
                skills=["Terraform"],
                source_type="ats",
            )
        ],
    )
    orchestrator = DiscoveryOrchestrator(
        connectors=[connector],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=[])
    run, candidates = orchestrator.run(requirement, _plan([]), existing_candidates=[])

    matching = [c for c in candidates if c.name == "Priya Singh"]
    assert len(matching) == 1
    assert set(matching[0].skills) == {"Go", "Terraform"}
    result = next(r for r in run.connector_results if r.source_name == "ats")
    assert result.candidates_merged == 1
    assert result.candidates_imported == 0


# --- Sprint 20H: discovery must happen exactly once -- no second,
# implicit, literal-match search stage after connectors already found and
# imported real candidates. See docs/SILENT_FAILURE_AUDIT.md finding #1.


def test_orchestrator_returns_connector_candidate_whose_fields_dont_literally_match_the_plan(tmp_path):
    """Reproduces the exact bug this sprint fixes: a connector (like the
    real GitHub connector) discovers and imports a candidate whose
    normalized `role`/`skills` fields don't literally match the plan's
    search terms (a GitHub candidate's role defaults to "Unknown" and
    its skills come from repo languages, e.g. "Go" instead of the
    recruiter's own wording "Golang"). Before the Sprint 20H fix, the
    orchestrator's second `repository.search(plan)` call would silently
    drop this exact candidate from the response, even though the
    connector had already correctly found and imported them."""
    repo = _repo(tmp_path)
    connector = FakeConnector(
        "github",
        15,
        True,
        [
            CandidateImportRequest(
                name="Gopher Dev",
                role="Unknown",
                skills=["Go"],
                source_type="github",
            )
        ],
    )
    orchestrator = DiscoveryOrchestrator(
        connectors=[connector],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=["Golang"])
    # A literal-match plan that a real Query Understanding pass would
    # build from the recruiter's own wording -- note it shares zero
    # literal words with the candidate's role="Unknown"/skills=["Go"].
    plan = _plan(["Senior Golang Developer", "Golang"])

    run, candidates = orchestrator.run(requirement, plan, existing_candidates=[])

    assert run.new_candidates_imported == 1
    assert any(c.name == "Gopher Dev" for c in candidates)


def test_orchestrator_never_calls_repository_search_during_a_triggered_run(tmp_path):
    """Direct guard against the regression this sprint fixes: the
    repository's search() must never be invoked as a second, implicit
    discovery-filtering stage after connectors have already run."""
    repo = _repo(tmp_path)
    search_calls = []
    original_search = repo.search

    def _tracking_search(plan):
        search_calls.append(plan)
        return original_search(plan)

    repo.search = _tracking_search

    connector = FakeConnector(
        "github",
        15,
        True,
        [CandidateImportRequest(name="Gopher Dev", role="Unknown", skills=["Go"], source_type="github")],
    )
    orchestrator = DiscoveryOrchestrator(
        connectors=[connector],
        repository=repo,
        decision_engine=DiscoveryDecisionEngine(min_result_threshold=5, min_confidence_threshold=0),
    )
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=["Golang"])
    plan = _plan(["Senior Golang Developer", "Golang"])

    orchestrator.run(requirement, plan, existing_candidates=[])

    assert search_calls == []
