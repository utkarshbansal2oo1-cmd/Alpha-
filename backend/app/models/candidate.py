"""SQLAlchemy model for persisted candidates -- Sprint 30.

One row per candidate, storing the entire Candidate (Pydantic) model as a
JSON blob rather than fully normalizing every nested list (education,
capture_sources, evidence_history, version_history) into child tables.
This is a deliberate, POC-appropriate choice matching this codebase's
existing pattern of keeping the Candidate shape source-agnostic and
evolving freely (see candidate_repository/models.py's own docstring on
additive fields across Sprints 12/14/20D) -- a rigid relational schema
would need a migration every time a new field is added to Candidate;
JSONB does not.

`id` is the same string id CandidateRepository already treats as
authoritative everywhere (UUID or connector-provided id, e.g. a GitHub
username-derived id) -- not a new synthetic key.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CandidateRow(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
