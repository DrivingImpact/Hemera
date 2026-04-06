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
