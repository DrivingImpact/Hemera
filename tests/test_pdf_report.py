"""Tests for PDF report generation."""

import pytest
from unittest.mock import MagicMock
from hemera.services.pdf_report import generate_report_data, render_report_html, generate_pdf


def _make_txn(**kwargs):
    t = MagicMock()
    t.co2e_kg = kwargs.get("co2e_kg", 100)
    t.amount_gbp = kwargs.get("amount_gbp", 1000)
    t.scope = kwargs.get("scope", 3)
    t.category_name = kwargs.get("category_name", "General")
    t.ef_level = kwargs.get("ef_level", 4)
    t.ef_source = kwargs.get("ef_source", "defra")
    t.ef_year = kwargs.get("ef_year", 2024)
    t.ef_region = kwargs.get("ef_region", "UK")
    t.gsd_total = kwargs.get("gsd_total", 1.5)
    t.pedigree_reliability = kwargs.get("pedigree_reliability", 3)
    t.pedigree_completeness = kwargs.get("pedigree_completeness", 2)
    t.pedigree_temporal = kwargs.get("pedigree_temporal", 2)
    t.pedigree_geographical = kwargs.get("pedigree_geographical", 1)
    t.pedigree_technological = kwargs.get("pedigree_technological", 4)
    t.is_duplicate = False
    t.needs_review = False
    t.raw_description = kwargs.get("raw_description", "Test item")
    t.raw_supplier = kwargs.get("raw_supplier", "Test Supplier")
    t.raw_category = kwargs.get("raw_category", "General")
    t.classification_method = kwargs.get("classification_method", "keyword")
    t.classification_confidence = kwargs.get("classification_confidence", 0.8)
    t.row_number = kwargs.get("row_number", 1)
    t.transaction_date = None
    t.ef_unit = "kgCO2e/GBP"
    t.ef_value = 0.5
    t.supplier_id = None
    return t


def _make_engagement(**kwargs):
    e = MagicMock()
    e.id = kwargs.get("id", 1)
    e.org_name = kwargs.get("org_name", "Acme Ltd")
    e.fiscal_year_start = kwargs.get("fiscal_year_start", "2024-04-01")
    e.fiscal_year_end = kwargs.get("fiscal_year_end", "2025-03-31")
    e.total_co2e = kwargs.get("total_co2e", 47.2)
    e.scope1_co2e = kwargs.get("scope1_co2e", 3.8)
    e.scope2_co2e = kwargs.get("scope2_co2e", 5.7)
    e.scope3_co2e = kwargs.get("scope3_co2e", 37.7)
    e.gsd_total = kwargs.get("gsd_total", 1.47)
    e.ci_lower = kwargs.get("ci_lower", 32.1)
    e.ci_upper = kwargs.get("ci_upper", 69.4)
    e.status = "delivered"
    return e


@pytest.fixture
def sample_engagement():
    return _make_engagement()


@pytest.fixture
def sample_transactions():
    return [
        _make_txn(scope=2, category_name="Purchased electricity", co2e_kg=5700, amount_gbp=15000, row_number=1),
        _make_txn(scope=3, category_name="Purchased goods — office supplies", co2e_kg=18600, amount_gbp=248000, row_number=2),
        _make_txn(scope=3, category_name="Business travel — air", co2e_kg=8200, amount_gbp=42000, row_number=3),
        _make_txn(scope=1, category_name="Stationary combustion — gas/heating fuel", co2e_kg=3800, amount_gbp=8000, row_number=4),
        _make_txn(scope=3, category_name="Freight & logistics", co2e_kg=5100, amount_gbp=67000, row_number=5),
    ]


class TestGenerateReportData:
    def test_returns_dict(self, sample_engagement, sample_transactions):
        data = generate_report_data(sample_engagement, sample_transactions)
        assert isinstance(data, dict)

    def test_has_required_keys(self, sample_engagement, sample_transactions):
        data = generate_report_data(sample_engagement, sample_transactions)
        required = {"org_name", "total_co2e", "scope_donut_svg", "top_categories_bar_svg",
                     "reduction_recs", "categories"}
        missing = required - set(data.keys())
        assert not missing, f"Missing: {missing}"


class TestRenderHtml:
    def test_returns_html_string(self, sample_engagement, sample_transactions):
        data = generate_report_data(sample_engagement, sample_transactions)
        html = render_report_html(data)
        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "Hemera" in html

    def test_contains_org_name(self, sample_engagement, sample_transactions):
        data = generate_report_data(sample_engagement, sample_transactions)
        html = render_report_html(data)
        assert "Acme Ltd" in html


class TestGeneratePdf:
    def test_returns_bytes(self, sample_engagement, sample_transactions):
        data = generate_report_data(sample_engagement, sample_transactions)
        html = render_report_html(data)
        pdf_bytes = generate_pdf(html)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_pdf_has_content(self, sample_engagement, sample_transactions):
        data = generate_report_data(sample_engagement, sample_transactions)
        html = render_report_html(data)
        pdf_bytes = generate_pdf(html)
        assert len(pdf_bytes) > 10000
