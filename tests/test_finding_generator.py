# tests/test_finding_generator.py
"""Tests for deterministic finding generation from ESGResult."""
import pytest
from hemera.services.esg_scorer import ESGResult
from hemera.services.finding_generator import generate_findings_from_result


def test_critical_flag_generates_critical_finding():
    result = ESGResult(
        hemera_score=35.0,
        critical_flag=True,
        flags=["SANCTIONS HIT"],
        governance_identity=20.0,
        confidence="medium",
        layers_completed=6,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")
    critical = [f for f in findings if f["severity"] == "critical"]
    assert len(critical) >= 1
    assert any("SANCTIONS" in f["title"].upper() for f in critical)


def test_low_domain_generates_finding():
    result = ESGResult(
        hemera_score=55.0,
        carbon_climate=25.0,
        flags=["Environment Agency enforcement actions"],
        confidence="medium",
        layers_completed=5,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")
    carbon_findings = [f for f in findings if f["domain"] == "carbon"]
    assert len(carbon_findings) >= 1


def test_positive_findings_generated():
    result = ESGResult(
        hemera_score=78.0,
        labour_ethics=85.0,
        product_supply_chain=75.0,
        flags=[],
        confidence="high",
        layers_completed=10,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")
    positives = [f for f in findings if f["severity"] == "positive"]
    assert len(positives) >= 1


def test_all_flags_become_findings():
    result = ESGResult(
        hemera_score=30.0,
        critical_flag=True,
        flags=[
            "SANCTIONS HIT",
            "HSE: 3 enforcement actions",
            "Company dissolved or in liquidation",
        ],
        governance_identity=15.0,
        labour_ethics=30.0,
        confidence="low",
        layers_completed=3,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")
    assert len(findings) >= 3


def test_finding_dict_structure():
    result = ESGResult(
        hemera_score=60.0,
        flags=["PEP detected among directors/PSCs"],
        confidence="medium",
        layers_completed=5,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")
    for f in findings:
        assert "source" in f and f["source"] == "deterministic"
        assert "domain" in f
        assert "severity" in f
        assert "title" in f
        assert "detail" in f
        assert "source_name" in f
        assert f["domain"] in (
            "governance", "labour", "carbon", "water",
            "product", "transparency", "anti_corruption", "social_value",
        )
        assert f["severity"] in ("critical", "high", "medium", "info", "positive")


def test_domain_score_thresholds():
    result = ESGResult(
        hemera_score=45.0,
        governance_identity=20.0,
        carbon_climate=25.0,
        labour_ethics=80.0,
        flags=[],
        confidence="medium",
        layers_completed=6,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")
    domains_flagged = {f["domain"] for f in findings if f["severity"] in ("high", "medium")}
    assert "governance" in domains_flagged
    assert "carbon" in domains_flagged
    assert "labour" not in domains_flagged


def test_low_confidence_generates_info_finding():
    result = ESGResult(
        hemera_score=50.0,
        flags=[],
        confidence="low",
        layers_completed=2,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")
    info = [f for f in findings if f["severity"] == "info"]
    assert any("confidence" in f["title"].lower() or "data coverage" in f["title"].lower() for f in info)
