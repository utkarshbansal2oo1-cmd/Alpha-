"""Tests for OrganizationAnalyzer -- Sprint 20D."""
from __future__ import annotations

from app.integrations.github.intelligence.config import GitHubIntelligenceConfig
from app.integrations.github.intelligence.organization_analyzer import OrganizationAnalyzer


def test_analyze_reads_company_field_from_profile():
    analyzer = OrganizationAnalyzer(GitHubIntelligenceConfig())
    result = analyzer.analyze({"company": "@github"}, None)

    assert result.company == "@github"
    assert result.organizations == []
    assert result.organization_count == 0
    assert result.verified_organization is False


def test_analyze_collects_public_org_memberships():
    analyzer = OrganizationAnalyzer(GitHubIntelligenceConfig())
    orgs = [{"login": "octo-org", "type": "Organization"}, {"login": "octo-team", "type": "Organization"}]
    result = analyzer.analyze({"company": None}, orgs)

    assert set(result.organizations) == {"octo-org", "octo-team"}
    assert result.organization_count == 2
    assert result.verified_organization is True


def test_analyze_handles_no_orgs_gracefully():
    analyzer = OrganizationAnalyzer(GitHubIntelligenceConfig())
    result = analyzer.analyze({"company": None}, [])

    assert result.organizations == []
    assert result.organization_count == 0
    assert result.verified_organization is False


def test_analyze_skips_orgs_missing_login():
    analyzer = OrganizationAnalyzer(GitHubIntelligenceConfig())
    result = analyzer.analyze({}, [{"type": "Organization"}])

    assert result.organizations == []
    assert result.organization_count == 0
