"""Engagement endpoints — CRUD for client reports."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.dependencies import get_current_user, require_admin
from hemera.services.clerk import ClerkUser
from hemera.services.engagement_data import (
    build_category_summary, build_monthly_summary, build_engagement_suppliers,
)
from hemera.services.reduction_recs import generate_reduction_recommendations, compute_projections
from hemera.services.data_quality import generate_recommendations
from hemera.services.pipeline import run_processing_pipeline

router = APIRouter()


def _load_engagement(engagement_id: int, db, current_user):
    """Load engagement with auth check. Raises HTTPException on failure."""
    e = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role != "admin" and e.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")
    return e


def _load_transactions(engagement_id: int, db):
    return db.query(Transaction).filter(Transaction.engagement_id == engagement_id).all()


@router.get("/engagements")
def list_engagements(db: Session = Depends(get_db), current_user: ClerkUser = Depends(get_current_user)):
    query = db.query(Engagement)
    if current_user.role != "admin":
        query = query.filter(Engagement.org_name == current_user.org_name)
    engagements = query.order_by(Engagement.created_at.desc()).all()
    return [
        {
            "id": e.id,
            "org_name": e.org_name,
            "status": e.status,
            "transaction_count": e.transaction_count,
            "total_co2e": e.total_co2e,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in engagements
    ]


@router.delete("/engagements/{engagement_id}")
def delete_engagement(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Delete an engagement and its transactions. Only allowed for non-approved engagements."""
    e = _load_engagement(engagement_id, db, current_user)
    if e.status == "qc_passed":
        raise HTTPException(status_code=400, detail="Cannot delete an approved engagement")
    db.query(Transaction).filter(Transaction.engagement_id == engagement_id).delete()
    db.delete(e)
    db.commit()
    return {"detail": "Deleted"}


@router.get("/engagements/{engagement_id}/categories")
def get_engagement_categories(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    return build_category_summary(txns)


@router.get("/engagements/{engagement_id}/monthly")
def get_engagement_monthly(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    return build_monthly_summary(txns)


@router.get("/engagements/{engagement_id}/suppliers")
def get_engagement_suppliers(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    return build_engagement_suppliers(txns)


@router.get("/engagements/{engagement_id}/reduction")
def get_engagement_reduction(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    e = _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    recs = generate_reduction_recommendations(txns)
    dq_recs = generate_recommendations(txns)

    total_co2e = e.total_co2e or 0
    ci_lower = e.ci_lower or total_co2e * 0.7
    ci_upper = e.ci_upper or total_co2e * 1.4

    projections = compute_projections(
        total_co2e_kg=total_co2e * 1000,
        ci_lower_kg=ci_lower * 1000,
        ci_upper_kg=ci_upper * 1000,
        reduction_recs=recs,
        data_quality_recs=dq_recs,
    )

    return {
        "recommendations": recs,
        "projections": {
            "baseline": total_co2e,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "year2_ci_lower": projections["year2_ci_lower_kg"] / 1000,
            "year2_ci_upper": projections["year2_ci_upper_kg"] / 1000,
            "year3_target": projections["year3_target_kg"] / 1000,
            "year3_ci_lower": projections["year3_ci_lower_kg"] / 1000,
            "year3_ci_upper": projections["year3_ci_upper_kg"] / 1000,
            "total_reduction": projections["total_reduction_kg"] / 1000,
        },
    }


@router.get("/engagements/{engagement_id}/transactions")
def get_engagement_transactions(
    engagement_id: int,
    scope: int | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    _load_engagement(engagement_id, db, current_user)
    query = db.query(Transaction).filter(
        Transaction.engagement_id == engagement_id,
        Transaction.is_duplicate == False,  # noqa: E712
    )
    if scope:
        query = query.filter(Transaction.scope == scope)
    if category:
        query = query.filter(Transaction.category_name == category)

    total = query.count()
    txns = query.order_by(Transaction.co2e_kg.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "transactions": [
            {
                "id": t.id,
                "date": str(t.transaction_date) if t.transaction_date else None,
                "description": t.raw_description,
                "supplier": t.raw_supplier,
                "amount_gbp": t.amount_gbp,
                "scope": t.scope,
                "category": t.category_name,
                "ef_source": t.ef_source,
                "ef_level": t.ef_level,
                "co2e_kg": t.co2e_kg,
                "gsd": t.gsd_total,
            }
            for t in txns
        ],
    }


@router.post("/engagements/{engagement_id}/process")
def process_engagement(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Admin-only: trigger full classification + calculation pipeline."""
    e = _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    if not txns:
        raise HTTPException(status_code=404, detail="No transactions found")
    try:
        result = run_processing_pipeline(e, txns, db)
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    return result


@router.get("/engagements/{engagement_id}")
def get_engagement(engagement_id: int, db: Session = Depends(get_db), current_user: ClerkUser = Depends(get_current_user)):
    e = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role != "admin" and e.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "id": e.id,
        "org_name": e.org_name,
        "status": e.status,
        "transaction_count": e.transaction_count,
        "supplier_count": e.supplier_count,
        "total_co2e": e.total_co2e,
        "scope1_co2e": e.scope1_co2e,
        "scope2_co2e": e.scope2_co2e,
        "scope3_co2e": e.scope3_co2e,
        "gsd_total": e.gsd_total,
        "ci_lower": e.ci_lower,
        "ci_upper": e.ci_upper,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
