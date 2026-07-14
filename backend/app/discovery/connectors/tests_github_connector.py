"""Tests for GitHubDiscoveryConnector -- Sprint 20B, extended in Sprint 20D
and Sprint 20E.

Exercises discover() against constructed HTTP responses via respx --
same approach the Greenhouse connector's own tests use -- rather than a
hand-rolled fake GitHubClient, so the whole real request/response path
(auth header, JSON shape, rate-limit handling) is covered.
"""
from __future__ import annotations

import httpx
import respx

from app.discovery.connectors.github_connector import GitHubDiscoveryConnector
from app.integrations.github.config import GitHubConfig, GitHubConfigStore
from app.integrations.github.intelligence.config import GitHubIntelligenceConfig
from app.search_planner.models import CanonicalJobRequirement


def _configured_store():
    store = GitHubConfigStore()
    store.set(GitHubConfig(personal_access_token="fake-pat"))
    return store


def test_not_available_when_unconfigured():
    connector = GitHubDiscoveryConnector(GitHubConfigStore())
    assert connector.is_available() is False
    assert connector.discover(CanonicalJobRequirement(role="Backend Engineer", skills=[])) == []


@respx.mock
def test_discover_finds_and_normalizes_matching_candidate():
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "octocat"}]})
    )
    respx.get("https://api.github.com/users/octocat").mock(
        return_value=httpx.Response(200, json={"login": "octocat", "name": "The Octocat", "location": "Remote"})
    )
    respx.get("https://api.github.com/users/octocat/repos").mock(
        return_value=httpx.Response(
            200, json=[{"name": "hello-world", "language": "Python", "fork": False, "stargazers_count": 3}]
        )
    )
    # Sprint 20D: discover() now also enriches each matched candidate via
    # GitHubEnrichmentEngine, which calls list_orgs() (always) and
    # get_readme() for the top-starred non-fork repos -- both need mocks
    # now, same as the pre-existing profile/repos calls above.
    respx.get("https://api.github.com/users/octocat/orgs").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://api.github.com/repos/octocat/hello-world/readme").mock(
        return_value=httpx.Response(200, text="# Hello World\nA sample FastAPI project.")
    )

    connector = GitHubDiscoveryConnector(_configured_store())
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=["Python"])
    results = connector.discover(requirement)

    assert len(results) == 1
    assert results[0].name == "The Octocat"
    assert "Python" in results[0].skills
    assert results[0].source_type == "github"
    # Sprint 20D: enrichment fields should now be populated additively.
    assert results[0].github_repositories_analyzed == 1
    assert results[0].github_quality_score is not None


@respx.mock
def test_discover_filters_out_candidates_missing_required_skills():
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "rubydev"}]})
    )
    respx.get("https://api.github.com/users/rubydev").mock(
        return_value=httpx.Response(200, json={"login": "rubydev"})
    )
    respx.get("https://api.github.com/users/rubydev/repos").mock(
        return_value=httpx.Response(200, json=[{"language": "Ruby", "fork": False}])
    )

    connector = GitHubDiscoveryConnector(_configured_store())
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=["Python"])
    results = connector.discover(requirement)

    assert results == []


@respx.mock
def test_discover_skips_a_user_whose_profile_lookup_fails():
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "ghost"}]})
    )
    respx.get("https://api.github.com/users/ghost").mock(return_value=httpx.Response(404, text="Not Found"))

    connector = GitHubDiscoveryConnector(_configured_store())
    results = connector.discover(CanonicalJobRequirement(role="Backend Engineer", skills=[]))

    assert results == []


@respx.mock
def test_discover_returns_empty_when_search_itself_fails():
    respx.get("https://api.github.com/search/users").mock(return_value=httpx.Response(422, text="bad query"))

    connector = GitHubDiscoveryConnector(_configured_store())
    results = connector.discover(CanonicalJobRequirement(role="Backend Engineer", skills=[]))

    assert results == []


# --- Sprint 20E regression tests: proven live bugs, now fixed ---------------
#
# Each test below reproduces, with mocked-but-realistic data, one of the
# six real recruiter queries that returned ZERO GitHub candidates when
# tested live against the deployed app (see GITHUB_LIVE_VALIDATION.md),
# and confirms the specific fix that makes each one now return a match.


@respx.mock
def test_discover_matches_golang_requirement_against_go_language_repo():
    """Live evidence: a real GitHub user (login 'evt') had a repo with
    language="Go" and description "Toptal home assignment for Senior
    Golang Engineer" -- a genuine Go developer that the pre-fix filter
    dropped because "golang" (the recruiter's skill token) != "go"
    (GitHub's own language spelling) under plain equality."""
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "evt"}]})
    )
    respx.get("https://api.github.com/users/evt").mock(
        return_value=httpx.Response(200, json={"login": "evt", "name": "Go Developer"})
    )
    respx.get("https://api.github.com/users/evt/repos").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "toptal-home-assignment",
                    "language": "Go",
                    "fork": False,
                    "description": "Toptal home assignment for Senior Golang Engineer",
                    "stargazers_count": 1,
                }
            ],
        )
    )
    respx.get("https://api.github.com/users/evt/orgs").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://api.github.com/repos/evt/toptal-home-assignment/readme").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    connector = GitHubDiscoveryConnector(_configured_store())
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=["Golang"])
    results = connector.discover(requirement)

    assert len(results) == 1
    assert results[0].name == "Go Developer"


@respx.mock
def test_discover_matches_react_requirement_via_topic_evidence_not_language():
    """Live evidence: 'React' is a real, recruiter-relevant skill that
    GitHub's repo `language` field can never report (React apps are
    still classified by language, e.g. JavaScript/TypeScript) -- the
    pre-fix filter, which only checked `language`, dropped every React
    developer. The fix checks SkillExtractor's topic-based evidence too."""
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "reactdev"}]})
    )
    respx.get("https://api.github.com/users/reactdev").mock(
        return_value=httpx.Response(200, json={"login": "reactdev", "name": "React Developer"})
    )
    respx.get("https://api.github.com/users/reactdev/repos").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "dashboard-ui",
                    "language": "JavaScript",
                    "fork": False,
                    "topics": ["react", "frontend"],
                    "stargazers_count": 5,
                }
            ],
        )
    )
    respx.get("https://api.github.com/users/reactdev/orgs").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://api.github.com/repos/reactdev/dashboard-ui/readme").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    connector = GitHubDiscoveryConnector(_configured_store())
    requirement = CanonicalJobRequirement(role="Senior React Developer", skills=["React"])
    results = connector.discover(requirement)

    assert len(results) == 1
    assert results[0].name == "React Developer"


@respx.mock
def test_discover_matches_pytorch_requirement_via_description_evidence():
    """Live evidence: 'PyTorch' (Machine Learning Engineer PyTorch query)
    is a Python library, never a repo `language` value -- same class of
    bug as React above, fixed the same way."""
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "mldev"}]})
    )
    respx.get("https://api.github.com/users/mldev").mock(
        return_value=httpx.Response(200, json={"login": "mldev", "name": "ML Engineer"})
    )
    respx.get("https://api.github.com/users/mldev/repos").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "image-classifier",
                    "language": "Python",
                    "fork": False,
                    "description": "PyTorch image classification model",
                    "stargazers_count": 12,
                }
            ],
        )
    )
    respx.get("https://api.github.com/users/mldev/orgs").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://api.github.com/repos/mldev/image-classifier/readme").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    connector = GitHubDiscoveryConnector(_configured_store())
    requirement = CanonicalJobRequirement(role="Machine Learning Engineer", skills=["PyTorch"])
    results = connector.discover(requirement)

    assert len(results) == 1
    assert results[0].name == "ML Engineer"


@respx.mock
def test_discover_still_filters_out_candidates_with_zero_evidence_after_fix():
    """The fix broadens what counts as evidence -- it must not become a
    rubber stamp. A candidate with no language/topic/name/description
    match for the required skill must still be excluded."""
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "unrelated"}]})
    )
    respx.get("https://api.github.com/users/unrelated").mock(
        return_value=httpx.Response(200, json={"login": "unrelated"})
    )
    respx.get("https://api.github.com/users/unrelated/repos").mock(
        return_value=httpx.Response(
            200, json=[{"name": "cooking-blog", "language": "HTML", "fork": False, "description": "My recipes"}]
        )
    )

    connector = GitHubDiscoveryConnector(_configured_store())
    requirement = CanonicalJobRequirement(role="AI Engineer", skills=["LangChain"])
    results = connector.discover(requirement)

    assert results == []


# --- Sprint 20F: fully dynamic evidence matching, zero fixed technology lists


@respx.mock
def test_discover_matches_a_job_title_never_seen_before_with_no_code_changes():
    """The whole point of Sprint 20F: this exact job title, and this exact
    technology ('ABAP'), appear nowhere in this codebase -- not in a
    skills table, not in a role taxonomy, not in a lookup dict anywhere.
    If this test passes, discovery works for arbitrary future queries
    without any source change, because the match is driven entirely by
    the recruiter's own query text against real GitHub evidence."""
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "abapdev"}]})
    )
    respx.get("https://api.github.com/users/abapdev").mock(
        return_value=httpx.Response(200, json={"login": "abapdev", "name": "SAP Consultant"})
    )
    respx.get("https://api.github.com/users/abapdev/repos").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "abap-cds-views",
                    "language": None,
                    "fork": False,
                    "description": "A collection of SAP ABAP CDS view examples",
                    "topics": ["sap", "abap"],
                }
            ],
        )
    )
    respx.get("https://api.github.com/users/abapdev/orgs").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://api.github.com/repos/abapdev/abap-cds-views/readme").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    connector = GitHubDiscoveryConnector(_configured_store())
    requirement = CanonicalJobRequirement(role="SAP ABAP Consultant", skills=["ABAP"])
    results = connector.discover(requirement)

    assert len(results) == 1
    assert results[0].name == "SAP Consultant"


@respx.mock
def test_discover_rejects_when_query_words_are_only_generic_role_noise():
    """A recruiter query whose only 'skill' words are generic seniority/
    role terms (which carry no technology signal and are stripped as
    noise) should not match every random repo just because a repo
    description happens to contain the word 'engineer'."""
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "someone"}]})
    )
    respx.get("https://api.github.com/users/someone").mock(
        return_value=httpx.Response(200, json={"login": "someone"})
    )
    respx.get("https://api.github.com/users/someone/repos").mock(
        return_value=httpx.Response(
            200,
            json=[{"name": "misc-scripts", "language": "Shell", "fork": False, "description": "random utility scripts"}],
        )
    )
    respx.get("https://api.github.com/users/someone/orgs").mock(return_value=httpx.Response(200, json=[]))

    connector = GitHubDiscoveryConnector(_configured_store())
    # "Quantum Computing Researcher" -- "Researcher" is noise, but
    # "Quantum" and "Computing" are real, specific query tokens with no
    # evidence in this candidate's repos, so this candidate is rejected.
    requirement = CanonicalJobRequirement(role="Quantum Computing Researcher", skills=[])
    results = connector.discover(requirement)

    assert results == []


# --- Sprint 20G: semantic evidence matching (primary), token fallback -------


class _FakeMatcher:
    """Test double for SemanticEvidenceMatcher -- lets a test dictate
    exactly which (requirement_text, evidence_text) pairs are "relevant"
    without invoking any real embedding model."""

    def __init__(self, relevant_evidence_substrings: list[str]):
        self._relevant_substrings = relevant_evidence_substrings

    def is_relevant(self, requirement_text, evidence_text):
        is_relevant = any(s in evidence_text for s in self._relevant_substrings)
        return is_relevant, 1.0 if is_relevant else 0.0


class _AlwaysUnavailableMatcher:
    """Simulates the embedding API being unreachable/unconfigured on
    every call -- the connector must fall back to Sprint 20F's literal
    token match rather than dropping every candidate."""

    def is_relevant(self, requirement_text, evidence_text):
        from app.integrations.github.intelligence.semantic_matcher import EmbeddingUnavailableError

        raise EmbeddingUnavailableError("simulated: no API key configured")


@respx.mock
def test_discover_uses_semantic_matcher_to_match_candidate_with_no_shared_words():
    """'Computer Vision' and a repo about 'YOLO OpenCV Detectron2' share
    zero literal words -- only a semantic comparison (not token overlap)
    can connect them. Proven here via an injected fake matcher standing
    in for the real embedding model."""
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "cvdev"}]})
    )
    respx.get("https://api.github.com/users/cvdev").mock(
        return_value=httpx.Response(200, json={"login": "cvdev", "name": "CV Engineer"})
    )
    respx.get("https://api.github.com/users/cvdev/repos").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "object-detector",
                    "language": "Python",
                    "fork": False,
                    "description": "YOLO OpenCV Detectron2 object detection pipeline",
                }
            ],
        )
    )
    respx.get("https://api.github.com/users/cvdev/orgs").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://api.github.com/repos/cvdev/object-detector/readme").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    fake_matcher = _FakeMatcher(relevant_evidence_substrings=["yolo"])
    connector = GitHubDiscoveryConnector(_configured_store(), semantic_matcher=fake_matcher)
    requirement = CanonicalJobRequirement(role="Computer Vision Engineer", skills=["Computer Vision"])
    results = connector.discover(requirement)

    assert len(results) == 1
    assert results[0].name == "CV Engineer"


@respx.mock
def test_discover_semantic_matcher_rejects_irrelevant_candidate():
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "unrelated"}]})
    )
    respx.get("https://api.github.com/users/unrelated").mock(
        return_value=httpx.Response(200, json={"login": "unrelated"})
    )
    respx.get("https://api.github.com/users/unrelated/repos").mock(
        return_value=httpx.Response(
            200, json=[{"name": "cooking-blog", "language": "HTML", "fork": False, "description": "My recipes"}]
        )
    )

    fake_matcher = _FakeMatcher(relevant_evidence_substrings=["yolo"])
    connector = GitHubDiscoveryConnector(_configured_store(), semantic_matcher=fake_matcher)
    requirement = CanonicalJobRequirement(role="Computer Vision Engineer", skills=["Computer Vision"])
    results = connector.discover(requirement)

    assert results == []


@respx.mock
def test_discover_falls_back_to_token_match_when_semantic_matcher_unavailable():
    """Availability must never depend on the embedding API succeeding --
    when it's unavailable, the connector must still return candidates it
    can prove relevant via literal evidence, not silently return nothing."""
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": [{"login": "godev"}]})
    )
    respx.get("https://api.github.com/users/godev").mock(
        return_value=httpx.Response(200, json={"login": "godev", "name": "Go Developer"})
    )
    respx.get("https://api.github.com/users/godev/repos").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "golang-service",
                    "language": "Go",
                    "fork": False,
                    "description": "A Golang microservice",
                }
            ],
        )
    )
    respx.get("https://api.github.com/users/godev/orgs").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://api.github.com/repos/godev/golang-service/readme").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    connector = GitHubDiscoveryConnector(_configured_store(), semantic_matcher=_AlwaysUnavailableMatcher())
    requirement = CanonicalJobRequirement(role="Senior Golang Developer", skills=["Golang"])
    results = connector.discover(requirement)

    assert len(results) == 1
    assert results[0].name == "Go Developer"


# --- Sprint 20H: the search result window is a configurable tunable, not
# a hardcoded module constant. See docs/SILENT_FAILURE_AUDIT.md finding #2.


@respx.mock
def test_discover_honors_a_configured_max_search_results_smaller_than_default():
    """GitHub's Search Users API can return thousands of matches (e.g.
    total_count 1729 for "golang", live-confirmed) -- this test proves
    the connector actually passes GitHubIntelligenceConfig.max_search_results
    through to the search call's `per_page`, rather than always using the
    old hardcoded value of 10."""
    search_route = respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    config = GitHubIntelligenceConfig(max_search_results=3)
    connector = GitHubDiscoveryConnector(_configured_store(), intelligence_config=config)
    connector.discover(CanonicalJobRequirement(role="Backend Engineer", skills=["Python"]))

    assert search_route.calls.last.request.url.params["per_page"] == "3"


@respx.mock
def test_discover_honors_a_configured_max_search_results_larger_than_default():
    """The inverse case -- proves the cap can be raised, not just lowered,
    confirming this is a real tunable and not a disguised hardcoded max."""
    search_route = respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    config = GitHubIntelligenceConfig(max_search_results=50)
    connector = GitHubDiscoveryConnector(_configured_store(), intelligence_config=config)
    connector.discover(CanonicalJobRequirement(role="Backend Engineer", skills=["Python"]))

    assert search_route.calls.last.request.url.params["per_page"] == "50"


# --- Sprint 32: runtime 401 marks the credential store invalid --------------


@respx.mock
def test_discover_marks_credential_store_error_on_401():
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(401, json={"message": "Bad credentials"})
    )

    store = _configured_store()
    connector = GitHubDiscoveryConnector(store)
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=["Python"])

    results = connector.discover(requirement)

    assert results == []
    status = store.get_status()
    assert status["status"] == "invalid"
    assert "401" in status["last_error"]


@respx.mock
def test_discover_does_not_mark_error_on_non_401_search_failure():
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(422, json={"message": "Validation failed"})
    )

    store = _configured_store()
    connector = GitHubDiscoveryConnector(store)
    requirement = CanonicalJobRequirement(role="Backend Engineer", skills=["Python"])

    results = connector.discover(requirement)

    assert results == []
    # A malformed query (422) isn't a token problem -- shouldn't be
    # reported as one.
    assert store.get_status()["status"] != "invalid"
