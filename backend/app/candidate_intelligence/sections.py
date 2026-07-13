"""The canonical section vocabulary every engine in this package shares --
one place that maps a Candidate's fields onto human-meaningful profile
sections, and how much each section is worth toward the overall Health
Score. Changing a weight or a field mapping here changes every engine
consistently; nothing else in this package hardcodes a field list.
"""
from __future__ import annotations

IDENTITY = "identity"
PROFESSIONAL = "professional"
SKILLS = "skills"
EDUCATION = "education"
CONTACT = "contact"
SUMMARY = "summary"

# Section -> (weight toward the 0-100 overall score, list of Candidate
# field names that belong to it). Weights sum to 100.
SECTION_WEIGHTS = {
    IDENTITY: 15,
    PROFESSIONAL: 25,
    SKILLS: 20,
    EDUCATION: 10,
    CONTACT: 15,
    SUMMARY: 15,
}

SECTION_FIELDS = {
    IDENTITY: ["name", "location"],
    PROFESSIONAL: ["role", "current_company", "experience"],
    SKILLS: ["skills"],
    EDUCATION: ["education"],
    CONTACT: ["public_profile_url", "resume_link"],
    SUMMARY: ["summary"],
}

# Which section a given field belongs to -- the inverse of SECTION_FIELDS,
# built once here so the Evidence Timeline can tag every event with a
# section without duplicating the mapping.
FIELD_TO_SECTION = {
    field: section for section, fields in SECTION_FIELDS.items() for field in fields
}


def field_present(candidate, field_name: str) -> bool:
    """Whether a given field counts as "present" for health/completeness
    purposes. Not just falsy/truthy: `experience` defaults to 0 for
    unknown values (see normalizer.py's placeholder handling), so 0 is
    treated as *not yet known* rather than "zero years of experience" --
    the one deliberate special case here. Every other field is a plain
    presence check (non-empty string / non-empty list).
    """
    value = getattr(candidate, field_name, None)
    if field_name == "experience":
        return bool(value and value > 0)
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, str):
        return value.strip() not in ("", "Unknown")
    return value is not None
