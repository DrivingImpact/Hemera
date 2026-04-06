"""Report generation endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.services.data_quality import generate_data_quality_report
from hemera.services.pdf_report import generate_report_data, render_report_html, generate_pdf
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


@router.get("/reports/{engagement_id}/pdf")
def get_pdf_report(engagement_id: int, db: Session = Depends(get_db), current_user: ClerkUser = Depends(get_current_user)):
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if current_user.role != "admin" and engagement.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")
    if engagement.status != "delivered":
        raise HTTPException(status_code=400, detail="Report not yet delivered")

    transactions = db.query(Transaction).filter(Transaction.engagement_id == engagement_id).all()
    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found")

    data = generate_report_data(engagement, transactions)
    html = render_report_html(data)
    pdf_bytes = generate_pdf(html)

    filename = f"hemera-carbon-report-{engagement.org_name.replace(' ', '-').lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
