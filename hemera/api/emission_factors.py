"""Emission factor context endpoint — shows surrounding rows and calculation breakdown."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from hemera.database import get_db
from hemera.dependencies import get_current_user
from hemera.models.emission_factor import EmissionFactor
from hemera.models.transaction import Transaction

router = APIRouter()


@router.get("/emission-factors/{factor_id}/context")
def get_emission_factor_context(
    factor_id: int,
    transaction_id: int | None = Query(None, description="Optional transaction ID for calculation breakdown"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get an emission factor with surrounding context rows and optional calculation breakdown."""

    factor = db.query(EmissionFactor).filter(EmissionFactor.id == factor_id).first()
    if not factor:
        raise HTTPException(status_code=404, detail="Emission factor not found")

    # Find surrounding factors: same source_sheet, source_row within +/-7 rows
    context_rows = []
    if factor.source_sheet and factor.source_row is not None:
        context_rows = (
            db.query(EmissionFactor)
            .filter(
                EmissionFactor.source_sheet == factor.source_sheet,
                EmissionFactor.source_row >= factor.source_row - 7,
                EmissionFactor.source_row <= factor.source_row + 7,
                EmissionFactor.id != factor.id,
            )
            .order_by(EmissionFactor.source_row)
            .all()
        )

    def _serialise_factor(f: EmissionFactor) -> dict:
        return {
            "id": f.id,
            "source": f.source,
            "category": f.category,
            "subcategory": f.subcategory,
            "scope": f.scope,
            "factor_value": f.factor_value,
            "unit": f.unit,
            "factor_type": f.factor_type,
            "year": f.year,
            "region": f.region,
            "keywords": f.keywords,
            "source_sheet": f.source_sheet,
            "source_row": f.source_row,
            "source_hierarchy": f.source_hierarchy,
        }

    # Build calculation breakdown if transaction_id provided
    calculation = None
    if transaction_id is not None:
        txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if txn:
            if txn.data_type == "activity" and txn.quantity is not None:
                quantity = txn.quantity
                unit = txn.quantity_unit or ""
                description = f"{quantity} {unit} x {factor.factor_value} {factor.unit}"
            else:
                quantity = txn.amount_gbp or 0
                unit = "GBP"
                description = f"£{quantity:,.2f} x {factor.factor_value} {factor.unit}"

            calculation = {
                "description": description,
                "quantity": quantity,
                "unit": unit,
                "factor_value": factor.factor_value,
                "factor_unit": factor.unit,
                "co2e_kg": txn.co2e_kg,
            }

    return {
        "factor": _serialise_factor(factor),
        "context_rows": [_serialise_factor(r) for r in context_rows],
        "calculation": calculation,
    }


@router.get("/emission-factors/by-transaction/{transaction_id}/context")
def get_emission_factor_context_by_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Find the emission factor used for a transaction and return context."""

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if not txn.ef_source or not txn.ef_value:
        raise HTTPException(status_code=404, detail="No emission factor on this transaction")

    # Find the matching emission factor by source, value, year
    query = db.query(EmissionFactor).filter(
        EmissionFactor.factor_value == txn.ef_value,
        EmissionFactor.year == txn.ef_year,
    )
    if txn.ef_source:
        query = query.filter(EmissionFactor.source == txn.ef_source.lower().replace(" ", "-").split("(")[0].strip().rstrip("-"))

    factor = query.first()

    # Fallback: try matching just by value and year across all sources
    if not factor:
        factor = (
            db.query(EmissionFactor)
            .filter(EmissionFactor.factor_value == txn.ef_value, EmissionFactor.year == txn.ef_year)
            .first()
        )

    if not factor:
        # Return a synthetic response without context rows
        if txn.data_type == "activity" and txn.quantity is not None:
            calc_desc = f"{txn.quantity} {txn.quantity_unit or ''} x {txn.ef_value} {txn.ef_unit or ''}"
            calc_qty = txn.quantity
            calc_unit = txn.quantity_unit or ""
        else:
            calc_desc = f"£{abs(txn.amount_gbp or 0):,.2f} x {txn.ef_value} {txn.ef_unit or ''}"
            calc_qty = abs(txn.amount_gbp or 0)
            calc_unit = "GBP"

        return {
            "factor": {
                "id": None,
                "source": txn.ef_source,
                "category": txn.category_name,
                "subcategory": None,
                "scope": txn.scope,
                "factor_value": txn.ef_value,
                "unit": txn.ef_unit,
                "factor_type": txn.data_type or "spend",
                "year": txn.ef_year,
                "region": txn.ef_region,
                "keywords": None,
                "source_sheet": None,
                "source_row": None,
                "source_hierarchy": None,
            },
            "context_rows": [],
            "calculation": {
                "description": calc_desc,
                "quantity": calc_qty,
                "unit": calc_unit,
                "factor_value": txn.ef_value,
                "factor_unit": txn.ef_unit or "",
                "co2e_kg": txn.co2e_kg,
            },
        }

    # Found the factor — use the existing context logic
    context_rows = []
    if factor.source_sheet and factor.source_row is not None:
        context_rows = (
            db.query(EmissionFactor)
            .filter(
                EmissionFactor.source_sheet == factor.source_sheet,
                EmissionFactor.source_row >= factor.source_row - 7,
                EmissionFactor.source_row <= factor.source_row + 7,
                EmissionFactor.id != factor.id,
            )
            .order_by(EmissionFactor.source_row)
            .all()
        )

    def _ser(f: EmissionFactor) -> dict:
        return {
            "id": f.id,
            "source": f.source,
            "category": f.category,
            "subcategory": f.subcategory,
            "scope": f.scope,
            "factor_value": f.factor_value,
            "unit": f.unit,
            "factor_type": f.factor_type,
            "year": f.year,
            "region": f.region,
            "keywords": f.keywords,
            "source_sheet": f.source_sheet,
            "source_row": f.source_row,
            "source_hierarchy": f.source_hierarchy,
        }

    if txn.data_type == "activity" and txn.quantity is not None:
        calc_desc = f"{txn.quantity} {txn.quantity_unit or ''} x {factor.factor_value} {factor.unit}"
        calc_qty = txn.quantity
        calc_unit = txn.quantity_unit or ""
    else:
        calc_desc = f"£{abs(txn.amount_gbp or 0):,.2f} x {factor.factor_value} {factor.unit}"
        calc_qty = abs(txn.amount_gbp or 0)
        calc_unit = "GBP"

    return {
        "factor": _ser(factor),
        "context_rows": [_ser(r) for r in context_rows],
        "calculation": {
            "description": calc_desc,
            "quantity": calc_qty,
            "unit": calc_unit,
            "factor_value": factor.factor_value,
            "factor_unit": factor.unit,
            "co2e_kg": txn.co2e_kg,
        },
    }
