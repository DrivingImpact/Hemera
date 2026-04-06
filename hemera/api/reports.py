"""Report generation endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.services.data_quality import generate_data_quality_report
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser

router = APIRouter()


@router.get("/reports/{engagement_id}/data-quality")
def get_data_quality_report(engagement_id: int, db: Session = Depends(get_db), current_user: ClerkUser = Depends(get_current_user)):
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if current_user.role != "admin" and engagement.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")
    transactions = db.query(Transaction).filter(Transaction.engagement_id == engagement_id).all()
    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found for engagement")
    return generate_data_quality_report(transactions, engagement_id)
