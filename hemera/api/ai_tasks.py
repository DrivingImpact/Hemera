"""AI task endpoints — create, query, and paste-back."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.ai_task import AITask
from hemera.services.ai_task_runner import create_ai_task, complete_manual_task
from hemera.dependencies import require_admin
from hemera.services.clerk import ClerkUser

router = APIRouter()


class CreateAITaskRequest(BaseModel):
    task_type: str
    target_type: str
    target_id: int
    mode: str  # "api" or "manual"
    context: dict | None = None  # Optional override; if None, auto-built from target


class PasteBackRequest(BaseModel):
    response_text: str


@router.post("/ai-tasks", status_code=201)
def create_task(
    req: CreateAITaskRequest,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    context = req.context or _build_context_from_target(req.task_type, req.target_type, req.target_id, db)

    task = create_ai_task(
        db=db,
        task_type=req.task_type,
        target_type=req.target_type,
        target_id=req.target_id,
        mode=req.mode,
        context=context,
    )
    db.commit()
    return _task_to_dict(task)


@router.patch("/ai-tasks/{task_id}")
def paste_back(
    task_id: int,
    req: PasteBackRequest,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    task = db.query(AITask).filter(AITask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")
    if task.status != "prompt_copied":
        raise HTTPException(status_code=400, detail=f"Task status is {task.status}, expected prompt_copied")

    task = complete_manual_task(db, task, req.response_text)
    db.commit()
    return _task_to_dict(task)


@router.get("/ai-tasks")
def list_tasks(
    target_type: str | None = None,
    target_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    query = db.query(AITask)
    if target_type:
        query = query.filter(AITask.target_type == target_type)
    if target_id:
        query = query.filter(AITask.target_id == target_id)
    tasks = query.order_by(AITask.created_at.desc()).limit(50).all()
    return [_task_to_dict(t) for t in tasks]


def _build_context_from_target(task_type: str, target_type: str, target_id: int, db) -> dict:
    """Auto-build prompt context from database state."""
    if target_type == "supplier":
        from hemera.models.supplier import Supplier, SupplierSource
        from hemera.models.finding import SupplierFinding
        from hemera.models.supplier_engagement import SupplierEngagement

        supplier = db.query(Supplier).filter(Supplier.id == target_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        if task_type == "risk_analysis":
            sources = db.query(SupplierSource).filter(SupplierSource.supplier_id == target_id).all()
            findings = db.query(SupplierFinding).filter(
                SupplierFinding.supplier_id == target_id,
                SupplierFinding.is_active == True,  # noqa: E712
                SupplierFinding.source == "deterministic",
            ).all()
            return {
                "supplier_name": supplier.legal_name or supplier.name,
                "sector": supplier.sector,
                "sic_codes": supplier.sic_codes or [],
                "sources_summary": [
                    {"layer": s.layer, "source": s.source_name, "summary": s.summary or ""}
                    for s in sources
                ],
                "deterministic_findings": [
                    {"title": f.title, "severity": f.severity}
                    for f in findings
                ],
                "hemera_score": supplier.hemera_score,
                "domain_scores": {},
            }

        if task_type in ("client_language", "recommended_actions"):
            findings = db.query(SupplierFinding).filter(
                SupplierFinding.supplier_id == target_id,
                SupplierFinding.is_active == True,  # noqa: E712
            ).all()
            return {
                "supplier_name": supplier.legal_name or supplier.name,
                "findings": [
                    {"title": f.title, "detail": f.detail, "severity": f.severity, "domain": f.domain}
                    for f in findings
                ],
            }

        if task_type == "engagement_summary":
            engs = db.query(SupplierEngagement).filter(
                SupplierEngagement.supplier_id == target_id
            ).all()
            return {
                "supplier_name": supplier.legal_name or supplier.name,
                "engagements": [
                    {"subject": e.subject, "status": e.status, "notes": e.notes}
                    for e in engs
                ],
            }

    if target_type == "engagement" and task_type == "exec_summary":
        from hemera.models.engagement import Engagement

        engagement = db.query(Engagement).filter(Engagement.id == target_id).first()
        if not engagement:
            raise HTTPException(status_code=404, detail="Engagement not found")

        return {
            "org_name": engagement.display_name or engagement.org_name,
            "supplier_count": engagement.supplier_count or 0,
            "total_spend": 0,
            "critical_count": 0,
            "attention_count": 0,
            "strong_count": 0,
        }

    return {}


def _task_to_dict(t: AITask) -> dict:
    return {
        "id": t.id,
        "task_type": t.task_type,
        "target_type": t.target_type,
        "target_id": t.target_id,
        "mode": t.mode,
        "status": t.status,
        "prompt_text": t.prompt_text,
        "response_text": t.response_text,
        "prompt_hash": t.prompt_hash,
        "token_count": t.token_count,
        "cost_usd": t.cost_usd,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }
