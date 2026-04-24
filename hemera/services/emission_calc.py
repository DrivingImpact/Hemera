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

from sqlalchemy import or_
from sqlalchemy.orm import Session
from hemera.models.emission_factor import EmissionFactor
from hemera.models.transaction import Transaction
from hemera.services.pedigree import score_emission_factor, aggregate_uncertainty, PedigreeScore


# ── Classifier category → DEFRA EEIO SIC category mapping ──
#
# Each classifier category_name maps to an ordered list of substrings to match
# against the EEIO factor's `category` or `keywords` field. The first substring
# that hits a defra-eeio row is the chosen factor. If nothing matches, the
# transaction is flagged for review — we do NOT fall back to a generic scope-3
# factor (that's how Office Furniture was silently getting matched to
# Agriculture before).
_EEIO_MATCH_MAP: dict[str, list[str]] = {
    # Scope 3 Cat 1 — Purchased goods
    "Purchased goods — office supplies": ["paper and paper products"],
    "Purchased goods — IT equipment": ["computer, electronic and optical products"],
    "Purchased goods — catering/food": ["other food products", "food and beverage serving"],
    "Purchased goods — drinks/alcohol": ["alcoholic beverages", "soft drinks"],
    "Purchased goods — cleaning/hygiene": ["soap and detergents"],
    "Purchased goods — merchandise/promotional": ["wearing apparel", "other manufactured goods"],
    # Scope 3 Cat 1 — Services
    "Purchased services — professional": ["legal services", "accounting, bookkeeping"],
    "Purchased services — marketing": ["advertising and market research"],
    "Purchased services — insurance": ["insurance, reinsurance"],
    "Purchased services — telecoms": ["telecommunications services"],
    "Purchased services — water supply": ["natural water; water treatment"],
    # Scope 3 Cat 2 — Capital goods
    "Capital goods": ["furniture", "machinery and equipment"],
    # Scope 3 Cat 4 — Upstream transport
    "Upstream transport & distribution": ["postal and courier", "land transport services"],
    # Scope 3 Cat 5 — Waste
    "Waste generated in operations": ["waste collection"],
    # Scope 3 Cat 6 — Business travel
    "Business travel — rail": ["rail transport services"],
    "Business travel — air": ["air transport services"],
    "Business travel — taxi": ["land transport services"],
    "Business travel — accommodation": ["accommodation services"],
    "Business travel — mileage/expenses": ["land transport services"],
    # Scope 3 Cat 7 — Employee commuting
    "Employee commuting": ["land transport services"],
    # Scope 3 Cat 8 — Upstream leased assets
    "Upstream leased assets": ["real estate services"],
    # Scope 1 (EEIO only as a last-resort fallback; activity-based is preferred)
    "Stationary combustion — gas/heating fuel": ["gas; distribution of gaseous fuels"],
    "Mobile combustion — company vehicles": ["coke and refined petroleum products"],
    "Fugitive emissions — refrigerants": ["other chemical products"],
    # Scope 2 (EEIO only as a last-resort fallback)
    "Purchased electricity": ["electricity, transmission"],
    "Purchased heat/steam/cooling": ["gas; distribution of gaseous fuels"],
}


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
        if t.is_duplicate:
            continue

        # Skip rows with no usable numeric value
        is_activity = t.data_type == "activity"
        if is_activity:
            if not t.quantity:
                continue
        else:
            if not t.amount_gbp:
                continue

        # Find the best emission factor (activity uses Level 2, spend Level 3-5)
        ef, level = _find_emission_factor(t, db)

        if ef:
            # Calculate emissions — activity: quantity × factor, spend: amount × factor
            if is_activity:
                co2e_kg = abs(t.quantity) * ef.factor_value
            else:
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

    # Level 2: Activity-based DEFRA — prefer this when the transaction has
    # physical quantities (kWh, litres, m3, kg, km) rather than spend in GBP.
    if transaction.data_type == "activity" and transaction.activity_type:
        ef = _find_activity_factor(transaction, db)
        if ef:
            return ef, 2

    # Level 4: DEFRA EEIO spend-based, matched via the explicit SIC map.
    if transaction.category_name:
        ef = _find_eeio_factor(transaction.category_name, db)
        if ef:
            return ef, 4

    # No reliable match. We intentionally do NOT fall back to an arbitrary
    # scope-3 factor — silently matching unmapped transactions to whatever
    # SIC happens to sort first in the DB is how office furniture ended up
    # classified as "Products of agriculture". Leave the transaction flagged
    # for review so a QC analyst can map it manually.
    return None, 0


def _find_eeio_factor(category_name: str, db: Session) -> EmissionFactor | None:
    """Look up a DEFRA EEIO factor for a classifier category_name.

    Uses _EEIO_MATCH_MAP to translate the classifier's category_name into an
    ordered list of substrings; returns the first EEIO factor whose own
    category/keywords match one of those substrings. Returns None if the
    category isn't in the map or no EEIO row matches.
    """
    substrings = _EEIO_MATCH_MAP.get(category_name)
    if not substrings:
        return None

    for substr in substrings:
        ef = (
            db.query(EmissionFactor)
            .filter(
                EmissionFactor.source == "defra-eeio",
                EmissionFactor.factor_type == "spend",
                or_(
                    EmissionFactor.category.ilike(f"%{substr}%"),
                    EmissionFactor.keywords.ilike(f"%{substr}%"),
                ),
            )
            .order_by(EmissionFactor.year.desc())
            .first()
        )
        if ef:
            return ef

    return None


# Map canonical activity_type → (DEFRA category keywords, expected unit substring)
# Used to narrow the DEFRA activity factor lookup.
ACTIVITY_TYPE_LOOKUP: dict[str, tuple[list[str], str | None]] = {
    "electricity":   (["electricity", "grid"],          "kWh"),
    "natural_gas":   (["natural gas", "gas"],            "kWh"),
    "diesel":        (["diesel"],                        "litre"),
    "petrol":        (["petrol"],                        "litre"),
    "lpg":           (["lpg", "liquefied petroleum"],    "litre"),
    "heating_oil":   (["burning oil", "heating oil"],    "litre"),
    "heat":          (["district heat", "heat"],         "kWh"),
    "water":         (["water supply", "water"],         "m3"),
    "waste":         (["waste"],                         "tonne"),
    "distance":      (["passenger car", "van", "hgv"],   "km"),
    "refrigerants":  (["refrigerant"],                   "kg"),
    "other":         ([],                                 None),
}


def _find_activity_factor(
    transaction: Transaction,
    db: Session,
) -> EmissionFactor | None:
    """Look up a DEFRA (or other) activity-based factor for a transaction.

    Filters to factor_type='activity' and matches the category keyword(s)
    associated with the transaction's activity_type. Optionally narrows by
    unit when possible (e.g. kWh vs m3 for gas).
    """
    at = transaction.activity_type or ""
    keywords, unit_hint = ACTIVITY_TYPE_LOOKUP.get(at, ([], None))
    if not keywords:
        return None

    query = db.query(EmissionFactor).filter(
        EmissionFactor.factor_type == "activity",
    )

    # Build a keyword filter
    from sqlalchemy import or_
    query = query.filter(
        or_(*[EmissionFactor.category.ilike(f"%{kw}%") for kw in keywords])
    )

    # Narrow by unit when a hint is available
    if unit_hint:
        query = query.filter(EmissionFactor.unit.ilike(f"%{unit_hint}%"))

    return query.order_by(EmissionFactor.year.desc()).first()
