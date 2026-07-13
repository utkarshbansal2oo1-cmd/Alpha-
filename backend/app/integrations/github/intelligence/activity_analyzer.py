"""Activity Analyzer -- Sprint 20D.

Measures recency and breadth of activity from each repo's own
`pushed_at` timestamp (per
https://docs.github.com/en/rest/repos/repos#list-repositories-for-a-user)
-- GitHub's REST API has no separate "last commit" endpoint cheaper than
fetching full commit history per repo, so `pushed_at` (updated whenever
a push lands on any branch) is the documented, honest proxy for "last
commit" used here, exactly as GitHub's own contribution-graph tooling
uses it.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

_ACTIVE_WINDOW_MONTHS = 12


class ActivityAnalysis(BaseModel):
    last_push_at: datetime | None = None
    months_since_last_activity: float | None = None
    active_repositories: int = 0
    inactive_repositories: int = 0
    activity_score: float = Field(default=0.0, ge=0.0, le=100.0)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _months_between(earlier: datetime, later: datetime) -> float:
    delta_days = (later - earlier).total_seconds() / 86400.0
    return round(delta_days / 30.437, 2)  # average month length


class ActivityAnalyzer:
    def __init__(self, config):
        self._config = config

    def analyze(self, raw_repos: list[dict], now: datetime | None = None) -> ActivityAnalysis:
        now = now or datetime.now(timezone.utc)
        capped = raw_repos[: self._config.max_repositories]

        pushed_dates = [_parse_timestamp(r.get("pushed_at")) for r in capped]
        pushed_dates = [d for d in pushed_dates if d is not None]

        if not pushed_dates:
            return ActivityAnalysis()

        last_push = max(pushed_dates)
        months_since = _months_between(last_push, now)

        active = sum(1 for d in pushed_dates if _months_between(d, now) <= _ACTIVE_WINDOW_MONTHS)
        inactive = len(pushed_dates) - active

        # Heuristic, bounded 0-100: recency dominates (a very stale
        # profile scores low regardless of repo count), breadth of
        # currently-active repos adds on top of that.
        recency_score = max(0.0, 100.0 - (months_since * 5.0))
        breadth_score = min(40.0, active * 8.0)
        activity_score = round(min(100.0, max(0.0, recency_score * 0.6 + breadth_score)), 2)

        return ActivityAnalysis(
            last_push_at=last_push,
            months_since_last_activity=months_since,
            active_repositories=active,
            inactive_repositories=inactive,
            activity_score=activity_score,
        )
