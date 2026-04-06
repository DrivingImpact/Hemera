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
        "reduction_pct": 0.80,
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
        avg_improvement = 0.9

    year2_ci_width = ci_width * avg_improvement
    year2_ci_lower = total_co2e_kg - year2_ci_width / 2
    year2_ci_upper = total_co2e_kg + year2_ci_width / 2

    total_reduction = sum(r.get("potential_reduction_kg", 0) for r in reduction_recs)
    year3_target = total_co2e_kg - total_reduction

    year3_ci_width = year2_ci_width * 0.85
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
