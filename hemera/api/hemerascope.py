"""HemeraScope report curation, preview, publish, and client-facing endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.finding import SupplierFinding, ReportSelection, ReportAction
from hemera.models.supplier import Supplier, SupplierSource
from hemera.models.supplier_engagement import SupplierEngagement
from hemera.models.transaction import Transaction
from hemera.models.user import User
from hemera.dependencies import require_admin, get_current_user
from hemera.services.clerk import ClerkUser

router = APIRouter()


class SelectionItem(BaseModel):
    finding_id: int
    included: bool
    client_title: str | None = None
    client_detail: str | None = None
    client_language_source: str | None = None
    analyst_note: str | None = None


class SaveSelectionsRequest(BaseModel):
    selections: list[SelectionItem]


class SaveActionsRequest(BaseModel):
    supplier_id: int
    actions: list[dict]  # [{action_text, priority, linked_finding_ids, language_source}]


def _load_engagement(engagement_id: int, db: Session) -> Engagement:
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return engagement


@router.get("/engagements/{engagement_id}/supplier-report")
def get_supplier_report(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Get all suppliers, findings, and current selections for curation."""
    engagement = _load_engagement(engagement_id, db)

    # Get all suppliers linked to this engagement via transactions
    supplier_ids = (
        db.query(Transaction.supplier_id)
        .filter(
            Transaction.engagement_id == engagement_id,
            Transaction.supplier_id.isnot(None),
            Transaction.is_duplicate == False,  # noqa: E712
        )
        .distinct()
        .all()
    )
    supplier_ids = [sid for (sid,) in supplier_ids]

    suppliers_data = []
    for sid in supplier_ids:
        supplier = db.query(Supplier).filter(Supplier.id == sid).first()
        if not supplier:
            continue

        findings = (
            db.query(SupplierFinding)
            .filter(SupplierFinding.supplier_id == sid, SupplierFinding.is_active == True)  # noqa: E712
            .order_by(SupplierFinding.severity, SupplierFinding.created_at.desc())
            .all()
        )

        finding_ids = [f.id for f in findings]
        selections = []
        if finding_ids:
            selections = (
                db.query(ReportSelection)
                .filter(
                    ReportSelection.engagement_id == engagement_id,
                    ReportSelection.finding_id.in_(finding_ids),
                )
                .all()
            )
        selections_map = {s.finding_id: s for s in selections}

        actions = (
            db.query(ReportAction)
            .filter(ReportAction.engagement_id == engagement_id, ReportAction.supplier_id == sid)
            .order_by(ReportAction.priority)
            .all()
        )

        hemera_engs = (
            db.query(SupplierEngagement)
            .filter(SupplierEngagement.supplier_id == sid)
            .order_by(SupplierEngagement.created_at.desc())
            .all()
        )

        # Get raw source data so admin can see what fed each finding
        sources = (
            db.query(SupplierSource)
            .filter(SupplierSource.supplier_id == sid)
            .order_by(SupplierSource.layer)
            .all()
        )
        # Build a lookup: layer -> list of source summaries
        sources_by_layer = {}
        for src in sources:
            if src.layer not in sources_by_layer:
                sources_by_layer[src.layer] = []
            sources_by_layer[src.layer].append({
                "source_name": src.source_name,
                "tier": src.tier,
                "summary": src.summary,
                "data": src.data,
                "fetched_at": src.fetched_at.isoformat() if src.fetched_at else None,
                "is_verified": src.is_verified,
            })

        # Aggregate transaction stats
        stats = db.query(
            func.count(Transaction.id),
            func.sum(Transaction.amount_gbp),
            func.sum(Transaction.co2e_kg),
        ).filter(
            Transaction.engagement_id == engagement_id,
            Transaction.supplier_id == sid,
            Transaction.is_duplicate == False,  # noqa: E712
        ).first()

        suppliers_data.append({
            "supplier": {
                "id": supplier.id,
                "name": supplier.name,
                "legal_name": supplier.legal_name,
                "ch_number": supplier.ch_number,
                "sector": supplier.sector,
                "entity_type": supplier.entity_type,
                "hemera_score": supplier.hemera_score,
                "confidence": supplier.confidence,
                "critical_flag": supplier.critical_flag,
                "hemera_verified": supplier.hemera_verified,
            },
            "txn_count": stats[0] if stats else 0,
            "total_spend": round(stats[1] or 0, 2) if stats else 0,
            "total_co2e_kg": round(stats[2] or 0, 2) if stats else 0,
            "findings": [
                {
                    "id": f.id,
                    "source": f.source,
                    "domain": f.domain,
                    "severity": f.severity,
                    "title": f.title,
                    "detail": f.detail,
                    "evidence_url": f.evidence_url,
                    "layer": f.layer,
                    "source_name": f.source_name,
                    "evidence": sources_by_layer.get(f.layer, []) if f.layer else [],
                    "selection": {
                        "included": selections_map[f.id].included,
                        "client_title": selections_map[f.id].client_title,
                        "client_detail": selections_map[f.id].client_detail,
                        "analyst_note": selections_map[f.id].analyst_note,
                    } if f.id in selections_map else None,
                }
                for f in findings
            ],
            "sources": [
                {
                    "layer": src.layer,
                    "source_name": src.source_name,
                    "tier": src.tier,
                    "summary": src.summary,
                    "fetched_at": src.fetched_at.isoformat() if src.fetched_at else None,
                }
                for src in sources
            ],
            "actions": [
                {
                    "id": a.id,
                    "action_text": a.action_text,
                    "priority": a.priority,
                    "linked_finding_ids": a.linked_finding_ids,
                    "language_source": a.language_source,
                }
                for a in actions
            ],
            "hemera_engagements": [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "status": e.status,
                    "engagement_type": e.engagement_type,
                    "contacted_at": e.contacted_at.isoformat() if e.contacted_at else None,
                    "responded_at": e.responded_at.isoformat() if e.responded_at else None,
                    "notes": e.notes,
                }
                for e in hemera_engs
            ],
        })

    # Sort: critical first, then by hemera_score ascending
    suppliers_data.sort(
        key=lambda s: (
            0 if s["supplier"]["critical_flag"] else 1,
            s["supplier"]["hemera_score"] or 999,
        )
    )

    return {
        "engagement_id": engagement_id,
        "client_name": engagement.display_name or engagement.org_name,
        "status": engagement.supplier_report_status or "pending",
        "supplier_count": len(suppliers_data),
        "suppliers": suppliers_data,
    }


LAYER_NAMES = {
    1: "Corporate Identity (Companies House)",
    3: "Financial Health",
    4: "Carbon & Environmental",
    5: "Labour & Modern Slavery",
    6: "Certifications",
    7: "Regulator Actions",
    9: "Government Contracts",
    10: "Nature & Water Risk",
    11: "Debarment Lists",
    12: "Cyber Risk",
    13: "Social Value",
}

# Free layers only — skip Layer 2 (OpenSanctions costs money)
FREE_LAYERS = [1, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13]


@router.post("/engagements/{engagement_id}/supplier-report/enrich/{supplier_id}")
async def enrich_single_supplier(
    engagement_id: int,
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Run enrichment on a single supplier, streaming per-layer progress.

    Uses only FREE data layers. Skips Layer 2 (OpenSanctions) to avoid API costs.
    """
    from fastapi.responses import StreamingResponse
    from hemera.services.enrichment import enrich_supplier as run_enrich
    from hemera.services.finding_generator import generate_findings_from_sources
    from hemera.models.finding import SupplierFinding
    from datetime import datetime
    import json as _json

    _load_engagement(engagement_id, db)
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    total_layers = len(FREE_LAYERS)

    async def stream():
        # Run enrichment layer by layer
        for i, layer in enumerate(FREE_LAYERS):
            layer_name = LAYER_NAMES.get(layer, f"Layer {layer}")
            yield _json.dumps({
                "type": "progress",
                "current": i + 1,
                "total": total_layers,
                "layer": layer,
                "layer_name": layer_name,
                "status": "analysing",
            }) + "\n"

            try:
                await run_enrich(supplier, db, layers=[layer])
            except Exception as e:
                yield _json.dumps({
                    "type": "progress",
                    "current": i + 1,
                    "total": total_layers,
                    "layer": layer,
                    "layer_name": layer_name,
                    "status": "error",
                    "error": str(e)[:200],
                }) + "\n"

        # Supersede old findings and regenerate
        yield _json.dumps({"type": "progress", "current": total_layers, "total": total_layers, "layer_name": "Generating findings", "status": "analysing"}) + "\n"

        db.query(SupplierFinding).filter(
            SupplierFinding.supplier_id == supplier_id,
            SupplierFinding.source == "deterministic",
            SupplierFinding.is_active == True,  # noqa: E712
        ).update({"is_active": False, "superseded_at": datetime.utcnow()})

        all_sources = db.query(SupplierSource).filter(SupplierSource.supplier_id == supplier_id).all()
        finding_dicts = generate_findings_from_sources(all_sources, supplier_name=supplier.name)
        for fd in finding_dicts:
            finding = SupplierFinding(supplier_id=supplier_id, is_active=True, **fd)
            db.add(finding)

        db.commit()

        yield _json.dumps({
            "type": "done",
            "findings_generated": len(finding_dicts),
            "layers_completed": total_layers,
        }) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@router.patch("/engagements/{engagement_id}/supplier-report/selections")
def save_selections(
    engagement_id: int,
    req: SaveSelectionsRequest,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Save include/exclude decisions incrementally (upsert)."""
    engagement = _load_engagement(engagement_id, db)

    if not engagement.supplier_report_status or engagement.supplier_report_status == "pending":
        engagement.supplier_report_status = "curating"

    user = db.query(User).filter(User.clerk_id == current_user.clerk_id).first()
    user_id = user.id if user else 0

    saved = 0
    for item in req.selections:
        existing = db.query(ReportSelection).filter(
            ReportSelection.engagement_id == engagement_id,
            ReportSelection.finding_id == item.finding_id,
        ).first()

        if existing:
            existing.included = item.included
            if item.client_title is not None:
                existing.client_title = item.client_title
            if item.client_detail is not None:
                existing.client_detail = item.client_detail
            if item.client_language_source is not None:
                existing.client_language_source = item.client_language_source
            if item.analyst_note is not None:
                existing.analyst_note = item.analyst_note
        else:
            sel = ReportSelection(
                engagement_id=engagement_id,
                finding_id=item.finding_id,
                included=item.included,
                client_title=item.client_title,
                client_detail=item.client_detail,
                client_language_source=item.client_language_source,
                analyst_note=item.analyst_note,
                selected_by=user_id,
            )
            db.add(sel)
        saved += 1

    db.commit()
    return {"saved": saved}


@router.post("/engagements/{engagement_id}/supplier-report/actions")
def save_actions(
    engagement_id: int,
    req: SaveActionsRequest,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Save recommended actions for a supplier in this engagement."""
    _load_engagement(engagement_id, db)

    user = db.query(User).filter(User.clerk_id == current_user.clerk_id).first()
    user_id = user.id if user else 0

    # Clear existing actions for this supplier
    db.query(ReportAction).filter(
        ReportAction.engagement_id == engagement_id,
        ReportAction.supplier_id == req.supplier_id,
    ).delete()

    for action in req.actions:
        ra = ReportAction(
            engagement_id=engagement_id,
            supplier_id=req.supplier_id,
            action_text=action["action_text"],
            priority=action.get("priority", 1),
            linked_finding_ids=action.get("linked_finding_ids"),
            language_source=action.get("language_source", "analyst"),
            created_by=user_id,
        )
        db.add(ra)

    db.commit()
    return {"status": "ok"}


@router.post("/engagements/{engagement_id}/supplier-report/publish")
def publish_report(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Publish the supplier report to the client dashboard."""
    engagement = _load_engagement(engagement_id, db)
    engagement.supplier_report_status = "published"
    db.commit()
    return {"status": "published", "engagement_id": engagement_id}


# -- Client-facing endpoints (authenticated, not admin-only) --

@router.get("/engagements/{engagement_id}/supplier-intelligence")
def get_published_report(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Client-facing: get published supplier intelligence data."""
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Org scoping for non-admin users
    if current_user.role != "admin" and engagement.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")

    if engagement.supplier_report_status != "published":
        raise HTTPException(status_code=404, detail="Supplier report not yet published")

    # Reuse the curation data but filter to included selections only
    # Build the data inline to avoid re-calling the admin-authed endpoint
    supplier_ids = (
        db.query(Transaction.supplier_id)
        .filter(
            Transaction.engagement_id == engagement_id,
            Transaction.supplier_id.isnot(None),
            Transaction.is_duplicate == False,  # noqa: E712
        )
        .distinct()
        .all()
    )
    supplier_ids = [sid for (sid,) in supplier_ids]

    suppliers_data = []
    for sid in supplier_ids:
        supplier = db.query(Supplier).filter(Supplier.id == sid).first()
        if not supplier:
            continue

        findings = (
            db.query(SupplierFinding)
            .filter(SupplierFinding.supplier_id == sid, SupplierFinding.is_active == True)  # noqa: E712
            .all()
        )

        finding_ids = [f.id for f in findings]
        selections = []
        if finding_ids:
            selections = (
                db.query(ReportSelection)
                .filter(
                    ReportSelection.engagement_id == engagement_id,
                    ReportSelection.finding_id.in_(finding_ids),
                )
                .all()
            )
        selections_map = {s.finding_id: s for s in selections}

        # Only include findings that have been selected as "included"
        client_findings = []
        for f in findings:
            sel = selections_map.get(f.id)
            if sel and sel.included:
                client_findings.append({
                    "title": sel.client_title or f.title,
                    "detail": sel.client_detail or f.detail,
                    "severity": f.severity,
                    "domain": f.domain,
                })

        actions = (
            db.query(ReportAction)
            .filter(ReportAction.engagement_id == engagement_id, ReportAction.supplier_id == sid)
            .order_by(ReportAction.priority)
            .all()
        )

        hemera_engs = (
            db.query(SupplierEngagement)
            .filter(SupplierEngagement.supplier_id == sid)
            .order_by(SupplierEngagement.created_at.desc())
            .all()
        )

        stats = db.query(
            func.count(Transaction.id),
            func.sum(Transaction.amount_gbp),
            func.sum(Transaction.co2e_kg),
        ).filter(
            Transaction.engagement_id == engagement_id,
            Transaction.supplier_id == sid,
            Transaction.is_duplicate == False,  # noqa: E712
        ).first()

        suppliers_data.append({
            "supplier": {
                "id": supplier.id,
                "name": supplier.name,
                "sector": supplier.sector,
                "hemera_score": supplier.hemera_score,
                "confidence": supplier.confidence,
                "critical_flag": supplier.critical_flag,
            },
            "txn_count": stats[0] if stats else 0,
            "total_spend": round(stats[1] or 0, 2) if stats else 0,
            "total_co2e_kg": round(stats[2] or 0, 2) if stats else 0,
            "findings": client_findings,
            "actions": [
                {
                    "action_text": a.action_text,
                    "priority": a.priority,
                }
                for a in actions
            ],
            "hemera_engagements": [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "status": e.status,
                    "engagement_type": e.engagement_type,
                    "contacted_at": e.contacted_at.isoformat() if e.contacted_at else None,
                    "responded_at": e.responded_at.isoformat() if e.responded_at else None,
                    # notes stripped for client view
                }
                for e in hemera_engs
            ],
        })

    suppliers_data.sort(
        key=lambda s: (
            0 if s["supplier"]["critical_flag"] else 1,
            s["supplier"]["hemera_score"] or 999,
        )
    )

    return {
        "engagement_id": engagement_id,
        "status": "published",
        "exec_summary": engagement.supplier_report_exec_summary,
        "supplier_count": len(suppliers_data),
        "suppliers": suppliers_data,
    }


@router.get("/engagements/{engagement_id}/supplier-intelligence/pdf")
def export_pdf(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Export the HemeraScope supplier intelligence report as PDF."""
    from fastapi.responses import Response
    from hemera.services.hemerascope_report import generate_hemerascope_pdf

    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Org scoping for non-admin users
    if current_user.role != "admin" and engagement.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")

    pdf_bytes = generate_hemerascope_pdf(engagement, db)
    filename = f"HemeraScope-{engagement.display_name or engagement.org_name}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
