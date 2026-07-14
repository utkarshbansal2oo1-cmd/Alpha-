"""SQLAlchemy models for persistent search sessions -- Sprint 33.

Closes the "every page repeats the entire pipeline" gap: Query
Understanding, Search Planner, Discovery (including live GitHub calls),
the Matching Engine, and the Ranking Engine all ran again on every single
page turn under Sprint 31's pagination (that sprint only avoided a SECOND
in-process computation within the same request -- across requests, going
to page 2 meant a brand-new POST /api/search/smart, i.e. the whole
pipeline again). This sprint runs the full pipeline exactly once per
search, persists its ranked output, and pages read that stored output.

Two tables, deliberately NOT one:

- `SearchSessionRow`: one row per completed search. `session_data` is a
  small JSON blob holding the pipeline's own intermediate/summary output
  (requirement, search_plan, discovery run) -- NOT candidate data. This
  is what lets GET /api/search/session/{id} echo the same
  requirement/search_plan/discovery fields POST returned, from storage,
  with no recomputation.
- `SearchSessionCandidateRow`: the ranked candidate LIST for a session --
  one row per candidate, storing only its id, rank, and the Matching
  Engine's MatchResult fields (score, component scores, matched/missing
  fields, reasons). Explicitly NOT the full Candidate object -- pages
  re-fetch the actual Candidate from the existing CandidateRepository by
  id, so this table never duplicates candidate data that repository
  already owns. A unique constraint on (session_id, candidate_id) makes
  a duplicate candidate within one session structurally impossible, not
  just something application code has to remember to check.

Future-ready, not yet built (explicitly out of scope for this sprint):
per-candidate-per-session recruiter state (viewed/rejected/shortlisted/
notes/interviewed) is a natural additional table keyed by
(session_id, candidate_id) alongside this one -- SearchSessionCandidateRow
already has that exact composite key shape, so adding it later is a new
table + a join, not a redesign of this one.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SearchSessionRow(Base):
    __tablename__ = "search_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    recruiter_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    query: Mapped[str] = mapped_column(String, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # Bundles requirement/search_plan/discovery (all small, structured
    # pipeline output, not candidate data) into one JSON column rather
    # than three -- see this module's own docstring for why storing
    # candidate data itself here would be wrong.
    session_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class SearchSessionCandidateRow(Base):
    __tablename__ = "search_session_candidates"
    __table_args__ = (
        UniqueConstraint("session_id", "candidate_id", name="uq_search_session_candidate"),
        UniqueConstraint("session_id", "rank", name="uq_search_session_rank"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("search_sessions.id"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    component_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    matched_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    missing_fields: Mapped[list] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list] = mapped_column(JSON, nullable=False)
