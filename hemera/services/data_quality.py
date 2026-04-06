"""Data Quality Improvement Report engine.

Analyses engagement transactions to identify uncertainty sources and
generate ranked recommendations for improving carbon footprint accuracy.
Pure functions — no DB writes, no side effects.
"""

import math
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
