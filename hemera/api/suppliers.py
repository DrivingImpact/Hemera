"""Supplier registry endpoints."""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, case, exists
from sqlalchemy.orm import Session

from hemera.database import get_db
from hemera.dependencies import require_admin
from hemera.models.supplier import Supplier, SupplierScore, SupplierSource
from hemera.models.transaction import Transaction
from hemera.models.engagement import Engagement
from hemera.models.finding import SupplierFinding
from hemera.models.ai_task import AITask
from hemera.services.enrichment import enrich_supplier, enrich_batch
from hemera.services.companies_house import search_company, get_company
from hemera.services.ai_task_runner import create_ai_task

router = APIRouter()


@router.get("/suppliers")
def list_suppliers(
    q: str = Query(None, description="Search by name"),
    ch_number: str | None = Query(None, description="Search by Companies House number"),
    risk_level: str | None = Query(None, description="Filter by risk level: critical, high, medium, low"),
    min_score: float | None = Query(None, description="Minimum Hemera Score"),
    max_score: float | None = Query(None, description="Maximum Hemera Score"),
    sector: str | None = Query(None, description="Filter by sector"),
    enrichment_status: str | None = Query(None, description="enriched or not_enriched"),
    analysed_after: str | None = Query(None, description="ISO date string, filter by last analysis date"),
    analysed_before: str | None = Query(None, description="ISO date string, filter by last analysis date"),
    sort_by: str = Query("name", description="Sort by: name, score, last_analysed, risk"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """List suppliers with advanced filtering, sorting, and pagination."""

    # Subquery: last_analysed_at (max fetched_at from SupplierSource)
    last_analysed_sub = (
        db.query(
            SupplierSource.supplier_id,
            func.max(SupplierSource.fetched_at).label("last_analysed_at"),
        )
        .group_by(SupplierSource.supplier_id)
        .subquery()
    )

    # Subquery: engagement_count (count of distinct engagements via Transaction)
    engagement_count_sub = (
        db.query(
            Transaction.supplier_id,
            func.count(func.distinct(Transaction.engagement_id)).label("engagement_count"),
        )
        .filter(Transaction.supplier_id.isnot(None))
        .group_by(Transaction.supplier_id)
        .subquery()
    )

    # Subquery: has_sources (for enrichment_status filter)
    has_sources_sub = (
        db.query(SupplierSource.supplier_id)
        .distinct()
        .subquery()
    )

    query = (
        db.query(
            Supplier,
            last_analysed_sub.c.last_analysed_at,
            engagement_count_sub.c.engagement_count,
        )
        .outerjoin(last_analysed_sub, Supplier.id == last_analysed_sub.c.supplier_id)
        .outerjoin(engagement_count_sub, Supplier.id == engagement_count_sub.c.supplier_id)
    )

    # Filters
    if q:
        query = query.filter(Supplier.name.ilike(f"%{q}%"))
    if ch_number:
        query = query.filter(Supplier.ch_number == ch_number)
    if sector:
        query = query.filter(Supplier.sector.ilike(f"%{sector}%"))
    if min_score is not None:
        query = query.filter(Supplier.hemera_score >= min_score)
    if max_score is not None:
        query = query.filter(Supplier.hemera_score <= max_score)

    if risk_level:
        if risk_level == "critical":
            query = query.filter(Supplier.critical_flag == True)
        elif risk_level == "high":
            query = query.filter(Supplier.critical_flag == False, Supplier.hemera_score < 40)
        elif risk_level == "medium":
            query = query.filter(
                Supplier.critical_flag == False,
                Supplier.hemera_score >= 40,
                Supplier.hemera_score <= 70,
            )
        elif risk_level == "low":
            query = query.filter(Supplier.critical_flag == False, Supplier.hemera_score > 70)

    if enrichment_status == "enriched":
        query = query.filter(Supplier.id.in_(db.query(has_sources_sub.c.supplier_id)))
    elif enrichment_status == "not_enriched":
        query = query.filter(~Supplier.id.in_(db.query(has_sources_sub.c.supplier_id)))

    if analysed_after:
        query = query.filter(last_analysed_sub.c.last_analysed_at >= analysed_after)
    if analysed_before:
        query = query.filter(last_analysed_sub.c.last_analysed_at <= analysed_before)

    # Sorting
    if sort_by == "score":
        query = query.order_by(Supplier.hemera_score.desc().nullslast())
    elif sort_by == "last_analysed":
        query = query.order_by(last_analysed_sub.c.last_analysed_at.desc().nullslast())
    elif sort_by == "risk":
        # critical first, then by score ascending (worst first)
        query = query.order_by(
            Supplier.critical_flag.desc(),
            Supplier.hemera_score.asc().nullslast(),
        )
    else:
        query = query.order_by(Supplier.name)

    results = query.offset(offset).limit(limit).all()

    return [
        {
            "id": s.id,
            "ch_number": s.ch_number,
            "name": s.name,
            "sector": s.sector,
            "hemera_score": s.hemera_score,
            "confidence": s.confidence,
            "critical_flag": s.critical_flag,
            "status": s.status,
            "last_analysed_at": last_analysed.isoformat() if last_analysed else None,
            "engagement_count": eng_count or 0,
        }
        for s, last_analysed, eng_count in results
    ]


@router.get("/suppliers/search/companies-house")
async def search_companies_house(
    q: str = Query(..., description="Search query for Companies House"),
    _admin=Depends(require_admin),
):
    """Search Companies House API for companies."""
    results = await search_company(q, limit=10)
    return results


@router.post("/suppliers/from-companies-house")
async def create_from_companies_house(
    body: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Create a new supplier from Companies House data.

    Body: { company_number: str, company_name: str, enrich: bool = False }
    """
    company_number = body.get("company_number")
    company_name = body.get("company_name")
    do_enrich = body.get("enrich", False)

    if not company_number or not company_name:
        raise HTTPException(status_code=422, detail="company_number and company_name are required")

    # Check for existing supplier with this CH number
    existing = db.query(Supplier).filter(Supplier.ch_number == company_number).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Supplier with CH number {company_number} already exists (id={existing.id})")

    # Fetch full profile from Companies House
    ch_data = await get_company(company_number)

    supplier = Supplier(
        ch_number=company_number,
        hemera_id=str(uuid.uuid4()),
        name=company_name,
        legal_name=ch_data.get("name") if ch_data else company_name,
        status="unverified",
        sic_codes=ch_data.get("sic_codes") if ch_data else None,
        registered_address=str(ch_data.get("registered_address")) if ch_data and ch_data.get("registered_address") else None,
    )

    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    if do_enrich:
        background_tasks.add_task(enrich_supplier, supplier, db)

    return {
        "id": supplier.id,
        "ch_number": supplier.ch_number,
        "hemera_id": supplier.hemera_id,
        "name": supplier.name,
        "legal_name": supplier.legal_name,
        "status": supplier.status,
        "sic_codes": supplier.sic_codes,
        "registered_address": supplier.registered_address,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
        "enrich_queued": do_enrich,
    }


@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    """Get full supplier profile with score history, sources, engagements, and findings."""
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

    # Get engagements via Transaction join
    engagement_rows = (
        db.query(
            Engagement.id,
            Engagement.org_name,
            Engagement.display_name,
            Engagement.status,
            Engagement.created_at,
            func.sum(Transaction.amount_gbp).label("spend"),
            func.sum(Transaction.co2e_kg).label("co2e"),
        )
        .join(Transaction, Transaction.engagement_id == Engagement.id)
        .filter(Transaction.supplier_id == supplier_id)
        .group_by(
            Engagement.id,
            Engagement.org_name,
            Engagement.display_name,
            Engagement.status,
            Engagement.created_at,
        )
        .all()
    )

    # Get active findings
    findings = (
        db.query(SupplierFinding)
        .filter(
            SupplierFinding.supplier_id == supplier_id,
            SupplierFinding.is_active == True,
        )
        .order_by(SupplierFinding.created_at.desc())
        .all()
    )

    # Get completed AI analysis tasks for this supplier
    ai_tasks = (
        db.query(AITask)
        .filter(
            AITask.target_type == "supplier",
            AITask.target_id == supplier_id,
            AITask.status == "completed",
        )
        .order_by(AITask.completed_at.desc())
        .all()
    )

    ai_analysis = {
        "risk_analysis": None,
        "recommended_actions": None,
        "last_analysed_at": None,
    }

    for task in ai_tasks:
        task_type = task.task_type
        if task_type in ("risk_analysis", "recommended_actions") and ai_analysis[task_type] is None:
            try:
                parsed = json.loads(task.response_text)
            except (json.JSONDecodeError, TypeError):
                parsed = task.response_text
            ai_analysis[task_type] = parsed
            if ai_analysis["last_analysed_at"] is None and task.completed_at:
                ai_analysis["last_analysed_at"] = task.completed_at.isoformat()

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
        "hemera_score": s.hemera_score,
        "confidence": s.confidence,
        "critical_flag": s.critical_flag,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "score_history": [
            {
                "hemera_score": sc.hemera_score,
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
        "engagements": [
            {
                "id": row.id,
                "org_name": row.org_name,
                "display_name": row.display_name,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "spend": round(row.spend, 2) if row.spend else 0,
                "co2e": round(row.co2e, 2) if row.co2e else 0,
            }
            for row in engagement_rows
        ],
        "findings": [
            {
                "id": f.id,
                "domain": f.domain,
                "severity": f.severity,
                "title": f.title,
                "detail": f.detail,
                "source": f.source,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in findings
        ],
        "ai_analysis": ai_analysis,
    }


@router.post("/suppliers/{supplier_id}/enrich")
async def enrich_single_supplier(supplier_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
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
    _admin=Depends(require_admin),
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


class AIAnalysisRequest(BaseModel):
    mode: str = "api"  # "api" = call Claude now, "manual" = stage prompt for Max
    task_types: list[str] = ["risk_analysis", "recommended_actions"]


@router.post("/suppliers/{supplier_id}/ai-analysis")
def run_supplier_ai_analysis(
    supplier_id: int,
    body: AIAnalysisRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Run AI analysis on a supplier. Admin chooses API (automatic) or Manual (Max mode).

    In API mode, Claude is called immediately and the response is stored.
    In Manual mode, prompts are generated and staged — the admin copies them
    to Claude Max, gets the response, and pastes it back.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Build context from supplier's current data
    latest_score = (
        db.query(SupplierScore)
        .filter(SupplierScore.supplier_id == supplier_id)
        .order_by(SupplierScore.scored_at.desc())
        .first()
    )

    all_sources = (
        db.query(SupplierSource)
        .filter(SupplierSource.supplier_id == supplier_id)
        .all()
    )

    active_findings = (
        db.query(SupplierFinding)
        .filter(SupplierFinding.supplier_id == supplier_id, SupplierFinding.is_active == True)
        .all()
    )

    context = {
        "supplier_name": supplier.name,
        "sector": supplier.sector,
        "sic_codes": supplier.sic_codes,
        "hemera_score": supplier.hemera_score,
        "domain_scores": {
            "governance_identity": latest_score.governance_identity if latest_score else None,
            "labour_ethics": latest_score.labour_ethics if latest_score else None,
            "carbon_climate": latest_score.carbon_climate if latest_score else None,
            "water_biodiversity": latest_score.water_biodiversity if latest_score else None,
            "product_supply_chain": latest_score.product_supply_chain if latest_score else None,
            "transparency_disclosure": latest_score.transparency_disclosure if latest_score else None,
            "anti_corruption": latest_score.anti_corruption if latest_score else None,
            "social_value": latest_score.social_value if latest_score else None,
        } if latest_score else {},
        "sources_summary": [
            {"layer": s.layer, "source": s.source_name, "summary": s.summary}
            for s in all_sources
        ],
        "deterministic_findings": [
            {"severity": f.severity, "title": f.title, "domain": f.domain, "detail": f.detail}
            for f in active_findings
        ],
    }

    tasks_created = []
    for task_type in body.task_types:
        if task_type == "recommended_actions":
            task_context = {"supplier_name": supplier.name, "findings": context["deterministic_findings"]}
        else:
            task_context = context

        task = create_ai_task(db, task_type, "supplier", supplier.id, body.mode, task_context)
        tasks_created.append({
            "id": task.id,
            "task_type": task.task_type,
            "mode": task.mode,
            "status": task.status,
            "prompt_text": task.prompt_text if body.mode != "api" else None,
            "response_text": task.response_text,
        })

    db.commit()

    return {
        "supplier_id": supplier.id,
        "tasks": tasks_created,
    }
