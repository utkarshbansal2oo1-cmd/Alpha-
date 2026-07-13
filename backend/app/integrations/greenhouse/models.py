"""Sync-run bookkeeping for the Greenhouse connector. Kept separate from
app/candidate_repository/models.py -- SyncRun is connector-specific
operational metadata (how did this pull go), not part of the
source-agnostic Candidate shape every repository returns.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SyncRun(BaseModel):
    """One pull-sync execution's summary -- what recruiters/admins see on
    a sync status screen: when it ran, how many candidates were pulled,
    how many were brand new vs. merged into existing candidates, and any
    per-candidate errors (a single bad record from Greenhouse should never
    fail the whole sync -- see sync.py's pull_sync())."""

    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    status: str = Field(default="running", description="'running' | 'completed' | 'failed'")
    candidates_pulled: int = 0
    candidates_created: int = 0
    candidates_merged: int = 0
    errors: list[str] = Field(default_factory=list)
