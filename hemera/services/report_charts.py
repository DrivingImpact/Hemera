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
