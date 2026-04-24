"""Tests for the emission-factor matching cascade.

Anchored on the real bug: office furniture purchases were being matched to
"Products of agriculture, hunting and related services" because the EEIO
lookup was a naive substring match with a scope-only fallback that returned
whatever row happened to sort first in the DB.
"""
import pytest
from hemera.models.emission_factor import EmissionFactor
from hemera.models.transaction import Transaction
from hemera.services.emission_calc import (
    _find_emission_factor,
    _find_eeio_factor,
    _EEIO_MATCH_MAP,
)


# A subset of real DEFRA EEIO SIC categories, enough to exercise the mapping.
_EEIO_ROWS = [
    ("01", "Products of agriculture, hunting and related services"),
    ("17", "Paper and paper products"),
    ("19", "Coke and refined petroleum products"),
    ("20.4", "Soap and detergents, cleaning and polishing preparations"),
    ("20.5", "Other chemical products"),
    ("26", "Computer, electronic and optical products"),
    ("28", "Machinery and equipment n.e.c."),
    ("31", "Furniture"),
    ("32", "Other manufactured goods"),
    ("35.1", "Electricity, transmission and distribution"),
    ("35.2-3", "Gas; distribution of gaseous fuels through mains"),
    ("36", "Natural water; water treatment and supply services"),
    ("38", "Waste collection, treatment and disposal services"),
    ("49.1-2", "Rail transport services"),
    ("49.3-5", "Land transport services and transport services via pipelines"),
    ("51", "Air transport services"),
    ("53", "Postal and courier services"),
    ("55", "Accommodation services"),
    ("56", "Food and beverage serving services"),
    ("61", "Telecommunications services"),
    ("65.1-2", "Insurance, reinsurance and pension funding services"),
    ("68.3", "Real estate services on a fee or contract basis"),
    ("69.1", "Legal services"),
    ("69.2", "Accounting, bookkeeping and auditing services"),
    ("73", "Advertising and market research services"),
]


@pytest.fixture
def eeio_factors(db):
    factors = []
    for sic, desc in _EEIO_ROWS:
        ef = EmissionFactor(
            source="defra-eeio", category=desc, subcategory=sic,
            scope=3, factor_value=1.0, unit="kgCO2e/GBP",
            factor_type="spend", year=2022, region="UK",
            keywords=desc.lower(),
        )
        db.add(ef)
        factors.append(ef)
    # Also add one non-EEIO row to make sure we don't accidentally pick it.
    db.add(EmissionFactor(
        source="defra", category="Electricity", subcategory="UK",
        scope=2, factor_value=0.23, unit="kgCO2e/kWh",
        factor_type="activity", year=2024, region="UK", keywords="electricity",
    ))
    db.flush()
    return factors


# ── Regression: the exact bug from the screenshot ──

def test_office_furniture_does_not_match_agriculture(db, eeio_factors):
    """Viking Direct → 'Purchased goods — office supplies' must NOT return SIC 01."""
    txn = Transaction(
        engagement_id=1, row_number=1,
        raw_description="Office furniture – desks", raw_supplier="Viking Direct",
        raw_amount=1890.0, amount_gbp=1890.0,
        scope=3, ghg_category=1,
        category_name="Purchased goods — office supplies",
        classification_method="keyword", classification_confidence=0.85,
    )
    ef, level = _find_emission_factor(txn, db)
    assert ef is not None
    assert level == 4
    assert "agriculture" not in ef.category.lower()
    assert ef.subcategory == "17"  # Paper and paper products


def test_capital_goods_matches_furniture(db, eeio_factors):
    """A transaction classified as Capital goods should find SIC 31 Furniture."""
    txn = Transaction(
        engagement_id=1, row_number=1,
        raw_description="Desk", raw_supplier="IKEA Business",
        raw_amount=500.0, amount_gbp=500.0,
        scope=3, ghg_category=2,
        category_name="Capital goods",
    )
    ef, _ = _find_emission_factor(txn, db)
    assert ef is not None
    assert ef.subcategory == "31"


# ── No silent fallback: unmapped categories flag for review ──

def test_unmapped_category_returns_none(db, eeio_factors):
    """An unknown category_name must not auto-fall back to an arbitrary SIC."""
    txn = Transaction(
        engagement_id=1, row_number=1,
        raw_description="Mystery payment", raw_supplier="Unknown Co",
        raw_amount=1000.0, amount_gbp=1000.0,
        scope=3, ghg_category=1,
        category_name="Something the classifier invented",
    )
    ef, level = _find_emission_factor(txn, db)
    assert ef is None
    assert level == 0


# ── Coverage of the full classifier → EEIO map ──

def test_every_classifier_category_has_a_match(db, eeio_factors):
    """Every entry in _EEIO_MATCH_MAP must resolve to an EEIO row using the
    fixture data — catches typos like "telecom" vs "telecommunications"."""
    # The fixture data is a subset, so only check the categories whose
    # target SIC is in the fixture. This still exercises the mapping format.
    represented_in_fixture = {
        "Purchased goods — office supplies",
        "Purchased goods — IT equipment",
        "Purchased goods — catering/food",
        "Purchased goods — cleaning/hygiene",
        "Purchased goods — merchandise/promotional",
        "Purchased services — professional",
        "Purchased services — marketing",
        "Purchased services — insurance",
        "Purchased services — telecoms",
        "Purchased services — water supply",
        "Capital goods",
        "Upstream transport & distribution",
        "Waste generated in operations",
        "Business travel — rail",
        "Business travel — air",
        "Business travel — taxi",
        "Business travel — accommodation",
        "Business travel — mileage/expenses",
        "Employee commuting",
        "Upstream leased assets",
        "Mobile combustion — company vehicles",
        "Fugitive emissions — refrigerants",
        "Purchased electricity",
        "Purchased heat/steam/cooling",
        "Stationary combustion — gas/heating fuel",
    }
    missing = []
    for category in represented_in_fixture:
        assert category in _EEIO_MATCH_MAP, f"{category} missing from _EEIO_MATCH_MAP"
        ef = _find_eeio_factor(category, db)
        if ef is None:
            missing.append(category)
    assert not missing, (
        "These classifier categories could not find any matching EEIO row: "
        + ", ".join(missing)
    )
