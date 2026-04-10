# tests/test_finding_generator.py
"""Tests for source-based finding generation."""
import pytest
from unittest.mock import MagicMock
from hemera.services.finding_generator import generate_findings_from_sources


def _make_source(layer, source_name, data, tier=1):
    """Create a mock SupplierSource."""
    src = MagicMock()
    src.layer = layer
    src.source_name = source_name
    src.data = data
    src.tier = tier
    return src


def test_active_company_generates_positive_finding():
    sources = [_make_source(1, "companies_house", {"status": "active", "filing_count": 15, "has_recent_filings": True})]
    findings = generate_findings_from_sources(sources, "Test Corp")
    assert any(f["title"] == "Company status: Active" and f["severity"] == "positive" for f in findings)


def test_dissolved_company_generates_high_finding():
    sources = [_make_source(1, "companies_house", {"status": "dissolved"})]
    findings = generate_findings_from_sources(sources, "Test Corp")
    assert any("dissolved" in f["title"] and f["severity"] == "high" for f in findings)


def test_sanctions_hit_generates_critical():
    sources = [_make_source(2, "opensanctions", {"is_sanctioned": True, "is_pep": False})]
    findings = generate_findings_from_sources(sources, "Test Corp")
    critical = [f for f in findings if f["severity"] == "critical"]
    assert len(critical) >= 1
    assert any("SANCTIONS" in f["title"] for f in critical)


def test_hse_enforcement_generates_high():
    sources = [_make_source(5, "hse", {"hse_enforcement_count": 3})]
    findings = generate_findings_from_sources(sources, "Test Corp")
    assert any("3 enforcement" in f["title"] and f["severity"] == "high" for f in findings)


def test_certifications_generate_positive():
    sources = [_make_source(6, "certifications", {"b_corp": True, "iso_14001": True})]
    findings = generate_findings_from_sources(sources, "Test Corp")
    positives = [f for f in findings if f["severity"] == "positive"]
    assert any("B Corp" in f["title"] for f in positives)
    assert any("ISO 14001" in f["title"] for f in positives)


def test_multiple_layers_produce_multiple_findings():
    sources = [
        _make_source(1, "companies_house", {"status": "active", "filing_count": 10, "has_recent_filings": True}),
        _make_source(4, "environment_agency", {"has_sbti_target": False, "has_cdp_disclosure": True}),
        _make_source(5, "hse", {"modern_slavery_statement": True, "hse_enforcement_count": 0}),
    ]
    findings = generate_findings_from_sources(sources, "Test Corp")
    layers_covered = {f["layer"] for f in findings}
    assert 1 in layers_covered
    assert 4 in layers_covered
    assert 5 in layers_covered


def test_finding_dict_structure():
    sources = [_make_source(1, "companies_house", {"status": "active"})]
    findings = generate_findings_from_sources(sources, "Test Corp")
    for f in findings:
        assert "source" in f and f["source"] == "deterministic"
        assert "domain" in f
        assert "severity" in f
        assert "title" in f
        assert "detail" in f
        assert "layer" in f
        assert "source_name" in f


def test_low_coverage_warning():
    sources = [_make_source(1, "companies_house", {"status": "active"})]
    findings = generate_findings_from_sources(sources, "Test Corp")
    info = [f for f in findings if f["severity"] == "info" and "coverage" in f["title"].lower()]
    assert len(info) >= 1


def test_no_sources_returns_low_coverage():
    findings = generate_findings_from_sources([], "Test Corp")
    assert len(findings) >= 1
    assert any("coverage" in f["title"].lower() for f in findings)
