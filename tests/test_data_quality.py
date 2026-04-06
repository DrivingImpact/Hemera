"""Tests for the data quality analysis engine."""

from hemera.services.data_quality import (
    detect_vague_codes,
    compute_uncertainty_contributors,
)


def test_detect_vague_codes(sample_transactions):
    """Sundries and Miscellaneous should be flagged as vague."""
    result = detect_vague_codes(sample_transactions)
    assert len(result) == 2
    sundries = next(r for r in result if r["raw_category"] == "Sundries")
    assert sundries["transaction_count"] == 2
    assert sundries["spend_gbp"] == 8000.0
    assert set(sundries["classified_as"]) == {
        "Purchased goods — office supplies",
        "Purchased goods — IT equipment",
    }
    misc = next(r for r in result if r["raw_category"] == "Miscellaneous")
    assert misc["transaction_count"] == 1
    assert misc["spend_gbp"] == 1000.0


def test_well_classified_not_flagged(sample_transactions):
    """Utilities with high confidence should not be flagged."""
    result = detect_vague_codes(sample_transactions)
    raw_cats = [r["raw_category"] for r in result]
    assert "Utilities" not in raw_cats
    assert "Catering" not in raw_cats


# --- Task 2: Uncertainty Contribution Decomposition ---

def test_uncertainty_contributors_sum_to_100(sample_transactions):
    result = compute_uncertainty_contributors(sample_transactions)
    total_pct = sum(r["uncertainty_contribution_pct"] for r in result)
    assert abs(total_pct - 100.0) < 0.1


def test_uncertainty_contributors_ranked_descending(sample_transactions):
    result = compute_uncertainty_contributors(sample_transactions)
    pcts = [r["uncertainty_contribution_pct"] for r in result]
    assert pcts == sorted(pcts, reverse=True)


def test_uncertainty_contributors_fields(sample_transactions):
    result = compute_uncertainty_contributors(sample_transactions)
    assert len(result) > 0
    first = result[0]
    for field in ["raw_category", "transaction_count", "spend_gbp", "co2e_kg", "avg_gsd", "uncertainty_contribution_pct", "dominant_pedigree_indicator"]:
        assert field in first
