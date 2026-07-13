"""Skill Extractor -- Sprint 20D, extended in Sprint 20E.

Never hallucinates: a skill is only reported if its literal keyword (or
one of a small list of known aliases) appears somewhere in evidence that
actually came back from GitHub's API for this specific user -- repo
languages, repo names, repo descriptions, repo topics, or README text.
No skill is ever inferred from a role title, a recruiter query, or any
external knowledge about what skills "usually go together." Every
extracted skill is returned alongside the evidence type that produced it
(language / topic / repo_name / description / readme), so a caller can
audit exactly why a skill was attributed.

Sprint 20E addition: React and PyTorch, added after live validation
against the real deployed app proved these are exactly the kind of real,
recruiter-relevant skills GitHub's repo `language` field can never
surface on its own (they're libraries, not languages a repo is "written
in" per GitHub's linguist classification) -- yet real evidence for them
(topics, repo names, descriptions) is genuinely present on real GitHub
profiles.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

# Canonical skill name -> keyword/alias variants to search for, matched
# as whole words (case-insensitive) against text evidence, or as exact
# values against structured evidence (languages/topics). Deliberately a
# plain, auditable table -- exactly the same "no black-box inference"
# approach as app.discovery.query_translation.strategies.github's
# SKILL_TO_GITHUB_TERMS mapping.
SKILL_KEYWORDS: dict[str, list[str]] = {
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring boot", "spring-boot", "springboot"],
    "Kafka": ["kafka"],
    "Redis": ["redis"],
    "RabbitMQ": ["rabbitmq", "rabbit-mq"],
    "Docker": ["docker"],
    "Terraform": ["terraform"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "LangChain": ["langchain"],
    "LlamaIndex": ["llamaindex", "llama-index", "llama_index"],
    "RAG": ["retrieval augmented generation", "retrieval-augmented-generation", "rag"],
    "OpenAI": ["openai"],
    "Vector DB": ["vector db", "vector-db", "pinecone", "weaviate", "qdrant", "milvus", "chroma", "chromadb"],
    "ElasticSearch": ["elasticsearch", "elastic search"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb", "mongo"],
    "Neo4j": ["neo4j"],
    # --- Sprint 20E additions: proven necessary by live validation -----
    "React": ["react", "reactjs", "react.js", "react-native"],
    "PyTorch": ["pytorch", "torch"],
}


class SkillEvidence(BaseModel):
    skill: str
    evidence_type: str  # "language" | "topic" | "repo_name" | "description" | "readme"
    source: str  # the repo name (or "profile") the evidence came from


class SkillExtractionResult(BaseModel):
    skills: list[str] = Field(default_factory=list)
    evidence: list[SkillEvidence] = Field(default_factory=list)


def _contains_keyword(text: str, keyword: str) -> bool:
    if " " in keyword or "-" in keyword or "_" in keyword:
        return keyword.lower() in text.lower()
    return re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE) is not None


class SkillExtractor:
    def __init__(self, config):
        self._config = config

    def extract(
        self,
        repos: list[dict],
        readmes: dict[str, str] | None = None,
    ) -> SkillExtractionResult:
        if not self._config.enable_skill_extraction:
            return SkillExtractionResult()

        readmes = readmes or {}
        found_skills: dict[str, SkillEvidence] = {}

        def _record(skill: str, evidence_type: str, source: str) -> None:
            if skill not in found_skills:
                found_skills[skill] = SkillEvidence(skill=skill, evidence_type=evidence_type, source=source)

        for repo in repos[: self._config.max_repositories]:
            repo_name = repo.get("name", "")
            language = (repo.get("language") or "").strip()
            topics = [t for t in (repo.get("topics") or []) if t]
            description = repo.get("description") or ""
            readme_text = readmes.get(repo_name, "")

            for skill, keywords in SKILL_KEYWORDS.items():
                if skill in found_skills:
                    continue
                if language and any(_contains_keyword(language, kw) for kw in keywords):
                    _record(skill, "language", repo_name)
                    continue
                if any(any(_contains_keyword(t, kw) for kw in keywords) for t in topics):
                    _record(skill, "topic", repo_name)
                    continue
                if any(_contains_keyword(repo_name, kw) for kw in keywords):
                    _record(skill, "repo_name", repo_name)
                    continue
                if description and any(_contains_keyword(description, kw) for kw in keywords):
                    _record(skill, "description", repo_name)
                    continue
                if readme_text and any(_contains_keyword(readme_text, kw) for kw in keywords):
                    _record(skill, "readme", repo_name)

        ordered_skills = list(found_skills.keys())
        return SkillExtractionResult(
            skills=ordered_skills,
            evidence=list(found_skills.values()),
        )
