"""Tests for the data quality analysis engine."""

from hemera.services.data_quality import (
    detect_vague_codes,
    compute_uncertainty_contributors,
    compute_cascade_distribution,
    compute_pedigree_breakdown,
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


# --- Task 3: Cascade Distribution and Pedigree Breakdown ---

def test_cascade_distribution_sums_to_100(sample_transactions):
    result = compute_cascade_distribution(sample_transactions)
    spend_total = sum(result["current_by_spend_pct"].values())
    assert abs(spend_total - 100.0) < 0.1


def test_cascade_distribution_has_target(sample_transactions):
    result = compute_cascade_distribution(sample_transactions)
    assert "target_by_spend_pct" in result
    assert result["target_by_spend_pct"]["L2"] == 30


def test_cascade_all_level_4(sample_transactions):
    result = compute_cascade_distribution(sample_transactions)
    assert result["current_by_spend_pct"]["L4"] > 50


def test_pedigree_breakdown_contributions_sum_to_100(sample_transactions):
    result = compute_pedigree_breakdown(sample_transactions)
    total = sum(v["contribution_pct"] for v in result.values())
    assert abs(total - 100.0) < 0.1


def test_pedigree_reliability_dominates(sample_transactions):
    """Reliability scores of 3-4 (GSD 1.61-1.69) produce more variance than
    technological scores of 4-5 (GSD 1.21-1.35) in the sample fixture."""
    result = compute_pedigree_breakdown(sample_transactions)
    assert result["reliability"]["contribution_pct"] > result["technological"]["contribution_pct"]
