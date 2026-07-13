"""Identity resolution: collapse the same human seen across multiple
connectors into one canonical candidate. Runs purely on normalized
RawCandidate data — has no idea which source anything came from beyond
the label needed for the final "sources" list.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from app.services.connectors.base import RawCandidate


def dedupe(
    candidates_by_source: Dict[str, List[RawCandidate]]
) -> List[Tuple[RawCandidate, List[str]]]:
    """Returns list of (representative_candidate, [source_names]) merging
    matches on email (primary key) or full_name+current_company (fallback)."""
    merged: Dict[str, Tuple[RawCandidate, List[str]]] = {}

    for source_name, candidates in candidates_by_source.items():
        for c in candidates:
            key = (c.email or f"{c.full_name.lower()}|{(c.current_company or '').lower()}")
            if key in merged:
                rep, sources = merged[key]
                if source_name not in sources:
                    sources.append(source_name)
            else:
                merged[key] = (c, [source_name])

    return list(merged.values())
