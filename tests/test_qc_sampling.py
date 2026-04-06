"""Tests for QC sampling engine."""
import pytest
from hemera.services.qc_sampling import calculate_sample_size


@pytest.mark.parametrize("population,expected_sample", [
    (50, 44), (100, 80), (250, 152), (500, 217), (1000, 278), (5000, 357),
])
def test_sample_size_matches_methodology_table(population, expected_sample):
    result = calculate_sample_size(population)
    assert result == expected_sample, f"For N={population}: expected {expected_sample}, got {result}"


def test_sample_size_small_population():
    assert calculate_sample_size(5) == 5
    assert calculate_sample_size(1) == 1


def test_sample_size_zero_population():
    assert calculate_sample_size(0) == 0


from hemera.services.qc_sampling import select_sample, compute_sampling_weight, get_sampling_reasons


def test_compute_weight_base(sample_transactions):
    gas_txn = sample_transactions[5]  # 1500 GBP, keyword, 0.95, L4
    weights = compute_sampling_weight(gas_txn, top_10_threshold=5000.0)
    assert weights["base"] == 1.0
    assert weights["total"] == 1.0


def test_compute_weight_high_spend(sample_transactions):
    catering_txn = sample_transactions[4]  # 8000 GBP
    weights = compute_sampling_weight(catering_txn, top_10_threshold=5000.0)
    assert weights["high_value"] == 2.0
    assert weights["total"] >= 2.0


def test_compute_weight_unclassified(sample_transactions):
    unclassified_txn = sample_transactions[2]  # method="none"
    weights = compute_sampling_weight(unclassified_txn, top_10_threshold=50000.0)
    assert weights["low_confidence"] == 2.0
    assert weights["total"] >= 2.0


def test_compute_weight_high_uncertainty_ef(sample_transactions):
    l5_txn = sample_transactions[2]  # ef_level=5
    weights = compute_sampling_weight(l5_txn, top_10_threshold=50000.0)
    assert weights["high_uncertainty_ef"] == 2.0


def test_select_sample_correct_size(sample_transactions):
    sample = select_sample(sample_transactions, engagement_id=1)
    expected_size = calculate_sample_size(len(sample_transactions))
    assert len(sample) == expected_size


def test_select_sample_deterministic(sample_transactions):
    sample1 = select_sample(sample_transactions, engagement_id=42)
    sample2 = select_sample(sample_transactions, engagement_id=42)
    ids1 = [t.row_number for t in sample1]
    ids2 = [t.row_number for t in sample2]
    assert ids1 == ids2


def test_select_sample_different_seed(sample_transactions):
    sample1 = select_sample(sample_transactions, engagement_id=1)
    sample2 = select_sample(sample_transactions, engagement_id=2)
    assert len(sample1) == len(sample2)


def test_get_sampling_reasons_high_spend(sample_transactions):
    catering_txn = sample_transactions[4]
    reasons = get_sampling_reasons(catering_txn, top_10_threshold=5000.0)
    assert any("High-spend" in r for r in reasons)


def test_get_sampling_reasons_unclassified(sample_transactions):
    txn = sample_transactions[2]
    reasons = get_sampling_reasons(txn, top_10_threshold=50000.0)
    assert any("Low-confidence" in r for r in reasons)


def test_get_sampling_reasons_routine(sample_transactions):
    gas_txn = sample_transactions[5]
    reasons = get_sampling_reasons(gas_txn, top_10_threshold=50000.0)
    assert reasons == ["Routine sample (proportional representation)"]


# ---------------------------------------------------------------------------
# Task 2: QC Card Builder
# ---------------------------------------------------------------------------

from hemera.services.qc_sampling import build_qc_card, build_qc_cards


def test_build_qc_card_has_all_sections(sample_transactions):
    txn = sample_transactions[0]
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=5000.0)
    assert card["card_number"] == 1
    assert card["total_cards"] == 6
    assert card["remaining"] == 6
    assert "sampling_reasons" in card
    assert "raw_data" in card
    assert "decisions" in card
    assert "checks" in card


def test_build_qc_card_raw_data(sample_transactions):
    txn = sample_transactions[0]
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=50000.0)
    raw = card["raw_data"]
    assert raw["row_number"] == 1
    assert raw["raw_description"] == "Office bits"
    assert raw["raw_supplier"] == "Generic Supplies Ltd"
    assert raw["raw_amount"] == 5000.0
    assert raw["raw_category"] == "Sundries"


def test_build_qc_card_decisions(sample_transactions):
    txn = sample_transactions[0]
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=50000.0)
    decisions = card["decisions"]
    assert decisions["classification"]["scope"] == 3
    assert decisions["classification"]["category_name"] == "Purchased goods — office supplies"
    assert decisions["emission_factor"]["source"] == "defra"
    assert decisions["emission_factor"]["level"] == 4
    assert decisions["calculation"]["arithmetic_verified"] is True
    assert decisions["pedigree"]["gsd_total"] == 1.82


def test_build_qc_card_arithmetic_flag(sample_transactions):
    txn = sample_transactions[0]  # 5000 * 0.5 = 2500
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=50000.0)
    assert card["decisions"]["calculation"]["arithmetic_verified"] is True


def test_build_qc_card_checks_list(sample_transactions):
    txn = sample_transactions[0]
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=50000.0)
    assert card["checks"] == ["classification", "emission_factor", "arithmetic", "supplier_match", "pedigree"]


def test_build_qc_cards_numbering(sample_transactions):
    cards = build_qc_cards(sample_transactions, top_10_threshold=5000.0)
    for i, card in enumerate(cards, 1):
        assert card["card_number"] == i
        assert card["total_cards"] == len(sample_transactions)
        assert card["remaining"] == len(sample_transactions) - i + 1


# ---------------------------------------------------------------------------
# Task 3: Error Rate and Hard Gate
# ---------------------------------------------------------------------------

import json
from hemera.services.qc_sampling import compute_qc_status, apply_qc_result, HARD_GATE_THRESHOLD


def test_compute_qc_status_not_started(sample_transactions):
    status = compute_qc_status(sample_transactions)
    assert status["status"] == "not_started"
    assert status["sample_size"] == 0


def test_compute_qc_status_in_progress(sample_transactions, db):
    sample_transactions[0].is_sampled = True
    sample_transactions[1].is_sampled = True
    sample_transactions[0].qc_pass = True
    db.flush()
    status = compute_qc_status(sample_transactions)
    assert status["status"] == "in_progress"
    assert status["sample_size"] == 2
    assert status["reviewed_count"] == 1
    assert status["remaining_count"] == 1


def test_compute_qc_status_passed(sample_transactions, db):
    for t in sample_transactions[:3]:
        t.is_sampled = True
        t.qc_pass = True
    db.flush()
    status = compute_qc_status(sample_transactions)
    assert status["status"] == "passed"
    assert status["current_error_rate"] == 0.0
    assert status["hard_gate_result"] == "passed"


def test_compute_qc_status_failed(sample_transactions, db):
    for t in sample_transactions[:3]:
        t.is_sampled = True
    sample_transactions[0].qc_pass = True
    sample_transactions[1].qc_pass = True
    sample_transactions[2].qc_pass = False
    db.flush()
    status = compute_qc_status(sample_transactions)
    assert status["status"] == "failed"
    assert abs(status["current_error_rate"] - 1/3) < 0.01
    assert status["hard_gate_result"] == "failed"


def test_apply_qc_result_all_pass(sample_transactions, db):
    t = sample_transactions[0]
    t.is_sampled = True
    db.flush()
    result = {"classification_pass": True, "emission_factor_pass": True, "arithmetic_pass": True, "supplier_match_pass": True, "pedigree_pass": True, "notes": ""}
    apply_qc_result(t, result)
    assert t.qc_pass is True
    assert t.qc_notes is not None
    stored = json.loads(t.qc_notes)
    assert stored["classification_pass"] is True


def test_apply_qc_result_one_fail(sample_transactions, db):
    t = sample_transactions[0]
    t.is_sampled = True
    db.flush()
    result = {"classification_pass": True, "emission_factor_pass": True, "arithmetic_pass": True, "supplier_match_pass": True, "pedigree_pass": False, "notes": "Technological score wrong"}
    apply_qc_result(t, result)
    assert t.qc_pass is False
    stored = json.loads(t.qc_notes)
    assert stored["pedigree_pass"] is False
    assert stored["notes"] == "Technological score wrong"


# ---------------------------------------------------------------------------
# Task 4: API endpoints
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from hemera.database import Base, get_db
from hemera.main import app
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction


def _make_test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_engagement_with_transactions(session, count=20):
    eng = Engagement(org_name="QC Test SU", status="reviewing", transaction_count=count)
    session.add(eng)
    session.flush()
    for i in range(count):
        txn = Transaction(
            engagement_id=eng.id, row_number=i + 1,
            raw_description=f"Test item {i+1}", raw_supplier=f"Supplier {i+1}",
            raw_category="General", raw_amount=1000.0 + i * 100, amount_gbp=1000.0 + i * 100,
            scope=3, ghg_category=1, category_name="Purchased goods — office supplies",
            classification_method="keyword", classification_confidence=0.85,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2024, ef_region="UK",
            co2e_kg=(1000.0 + i * 100) * 0.5,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=1, pedigree_geographical=1, pedigree_technological=4,
            gsd_total=1.69,
        )
        session.add(txn)
    session.flush()
    return eng


def test_api_qc_generate():
    session = _make_test_session()
    def override_get_db():
        try: yield session
        finally: pass
    app.dependency_overrides[get_db] = override_get_db
    eng = _seed_engagement_with_transactions(session, count=20)
    client = TestClient(app)
    response = client.post(f"/api/engagements/{eng.id}/qc/generate")
    assert response.status_code == 200
    data = response.json()
    assert data["engagement_id"] == eng.id
    assert data["sample_size"] > 0
    assert data["population_size"] == 20
    assert len(data["cards"]) == data["sample_size"]
    assert data["cards"][0]["card_number"] == 1
    assert "sampling_reasons" in data["cards"][0]
    assert "raw_data" in data["cards"][0]
    assert "decisions" in data["cards"][0]
    app.dependency_overrides.clear()
    session.close()


def test_api_qc_generate_idempotent():
    session = _make_test_session()
    def override_get_db():
        try: yield session
        finally: pass
    app.dependency_overrides[get_db] = override_get_db
    eng = _seed_engagement_with_transactions(session, count=20)
    client = TestClient(app)
    r1 = client.post(f"/api/engagements/{eng.id}/qc/generate")
    r2 = client.post(f"/api/engagements/{eng.id}/qc/generate")
    assert r1.json()["sample_size"] == r2.json()["sample_size"]
    app.dependency_overrides.clear()
    session.close()


def test_api_qc_status():
    session = _make_test_session()
    def override_get_db():
        try: yield session
        finally: pass
    app.dependency_overrides[get_db] = override_get_db
    eng = _seed_engagement_with_transactions(session, count=10)
    client = TestClient(app)
    r = client.get(f"/api/engagements/{eng.id}/qc")
    assert r.status_code == 200
    assert r.json()["status"] == "not_started"
    client.post(f"/api/engagements/{eng.id}/qc/generate")
    r = client.get(f"/api/engagements/{eng.id}/qc")
    assert r.json()["status"] == "in_progress"
    app.dependency_overrides.clear()
    session.close()


def test_api_qc_submit_and_gate():
    session = _make_test_session()
    def override_get_db():
        try: yield session
        finally: pass
    app.dependency_overrides[get_db] = override_get_db
    eng = _seed_engagement_with_transactions(session, count=5)
    client = TestClient(app)
    gen_response = client.post(f"/api/engagements/{eng.id}/qc/generate")
    cards = gen_response.json()["cards"]
    for card in cards:
        r = client.post(f"/api/engagements/{eng.id}/qc/submit", json={
            "results": [{"transaction_id": card["transaction_id"],
                "classification_pass": True, "emission_factor_pass": True,
                "arithmetic_pass": True, "supplier_match_pass": True,
                "pedigree_pass": True, "notes": ""}]
        })
        assert r.status_code == 200
    status = client.get(f"/api/engagements/{eng.id}/qc").json()
    assert status["status"] == "passed"
    eng_refreshed = session.query(Engagement).filter(Engagement.id == eng.id).first()
    assert eng_refreshed.status == "delivered"
    app.dependency_overrides.clear()
    session.close()


def test_api_qc_submit_not_found():
    session = _make_test_session()
    def override_get_db():
        try: yield session
        finally: pass
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    r = client.post("/api/engagements/99999/qc/submit", json={
        "results": [{"transaction_id": 1, "classification_pass": True,
            "emission_factor_pass": True, "arithmetic_pass": True,
            "supplier_match_pass": True, "pedigree_pass": True, "notes": ""}]
    })
    assert r.status_code == 404
    app.dependency_overrides.clear()
    session.close()
