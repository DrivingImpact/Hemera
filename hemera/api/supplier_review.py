"""Supplier claims review — verify supplier matches and risk assessments."""

import math
import random
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.models.supplier import Supplier
from hemera.dependencies import require_admin
from hemera.services.clerk import ClerkUser

router = APIRouter()

Z = 1.96
P = 0.5
E = 0.10  # 10% acceptable error for supplier review (less strict than carbon)


def _sample_size(population: int) -> int:
    if population <= 0:
        return 0
    n = (population * Z**2 * P * (1 - P)) / (E**2 * (population - 1) + Z**2 * P * (1 - P))
    return min(round(n), population)


@router.post("/engagements/{engagement_id}/supplier-review/generate")
def generate_supplier_review(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Generate a sample of supplier claims for review."""
    eng = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng.status not in ("delivered", "qc_passed"):
        raise HTTPException(status_code=400, detail="Engagement must be delivered first")

    # Group transactions by raw_supplier to get unique supplier claims
    claims = (
        db.query(
            Transaction.raw_supplier,
            Transaction.supplier_id,
            Transaction.supplier_match_method,
            func.count().label("txn_count"),
            func.sum(func.abs(Transaction.amount_gbp)).label("total_spend"),
            func.sum(Transaction.co2e_kg).label("total_co2e_kg"),
        )
        .filter(
            Transaction.engagement_id == engagement_id,
            Transaction.is_duplicate == False,
            Transaction.raw_supplier != None,
            Transaction.raw_supplier != "",
        )
        .group_by(
            Transaction.raw_supplier,
            Transaction.supplier_id,
            Transaction.supplier_match_method,
        )
        .all()
    )

    if not claims:
        raise HTTPException(status_code=404, detail="No supplier claims found")

    # Build full claim objects with supplier details
    supplier_ids = [c.supplier_id for c in claims if c.supplier_id]
    suppliers = {}
    if supplier_ids:
        for s in db.query(Supplier).filter(Supplier.id.in_(supplier_ids)).all():
            suppliers[s.id] = s

    claim_cards = []
    for c in claims:
        supplier = suppliers.get(c.supplier_id) if c.supplier_id else None
        claim_cards.append({
            "raw_supplier": c.raw_supplier,
            "supplier_id": c.supplier_id,
            "match_method": c.supplier_match_method or "none",
            "matched_name": supplier.name if supplier else None,
            "matched_sector": supplier.sector if supplier else None,
            "sic_codes": supplier.sic_codes if supplier else [],
            "esg_score": supplier.esg_score if supplier else None,
            "ch_number": supplier.ch_number if supplier else None,
            "txn_count": c.txn_count,
            "total_spend": round(float(c.total_spend or 0), 2),
            "total_co2e_kg": round(float(c.total_co2e_kg or 0), 2),
        })

    # Weight by spend — high-spend suppliers should be reviewed first
    claim_cards.sort(key=lambda x: x["total_spend"], reverse=True)

    # Sample
    population = len(claim_cards)
    n = _sample_size(population)

    # Weighted selection — prioritise fuzzy matches and high-spend
    rng = random.Random(engagement_id * 2000)
    weighted = []
    for i, card in enumerate(claim_cards):
        w = 1.0
        if card["match_method"] == "fuzzy":
            w *= 3.0  # fuzzy matches most likely to be wrong
        if card["match_method"] == "none" or not card["supplier_id"]:
            w *= 2.0  # unmatched suppliers need attention
        if i < len(claim_cards) // 10:
            w *= 2.0  # top 10% by spend
        weighted.append((i, w))

    selected_indices = set()
    remaining = list(weighted)
    for _ in range(n):
        if not remaining:
            break
        total_w = sum(w for _, w in remaining)
        pick = rng.uniform(0, total_w)
        cumulative = 0.0
        for j, (idx, w) in enumerate(remaining):
            cumulative += w
            if cumulative >= pick:
                selected_indices.add(idx)
                remaining.pop(j)
                break

    sampled = [claim_cards[i] for i in sorted(selected_indices)]

    # Add card numbers and sampling reasons
    for i, card in enumerate(sampled, 1):
        card["card_number"] = i
        card["total_cards"] = len(sampled)
        reasons = []
        if card["match_method"] == "fuzzy":
            reasons.append("Fuzzy match — verify correct supplier")
        if card["match_method"] == "none" or not card["supplier_id"]:
            reasons.append("No supplier match found")
        if card["total_spend"] >= (claim_cards[len(claim_cards) // 10]["total_spend"] if len(claim_cards) > 10 else 0):
            reasons.append("High-spend supplier (top 10%)")
        if not reasons:
            reasons.append("Routine sample")
        card["sampling_reasons"] = reasons

    return {
        "engagement_id": engagement_id,
        "population_size": population,
        "sample_size": len(sampled),
        "confidence_level": 0.95,
        "acceptable_error_rate": E,
        "cards": sampled,
        "summary": {
            "total_suppliers": population,
            "matched_exact": sum(1 for c in claim_cards if c["match_method"] == "exact"),
            "matched_fuzzy": sum(1 for c in claim_cards if c["match_method"] == "fuzzy"),
            "unmatched": sum(1 for c in claim_cards if not c["supplier_id"]),
        },
    }
