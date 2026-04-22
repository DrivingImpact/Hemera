"""CSV upload endpoint — parse only. No AI token usage.

Processing (classification + emission calculation) is triggered separately
by an admin via POST /engagements/{id}/process.
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends
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
    data_type: str = Form("spend"),
    activity_type: str | None = Form(None),
    raw_activity_label: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Upload an accounting CSV/Excel file — parse only, no AI calls.

    Creates an engagement with status 'uploaded' and saves raw transactions.
    An admin must trigger /engagements/{id}/process to run classification
    and emission calculation.

    Form fields:
        file: CSV or Excel file
        data_type: "spend" (default, traditional accounting) or "activity"
        activity_type: when data_type="activity", one of electricity, natural_gas,
            diesel, petrol, lpg, heating_oil, heat, water, waste, distance,
            refrigerants, or other. Can be omitted if the column headers make the
            type obvious (e.g. a column literally named "kWh").
        raw_activity_label: freeform text when the user picks "other" or types
            their own activity description.
    """
    contents = await file.read()
    filename = file.filename or "upload.csv"

    # 1. Create engagement
    engagement = Engagement(
        org_name=current_user.org_name,
        upload_filename=filename,
        status="uploaded",
        uploaded_by_email=current_user.email,
    )
    db.add(engagement)
    db.flush()

    # 2. Parse the file (spend or activity mode)
    transactions, parse_summary = parse_accounting_csv(
        contents,
        filename,
        engagement.id,
        data_type=data_type,
        activity_type=activity_type,
        raw_activity_label=raw_activity_label,
    )

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
            "data_type": parse_summary["data_type"],
            "activity_type": parse_summary["activity_type"],
            "detected_unit": parse_summary["detected_unit"],
            "total_quantity": parse_summary["total_quantity"],
        },
    }
