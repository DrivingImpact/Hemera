"""Tests for engagement detail endpoints."""

from datetime import date
from unittest.mock import MagicMock
import pytest
from hemera.services.engagement_data import (
    build_category_summary,
    build_monthly_summary,
    build_engagement_suppliers,
)


def _make_txn(**kwargs):
    t = MagicMock()
    t.co2e_kg = kwargs.get("co2e_kg", 100)
    t.amount_gbp = kwargs.get("amount_gbp", 1000)
    t.scope = kwargs.get("scope", 3)
    t.category_name = kwargs.get("category_name", "General")
    t.gsd_total = kwargs.get("gsd_total", 1.5)
    t.is_duplicate = kwargs.get("is_duplicate", False)
    t.transaction_date = kwargs.get("transaction_date", None)
    t.supplier_id = kwargs.get("supplier_id", None)
    t.raw_supplier = kwargs.get("raw_supplier", "Test Supplier")
    return t


class TestBuildCategorySummary:
    def test_groups_by_category(self):
        txns = [
            _make_txn(category_name="Electricity", co2e_kg=5000, scope=2, amount_gbp=2000),
            _make_txn(category_name="Electricity", co2e_kg=3000, scope=2, amount_gbp=1000),
            _make_txn(category_name="Travel", co2e_kg=2000, scope=3, amount_gbp=500),
        ]
        result = build_category_summary(txns)
        assert len(result) == 2
        elec = next(c for c in result if c["name"] == "Electricity")
        assert elec["co2e_tonnes"] == 8.0
        assert elec["spend_gbp"] == 3000
        assert elec["scope"] == 2

    def test_sorted_descending_by_co2e(self):
        txns = [
            _make_txn(category_name="Small", co2e_kg=100),
            _make_txn(category_name="Big", co2e_kg=9000),
        ]
        result = build_category_summary(txns)
        assert result[0]["name"] == "Big"

    def test_skips_duplicates(self):
        txns = [
            _make_txn(category_name="A", co2e_kg=500, is_duplicate=True),
            _make_txn(category_name="A", co2e_kg=500, is_duplicate=False),
        ]
        result = build_category_summary(txns)
        assert result[0]["co2e_tonnes"] == 0.5

    def test_returns_gsd_average(self):
        txns = [
            _make_txn(category_name="A", co2e_kg=100, gsd_total=1.2),
            _make_txn(category_name="A", co2e_kg=100, gsd_total=1.8),
        ]
        result = build_category_summary(txns)
        assert result[0]["gsd"] == pytest.approx(1.5)


class TestBuildMonthlySummary:
    def test_returns_no_data_when_few_dates(self):
        txns = [
            _make_txn(transaction_date=None),
            _make_txn(transaction_date=None),
            _make_txn(transaction_date=date(2024, 1, 15)),
        ]
        result = build_monthly_summary(txns)
        assert result["has_data"] is False
        assert result["months"] == []

    def test_groups_by_month_and_scope(self):
        txns = [
            _make_txn(transaction_date=date(2024, 1, 10), co2e_kg=1000, scope=2),
            _make_txn(transaction_date=date(2024, 1, 20), co2e_kg=2000, scope=3),
            _make_txn(transaction_date=date(2024, 2, 5), co2e_kg=500, scope=3),
        ]
        result = build_monthly_summary(txns)
        assert result["has_data"] is True
        months = result["months"]
        jan = next(m for m in months if m["month"] == "2024-01")
        assert jan["scope2"] == pytest.approx(1.0)
        assert jan["scope3"] == pytest.approx(2.0)
        feb = next(m for m in months if m["month"] == "2024-02")
        assert feb["scope3"] == pytest.approx(0.5)

    def test_sorted_by_month(self):
        txns = [
            _make_txn(transaction_date=date(2024, 3, 1), co2e_kg=100, scope=3),
            _make_txn(transaction_date=date(2024, 1, 1), co2e_kg=100, scope=3),
        ]
        result = build_monthly_summary(txns)
        assert result["months"][0]["month"] == "2024-01"

    def test_skips_duplicates(self):
        txns = [
            _make_txn(transaction_date=date(2024, 1, 1), co2e_kg=500, scope=3, is_duplicate=True),
            _make_txn(transaction_date=date(2024, 1, 1), co2e_kg=500, scope=3, is_duplicate=False),
        ]
        result = build_monthly_summary(txns)
        jan = result["months"][0]
        assert jan["scope3"] == pytest.approx(0.5)


class TestBuildEngagementSuppliers:
    def test_groups_by_supplier(self):
        txns = [
            _make_txn(supplier_id=1, raw_supplier="Acme", co2e_kg=1000, amount_gbp=500),
            _make_txn(supplier_id=1, raw_supplier="Acme", co2e_kg=2000, amount_gbp=1000),
            _make_txn(supplier_id=2, raw_supplier="Beta", co2e_kg=500, amount_gbp=250),
        ]
        result = build_engagement_suppliers(txns)
        assert len(result) == 2
        acme = next(s for s in result if s["name"] == "Acme")
        assert acme["co2e_tonnes"] == pytest.approx(3.0)
        assert acme["spend_gbp"] == 1500
        assert acme["transaction_count"] == 2

    def test_sorted_descending_by_co2e(self):
        txns = [
            _make_txn(supplier_id=1, raw_supplier="Small", co2e_kg=100, amount_gbp=100),
            _make_txn(supplier_id=2, raw_supplier="Large", co2e_kg=9000, amount_gbp=500),
        ]
        result = build_engagement_suppliers(txns)
        assert result[0]["name"] == "Large"

    def test_skips_duplicates(self):
        txns = [
            _make_txn(supplier_id=1, raw_supplier="Dup", co2e_kg=500, amount_gbp=200, is_duplicate=True),
            _make_txn(supplier_id=1, raw_supplier="Dup", co2e_kg=500, amount_gbp=200, is_duplicate=False),
        ]
        result = build_engagement_suppliers(txns)
        assert result[0]["co2e_tonnes"] == pytest.approx(0.5)
        assert result[0]["transaction_count"] == 1

    def test_intensity_calculation(self):
        txns = [
            _make_txn(supplier_id=1, raw_supplier="S1", co2e_kg=1000, amount_gbp=500),
        ]
        result = build_engagement_suppliers(txns)
        assert result[0]["intensity_kg_per_gbp"] == pytest.approx(2.0)

    def test_zero_intensity_when_no_spend(self):
        txns = [
            _make_txn(supplier_id=1, raw_supplier="S1", co2e_kg=1000, amount_gbp=0),
        ]
        result = build_engagement_suppliers(txns)
        assert result[0]["intensity_kg_per_gbp"] == 0
