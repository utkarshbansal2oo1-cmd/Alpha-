"""Recruiter authentication service -- Sprint 30.

Deliberately no user-registration endpoint -- recruiter accounts are
created only via ensure_admin() at startup (from ADMIN_USERNAME/
ADMIN_PASSWORD), matching the Sprint 30 brief's "not enterprise auth, just
enough" scope. Adding real multi-recruiter self-service signup is
explicitly out of scope for this sprint.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.security import generate_session_token, hash_password, verify_password
from app.config import settings
from app.database import SessionLocal
from app.models.recruiter import RecruiterRow, SessionRow


class AuthService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None):
        self._session_factory = session_factory or SessionLocal

    def ensure_admin(self, username: str, password: str) -> None:
        """Creates a recruiter account from the given credentials if, and
        only if, no recruiter exists yet -- a one-time bootstrap, not a
        way to reset/create arbitrary additional accounts. Silently does
        nothing if username/password aren't set, so this is always safe
        to call unconditionally at startup."""
        if not username or not password:
            return

        with self._session_factory() as db:
            if db.execute(select(RecruiterRow.id)).first() is not None:
                return

            password_hash, salt = hash_password(password)
            db.add(
                RecruiterRow(
                    id=str(uuid.uuid4()),
                    username=username,
                    password_hash=password_hash,
                    password_salt=salt,
                )
            )
            db.commit()

    def authenticate(self, username: str, password: str) -> str | None:
        """Returns a new session token if the credentials are valid, else
        None. Callers must not distinguish "unknown username" from "wrong
        password" in their response -- both return None here precisely so
        that distinction can't leak to an attacker."""
        with self._session_factory() as db:
            recruiter = db.execute(
                select(RecruiterRow).where(RecruiterRow.username == username)
            ).scalar_one_or_none()

            if recruiter is None or not verify_password(password, recruiter.password_hash, recruiter.password_salt):
                return None

            token = generate_session_token()
            expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)
            db.add(SessionRow(token=token, recruiter_id=recruiter.id, expires_at=expires_at))
            db.commit()
            return token

    def get_recruiter_for_token(self, token: str) -> RecruiterRow | None:
        with self._session_factory() as db:
            session = db.get(SessionRow, token)
            if session is None:
                return None

            expires_at = session.expires_at
            if expires_at.tzinfo is None:
                # SQLite (used in tests -- see tests_service.py) doesn't
                # preserve tzinfo across a round-trip through a
                # DateTime(timezone=True) column the way Postgres does, so
                # a naive datetime coming back here doesn't necessarily
                # mean it was stored as UTC by anything other than this
                # class -- which is the only writer of expires_at (see
                # authenticate() above), so treating a naive value as UTC
                # is correct, not a guess.
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at < datetime.now(timezone.utc):
                return None
            return db.get(RecruiterRow, session.recruiter_id)
