"""Validates a parsed JSON dict against the CanonicalJobRequirement
contract and constructs the final object.

Deliberately does NOT touch the Knowledge Engine or Search Planner --
per the brief, this module performs no taxonomy expansion, no matching, no
search. It only checks: does this dict have a non-blank `role` string and a
`skills` field that, if present, is a list of strings. Anything else raises
QueryValidationError with a message specific enough to drive the single
retry attempt in service.py.
"""
from __future__ import annotations

from app.query_understanding.models import CanonicalJobRequirement, QueryValidationError


class QueryValidator:
    """Validates and converts a parsed dict into a CanonicalJobRequirement."""

    def validate(self, data: dict) -> CanonicalJobRequirement:
        if not isinstance(data, dict):
            raise QueryValidationError(
                f"Expected a JSON object, got {type(data).__name__}"
            )

        role = data.get("role")
        if not isinstance(role, str) or not role.strip():
            raise QueryValidationError(
                "'role' must be a non-empty string, got "
                f"{role!r} ({type(role).__name__})"
            )

        skills = data.get("skills", [])
        if not isinstance(skills, list):
            raise QueryValidationError(
                f"'skills' must be a list of strings, got {type(skills).__name__}"
            )

        cleaned_skills: list[str] = []
        for i, skill in enumerate(skills):
            if not isinstance(skill, str):
                raise QueryValidationError(
                    f"'skills[{i}]' must be a string, got {type(skill).__name__}"
                )
            if skill.strip():
                cleaned_skills.append(skill.strip())

        unexpected_keys = set(data.keys()) - {"role", "skills"}
        if unexpected_keys:
            raise QueryValidationError(
                f"Response contained unexpected field(s): {sorted(unexpected_keys)}. "
                "Only 'role' and 'skills' are permitted."
            )

        return CanonicalJobRequirement(role=role.strip(), skills=cleaned_skills)
