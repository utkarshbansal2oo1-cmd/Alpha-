"""Day-1 stand-in for real sources. Returns a config-driven synthetic pool so
the full pipeline can be proven end-to-end before LinkedIn/Naukri/ATS
integrations exist. Swapping this out later requires zero changes elsewhere.
"""
from __future__ import annotations

from typing import List

from .base import RawCandidate, SourceConnector

_POOL = [
    RawCandidate(
        external_id="mock-1", full_name="Asha Rao", email="asha.rao@example.com",
        phone="+91-9000000001", location="Bangalore", current_title="Senior Product Engineer",
        current_company="Acme Cloud", total_experience_yrs=8.5,
        skills=["AWS", "Kubernetes", "Python", "React"],
        summary="8.5 years building cloud-native product platforms.",
    ),
    RawCandidate(
        external_id="mock-2", full_name="Rahul Mehta", email="rahul.mehta@example.com",
        phone="+91-9000000002", location="Bangalore", current_title="Product Engineer",
        current_company="Foo Systems", total_experience_yrs=6.0,
        skills=["AWS", "Docker", "Node.js"],
        summary="6 years full-stack, recent AWS certification.",
    ),
    RawCandidate(
        external_id="mock-3", full_name="Priya Singh", email="priya.singh@example.com",
        phone="+91-9000000003", location="Hyderabad", current_title="Staff Product Engineer",
        current_company="Bar Labs", total_experience_yrs=9.0,
        skills=["Kubernetes", "AWS", "Go", "Terraform"],
        summary="9 years, deep Kubernetes/infra background, based in Hyderabad.",
    ),
    RawCandidate(
        external_id="mock-4", full_name="Karthik Iyer", email="karthik.iyer@example.com",
        phone="+91-9000000004", location="Bangalore", current_title="Backend Engineer",
        current_company="Acme Cloud", total_experience_yrs=4.0,
        skills=["Python", "PostgreSQL"],
        summary="4 years backend, no cloud infra exposure yet.",
    ),
    RawCandidate(
        external_id="mock-5", full_name="Neha Kulkarni", email="neha.kulkarni@example.com",
        phone="+91-9000000005", location="Bangalore", current_title="Principal Product Engineer",
        current_company="Acme Cloud", total_experience_yrs=11.0,
        skills=["AWS", "Kubernetes", "Java", "System Design"],
        summary="11 years, led platform re-architecture onto Kubernetes.",
    ),
]


class MockConnector(SourceConnector):
    name = "mock"

    def fetch(self, requirement) -> List[RawCandidate]:
        return list(_POOL)
