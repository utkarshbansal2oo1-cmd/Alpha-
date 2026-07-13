"""Candidate Matching Engine + Ranking Engine -- Sprint 19.

New, additive package. Scores every candidate a search returns across
multiple weighted dimensions (role, skills, industry, experience,
location, education, certifications, company preference, keyword
similarity, knowledge-expansion similarity, candidate health, and
confidence), then ranks them. Nothing in Query Understanding, the
Knowledge Engine, the Search Planner, the Candidate Intelligence
Lifecycle, or CandidateRepository is modified -- this package only reads
the CanonicalJobRequirement, SearchPlan, and Candidate objects those
modules already produce.
"""
