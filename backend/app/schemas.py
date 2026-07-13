"""Pydantic schemas shared across the API. Kept source-agnostic on purpose:
nothing here knows about LinkedIn/Naukri/ATS — that lives only in services/connectors/.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class JobRequirement(BaseModel):
    role: str
    min_experience_yrs: float = 0
    location: Optional[str] = None
    must_have_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str


class CandidateOut(BaseModel):
    candidate_id: str
    full_name: str
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    location: Optional[str] = None
    total_experience_yrs: Optional[float] = None
    match_score: float
    reasoning: str
    sources: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    search_id: str
    parsed_requirement: JobRequirement
    results: List[CandidateOut]
    count: int


class CandidateSourceOut(BaseModel):
    name: str
    external_id: str
    fetched_at: str


class CandidateDetailOut(BaseModel):
    candidate_id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    total_experience_yrs: Optional[float] = None
    skills: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    resume_url: Optional[str] = None
    sources: List[CandidateSourceOut] = Field(default_factory=list)


class SourceOut(BaseModel):
    id: str
    name: str
    type: str
    is_active: bool


class SourceCreate(BaseModel):
    name: str
    type: str
    config: dict = Field(default_factory=dict)


class ShortlistRequest(BaseModel):
    search_id: str
