"""CSV upload endpoint — parse only. No AI token usage.

Processing (classification + emission calculation) is triggered separately
by an admin via POST /engagements/{id}/process.
"""

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.services.csv_parser import parse_accounting_csv
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser

router = APIRouter()


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Upload an accounting CSV/Excel file — parse only, no AI calls.

    Creates an engagement with status 'uploaded' and saves raw transactions.
    An admin must trigger /engagements/{id}/process to run classification
    and emission calculation.
    """
    contents = await file.read()
    filename = file.filename or "upload.csv"

    # 1. Create engagement
    engagement = Engagement(
        org_name=current_user.org_name,
        upload_filename=filename,
        status="uploaded",
    )
    db.add(engagement)
    db.flush()

    # 2. Parse the file
    transactions, parse_summary = parse_accounting_csv(contents, filename, engagement.id)

    # 3. Save raw transactions
    db.add_all(transactions)

    # 4. Update engagement counts
    engagement.transaction_count = len(transactions)
    engagement.supplier_count = parse_summary["unique_suppliers"]

    db.commit()

    return {
        "engagement_id": engagement.id,
        "filename": filename,
        "status": "uploaded",
        "parsing": {
            "transactions_parsed": len(transactions),
            "duplicates_removed": parse_summary["duplicates_removed"],
            "date_range": parse_summary["date_range"],
            "total_spend_gbp": round(parse_summary["total_spend"], 2),
            "unique_suppliers": parse_summary["unique_suppliers"],
        },
    }
