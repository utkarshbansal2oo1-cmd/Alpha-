"""Generic, persistent, encrypted credential store for connectors -- Sprint 32.

Built to close a specific gap: GitHubConfigStore (and Greenhouse's
equivalent) held its Personal Access Token purely in memory, so every
Railway restart/redeploy silently wiped it and discovery would quietly
skip GitHub until someone re-POSTed /integrations/github/configure. This
service reads from Postgres on first use, keeps a simple in-process cache
(so hot paths like the GitHub connector's `is_available()` don't hit the
database on every request), and writes through to both on `set_secret`.

Deliberately keyed by `provider` (a plain string like "github") rather
than one table per connector -- see app/models/connector_credential.py's
own docstring for why this is meant to be reused by future connectors,
not GitHub-specific.

Second pass (same sprint): mark_verified()/mark_error()/get_status() add
connector health tracking on top of the secret itself -- see
app/models/connector_credential.py's docstring for the exact fields and
why (surfacing "invalid token" to an admin instead of silent thin
searches). These deliberately do NOT go through `_cache` (which only ever
held bare secret strings) -- status reads always hit Postgres, since
they're low-frequency (an admin checking a dashboard, or one write per
verify/failure), unlike `get_secret` which is on the hot discovery path.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.credentials.crypto import decrypt_secret, encrypt_secret
from app.database import SessionLocal
from app.models.connector_credential import ConnectorCredentialRow


class ConnectorCredentialStore:
    def __init__(self, session_factory: sessionmaker[Session] | None = None):
        self._session_factory = session_factory or SessionLocal
        self._cache: dict[str, str] = {}

    def get_secret(self, provider: str) -> str | None:
        if provider in self._cache:
            return self._cache[provider]

        with self._session_factory() as db:
            row = db.execute(
                select(ConnectorCredentialRow).where(ConnectorCredentialRow.provider == provider)
            ).scalar_one_or_none()

        if row is None:
            return None

        secret = decrypt_secret(row.encrypted_secret)
        self._cache[provider] = secret
        return secret

    def set_secret(self, provider: str, secret: str, created_by: str | None = None) -> None:
        encrypted = encrypt_secret(secret)
        now = datetime.now(timezone.utc)

        with self._session_factory() as db:
            row = db.execute(
                select(ConnectorCredentialRow).where(ConnectorCredentialRow.provider == provider)
            ).scalar_one_or_none()

            if row is None:
                db.add(
                    ConnectorCredentialRow(
                        id=str(uuid.uuid4()),
                        provider=provider,
                        encrypted_secret=encrypted,
                        status="unconfigured",  # mark_verified() is always called right after in practice
                        created_at=now,
                        updated_at=now,
                        created_by=created_by,
                    )
                )
            else:
                row.encrypted_secret = encrypted
                row.updated_at = now
                if created_by:
                    row.created_by = created_by

            db.commit()

        self._cache[provider] = secret

    def is_configured(self, provider: str) -> bool:
        return self.get_secret(provider) is not None

    def mark_verified(self, provider: str, username: str | None, scopes: list[str] | None = None) -> None:
        """Records a successful live verification (e.g. GitHub's GET /user
        returned 200 for this PAT) -- called right after set_secret() on
        initial configure, and again any time runtime re-verification
        succeeds. Clears any prior last_error."""
        now = datetime.now(timezone.utc)
        with self._session_factory() as db:
            row = db.execute(
                select(ConnectorCredentialRow).where(ConnectorCredentialRow.provider == provider)
            ).scalar_one_or_none()
            if row is None:
                return  # nothing to mark -- set_secret() must be called first
            row.status = "connected"
            row.last_error = None
            row.verified_username = username
            row.verified_scopes = ",".join(scopes) if scopes else None
            row.last_verified_at = now
            row.updated_at = now
            db.commit()

    def mark_error(self, provider: str, error_message: str) -> None:
        """Records a failed verification or a runtime auth failure (e.g.
        the GitHub connector got a live 401 mid-search) -- so a dashboard
        can show "Invalid token" instead of a recruiter just seeing an
        unexplained thin result set. Does NOT clear the stored secret --
        an admin should be able to see what's wrong and reconnect, not
        lose the (possibly still-fixable) configuration."""
        now = datetime.now(timezone.utc)
        with self._session_factory() as db:
            row = db.execute(
                select(ConnectorCredentialRow).where(ConnectorCredentialRow.provider == provider)
            ).scalar_one_or_none()
            if row is None:
                return
            row.status = "invalid"
            row.last_error = error_message
            row.updated_at = now
            db.commit()

    def clear_secret(self, provider: str) -> None:
        """Sprint 37: a real "disconnect" -- deletes the persisted row
        entirely (not just blanking the secret or resetting status),
        matching what a recruiter/admin clicking "Disconnect" expects: the
        credential is gone, not lingering encrypted-but-unused. Evicts the
        in-process cache too, so a stale `get_secret()` never serves the
        disconnected token to the hot discovery path in the same process.
        Idempotent -- calling this when nothing was ever configured is a
        no-op, not an error."""
        with self._session_factory() as db:
            row = db.execute(
                select(ConnectorCredentialRow).where(ConnectorCredentialRow.provider == provider)
            ).scalar_one_or_none()
            if row is not None:
                db.delete(row)
                db.commit()
        self._cache.pop(provider, None)

    def get_status(self, provider: str) -> dict:
        """Always returns a dict, even when the provider was never
        configured -- callers (GET /integrations/status) shouldn't need
        to special-case None."""
        with self._session_factory() as db:
            row = db.execute(
                select(ConnectorCredentialRow).where(ConnectorCredentialRow.provider == provider)
            ).scalar_one_or_none()

        if row is None:
            return {
                "configured": False,
                "status": "unconfigured",
                "verified_username": None,
                "verified_scopes": None,
                "last_verified_at": None,
                "last_error": None,
            }

        return {
            "configured": True,
            "status": row.status,
            "verified_username": row.verified_username,
            "verified_scopes": row.verified_scopes.split(",") if row.verified_scopes else None,
            "last_verified_at": row.last_verified_at,
            "last_error": row.last_error,
        }
