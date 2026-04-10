"""HemeraScope PDF report orchestrator.

Gathers supplier intelligence data, generates charts, renders HTML via Jinja2,
and converts to PDF via WeasyPrint. Follows the same pattern as pdf_report.py.
"""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func
from sqlalchemy.orm import Session
import plotly.graph_objects as go
import weasyprint

from hemera.models.engagement import Engagement
from hemera.models.finding import SupplierFinding, ReportSelection, ReportAction
from hemera.models.supplier import Supplier
from hemera.models.supplier_engagement import SupplierEngagement
from hemera.models.transaction import Transaction

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Brand colours
TEAL = "#0D9488"
SLATE = "#1E293B"
AMBER = "#F59E0B"
BEIGE = "#F5F5F0"

SEVERITY_COLOURS = {
    "critical": "#EF4444",
    "high": "#F59E0B",
    "medium": "#FB923C",
    "info": "#64748B",
    "positive": "#10B981",
}

DOMAIN_LABELS = {
    "governance": "Governance",
    "governance_identity": "Governance",
    "labour": "Labour",
    "labour_ethics": "Labour",
    "carbon": "Carbon",
    "carbon_climate": "Carbon",
    "water": "Water",
    "water_biodiversity": "Water",
    "product": "Product",
    "product_supply_chain": "Product",
    "transparency": "Transparency",
    "transparency_disclosure": "Transparency",
    "anti_corruption": "Anti-Corruption",
    "social_value": "Social Value",
}

HEMERA_CHART_LAYOUT = {
    "font": {"family": "Plus Jakarta Sans, system-ui, sans-serif", "size": 13, "color": SLATE},
    "paper_bgcolor": BEIGE,
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 60, "r": 20, "t": 40, "b": 40},
}


def _to_svg(fig: go.Figure, width: int = 600, height: int = 400) -> str:
    """Convert a Plotly figure to an inline SVG string."""
    import plotly.io as pio
    fig.update_layout(**HEMERA_CHART_LAYOUT)
    return pio.to_image(fig, format="svg", width=width, height=height).decode("utf-8")


def chart_risk_donut(severity_counts: dict) -> str:
    """Donut chart of finding severity distribution."""
    labels = []
    values = []
    colours = []
    for sev in ["critical", "high", "medium", "info", "positive"]:
        count = severity_counts.get(sev, 0)
        if count > 0:
            labels.append(sev.capitalize())
            values.append(count)
            colours.append(SEVERITY_COLOURS.get(sev, "#64748B"))

    if not values:
        return ""

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colours),
        textinfo="label+value",
        textposition="outside",
        outsidetextfont=dict(size=11),
        hoverinfo="label+value",
    )])
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=30, b=40),
    )
    return _to_svg(fig, width=400, height=340)


def chart_domain_bar(domain_counts: dict) -> str:
    """Horizontal bar chart of findings per domain."""
    if not domain_counts:
        return ""

    sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1])
    labels = [DOMAIN_LABELS.get(d, d.replace("_", " ").title()) for d, _ in sorted_domains]
    values = [v for _, v in sorted_domains]

    fig = go.Figure(data=[go.Bar(
        y=labels,
        x=values,
        orientation="h",
        marker_color=TEAL,
        text=[str(v) for v in values],
        textposition="outside",
        textfont=dict(size=12),
    )])
    fig.update_layout(
        xaxis_title="Number of findings",
        xaxis=dict(title_font=dict(size=12), tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=12)),
        margin=dict(l=160, r=40, t=20, b=40),
    )
    height = max(250, len(labels) * 35 + 60)
    return _to_svg(fig, width=400, height=height)


def chart_supplier_scores(suppliers: list[dict]) -> str:
    """Horizontal bar chart of supplier Hemera Scores."""
    scored = [s for s in suppliers if s["supplier"].get("hemera_score") is not None]
    if not scored:
        return ""

    scored.sort(key=lambda s: s["supplier"]["hemera_score"])
    names = [s["supplier"]["name"][:30] for s in scored]
    scores = [s["supplier"]["hemera_score"] for s in scored]
    colours = [
        "#EF4444" if s["supplier"].get("critical_flag") else
        (AMBER if s["supplier"]["hemera_score"] < 60 else TEAL)
        for s in scored
    ]

    fig = go.Figure(data=[go.Bar(
        y=names,
        x=scores,
        orientation="h",
        marker_color=colours,
        text=[f'{s:.0f}' for s in scores],
        textposition="outside",
        textfont=dict(size=11),
    )])
    fig.update_layout(
        xaxis_title="Hemera Score",
        xaxis=dict(title_font=dict(size=12), tickfont=dict(size=11), range=[0, 105]),
        yaxis=dict(tickfont=dict(size=11)),
        margin=dict(l=200, r=40, t=20, b=40),
    )
    height = max(250, len(names) * 28 + 60)
    return _to_svg(fig, width=700, height=height)


def generate_hemerascope_data(engagement: Engagement, db: Session) -> dict:
    """Gather all supplier intelligence data and generate chart SVGs."""
    # Get all supplier IDs for this engagement
    supplier_ids = (
        db.query(Transaction.supplier_id)
        .filter(
            Transaction.engagement_id == engagement.id,
            Transaction.supplier_id.isnot(None),
            Transaction.is_duplicate == False,  # noqa: E712
        )
        .distinct()
        .all()
    )
    supplier_ids = [sid for (sid,) in supplier_ids]

    suppliers_data = []
    all_findings = []
    all_actions = []
    engaged_supplier_ids = set()

    for sid in supplier_ids:
        supplier = db.query(Supplier).filter(Supplier.id == sid).first()
        if not supplier:
            continue

        # Get active findings
        findings = (
            db.query(SupplierFinding)
            .filter(SupplierFinding.supplier_id == sid, SupplierFinding.is_active == True)  # noqa: E712
            .order_by(SupplierFinding.severity, SupplierFinding.created_at.desc())
            .all()
        )

        # Get selections for this engagement
        finding_ids = [f.id for f in findings]
        selections_map = {}
        if finding_ids:
            selections = (
                db.query(ReportSelection)
                .filter(
                    ReportSelection.engagement_id == engagement.id,
                    ReportSelection.finding_id.in_(finding_ids),
                )
                .all()
            )
            selections_map = {s.finding_id: s for s in selections}

        # Build client-facing findings (included only)
        client_findings = []
        for f in findings:
            sel = selections_map.get(f.id)
            if sel and sel.included:
                client_findings.append({
                    "title": sel.client_title or f.title,
                    "detail": sel.client_detail or f.detail,
                    "severity": f.severity,
                    "domain": f.domain,
                })
                all_findings.append({
                    "severity": f.severity,
                    "domain": f.domain,
                })

        # Get actions
        actions = (
            db.query(ReportAction)
            .filter(ReportAction.engagement_id == engagement.id, ReportAction.supplier_id == sid)
            .order_by(ReportAction.priority)
            .all()
        )
        action_dicts = [
            {
                "action_text": a.action_text,
                "priority": a.priority,
                "supplier_name": supplier.name,
            }
            for a in actions
        ]
        all_actions.extend(action_dicts)

        # Get engagements
        hemera_engs = (
            db.query(SupplierEngagement)
            .filter(SupplierEngagement.supplier_id == sid)
            .order_by(SupplierEngagement.created_at.desc())
            .all()
        )
        if hemera_engs:
            engaged_supplier_ids.add(sid)

        engagement_dicts = [
            {
                "engagement_type": e.engagement_type,
                "subject": e.subject,
                "status": e.status,
                "contacted_at": e.contacted_at.strftime("%d %b %Y") if e.contacted_at else None,
            }
            for e in hemera_engs
        ]

        # Transaction stats
        stats = db.query(
            func.count(Transaction.id),
            func.sum(Transaction.amount_gbp),
            func.sum(Transaction.co2e_kg),
        ).filter(
            Transaction.engagement_id == engagement.id,
            Transaction.supplier_id == sid,
            Transaction.is_duplicate == False,  # noqa: E712
        ).first()

        suppliers_data.append({
            "supplier": {
                "name": supplier.name,
                "legal_name": supplier.legal_name,
                "ch_number": supplier.ch_number,
                "sector": supplier.sector,
                "entity_type": supplier.entity_type,
                "hemera_score": supplier.hemera_score,
                "confidence": supplier.confidence,
                "critical_flag": supplier.critical_flag,
            },
            "txn_count": stats[0] if stats else 0,
            "total_spend": round(stats[1] or 0, 2) if stats else 0,
            "total_co2e_kg": round(stats[2] or 0, 2) if stats else 0,
            "findings": client_findings,
            "actions": action_dicts,
            "engagements": engagement_dicts,
        })

    # Sort: critical first, then by hemera_score ascending
    suppliers_data.sort(
        key=lambda s: (
            0 if s["supplier"]["critical_flag"] else 1,
            s["supplier"]["hemera_score"] or 999,
        )
    )

    # Aggregate stats
    severity_counts = Counter(f["severity"] for f in all_findings)
    domain_counts = Counter(f["domain"] for f in all_findings)
    scores = [s["supplier"]["hemera_score"] for s in suppliers_data if s["supplier"]["hemera_score"] is not None]
    avg_score = sum(scores) / len(scores) if scores else 0
    critical_count = sum(1 for s in suppliers_data if s["supplier"]["critical_flag"])

    # Generate charts
    risk_donut_svg = chart_risk_donut(dict(severity_counts)) if all_findings else ""
    domain_bar_svg = chart_domain_bar(dict(domain_counts)) if all_findings else ""
    supplier_score_bar_svg = chart_supplier_scores(suppliers_data)

    # Group actions by priority
    priority_1 = [a for a in all_actions if a["priority"] == 1]
    priority_2 = [a for a in all_actions if a["priority"] == 2]
    priority_3 = [a for a in all_actions if a["priority"] >= 3]

    data = {
        # Meta
        "org_name": engagement.org_name,
        "fiscal_year_start": str(engagement.fiscal_year_start or ""),
        "fiscal_year_end": str(engagement.fiscal_year_end or ""),
        "generated_date": datetime.now(timezone.utc).strftime("%d %B %Y"),

        # Carbon data (if available)
        "total_co2e": engagement.total_co2e or 0,
        "scope3": engagement.scope3_co2e or 0,
        "data_quality_grade": getattr(engagement, "data_quality_grade", None) or "",

        # Supplier aggregate stats
        "supplier_count": len(suppliers_data),
        "avg_hemera_score": avg_score,
        "critical_count": critical_count,
        "total_findings": len(all_findings),
        "high_severity_count": severity_counts.get("critical", 0) + severity_counts.get("high", 0),
        "positive_count": severity_counts.get("positive", 0),
        "engaged_count": len(engaged_supplier_ids),

        # Charts
        "risk_donut_svg": risk_donut_svg,
        "domain_bar_svg": domain_bar_svg,
        "supplier_score_bar_svg": supplier_score_bar_svg,

        # Severity table
        "severity_counts": dict(severity_counts),

        # Supplier pages
        "supplier_pages": suppliers_data,

        # Recommendations
        "priority_1_actions": priority_1,
        "priority_2_actions": priority_2,
        "priority_3_actions": priority_3,
    }

    return data


def render_hemerascope_html(data: dict) -> str:
    """Render HemeraScope report data into a complete HTML string."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("hemerascope/base.html")

    pages = [
        "hemerascope/exec_summary.html",
        "hemerascope/methodology.html",
        "hemerascope/risk_overview.html",
        "hemerascope/recommendations.html",
    ]

    return template.render(pages=pages, **data)


def generate_hemerascope_pdf(engagement: Engagement, db: Session) -> bytes:
    """Generate the full HemeraScope PDF report.

    Returns PDF bytes ready for HTTP response or file storage.
    """
    data = generate_hemerascope_data(engagement, db)
    html = render_hemerascope_html(data)

    css_path = str(TEMPLATES_DIR / "report.css")
    doc = weasyprint.HTML(string=html, base_url=str(TEMPLATES_DIR))
    return doc.write_pdf(stylesheets=[weasyprint.CSS(filename=css_path)])
