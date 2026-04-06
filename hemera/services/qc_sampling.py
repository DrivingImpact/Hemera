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
