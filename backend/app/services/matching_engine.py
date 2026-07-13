"""Scores and ranks candidates against a JobRequirement.

Source-agnostic by construction: input is RawCandidate + JobRequirement,
nothing here ever branches on where the candidate came from. Swapping in a
real embedding-similarity model later replaces `_skill_score`/`_experience_score`
internals only.
"""
from __future__ import annotations

from typing import List, Tuple

from app.schemas import JobRequirement
from app.services.connectors.base import RawCandidate

_WEIGHTS = {"skills": 0.5, "experience": 0.25, "location": 0.15, "seniority_bonus": 0.10}


def _skill_score(candidate: RawCandidate, req: JobRequirement) -> float:
    if not req.must_have_skills:
        return 1.0
    have = {s.lower() for s in candidate.skills}
    want = {s.lower() for s in req.must_have_skills}
    return len(have & want) / len(want)


def _experience_score(candidate: RawCandidate, req: JobRequirement) -> float:
    yrs = candidate.total_experience_yrs or 0
    if req.min_experience_yrs <= 0:
        return 1.0
    if yrs >= req.min_experience_yrs:
        return 1.0
    return max(0.0, yrs / req.min_experience_yrs)


def _location_score(candidate: RawCandidate, req: JobRequirement) -> float:
    if not req.location:
        return 1.0
    if candidate.location and req.location.lower() in candidate.location.lower():
        return 1.0
    return 0.0


def _explain(candidate: RawCandidate, req: JobRequirement, skill_s, exp_s, loc_s) -> str:
    parts = []
    if req.must_have_skills:
        have = {s.lower() for s in candidate.skills}
        matched = [s for s in req.must_have_skills if s.lower() in have]
        missing = [s for s in req.must_have_skills if s.lower() not in have]
        if matched:
            parts.append(f"matches required skills: {', '.join(matched)}")
        if missing:
            parts.append(f"missing: {', '.join(missing)}")
    if req.min_experience_yrs:
        yrs = candidate.total_experience_yrs or 0
        cmp = "meets/exceeds" if yrs >= req.min_experience_yrs else "is below"
        parts.append(f"{yrs} yrs experience {cmp} the {req.min_experience_yrs}-yr bar")
    if req.location:
        parts.append(
            f"based in {candidate.location}" if loc_s == 1.0 else f"not located in {req.location}"
        )
    return "; ".join(parts) if parts else "General profile match."


def rank(
    candidates: List[Tuple[RawCandidate, List[str]]], req: JobRequirement
) -> List[dict]:
    scored = []
    for candidate, sources in candidates:
        skill_s = _skill_score(candidate, req)
        exp_s = _experience_score(candidate, req)
        loc_s = _location_score(candidate, req)
        seniority_bonus = 1.0 if (candidate.total_experience_yrs or 0) > req.min_experience_yrs else 0.5

        total = (
            skill_s * _WEIGHTS["skills"]
            + exp_s * _WEIGHTS["experience"]
            + loc_s * _WEIGHTS["location"]
            + seniority_bonus * _WEIGHTS["seniority_bonus"]
        )
        match_score = round(total * 100, 1)
        reasoning = _explain(candidate, req, skill_s, exp_s, loc_s)

        scored.append(
            {
                "candidate": candidate,
                "sources": sources,
                "match_score": match_score,
                "reasoning": reasoning,
            }
        )

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored
