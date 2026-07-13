"""Strongly typed models for the Knowledge Engine.

Every taxonomy (roles, skills, industries, company categories) shares one
shape: a Taxonomy containing TaxonomyEntry objects, each with Aliases
(same-thing-different-words, resolve inward to the canonical value) and
Expansions (related-but-distinct, directional, weighted edges to other
entries). See docs/KNOWLEDGE_ENGINE.md section 4 for the full rationale --
this module is a direct, literal implementation of that data model and
introduces no new concepts beyond it.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TaxonomyType(str, Enum):
    ROLE = "role"
    SKILL = "skill"
    INDUSTRY = "industry"
    COMPANY_CATEGORY = "company_category"


class EntryStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class Alias(BaseModel):
    """A surface form that resolves INTO a canonical value. Modeled as its
    own type (rather than a bare string) so validation logic and any future
    per-alias metadata (e.g. source, confidence) has a home without
    reshaping TaxonomyEntry.
    """

    value: str

    @field_validator("value")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("alias value must not be blank")
        return v


class Expansion(BaseModel):
    """A directional, weighted edge from one TaxonomyEntry to another
    related-but-distinct entry. `target_id` is resolved against the loaded
    taxonomy graph at load time (see loader.py) -- a dangling target_id fails
    validation and aborts startup, per docs/KNOWLEDGE_ENGINE.md section 6.
    """

    target_id: str
    weight: float = Field(ge=0.0, le=1.0)
    notes: str = ""

    @field_validator("target_id")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("expansion target_id must not be blank")
        return v


class TaxonomyEntry(BaseModel):
    """One canonical concept within a taxonomy (e.g. the role 'Product
    Engineer', or the skill 'AWS'), plus everything that resolves into it
    (aliases) and everything it broadens out to (expansions).
    """

    id: str
    canonical: str
    aliases: list[str] = Field(default_factory=list)
    expansions: list[Expansion] = Field(default_factory=list)
    status: EntryStatus = EntryStatus.ACTIVE
    created_at: date
    updated_at: date

    @field_validator("id", "canonical")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("id/canonical must not be blank")
        return v


class Taxonomy(BaseModel):
    """One taxonomy file's contents (e.g. all of skills.json)."""

    taxonomy_type: TaxonomyType
    version: str
    updated_at: date
    entries: list[TaxonomyEntry]

    @field_validator("version")
    @classmethod
    def version_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("taxonomy version must not be blank")
        return v


# --- Validation result models -------------------------------------------------


class ValidationIssue(BaseModel):
    """One structural problem found while validating a taxonomy file."""

    taxonomy_type: Optional[str] = None
    entry_id: Optional[str] = None
    message: str


class ValidationResult(BaseModel):
    """Outcome of validating one or more taxonomy files. `is_valid=False`
    means application startup must fail (see loader.py / KNOWLEDGE_ENGINE.md
    section 6: "a failed validation should hard-fail application startup").
    """

    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
