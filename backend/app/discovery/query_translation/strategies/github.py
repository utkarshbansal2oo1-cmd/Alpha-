"""GitHub query translation strategy -- Sprint 20C.

GitHub is not LinkedIn: its user-search index responds to language
qualifiers, ecosystem keywords, and bio/repo/topic terms, not literal
recruiter job titles ("Senior Golang Developer" performs far worse than
"golang", "go", "language:Go", "backend go", "go grpc", etc.). This
module translates a recruiter's role + skills into GitHub-native search
expressions, WITHOUT touching app/discovery/connectors/github_connector.py
itself -- the orchestrator calls that connector's unchanged discover()
once per translated expression (see orchestrator.py), passing a small
synthetic CanonicalJobRequirement whose `role` is the translated string.

Skill -> GitHub-term mapping, exactly per the sprint brief's table.
Deliberately a plain dict, not a call to Knowledge Engine (frozen this
sprint, and answers a different question -- taxonomy expansion for
matching, not connector-native search syntax).
"""
from __future__ import annotations

import re

from app.discovery.query_translation.models import ConnectorQuery
from app.search_planner.models import CanonicalJobRequirement, SearchPlan

SKILL_TO_GITHUB_TERMS: dict[str, list[str]] = {
    "python": ["python"],
    "fastapi": ["fastapi"],
    "react": ["react"],
    "node": ["nodejs"],
    "node.js": ["nodejs"],
    "nodejs": ["nodejs"],
    "go": ["golang", "language:Go"],
    "golang": ["golang", "language:Go"],
    "rust": ["rust"],
    "java": ["spring", "java"],
    "spring": ["spring", "java"],
    "kubernetes": ["kubernetes"],
    "k8s": ["kubernetes"],
    "docker": ["docker"],
    "terraform": ["terraform"],
    "langchain": ["langchain"],
    "llamaindex": ["llamaindex"],
    "rag": ["retrieval augmented generation"],
    "pytorch": ["pytorch"],
    "typescript": ["typescript"],
    "machine learning": ["machine learning", "ml"],
    "aws": ["aws"],
    "devops": ["devops"],
}

# Domain/ecosystem terms combined with the primary detected language to
# produce the "backend go", "go grpc", "go microservices"-style expansion
# terms the sprint brief's example shows -- capped by max_depth/max_queries.
_DOMAIN_COMBO_TERMS = ["backend", "grpc", "microservices", "kubernetes", "docker"]

_STOPWORDS = {
    "senior", "junior", "lead", "principal", "staff", "engineer", "engineers",
    "developer", "developers", "manager", "with", "and", "the", "a", "in",
}


def _tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    return [t for t in re.split(r"[\s,/]+", text.strip()) if t]


def build_github_queries(
    requirement: CanonicalJobRequirement,
    raw_query: str | None,
    config,
) -> tuple[list[str], float]:
    """Returns (queries, confidence). Confidence is 1.0 when at least one
    term came from an explicit SKILL_TO_GITHUB_TERMS mapping, 0.5 when
    everything fell back to raw, unmapped role tokens."""
    candidate_tokens = _tokenize(requirement.role) + _tokenize(raw_query) + list(requirement.skills)

    mapped: list[str] = []
    for token in candidate_tokens:
        key = token.strip().lower()
        if key in SKILL_TO_GITHUB_TERMS:
            mapped.extend(SKILL_TO_GITHUB_TERMS[key])

    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out = []
        for item in items:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    mapped = _dedupe(mapped)
    confidence = 1.0

    if mapped:
        base = mapped
    else:
        # No recognized skill/language -- fall back to the recruiter's own
        # significant role words (stopwords stripped) rather than a
        # fabricated technical guess.
        confidence = 0.5
        fallback_tokens = [t for t in _tokenize(requirement.role) if t.lower() not in _STOPWORDS]
        base = fallback_tokens or [requirement.role]

    queries = list(base)

    if config.expansion_enabled and config.max_depth > 0 and base:
        primary = base[0].split(":")[-1]  # e.g. "language:Go" -> "Go"
        for domain_term in _DOMAIN_COMBO_TERMS[: config.max_depth * len(_DOMAIN_COMBO_TERMS)]:
            queries.append(f"{domain_term} {primary}".strip())

    queries = _dedupe(queries)
    return queries[: config.max_queries_per_connector], confidence


def translate(
    connector_name: str,
    requirement: CanonicalJobRequirement,
    raw_query: str | None,
    plan: SearchPlan,
    config,
) -> ConnectorQuery:
    queries, confidence = build_github_queries(requirement, raw_query, config)

    filters: dict[str, str] = {}
    for query in queries:
        if ":" in query:
            key, _, value = query.partition(":")
            filters[key.strip()] = value.strip()

    return ConnectorQuery(
        connector_name=connector_name,
        original_query=raw_query or requirement.role,
        connector_queries=queries,
        filters=filters,
        metadata={"strategy": "github", "passthrough": False},
        confidence=confidence,
    )
