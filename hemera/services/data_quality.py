"""Data Quality Improvement Report engine.

Analyses engagement transactions to identify uncertainty sources and
generate ranked recommendations for improving carbon footprint accuracy.
Pure functions — no DB writes, no side effects.
"""

import math
from datetime import datetime, timezone
from hemera.services.pedigree import (
    RELIABILITY_GSD, COMPLETENESS_GSD, TEMPORAL_GSD,
    GEOGRAPHICAL_GSD, TECHNOLOGICAL_GSD, BASIC_GSD,
)

VAGUE_CODES = {
    "sundries", "general expenses", "miscellaneous", "other costs",
    "office costs", "general supplies", "other expenses", "admin",
    "administration", "various", "petty cash", "other overheads",
    "general overheads", "sundry expenses", "other purchases",
    "unclassified", "general", "misc",
}


def detect_vague_codes(transactions: list) -> list[dict]:
    """Identify transactions with vague nominal codes.

    A transaction is vague if:
    - classification_method == 'none', OR
    - classification_confidence < 0.7, OR
    - raw_category (lowercased) is in the VAGUE_CODES set
    """
    vague_txns = []
    for t in transactions:
        if t.co2e_kg is None or t.is_duplicate:
            continue
        raw_cat = (t.raw_category or "").strip()
        is_vague = (
            t.classification_method == "none"
            or (t.classification_confidence is not None and t.classification_confidence < 0.7)
            or raw_cat.lower() in VAGUE_CODES
        )
        if is_vague:
            vague_txns.append(t)

    groups: dict[str, list] = {}
    for t in vague_txns:
        key = (t.raw_category or "(blank)").strip()
        groups.setdefault(key, []).append(t)

    result = []
    for raw_cat, txns in groups.items():
        spend = sum(abs(t.amount_gbp or 0) for t in txns)
        classified_as = sorted({t.category_name for t in txns if t.category_name})
        result.append({
            "raw_category": raw_cat,
            "transaction_count": len(txns),
            "spend_gbp": spend,
            "classified_as": classified_as,
        })

    result.sort(key=lambda r: r["spend_gbp"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Task 2: Uncertainty Contribution Decomposition
# ---------------------------------------------------------------------------

def _uncertainty_contribution(co2e: float, gsd: float, total_co2e: float) -> float:
    if total_co2e == 0 or gsd <= 0 or co2e <= 0:
        return 0.0
    weight = co2e / total_co2e
    return (weight * math.log(gsd)) ** 2


def _dominant_pedigree_indicator(t) -> str:
    indicators = {
        "reliability": RELIABILITY_GSD.get(t.pedigree_reliability or 3, 1.61),
        "completeness": COMPLETENESS_GSD.get(t.pedigree_completeness or 3, 1.04),
        "temporal": TEMPORAL_GSD.get(t.pedigree_temporal or 3, 1.10),
        "geographical": GEOGRAPHICAL_GSD.get(t.pedigree_geographical or 3, 1.08),
        "technological": TECHNOLOGICAL_GSD.get(t.pedigree_technological or 3, 1.12),
    }
    return max(indicators, key=lambda k: math.log(indicators[k]) ** 2)


def compute_uncertainty_contributors(transactions: list) -> list[dict]:
    valid = [t for t in transactions if t.co2e_kg and t.co2e_kg > 0 and not t.is_duplicate]
    total_co2e = sum(t.co2e_kg for t in valid)
    if total_co2e == 0:
        return []

    txn_contributions = []
    for t in valid:
        contrib = _uncertainty_contribution(t.co2e_kg, t.gsd_total or 1.0, total_co2e)
        txn_contributions.append((t, contrib))

    total_variance = sum(c for _, c in txn_contributions)
    if total_variance == 0:
        return []

    groups: dict[str, list[tuple]] = {}
    for t, contrib in txn_contributions:
        key = (t.raw_category or "(blank)").strip()
        groups.setdefault(key, []).append((t, contrib))

    result = []
    for raw_cat, items in groups.items():
        txns_in_group = [t for t, _ in items]
        group_variance = sum(c for _, c in items)
        group_co2e = sum(t.co2e_kg for t in txns_in_group)
        group_spend = sum(abs(t.amount_gbp or 0) for t in txns_in_group)
        gsd_values = [t.gsd_total for t in txns_in_group if t.gsd_total]
        top_txn = max(items, key=lambda x: x[1])[0]

        result.append({
            "raw_category": raw_cat,
            "transaction_count": len(txns_in_group),
            "spend_gbp": group_spend,
            "co2e_kg": group_co2e,
            "avg_gsd": sum(gsd_values) / len(gsd_values) if gsd_values else 1.0,
            "uncertainty_contribution_pct": round(group_variance / total_variance * 100, 1),
            "dominant_pedigree_indicator": _dominant_pedigree_indicator(top_txn),
        })

    result.sort(key=lambda r: r["uncertainty_contribution_pct"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Task 3: Cascade Distribution and Pedigree Breakdown
# ---------------------------------------------------------------------------

CASCADE_TARGET = {"L1": 10, "L2": 30, "L3": 20, "L4": 30, "L5": 10, "L6": 0}


def compute_cascade_distribution(transactions: list) -> dict:
    valid = [t for t in transactions if t.co2e_kg is not None and not t.is_duplicate]
    total_spend = sum(abs(t.amount_gbp or 0) for t in valid)
    total_co2e = sum(t.co2e_kg for t in valid)

    spend_by_level = {f"L{i}": 0.0 for i in range(1, 7)}
    co2e_by_level = {f"L{i}": 0.0 for i in range(1, 7)}

    for t in valid:
        level_key = f"L{t.ef_level or 5}"
        if level_key not in spend_by_level:
            level_key = "L6"
        spend_by_level[level_key] += abs(t.amount_gbp or 0)
        co2e_by_level[level_key] += t.co2e_kg

    spend_pct = {k: round(v / total_spend * 100, 1) if total_spend > 0 else 0.0 for k, v in spend_by_level.items()}
    co2e_pct = {k: round(v / total_co2e * 100, 1) if total_co2e > 0 else 0.0 for k, v in co2e_by_level.items()}

    return {
        "current_by_spend_pct": spend_pct,
        "current_by_co2e_pct": co2e_pct,
        "target_by_spend_pct": CASCADE_TARGET.copy(),
    }


def compute_pedigree_breakdown(transactions: list) -> dict:
    valid = [t for t in transactions if t.co2e_kg and t.co2e_kg > 0 and not t.is_duplicate]
    total_co2e = sum(t.co2e_kg for t in valid)

    if total_co2e == 0:
        return {ind: {"weighted_avg_score": 0, "contribution_pct": 0}
                for ind in ["reliability", "completeness", "temporal", "geographical", "technological"]}

    gsd_maps = {
        "reliability": RELIABILITY_GSD,
        "completeness": COMPLETENESS_GSD,
        "temporal": TEMPORAL_GSD,
        "geographical": GEOGRAPHICAL_GSD,
        "technological": TECHNOLOGICAL_GSD,
    }
    score_attrs = {
        "reliability": "pedigree_reliability",
        "completeness": "pedigree_completeness",
        "temporal": "pedigree_temporal",
        "geographical": "pedigree_geographical",
        "technological": "pedigree_technological",
    }

    weighted_scores = {}
    for ind, attr in score_attrs.items():
        weighted_sum = sum((getattr(t, attr) or 3) * t.co2e_kg for t in valid)
        weighted_scores[ind] = round(weighted_sum / total_co2e, 1)

    indicator_variance = {ind: 0.0 for ind in gsd_maps}
    for t in valid:
        weight = t.co2e_kg / total_co2e
        for ind, gsd_map in gsd_maps.items():
            score = getattr(t, score_attrs[ind]) or 3
            gsd_val = gsd_map.get(score, 1.0)
            indicator_variance[ind] += (weight * math.log(gsd_val)) ** 2

    total_indicator_variance = sum(indicator_variance.values())
    if total_indicator_variance == 0:
        total_indicator_variance = 1.0

    result = {}
    for ind in gsd_maps:
        result[ind] = {
            "weighted_avg_score": weighted_scores[ind],
            "contribution_pct": round(indicator_variance[ind] / total_indicator_variance * 100, 1),
        }
    return result


# ---------------------------------------------------------------------------
# Task 4: Data Quality Grade and Summary
# ---------------------------------------------------------------------------

def compute_data_quality_grade(cascade_spend_pct: dict) -> str:
    l1_l2 = cascade_spend_pct.get("L1", 0) + cascade_spend_pct.get("L2", 0)
    l1_l3 = l1_l2 + cascade_spend_pct.get("L3", 0)
    l4_plus = cascade_spend_pct.get("L4", 0) + cascade_spend_pct.get("L5", 0) + cascade_spend_pct.get("L6", 0)
    if l1_l2 > 60:
        return "A"
    if l1_l3 > 40:
        return "B"
    if l4_plus > 80:
        return "D"
    if l4_plus > 60:
        return "C"
    return "E"


def compute_summary(transactions: list) -> dict:
    valid = [t for t in transactions if t.co2e_kg is not None and not t.is_duplicate]
    total_spend = sum(abs(t.amount_gbp or 0) for t in valid)
    total_co2e_kg = sum(t.co2e_kg for t in valid)

    vague_codes = detect_vague_codes(transactions)
    vague_count = sum(v["transaction_count"] for v in vague_codes)
    vague_spend = sum(v["spend_gbp"] for v in vague_codes)

    cascade = compute_cascade_distribution(transactions)
    grade = compute_data_quality_grade(cascade["current_by_spend_pct"])

    gsd_values = [t.gsd_total for t in valid if t.gsd_total and t.gsd_total > 0]
    co2e_values = [t.co2e_kg for t in valid if t.gsd_total and t.gsd_total > 0]

    if gsd_values and co2e_values:
        total = sum(co2e_values)
        ln_sq_sum = 0.0
        for gsd, co2e in zip(gsd_values, co2e_values):
            weight = co2e / total
            ln_sq_sum += (weight * math.log(gsd)) ** 2
        overall_gsd = math.exp(math.sqrt(ln_sq_sum))
    else:
        overall_gsd = 1.0

    ci_pct = round((overall_gsd ** 2 - 1) * 100, 0)

    return {
        "overall_gsd": round(overall_gsd, 3),
        "ci_95_percent": f"+/-{int(ci_pct)}%",
        "total_spend_gbp": round(total_spend, 2),
        "total_co2e_tonnes": round(total_co2e_kg / 1000, 2),
        "data_quality_grade": grade,
        "transactions_analysed": len(valid),
        "vague_code_count": vague_count,
        "vague_code_spend_gbp": round(vague_spend, 2),
        "vague_code_spend_pct": round(vague_spend / total_spend * 100, 1) if total_spend > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Task 5: Recommendations Engine
# ---------------------------------------------------------------------------

ACTIVITY_DATA_CATEGORIES = {
    "Purchased electricity": {
        "data_needed": "kWh from electricity bills or supplier portal",
        "recommended_method": "activity-based kWh (Level 2)",
        "projected_gsd": 1.05,
    },
    "Purchased heat/steam/cooling": {
        "data_needed": "kWh from heating bills",
        "recommended_method": "activity-based kWh (Level 2)",
        "projected_gsd": 1.10,
    },
    "Stationary combustion — gas/heating fuel": {
        "data_needed": "kWh or litres from gas bills",
        "recommended_method": "activity-based kWh/litres (Level 2)",
        "projected_gsd": 1.05,
    },
    "Mobile combustion — company vehicles": {
        "data_needed": "Litres from fuel card statements",
        "recommended_method": "activity-based litres (Level 2)",
        "projected_gsd": 1.10,
    },
    "Waste generated in operations": {
        "data_needed": "Tonnes by waste type from contractor reports",
        "recommended_method": "waste-type based tonnes (Level 2)",
        "projected_gsd": 1.15,
    },
    "Business travel — rail": {
        "data_needed": "Passenger-km from booking confirmations",
        "recommended_method": "distance-based pax-km (Level 2)",
        "projected_gsd": 1.10,
    },
    "Business travel — air": {
        "data_needed": "Passenger-km and cabin class from bookings",
        "recommended_method": "distance-based pax-km (Level 2)",
        "projected_gsd": 1.10,
    },
    "Purchased services — water supply": {
        "data_needed": "m3 from water bills",
        "recommended_method": "activity-based m3 (Level 2)",
        "projected_gsd": 1.05,
    },
}


def _projected_gsd_one_level_better(current_gsd: float) -> float:
    ln_gsd = math.log(current_gsd)
    return math.exp(ln_gsd * 0.8)


def generate_recommendations(transactions: list) -> list[dict]:
    valid = [t for t in transactions if t.co2e_kg is not None and not t.is_duplicate]
    recs = []

    # 1. Chart-of-accounts
    vague = detect_vague_codes(transactions)
    for v in vague:
        if len(v["classified_as"]) >= 2:
            group_txns = [t for t in valid if (t.raw_category or "").strip() == v["raw_category"]]
            gsd_vals = [t.gsd_total for t in group_txns if t.gsd_total]
            avg_gsd = sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5
            projected = _projected_gsd_one_level_better(avg_gsd)
            impact = v["spend_gbp"] * (avg_gsd - projected)
            reduction_pct = round((1 - projected / avg_gsd) * 100, 1)
            recs.append({
                "type": "chart_of_accounts",
                "impact_score": round(impact, 1),
                "current_code": v["raw_category"],
                "suggested_splits": v["classified_as"],
                "spend_gbp": v["spend_gbp"],
                "current_avg_gsd": round(avg_gsd, 2),
                "projected_avg_gsd": round(projected, 2),
                "uncertainty_reduction_pct": reduction_pct,
                "explanation": (
                    f"{v['transaction_count']} transactions under this code were classified into "
                    f"{len(v['classified_as'])} distinct categories. Splitting the nominal code "
                    f"would allow more specific emission factors."
                ),
            })

    # 2. Activity data
    category_groups: dict[str, list] = {}
    for t in valid:
        if t.category_name and (t.ef_level or 0) >= 4:
            category_groups.setdefault(t.category_name, []).append(t)

    for cat_name, txns in category_groups.items():
        if cat_name in ACTIVITY_DATA_CATEGORIES:
            info = ACTIVITY_DATA_CATEGORIES[cat_name]
            spend = sum(abs(t.amount_gbp or 0) for t in txns)
            gsd_vals = [t.gsd_total for t in txns if t.gsd_total]
            avg_gsd = sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5
            impact = spend * (avg_gsd - info["projected_gsd"])
            recs.append({
                "type": "activity_data",
                "impact_score": round(impact, 1),
                "category": cat_name,
                "current_method": f"spend-based (Level {txns[0].ef_level})",
                "recommended_method": info["recommended_method"],
                "spend_gbp": spend,
                "current_gsd": round(avg_gsd, 2),
                "projected_gsd": info["projected_gsd"],
                "data_needed": info["data_needed"],
                "explanation": (
                    f"{cat_name} spend is currently estimated from GBP. Providing "
                    f"{info['data_needed'].split(' from ')[0].lower()} would move this "
                    f"from Level {txns[0].ef_level} to Level 2."
                ),
            })

    # 3. Supplier engagement
    supplier_groups: dict[str, list] = {}
    for t in valid:
        if t.raw_supplier and (t.ef_level or 0) >= 4:
            supplier_groups.setdefault(t.raw_supplier.strip(), []).append(t)

    for supplier_name, txns in supplier_groups.items():
        spend = sum(abs(t.amount_gbp or 0) for t in txns)
        if spend < 2000:
            continue
        gsd_vals = [t.gsd_total for t in txns if t.gsd_total]
        avg_gsd = sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5
        projected = 1.05
        impact = spend * (avg_gsd - projected)
        recs.append({
            "type": "supplier_engagement",
            "impact_score": round(impact, 1),
            "supplier_name": supplier_name,
            "supplier_id": txns[0].supplier_id,
            "spend_gbp": spend,
            "current_ef_level": txns[0].ef_level,
            "projected_ef_level": 1,
            "explanation": (
                f"{supplier_name} is a significant supplier by spend. Requesting their emission "
                f"intensity data would reduce uncertainty from GSD {round(avg_gsd, 2)} to ~1.05."
            ),
        })

    recs.sort(key=lambda r: r["impact_score"], reverse=True)
    for i, r in enumerate(recs, 1):
        r["rank"] = i
    return recs

