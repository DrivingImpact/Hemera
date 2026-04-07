"""QC sampling endpoints — generate sample, get status, submit results."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.services.qc_sampling import (
    calculate_sample_size, select_sample, build_qc_cards,
    compute_qc_status, apply_qc_result, _compute_top_10_threshold,
    HARD_GATE_THRESHOLD,
)
from hemera.dependencies import require_admin
from hemera.services.clerk import ClerkUser

router = APIRouter()


class QCCheckResult(BaseModel):
    transaction_id: int
    classification_pass: bool
    emission_factor_pass: bool
    arithmetic_pass: bool
    supplier_match_pass: bool
    pedigree_pass: bool
    notes: str = ""


class QCSubmitRequest(BaseModel):
    results: list[QCCheckResult]


def _get_engagement_or_404(engagement_id: int, db: Session) -> Engagement:
    eng = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return eng


def _get_transactions(engagement_id: int, db: Session) -> list[Transaction]:
    return db.query(Transaction).filter(Transaction.engagement_id == engagement_id).all()


@router.post("/engagements/{engagement_id}/qc/generate")
def generate_qc_sample(engagement_id: int, db: Session = Depends(get_db), current_user: ClerkUser = Depends(require_admin)):
    """Generate a stratified QC sample for analyst verification."""
    eng = _get_engagement_or_404(engagement_id, db)
    transactions = _get_transactions(engagement_id, db)
    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found")

    already_sampled = [t for t in transactions if t.is_sampled]
    if already_sampled:
        top_10 = _compute_top_10_threshold(transactions)
        cards = build_qc_cards(already_sampled, top_10)
        return _build_generate_response(eng, transactions, already_sampled, cards)

    sample = select_sample(transactions, engagement_id=eng.id)
    for t in sample:
        t.is_sampled = True
    db.flush()
    db.commit()

    top_10 = _compute_top_10_threshold(transactions)
    cards = build_qc_cards(sample, top_10)
    return _build_generate_response(eng, transactions, sample, cards)


def _build_generate_response(eng, all_txns, sample, cards) -> dict:
    by_scope = {}
    by_ef_level = {}
    high_value_count = 0
    low_confidence_count = 0
    top_10 = _compute_top_10_threshold(all_txns)

    for t in sample:
        scope_key = str(t.scope or "?")
        by_scope[scope_key] = by_scope.get(scope_key, 0) + 1
        level_key = f"L{t.ef_level or 0}"
        by_ef_level[level_key] = by_ef_level.get(level_key, 0) + 1
        if abs(t.amount_gbp or 0) >= top_10:
            high_value_count += 1
        if t.classification_method in ("none", "llm"):
            low_confidence_count += 1

    return {
        "engagement_id": eng.id,
        "sample_size": len(sample),
        "population_size": len(all_txns),
        "confidence_level": 0.95,
        "acceptable_error_rate": 0.05,
        "strata_breakdown": {
            "by_scope": by_scope, "by_ef_level": by_ef_level,
            "high_value_sampled": high_value_count,
            "low_confidence_sampled": low_confidence_count,
        },
        "cards": cards,
    }


@router.get("/engagements/{engagement_id}/qc")
def get_qc_status(engagement_id: int, db: Session = Depends(get_db), current_user: ClerkUser = Depends(require_admin)):
    """Get current QC status for an engagement."""
    _get_engagement_or_404(engagement_id, db)
    transactions = _get_transactions(engagement_id, db)
    status = compute_qc_status(transactions)
    status["engagement_id"] = engagement_id
    return status


@router.post("/engagements/{engagement_id}/qc/submit")
def submit_qc_results(engagement_id: int, body: QCSubmitRequest, db: Session = Depends(get_db), current_user: ClerkUser = Depends(require_admin)):
    """Submit QC check results for sampled transactions."""
    eng = _get_engagement_or_404(engagement_id, db)
    transactions = _get_transactions(engagement_id, db)
    txn_map = {t.id: t for t in transactions}

    accepted = 0
    for result in body.results:
        txn = txn_map.get(result.transaction_id)
        if not txn or not txn.is_sampled:
            continue
        apply_qc_result(txn, result.model_dump())
        accepted += 1

    db.flush()
    db.commit()

    status = compute_qc_status(transactions)
    if status["status"] == "passed":
        eng.status = "qc_passed"
        db.flush()
        db.commit()

    sampled = [t for t in transactions if t.is_sampled]
    reviewed = [t for t in sampled if t.qc_pass is not None]
    remaining = len(sampled) - len(reviewed)

    response = {
        "accepted": accepted, "remaining": remaining,
        "qc_complete": status["status"] in ("passed", "failed"),
        "current_error_rate": status.get("current_error_rate", 0.0),
    }
    if status["status"] in ("passed", "failed"):
        response["hard_gate_result"] = status.get("hard_gate_result", "unknown")
        response["engagement_status"] = eng.status
    return response
