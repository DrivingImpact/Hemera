# Carbon Footprint PDF Report — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a board-ready PDF carbon footprint report with 19 charts from an engagement's data, served via `GET /api/reports/{id}/pdf`.

**Architecture:** Plotly generates charts as inline SVG strings. Jinja2 templates compose them into styled HTML pages using the Hemera brand CSS. WeasyPrint converts HTML→PDF with CSS `@page` rules for proper pagination. A new reduction recommendation engine provides the data for reduction/projection pages.

**Tech Stack:** Python 3.14, Plotly 6, Jinja2, WeasyPrint, pytest

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `hemera/services/report_charts.py` | Create | All 19 Plotly chart functions + brand theme |
| `hemera/services/reduction_recs.py` | Create | Reduction recommendation engine + projection logic |
| `hemera/services/pdf_report.py` | Create | Orchestrator: gather data, call charts, render templates, produce PDF bytes |
| `hemera/templates/report.css` | Create | Brand CSS for PDF (page rules, typography, components) |
| `hemera/templates/report_base.html` | Create | Jinja2 base template wrapping all pages |
| `hemera/templates/pages/cover.html` | Create | Cover page template |
| `hemera/templates/pages/executive_summary.html` | Create | Exec summary with KPIs + 2 charts |
| `hemera/templates/pages/scope_breakdown.html` | Create | Scope breakdown with 2 charts |
| `hemera/templates/pages/hotspots.html` | Create | Category hotspots with 2 charts |
| `hemera/templates/pages/monthly.html` | Create | Monthly pattern with 2 charts |
| `hemera/templates/pages/reduction_roadmap.html` | Create | Reduction roadmap with 2 charts |
| `hemera/templates/pages/quick_wins.html` | Create | Quick wins with 1 chart + table |
| `hemera/templates/pages/projections.html` | Create | Footprint journey with 2 charts + KPIs |
| `hemera/templates/pages/uncertainty.html` | Create | Uncertainty analysis with 3 charts |
| `hemera/templates/pages/data_quality.html` | Create | Data quality with 2 charts |
| `hemera/templates/pages/methodology.html` | Create | Methodology note (text) |
| `hemera/templates/pages/appendix.html` | Create | Transaction detail table |
| `hemera/api/reports.py` | Modify | Add PDF endpoint |
| `tests/test_report_charts.py` | Create | Chart function tests |
| `tests/test_reduction_recs.py` | Create | Reduction engine tests |
| `tests/test_pdf_report.py` | Create | PDF pipeline integration tests |

---

### Task 1: Plotly brand theme + first chart (donut)

**Files:**
- Create: `hemera/services/report_charts.py`
- Create: `tests/test_report_charts.py`

- [ ] **Step 1: Write failing tests for theme and donut chart**

Create `tests/test_report_charts.py`:

```python
"""Tests for report chart generation."""

import pytest
from hemera.services.report_charts import HEMERA_THEME, chart_scope_donut


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
        assert "<svg" in svg.lower() or "svg" in svg.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_report_charts.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement theme and donut chart**

Create `hemera/services/report_charts.py`:

```python
"""Plotly chart generation for PDF reports.

All functions return inline SVG strings ready for embedding in HTML templates.
Uses the Hemera brand theme for consistent styling.

Scope colours: Scope 1 = #1E293B (Slate), Scope 2 = #0D9488 (Teal), Scope 3 = #F59E0B (Amber)
"""

import plotly.graph_objects as go
import plotly.io as pio

SCOPE_COLOURS = {1: "#1E293B", 2: "#0D9488", 3: "#F59E0B"}

HEMERA_THEME = {
    "layout": {
        "font": {"family": "Plus Jakarta Sans, system-ui, sans-serif", "size": 12, "color": "#1E293B"},
        "paper_bgcolor": "#FFFFFF",
        "plot_bgcolor": "#FFFFFF",
        "colorway": ["#1E293B", "#0D9488", "#F59E0B", "#10B981", "#EF4444", "#64748B"],
        "margin": {"l": 60, "r": 20, "t": 40, "b": 40},
    }
}


def _to_svg(fig: go.Figure, width: int = 600, height: int = 400) -> str:
    """Convert a Plotly figure to an inline SVG string."""
    fig.update_layout(**HEMERA_THEME["layout"])
    return pio.to_image(fig, format="svg", width=width, height=height).decode("utf-8")


def chart_scope_donut(scope1: float, scope2: float, scope3: float) -> str:
    """Donut chart showing Scope 1/2/3 split."""
    labels = ["Scope 1", "Scope 2", "Scope 3"]
    values = [scope1, scope2, scope3]
    colours = [SCOPE_COLOURS[1], SCOPE_COLOURS[2], SCOPE_COLOURS[3]]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colours),
        textinfo="label+percent",
        textfont=dict(size=11),
        hoverinfo="label+value",
    )])
    fig.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return _to_svg(fig, width=360, height=300)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_report_charts.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hemera/services/report_charts.py tests/test_report_charts.py
git commit -m "feat: add Plotly brand theme and scope donut chart for PDF report"
```

---

### Task 2: Core chart functions — bars, treemap, scatter

**Files:**
- Modify: `hemera/services/report_charts.py`
- Modify: `tests/test_report_charts.py`

- [ ] **Step 1: Write failing tests for bar charts, treemap, and scatter**

Append to `tests/test_report_charts.py`:

```python
from hemera.services.report_charts import (
    chart_top_categories_bar,
    chart_scope_stacked_bar,
    chart_category_treemap,
    chart_spend_vs_emissions_scatter,
)


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
        svg = chart_scope_stacked_bar(
            scope1=3.8, scope2=5.7, scope3=37.7,
            ci_lower=32.1, ci_upper=69.4,
        )
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestCategoryTreemap:
    def test_returns_svg(self, sample_categories):
        svg = chart_category_treemap(sample_categories)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestSpendVsEmissionsScatter:
    def test_returns_svg(self, sample_categories):
        svg = chart_spend_vs_emissions_scatter(sample_categories)
        assert "<svg" in svg.lower() or "svg" in svg.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_report_charts.py -v -k "TopCategories or ScopeStacked or Treemap or SpendVs"
```

Expected: `ImportError`

- [ ] **Step 3: Implement the four chart functions**

Append to `hemera/services/report_charts.py`:

```python
def chart_top_categories_bar(categories: list[dict], limit: int = 10) -> str:
    """Horizontal bar chart of top emission categories by tCO2e."""
    cats = sorted(categories, key=lambda c: c["co2e_tonnes"], reverse=True)[:limit]
    cats.reverse()  # bottom-to-top for horizontal bar

    fig = go.Figure(data=[go.Bar(
        y=[c["name"] for c in cats],
        x=[c["co2e_tonnes"] for c in cats],
        orientation="h",
        marker_color=[SCOPE_COLOURS.get(c["scope"], "#64748B") for c in cats],
        text=[f'{c["co2e_tonnes"]:.1f}t' for c in cats],
        textposition="outside",
    )])
    fig.update_layout(
        xaxis_title="tCO2e",
        yaxis=dict(tickfont=dict(size=10)),
        margin=dict(l=180, r=40, t=20, b=40),
    )
    return _to_svg(fig, width=700, height=400)


def chart_scope_stacked_bar(
    scope1: float, scope2: float, scope3: float,
    ci_lower: float, ci_upper: float,
) -> str:
    """Stacked bar showing scope 1/2/3 with CI error whiskers on total."""
    total = scope1 + scope2 + scope3
    fig = go.Figure()
    for scope, val, name in [(1, scope1, "Scope 1"), (2, scope2, "Scope 2"), (3, scope3, "Scope 3")]:
        fig.add_trace(go.Bar(
            x=["Emissions"],
            y=[val],
            name=name,
            marker_color=SCOPE_COLOURS[scope],
        ))
    # CI whiskers as invisible scatter with error bars
    fig.add_trace(go.Scatter(
        x=["Emissions"],
        y=[total],
        error_y=dict(
            type="data",
            symmetric=False,
            array=[ci_upper - total],
            arrayminus=[total - ci_lower],
            color="#64748B",
            thickness=2,
            width=10,
        ),
        mode="markers",
        marker=dict(size=0.1, color="rgba(0,0,0,0)"),
        showlegend=False,
    ))
    fig.update_layout(barmode="stack", yaxis_title="tCO2e")
    return _to_svg(fig, width=400, height=400)


def chart_category_treemap(categories: list[dict]) -> str:
    """Treemap of categories nested by scope. Size = tCO2e."""
    labels = ["Total"]
    parents = [""]
    values = [0]
    colours = ["#FFFFFF"]

    scope_names = {1: "Scope 1", 2: "Scope 2", 3: "Scope 3"}
    for s in [1, 2, 3]:
        scope_cats = [c for c in categories if c["scope"] == s]
        if scope_cats:
            labels.append(scope_names[s])
            parents.append("Total")
            values.append(0)
            colours.append(SCOPE_COLOURS[s])
            for c in scope_cats:
                labels.append(c["name"])
                parents.append(scope_names[s])
                values.append(c["co2e_tonnes"])
                colours.append(SCOPE_COLOURS[s])

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colours),
        textinfo="label+value",
        texttemplate="%{label}<br>%{value:.1f}t",
        branchvalues="total",
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return _to_svg(fig, width=700, height=350)


def chart_spend_vs_emissions_scatter(categories: list[dict]) -> str:
    """Scatter: spend (x) vs tCO2e (y), bubble size = GSD uncertainty."""
    fig = go.Figure()
    for c in categories:
        fig.add_trace(go.Scatter(
            x=[c["spend_gbp"]],
            y=[c["co2e_tonnes"]],
            mode="markers+text",
            marker=dict(
                size=max(c.get("gsd", 1.0) * 20, 10),
                color=SCOPE_COLOURS.get(c["scope"], "#64748B"),
                opacity=0.7,
            ),
            text=[c["name"]],
            textposition="top center",
            textfont=dict(size=9),
            showlegend=False,
        ))
    fig.update_layout(
        xaxis_title="Spend (GBP)",
        yaxis_title="tCO2e",
        margin=dict(l=60, r=20, t=20, b=50),
    )
    return _to_svg(fig, width=700, height=400)
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_report_charts.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hemera/services/report_charts.py tests/test_report_charts.py
git commit -m "feat: add bar, treemap, and scatter chart functions for PDF report"
```

---

### Task 3: Monthly, uncertainty, and data quality charts

**Files:**
- Modify: `hemera/services/report_charts.py`
- Modify: `tests/test_report_charts.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_report_charts.py`:

```python
from hemera.services.report_charts import (
    chart_monthly_stacked_area,
    chart_cumulative_line,
    chart_error_bars,
    chart_pedigree_radar,
    chart_pedigree_contribution_bar,
    chart_cascade_grouped_bar,
)


@pytest.fixture
def sample_monthly():
    return [
        {"month": "2024-04", "scope1": 0.3, "scope2": 0.5, "scope3": 3.1},
        {"month": "2024-05", "scope1": 0.3, "scope2": 0.5, "scope3": 3.0},
        {"month": "2024-06", "scope1": 0.4, "scope2": 0.4, "scope3": 3.5},
        {"month": "2024-07", "scope1": 0.3, "scope2": 0.5, "scope3": 3.2},
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
        indicators = {
            "reliability": 3.2,
            "completeness": 2.1,
            "temporal": 1.8,
            "geographical": 1.0,
            "technological": 3.8,
        }
        svg = chart_pedigree_radar(indicators)
        assert "<svg" in svg.lower() or "svg" in svg.lower()

    def test_pedigree_contribution_returns_svg(self):
        contributions = {
            "reliability": 25.0,
            "completeness": 8.0,
            "temporal": 12.0,
            "geographical": 5.0,
            "technological": 50.0,
        }
        svg = chart_pedigree_contribution_bar(contributions)
        assert "<svg" in svg.lower() or "svg" in svg.lower()


class TestDataQualityCharts:
    def test_cascade_grouped_bar_returns_svg(self):
        current = {"L1": 0, "L2": 5, "L3": 0, "L4": 85, "L5": 10, "L6": 0}
        target = {"L1": 10, "L2": 30, "L3": 20, "L4": 30, "L5": 10, "L6": 0}
        svg = chart_cascade_grouped_bar(current, target)
        assert "<svg" in svg.lower() or "svg" in svg.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_report_charts.py -v -k "Monthly or Uncertainty or DataQuality"
```

Expected: `ImportError`

- [ ] **Step 3: Implement the six chart functions**

Append to `hemera/services/report_charts.py`:

```python
def chart_monthly_stacked_area(monthly_data: list[dict]) -> str:
    """Stacked area chart of monthly emissions by scope."""
    months = [m["month"] for m in monthly_data]
    fig = go.Figure()
    for scope, key, name in [(1, "scope1", "Scope 1"), (2, "scope2", "Scope 2"), (3, "scope3", "Scope 3")]:
        fig.add_trace(go.Scatter(
            x=months,
            y=[m[key] for m in monthly_data],
            name=name,
            mode="lines",
            stackgroup="one",
            line=dict(width=0.5, color=SCOPE_COLOURS[scope]),
            fillcolor=SCOPE_COLOURS[scope] + "80",  # with alpha
        ))
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="tCO2e",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _to_svg(fig, width=700, height=350)


def chart_cumulative_line(monthly_data: list[dict]) -> str:
    """Cumulative actual vs linear projection line chart."""
    months = [m["month"] for m in monthly_data]
    monthly_totals = [m["scope1"] + m["scope2"] + m["scope3"] for m in monthly_data]

    cumulative = []
    running = 0
    for t in monthly_totals:
        running += t
        cumulative.append(running)

    annual_total = cumulative[-1] / len(cumulative) * 12
    linear = [annual_total / 12 * (i + 1) for i in range(len(months))]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months, y=cumulative, name="Actual (cumulative)",
        mode="lines+markers",
        line=dict(color="#0D9488", width=2.5),
    ))
    fig.add_trace(go.Scatter(
        x=months, y=linear, name="Linear projection",
        mode="lines",
        line=dict(color="#64748B", width=1.5, dash="dash"),
    ))
    fig.update_layout(
        yaxis_title="Cumulative tCO2e",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _to_svg(fig, width=700, height=350)


def chart_error_bars(scopes: list[dict]) -> str:
    """Error bar chart showing central estimate ± 95% CI per scope + total."""
    fig = go.Figure()
    colours = [SCOPE_COLOURS.get(i + 1, "#64748B") for i in range(len(scopes))]
    fig.add_trace(go.Bar(
        x=[s["name"] for s in scopes],
        y=[s["value"] for s in scopes],
        error_y=dict(
            type="data",
            symmetric=False,
            array=[s["ci_upper"] - s["value"] for s in scopes],
            arrayminus=[s["value"] - s["ci_lower"] for s in scopes],
            color="#64748B",
            thickness=2,
            width=6,
        ),
        marker_color=colours,
    ))
    fig.update_layout(yaxis_title="tCO2e", showlegend=False)
    return _to_svg(fig, width=500, height=350)


def chart_pedigree_radar(indicators: dict[str, float]) -> str:
    """Radar chart of 5 pedigree indicator weighted average scores."""
    names = list(indicators.keys())
    values = list(indicators.values())
    # Close the polygon
    names.append(names[0])
    values.append(values[0])

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=[n.capitalize() for n in names],
        fill="toself",
        fillcolor="rgba(13,148,136,0.15)",
        line=dict(color="#0D9488", width=2),
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5], tickvals=[1, 2, 3, 4, 5]),
        ),
        showlegend=False,
        margin=dict(l=60, r=60, t=40, b=40),
    )
    return _to_svg(fig, width=400, height=350)


def chart_pedigree_contribution_bar(contributions: dict[str, float]) -> str:
    """Horizontal stacked bar showing pedigree indicator contribution to uncertainty."""
    names = [k.capitalize() for k in contributions.keys()]
    values = list(contributions.values())
    colours = ["#1E293B", "#0D9488", "#F59E0B", "#10B981", "#EF4444"]

    fig = go.Figure()
    cumulative = 0
    for i, (name, val) in enumerate(zip(names, values)):
        fig.add_trace(go.Bar(
            y=["Uncertainty"],
            x=[val],
            name=name,
            orientation="h",
            marker_color=colours[i % len(colours)],
            text=[f"{val:.0f}%"],
            textposition="inside",
        ))
    fig.update_layout(
        barmode="stack",
        xaxis_title="Contribution to total uncertainty (%)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=20, t=50, b=40),
    )
    return _to_svg(fig, width=700, height=200)


def chart_cascade_grouped_bar(current_pct: dict, target_pct: dict) -> str:
    """Grouped bar chart: current vs target cascade distribution (L1-L6)."""
    levels = ["L1", "L2", "L3", "L4", "L5", "L6"]
    level_labels = [
        "L1\nSupplier", "L2\nActivity", "L3\nExiobase",
        "L4\nDEFRA EEIO", "L5\nUSEEIO", "L6\nClimatiq",
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=level_labels,
        y=[current_pct.get(l, 0) for l in levels],
        name="Current",
        marker_color="#F59E0B",
    ))
    fig.add_trace(go.Bar(
        x=level_labels,
        y=[target_pct.get(l, 0) for l in levels],
        name="Target",
        marker_color="#0D9488",
    ))
    fig.update_layout(
        barmode="group",
        yaxis_title="% of spend",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _to_svg(fig, width=700, height=350)
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_report_charts.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hemera/services/report_charts.py tests/test_report_charts.py
git commit -m "feat: add monthly, uncertainty, and data quality charts for PDF report"
```

---

### Task 4: Reduction and projection charts

**Files:**
- Modify: `hemera/services/report_charts.py`
- Modify: `tests/test_report_charts.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_report_charts.py`:

```python
from hemera.services.report_charts import (
    chart_reduction_quadrant,
    chart_reduction_waterfall,
    chart_reduction_potential_bar,
    chart_projection_fan,
    chart_projection_waterfall,
    chart_impact_bar,
)


@pytest.fixture
def sample_reductions():
    return [
        {"action": "Switch to renewable tariff", "type": "energy", "reduction_tonnes": 4.5, "effort": "low"},
        {"action": "Consolidate freight", "type": "transport", "reduction_tonnes": 2.1, "effort": "medium"},
        {"action": "Remote work policy", "type": "operations", "reduction_tonnes": 1.3, "effort": "low"},
        {"action": "Engage top supplier", "type": "procurement", "reduction_tonnes": 3.0, "effort": "high"},
    ]


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
            baseline=47.2,
            year2_data_improvement=-0.0,
            year2_ci_narrowing=8.4,
            year3_reductions=-10.9,
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_report_charts.py -v -k "Reduction or Projection or ImpactBar"
```

Expected: `ImportError`

- [ ] **Step 3: Implement the six chart functions**

Append to `hemera/services/report_charts.py`:

```python
EFFORT_MAP = {"low": 1, "medium": 2, "high": 3}
TYPE_COLOURS = {
    "energy": "#0D9488",
    "transport": "#F59E0B",
    "procurement": "#1E293B",
    "operations": "#10B981",
}


def chart_reduction_quadrant(reductions: list[dict]) -> str:
    """Quadrant scatter: impact (y) vs effort (x). Labelled quadrants."""
    fig = go.Figure()
    for r in reductions:
        effort_val = EFFORT_MAP.get(r["effort"], 2)
        fig.add_trace(go.Scatter(
            x=[effort_val],
            y=[r["reduction_tonnes"]],
            mode="markers+text",
            marker=dict(size=max(r["reduction_tonnes"] * 8, 15), color=TYPE_COLOURS.get(r["type"], "#64748B"), opacity=0.7),
            text=[r["action"]],
            textposition="top center",
            textfont=dict(size=9),
            showlegend=False,
        ))
    # Quadrant lines
    fig.add_hline(y=sum(r["reduction_tonnes"] for r in reductions) / len(reductions), line_dash="dot", line_color="#CBD5E1")
    fig.add_vline(x=2, line_dash="dot", line_color="#CBD5E1")
    # Quadrant labels
    fig.add_annotation(x=1, y=max(r["reduction_tonnes"] for r in reductions) * 1.1, text="Quick Wins", showarrow=False, font=dict(size=10, color="#10B981"))
    fig.add_annotation(x=3, y=max(r["reduction_tonnes"] for r in reductions) * 1.1, text="Strategic", showarrow=False, font=dict(size=10, color="#F59E0B"))
    fig.update_layout(
        xaxis=dict(title="Effort", tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"], range=[0.5, 3.5]),
        yaxis_title="Reduction potential (tCO2e)",
    )
    return _to_svg(fig, width=600, height=400)


def chart_reduction_waterfall(current_total: float, reductions: list[dict]) -> str:
    """Waterfall from current total through each reduction to projected total."""
    sorted_recs = sorted(reductions, key=lambda r: r["reduction_tonnes"], reverse=True)

    labels = ["Current"] + [r["action"] for r in sorted_recs] + ["Projected"]
    measures = ["absolute"] + ["relative"] * len(sorted_recs) + ["total"]
    values = [current_total] + [-r["reduction_tonnes"] for r in sorted_recs] + [0]

    fig = go.Figure(go.Waterfall(
        x=labels,
        y=values,
        measure=measures,
        connector=dict(line=dict(color="#CBD5E1")),
        increasing=dict(marker=dict(color="#EF4444")),
        decreasing=dict(marker=dict(color="#10B981")),
        totals=dict(marker=dict(color="#0D9488")),
        textposition="outside",
        text=[f"{abs(v):.1f}t" for v in values],
    ))
    fig.update_layout(
        yaxis_title="tCO2e",
        margin=dict(l=60, r=20, t=20, b=80),
        xaxis=dict(tickangle=-30, tickfont=dict(size=9)),
    )
    return _to_svg(fig, width=700, height=400)


def chart_reduction_potential_bar(reductions: list[dict]) -> str:
    """Horizontal bar of reduction potential per action, coloured by type."""
    sorted_recs = sorted(reductions, key=lambda r: r["reduction_tonnes"])

    fig = go.Figure(data=[go.Bar(
        y=[r["action"] for r in sorted_recs],
        x=[r["reduction_tonnes"] for r in sorted_recs],
        orientation="h",
        marker_color=[TYPE_COLOURS.get(r["type"], "#64748B") for r in sorted_recs],
        text=[f'{r["reduction_tonnes"]:.1f}t' for r in sorted_recs],
        textposition="outside",
    )])
    fig.update_layout(
        xaxis_title="Reduction potential (tCO2e)",
        margin=dict(l=200, r=50, t=20, b=40),
    )
    return _to_svg(fig, width=700, height=300)


def chart_projection_fan(
    baseline: float, ci_lower: float, ci_upper: float,
    year2_ci_lower: float, year2_ci_upper: float,
    year3_target: float, year3_ci_lower: float, year3_ci_upper: float,
) -> str:
    """Fan chart showing 3-year projection with narrowing CI bands."""
    years = ["Year 1\n(Baseline)", "Year 2\n(Better data)", "Year 3\n(Reductions)"]
    central = [baseline, baseline, year3_target]
    upper = [ci_upper, year2_ci_upper, year3_ci_upper]
    lower = [ci_lower, year2_ci_lower, year3_ci_lower]

    fig = go.Figure()
    # CI band
    fig.add_trace(go.Scatter(
        x=years + years[::-1],
        y=upper + lower[::-1],
        fill="toself",
        fillcolor="rgba(13,148,136,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
    ))
    # Central line
    fig.add_trace(go.Scatter(
        x=years, y=central,
        mode="lines+markers",
        line=dict(color="#0D9488", width=3),
        marker=dict(size=10, color="#0D9488"),
        name="Central estimate",
    ))
    # Do-nothing line
    fig.add_trace(go.Scatter(
        x=years, y=[baseline, baseline, baseline],
        mode="lines",
        line=dict(color="#EF4444", width=1.5, dash="dash"),
        name="Do nothing",
    ))
    fig.update_layout(
        yaxis_title="tCO2e",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _to_svg(fig, width=700, height=400)


def chart_projection_waterfall(
    baseline: float,
    year2_data_improvement: float,
    year2_ci_narrowing: float,
    year3_reductions: float,
) -> str:
    """Stepped waterfall: baseline → better data → reductions → target."""
    projected = baseline + year3_reductions
    labels = ["Year 1\nBaseline", "Data quality\nimprovement", "Emission\nreductions", "Year 3\nProjected"]
    values = [baseline, year2_data_improvement, year3_reductions, 0]
    measures = ["absolute", "relative", "relative", "total"]

    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=measures,
        connector=dict(line=dict(color="#CBD5E1")),
        decreasing=dict(marker=dict(color="#10B981")),
        increasing=dict(marker=dict(color="#EF4444")),
        totals=dict(marker=dict(color="#0D9488")),
        text=[f"{abs(v):.1f}t" if v != 0 else "" for v in values],
        textposition="outside",
    ))
    fig.update_layout(yaxis_title="tCO2e")
    return _to_svg(fig, width=600, height=350)


def chart_impact_bar(recommendations: list[dict], limit: int = 5) -> str:
    """Horizontal bar of top data quality recommendations by impact score."""
    recs = sorted(recommendations, key=lambda r: r["impact_score"], reverse=True)[:limit]
    recs.reverse()

    fig = go.Figure(data=[go.Bar(
        y=[r["action"] for r in recs],
        x=[r["impact_score"] for r in recs],
        orientation="h",
        marker_color="#0D9488",
        text=[f'{r["impact_score"]:.0f}' for r in recs],
        textposition="outside",
    )])
    fig.update_layout(
        xaxis_title="Uncertainty reduction impact",
        margin=dict(l=220, r=50, t=20, b=40),
    )
    return _to_svg(fig, width=700, height=250)
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_report_charts.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hemera/services/report_charts.py tests/test_report_charts.py
git commit -m "feat: add reduction, projection, and impact chart functions for PDF report"
```

---

### Task 5: Reduction recommendation engine

**Files:**
- Create: `hemera/services/reduction_recs.py`
- Create: `tests/test_reduction_recs.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_reduction_recs.py`:

```python
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
            total_co2e_kg=47200,
            ci_lower_kg=32100,
            ci_upper_kg=69400,
            reduction_recs=[{"potential_reduction_kg": 4500}, {"potential_reduction_kg": 2100}],
            data_quality_recs=[{"projected_avg_gsd": 1.2, "current_avg_gsd": 1.5}],
        )
        assert isinstance(result, dict)

    def test_year3_target_lower_than_baseline(self):
        result = compute_projections(
            total_co2e_kg=47200,
            ci_lower_kg=32100,
            ci_upper_kg=69400,
            reduction_recs=[{"potential_reduction_kg": 4500}],
            data_quality_recs=[],
        )
        assert result["year3_target_kg"] < 47200

    def test_year2_ci_narrower_than_baseline(self):
        result = compute_projections(
            total_co2e_kg=47200,
            ci_lower_kg=32100,
            ci_upper_kg=69400,
            reduction_recs=[],
            data_quality_recs=[{"projected_avg_gsd": 1.2, "current_avg_gsd": 1.8}],
        )
        baseline_width = 69400 - 32100
        year2_width = result["year2_ci_upper_kg"] - result["year2_ci_lower_kg"]
        assert year2_width < baseline_width
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_reduction_recs.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement the reduction engine**

Create `hemera/services/reduction_recs.py`:

```python
"""Reduction recommendation engine and projection logic.

Generates emission reduction recommendations based on the engagement's
calculated data. Also computes 3-year projections for the "Footprint Journey" page.

Reduction percentages are conservative estimates based on published benchmarks.
The report notes these are indicative, not precise.
"""

# Category → reduction benchmark
# Sources: Carbon Trust, BEIS, IEA published benchmarks
REDUCTION_BENCHMARKS = {
    "Purchased electricity": {
        "action": "Switch to a certified renewable electricity tariff",
        "type": "energy",
        "reduction_pct": 0.80,  # market-based Scope 2 drops ~80% with green tariff
        "effort": "low",
        "timeline": "quick",
    },
    "Stationary combustion — gas/heating fuel": {
        "action": "Improve heating efficiency (insulation, controls, heat pump feasibility study)",
        "type": "energy",
        "reduction_pct": 0.15,
        "effort": "medium",
        "timeline": "medium",
    },
    "Mobile combustion — company vehicles": {
        "action": "Transition fleet to electric/hybrid vehicles",
        "type": "transport",
        "reduction_pct": 0.50,
        "effort": "high",
        "timeline": "strategic",
    },
    "Business travel — air": {
        "action": "Implement travel policy: replace short-haul flights with rail, reduce non-essential travel",
        "type": "transport",
        "reduction_pct": 0.30,
        "effort": "low",
        "timeline": "quick",
    },
    "Business travel — rail": {
        "action": "Already low-carbon — maintain rail preference over road/air",
        "type": "transport",
        "reduction_pct": 0.05,
        "effort": "low",
        "timeline": "quick",
    },
    "Business travel — land": {
        "action": "Encourage public transport, cycling, remote meetings",
        "type": "transport",
        "reduction_pct": 0.20,
        "effort": "low",
        "timeline": "quick",
    },
    "Waste generated in operations": {
        "action": "Implement waste reduction and recycling programme",
        "type": "operations",
        "reduction_pct": 0.25,
        "effort": "medium",
        "timeline": "medium",
    },
    "Purchased services — water supply": {
        "action": "Install water-efficient fixtures and monitor consumption",
        "type": "operations",
        "reduction_pct": 0.15,
        "effort": "low",
        "timeline": "quick",
    },
}

# Fallback for Scope 3 categories without specific benchmarks
SCOPE3_GENERIC = {
    "action": "Engage key suppliers to collect actual emission data and identify alternatives",
    "type": "procurement",
    "reduction_pct": 0.10,
    "effort": "medium",
    "timeline": "medium",
}


def generate_reduction_recommendations(transactions: list) -> list[dict]:
    """Generate reduction recommendations from transaction data.

    Returns list of dicts sorted by potential_reduction_kg descending.
    """
    valid = [t for t in transactions if t.co2e_kg and t.co2e_kg > 0 and not t.is_duplicate]

    # Group by category
    category_groups: dict[str, list] = {}
    for t in valid:
        key = t.category_name or "Unclassified"
        category_groups.setdefault(key, []).append(t)

    recs = []
    for cat_name, txns in category_groups.items():
        total_co2e = sum(t.co2e_kg for t in txns)

        benchmark = REDUCTION_BENCHMARKS.get(cat_name)
        if not benchmark and txns[0].scope == 3 and total_co2e > 500:
            benchmark = SCOPE3_GENERIC

        if not benchmark:
            continue

        reduction_kg = total_co2e * benchmark["reduction_pct"]

        recs.append({
            "type": benchmark["type"],
            "category": cat_name,
            "action": benchmark["action"],
            "current_co2e_kg": round(total_co2e, 1),
            "potential_reduction_pct": round(benchmark["reduction_pct"] * 100, 1),
            "potential_reduction_kg": round(reduction_kg, 1),
            "effort": benchmark["effort"],
            "timeline": benchmark["timeline"],
            "explanation": (
                f"{cat_name} contributes {total_co2e / 1000:.1f} tCO2e. "
                f"{benchmark['action']} could reduce this by ~{benchmark['reduction_pct'] * 100:.0f}%."
            ),
        })

    recs.sort(key=lambda r: r["potential_reduction_kg"], reverse=True)
    return recs


def compute_projections(
    total_co2e_kg: float,
    ci_lower_kg: float,
    ci_upper_kg: float,
    reduction_recs: list[dict],
    data_quality_recs: list[dict],
) -> dict:
    """Compute 3-year projection for the Footprint Journey page.

    Year 1: baseline (current)
    Year 2: better data quality → narrower CI, same central estimate
    Year 3: reductions implemented → lower central estimate + narrower CI
    """
    # Year 2: CI narrows proportionally to average GSD improvement
    ci_width = ci_upper_kg - ci_lower_kg
    if data_quality_recs:
        gsd_improvements = []
        for r in data_quality_recs:
            current = r.get("current_avg_gsd", 1.5)
            projected = r.get("projected_avg_gsd", 1.3)
            if current > 1:
                gsd_improvements.append(projected / current)
        avg_improvement = sum(gsd_improvements) / len(gsd_improvements) if gsd_improvements else 0.9
    else:
        avg_improvement = 0.9  # 10% CI narrowing from general improvements

    year2_ci_width = ci_width * avg_improvement
    year2_ci_lower = total_co2e_kg - year2_ci_width / 2
    year2_ci_upper = total_co2e_kg + year2_ci_width / 2

    # Year 3: reductions applied
    total_reduction = sum(r.get("potential_reduction_kg", 0) for r in reduction_recs)
    year3_target = total_co2e_kg - total_reduction

    year3_ci_width = year2_ci_width * 0.85  # further narrowing from better data
    year3_ci_lower = year3_target - year3_ci_width / 2
    year3_ci_upper = year3_target + year3_ci_width / 2

    return {
        "baseline_kg": total_co2e_kg,
        "ci_lower_kg": ci_lower_kg,
        "ci_upper_kg": ci_upper_kg,
        "year2_ci_lower_kg": round(year2_ci_lower, 1),
        "year2_ci_upper_kg": round(year2_ci_upper, 1),
        "year3_target_kg": round(year3_target, 1),
        "year3_ci_lower_kg": round(year3_ci_lower, 1),
        "year3_ci_upper_kg": round(year3_ci_upper, 1),
        "total_reduction_kg": round(total_reduction, 1),
    }
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_reduction_recs.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hemera/services/reduction_recs.py tests/test_reduction_recs.py
git commit -m "feat: add reduction recommendation engine and projection logic"
```

---

### Task 6: HTML templates — base CSS and cover page

**Files:**
- Create: `hemera/templates/report.css`
- Create: `hemera/templates/report_base.html`
- Create: `hemera/templates/pages/cover.html`

- [ ] **Step 1: Create brand CSS for PDF**

Create `hemera/templates/report.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

@page {
    size: A4;
    margin: 20mm 18mm 25mm 18mm;
    @bottom-center {
        content: "Confidential  |  Page " counter(page) " of " counter(pages);
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
        font-size: 8pt;
        color: #94A3B8;
    }
}

@page cover {
    margin: 0;
    @bottom-center { content: none; }
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    font-size: 10pt;
    color: #1E293B;
    line-height: 1.6;
    background: #FFFFFF;
}

.page-break { page-break-before: always; }
.no-break { page-break-inside: avoid; }

h1 { font-size: 20pt; font-weight: 800; margin-bottom: 8pt; }
h2 { font-size: 14pt; font-weight: 700; margin-bottom: 6pt; color: #1E293B; }
h3 { font-size: 11pt; font-weight: 600; margin-bottom: 4pt; color: #64748B; }

.section-label {
    font-size: 8pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5pt;
    color: #64748B;
    margin-bottom: 4pt;
}

.metric-value {
    font-size: 24pt;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.metric-unit {
    font-size: 10pt;
    font-weight: 400;
    color: #94A3B8;
}
.metric-teal { color: #0D9488; }
.metric-slate { color: #1E293B; }
.metric-amber { color: #F59E0B; }

.kpi-grid {
    display: flex;
    gap: 12pt;
    margin-bottom: 16pt;
}
.kpi-card {
    flex: 1;
    background: #F5F5F0;
    border-radius: 6pt;
    padding: 12pt 16pt;
}
.kpi-card.warning {
    background: #FEF3C7;
}

.chart-container {
    margin: 12pt 0;
    text-align: center;
}
.chart-container svg {
    max-width: 100%;
    height: auto;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
    margin: 8pt 0;
}
.data-table th {
    text-align: left;
    padding: 6pt 8pt;
    background: #F5F5F0;
    font-weight: 600;
    font-size: 7pt;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    color: #64748B;
    border-bottom: 1.5pt solid #E5E5E0;
}
.data-table td {
    padding: 5pt 8pt;
    border-bottom: 0.5pt solid #F0F0EB;
    vertical-align: top;
}
.data-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.data-table tr:nth-child(even) td {
    background: #FAFAF7;
}

.badge {
    display: inline-block;
    padding: 1pt 6pt;
    border-radius: 3pt;
    font-size: 7pt;
    font-weight: 600;
}
.badge-teal { background: #CCFBF1; color: #0F766E; }
.badge-amber { background: #FEF3C7; color: #92400E; }
.badge-red { background: #FEE2E2; color: #991B1B; }
.badge-green { background: #D1FAE5; color: #065F46; }

.source-note {
    font-size: 7pt;
    color: #94A3B8;
    margin-top: 8pt;
}

.two-col {
    display: flex;
    gap: 16pt;
}
.two-col > * { flex: 1; }
```

- [ ] **Step 2: Create base HTML template**

Create `hemera/templates/report_base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="report.css">
    <title>{{ org_name }} — Carbon Footprint Report</title>
</head>
<body>
    {% include "pages/cover.html" %}
    {% for page in pages %}
    <div class="page-break"></div>
    {% include page %}
    {% endfor %}
</body>
</html>
```

- [ ] **Step 3: Create cover page template**

Create `hemera/templates/pages/cover.html`:

```html
<div style="page: cover; background: #1E293B; color: #fff; width: 210mm; height: 297mm; display: flex; flex-direction: column; justify-content: center; padding: 40mm;">
    <div style="color: #0D9488; font-size: 12pt; text-transform: uppercase; letter-spacing: 3pt; font-weight: 700; margin-bottom: 8pt;">Hemera</div>
    <h1 style="font-size: 32pt; font-weight: 800; color: #fff; margin-bottom: 12pt;">Carbon Footprint<br>Report</h1>
    <div style="font-size: 14pt; color: #94A3B8; margin-bottom: 40pt;">{{ org_name }}</div>
    <div style="font-size: 10pt; color: #64748B;">
        <div>Reporting period: {{ fiscal_year_start }} — {{ fiscal_year_end }}</div>
        <div>Generated: {{ generated_date }}</div>
        <div style="margin-top: 16pt;">Classification: Confidential</div>
    </div>
</div>
```

- [ ] **Step 4: Commit**

```bash
mkdir -p hemera/templates/pages
git add hemera/templates/report.css hemera/templates/report_base.html hemera/templates/pages/cover.html
git commit -m "feat: add PDF report CSS, base template, and cover page"
```

---

### Task 7: Page templates — executive summary through monthly

**Files:**
- Create: `hemera/templates/pages/executive_summary.html`
- Create: `hemera/templates/pages/scope_breakdown.html`
- Create: `hemera/templates/pages/hotspots.html`
- Create: `hemera/templates/pages/monthly.html`

- [ ] **Step 1: Create executive summary template**

Create `hemera/templates/pages/executive_summary.html`:

```html
<h2>Executive Summary</h2>

<div class="kpi-grid">
    <div class="kpi-card">
        <div class="section-label">Total emissions</div>
        <div class="metric-value metric-teal">{{ "%.1f"|format(total_co2e) }} <span class="metric-unit">tCO2e</span></div>
    </div>
    <div class="kpi-card">
        <div class="section-label">95% confidence interval</div>
        <div class="metric-value metric-slate">{{ "%.1f"|format(ci_lower) }} – {{ "%.1f"|format(ci_upper) }} <span class="metric-unit">tCO2e</span></div>
    </div>
    <div class="kpi-card {{ 'warning' if data_quality_grade in ('D', 'E') else '' }}">
        <div class="section-label">Data quality grade</div>
        <div class="metric-value {{ 'metric-amber' if data_quality_grade in ('C', 'D', 'E') else 'metric-teal' }}">{{ data_quality_grade }}</div>
    </div>
</div>

<div class="two-col">
    <div>
        <h3>Scope Split</h3>
        <div class="chart-container">{{ scope_donut_svg | safe }}</div>
    </div>
    <div>
        <h3>Top Emission Categories</h3>
        <div class="chart-container">{{ top_categories_mini_svg | safe }}</div>
    </div>
</div>

<p style="margin-top: 12pt; color: #475569;">
    {{ org_name }}'s total carbon footprint for the reporting period is <strong>{{ "%.1f"|format(total_co2e) }} tCO2e</strong>
    (95% CI: {{ "%.1f"|format(ci_lower) }}–{{ "%.1f"|format(ci_upper) }}). Scope 3 value chain emissions account for
    {{ "%.0f"|format(scope3_pct) }}% of the total. The data quality grade of <strong>{{ data_quality_grade }}</strong>
    reflects the current mix of emission factor sources.
</p>
```

- [ ] **Step 2: Create scope breakdown template**

Create `hemera/templates/pages/scope_breakdown.html`:

```html
<h2>Scope Breakdown</h2>

<div class="two-col">
    <div>
        <h3>Emissions by Scope</h3>
        <div class="chart-container">{{ scope_stacked_bar_svg | safe }}</div>
    </div>
    <div>
        <table class="data-table">
            <thead>
                <tr><th>Scope</th><th class="num">tCO2e</th><th class="num">% of Total</th><th class="num">95% CI</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>Scope 1 — Direct emissions</td>
                    <td class="num">{{ "%.1f"|format(scope1) }}</td>
                    <td class="num">{{ "%.0f"|format(scope1_pct) }}%</td>
                    <td class="num">{{ scope1_ci }}</td>
                </tr>
                <tr>
                    <td>Scope 2 — Purchased energy</td>
                    <td class="num">{{ "%.1f"|format(scope2) }}</td>
                    <td class="num">{{ "%.0f"|format(scope2_pct) }}%</td>
                    <td class="num">{{ scope2_ci }}</td>
                </tr>
                <tr>
                    <td>Scope 3 — Value chain</td>
                    <td class="num">{{ "%.1f"|format(scope3) }}</td>
                    <td class="num">{{ "%.0f"|format(scope3_pct) }}%</td>
                    <td class="num">{{ scope3_ci }}</td>
                </tr>
                <tr style="font-weight: 700;">
                    <td>Total</td>
                    <td class="num">{{ "%.1f"|format(total_co2e) }}</td>
                    <td class="num">100%</td>
                    <td class="num">{{ total_ci }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>

<h3>Category Distribution</h3>
<div class="chart-container">{{ treemap_svg | safe }}</div>
```

- [ ] **Step 3: Create hotspots template**

Create `hemera/templates/pages/hotspots.html`:

```html
<h2>Emission Hotspots</h2>

<h3>Top 10 Categories by Carbon Impact</h3>
<div class="chart-container">{{ top_categories_bar_svg | safe }}</div>

<h3>Spend vs Emissions</h3>
<p style="font-size: 8pt; color: #64748B; margin-bottom: 4pt;">Bubble size indicates uncertainty (GSD). Larger bubbles = less certain estimates.</p>
<div class="chart-container">{{ spend_vs_emissions_svg | safe }}</div>
```

- [ ] **Step 4: Create monthly template**

Create `hemera/templates/pages/monthly.html`:

```html
{% if has_monthly_data %}
<h2>Monthly Emission Pattern</h2>

<h3>Monthly Emissions by Scope</h3>
<div class="chart-container">{{ monthly_area_svg | safe }}</div>

<h3>Cumulative Progress</h3>
<div class="chart-container">{{ cumulative_line_svg | safe }}</div>
{% else %}
<h2>Monthly Emission Pattern</h2>
<p style="color: #64748B; padding: 40pt 0;">
    Monthly breakdown is not available for this engagement. Transaction dates were not present in
    sufficient quantity (>50% required). Providing dated transactions in future uploads will enable
    seasonal analysis.
</p>
{% endif %}
```

- [ ] **Step 5: Commit**

```bash
git add hemera/templates/pages/executive_summary.html hemera/templates/pages/scope_breakdown.html hemera/templates/pages/hotspots.html hemera/templates/pages/monthly.html
git commit -m "feat: add page templates for exec summary, scope breakdown, hotspots, monthly"
```

---

### Task 8: Page templates — reduction, projections, uncertainty, data quality

**Files:**
- Create: `hemera/templates/pages/reduction_roadmap.html`
- Create: `hemera/templates/pages/quick_wins.html`
- Create: `hemera/templates/pages/projections.html`
- Create: `hemera/templates/pages/uncertainty.html`
- Create: `hemera/templates/pages/data_quality.html`

- [ ] **Step 1: Create reduction roadmap template**

Create `hemera/templates/pages/reduction_roadmap.html`:

```html
<h2>Reduction Roadmap</h2>

<h3>Impact vs Effort</h3>
<p style="font-size: 8pt; color: #64748B; margin-bottom: 4pt;">Top-left = quick wins (high impact, low effort). Actions are sized by reduction potential.</p>
<div class="chart-container">{{ quadrant_svg | safe }}</div>

<h3>Reduction Pathway</h3>
<div class="chart-container">{{ reduction_waterfall_svg | safe }}</div>
```

- [ ] **Step 2: Create quick wins template**

Create `hemera/templates/pages/quick_wins.html`:

```html
<h2>Quick Wins &amp; Strategic Actions</h2>

<h3>Reduction Potential by Action</h3>
<div class="chart-container">{{ reduction_bar_svg | safe }}</div>

<table class="data-table">
    <thead>
        <tr><th>Rank</th><th>Action</th><th>Type</th><th class="num">Current tCO2e</th><th class="num">Reduction</th><th>Effort</th><th>Timeline</th></tr>
    </thead>
    <tbody>
        {% for r in reduction_recs %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ r.action }}</td>
            <td><span class="badge badge-{{ 'teal' if r.type == 'energy' else ('amber' if r.type == 'transport' else 'green') }}">{{ r.type }}</span></td>
            <td class="num">{{ "%.1f"|format(r.current_co2e_kg / 1000) }}</td>
            <td class="num">{{ "%.1f"|format(r.potential_reduction_kg / 1000) }}t ({{ "%.0f"|format(r.potential_reduction_pct) }}%)</td>
            <td>{{ r.effort }}</td>
            <td>{{ r.timeline }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<p class="source-note">Reduction estimates are indicative, based on published benchmarks (Carbon Trust, BEIS, IEA). Actual reductions depend on implementation specifics.</p>
```

- [ ] **Step 3: Create projections template**

Create `hemera/templates/pages/projections.html`:

```html
<h2>Your Footprint Journey — Projections</h2>

<div class="kpi-grid">
    <div class="kpi-card">
        <div class="section-label">Year 3 projected target</div>
        <div class="metric-value metric-teal">{{ "%.1f"|format(year3_target) }} <span class="metric-unit">tCO2e</span></div>
    </div>
    <div class="kpi-card">
        <div class="section-label">Projected CI reduction</div>
        <div class="metric-value metric-teal">{{ "%.0f"|format(ci_reduction_pct) }}% <span class="metric-unit">narrower</span></div>
    </div>
</div>

<div class="two-col">
    <div>
        <h3>3-Year Projection</h3>
        <div class="chart-container">{{ fan_chart_svg | safe }}</div>
    </div>
    <div>
        <h3>Improvement Pathway</h3>
        <div class="chart-container">{{ projection_waterfall_svg | safe }}</div>
    </div>
</div>

<p style="color: #475569; font-size: 9pt;">
    Projections are indicative and assume implementation of the recommended reduction actions and data quality improvements.
    Year 2 shows the effect of better data alone — the central estimate may remain unchanged but the confidence interval narrows,
    revealing your true footprint. Year 3 includes the combined effect of data improvement and emission reductions.
</p>
```

- [ ] **Step 4: Create uncertainty template**

Create `hemera/templates/pages/uncertainty.html`:

```html
<h2>Uncertainty Analysis</h2>

<h3>95% Confidence Intervals by Scope</h3>
<div class="chart-container">{{ error_bars_svg | safe }}</div>

<div class="two-col">
    <div>
        <h3>Pedigree Indicator Scores</h3>
        <p style="font-size: 8pt; color: #64748B; margin-bottom: 4pt;">1 = best quality, 5 = worst. Weighted by emission contribution.</p>
        <div class="chart-container">{{ radar_svg | safe }}</div>
    </div>
    <div>
        <h3>Uncertainty Sources</h3>
        <p style="font-size: 8pt; color: #64748B; margin-bottom: 4pt;">Which data quality indicators drive the most uncertainty.</p>
        <div class="chart-container">{{ pedigree_bar_svg | safe }}</div>
    </div>
</div>
```

- [ ] **Step 5: Create data quality template**

Create `hemera/templates/pages/data_quality.html`:

```html
<h2>Data Quality Improvement</h2>

<h3>Emission Factor Cascade — Current vs Target</h3>
<p style="font-size: 8pt; color: #64748B; margin-bottom: 4pt;">Level 1 (supplier-specific) is most accurate. Level 6 (fallback) is least. Moving spend up the cascade reduces uncertainty.</p>
<div class="chart-container">{{ cascade_bar_svg | safe }}</div>

<h3>Top Actions to Reduce Uncertainty</h3>
<div class="chart-container">{{ impact_bar_svg | safe }}</div>
```

- [ ] **Step 6: Commit**

```bash
git add hemera/templates/pages/
git commit -m "feat: add page templates for reduction, projections, uncertainty, data quality"
```

---

### Task 9: Page templates — methodology and appendix

**Files:**
- Create: `hemera/templates/pages/methodology.html`
- Create: `hemera/templates/pages/appendix.html`

- [ ] **Step 1: Create methodology template**

Create `hemera/templates/pages/methodology.html`:

```html
<h2>Methodology Note</h2>

<h3>Standards Alignment</h3>
<p>This report aligns with the GHG Protocol Corporate Standard, GHG Protocol Value Chain (Scope 3) Standard,
ISO 14064-1:2018, and DEFRA/DESNZ Environmental Reporting Guidelines. It is prepared for UK Streamlined Energy
and Carbon Reporting (SECR) and readiness for UK Sustainability Reporting Standards (SRS S2, effective January 2027)
and ISSA 5000 assurance (effective December 2026).</p>

<h3>Calculation Approach</h3>
<p>Hemera uses a hybrid approach: activity-based calculations where physical data exists (kWh, litres, km),
with spend-based EEIO estimates as a baseline for all other categories. The methodology progressively replaces
generic estimates with supplier-specific verified data over successive reporting periods.</p>

<h3>6-Level Emission Factor Cascade</h3>
<table class="data-table">
    <thead><tr><th>Level</th><th>Source</th><th>Data Required</th><th>Uncertainty</th></tr></thead>
    <tbody>
        <tr><td>1</td><td>Supplier-specific verified</td><td>CDP/actual emission intensity</td><td>Lowest</td></tr>
        <tr><td>2</td><td>DEFRA/DESNZ activity-based</td><td>Physical quantities (kWh, litres)</td><td>Low-moderate</td></tr>
        <tr><td>3</td><td>Exiobase MRIO</td><td>Spend + country of origin</td><td>Moderate</td></tr>
        <tr><td>4</td><td>DEFRA supplementary EEIO</td><td>Spend in GBP</td><td>Moderate-high</td></tr>
        <tr><td>5</td><td>USEEIO</td><td>Spend on US goods</td><td>Moderate</td></tr>
        <tr><td>6</td><td>Climatiq API</td><td>Any (fallback)</td><td>Variable</td></tr>
    </tbody>
</table>

<h3>Uncertainty Quantification</h3>
<p>Every emission estimate carries a pedigree-scored uncertainty using the ecoinvent methodology
(Ciroth et al., 2016). Five indicators (reliability, completeness, temporal, geographical, technological)
each scored 1–5, combined under a lognormal distribution to produce a Geometric Standard Deviation (GSD).
The 95% confidence interval is [central / GSD², central × GSD²].</p>

<h3>Data Sources</h3>
<p>Emission factors: DEFRA/DESNZ GHG Conversion Factors {{ ef_years|join(', ') }}.
EEIO spend-based factors: DEFRA UK Carbon Footprint 2022.
Quality control: ISO 19011 statistical sampling at 95% confidence, 5% acceptable error rate.</p>
```

- [ ] **Step 2: Create appendix template**

Create `hemera/templates/pages/appendix.html`:

```html
<h2>Appendix — Transaction Detail</h2>
<p style="font-size: 8pt; color: #64748B; margin-bottom: 8pt;">
    Full line-item audit trail. {{ transactions|length }} transactions sorted by tCO2e descending.
</p>

{% for chunk in transaction_chunks %}
{% if not loop.first %}<div class="page-break"></div>{% endif %}
<table class="data-table">
    <thead>
        <tr>
            <th>#</th>
            <th>Date</th>
            <th>Description</th>
            <th>Supplier</th>
            <th class="num">Amount (GBP)</th>
            <th>Scope</th>
            <th>Category</th>
            <th>EF Source</th>
            <th>EF Level</th>
            <th class="num">tCO2e</th>
            <th class="num">GSD</th>
        </tr>
    </thead>
    <tbody>
        {% for t in chunk %}
        <tr>
            <td>{{ t.row_number }}</td>
            <td>{{ t.transaction_date or '—' }}</td>
            <td>{{ t.raw_description[:40] if t.raw_description else '—' }}</td>
            <td>{{ t.raw_supplier[:25] if t.raw_supplier else '—' }}</td>
            <td class="num">{{ "{:,.0f}"|format(t.amount_gbp or 0) }}</td>
            <td>{{ t.scope or '—' }}</td>
            <td>{{ t.category_name[:30] if t.category_name else '—' }}</td>
            <td>{{ t.ef_source or '—' }}</td>
            <td>{{ t.ef_level or '—' }}</td>
            <td class="num">{{ "%.3f"|format((t.co2e_kg or 0) / 1000) }}</td>
            <td class="num">{{ "%.2f"|format(t.gsd_total or 0) }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endfor %}
```

- [ ] **Step 3: Commit**

```bash
git add hemera/templates/pages/methodology.html hemera/templates/pages/appendix.html
git commit -m "feat: add methodology note and transaction appendix templates"
```

---

### Task 10: PDF orchestrator

**Files:**
- Create: `hemera/services/pdf_report.py`
- Create: `tests/test_pdf_report.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_pdf_report.py`:

```python
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
        assert len(pdf_bytes) > 10000  # non-trivial PDF
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_pdf_report.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement the PDF orchestrator**

Create `hemera/services/pdf_report.py`:

```python
"""PDF report orchestrator.

Gathers engagement data, generates all charts, renders HTML via Jinja2,
and converts to PDF via WeasyPrint.
"""

from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

from jinja2 import Environment, FileSystemLoader
import weasyprint

from hemera.services.report_charts import (
    chart_scope_donut, chart_top_categories_bar, chart_scope_stacked_bar,
    chart_category_treemap, chart_spend_vs_emissions_scatter,
    chart_monthly_stacked_area, chart_cumulative_line,
    chart_error_bars, chart_pedigree_radar, chart_pedigree_contribution_bar,
    chart_cascade_grouped_bar, chart_reduction_quadrant,
    chart_reduction_waterfall, chart_reduction_potential_bar,
    chart_projection_fan, chart_projection_waterfall, chart_impact_bar,
)
from hemera.services.reduction_recs import generate_reduction_recommendations, compute_projections
from hemera.services.data_quality import (
    compute_cascade_distribution, compute_pedigree_breakdown,
    compute_summary, generate_recommendations,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
ROWS_PER_APPENDIX_PAGE = 30


def generate_report_data(engagement, transactions: list) -> dict:
    """Gather all data and generate all chart SVGs for the report."""
    total_co2e = engagement.total_co2e or 0
    scope1 = engagement.scope1_co2e or 0
    scope2 = engagement.scope2_co2e or 0
    scope3 = engagement.scope3_co2e or 0
    ci_lower = engagement.ci_lower or total_co2e * 0.7
    ci_upper = engagement.ci_upper or total_co2e * 1.4

    # Build category summaries
    cat_groups = defaultdict(lambda: {"co2e_kg": 0, "spend_gbp": 0, "gsd_values": [], "scope": 3})
    for t in transactions:
        if t.co2e_kg and not t.is_duplicate:
            key = t.category_name or "Unclassified"
            cat_groups[key]["co2e_kg"] += t.co2e_kg
            cat_groups[key]["spend_gbp"] += abs(t.amount_gbp or 0)
            if t.gsd_total:
                cat_groups[key]["gsd_values"].append(t.gsd_total)
            cat_groups[key]["scope"] = t.scope or 3

    categories = []
    for name, data in cat_groups.items():
        gsd_vals = data["gsd_values"]
        categories.append({
            "name": name,
            "scope": data["scope"],
            "co2e_tonnes": data["co2e_kg"] / 1000,
            "spend_gbp": data["spend_gbp"],
            "gsd": sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5,
        })
    categories.sort(key=lambda c: c["co2e_tonnes"], reverse=True)

    # Monthly data
    monthly_groups = defaultdict(lambda: {"scope1": 0, "scope2": 0, "scope3": 0})
    dated_count = sum(1 for t in transactions if t.transaction_date)
    has_monthly = dated_count > len(transactions) * 0.5
    if has_monthly:
        for t in transactions:
            if t.transaction_date and t.co2e_kg and not t.is_duplicate:
                month_key = t.transaction_date.strftime("%Y-%m") if hasattr(t.transaction_date, "strftime") else str(t.transaction_date)[:7]
                scope_key = f"scope{t.scope or 3}"
                monthly_groups[month_key][scope_key] += t.co2e_kg / 1000

    monthly_data = [{"month": k, **v} for k, v in sorted(monthly_groups.items())]

    # Existing data quality functions
    summary = compute_summary(transactions)
    cascade = compute_cascade_distribution(transactions)
    pedigree = compute_pedigree_breakdown(transactions)
    dq_recs = generate_recommendations(transactions)

    # Reduction recommendations
    reduction_recs = generate_reduction_recommendations(transactions)

    # Projections
    projections = compute_projections(
        total_co2e_kg=total_co2e * 1000,
        ci_lower_kg=ci_lower * 1000,
        ci_upper_kg=ci_upper * 1000,
        reduction_recs=reduction_recs,
        data_quality_recs=dq_recs,
    )

    # Scope CIs (approximate per-scope using proportional split)
    scope_total = scope1 + scope2 + scope3 or 1
    scope_ci = lambda s: f"±{((ci_upper - ci_lower) / 2 / scope_total * s / (s or 1) * 100):.0f}%" if s > 0 else "—"

    # Pedigree indicators for radar
    pedigree_scores = {k: v["weighted_avg_score"] for k, v in pedigree.items()}
    pedigree_contributions = {k: v["contribution_pct"] for k, v in pedigree.items()}

    # Generate all chart SVGs
    data = {
        # Meta
        "org_name": engagement.org_name,
        "fiscal_year_start": str(engagement.fiscal_year_start or ""),
        "fiscal_year_end": str(engagement.fiscal_year_end or ""),
        "generated_date": datetime.now(timezone.utc).strftime("%d %B %Y"),

        # Totals
        "total_co2e": total_co2e,
        "scope1": scope1, "scope2": scope2, "scope3": scope3,
        "scope1_pct": scope1 / scope_total * 100 if scope_total else 0,
        "scope2_pct": scope2 / scope_total * 100 if scope_total else 0,
        "scope3_pct": scope3 / scope_total * 100 if scope_total else 0,
        "ci_lower": ci_lower, "ci_upper": ci_upper,
        "scope1_ci": scope_ci(scope1), "scope2_ci": scope_ci(scope2), "scope3_ci": scope_ci(scope3),
        "total_ci": f"{ci_lower:.1f}–{ci_upper:.1f}",
        "data_quality_grade": summary["data_quality_grade"],

        # Categories
        "categories": categories,

        # Charts — exec summary
        "scope_donut_svg": chart_scope_donut(scope1, scope2, scope3),
        "top_categories_mini_svg": chart_top_categories_bar(categories, limit=5),

        # Charts — scope breakdown
        "scope_stacked_bar_svg": chart_scope_stacked_bar(scope1, scope2, scope3, ci_lower, ci_upper),
        "treemap_svg": chart_category_treemap(categories),

        # Charts — hotspots
        "top_categories_bar_svg": chart_top_categories_bar(categories, limit=10),
        "spend_vs_emissions_svg": chart_spend_vs_emissions_scatter(categories[:15]),

        # Charts — monthly
        "has_monthly_data": has_monthly,
        "monthly_area_svg": chart_monthly_stacked_area(monthly_data) if has_monthly and monthly_data else "",
        "cumulative_line_svg": chart_cumulative_line(monthly_data) if has_monthly and monthly_data else "",

        # Charts — reduction
        "reduction_recs": reduction_recs,
        "quadrant_svg": chart_reduction_quadrant([
            {"action": r["action"][:40], "type": r["type"],
             "reduction_tonnes": r["potential_reduction_kg"] / 1000, "effort": r["effort"]}
            for r in reduction_recs[:8]
        ]) if reduction_recs else "",
        "reduction_waterfall_svg": chart_reduction_waterfall(
            total_co2e, [
                {"action": r["action"][:30], "reduction_tonnes": r["potential_reduction_kg"] / 1000}
                for r in reduction_recs[:6]
            ]
        ) if reduction_recs else "",
        "reduction_bar_svg": chart_reduction_potential_bar([
            {"action": r["action"][:40], "type": r["type"],
             "reduction_tonnes": r["potential_reduction_kg"] / 1000}
            for r in reduction_recs
        ]) if reduction_recs else "",

        # Charts — projections
        "year3_target": projections["year3_target_kg"] / 1000,
        "ci_reduction_pct": round((1 - (projections["year3_ci_upper_kg"] - projections["year3_ci_lower_kg"]) / ((ci_upper - ci_lower) * 1000)) * 100, 0) if (ci_upper - ci_lower) > 0 else 0,
        "fan_chart_svg": chart_projection_fan(
            baseline=total_co2e,
            ci_lower=ci_lower, ci_upper=ci_upper,
            year2_ci_lower=projections["year2_ci_lower_kg"] / 1000,
            year2_ci_upper=projections["year2_ci_upper_kg"] / 1000,
            year3_target=projections["year3_target_kg"] / 1000,
            year3_ci_lower=projections["year3_ci_lower_kg"] / 1000,
            year3_ci_upper=projections["year3_ci_upper_kg"] / 1000,
        ),
        "projection_waterfall_svg": chart_projection_waterfall(
            baseline=total_co2e,
            year2_data_improvement=0,
            year2_ci_narrowing=round((ci_upper - ci_lower) - (projections["year2_ci_upper_kg"] - projections["year2_ci_lower_kg"]) / 1000, 1),
            year3_reductions=-projections["total_reduction_kg"] / 1000,
        ),

        # Charts — uncertainty
        "error_bars_svg": chart_error_bars([
            {"name": "Scope 1", "value": scope1, "ci_lower": scope1 * 0.65, "ci_upper": scope1 * 1.5},
            {"name": "Scope 2", "value": scope2, "ci_lower": scope2 * 0.72, "ci_upper": scope2 * 1.39},
            {"name": "Scope 3", "value": scope3, "ci_lower": scope3 * 0.68, "ci_upper": scope3 * 1.47},
            {"name": "Total", "value": total_co2e, "ci_lower": ci_lower, "ci_upper": ci_upper},
        ]),
        "radar_svg": chart_pedigree_radar(pedigree_scores),
        "pedigree_bar_svg": chart_pedigree_contribution_bar(pedigree_contributions),

        # Charts — data quality
        "cascade_bar_svg": chart_cascade_grouped_bar(
            cascade["current_by_spend_pct"],
            cascade["target_by_spend_pct"],
        ),
        "impact_bar_svg": chart_impact_bar([
            {"action": r.get("current_code", r.get("category", "Unknown"))[:40],
             "impact_score": r.get("impact_score", 0)}
            for r in dq_recs[:5]
        ]) if dq_recs else "",

        # Methodology
        "ef_years": sorted({t.ef_year for t in transactions if t.ef_year}),

        # Appendix
        "transactions": sorted(
            [t for t in transactions if not t.is_duplicate],
            key=lambda t: t.co2e_kg or 0,
            reverse=True,
        ),
        "transaction_chunks": [],
    }

    # Chunk transactions for appendix pagination
    txns = data["transactions"]
    data["transaction_chunks"] = [txns[i:i + ROWS_PER_APPENDIX_PAGE] for i in range(0, len(txns), ROWS_PER_APPENDIX_PAGE)]

    return data


def render_report_html(data: dict) -> str:
    """Render the report data into a complete HTML string."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("report_base.html")

    pages = [
        "pages/executive_summary.html",
        "pages/scope_breakdown.html",
        "pages/hotspots.html",
        "pages/monthly.html",
        "pages/reduction_roadmap.html",
        "pages/quick_wins.html",
        "pages/projections.html",
        "pages/uncertainty.html",
        "pages/data_quality.html",
        "pages/methodology.html",
        "pages/appendix.html",
    ]

    return template.render(pages=pages, **data)


def generate_pdf(html: str) -> bytes:
    """Convert rendered HTML to PDF bytes via WeasyPrint."""
    css_path = str(TEMPLATES_DIR / "report.css")
    doc = weasyprint.HTML(string=html, base_url=str(TEMPLATES_DIR))
    return doc.write_pdf(stylesheets=[weasyprint.CSS(filename=css_path)])
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_pdf_report.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hemera/services/pdf_report.py tests/test_pdf_report.py
git commit -m "feat: add PDF report orchestrator — data gathering, HTML rendering, PDF generation"
```

---

### Task 11: API endpoint

**Files:**
- Modify: `hemera/api/reports.py`

- [ ] **Step 1: Add PDF endpoint to reports.py**

Add to `hemera/api/reports.py` after the existing data-quality endpoint:

```python
from fastapi.responses import Response
from hemera.services.pdf_report import generate_report_data, render_report_html, generate_pdf


@router.get("/reports/{engagement_id}/pdf")
def get_pdf_report(engagement_id: int, db: Session = Depends(get_db), current_user: ClerkUser = Depends(get_current_user)):
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if current_user.role != "admin" and engagement.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")
    if engagement.status != "delivered":
        raise HTTPException(status_code=400, detail="Report not yet delivered")

    transactions = db.query(Transaction).filter(Transaction.engagement_id == engagement_id).all()
    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found")

    data = generate_report_data(engagement, transactions)
    html = render_report_html(data)
    pdf_bytes = generate_pdf(html)

    filename = f"hemera-carbon-report-{engagement.org_name.replace(' ', '-').lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 2: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: All tests PASS (existing + new).

- [ ] **Step 3: Commit**

```bash
git add hemera/api/reports.py
git commit -m "feat: add GET /api/reports/{id}/pdf endpoint for carbon footprint report"
```

---

### Task 12: Full regression and integration test

**Files:** None modified — verification only.

- [ ] **Step 1: Run the full test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 2: Generate a test PDF manually**

```bash
.venv/bin/python -c "
from hemera.services.pdf_report import generate_report_data, render_report_html, generate_pdf
from unittest.mock import MagicMock

# Create mock engagement
e = MagicMock()
e.id = 1
e.org_name = 'Acme Ltd'
e.fiscal_year_start = '2024-04-01'
e.fiscal_year_end = '2025-03-31'
e.total_co2e = 47.2
e.scope1_co2e = 3.8
e.scope2_co2e = 5.7
e.scope3_co2e = 37.7
e.gsd_total = 1.47
e.ci_lower = 32.1
e.ci_upper = 69.4
e.status = 'delivered'

# Create mock transactions
def make_txn(**kw):
    t = MagicMock()
    for k, v in kw.items():
        setattr(t, k, v)
    t.is_duplicate = False
    t.needs_review = False
    t.transaction_date = None
    t.ef_unit = 'kgCO2e/GBP'
    t.ef_value = 0.5
    t.ef_source = 'defra'
    t.ef_year = 2024
    t.ef_region = 'UK'
    t.supplier_id = None
    t.classification_method = 'keyword'
    t.classification_confidence = 0.8
    t.raw_category = 'General'
    return t

txns = [
    make_txn(scope=2, category_name='Purchased electricity', co2e_kg=5700, amount_gbp=15000, gsd_total=1.1, row_number=1, raw_description='Electricity Q1', raw_supplier='EDF', pedigree_reliability=2, pedigree_completeness=2, pedigree_temporal=1, pedigree_geographical=1, pedigree_technological=2, ef_level=4),
    make_txn(scope=3, category_name='Purchased goods — office supplies', co2e_kg=18600, amount_gbp=248000, gsd_total=1.82, row_number=2, raw_description='Office supplies', raw_supplier='Staples', pedigree_reliability=3, pedigree_completeness=2, pedigree_temporal=2, pedigree_geographical=1, pedigree_technological=4, ef_level=4),
    make_txn(scope=3, category_name='Business travel — air', co2e_kg=8200, amount_gbp=42000, gsd_total=1.5, row_number=3, raw_description='Flights', raw_supplier='BA', pedigree_reliability=3, pedigree_completeness=2, pedigree_temporal=2, pedigree_geographical=1, pedigree_technological=3, ef_level=4),
    make_txn(scope=1, category_name='Stationary combustion — gas/heating fuel', co2e_kg=3800, amount_gbp=8000, gsd_total=1.1, row_number=4, raw_description='Gas bill', raw_supplier='British Gas', pedigree_reliability=2, pedigree_completeness=2, pedigree_temporal=1, pedigree_geographical=1, pedigree_technological=2, ef_level=4),
    make_txn(scope=3, category_name='Freight & logistics', co2e_kg=5100, amount_gbp=67000, gsd_total=1.7, row_number=5, raw_description='Courier', raw_supplier='DHL', pedigree_reliability=3, pedigree_completeness=3, pedigree_temporal=2, pedigree_geographical=1, pedigree_technological=4, ef_level=4),
]

data = generate_report_data(e, txns)
html = render_report_html(data)
pdf = generate_pdf(html)

with open('test-report.pdf', 'wb') as f:
    f.write(pdf)
print(f'Generated test-report.pdf ({len(pdf)} bytes)')
"
```

Open `test-report.pdf` and visually verify: cover page, exec summary with donut chart, scope breakdown, hotspots, reduction roadmap, projections, uncertainty, data quality, methodology, appendix.

- [ ] **Step 3: Cleanup and commit**

```bash
rm -f test-report.pdf
git add -A
git commit -m "chore: final integration test for PDF report generation"
```
