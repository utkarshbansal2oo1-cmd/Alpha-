"""GreenhouseClient -- the only code in this connector that makes an HTTP
call. Built directly against Greenhouse's documented Harvest API contract
(https://developers.greenhouse.io/harvest.html):

- Auth: HTTP Basic, API key as username, blank password.
- Pagination: a `Link` response header with rel="next" (RFC 5988), not a
  page-count field in the body -- this client follows that header rather
  than assuming a fixed page size.
- Rate limiting: Greenhouse enforces roughly 50 requests per 10 seconds
  per API key and returns 429 with a `Retry-After` header when exceeded;
  this client honors that header with one retry rather than failing
  immediately, since a sync job hitting the limit briefly is expected
  behavior, not an error.

Nothing here is simulated -- pointing `GreenhouseConfig` at the real
`https://harvest.greenhouse.io/v1` with a real API key makes every method
below a real call. Tests exercise this client against constructed HTTP
responses shaped like Greenhouse's real documented payloads (via `respx`,
see tests_greenhouse.py), not a hand-rolled fake server.
"""
from __future__ import annotations

import re
import time

import httpx

from app.integrations.greenhouse.config import GreenhouseConfig

_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


class GreenhouseAPIError(Exception):
    """Raised when Greenhouse returns a non-2xx response that isn't a
    retryable rate-limit (429) -- e.g. 401 (bad API key), 404, 422."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"Greenhouse API error {status_code}: {message}")
        self.status_code = status_code


class GreenhouseClient:
    def __init__(self, config: GreenhouseConfig, http_client: httpx.Client | None = None):
        self._config = config
        # Callers (tests, or a future async deployment) may inject their
        # own httpx.Client -- e.g. one routed through respx's mock
        # transport -- rather than this one always opening real sockets.
        self._http = http_client or httpx.Client(
            base_url=config.base_url,
            auth=(config.api_key, ""),
            timeout=10.0,
            # Don't inherit HTTP_PROXY/HTTPS_PROXY/etc. from the process
            # environment -- a stray proxy env var in a deployment
            # environment should never silently reroute calls to
            # Greenhouse's API, and it also avoids eagerly resolving a
            # proxy transport before test tooling (respx) can patch it.
            trust_env=False,
        )

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = self._http.request(method, path, **kwargs)

        if response.status_code == 429:
            # Rate limited -- Greenhouse's own documented behavior. Honor
            # Retry-After and try exactly once more; a sync job that's
            # still rate limited after that surfaces the error rather
            # than retrying indefinitely and masking a real problem.
            retry_after = float(response.headers.get("Retry-After", "1"))
            time.sleep(min(retry_after, 5.0))
            response = self._http.request(method, path, **kwargs)

        if response.status_code >= 400:
            raise GreenhouseAPIError(response.status_code, response.text)

        return response

    def list_candidates(self, per_page: int = 100) -> list[dict]:
        """Fetches every candidate, following the `Link: rel="next"`
        pagination header until there isn't one -- matches Greenhouse's
        real pagination contract rather than assuming a fixed number of
        pages."""
        candidates: list[dict] = []
        path = f"/candidates?per_page={per_page}"

        while path:
            response = self._request("GET", path)
            candidates.extend(response.json())

            link_header = response.headers.get("Link", "")
            match = _LINK_NEXT_RE.search(link_header)
            if not match:
                break
            next_url = match.group(1)
            # httpx.Client.request accepts a path relative to base_url, or
            # a full URL -- the Link header gives a full URL, which httpx
            # handles transparently either way.
            path = next_url

        return candidates

    def get_candidate(self, candidate_id: int | str) -> dict:
        response = self._request("GET", f"/candidates/{candidate_id}")
        return response.json()

    def create_candidate(self, payload: dict) -> dict:
        response = self._request("POST", "/candidates", json=payload)
        return response.json()

    def add_candidate_note(self, candidate_id: int | str, body: str, visibility: str = "admin_only") -> dict:
        response = self._request(
            "POST",
            f"/candidates/{candidate_id}/activity_feed/notes",
            json={"body": body, "visibility": visibility},
        )
        return response.json()

    def close(self) -> None:
        self._http.close()
