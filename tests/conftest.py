"""Shared test fixtures — in-memory SQLite database and sample transactions."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hemera.database import Base
from hemera.models.transaction import Transaction
from hemera.models.engagement import Engagement
from hemera.models.supplier import Supplier
from hemera.models.emission_factor import EmissionFactor


@pytest.fixture
def db():
    """In-memory SQLite session for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_engagement(db):
    e = Engagement(
        org_name="Test SU",
        status="delivered",
        transaction_count=6,
        total_co2e=5.0,
        gsd_total=1.5,
    )
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def sample_transactions(db, sample_engagement):
    txns = [
        Transaction(
            engagement_id=sample_engagement.id, row_number=1,
            raw_description="Office bits", raw_supplier="Generic Supplies Ltd",
            raw_category="Sundries", raw_amount=5000.0, amount_gbp=5000.0,
            scope=3, ghg_category=1, category_name="Purchased goods — office supplies",
            classification_method="keyword", classification_confidence=0.5,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2022, ef_region="UK", co2e_kg=2500.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=2, pedigree_geographical=1, pedigree_technological=4,
            gsd_total=1.82,
        ),
        Transaction(
            engagement_id=sample_engagement.id, row_number=2,
            raw_description="Computer stuff", raw_supplier="Tech World",
            raw_category="Sundries", raw_amount=3000.0, amount_gbp=3000.0,
            scope=3, ghg_category=1, category_name="Purchased goods — IT equipment",
            classification_method="keyword", classification_confidence=0.6,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2022, ef_region="UK", co2e_kg=1500.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=2, pedigree_geographical=1, pedigree_technological=4,
            gsd_total=1.82,
        ),
        Transaction(
            engagement_id=sample_engagement.id, row_number=3,
            raw_description="Payment ref 9921", raw_supplier="Unknown Co",
            raw_category="Miscellaneous", raw_amount=1000.0, amount_gbp=1000.0,
            scope=3, ghg_category=1, category_name="Unclassified — needs review",
            classification_method="none", classification_confidence=0.0,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=5, ef_year=2022, ef_region="UK", co2e_kg=500.0,
            pedigree_reliability=4, pedigree_completeness=4,
            pedigree_temporal=2, pedigree_geographical=1, pedigree_technological=5,
            gsd_total=2.1, needs_review=True,
        ),
        Transaction(
            engagement_id=sample_engagement.id, row_number=4,
            raw_description="Electricity bill Q1", raw_supplier="EDF Energy",
            raw_category="Utilities", raw_amount=2000.0, amount_gbp=2000.0,
            scope=2, ghg_category=None, category_name="Purchased electricity",
            classification_method="keyword", classification_confidence=0.95,
            ef_value=0.23, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2024, ef_region="UK", co2e_kg=460.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=1, pedigree_geographical=1, pedigree_technological=4,
            gsd_total=1.69,
        ),
        Transaction(
            engagement_id=sample_engagement.id, row_number=5,
            raw_description="Monthly catering", raw_supplier="Compass Group",
            raw_category="Catering", raw_amount=8000.0, amount_gbp=8000.0,
            scope=3, ghg_category=1, category_name="Purchased goods — catering/food",
            classification_method="keyword", classification_confidence=0.85,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2022, ef_region="UK", co2e_kg=4000.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=2, pedigree_geographical=1, pedigree_technological=4,
            gsd_total=1.82, supplier_id=None,
        ),
        Transaction(
            engagement_id=sample_engagement.id, row_number=6,
            raw_description="Gas bill", raw_supplier="British Gas",
            raw_category="Utilities", raw_amount=1500.0, amount_gbp=1500.0,
            scope=1, ghg_category=None, category_name="Stationary combustion — gas/heating fuel",
            classification_method="keyword", classification_confidence=0.95,
            ef_value=0.2, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2024, ef_region="UK", co2e_kg=300.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=1, pedigree_geographical=1, pedigree_technological=4,
            gsd_total=1.69,
        ),
    ]
    db.add_all(txns)
    db.flush()
    return txns
