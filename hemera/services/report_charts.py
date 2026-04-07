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
        "paper_bgcolor": "#F5F5F0",
        "plot_bgcolor": "#FAFAF7",
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
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=20, b=40),
    )
    return _to_svg(fig, width=360, height=320)


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
            y=["Emissions"],
            x=[val],
            name=name,
            orientation="h",
            marker_color=SCOPE_COLOURS[scope],
        ))
    # CI whiskers as invisible scatter with error bars
    fig.add_trace(go.Scatter(
        y=["Emissions"],
        x=[total],
        error_x=dict(
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
    fig.update_layout(barmode="stack", xaxis_title="tCO2e")
    return _to_svg(fig, width=500, height=250)


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
    # Group by scope for legend
    scope_groups: dict[int, list[dict]] = {}
    for c in categories:
        scope_groups.setdefault(c["scope"], []).append(c)
    scope_names = {1: "Scope 1", 2: "Scope 2", 3: "Scope 3"}
    for scope in sorted(scope_groups.keys()):
        cats = scope_groups[scope]
        fig.add_trace(go.Scatter(
            x=[c["spend_gbp"] for c in cats],
            y=[c["co2e_tonnes"] for c in cats],
            mode="markers+text",
            marker=dict(
                size=[max(c.get("gsd", 1.0) * 20, 10) for c in cats],
                color=SCOPE_COLOURS.get(scope, "#64748B"),
                opacity=0.7,
            ),
            text=[c["name"] for c in cats],
            textposition="top center",
            textfont=dict(size=9),
            name=scope_names.get(scope, f"Scope {scope}"),
            showlegend=True,
        ))
    fig.update_layout(
        xaxis_title="Spend (GBP)",
        yaxis_title="tCO2e",
        margin=dict(l=60, r=20, t=20, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _to_svg(fig, width=700, height=400)


def chart_monthly_stacked_area(monthly_data: list[dict]) -> str:
    """Stacked area chart of monthly emissions by scope."""
    months = [m["month"] for m in monthly_data]
    fig = go.Figure()
    scope_fill_colours = {
        1: "rgba(30,41,59,0.5)",
        2: "rgba(13,148,136,0.5)",
        3: "rgba(245,158,11,0.5)",
    }
    for scope, key, name in [(1, "scope1", "Scope 1"), (2, "scope2", "Scope 2"), (3, "scope3", "Scope 3")]:
        fig.add_trace(go.Scatter(
            x=months,
            y=[m[key] for m in monthly_data],
            name=name,
            mode="lines",
            stackgroup="one",
            line=dict(width=0.5, color=SCOPE_COLOURS[scope]),
            fillcolor=scope_fill_colours[scope],
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
    scope_names = {1: "Scope 1", 2: "Scope 2", 3: "Scope 3"}
    for i, s in enumerate(scopes):
        scope_num = i + 1
        colour = SCOPE_COLOURS.get(scope_num, "#64748B")
        fig.add_trace(go.Bar(
            x=[s["name"]],
            y=[s["value"]],
            error_y=dict(
                type="data",
                symmetric=False,
                array=[s["ci_upper"] - s["value"]],
                arrayminus=[s["value"] - s["ci_lower"]],
                color="#64748B",
                thickness=2,
                width=6,
            ),
            marker_color=colour,
            name=scope_names.get(scope_num, s["name"]),
            showlegend=True,
        ))
    fig.update_layout(
        yaxis_title="tCO2e",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _to_svg(fig, width=500, height=350)


def chart_pedigree_radar(indicators: dict[str, float]) -> str:
    """Radar chart of 5 pedigree indicator weighted average scores."""
    names = list(indicators.keys())
    values = list(indicators.values())
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
        y=level_labels,
        x=[current_pct.get(l, 0) for l in levels],
        name="Current",
        orientation="h",
        marker_color="#F59E0B",
    ))
    fig.add_trace(go.Bar(
        y=level_labels,
        x=[target_pct.get(l, 0) for l in levels],
        name="Target",
        orientation="h",
        marker_color="#0D9488",
    ))
    fig.update_layout(
        barmode="group",
        xaxis_title="% of spend",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=120, r=20, t=40, b=40),
    )
    return _to_svg(fig, width=700, height=350)


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
    # Group by type for legend
    type_groups: dict[str, list[dict]] = {}
    for r in reductions:
        type_groups.setdefault(r["type"], []).append(r)
    for type_name in sorted(type_groups.keys()):
        items = type_groups[type_name]
        colour = TYPE_COLOURS.get(type_name, "#64748B")
        fig.add_trace(go.Scatter(
            x=[EFFORT_MAP.get(r["effort"], 2) for r in items],
            y=[r["reduction_tonnes"] for r in items],
            mode="markers+text",
            marker=dict(
                size=[max(r["reduction_tonnes"] * 8, 15) for r in items],
                color=colour,
                opacity=0.7,
            ),
            text=[r["action"] for r in items],
            textposition="top center",
            textfont=dict(size=9),
            name=type_name.capitalize(),
            showlegend=True,
        ))
    fig.add_hline(y=sum(r["reduction_tonnes"] for r in reductions) / len(reductions), line_dash="dot", line_color="#CBD5E1")
    fig.add_vline(x=2, line_dash="dot", line_color="#CBD5E1")
    fig.add_annotation(x=1, y=max(r["reduction_tonnes"] for r in reductions) * 1.1, text="Quick Wins", showarrow=False, font=dict(size=10, color="#10B981"))
    fig.add_annotation(x=3, y=max(r["reduction_tonnes"] for r in reductions) * 1.1, text="Strategic", showarrow=False, font=dict(size=10, color="#F59E0B"))
    fig.update_layout(
        xaxis=dict(title="Effort", tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"], range=[0.5, 3.5]),
        yaxis_title="Reduction potential (tCO2e)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _to_svg(fig, width=600, height=400)


def chart_reduction_waterfall(current_total: float, reductions: list[dict]) -> str:
    """Waterfall from current total through each reduction to projected total."""
    sorted_recs = sorted(reductions, key=lambda r: r["reduction_tonnes"], reverse=True)

    labels = ["Current"] + [r["action"] for r in sorted_recs] + ["Projected"]
    measures = ["absolute"] + ["relative"] * len(sorted_recs) + ["total"]
    values = [current_total] + [-r["reduction_tonnes"] for r in sorted_recs] + [0]

    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=measures,
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
    fig.add_trace(go.Scatter(
        x=years + years[::-1], y=upper + lower[::-1],
        fill="toself", fillcolor="rgba(13,148,136,0.12)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=years, y=central, mode="lines+markers",
        line=dict(color="#0D9488", width=3),
        marker=dict(size=10, color="#0D9488"), name="Central estimate",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=[baseline, baseline, baseline], mode="lines",
        line=dict(color="#EF4444", width=1.5, dash="dash"), name="Do nothing",
    ))
    fig.update_layout(
        yaxis_title="tCO2e",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _to_svg(fig, width=700, height=400)


def chart_projection_waterfall(
    baseline: float, year2_data_improvement: float,
    year2_ci_narrowing: float, year3_reductions: float,
) -> str:
    """Stepped waterfall: baseline → better data → reductions → target."""
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
