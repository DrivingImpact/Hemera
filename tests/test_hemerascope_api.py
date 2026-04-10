"""Tests for HemeraScope API endpoints — findings, AI tasks, curation."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from hemera.main import app
from hemera.database import Base, get_db
from hemera.models.supplier import Supplier
from hemera.models.engagement import Engagement
from hemera.models.finding import SupplierFinding, ReportSelection
from hemera.models.ai_task import AITask
from hemera.models.supplier_engagement import SupplierEngagement
from hemera.models.transaction import Transaction
from hemera.services.clerk import ClerkUser


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


MOCK_ADMIN = ClerkUser(
    clerk_id="admin_1",
    email="admin@hemera.com",
    org_name="Hemera",
    role="admin",
)

AUTH_HEADERS = {"Authorization": "Bearer fake_token"}


@pytest.fixture
def session_and_client():
    session = _make_session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield session, client
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def supplier(session_and_client):
    session, _ = session_and_client
    s = Supplier(name="Test Corp", hemera_id="test-api-1", hemera_score=55.0)
    session.add(s)
    session.flush()
    return s


@pytest.fixture
def engagement(session_and_client):
    session, _ = session_and_client
    e = Engagement(org_name="Client A", contact_email="a@test.com", status="delivered")
    session.add(e)
    session.flush()
    return e


@pytest.fixture
def finding(session_and_client, supplier):
    session, _ = session_and_client
    f = SupplierFinding(
        supplier_id=supplier.id,
        source="deterministic",
        domain="governance",
        severity="high",
        title="Insolvency history",
        detail="Test detail",
        source_name="companies_house",
        is_active=True,
    )
    session.add(f)
    session.flush()
    return f


# -- Findings endpoints --

@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_get_supplier_findings(mock_auth, session_and_client, supplier, finding):
    _, client = session_and_client
    resp = client.get(f"/api/suppliers/{supplier.id}/findings", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Insolvency history"


@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_create_manual_finding(mock_auth, session_and_client, supplier):
    _, client = session_and_client
    resp = client.post(
        f"/api/suppliers/{supplier.id}/findings",
        json={
            "source": "ai_manual",
            "domain": "carbon",
            "severity": "medium",
            "title": "Unusual filing pattern",
            "detail": "High filing activity despite declining revenue.",
            "source_name": "analyst",
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Unusual filing pattern"


# -- AI Tasks endpoints --

@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_create_ai_task_manual_mode(mock_auth, session_and_client, supplier):
    _, client = session_and_client
    resp = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "risk_analysis",
            "target_type": "supplier",
            "target_id": supplier.id,
            "mode": "manual",
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "prompt_copied"
    assert data["prompt_text"] is not None
    assert len(data["prompt_text"]) > 100


@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_paste_back_ai_task(mock_auth, session_and_client, supplier):
    session, client = session_and_client
    task = AITask(
        task_type="client_language",
        target_type="supplier",
        target_id=supplier.id,
        mode="manual",
        status="prompt_copied",
        prompt_text="Test prompt",
        prompt_hash="abc",
    )
    session.add(task)
    session.flush()

    resp = client.patch(
        f"/api/ai-tasks/{task.id}",
        json={"response_text": '[{"original_title": "test", "client_title": "Test", "client_detail": "Detail"}]'},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


# -- Supplier Engagement endpoints --

@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_log_supplier_engagement(mock_auth, session_and_client, supplier):
    _, client = session_and_client
    resp = client.post(
        f"/api/suppliers/{supplier.id}/engagements",
        json={
            "engagement_type": "outreach",
            "subject": "SBTi Discussion",
            "status": "contacted",
            "notes": "Sent initial email.",
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 201
    assert resp.json()["subject"] == "SBTi Discussion"


@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_get_supplier_engagements(mock_auth, session_and_client, supplier):
    session, client = session_and_client
    eng = SupplierEngagement(
        supplier_id=supplier.id,
        engagement_type="meeting",
        subject="Review session",
        status="completed",
        created_by=1,
    )
    session.add(eng)
    session.flush()

    resp = client.get(f"/api/suppliers/{supplier.id}/engagements", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# -- HemeraScope curation endpoints --

@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_save_report_selection(mock_auth, session_and_client, engagement, finding):
    _, client = session_and_client
    resp = client.patch(
        f"/api/engagements/{engagement.id}/supplier-report/selections",
        json={
            "selections": [
                {"finding_id": finding.id, "included": True, "analyst_note": "Important for this client"},
            ],
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["saved"] == 1


@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_upsert_report_selection(mock_auth, session_and_client, engagement, finding):
    """Saving the same finding twice should upsert, not duplicate."""
    _, client = session_and_client

    # First save
    client.patch(
        f"/api/engagements/{engagement.id}/supplier-report/selections",
        json={"selections": [{"finding_id": finding.id, "included": True}]},
        headers=AUTH_HEADERS,
    )

    # Second save (update)
    resp = client.patch(
        f"/api/engagements/{engagement.id}/supplier-report/selections",
        json={"selections": [{"finding_id": finding.id, "included": False, "analyst_note": "Updated"}]},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200

    # Verify only one selection exists
    session, _ = session_and_client
    count = session.query(ReportSelection).filter(
        ReportSelection.engagement_id == engagement.id,
        ReportSelection.finding_id == finding.id,
    ).count()
    assert count == 1


@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_publish_report(mock_auth, session_and_client, engagement):
    _, client = session_and_client
    resp = client.post(
        f"/api/engagements/{engagement.id}/supplier-report/publish",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_supplier_report_with_transactions(mock_auth, session_and_client, engagement, supplier, finding):
    """Test the full curation endpoint with supplier linked via transactions."""
    session, client = session_and_client

    # Create a transaction linking supplier to engagement
    txn = Transaction(
        engagement_id=engagement.id,
        supplier_id=supplier.id,
        row_number=1,
        raw_description="Test purchase",
        raw_supplier="Test Corp",
        amount_gbp=1000.0,
        co2e_kg=50.0,
        is_duplicate=False,
    )
    session.add(txn)
    session.flush()

    resp = client.get(
        f"/api/engagements/{engagement.id}/supplier-report",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["supplier_count"] == 1
    assert data["suppliers"][0]["supplier"]["name"] == "Test Corp"
    assert len(data["suppliers"][0]["findings"]) >= 1


# -- Client-facing endpoint --

@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_supplier_intelligence_requires_published(mock_auth, session_and_client, engagement):
    """Should 404 if report not published."""
    _, client = session_and_client
    resp = client.get(
        f"/api/engagements/{engagement.id}/supplier-intelligence",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404


@patch("hemera.dependencies.verify_clerk_token", return_value=MOCK_ADMIN)
def test_supplier_intelligence_published(mock_auth, session_and_client, engagement, supplier, finding):
    """Published report should return client-facing data."""
    session, client = session_and_client

    # Set up: link supplier via transaction, publish report
    txn = Transaction(
        engagement_id=engagement.id,
        supplier_id=supplier.id,
        row_number=1,
        raw_description="Test",
        raw_supplier="Test Corp",
        amount_gbp=500.0,
        co2e_kg=25.0,
        is_duplicate=False,
    )
    session.add(txn)
    session.flush()

    # Include a finding and publish
    sel = ReportSelection(
        engagement_id=engagement.id,
        finding_id=finding.id,
        included=True,
        client_title="Client-friendly title",
        selected_by=1,
    )
    session.add(sel)
    engagement.supplier_report_status = "published"
    session.flush()

    resp = client.get(
        f"/api/engagements/{engagement.id}/supplier-intelligence",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "published"
    assert len(data["suppliers"]) == 1
    # Should use client_title
    assert data["suppliers"][0]["findings"][0]["title"] == "Client-friendly title"
    # Should not have internal notes in hemera_engagements
    for eng in data["suppliers"][0]["hemera_engagements"]:
        assert "notes" not in eng
