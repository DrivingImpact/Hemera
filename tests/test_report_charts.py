"""Tests for report chart generation."""

import pytest
from hemera.services.report_charts import (
    HEMERA_THEME, chart_scope_donut, chart_top_categories_bar,
    chart_scope_stacked_bar, chart_scope_category_bars, chart_spend_vs_emissions_scatter,
    chart_monthly_stacked_area, chart_cumulative_line,
    chart_error_bars, chart_pedigree_radar, chart_pedigree_contribution_bar,
    chart_cascade_grouped_bar, chart_reduction_quadrant, chart_reduction_waterfall,
    chart_reduction_potential_bar, chart_projection_fan, chart_projection_waterfall,
    chart_impact_bar,
)


class TestHemeraTheme:
    def test_theme_has_colorway(self):
        assert "layout" in HEMERA_THEME
        assert "colorway" in HEMERA_THEME["layout"]
        assert "#1E293B" in HEMERA_THEME["layout"]["colorway"]
        assert "#0D9488" in HEMERA_THEME["layout"]["colorway"]
        assert "#F59E0B" in HEMERA_THEME["layout"]["colorway"]

    def test_theme_has_font(self):
        assert "Plus Jakarta Sans" in HEMERA_THEME["layout"]["font"]["family"]


class TestScopeDonut:
    def test_returns_svg_string(self):
        svg = chart_scope_donut(scope1=3.8, scope2=5.7, scope3=37.7)
        assert isinstance(svg, str)
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_contains_scope_labels(self):
        svg = chart_scope_donut(scope1=3.8, scope2=5.7, scope3=37.7)
        assert "Scope 1" in svg
        assert "Scope 2" in svg
        assert "Scope 3" in svg

    def test_zero_scopes_handled(self):
        svg = chart_scope_donut(scope1=0, scope2=5.7, scope3=37.7)
        assert isinstance(svg, str)


@pytest.fixture
def sample_categories():
    return [
        {"name": "Purchased goods", "scope": 3, "co2e_tonnes": 18.6, "spend_gbp": 248000, "gsd": 1.82},
        {"name": "Business travel — flights", "scope": 3, "co2e_tonnes": 8.2, "spend_gbp": 42000, "gsd": 1.5},
        {"name": "Electricity", "scope": 2, "co2e_tonnes": 5.7, "spend_gbp": 15000, "gsd": 1.1},
        {"name": "Freight & logistics", "scope": 3, "co2e_tonnes": 5.1, "spend_gbp": 67000, "gsd": 1.7},
        {"name": "Natural gas", "scope": 1, "co2e_tonnes": 3.8, "spend_gbp": 8000, "gsd": 1.1},
    ]


class TestTopCategoriesBar:
    def test_returns_svg(self, sample_categories):
        svg = chart_top_categories_bar(sample_categories)
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_contains_category_names(self, sample_categories):
        svg = chart_top_categories_bar(sample_categories)
        assert "Purchased goods" in svg


class TestScopeStackedBar:
    def test_returns_svg(self):
        svg = chart_scope_stacked_bar(scope1=3.8, scope2=5.7, scope3=37.7, ci_lower=32.1, ci_upper=69.4)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestScopeCategoryBars:
    def test_returns_svg(self, sample_categories):
        svg = chart_scope_category_bars(sample_categories)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestSpendVsEmissionsScatter:
    def test_returns_svg(self, sample_categories):
        svg = chart_spend_vs_emissions_scatter(sample_categories)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


@pytest.fixture
def sample_monthly():
    return [
        {"month": "2024-04", "scope1": 0.3, "scope2": 0.5, "scope3": 3.1},
        {"month": "2024-05", "scope1": 0.3, "scope2": 0.5, "scope3": 3.0},
        {"month": "2024-06", "scope1": 0.4, "scope2": 0.4, "scope3": 3.5},
        {"month": "2024-07", "scope1": 0.3, "scope2": 0.5, "scope3": 3.2},
    ]


@pytest.fixture
def sample_reductions():
    return [
        {"action": "Switch to renewable tariff", "type": "energy", "reduction_tonnes": 4.5, "effort": "low"},
        {"action": "Consolidate freight", "type": "transport", "reduction_tonnes": 2.1, "effort": "medium"},
        {"action": "Remote work policy", "type": "operations", "reduction_tonnes": 1.3, "effort": "low"},
        {"action": "Engage top supplier", "type": "procurement", "reduction_tonnes": 3.0, "effort": "high"},
    ]


class TestMonthlyCharts:
    def test_stacked_area_returns_svg(self, sample_monthly):
        svg = chart_monthly_stacked_area(sample_monthly)
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_cumulative_line_returns_svg(self, sample_monthly):
        svg = chart_cumulative_line(sample_monthly)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestUncertaintyCharts:
    def test_error_bars_returns_svg(self):
        scopes = [
            {"name": "Scope 1", "value": 3.8, "ci_lower": 2.5, "ci_upper": 5.8},
            {"name": "Scope 2", "value": 5.7, "ci_lower": 4.1, "ci_upper": 7.9},
            {"name": "Scope 3", "value": 37.7, "ci_lower": 25.5, "ci_upper": 55.7},
            {"name": "Total", "value": 47.2, "ci_lower": 32.1, "ci_upper": 69.4},
        ]
        svg = chart_error_bars(scopes)
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_pedigree_radar_returns_svg(self):
        indicators = {"reliability": 3.2, "completeness": 2.1, "temporal": 1.8, "geographical": 1.0, "technological": 3.8}
        svg = chart_pedigree_radar(indicators)
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_pedigree_contribution_returns_svg(self):
        contributions = {"reliability": 25.0, "completeness": 8.0, "temporal": 12.0, "geographical": 5.0, "technological": 50.0}
        svg = chart_pedigree_contribution_bar(contributions)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestDataQualityCharts:
    def test_cascade_grouped_bar_returns_svg(self):
        current = {"L1": 0, "L2": 5, "L3": 0, "L4": 85, "L5": 10, "L6": 0}
        target = {"L1": 10, "L2": 30, "L3": 20, "L4": 30, "L5": 10, "L6": 0}
        svg = chart_cascade_grouped_bar(current, target)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestReductionCharts:
    def test_quadrant_returns_svg(self, sample_reductions):
        svg = chart_reduction_quadrant(sample_reductions)
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_waterfall_returns_svg(self, sample_reductions):
        svg = chart_reduction_waterfall(current_total=47.2, reductions=sample_reductions)
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_potential_bar_returns_svg(self, sample_reductions):
        svg = chart_reduction_potential_bar(sample_reductions)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestProjectionCharts:
    def test_fan_chart_returns_svg(self):
        svg = chart_projection_fan(
            baseline=47.2, ci_lower=32.1, ci_upper=69.4,
            year2_ci_lower=35.0, year2_ci_upper=61.0,
            year3_target=36.3, year3_ci_lower=30.0, year3_ci_upper=43.0,
        )
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_projection_waterfall_returns_svg(self):
        svg = chart_projection_waterfall(
            baseline=47.2, year2_data_improvement=-0.0,
            year2_ci_narrowing=8.4, year3_reductions=-10.9,
        )
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestImpactBar:
    def test_returns_svg(self):
        recs = [
            {"action": "Split office supplies code", "impact_score": 150.0},
            {"action": "Collect electricity kWh", "impact_score": 120.0},
            {"action": "Engage Compass Group", "impact_score": 80.0},
        ]
        svg = chart_impact_bar(recs)
        assert "<svg" in svg.lower() or "svg" in svg.lower()
