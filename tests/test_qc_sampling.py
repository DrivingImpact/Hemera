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
