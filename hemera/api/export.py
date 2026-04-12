"""Excel/Power BI export endpoints.

Produces a multi-sheet xlsx file per engagement. Same format serves both
human reviewers and Power BI — Power Query can pick up any sheet by name.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from hemera.database import get_db
from hemera.dependencies import get_current_user
from hemera.models.engagement import Engagement
from hemera.services.clerk import ClerkUser
from hemera.services.excel_export import build_engagement_workbook

router = APIRouter()


XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.get("/engagements/{engagement_id}/export/xlsx")
def export_engagement_xlsx(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Download a multi-sheet Excel summary of an engagement.

    The sheet layout is flat and typed so Power BI can ingest it via
    Get Data → Excel Workbook without any Power Query cleanup. Power BI
    users can pick any of the "By X" sheets depending on the visual they
    want to build.
    """
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if engagement is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    xlsx_bytes = build_engagement_workbook(engagement, db)
    slug = (engagement.org_name or f"engagement-{engagement_id}").replace(" ", "-").lower()
    filename = f"hemera-{slug}-{engagement_id}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # Helpful for Power BI users: indicates the file is intended for
            # direct import, not a preview.
            "X-Hemera-Export-Kind": "engagement-summary",
        },
    )
