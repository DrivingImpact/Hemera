"""Supplier registry endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.supplier import Supplier, SupplierScore, SupplierSource
from hemera.services.enrichment import enrich_supplier, enrich_batch

router = APIRouter()


@router.get("/suppliers")
def list_suppliers(
    q: str = Query(None, description="Search by name"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """List suppliers in the registry, optionally search by name."""
    query = db.query(Supplier)
    if q:
        query = query.filter(Supplier.name.ilike(f"%{q}%"))
    suppliers = query.order_by(Supplier.name).limit(limit).all()
    return [
        {
            "id": s.id,
            "ch_number": s.ch_number,
            "name": s.name,
            "sector": s.sector,
            "esg_score": s.esg_score,
            "confidence": s.confidence,
            "critical_flag": s.critical_flag,
        }
        for s in suppliers
    ]


@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """Get full supplier profile with score history and source data."""
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Get score history
    scores = (
        db.query(SupplierScore)
        .filter(SupplierScore.supplier_id == supplier_id)
        .order_by(SupplierScore.scored_at.desc())
        .limit(10)
        .all()
    )

    # Get source summary
    sources = (
        db.query(SupplierSource)
        .filter(SupplierSource.supplier_id == supplier_id)
        .order_by(SupplierSource.layer)
        .all()
    )

    return {
        "id": s.id,
        "ch_number": s.ch_number,
        "hemera_id": s.hemera_id,
        "name": s.name,
        "legal_name": s.legal_name,
        "status": s.status,
        "sic_codes": s.sic_codes,
        "sector": s.sector,
        "entity_type": s.entity_type,
        "registered_address": s.registered_address,
        "esg_score": s.esg_score,
        "confidence": s.confidence,
        "critical_flag": s.critical_flag,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "score_history": [
            {
                "total_score": sc.total_score,
                "confidence": sc.confidence,
                "critical_flag": sc.critical_flag,
                "layers_completed": sc.layers_completed,
                "domains": {
                    "governance_identity": sc.governance_identity,
                    "labour_ethics": sc.labour_ethics,
                    "carbon_climate": sc.carbon_climate,
                    "water_biodiversity": sc.water_biodiversity,
                    "product_supply_chain": sc.product_supply_chain,
                    "transparency_disclosure": sc.transparency_disclosure,
                    "anti_corruption": sc.anti_corruption,
                    "social_value": sc.social_value,
                },
                "scored_at": sc.scored_at.isoformat() if sc.scored_at else None,
            }
            for sc in scores
        ],
        "sources": [
            {
                "layer": src.layer,
                "source_name": src.source_name,
                "tier": src.tier,
                "summary": src.summary,
                "is_verified": src.is_verified,
                "fetched_at": src.fetched_at.isoformat() if src.fetched_at else None,
            }
            for src in sources
        ],
    }


@router.post("/suppliers/{supplier_id}/enrich")
async def enrich_single_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """Run the enrichment protocol on a single supplier.

    Executes Layers 1-3 (Corporate Identity, Ownership & Sanctions,
    Financial Health) and calculates the ESG score.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    result = await enrich_supplier(supplier, db)
    return result


@router.post("/suppliers/enrich-all")
async def enrich_all_unenriched(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    """Enrich all suppliers that haven't been enriched yet.

    Runs Layers 1-3 on suppliers with no existing source data.
    """
    unenriched = (
        db.query(Supplier)
        .filter(Supplier.status == "unverified")
        .limit(limit)
        .all()
    )

    if not unenriched:
        return {"message": "No unenriched suppliers found", "enriched": 0}

    results = await enrich_batch(unenriched, db)
    return {
        "enriched": len(results),
        "results": results,
    }
