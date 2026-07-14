"""GitHub connector configuration -- Sprint 20B, persistence + verification
added Sprint 32.

The Personal Access Token is held either purely in memory (default,
CONNECTOR_CREDENTIALS_BACKEND=memory -- same not-persisted-across-
restarts behavior as Sprint 20B originally shipped) or via the generic,
encrypted ConnectorCredentialStore (app/credentials/service.py) backed by
Postgres, once CONNECTOR_CREDENTIALS_BACKEND=postgres -- see get_github_
config_store()'s own comment for the selection logic, mirroring the same
safe-default pattern app/candidate_repository/repository.py already
established for CANDIDATE_REPOSITORY_BACKEND. Both backends stay fully
supported (not one collapsed into the other) so tests and local dev never
need a live Postgres, matching this project's established convention for
every other pluggable backend (QUERY_PROVIDER, CANDIDATE_REPOSITORY_BACKEND).

GitHub's REST API authenticates a PAT with an `Authorization: token <PAT>`
(classic) or `Bearer <PAT>` (fine-grained) header -- both are accepted by
GitHub's API, so this client always sends the classic `token` scheme,
which both token types honor. There is no OAuth dance modeled here: a
recruiter/admin generates a PAT from their own GitHub account (Settings ->
Developer settings -> Personal access tokens) and supplies it directly,
exactly like the Greenhouse API key.

Sprint 32 (second pass) adds connector health tracking (mark_verified/
mark_error/get_status) alongside the token itself -- see
app/models/connector_credential.py's docstring for the exact fields and
why. In memory mode, this is a plain dict on the instance (nothing to
persist); in persistent mode it delegates to the same
ConnectorCredentialStore holding the secret.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from app.config import settings

DEFAULT_BASE_URL = "https://api.github.com"

_PROVIDER = "github"

_UNCONFIGURED_STATUS: dict = {
    "configured": False,
    "status": "unconfigured",
    "verified_username": None,
    "verified_scopes": None,
    "last_verified_at": None,
    "last_error": None,
}


class GitHubConfig(BaseModel):
    personal_access_token: str
    base_url: str = DEFAULT_BASE_URL


class GitHubConfigError(Exception):
    """Raised when a GitHub-dependent operation is attempted before the
    connector has been configured (see POST /integrations/github/configure)."""


class GitHubConfigStore:
    """Holder for the active GitHubConfig.

    Sprint 32: the PAT itself is delegated to a `credential_store`
    (ConnectorCredentialStore) when one is supplied -- persisted,
    encrypted, and cached in-process by that store. When no
    credential_store is supplied (the default -- e.g. every existing
    test constructing `GitHubConfigStore()` directly), this falls back
    to the original Sprint 20B behavior: a plain in-memory attribute,
    not persisted, not shared with any other store. `base_url` is
    intentionally always kept in memory only, regardless of backend --
    it's not a secret, changes essentially never, and isn't worth a
    migration/column of its own.
    """

    def __init__(self, credential_store=None):
        self._credential_store = credential_store
        self._base_url: str = DEFAULT_BASE_URL
        self._pat_memory: str | None = None  # used only when credential_store is None
        # In-memory status, used only when credential_store is None --
        # mirrors the shape ConnectorCredentialStore.get_status() returns
        # so callers don't need to branch on which backend is active.
        self._status_memory: dict = dict(_UNCONFIGURED_STATUS)

    def set(self, config: GitHubConfig) -> None:
        self._base_url = config.base_url
        if self._credential_store is not None:
            self._credential_store.set_secret(_PROVIDER, config.personal_access_token)
        else:
            self._pat_memory = config.personal_access_token
            self._status_memory = dict(_UNCONFIGURED_STATUS)
            self._status_memory["configured"] = True

    def _current_pat(self) -> str | None:
        if self._credential_store is not None:
            return self._credential_store.get_secret(_PROVIDER)
        return self._pat_memory

    def get(self) -> GitHubConfig:
        pat = self._current_pat()
        if pat is None:
            raise GitHubConfigError(
                "GitHub is not configured yet -- call POST /integrations/github/configure with a personal_access_token first."
            )
        return GitHubConfig(personal_access_token=pat, base_url=self._base_url)

    def is_configured(self) -> bool:
        return self._current_pat() is not None

    def mark_verified(self, username: str | None, scopes: list[str] | None = None) -> None:
        if self._credential_store is not None:
            self._credential_store.mark_verified(_PROVIDER, username, scopes)
            return
        self._status_memory.update(
            {
                "configured": True,
                "status": "connected",
                "verified_username": username,
                "verified_scopes": scopes or None,
                "last_verified_at": datetime.now(timezone.utc),
                "last_error": None,
            }
        )

    def mark_error(self, error_message: str) -> None:
        if self._credential_store is not None:
            self._credential_store.mark_error(_PROVIDER, error_message)
            return
        self._status_memory["status"] = "invalid"
        self._status_memory["last_error"] = error_message

    def get_status(self) -> dict:
        if self._credential_store is not None:
            return self._credential_store.get_status(_PROVIDER)
        return dict(self._status_memory)


def _build_github_config_store() -> GitHubConfigStore:
    backend = settings.CONNECTOR_CREDENTIALS_BACKEND.strip().lower()
    if backend == "postgres":
        from app.credentials.service import ConnectorCredentialStore

        return GitHubConfigStore(credential_store=ConnectorCredentialStore())
    if backend == "memory":
        return GitHubConfigStore()
    raise ValueError(f"Unknown CONNECTOR_CREDENTIALS_BACKEND: {backend!r} (expected 'memory' or 'postgres')")


_store = _build_github_config_store()


def get_github_config_store() -> GitHubConfigStore:
    return _store
