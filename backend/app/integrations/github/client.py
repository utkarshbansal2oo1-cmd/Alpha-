"""GitHubClient -- the only code in this connector that makes an HTTP
call. Built directly against GitHub's documented, official REST API
(https://docs.github.com/en/rest):

- Auth: `Authorization: token <PAT>` header (see config.py).
- Search: GET /search/users?q=... (https://docs.github.com/en/rest/search/search#search-users)
- Profile: GET /users/{username} (https://docs.github.com/en/rest/users/users#get-a-user)
- Repos: GET /users/{username}/repos (https://docs.github.com/en/rest/repos/repos#list-repositories-for-a-user)
- Rate limiting: GitHub returns 403 with `X-RateLimit-Remaining: 0` and an
  `X-RateLimit-Reset` epoch-seconds header when the primary rate limit is
  hit; this client waits until that reset time (capped, same reasoning as
  GreenhouseClient's Retry-After handling) and retries exactly once,
  rather than failing immediately or retrying forever.

Nothing here is simulated -- a real Personal Access Token makes every
method below a real call against https://api.github.com. Tests exercise
this client against constructed HTTP responses shaped like GitHub's real
documented payloads (via respx), not a hand-rolled fake server.
"""
from __future__ import annotations

import time

import httpx

from app.integrations.github.config import GitHubConfig

_MAX_RATE_LIMIT_WAIT_SECONDS = 5.0


class GitHubAPIError(Exception):
    """Raised when GitHub returns a non-2xx response that isn't a
    retryable primary-rate-limit 403 -- e.g. 401 (bad token), 404, 422."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"GitHub API error {status_code}: {message}")
        self.status_code = status_code


class GitHubClient:
    def __init__(self, config: GitHubConfig, http_client: httpx.Client | None = None):
        self._config = config
        # Callers (tests, or a future async deployment) may inject their
        # own httpx.Client -- e.g. one routed through respx's mock
        # transport -- rather than this one always opening real sockets.
        self._http = http_client or httpx.Client(
            base_url=config.base_url,
            headers={
                "Authorization": f"token {config.personal_access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10.0,
            # Don't inherit HTTP_PROXY/etc. from the process environment --
            # same reasoning as GreenhouseClient.
            trust_env=False,
        )

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = self._http.request(method, path, **kwargs)

        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            reset_at = response.headers.get("X-RateLimit-Reset")
            wait_seconds = 1.0
            if reset_at:
                wait_seconds = max(0.0, float(reset_at) - time.time())
            time.sleep(min(wait_seconds, _MAX_RATE_LIMIT_WAIT_SECONDS))
            response = self._http.request(method, path, **kwargs)

        if response.status_code >= 400:
            raise GitHubAPIError(response.status_code, response.text)

        return response

    def search_users(self, query: str, per_page: int = 30) -> list[dict]:
        """GET /search/users -- returns the `items` array from GitHub's
        search response envelope (which also carries total_count and
        incomplete_results, not needed here)."""
        response = self._request("GET", "/search/users", params={"q": query, "per_page": per_page})
        return response.json().get("items", [])

    def get_user(self, username: str) -> dict:
        response = self._request("GET", f"/users/{username}")
        return response.json()

    def list_repos(self, username: str, per_page: int = 100) -> list[dict]:
        response = self._request(
            "GET", f"/users/{username}/repos", params={"per_page": per_page, "sort": "updated"}
        )
        return response.json()

    # --- Sprint 20D: GitHub Candidate Intelligence Engine additions ---------

    def list_orgs(self, username: str) -> list[dict]:
        """GET /users/{username}/orgs -- per
        https://docs.github.com/en/rest/orgs/orgs#list-organizations-for-a-user.
        Only ever returns the user's PUBLIC organization memberships;
        private memberships are invisible to this endpoint, which
        organization_analyzer.py reports honestly rather than guessing at."""
        response = self._request("GET", f"/users/{username}/orgs")
        return response.json()

    def get_readme(self, owner: str, repo: str, max_bytes: int | None = None) -> str | None:
        """GET /repos/{owner}/{repo}/readme, requesting raw text via the
        `application/vnd.github.raw+json` Accept override (per
        https://docs.github.com/en/rest/repos/contents#get-a-repository-readme)
        so no base64 decoding is needed. Returns None (never raises) when
        a repo has no README (GitHub returns 404) -- a missing README is
        expected, common, and not an error condition for enrichment
        purposes. `max_bytes` truncates the returned text, matching
        GitHubIntelligenceConfig's own README size safety limit."""
        try:
            response = self._request(
                "GET",
                f"/repos/{owner}/{repo}/readme",
                headers={"Accept": "application/vnd.github.raw+json"},
            )
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                return None
            raise
        text = response.text
        if max_bytes is not None:
            text = text[:max_bytes]
        return text

    def close(self) -> None:
        self._http.close()
