"""Tests for report chart generation."""

import pytest
from hemera.services.report_charts import (
    HEMERA_THEME, chart_scope_donut, chart_top_categories_bar,
    chart_scope_stacked_bar, chart_category_treemap, chart_spend_vs_emissions_scatter,
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


class TestCategoryTreemap:
    def test_returns_svg(self, sample_categories):
        svg = chart_category_treemap(sample_categories)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestSpendVsEmissionsScatter:
    def test_returns_svg(self, sample_categories):
        svg = chart_spend_vs_emissions_scatter(sample_categories)
        assert "<svg" in svg.lower() or "svg" in svg.lower()
