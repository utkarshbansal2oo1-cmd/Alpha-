"""GitHub connector configuration -- Sprint 20B.

Same POC-scoped, in-memory, single-process storage pattern as
app/integrations/greenhouse/config.py: one Personal Access Token, held in
memory, not persisted across restarts. GitHub's REST API authenticates a
PAT with an `Authorization: token <PAT>` (classic) or `Bearer <PAT>`
(fine-grained) header -- both are accepted by GitHub's API, so this
client always sends the classic `token` scheme, which both token types
honor. There is no OAuth dance modeled here: a recruiter/admin generates
a PAT from their own GitHub account (Settings -> Developer settings ->
Personal access tokens) and supplies it directly, exactly like the
Greenhouse API key.
"""
from __future__ import annotations

from pydantic import BaseModel

DEFAULT_BASE_URL = "https://api.github.com"


class GitHubConfig(BaseModel):
    personal_access_token: str
    base_url: str = DEFAULT_BASE_URL


class GitHubConfigError(Exception):
    """Raised when a GitHub-dependent operation is attempted before the
    connector has been configured (see POST /integrations/github/configure)."""


class GitHubConfigStore:
    """In-memory holder for the active GitHubConfig -- same not-thread
    -safe-beyond-the-GIL, single-process caveat as GreenhouseConfigStore."""

    def __init__(self):
        self._config: GitHubConfig | None = None

    def set(self, config: GitHubConfig) -> None:
        self._config = config

    def get(self) -> GitHubConfig:
        if self._config is None:
            raise GitHubConfigError(
                "GitHub is not configured yet -- call POST /integrations/github/configure with a personal_access_token first."
            )
        return self._config

    def is_configured(self) -> bool:
        return self._config is not None


_store = GitHubConfigStore()


def get_github_config_store() -> GitHubConfigStore:
    return _store
