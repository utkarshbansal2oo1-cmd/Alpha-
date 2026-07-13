"""Builds the structured prompt sent to the LLM client.

Per the Knowledge Engine design (docs/KNOWLEDGE_ENGINE.md section 9): the
LLM's only job is to extract canonical recruiter INTENT -- it must never
generate synonyms, related skills, or related roles. That expansion is the
Knowledge Engine's job (already implemented, approved, and frozen). This
prompt is written to make that boundary explicit to the model, not just
assumed.

The prompt asks for exactly the fields CanonicalJobRequirement needs today
(role, skills) -- see app.query_understanding.models for why that type is
reused rather than redefined. If/when CanonicalJobRequirement grows new
fields, this prompt's JSON schema section is the only thing that needs to
change to match.
"""
from __future__ import annotations

_RESPONSE_JSON_SCHEMA = """{
  "role": "<the single job role/title the recruiter is hiring for, as they stated it>",
  "skills": ["<each distinct skill the recruiter explicitly mentioned>", "..."]
}"""

_BASE_INSTRUCTIONS = f"""You are an information-extraction system for a recruiting platform.
Your ONLY task is to read a recruiter's free-text hiring request and extract
their stated intent into a strict JSON object.

Rules you MUST follow:
1. Extract ONLY what the recruiter actually said. Do not add related roles,
   related skills, or synonyms. Do not infer skills that were not mentioned.
2. Do not invent a value for a field if it was not stated -- for "role",
   use your best literal reading of the job title/function mentioned; for
   "skills", return an empty list if no skills were mentioned.
3. Respond with STRICT JSON ONLY. No markdown code fences, no commentary,
   no explanation text before or after the JSON. The entire response body
   must be a single JSON object parseable by a standard JSON parser.
4. The JSON object must have exactly this shape:

{_RESPONSE_JSON_SCHEMA}

Recruiter's request:
"""


class PromptBuilder:
    """Turns a raw recruiter query (and, on retry, the previous attempt's
    validation error) into the exact prompt string sent to the LLM client.
    Contains no LLM-calling logic itself -- purely string construction, so
    it can be unit tested without any network access and swapped/tuned
    independently of which LLM provider is behind gemini_client.py.
    """

    def build(self, raw_query: str, retry_hint: str | None = None) -> str:
        """Builds the prompt for a fresh attempt, or for the single retry
        attempt when `retry_hint` (the previous error message) is supplied.
        Per the required pipeline, retry happens at most once -- this
        method has no memory of attempt count; service.py owns that limit.
        """
        prompt = f"{_BASE_INSTRUCTIONS}{raw_query.strip()}"

        if retry_hint:
            prompt += (
                "\n\nYour previous response was invalid for this reason: "
                f"{retry_hint}\n"
                "Correct this and respond again with STRICT JSON ONLY, "
                "following the exact shape above."
            )

        return prompt
