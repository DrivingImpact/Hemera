"""Engagement data aggregation.

Extracts the category/monthly/supplier aggregation logic from pdf_report.py
into reusable functions for both the PDF report and the dashboard API.
"""

from collections import defaultdict


def build_category_summary(transactions: list) -> list[dict]:
    """Group transactions by category, return sorted list of category dicts."""
    groups = defaultdict(lambda: {"co2e_kg": 0, "spend_gbp": 0, "gsd_values": [], "scope": 3})
    for t in transactions:
        if t.co2e_kg and not t.is_duplicate:
            key = t.category_name or "Unclassified"
            groups[key]["co2e_kg"] += t.co2e_kg
            groups[key]["spend_gbp"] += abs(t.amount_gbp or 0)
            if t.gsd_total:
                groups[key]["gsd_values"].append(t.gsd_total)
            groups[key]["scope"] = t.scope or 3

    categories = []
    for name, data in groups.items():
        gsd_vals = data["gsd_values"]
        categories.append({
            "name": name,
            "scope": data["scope"],
            "co2e_tonnes": data["co2e_kg"] / 1000,
            "spend_gbp": data["spend_gbp"],
            "gsd": sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5,
        })
    categories.sort(key=lambda c: c["co2e_tonnes"], reverse=True)
    return categories


def build_monthly_summary(transactions: list) -> dict:
    """Group transactions by month and scope. Returns {has_data, months}."""
    dated_count = sum(1 for t in transactions if t.transaction_date)
    has_data = dated_count > len(transactions) * 0.5
    if not has_data:
        return {"has_data": False, "months": []}

    groups = defaultdict(lambda: {"scope1": 0, "scope2": 0, "scope3": 0})
    for t in transactions:
        if t.transaction_date and t.co2e_kg and not t.is_duplicate:
            month_key = (
                t.transaction_date.strftime("%Y-%m")
                if hasattr(t.transaction_date, "strftime")
                else str(t.transaction_date)[:7]
            )
            scope_key = f"scope{t.scope or 3}"
            groups[month_key][scope_key] += t.co2e_kg / 1000

    months = [{"month": k, **v} for k, v in sorted(groups.items())]
    return {"has_data": True, "months": months}


def build_engagement_suppliers(transactions: list) -> list[dict]:
    """Group transactions by supplier for this engagement."""
    groups = defaultdict(lambda: {
        "supplier_id": None, "name": "Unknown", "co2e_kg": 0,
        "spend_gbp": 0, "transaction_count": 0,
    })
    for t in transactions:
        if t.is_duplicate:
            continue
        key = t.supplier_id or t.raw_supplier or "Unknown"
        groups[key]["supplier_id"] = t.supplier_id
        groups[key]["name"] = t.raw_supplier or "Unknown"
        groups[key]["co2e_kg"] += t.co2e_kg or 0
        groups[key]["spend_gbp"] += abs(t.amount_gbp or 0)
        groups[key]["transaction_count"] += 1

    suppliers = []
    for data in groups.values():
        spend = data["spend_gbp"]
        co2e = data["co2e_kg"]
        suppliers.append({
            "supplier_id": data["supplier_id"],
            "name": data["name"],
            "co2e_tonnes": co2e / 1000,
            "spend_gbp": spend,
            "intensity_kg_per_gbp": co2e / spend if spend > 0 else 0,
            "transaction_count": data["transaction_count"],
        })
    suppliers.sort(key=lambda s: s["co2e_tonnes"], reverse=True)
    return suppliers
