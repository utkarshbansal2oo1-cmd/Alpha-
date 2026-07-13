"""In-memory history of SyncRuns, for the GET /integrations/greenhouse/
sync-status endpoint. Same POC-appropriate, single-process caveat as
GreenhouseConfigStore (config.py) -- a real deployment persists this in
the database, scoped per organization.
"""
from __future__ import annotations

from app.integrations.greenhouse.models import SyncRun


class SyncRunStore:
    def __init__(self):
        self._runs: list[SyncRun] = []

    def record(self, run: SyncRun) -> None:
        self._runs.append(run)

    def latest(self) -> SyncRun | None:
        return self._runs[-1] if self._runs else None

    def all(self) -> list[SyncRun]:
        return list(self._runs)


_store = SyncRunStore()


def get_sync_run_store() -> SyncRunStore:
    return _store
