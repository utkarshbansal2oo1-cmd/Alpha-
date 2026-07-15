"""Tests for GitHubClient -- Sprint 20B, extended in Sprint 20D. Exercises
constructed HTTP responses shaped like GitHub's real documented payloads
via respx, same tooling/approach as tests_greenhouse.py uses for
GreenhouseClient."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.integrations.github.client import GitHubAPIError, GitHubClient
from app.integrations.github.config import GitHubConfig


def _client():
    return GitHubClient(GitHubConfig(personal_access_token="fake-pat"))


@respx.mock
def test_search_users_returns_items_array():
    respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"total_count": 1, "items": [{"login": "octocat"}]})
    )
    # Sprint 34: now returns (items, total_count) so multi-page discovery
    # can tell whether more results exist without an extra request.
    users, total_count = _client().search_users("octocat type:user")
    assert users == [{"login": "octocat"}]
    assert total_count == 1


@respx.mock
def test_search_users_passes_page_param_for_pagination():
    route = respx.get("https://api.github.com/search/users").mock(
        return_value=httpx.Response(200, json={"total_count": 0, "items": []})
    )
    _client().search_users("octocat type:user", per_page=50, page=3)
    assert route.calls.last.request.url.params["page"] == "3"
    assert route.calls.last.request.url.params["per_page"] == "50"


@respx.mock
def test_get_user_returns_profile():
    respx.get("https://api.github.com/users/octocat").mock(
        return_value=httpx.Response(200, json={"login": "octocat", "name": "The Octocat"})
    )
    profile = _client().get_user("octocat")
    assert profile["name"] == "The Octocat"


@respx.mock
def test_list_repos_returns_repo_list():
    respx.get("https://api.github.com/users/octocat/repos").mock(
        return_value=httpx.Response(200, json=[{"name": "Hello-World", "language": "Python", "fork": False}])
    )
    repos = _client().list_repos("octocat")
    assert repos[0]["language"] == "Python"


@respx.mock
def test_non_rate_limit_error_raises_github_api_error():
    respx.get("https://api.github.com/users/ghost").mock(return_value=httpx.Response(404, text="Not Found"))
    with pytest.raises(GitHubAPIError) as exc_info:
        _client().get_user("ghost")
    assert exc_info.value.status_code == 404


@respx.mock
def test_rate_limit_response_retries_once_and_succeeds():
    route = respx.get("https://api.github.com/users/octocat")
    route.side_effect = [
        httpx.Response(
            403,
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "0"},
            text="rate limited",
        ),
        httpx.Response(200, json={"login": "octocat"}),
    ]
    profile = _client().get_user("octocat")
    assert profile["login"] == "octocat"
    assert route.call_count == 2


# --- Sprint 20D additions: list_orgs / get_readme ---------------------------


@respx.mock
def test_list_orgs_returns_org_list():
    respx.get("https://api.github.com/users/octocat/orgs").mock(
        return_value=httpx.Response(200, json=[{"login": "octo-org", "type": "Organization"}])
    )
    orgs = _client().list_orgs("octocat")
    assert orgs == [{"login": "octo-org", "type": "Organization"}]


@respx.mock
def test_get_readme_returns_raw_text():
    respx.get("https://api.github.com/repos/octocat/hello-world/readme").mock(
        return_value=httpx.Response(200, text="# Hello World\nSample project.")
    )
    text = _client().get_readme("octocat", "hello-world")
    assert text.startswith("# Hello World")


@respx.mock
def test_get_readme_returns_none_on_404():
    respx.get("https://api.github.com/repos/octocat/no-readme/readme").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    text = _client().get_readme("octocat", "no-readme")
    assert text is None


@respx.mock
def test_get_readme_truncates_to_max_bytes():
    respx.get("https://api.github.com/repos/octocat/big/readme").mock(
        return_value=httpx.Response(200, text="x" * 1000)
    )
    text = _client().get_readme("octocat", "big", max_bytes=10)
    assert len(text) == 10


@respx.mock
def test_get_readme_reraises_non_404_errors():
    respx.get("https://api.github.com/repos/octocat/broken/readme").mock(
        return_value=httpx.Response(500, text="server error")
    )
    with pytest.raises(GitHubAPIError):
        _client().get_readme("octocat", "broken")
