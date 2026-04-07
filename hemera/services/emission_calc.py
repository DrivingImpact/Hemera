"""Emission calculation engine.

Implements the cascading precision model:
  Level 1: Supplier-specific verified data (best)
  Level 2: Activity-based DEFRA factors (very good)
  Level 3: Exiobase MRIO spend-based by sector+geography (good)
  Level 4: DEFRA supplementary EEIO spend-based (UK baseline)
  Level 5: USEEIO (US-originated goods)
  Level 6: Climatiq API fallback

Each transaction gets:
  - An emission factor with source and level
  - A calculated kgCO2e value
  - A pedigree score with GSD uncertainty
"""

from sqlalchemy.orm import Session
from hemera.models.emission_factor import EmissionFactor
from hemera.models.transaction import Transaction
from hemera.services.pedigree import score_emission_factor, aggregate_uncertainty, PedigreeScore


def calculate_emissions(
    transactions: list[Transaction],
    db: Session,
    reporting_year: int = 2024,
) -> dict:
    """Calculate emissions for all transactions in an engagement.

    Modifies transactions in-place (sets ef_*, co2e_kg, pedigree_* fields).
    Returns summary stats.
    """
    total_co2e = 0.0
    gsd_values = []
    co2e_values = []

    for t in transactions:
        if not t.amount_gbp or t.is_duplicate:
            continue

        # Find the best emission factor
        ef, level = _find_emission_factor(t, db)

        if ef:
            # Calculate emissions
            co2e_kg = abs(t.amount_gbp) * ef.factor_value
            t.co2e_kg = co2e_kg
            t.ef_value = ef.factor_value
            t.ef_unit = ef.unit
            t.ef_source = ef.source
            t.ef_level = level
            t.ef_year = ef.year
            t.ef_region = ef.region

            # Calculate pedigree uncertainty
            pedigree = score_emission_factor(
                ef_source=ef.source,
                ef_level=level,
                ef_year=ef.year,
                ef_region=ef.region,
                current_year=reporting_year,
            )
            t.pedigree_reliability = pedigree.reliability
            t.pedigree_completeness = pedigree.completeness
            t.pedigree_temporal = pedigree.temporal
            t.pedigree_geographical = pedigree.geographical
            t.pedigree_technological = pedigree.technological
            t.gsd_total = pedigree.gsd_total

            total_co2e += co2e_kg
            gsd_values.append(pedigree.gsd_total)
            co2e_values.append(co2e_kg)
        else:
            # No emission factor found — flag for review
            t.needs_review = True
            t.ef_source = "none"
            t.ef_level = 0

    # Aggregate uncertainty
    overall_gsd = aggregate_uncertainty(gsd_values, co2e_values)
    ci_lower = total_co2e / (overall_gsd ** 2)
    ci_upper = total_co2e * (overall_gsd ** 2)

    # Scope breakdown
    scope1 = sum(t.co2e_kg or 0 for t in transactions if t.scope == 1)
    scope2 = sum(t.co2e_kg or 0 for t in transactions if t.scope == 2)
    scope3 = sum(t.co2e_kg or 0 for t in transactions if t.scope == 3)

    return {
        "total_co2e_kg": total_co2e,
        "total_co2e_tonnes": total_co2e / 1000,
        "scope1_kg": scope1,
        "scope2_kg": scope2,
        "scope3_kg": scope3,
        "overall_gsd": overall_gsd,
        "ci_lower_kg": ci_lower,
        "ci_upper_kg": ci_upper,
        "ci_lower_tonnes": ci_lower / 1000,
        "ci_upper_tonnes": ci_upper / 1000,
        "transactions_calculated": sum(1 for t in transactions if t.co2e_kg is not None),
        "transactions_missing_ef": sum(1 for t in transactions if t.needs_review),
    }


def _find_emission_factor(
    transaction: Transaction,
    db: Session,
) -> tuple[EmissionFactor | None, int]:
    """Find the best emission factor for a transaction using the cascade.

    Returns (EmissionFactor, cascade_level) or (None, 0).
    """
    # Level 1: Supplier-specific — skip for now (no supplier data yet)
    # This will be implemented when the registry has supplier-level carbon data.

    # Level 2: Activity-based DEFRA — only if we know the physical activity
    # This requires parsing utility bills, fuel records etc. Skip for MVP.

    # Level 3-4: Spend-based lookup by category
    if transaction.category_name:
        # Try to match by category name
        ef = (
            db.query(EmissionFactor)
            .filter(
                EmissionFactor.factor_type == "spend",
                EmissionFactor.category.ilike(f"%{transaction.category_name.split(' — ')[-1][:30]}%"),
            )
            .order_by(EmissionFactor.year.desc())
            .first()
        )
        if ef:
            level = 4 if ef.source == "defra" else 3
            return ef, level

    # Fallback: try matching by scope
    if transaction.scope:
        ef = (
            db.query(EmissionFactor)
            .filter(
                EmissionFactor.scope == transaction.scope,
                EmissionFactor.factor_type == "spend",
            )
            .order_by(EmissionFactor.year.desc())
            .first()
        )
        if ef:
            return ef, 4

    # Absolute fallback: general Scope 3 factor
    ef = (
        db.query(EmissionFactor)
        .filter(EmissionFactor.source == "defra", EmissionFactor.factor_type == "spend")
        .order_by(EmissionFactor.year.desc())
        .first()
    )
    if ef:
        return ef, 5

    return None, 0
