"""Tests for reduction recommendation engine."""

import pytest
from unittest.mock import MagicMock
from hemera.services.reduction_recs import generate_reduction_recommendations, compute_projections


def _make_txn(**kwargs):
    t = MagicMock()
    t.co2e_kg = kwargs.get("co2e_kg", 100)
    t.amount_gbp = kwargs.get("amount_gbp", 1000)
    t.scope = kwargs.get("scope", 3)
    t.category_name = kwargs.get("category_name", "General")
    t.ef_level = kwargs.get("ef_level", 4)
    t.gsd_total = kwargs.get("gsd_total", 1.5)
    t.is_duplicate = False
    t.raw_supplier = kwargs.get("raw_supplier", "Supplier A")
    return t


class TestReductionRecommendations:
    def test_returns_list(self):
        txns = [_make_txn(scope=2, category_name="Purchased electricity", co2e_kg=5700)]
        result = generate_reduction_recommendations(txns)
        assert isinstance(result, list)

    def test_electricity_gets_renewable_recommendation(self):
        txns = [_make_txn(scope=2, category_name="Purchased electricity", co2e_kg=5700)]
        result = generate_reduction_recommendations(txns)
        energy_recs = [r for r in result if r["type"] == "energy"]
        assert len(energy_recs) >= 1
        assert energy_recs[0]["potential_reduction_kg"] > 0

    def test_travel_gets_reduction_recommendation(self):
        txns = [_make_txn(scope=3, category_name="Business travel — air", co2e_kg=8200)]
        result = generate_reduction_recommendations(txns)
        transport_recs = [r for r in result if r["type"] == "transport"]
        assert len(transport_recs) >= 1

    def test_all_recs_have_required_fields(self):
        txns = [
            _make_txn(scope=2, category_name="Purchased electricity", co2e_kg=5700),
            _make_txn(scope=3, category_name="Business travel — air", co2e_kg=8200),
        ]
        result = generate_reduction_recommendations(txns)
        required = {"type", "category", "current_co2e_kg", "potential_reduction_pct",
                     "potential_reduction_kg", "effort", "timeline", "explanation"}
        for r in result:
            missing = required - set(r.keys())
            assert not missing, f"Missing: {missing} in {r.get('category', '?')}"

    def test_sorted_by_reduction_potential(self):
        txns = [
            _make_txn(scope=2, category_name="Purchased electricity", co2e_kg=5700),
            _make_txn(scope=3, category_name="Business travel — air", co2e_kg=8200),
            _make_txn(scope=1, category_name="Stationary combustion — gas/heating fuel", co2e_kg=3800),
        ]
        result = generate_reduction_recommendations(txns)
        if len(result) >= 2:
            assert result[0]["potential_reduction_kg"] >= result[1]["potential_reduction_kg"]


class TestProjections:
    def test_returns_dict(self):
        result = compute_projections(
            total_co2e_kg=47200, ci_lower_kg=32100, ci_upper_kg=69400,
            reduction_recs=[{"potential_reduction_kg": 4500}, {"potential_reduction_kg": 2100}],
            data_quality_recs=[{"projected_avg_gsd": 1.2, "current_avg_gsd": 1.5}],
        )
        assert isinstance(result, dict)

    def test_year3_target_lower_than_baseline(self):
        result = compute_projections(
            total_co2e_kg=47200, ci_lower_kg=32100, ci_upper_kg=69400,
            reduction_recs=[{"potential_reduction_kg": 4500}],
            data_quality_recs=[],
        )
        assert result["year3_target_kg"] < 47200

    def test_year2_ci_narrower_than_baseline(self):
        result = compute_projections(
            total_co2e_kg=47200, ci_lower_kg=32100, ci_upper_kg=69400,
            reduction_recs=[],
            data_quality_recs=[{"projected_avg_gsd": 1.2, "current_avg_gsd": 1.8}],
        )
        baseline_width = 69400 - 32100
        year2_width = result["year2_ci_upper_kg"] - result["year2_ci_lower_kg"]
        assert year2_width < baseline_width
