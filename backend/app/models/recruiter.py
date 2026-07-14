"""SQLAlchemy models for minimal recruiter identity -- Sprint 30.

Deliberately not enterprise auth (no roles/permissions/SSO/OAuth) -- per
the Sprint 30 brief, "just enough" identity so per-recruiter state
(viewed/shortlisted/hidden candidates, later sprints) has someone to
belong to, and so the publicly-deployed search endpoint isn't wide open
to anyone with the URL (see the standing gap flagged before this sprint:
zero authentication existed anywhere in this API).

Password storage: PBKDF2-HMAC-SHA256 via Python's stdlib `hashlib`
(app/auth/security.py) -- no new dependency (bcrypt/passlib) needed for a
POC-scale recruiter count. Sessions are opaque server-side tokens (not
JWTs) so a session can be revoked by deleting its row -- simpler to reason
about correctly than verifying/expiring a signed token client-side.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecruiterRow(Base):
    __tablename__ = "recruiters"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    password_salt: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class SessionRow(Base):
    """One issued login session. `token` (not `id`) is the primary key --
    it IS the bearer credential the frontend holds, so looking one up by
    its own value is the entire point (no separate lookup key needed)."""

    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    recruiter_id: Mapped[str] = mapped_column(String, ForeignKey("recruiters.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
