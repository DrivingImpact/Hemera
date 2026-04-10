"""Tests for HemeraScope models — findings, selections, actions, AI tasks, supplier engagements."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hemera.database import Base
from hemera.models.supplier import Supplier
from hemera.models.engagement import Engagement
from hemera.models.finding import SupplierFinding, ReportSelection, ReportAction
from hemera.models.ai_task import AITask
from hemera.models.supplier_engagement import SupplierEngagement


@pytest.fixture
def db():
    """In-memory SQLite session for HemeraScope model tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_supplier(db):
    s = Supplier(
        hemera_id="hs-test-001",
        name="Acme Corp",
        hemera_score=72.5,
        hemera_verified=False,
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def sample_engagement(db):
    e = Engagement(org_name="Test Client", status="delivered")
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def sample_ai_task(db):
    t = AITask(
        task_type="finding_generation",
        target_type="supplier",
        target_id=1,
        mode="auto",
        status="completed",
        prompt_text="Generate findings for supplier",
        response_text='{"findings": []}',
        token_count=150,
        cost_usd=0.003,
    )
    db.add(t)
    db.flush()
    return t


def test_supplier_finding_creation(db, sample_supplier, sample_ai_task):
    """SupplierFinding can be created with all fields and links to supplier + ai_task."""
    finding = SupplierFinding(
        supplier_id=sample_supplier.id,
        ai_task_id=sample_ai_task.id,
        domain="carbon_climate",
        title="No carbon reduction targets set",
        summary="Supplier has not disclosed any SBTi or internal carbon targets.",
        severity="high",
        confidence=0.85,
        source_layers=[4, 6],
        is_active=True,
    )
    db.add(finding)
    db.flush()

    assert finding.id is not None
    assert finding.supplier_id == sample_supplier.id
    assert finding.ai_task_id == sample_ai_task.id
    assert finding.domain == "carbon_climate"
    assert finding.severity == "high"
    assert finding.confidence == 0.85
    assert finding.is_active is True

    # Check relationship from supplier
    db.refresh(sample_supplier)
    assert len(sample_supplier.findings) == 1
    assert sample_supplier.findings[0].title == "No carbon reduction targets set"


def test_report_selection_unique_constraint(db, sample_supplier, sample_engagement, sample_ai_task):
    """ReportSelection enforces unique (engagement_id, finding_id)."""
    finding = SupplierFinding(
        supplier_id=sample_supplier.id,
        ai_task_id=sample_ai_task.id,
        domain="governance_identity",
        title="Test finding",
        summary="A test finding",
        severity="medium",
        confidence=0.7,
        is_active=True,
    )
    db.add(finding)
    db.flush()

    sel1 = ReportSelection(
        engagement_id=sample_engagement.id,
        finding_id=finding.id,
        included=True,
        selected_by="admin@hemera.co",
    )
    db.add(sel1)
    db.flush()

    # Duplicate should violate unique constraint
    sel2 = ReportSelection(
        engagement_id=sample_engagement.id,
        finding_id=finding.id,
        included=False,
        selected_by="other@hemera.co",
    )
    db.add(sel2)
    with pytest.raises(Exception):  # IntegrityError
        db.flush()
    db.rollback()


def test_ai_task_creation(db):
    """AITask can be created with all fields."""
    task = AITask(
        task_type="report_narrative",
        target_type="engagement",
        target_id=42,
        mode="manual",
        status="pending",
        prompt_text="Write executive summary",
        prompt_hash="abc123",
    )
    db.add(task)
    db.flush()

    assert task.id is not None
    assert task.task_type == "report_narrative"
    assert task.target_type == "engagement"
    assert task.target_id == 42
    assert task.mode == "manual"
    assert task.status == "pending"
    assert task.created_at is not None


def test_supplier_engagement_creation(db, sample_supplier):
    """SupplierEngagement can be created and links to supplier."""
    eng = SupplierEngagement(
        supplier_id=sample_supplier.id,
        engagement_type="data_request",
        subject="Carbon data collection",
        status="sent",
        contact_name="Jane Doe",
        contact_email="jane@acme.com",
        notes="Initial outreach for Scope 3 data",
        created_by="admin@hemera.co",
    )
    db.add(eng)
    db.flush()

    assert eng.id is not None
    assert eng.supplier_id == sample_supplier.id
    assert eng.engagement_type == "data_request"
    assert eng.status == "sent"

    # Check relationship from supplier
    db.refresh(sample_supplier)
    assert len(sample_supplier.hemera_engagements) == 1
    assert sample_supplier.hemera_engagements[0].subject == "Carbon data collection"


def test_report_action_creation(db, sample_engagement, sample_ai_task):
    """ReportAction can be created with all fields."""
    action = ReportAction(
        engagement_id=sample_engagement.id,
        ai_task_id=sample_ai_task.id,
        action_type="narrative",
        section="executive_summary",
        content="The supplier portfolio shows...",
        status="approved",
        approved_by="admin@hemera.co",
    )
    db.add(action)
    db.flush()

    assert action.id is not None
    assert action.engagement_id == sample_engagement.id
    assert action.action_type == "narrative"
    assert action.status == "approved"

    # Check relationship from engagement
    db.refresh(sample_engagement)
    assert len(sample_engagement.report_actions) == 1


def test_supplier_hemera_score_rename(db):
    """Supplier model uses hemera_score (not esg_score) and has hemera_verified."""
    s = Supplier(
        hemera_id="hs-rename-001",
        name="Rename Test Ltd",
        hemera_score=88.0,
        hemera_verified=True,
    )
    db.add(s)
    db.flush()

    assert s.hemera_score == 88.0
    assert s.hemera_verified is True
    assert not hasattr(s, "esg_score")


def test_engagement_supplier_report_fields(db):
    """Engagement model has supplier_report_status and supplier_report_exec_summary."""
    e = Engagement(
        org_name="Report Test Client",
        status="delivered",
        supplier_report_status="generated",
        supplier_report_exec_summary="Portfolio of 45 suppliers assessed...",
    )
    db.add(e)
    db.flush()

    assert e.supplier_report_status == "generated"
    assert e.supplier_report_exec_summary == "Portfolio of 45 suppliers assessed..."

    # Check report_selections relationship exists
    assert hasattr(e, "report_selections")
    assert hasattr(e, "report_actions")
