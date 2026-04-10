# tests/test_hemerascope_models.py
"""Tests for HemeraScope data models."""
import pytest
from datetime import datetime
from hemera.database import Base, engine, SessionLocal
from hemera.models.finding import SupplierFinding, ReportSelection, ReportAction
from hemera.models.ai_task import AITask
from hemera.models.supplier_engagement import SupplierEngagement
from hemera.models.supplier import Supplier
from hemera.models.engagement import Engagement


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()


def test_supplier_finding_creation(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-123")
    db.add(supplier)
    db.flush()

    finding = SupplierFinding(
        supplier_id=supplier.id,
        source="deterministic",
        domain="governance",
        severity="high",
        title="Insolvency history detected",
        detail="Companies House records show insolvency proceedings in 2024.",
        layer=1,
        source_name="companies_house",
        is_active=True,
    )
    db.add(finding)
    db.flush()

    assert finding.id is not None
    assert finding.supplier_id == supplier.id
    assert finding.source == "deterministic"
    assert finding.severity == "high"
    assert finding.is_active is True


def test_report_selection_unique_constraint(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-456")
    db.add(supplier)
    db.flush()

    engagement = Engagement(org_name="Client A", contact_email="a@test.com")
    db.add(engagement)
    db.flush()

    finding = SupplierFinding(
        supplier_id=supplier.id,
        source="deterministic",
        domain="carbon",
        severity="medium",
        title="No SBTi target",
        detail="No Science Based Target found.",
        source_name="sbti",
        is_active=True,
    )
    db.add(finding)
    db.flush()

    sel1 = ReportSelection(
        engagement_id=engagement.id,
        finding_id=finding.id,
        included=True,
        selected_by=1,
    )
    db.add(sel1)
    db.flush()

    sel2 = ReportSelection(
        engagement_id=engagement.id,
        finding_id=finding.id,
        included=False,
        selected_by=1,
    )
    db.add(sel2)

    with pytest.raises(Exception):
        db.flush()


def test_ai_task_creation(db):
    task = AITask(
        task_type="risk_analysis",
        target_type="supplier",
        target_id=1,
        mode="manual",
        status="prompt_copied",
        prompt_text="Analyse this supplier...",
        prompt_hash="abc123",
    )
    db.add(task)
    db.flush()

    assert task.id is not None
    assert task.mode == "manual"
    assert task.status == "prompt_copied"
    assert task.response_text is None


def test_supplier_engagement_creation(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-789")
    db.add(supplier)
    db.flush()

    eng = SupplierEngagement(
        supplier_id=supplier.id,
        engagement_type="outreach",
        subject="SBTi Commitment Discussion",
        status="contacted",
        notes="Sent initial email to sustainability team.",
        contacted_at=datetime.utcnow(),
        created_by=1,
    )
    db.add(eng)
    db.flush()

    assert eng.id is not None
    assert eng.status == "contacted"


def test_report_action_creation(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-abc")
    db.add(supplier)
    db.flush()

    engagement = Engagement(org_name="Client B", contact_email="b@test.com")
    db.add(engagement)
    db.flush()

    action = ReportAction(
        engagement_id=engagement.id,
        supplier_id=supplier.id,
        action_text="Hemera can facilitate a supplier engagement session.",
        priority=1,
        linked_finding_ids=[1, 2],
        language_source="ai_automated",
        created_by=1,
    )
    db.add(action)
    db.flush()

    assert action.id is not None
    assert action.linked_finding_ids == [1, 2]


def test_supplier_hemera_score_rename(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-rename")
    supplier.hemera_score = 72.5
    db.add(supplier)
    db.flush()

    assert supplier.hemera_score == 72.5


def test_engagement_supplier_report_fields(db):
    engagement = Engagement(org_name="Client C", contact_email="c@test.com")
    engagement.supplier_report_status = "curating"
    engagement.supplier_report_exec_summary = "This report covers 24 suppliers..."
    db.add(engagement)
    db.flush()

    assert engagement.supplier_report_status == "curating"
    assert engagement.supplier_report_exec_summary.startswith("This report")
