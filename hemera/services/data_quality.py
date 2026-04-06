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
