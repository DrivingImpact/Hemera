"""Tests for the standalone processing pipeline."""

from unittest.mock import MagicMock, patch
import pytest
from hemera.services.pipeline import run_processing_pipeline


def _make_engagement(status="uploaded", engagement_id=1):
    e = MagicMock()
    e.id = engagement_id
    e.status = status
    return e


def _make_transaction(supplier="Acme Ltd", description="Invoice", category="Services"):
    t = MagicMock()
    t.raw_supplier = supplier
    t.raw_description = description
    t.raw_category = category
    return t


def _mock_calc_results():
    return {
        "total_co2e_tonnes": 10.0,
        "scope1_kg": 1000.0,
        "scope2_kg": 2000.0,
        "scope3_kg": 7000.0,
        "overall_gsd": 1.5,
        "ci_lower_tonnes": 7.0,
        "ci_upper_tonnes": 14.0,
        "transactions_calculated": 2,
        "transactions_missing_ef": 0,
    }


@patch("hemera.services.pipeline.seed_emission_factors")
@patch("hemera.services.pipeline.calculate_emissions")
@patch("hemera.services.pipeline.match_suppliers_batch")
@patch("hemera.services.pipeline.classify_transaction")
def test_pipeline_sets_status_to_delivered(
    mock_classify, mock_match, mock_calc, mock_seed
):
    """Pipeline should update engagement status to 'delivered' on success."""
    db = MagicMock()
    engagement = _make_engagement(status="uploaded")
    transactions = [_make_transaction()]

    mock_classify.return_value = None  # unclassified path
    mock_match.return_value = {}
    mock_calc.return_value = _mock_calc_results()

    result = run_processing_pipeline(engagement, transactions, db)

    assert engagement.status == "delivered"
    assert result["status"] == "delivered"
    db.commit.assert_called_once()


@patch("hemera.services.pipeline.seed_emission_factors")
@patch("hemera.services.pipeline.calculate_emissions")
@patch("hemera.services.pipeline.match_suppliers_batch")
@patch("hemera.services.pipeline.classify_transaction")
def test_pipeline_rejects_non_uploaded_status(
    mock_classify, mock_match, mock_calc, mock_seed
):
    """Pipeline should raise ValueError if engagement is not in 'uploaded' status."""
    db = MagicMock()
    engagement = _make_engagement(status="delivered")
    transactions = [_make_transaction()]

    with pytest.raises(ValueError, match="expected status 'uploaded'"):
        run_processing_pipeline(engagement, transactions, db)

    db.commit.assert_not_called()


@patch("hemera.services.pipeline.seed_emission_factors")
@patch("hemera.services.pipeline.calculate_emissions")
@patch("hemera.services.pipeline.match_suppliers_batch")
@patch("hemera.services.pipeline.classify_transaction")
def test_pipeline_rejects_processing_status(
    mock_classify, mock_match, mock_calc, mock_seed
):
    """Pipeline should also reject engagements already in 'processing' status."""
    db = MagicMock()
    engagement = _make_engagement(status="processing")
    transactions = [_make_transaction()]

    with pytest.raises(ValueError, match="expected status 'uploaded'"):
        run_processing_pipeline(engagement, transactions, db)


@patch("hemera.services.pipeline.seed_emission_factors")
@patch("hemera.services.pipeline.calculate_emissions")
@patch("hemera.services.pipeline.match_suppliers_batch")
@patch("hemera.services.pipeline.classify_transaction")
def test_pipeline_sets_processing_status_during_run(
    mock_classify, mock_match, mock_calc, mock_seed
):
    """Pipeline should set status to 'processing' before starting classification."""
    db = MagicMock()
    engagement = _make_engagement(status="uploaded")
    transactions = [_make_transaction()]

    status_during_classify = []

    def capture_status(*args, **kwargs):
        status_during_classify.append(engagement.status)
        return None

    mock_classify.side_effect = capture_status
    mock_match.return_value = {}
    mock_calc.return_value = _mock_calc_results()

    run_processing_pipeline(engagement, transactions, db)

    assert status_during_classify[0] == "processing"


@patch("hemera.services.pipeline.seed_emission_factors")
@patch("hemera.services.pipeline.calculate_emissions")
@patch("hemera.services.pipeline.match_suppliers_batch")
@patch("hemera.services.pipeline.classify_transaction")
def test_pipeline_returns_carbon_footprint_summary(
    mock_classify, mock_match, mock_calc, mock_seed
):
    """Pipeline return value should include carbon footprint totals."""
    db = MagicMock()
    engagement = _make_engagement(status="uploaded")
    transactions = [_make_transaction()]

    mock_classify.return_value = None
    mock_match.return_value = {}
    mock_calc.return_value = _mock_calc_results()

    result = run_processing_pipeline(engagement, transactions, db)

    assert result["carbon_footprint"]["total_tCO2e"] == 10.0
    assert result["carbon_footprint"]["scope1_tCO2e"] == 1.0
    assert result["carbon_footprint"]["scope2_tCO2e"] == 2.0
    assert result["carbon_footprint"]["scope3_tCO2e"] == 7.0
