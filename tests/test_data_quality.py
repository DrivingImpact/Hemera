"""Tests for the data quality analysis engine."""

from hemera.services.data_quality import (
    detect_vague_codes,
    compute_uncertainty_contributors,
    compute_cascade_distribution,
    compute_pedigree_breakdown,
    compute_data_quality_grade,
    compute_summary,
    generate_recommendations,
    generate_data_quality_report,
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


# --- Task 4: Data Quality Grade and Summary ---

def test_grade_d_for_mostly_level4(sample_transactions):
    # Sample fixture has ~95% L4 + ~5% L5 = 100% L4+, which scores D (>80% L4+)
    cascade = compute_cascade_distribution(sample_transactions)
    grade = compute_data_quality_grade(cascade["current_by_spend_pct"])
    assert grade == "D"

def test_grade_a_for_high_l1_l2():
    dist = {"L1": 40, "L2": 25, "L3": 15, "L4": 15, "L5": 5, "L6": 0}
    assert compute_data_quality_grade(dist) == "A"

def test_grade_b_for_moderate_l1_l3():
    dist = {"L1": 15, "L2": 15, "L3": 15, "L4": 40, "L5": 15, "L6": 0}
    assert compute_data_quality_grade(dist) == "B"

def test_summary_has_all_fields(sample_transactions):
    result = compute_summary(sample_transactions)
    for field in ["overall_gsd", "ci_95_percent", "total_spend_gbp", "total_co2e_tonnes",
                  "data_quality_grade", "transactions_analysed", "vague_code_count",
                  "vague_code_spend_gbp", "vague_code_spend_pct"]:
        assert field in result, f"Missing field: {field}"


# --- Task 5: Recommendations Engine ---

def test_recommendations_include_chart_of_accounts(sample_transactions):
    recs = generate_recommendations(sample_transactions)
    coa_recs = [r for r in recs if r["type"] == "chart_of_accounts"]
    assert len(coa_recs) >= 1
    sundries_rec = next(r for r in coa_recs if r["current_code"] == "Sundries")
    assert set(sundries_rec["suggested_splits"]) == {
        "Purchased goods — office supplies",
        "Purchased goods — IT equipment",
    }
    assert sundries_rec["spend_gbp"] == 8000.0

def test_recommendations_include_activity_data(sample_transactions):
    recs = generate_recommendations(sample_transactions)
    act_recs = [r for r in recs if r["type"] == "activity_data"]
    elec = [r for r in act_recs if r["category"] == "Purchased electricity"]
    assert len(elec) == 1
    assert elec[0]["data_needed"] == "kWh from electricity bills or supplier portal"

def test_recommendations_include_gas_activity_data(sample_transactions):
    recs = generate_recommendations(sample_transactions)
    act_recs = [r for r in recs if r["type"] == "activity_data"]
    gas = [r for r in act_recs if "gas" in r["category"].lower() or "combustion" in r["category"].lower()]
    assert len(gas) == 1

def test_recommendations_ranked_by_impact(sample_transactions):
    recs = generate_recommendations(sample_transactions)
    scores = [r["impact_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)

def test_recommendations_have_required_fields(sample_transactions):
    recs = generate_recommendations(sample_transactions)
    for r in recs:
        assert "type" in r
        assert "rank" in r
        assert "impact_score" in r
        assert "explanation" in r


# --- Task 6: Full Report Assembly ---

def test_full_report_structure(sample_transactions, sample_engagement):
    report = generate_data_quality_report(sample_transactions, sample_engagement.id)
    assert report["engagement_id"] == sample_engagement.id
    assert "generated_at" in report
    assert "summary" in report
    assert "cascade_distribution" in report
    assert "uncertainty_contributors" in report
    assert "pedigree_breakdown" in report
    assert "recommendations" in report

def test_full_report_summary_grade(sample_transactions, sample_engagement):
    report = generate_data_quality_report(sample_transactions, sample_engagement.id)
    assert report["summary"]["data_quality_grade"] in ("A", "B", "C", "D", "E")
