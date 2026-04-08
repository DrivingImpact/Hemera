"""QC Sampling engine — ISO 19011 stratified random sampling."""
import math
import random
import json

Z = 1.96
P = 0.5
E = 0.05
HARD_GATE_THRESHOLD = 0.05


def calculate_sample_size(population: int) -> int:
    if population <= 0:
        return 0
    numerator = population * (Z ** 2) * P * (1 - P)
    denominator = (E ** 2) * (population - 1) + (Z ** 2) * P * (1 - P)
    n = round(numerator / denominator)
    return min(n, population)


def compute_sampling_weight(transaction, top_10_threshold: float) -> dict:
    weights = {"base": 1.0, "high_value": 1.0, "low_confidence": 1.0, "high_uncertainty_ef": 1.0}
    if abs(transaction.amount_gbp or 0) >= top_10_threshold:
        weights["high_value"] = 2.0
    if transaction.classification_method in ("none", "llm"):
        weights["low_confidence"] = 2.0
    if (transaction.ef_level or 0) >= 5:
        weights["high_uncertainty_ef"] = 2.0
    weights["total"] = weights["base"] * weights["high_value"] * weights["low_confidence"] * weights["high_uncertainty_ef"]
    return weights


def get_sampling_reasons(transaction, top_10_threshold: float) -> list[str]:
    reasons = []
    if abs(transaction.amount_gbp or 0) >= top_10_threshold:
        reasons.append("High-spend transaction (top 10% by value)")
    if transaction.classification_method == "none":
        reasons.append("Low-confidence classification (method: none)")
    elif transaction.classification_method == "llm":
        reasons.append("LLM-classified transaction")
    if (transaction.ef_level or 0) >= 5:
        reasons.append("High-uncertainty emission factor (Level 5-6)")
    if not reasons:
        reasons.append("Routine sample (proportional representation)")
    return reasons


def _compute_top_10_threshold(transactions: list) -> float:
    amounts = sorted([abs(t.amount_gbp or 0) for t in transactions], reverse=True)
    if not amounts:
        return 0.0
    index = max(0, len(amounts) // 10 - 1)
    return amounts[index]


def build_qc_card(transaction, card_number: int, total_cards: int, top_10_threshold: float) -> dict:
    t = transaction
    expected_co2e = abs(t.amount_gbp or 0) * (t.ef_value or 0)
    arithmetic_ok = abs(expected_co2e - (t.co2e_kg or 0)) < 0.01
    return {
        "card_number": card_number,
        "total_cards": total_cards,
        "remaining": total_cards - card_number + 1,
        "transaction_id": t.id,
        "qc_pass": t.qc_pass,  # None = not reviewed, True = pass, False = fail
        "sampling_reasons": get_sampling_reasons(t, top_10_threshold),
        "raw_data": {
            "row_number": t.row_number,
            "raw_date": t.raw_date,
            "raw_description": t.raw_description,
            "raw_supplier": t.raw_supplier,
            "raw_amount": t.raw_amount,
            "raw_category": t.raw_category,
        },
        "decisions": {
            "classification": {
                "scope": t.scope,
                "ghg_category": t.ghg_category,
                "category_name": t.category_name,
                "method": t.classification_method,
                "confidence": t.classification_confidence,
            },
            "supplier_match": {
                "supplier_id": t.supplier_id,
                "match_method": t.supplier_match_method,
            },
            "emission_factor": {
                "value": t.ef_value,
                "unit": t.ef_unit,
                "source": t.ef_source,
                "level": t.ef_level,
                "year": t.ef_year,
                "region": t.ef_region,
            },
            "calculation": {
                "amount_gbp": abs(t.amount_gbp or 0),
                "ef_value": t.ef_value,
                "co2e_kg": t.co2e_kg,
                "arithmetic_verified": arithmetic_ok,
            },
            "pedigree": {
                "reliability": t.pedigree_reliability,
                "completeness": t.pedigree_completeness,
                "temporal": t.pedigree_temporal,
                "geographical": t.pedigree_geographical,
                "technological": t.pedigree_technological,
                "gsd_total": t.gsd_total,
            },
        },
        "checks": ["classification", "emission_factor", "arithmetic", "supplier_match", "pedigree"],
    }


def build_qc_cards(transactions: list, top_10_threshold: float) -> list[dict]:
    total = len(transactions)
    return [
        build_qc_card(t, card_number=i, total_cards=total, top_10_threshold=top_10_threshold)
        for i, t in enumerate(transactions, 1)
    ]


def apply_qc_result(transaction, result: dict) -> None:
    all_pass = all([
        result.get("classification_pass", False),
        result.get("emission_factor_pass", False),
        result.get("arithmetic_pass", False),
        result.get("supplier_match_pass", False),
        result.get("pedigree_pass", False),
    ])
    transaction.qc_pass = all_pass
    transaction.qc_notes = json.dumps({
        "classification_pass": result.get("classification_pass"),
        "emission_factor_pass": result.get("emission_factor_pass"),
        "arithmetic_pass": result.get("arithmetic_pass"),
        "supplier_match_pass": result.get("supplier_match_pass"),
        "pedigree_pass": result.get("pedigree_pass"),
        "notes": result.get("notes", ""),
    })


def compute_qc_status(transactions: list) -> dict:
    sampled = [t for t in transactions if t.is_sampled]
    if not sampled:
        return {
            "status": "not_started", "sample_size": 0, "reviewed_count": 0,
            "remaining_count": 0, "pass_count": 0, "fail_count": 0,
            "current_error_rate": 0.0, "hard_gate_threshold": HARD_GATE_THRESHOLD,
            "would_pass_now": False,
        }
    reviewed = [t for t in sampled if t.qc_pass is not None]
    passed = [t for t in reviewed if t.qc_pass is True]
    failed = [t for t in reviewed if t.qc_pass is False]
    sample_size = len(sampled)
    reviewed_count = len(reviewed)
    remaining = sample_size - reviewed_count
    error_rate = len(failed) / sample_size if sample_size > 0 else 0.0

    if reviewed_count < sample_size:
        return {
            "status": "in_progress", "sample_size": sample_size,
            "reviewed_count": reviewed_count, "remaining_count": remaining,
            "pass_count": len(passed), "fail_count": len(failed),
            "current_error_rate": round(error_rate, 4),
            "hard_gate_threshold": HARD_GATE_THRESHOLD,
            "would_pass_now": error_rate <= HARD_GATE_THRESHOLD,
        }
    else:
        gate_passed = error_rate <= HARD_GATE_THRESHOLD
        return {
            "status": "passed" if gate_passed else "failed",
            "sample_size": sample_size, "reviewed_count": reviewed_count,
            "remaining_count": 0, "pass_count": len(passed), "fail_count": len(failed),
            "current_error_rate": round(error_rate, 4),
            "hard_gate_threshold": HARD_GATE_THRESHOLD,
            "hard_gate_result": "passed" if gate_passed else "failed",
        }


def select_sample(transactions: list, engagement_id: int, attempt: int = 1) -> list:
    valid = [t for t in transactions if t.co2e_kg is not None and not t.is_duplicate]
    if not valid:
        return []
    n = calculate_sample_size(len(valid))
    if n >= len(valid):
        return list(valid)
    top_10_threshold = _compute_top_10_threshold(valid)
    weighted = []
    for t in valid:
        w = compute_sampling_weight(t, top_10_threshold)
        weighted.append((t, w["total"]))
    rng = random.Random(engagement_id * 1000 + attempt)
    selected = []
    remaining = list(weighted)
    for _ in range(n):
        if not remaining:
            break
        total_weight = sum(w for _, w in remaining)
        pick = rng.uniform(0, total_weight)
        cumulative = 0.0
        for i, (t, w) in enumerate(remaining):
            cumulative += w
            if cumulative >= pick:
                selected.append(t)
                remaining.pop(i)
                break
    return selected
