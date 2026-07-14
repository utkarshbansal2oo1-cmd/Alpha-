"""SQLAlchemy model for persisted, encrypted connector credentials -- Sprint 32.

Generic across connectors on purpose (`provider` + `encrypted_secret`, not
a GitHub-specific table) so Greenhouse, Lever, Ashby, etc. can reuse the
same table/service later instead of each connector inventing its own
persistence -- see app/credentials/service.py's own docstring.

`encrypted_secret` is always ciphertext (Fernet, via app/credentials/
crypto.py) -- this row is never written or read as plaintext anywhere.

Sprint 32 (second pass) adds connector health/verification metadata so a
future UI can show "Connected" vs "Invalid token" instead of recruiters
discovering a dead connector only when a search comes back thin:

- `status`: "unconfigured" | "connected" | "invalid" -- set by
  ConnectorCredentialStore.mark_verified()/mark_error().
- `last_error`: the most recent verification/runtime auth failure
  message, if any. Cleared on the next successful verification.
- `verified_username`: the GitHub (or other provider) login the PAT
  actually resolved to, captured at verification time -- lets an admin
  confirm "yes, this is my token" without re-decrypting the secret.
- `verified_scopes`: comma-joined OAuth scopes GitHub reported for a
  classic PAT (fine-grained PATs don't return this header -- stored as
  None in that case, which is expected, not an error).

Deliberately NOT added: version history / rotated_at for the secret
itself -- out of scope for this sprint per explicit product decision;
replacing the existing encrypted_secret in place is sufficient for now.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConnectorCredentialRow(Base):
    __tablename__ = "connector_credentials"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    encrypted_secret: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="unconfigured")
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_username: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_scopes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
