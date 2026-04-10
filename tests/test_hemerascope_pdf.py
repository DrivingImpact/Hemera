"""Tests for HemeraScope PDF report generation."""

import pytest
from unittest.mock import MagicMock, patch
from hemera.services.hemerascope_report import (
    generate_hemerascope_data,
    render_hemerascope_html,
    chart_risk_donut,
    chart_domain_bar,
    chart_supplier_scores,
)


def _make_engagement(**kwargs):
    e = MagicMock()
    e.id = kwargs.get("id", 1)
    e.org_name = kwargs.get("org_name", "Acme Ltd")
    e.display_name = kwargs.get("display_name", None)
    e.fiscal_year_start = kwargs.get("fiscal_year_start", "2024-04-01")
    e.fiscal_year_end = kwargs.get("fiscal_year_end", "2025-03-31")
    e.total_co2e = kwargs.get("total_co2e", 47.2)
    e.scope1_co2e = kwargs.get("scope1_co2e", 3.8)
    e.scope2_co2e = kwargs.get("scope2_co2e", 5.7)
    e.scope3_co2e = kwargs.get("scope3_co2e", 37.7)
    e.ci_lower = kwargs.get("ci_lower", 32.1)
    e.ci_upper = kwargs.get("ci_upper", 69.4)
    e.data_quality_grade = kwargs.get("data_quality_grade", "C")
    e.supplier_report_status = kwargs.get("supplier_report_status", "published")
    return e


class TestChartGeneration:
    def test_risk_donut_returns_svg(self):
        svg = chart_risk_donut({"critical": 2, "high": 5, "medium": 8, "positive": 3})
        assert isinstance(svg, str)
        assert "<svg" in svg

    def test_risk_donut_empty_returns_empty(self):
        svg = chart_risk_donut({})
        assert svg == ""

    def test_domain_bar_returns_svg(self):
        svg = chart_domain_bar({"governance": 3, "labour": 5, "carbon": 2})
        assert isinstance(svg, str)
        assert "<svg" in svg

    def test_domain_bar_empty_returns_empty(self):
        svg = chart_domain_bar({})
        assert svg == ""

    def test_supplier_scores_returns_svg(self):
        suppliers = [
            {"supplier": {"name": "Supplier A", "hemera_score": 72, "critical_flag": False}},
            {"supplier": {"name": "Supplier B", "hemera_score": 45, "critical_flag": True}},
        ]
        svg = chart_supplier_scores(suppliers)
        assert isinstance(svg, str)
        assert "<svg" in svg

    def test_supplier_scores_no_scores_returns_empty(self):
        suppliers = [
            {"supplier": {"name": "Supplier A", "hemera_score": None, "critical_flag": False}},
        ]
        svg = chart_supplier_scores(suppliers)
        assert svg == ""


class TestRenderHtml:
    def test_renders_html_with_data(self):
        data = {
            "org_name": "Acme Ltd",
            "fiscal_year_start": "2024-04-01",
            "fiscal_year_end": "2025-03-31",
            "generated_date": "09 April 2026",
            "total_co2e": 47.2,
            "scope3": 37.7,
            "data_quality_grade": "C",
            "supplier_count": 3,
            "avg_hemera_score": 65.0,
            "critical_count": 1,
            "total_findings": 12,
            "high_severity_count": 4,
            "positive_count": 2,
            "engaged_count": 2,
            "risk_donut_svg": "<svg>mock</svg>",
            "domain_bar_svg": "<svg>mock</svg>",
            "supplier_score_bar_svg": "<svg>mock</svg>",
            "severity_counts": {"critical": 1, "high": 3, "medium": 5, "info": 1, "positive": 2},
            "supplier_pages": [
                {
                    "supplier": {
                        "name": "Test Supplier",
                        "legal_name": "Test Supplier Ltd",
                        "ch_number": "12345678",
                        "sector": "Technology",
                        "entity_type": "ltd",
                        "hemera_score": 65.0,
                        "confidence": "medium",
                        "critical_flag": False,
                    },
                    "txn_count": 5,
                    "total_spend": 50000,
                    "total_co2e_kg": 1200,
                    "findings": [
                        {"title": "Test finding", "detail": "Some detail", "severity": "medium", "domain": "governance"},
                    ],
                    "actions": [
                        {"action_text": "Request updated filing", "priority": 1},
                    ],
                    "engagements": [],
                },
            ],
            "priority_1_actions": [{"supplier_name": "Test Supplier", "action_text": "Request updated filing"}],
            "priority_2_actions": [],
            "priority_3_actions": [],
        }
        html = render_hemerascope_html(data)
        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "Acme Ltd" in html
        assert "HemeraScope" in html
        assert "Test Supplier" in html

    def test_contains_methodology(self):
        data = {
            "org_name": "Acme Ltd",
            "fiscal_year_start": "2024-04-01",
            "fiscal_year_end": "2025-03-31",
            "generated_date": "09 April 2026",
            "total_co2e": 0,
            "scope3": 0,
            "data_quality_grade": "",
            "supplier_count": 0,
            "avg_hemera_score": 0,
            "critical_count": 0,
            "total_findings": 0,
            "high_severity_count": 0,
            "positive_count": 0,
            "engaged_count": 0,
            "risk_donut_svg": "",
            "domain_bar_svg": "",
            "supplier_score_bar_svg": "",
            "severity_counts": {},
            "supplier_pages": [],
            "priority_1_actions": [],
            "priority_2_actions": [],
            "priority_3_actions": [],
        }
        html = render_hemerascope_html(data)
        assert "Our Approach" in html
        assert "8 weighted ESG domains" in html
        # Should NOT reveal the 13-layer protocol
        assert "13-layer" not in html
        assert "13 layer" not in html
