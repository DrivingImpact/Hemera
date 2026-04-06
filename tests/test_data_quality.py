"""Tests for the data quality analysis engine."""

from hemera.services.data_quality import detect_vague_codes


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
