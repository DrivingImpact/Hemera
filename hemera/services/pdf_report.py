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

TYPE_LABELS = {
    "chart_of_accounts": "Split code",
    "activity_data": "Collect activity data",
    "supplier_engagement": "Engage supplier",
}


def _format_dq_rec_label(rec: dict) -> str:
    """Format a data quality recommendation into a readable chart label."""
    rec_type = rec.get("type", "")
    prefix = TYPE_LABELS.get(rec_type, "Improve")
    target = rec.get("current_code", rec.get("category", ""))
    if target:
        return f"{prefix}: {target[:30]}"
    return prefix


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
            {"action": _format_dq_rec_label(r),
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
