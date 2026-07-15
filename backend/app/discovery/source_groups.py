"""Source Group registry -- Sprint 36.

A Source Group is a DOMAIN concept, not a UI concept: "where a candidate
belongs" for presentation/trust purposes. This is deliberately distinct
from a Connector, which answers "how we discovered this candidate" (see
`discovery_method_for()`/`connector_for()` below, and
`CandidateProvenance` in app/routers/discovery_search.py). Today those two
questions happen to have the same answer for every candidate (a GitHub
candidate was found BY the GitHub connector, INTO the GitHub source
group) -- but they are not guaranteed to stay the same answer forever.
Sprint 12's CaptureSource model already supports a candidate accumulating
MULTIPLE capture events from different connectors over its lifetime (a
profile first captured via the browser extension, later re-enriched via a
CSV import) -- at that point "source group" (its primary, trust-bearing
home) and "connector" (which mechanism most recently touched it) genuinely
diverge, and this module is where that distinction is meant to live.

This module owns ONLY presentation-layer facts about a source: its
display name, icon, trust level, and whether it's a "live" discovered
source or a fallback/reference one. It does NOT affect ranking, matching,
or discovery in any way -- `trust_level`/`is_fallback` are read by the
presentation layer (app/routers/discovery_search.py's grouping step)
strictly to decide section ordering and labeling, never passed into
MatchingConfig, RankingEngine, or DiscoveryOrchestrator.

Adding a brand-new connector (Lever, Ashby, Resume Database, Internal
ATS, ...) requires at most one new entry here for a polished label/icon --
`get_source_group_info()` already falls back to a reasonable generic
group (title-cased source name, "live" trust, not a fallback) for any
source string not explicitly listed, so the system never breaks or
mis-groups an unrecognized source; it just looks a little less polished
until an entry is added.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceGroupInfo:
    """Static, presentation-only facts about one source. Never mutated
    per-search -- per-search facts (candidate_count, searched_count,
    timings, etc.) live on the SourceGroup response model in
    app/routers/discovery_search.py, built by combining one of these with
    that search's actual results."""

    display_name: str
    icon: str  # a stable icon-key string; the frontend owns the icon asset per key
    trust_level: str  # "high" | "reference" | "unknown" -- UI-only, never read by scoring
    is_live: bool  # a genuinely discovered/connected source vs. bundled reference data
    is_fallback: bool  # only ever appended when live results are insufficient
    discovery_method: str  # human-readable "how" -- distinct from the source itself


# Sprint 36: explicit, curated entries for every source AlphaSource knows
# about today. This is a lookup table, not a control-flow branch -- the
# grouping/ranking code never does `if source == "github": ...`; it only
# ever calls get_source_group_info(source) and reads the fields back.
_SOURCE_GROUPS: dict[str, SourceGroupInfo] = {
    "github": SourceGroupInfo(
        display_name="GitHub Matches",
        icon="github",
        trust_level="high",
        is_live=True,
        is_fallback=False,
        discovery_method="GitHub Search API",
    ),
    "greenhouse_ats": SourceGroupInfo(
        display_name="Greenhouse Matches",
        icon="greenhouse",
        trust_level="high",
        is_live=True,
        is_fallback=False,
        discovery_method="Greenhouse Harvest API",
    ),
    # Sprint 36's core product requirement: seed data is fallback/demo
    # data, never shown to recruiters under the word "seed". The internal
    # `Candidate.source` value stays exactly "seed_data" (untouched, per
    # the sprint's explicit "do not redesign the Candidate/Repository"
    # instruction) -- only this lookup's display_name changes what a
    # recruiter actually sees.
    "seed_data": SourceGroupInfo(
        display_name="Suggested Profiles",
        icon="sparkles",
        trust_level="reference",
        is_live=False,
        is_fallback=True,
        discovery_method="Bundled reference dataset",
    ),
    # Sprint 18 future-connector stubs (app/discovery/connectors/future_connectors.py)
    # -- entries here so their sections, once real, display sensibly with
    # no further changes to this module beyond flipping their behavior on.
    "browser_extension": SourceGroupInfo(
        display_name="Browser Extension Captures",
        icon="browser",
        trust_level="high",
        is_live=True,
        is_fallback=False,
        discovery_method="Recruiter browser capture",
    ),
    "csv_import": SourceGroupInfo(
        display_name="CSV Imports",
        icon="file-spreadsheet",
        trust_level="high",
        is_live=True,
        is_fallback=False,
        discovery_method="CSV import",
    ),
    "resume_import": SourceGroupInfo(
        display_name="Resume Database",
        icon="file-text",
        trust_level="high",
        is_live=True,
        is_fallback=False,
        discovery_method="Resume database import",
    ),
    "hrms": SourceGroupInfo(
        display_name="Internal ATS",
        icon="building",
        trust_level="high",
        is_live=True,
        is_fallback=False,
        discovery_method="Internal ATS/HRMS sync",
    ),
}


def get_source_group_info(source: str) -> SourceGroupInfo:
    """Never raises -- an unrecognized source (a brand-new connector that
    hasn't had a polished entry added above yet) still gets a sensible,
    safe-default group rather than breaking grouping or being silently
    dropped. This is what lets a future connector "just work" the moment
    it's registered, with a nicer label as a fast-follow, not a blocker."""
    known = _SOURCE_GROUPS.get(source)
    if known is not None:
        return known
    return SourceGroupInfo(
        display_name=source.replace("_", " ").title(),
        icon="database",
        trust_level="unknown",
        is_live=True,
        is_fallback=False,
        discovery_method=source.replace("_", " ").title(),
    )
