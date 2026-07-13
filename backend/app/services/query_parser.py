"""Plain-English recruiter query -> structured JobRequirement.

MVP: rule/regex based extraction so the pipeline runs with zero external API
keys. Swap the body of `parse()` for an LLM call later (e.g. Claude) without
touching any caller — the function signature and JobRequirement shape stay
the same.
"""
from __future__ import annotations

import re

from app.schemas import JobRequirement

_KNOWN_SKILLS = [
    "AWS", "Kubernetes", "Docker", "Python", "React", "Node.js", "Java",
    "Go", "Terraform", "PostgreSQL", "System Design", "Azure", "GCP",
    "TypeScript", "Machine Learning",
]


def parse(query: str) -> JobRequirement:
    text = query.strip()

    exp_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*year", text, re.IGNORECASE)
    min_experience = float(exp_match.group(1)) if exp_match else 0.0

    loc_match = re.search(
        r"\bin\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)", text
    )
    location = loc_match.group(1) if loc_match else None

    found_skills = [s for s in _KNOWN_SKILLS if s.lower() in text.lower()]

    role_match = re.search(r"^(?:find|source|looking for)?\s*([A-Za-z ]+?)(?:with|in|\d|$)", text, re.IGNORECASE)
    role = (role_match.group(1).strip() if role_match else text).strip() or "Candidate"

    return JobRequirement(
        role=role,
        min_experience_yrs=min_experience,
        location=location,
        must_have_skills=found_skills,
        nice_to_have_skills=[],
    )
