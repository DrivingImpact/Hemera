# tests/test_ai_prompt_builder.py
"""Tests for AI prompt construction."""
import pytest
from hemera.services.ai_prompt_builder import build_prompt


def test_risk_analysis_prompt_contains_supplier_data():
    prompt = build_prompt(
        task_type="risk_analysis",
        context={
            "supplier_name": "Tesco PLC",
            "sector": "Retail",
            "sic_codes": ["47110"],
            "sources_summary": [
                {"layer": 1, "source": "companies_house", "summary": "Active company, 15 filings"},
                {"layer": 4, "source": "environment_agency", "summary": "2 enforcement notices"},
            ],
            "deterministic_findings": [
                {"title": "EA enforcement actions", "severity": "high"},
            ],
            "hemera_score": 38.0,
            "domain_scores": {"governance": 22, "carbon": 28},
        },
    )
    assert "Tesco PLC" in prompt
    assert "Retail" in prompt
    assert "enforcement" in prompt.lower()
    assert len(prompt) > 200


def test_client_language_prompt():
    prompt = build_prompt(
        task_type="client_language",
        context={
            "supplier_name": "Tesco PLC",
            "findings": [
                {"title": "EA enforcement actions", "detail": "2 active enforcement notices", "severity": "high"},
                {"title": "ISO 14001 certified", "detail": "Holds certification", "severity": "positive"},
            ],
        },
    )
    assert "professional" in prompt.lower() or "client" in prompt.lower()
    assert "constructive" in prompt.lower() or "collaborative" in prompt.lower()


def test_recommended_actions_prompt():
    prompt = build_prompt(
        task_type="recommended_actions",
        context={
            "supplier_name": "Tesco PLC",
            "findings": [{"title": "No SBTi target", "domain": "carbon"}],
        },
    )
    assert "Hemera" in prompt
    assert "action" in prompt.lower()


def test_engagement_summary_prompt():
    prompt = build_prompt(
        task_type="engagement_summary",
        context={
            "supplier_name": "Tesco PLC",
            "engagements": [
                {"type": "email", "date": "2026-03-01", "notes": "Positive response"},
            ],
        },
    )
    assert "Tesco PLC" in prompt
    assert "engagement_summary" in prompt
    # Reframed as a forward-looking strategy, not a retrospective summary.
    assert "forward-looking" in prompt.lower() or "strategy" in prompt.lower()


def test_recommended_actions_uses_upstream_risk_analysis():
    """When risk_analysis is in context, the prompt must guide the model to
    act on verified findings and ignore registry gaps."""
    prompt = build_prompt(
        task_type="recommended_actions",
        context={
            "supplier_name": "Tesco PLC",
            "findings": [{"title": "Energy intensity"}],
            "risk_analysis": {
                "risk_summary": "Moderate carbon exposure",
                "verified_findings": [
                    {"original_title": "No MS statement", "verdict": "likely_registry_gap", "confidence": "high"},
                    {"original_title": "Energy intensity above peers", "verdict": "correct", "confidence": "medium"},
                ],
                "additional_risks": [{"risk": "Scope 3 tail", "severity": "high", "rationale": "sector"}],
                "opportunities": [{"opportunity": "SBTi validated", "evidence": "public"}],
            },
        },
    )
    assert "Energy intensity above peers" in prompt
    assert "Scope 3 tail" in prompt
    # The registry-gap finding must be called out so it's not actioned.
    assert "registry gap" in prompt.lower() or "No MS statement" in prompt


def test_engagement_strategy_uses_upstream_plan():
    """Engagement strategy must anchor in the action plan's posture + actions."""
    prompt = build_prompt(
        task_type="engagement_summary",
        context={
            "supplier_name": "Tesco PLC",
            "engagements": [],
            "risk_analysis": {"risk_summary": "Material exposure"},
            "recommended_actions": {
                "strategic_posture": "remediate",
                "posture_rationale": "carbon exposure",
                "recommended_actions": [
                    {"action": "Quarterly disclosure", "priority": "high", "timeframe": "90d", "hemera_role": "facilitate"},
                ],
            },
        },
    )
    assert "remediate" in prompt
    assert "Quarterly disclosure" in prompt


def test_exec_summary_prompt():
    prompt = build_prompt(
        task_type="exec_summary",
        context={
            "org_name": "Acme Retail",
            "supplier_count": 24,
            "total_spend": 4200000,
            "critical_count": 3,
            "attention_count": 7,
            "strong_count": 14,
        },
    )
    assert "Acme Retail" in prompt
    assert "24" in prompt


def test_all_prompts_include_response_format():
    for task_type in ["risk_analysis", "client_language", "recommended_actions", "engagement_summary", "exec_summary"]:
        prompt = build_prompt(task_type=task_type, context=_minimal_context(task_type))
        assert "json" in prompt.lower() or "format" in prompt.lower() or "respond" in prompt.lower()


def _minimal_context(task_type):
    if task_type == "risk_analysis":
        return {"supplier_name": "X", "sector": "Y", "sic_codes": [], "sources_summary": [], "deterministic_findings": [], "hemera_score": 50, "domain_scores": {}}
    if task_type in ("client_language", "recommended_actions"):
        return {"supplier_name": "X", "findings": []}
    if task_type == "engagement_summary":
        return {"supplier_name": "X", "engagements": []}
    return {"org_name": "X", "supplier_count": 0, "total_spend": 0, "critical_count": 0, "attention_count": 0, "strong_count": 0}
