"""Engagement endpoints — CRUD for client reports."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser

router = APIRouter()


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
