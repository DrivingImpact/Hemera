"""Supplier findings and engagement management endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.finding import SupplierFinding
from hemera.models.supplier_engagement import SupplierEngagement
from hemera.models.supplier import Supplier
from hemera.models.user import User
from hemera.dependencies import require_admin
from hemera.services.clerk import ClerkUser

router = APIRouter()


class CreateFindingRequest(BaseModel):
    source: str  # ai_manual, analyst
    domain: str
    severity: str
    title: str
    detail: str
    source_name: str
    evidence_url: str | None = None
    evidence_data: dict | None = None
    layer: int | None = None
    ai_task_id: int | None = None


class CreateEngagementRequest(BaseModel):
    engagement_type: str
    subject: str
    status: str
    notes: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    next_action: str | None = None
    next_action_date: str | None = None


class UpdateEngagementRequest(BaseModel):
    status: str | None = None
    notes: str | None = None
    next_action: str | None = None
    next_action_date: str | None = None


@router.get("/suppliers/{supplier_id}/findings")
def get_findings(
    supplier_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    query = db.query(SupplierFinding).filter(SupplierFinding.supplier_id == supplier_id)
    if active_only:
        query = query.filter(SupplierFinding.is_active == True)  # noqa: E712
    findings = query.order_by(SupplierFinding.severity, SupplierFinding.created_at.desc()).all()
    return [_finding_to_dict(f) for f in findings]


@router.post("/suppliers/{supplier_id}/findings", status_code=201)
def create_finding(
    supplier_id: int,
    req: CreateFindingRequest,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    finding = SupplierFinding(
        supplier_id=supplier_id,
        source=req.source,
        domain=req.domain,
        severity=req.severity,
        title=req.title,
        detail=req.detail,
        source_name=req.source_name,
        evidence_url=req.evidence_url,
        evidence_data=req.evidence_data,
        layer=req.layer,
        ai_task_id=req.ai_task_id,
        is_active=True,
    )
    db.add(finding)
    db.commit()
    return _finding_to_dict(finding)


@router.post("/suppliers/{supplier_id}/re-analyse")
def re_analyse(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Supersede existing findings and regenerate from current source data."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Mark existing deterministic findings as superseded
    now = datetime.utcnow()
    db.query(SupplierFinding).filter(
        SupplierFinding.supplier_id == supplier_id,
        SupplierFinding.source == "deterministic",
        SupplierFinding.is_active == True,  # noqa: E712
    ).update({"is_active": False, "superseded_at": now})

    # Regenerate from current scores
    from hemera.services.finding_generator import generate_findings_from_sources
    from hemera.models.supplier import SupplierSource

    sources = db.query(SupplierSource).filter(SupplierSource.supplier_id == supplier_id).all()
    if sources:
        finding_dicts = generate_findings_from_sources(sources, supplier_name=supplier.name)

        for fd in finding_dicts:
            finding = SupplierFinding(supplier_id=supplier_id, is_active=True, **fd)
            db.add(finding)

    db.commit()
    return {"status": "ok", "supplier_id": supplier_id}


@router.get("/suppliers/{supplier_id}/engagements")
def get_engagements(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    engs = (
        db.query(SupplierEngagement)
        .filter(SupplierEngagement.supplier_id == supplier_id)
        .order_by(SupplierEngagement.created_at.desc())
        .all()
    )
    return [_engagement_to_dict(e) for e in engs]


@router.post("/suppliers/{supplier_id}/engagements", status_code=201)
def create_engagement(
    supplier_id: int,
    req: CreateEngagementRequest,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    user = db.query(User).filter(User.clerk_id == current_user.clerk_id).first()
    user_id = user.id if user else 0

    eng = SupplierEngagement(
        supplier_id=supplier_id,
        engagement_type=req.engagement_type,
        subject=req.subject,
        status=req.status,
        notes=req.notes,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        next_action=req.next_action,
        contacted_at=datetime.utcnow() if req.status in ("contacted", "in_progress") else None,
        created_by=user_id,
    )
    db.add(eng)
    db.commit()
    return _engagement_to_dict(eng)


@router.patch("/suppliers/{supplier_id}/engagements/{engagement_id}")
def update_engagement(
    supplier_id: int,
    engagement_id: int,
    req: UpdateEngagementRequest,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    eng = db.query(SupplierEngagement).filter(
        SupplierEngagement.id == engagement_id,
        SupplierEngagement.supplier_id == supplier_id,
    ).first()
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if req.status is not None:
        eng.status = req.status
        if req.status in ("in_progress", "completed") and eng.responded_at is None:
            eng.responded_at = datetime.utcnow()
    if req.notes is not None:
        eng.notes = req.notes
    if req.next_action is not None:
        eng.next_action = req.next_action

    db.commit()
    return _engagement_to_dict(eng)


def _finding_to_dict(f: SupplierFinding) -> dict:
    return {
        "id": f.id,
        "supplier_id": f.supplier_id,
        "source": f.source,
        "domain": f.domain,
        "severity": f.severity,
        "title": f.title,
        "detail": f.detail,
        "evidence_url": f.evidence_url,
        "layer": f.layer,
        "source_name": f.source_name,
        "is_active": f.is_active,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _engagement_to_dict(e: SupplierEngagement) -> dict:
    return {
        "id": e.id,
        "supplier_id": e.supplier_id,
        "engagement_type": e.engagement_type,
        "subject": e.subject,
        "status": e.status,
        "notes": e.notes,
        "contact_name": e.contact_name,
        "contacted_at": e.contacted_at.isoformat() if e.contacted_at else None,
        "responded_at": e.responded_at.isoformat() if e.responded_at else None,
        "next_action": e.next_action,
        "next_action_date": str(e.next_action_date) if e.next_action_date else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
