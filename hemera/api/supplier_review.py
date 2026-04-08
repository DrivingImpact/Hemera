"""Supplier claims review — verify claims we make about suppliers in the report."""

import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.models.supplier import Supplier, SupplierScore, SupplierSource
from hemera.dependencies import require_admin
from hemera.services.clerk import ClerkUser

router = APIRouter()

Z = 1.96
P = 0.5
E = 0.10  # 10% acceptable error for supplier claims


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
    """Generate a sample of supplier claims for verification."""
    eng = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if eng.status not in ("delivered", "qc_passed"):
        raise HTTPException(status_code=400, detail="Engagement must be delivered first")

    # Get unique suppliers in this engagement with their spend/impact
    supplier_agg = (
        db.query(
            Transaction.supplier_id,
            Transaction.raw_supplier,
            Transaction.supplier_match_method,
            func.count().label("txn_count"),
            func.sum(func.abs(Transaction.amount_gbp)).label("total_spend"),
            func.sum(Transaction.co2e_kg).label("total_co2e_kg"),
        )
        .filter(
            Transaction.engagement_id == engagement_id,
            Transaction.is_duplicate == False,
            Transaction.supplier_id != None,
        )
        .group_by(Transaction.supplier_id, Transaction.raw_supplier, Transaction.supplier_match_method)
        .all()
    )

    if not supplier_agg:
        raise HTTPException(status_code=404, detail="No matched suppliers found")

    # Load full supplier data with scores and sources
    supplier_ids = list(set(row.supplier_id for row in supplier_agg))
    suppliers = {s.id: s for s in db.query(Supplier).filter(Supplier.id.in_(supplier_ids)).all()}

    # Load latest score per supplier
    scores = {}
    for score in (
        db.query(SupplierScore)
        .filter(SupplierScore.supplier_id.in_(supplier_ids))
        .order_by(SupplierScore.scored_at.desc())
        .all()
    ):
        if score.supplier_id not in scores:
            scores[score.supplier_id] = score

    # Load sources per supplier
    sources_by_supplier = {}
    for src in db.query(SupplierSource).filter(SupplierSource.supplier_id.in_(supplier_ids)).all():
        sources_by_supplier.setdefault(src.supplier_id, []).append(src)

    # Build claim cards — one per unique supplier
    seen_suppliers = set()
    claim_cards = []
    for row in supplier_agg:
        if row.supplier_id in seen_suppliers:
            continue
        seen_suppliers.add(row.supplier_id)

        s = suppliers.get(row.supplier_id)
        if not s:
            continue

        score = scores.get(s.id)
        srcs = sources_by_supplier.get(s.id, [])

        # Build the claims list — these are statements we'd make in the report
        claims = []

        # Company identity claims
        if s.sector:
            claims.append({"category": "Identity", "claim": f"Classified as {s.sector} sector", "source": "SIC codes / Companies House", "verifiable": True})
        if s.entity_type:
            claims.append({"category": "Identity", "claim": f"Entity type: {s.entity_type}", "source": "Companies House", "verifiable": True})
        if s.status and s.status != "active":
            claims.append({"category": "Identity", "claim": f"Company status: {s.status}", "source": "Companies House", "verifiable": True, "flag": True})

        # ESG score claims
        if score:
            claims.append({"category": "ESG", "claim": f"Overall ESG score: {score.total_score:.0f}/100 ({s.confidence or 'unknown'} confidence)", "source": f"{score.layers_completed} data layers", "verifiable": True})
            if score.critical_flag:
                claims.append({"category": "ESG", "claim": "Flagged as critical risk supplier", "source": "ESG scoring model", "verifiable": True, "flag": True})

            # Domain scores
            domains = {
                "Governance & Identity": score.governance_identity,
                "Labour & Ethics": score.labour_ethics,
                "Carbon & Climate": score.carbon_climate,
                "Water & Biodiversity": score.water_biodiversity,
                "Product & Supply Chain": score.product_supply_chain,
                "Transparency & Disclosure": score.transparency_disclosure,
                "Anti-Corruption": score.anti_corruption,
                "Social Value": score.social_value,
            }
            for domain, val in domains.items():
                if val is not None and val < 30:
                    claims.append({"category": "ESG", "claim": f"Low score in {domain}: {val:.0f}/100", "source": "ESG scoring model", "verifiable": True, "flag": True})

        # Source-based claims
        for src in srcs:
            if src.summary:
                claims.append({
                    "category": "Evidence",
                    "claim": src.summary,
                    "source": f"Layer {src.layer}: {src.source_name}" + (" (verified)" if src.is_verified else " (unverified)"),
                    "verifiable": src.is_verified,
                })

        # If no claims, add a note
        if not claims:
            claims.append({"category": "Info", "claim": "No specific claims — basic supplier record only", "source": "System", "verifiable": False})

        claim_cards.append({
            "supplier_id": s.id,
            "name": s.name,
            "legal_name": s.legal_name,
            "ch_number": s.ch_number,
            "sector": s.sector,
            "entity_type": s.entity_type,
            "status": s.status,
            "sic_codes": s.sic_codes or [],
            "esg_score": s.esg_score,
            "confidence": s.confidence,
            "critical_flag": s.critical_flag,
            "raw_supplier": row.raw_supplier,
            "match_method": row.supplier_match_method,
            "txn_count": row.txn_count,
            "total_spend": round(float(row.total_spend or 0), 2),
            "total_co2e_kg": round(float(row.total_co2e_kg or 0), 2),
            "claims": claims,
        })

    # Sort by spend descending
    claim_cards.sort(key=lambda x: x["total_spend"], reverse=True)

    # Sample with weighting
    population = len(claim_cards)
    n = _sample_size(population)
    rng = random.Random(engagement_id * 3000)

    weighted = []
    for i, card in enumerate(claim_cards):
        w = 1.0
        if card["critical_flag"]:
            w *= 4.0
        if card["confidence"] == "low":
            w *= 3.0
        elif card["confidence"] == "medium":
            w *= 1.5
        if card["match_method"] == "fuzzy":
            w *= 2.0
        if i < max(1, len(claim_cards) // 10):
            w *= 2.0  # top 10% by spend
        flagged_claims = sum(1 for c in card["claims"] if c.get("flag"))
        w *= (1 + flagged_claims)
        weighted.append((i, w))

    selected = set()
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
                selected.add(idx)
                remaining.pop(j)
                break

    sampled = [claim_cards[i] for i in sorted(selected)]

    # Add card numbers and sampling reasons
    for i, card in enumerate(sampled, 1):
        card["card_number"] = i
        card["total_cards"] = len(sampled)
        reasons = []
        if card["critical_flag"]:
            reasons.append("Critical risk flag")
        if card["confidence"] == "low":
            reasons.append("Low confidence score")
        if card["match_method"] == "fuzzy":
            reasons.append("Fuzzy name match")
        flagged = sum(1 for c in card["claims"] if c.get("flag"))
        if flagged > 0:
            reasons.append(f"{flagged} flagged claim{'s' if flagged > 1 else ''}")
        if card["total_spend"] >= (claim_cards[max(1, len(claim_cards) // 10) - 1]["total_spend"] if len(claim_cards) > 1 else 0):
            reasons.append("High-spend supplier")
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
            "critical_flagged": sum(1 for c in claim_cards if c["critical_flag"]),
            "low_confidence": sum(1 for c in claim_cards if c["confidence"] == "low"),
            "fuzzy_matched": sum(1 for c in claim_cards if c["match_method"] == "fuzzy"),
        },
    }
