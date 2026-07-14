"""Tests for the Query Understanding Engine.

No real Gemini calls anywhere in this file -- every test injects a
FakeLLMClient (a minimal LLMClient implementation returning canned text,
shared with routers/tests_search_pipeline.py via app.testing.fakes) via the
same dependency-injection seam service.py exposes for real providers. This
is deliberately the whole point of the DI design: the pipeline's control
flow (prompt -> call -> parse -> validate -> retry once) is fully testable
without network access or an API key, and the same FakeLLMClient pattern is
exactly how an OpenAI/Claude client would be substituted later.
"""
from __future__ import annotations

import pytest

from app.query_understanding.models import (
    LLMClientError,
    QueryValidationError,
    ResponseParseError,
)
from app.query_understanding.parser import JSONResponseParser
from app.query_understanding.prompt_builder import PromptBuilder
from app.query_understanding.service import QueryUnderstandingService
from app.query_understanding.validator import QueryValidator
from app.search_planner.models import CanonicalJobRequirement
from app.search_planner.planner import SearchPlanner
from app.testing.fakes import FakeLLMClient


def test_prompt_builder_includes_raw_query():
    prompt = PromptBuilder().build("Product Engineer with 7+ years in Bangalore")
    assert "Product Engineer with 7+ years in Bangalore" in prompt


def test_prompt_builder_instructs_no_synonym_generation():
    prompt = PromptBuilder().build("Backend Developer who knows AWS")
    assert "Do not add related roles" in prompt or "synonyms" in prompt.lower()


def test_prompt_builder_without_retry_hint_has_no_correction_text():
    prompt = PromptBuilder().build("Data Scientist with ML and Python")
    assert "previous response was invalid" not in prompt


def test_prompt_builder_with_retry_hint_includes_it():
    prompt = PromptBuilder().build("Data Scientist with ML and Python", retry_hint="missing 'role'")
    assert "previous response was invalid" in prompt
    assert "missing 'role'" in prompt


def test_parser_parses_clean_json():
    data = JSONResponseParser().parse('{"role": "Product Engineer", "skills": ["AWS"]}')
    assert data == {"role": "Product Engineer", "skills": ["AWS"]}


def test_parser_strips_markdown_code_fences():
    raw = '```json\n{"role": "Product Engineer", "skills": ["AWS"]}\n```'
    data = JSONResponseParser().parse(raw)
    assert data == {"role": "Product Engineer", "skills": ["AWS"]}


def test_parser_raises_on_invalid_json():
    with pytest.raises(ResponseParseError):
        JSONResponseParser().parse("{not valid json")


def test_parser_raises_on_non_object_json():
    with pytest.raises(ResponseParseError):
        JSONResponseParser().parse("[1, 2, 3]")


def test_parser_raises_on_none():
    with pytest.raises(ResponseParseError):
        JSONResponseParser().parse(None)


def test_parser_raises_on_empty_string():
    with pytest.raises(ResponseParseError):
        JSONResponseParser().parse("   ")


def test_validator_accepts_well_formed_data():
    result = QueryValidator().validate({"role": "Product Engineer", "skills": ["AWS", "Kubernetes"]})
    assert isinstance(result, CanonicalJobRequirement)
    assert result.role == "Product Engineer"
    assert result.skills == ["AWS", "Kubernetes"]


def test_validator_defaults_missing_skills_to_empty_list():
    result = QueryValidator().validate({"role": "Product Manager"})
    assert result.skills == []


def test_validator_rejects_missing_role():
    with pytest.raises(QueryValidationError):
        QueryValidator().validate({"skills": ["AWS"]})


def test_validator_rejects_blank_role():
    with pytest.raises(QueryValidationError):
        QueryValidator().validate({"role": "   ", "skills": []})


def test_validator_rejects_non_string_role():
    with pytest.raises(QueryValidationError):
        QueryValidator().validate({"role": 123, "skills": []})


def test_validator_rejects_non_list_skills():
    with pytest.raises(QueryValidationError):
        QueryValidator().validate({"role": "Data Scientist", "skills": "Python"})


def test_validator_rejects_non_string_skill_items():
    with pytest.raises(QueryValidationError):
        QueryValidator().validate({"role": "Data Scientist", "skills": ["Python", 42]})


def test_validator_rejects_unexpected_fields():
    with pytest.raises(QueryValidationError):
        QueryValidator().validate(
            {"role": "Data Scientist", "skills": [], "location": "Bangalore"}
        )


def test_validator_strips_whitespace_from_skills():
    result = QueryValidator().validate({"role": "Data Scientist", "skills": ["  AWS  ", ""]})
    assert result.skills == ["AWS"]


def test_service_happy_path_first_attempt_succeeds():
    fake_llm = FakeLLMClient(['{"role": "Product Engineer", "skills": ["AWS", "Kubernetes"]}'])
    service = QueryUnderstandingService(llm_client=fake_llm)

    result = service.parse("Product Engineer with 7+ years in Bangalore, skilled in AWS and Kubernetes")

    assert isinstance(result, CanonicalJobRequirement)
    assert result.role == "Product Engineer"
    assert result.skills == ["AWS", "Kubernetes"]
    assert len(fake_llm.prompts_received) == 1


def test_service_retries_once_on_invalid_json_then_succeeds():
    fake_llm = FakeLLMClient(
        [
            "this is not json at all",
            '{"role": "Backend Developer", "skills": ["AWS", "Kubernetes"]}',
        ]
    )
    service = QueryUnderstandingService(llm_client=fake_llm)

    result = service.parse("Backend Developer who knows AWS and Kubernetes")

    assert result.role == "Backend Developer"
    assert len(fake_llm.prompts_received) == 2
    assert "previous response was invalid" in fake_llm.prompts_received[1]


def test_service_retries_once_on_validation_failure_then_succeeds():
    fake_llm = FakeLLMClient(
        [
            '{"skills": ["Python"]}',
            '{"role": "Data Scientist", "skills": ["Python", "ML"]}',
        ]
    )
    service = QueryUnderstandingService(llm_client=fake_llm)

    result = service.parse("Data Scientist with ML and Python")

    assert result.role == "Data Scientist"
    assert len(fake_llm.prompts_received) == 2


def test_service_raises_after_second_failure_no_further_retry():
    fake_llm = FakeLLMClient(["not json", "still not json"])
    service = QueryUnderstandingService(llm_client=fake_llm)

    with pytest.raises(ResponseParseError):
        service.parse("Product Manager from FinTech")

    assert len(fake_llm.prompts_received) == 2


def test_service_rejects_empty_recruiter_query():
    fake_llm = FakeLLMClient([])
    service = QueryUnderstandingService(llm_client=fake_llm)

    with pytest.raises(QueryValidationError):
        service.parse("   ")

    assert fake_llm.prompts_received == []


def test_service_uses_injected_collaborators_not_hardcoded_ones():
    fake_llm = FakeLLMClient(['{"role": "X", "skills": []}'])
    custom_prompt_builder = PromptBuilder()
    custom_parser = JSONResponseParser()
    custom_validator = QueryValidator()

    service = QueryUnderstandingService(
        llm_client=fake_llm,
        prompt_builder=custom_prompt_builder,
        response_parser=custom_parser,
        validator=custom_validator,
    )
    assert service._llm_client is fake_llm
    assert service._prompt_builder is custom_prompt_builder
    assert service._response_parser is custom_parser
    assert service._validator is custom_validator


class _AlwaysFailingLLMClient:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("simulated provider outage")


def test_service_wraps_llm_client_failure_in_llm_client_error():
    service = QueryUnderstandingService(llm_client=_AlwaysFailingLLMClient())

    with pytest.raises(LLMClientError):
        service.parse("Product Engineer with AWS")


def test_service_does_not_retry_on_llm_client_failure():
    failing_client = _AlwaysFailingLLMClient()
    calls = {"count": 0}
    original_generate = failing_client.generate

    def counting_generate(prompt: str) -> str:
        calls["count"] += 1
        return original_generate(prompt)

    failing_client.generate = counting_generate
    service = QueryUnderstandingService(llm_client=failing_client)

    with pytest.raises(LLMClientError):
        service.parse("Product Engineer with AWS")

    assert calls["count"] == 1


def test_output_feeds_directly_into_search_planner():
    fake_llm = FakeLLMClient(['{"role": "Product Engineer", "skills": ["AWS"]}'])
    service = QueryUnderstandingService(llm_client=fake_llm)

    requirement = service.parse(
        "Find Product Engineers with 7+ years of experience in Bangalore, skilled in AWS"
    )

    plan = SearchPlanner().build_plan(requirement)

    strict_values = {f.canonical_value for f in plan.strict}
    assert strict_values == {"Product Engineer", "AWS"}
    expanded_values = {f.expanded_value for f in plan.expanded}
    assert "EC2" in expanded_values
    assert "Backend Engineer" in expanded_values
