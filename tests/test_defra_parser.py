"""Tests for DEFRA workbook parsers."""

import os
import pytest
from hemera.services.defra_parser import parse_activity_factors


DEFRA_2024_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "defra",
    "ghg-conversion-factors-2024-flat.xlsx",
)


@pytest.fixture
def activity_factors_2024():
    """Parse the real 2024 DEFRA flat file."""
    return parse_activity_factors(DEFRA_2024_PATH, 2024)


class TestParseActivityFactors:
    def test_returns_list_of_dicts(self, activity_factors_2024):
        assert isinstance(activity_factors_2024, list)
        assert len(activity_factors_2024) > 0
        assert isinstance(activity_factors_2024[0], dict)

    def test_expected_row_count(self, activity_factors_2024):
        """Should have ~2500-2700 factors (kg CO2e rows only, no biogenic, no zero values)."""
        assert 2000 < len(activity_factors_2024) < 3000

    def test_no_individual_gas_breakdowns(self, activity_factors_2024):
        """Should only have total kg CO2e, not per-gas breakdowns."""
        units = {f["unit"] for f in activity_factors_2024}
        for u in units:
            assert "CO2 per unit" not in u
            assert "CH4 per unit" not in u
            assert "N2O per unit" not in u

    def test_no_outside_of_scopes(self, activity_factors_2024):
        """Biogenic (outside of scopes) should be excluded."""
        scopes = {f["scope"] for f in activity_factors_2024}
        assert all(s in (1, 2, 3) for s in scopes)

    def test_natural_gas_cubic_metres(self, activity_factors_2024):
        """Spot-check: natural gas in cubic metres = 2.04542 kgCO2e/m3."""
        matches = [
            f for f in activity_factors_2024
            if f["category"] == "Fuels"
            and "Natural gas" in (f["subcategory"] or "")
            and f["unit"] == "kgCO2e/cubic metres"
        ]
        assert len(matches) >= 1
        gas = matches[0]
        assert gas["factor_value"] == pytest.approx(2.04542, abs=0.001)
        assert gas["scope"] == 1
        assert gas["factor_type"] == "activity"
        assert gas["year"] == 2024
        assert gas["region"] == "UK"
        assert gas["source"] == "defra"

    def test_uk_electricity(self, activity_factors_2024):
        """Spot-check: UK electricity = 0.20705 kgCO2e/kWh."""
        matches = [
            f for f in activity_factors_2024
            if f["category"] == "UK electricity"
            and f["scope"] == 2
        ]
        assert len(matches) == 1
        elec = matches[0]
        assert elec["factor_value"] == pytest.approx(0.20705, abs=0.0001)
        assert elec["unit"] == "kgCO2e/kWh"

    def test_diesel_litres(self, activity_factors_2024):
        """Spot-check: diesel (avg biofuel) in litres = 2.51279 kgCO2e/litre."""
        matches = [
            f for f in activity_factors_2024
            if "Diesel (average biofuel blend)" in (f["subcategory"] or "")
            and f["unit"] == "kgCO2e/litres"
            and f["scope"] == 1
        ]
        assert len(matches) == 1
        assert matches[0]["factor_value"] == pytest.approx(2.51279, abs=0.001)

    def test_petrol_litres(self, activity_factors_2024):
        """Spot-check: petrol (avg biofuel) in litres = 2.0844 kgCO2e/litre."""
        matches = [
            f for f in activity_factors_2024
            if "Petrol (average biofuel blend)" in (f["subcategory"] or "")
            and f["unit"] == "kgCO2e/litres"
            and f["scope"] == 1
        ]
        assert len(matches) == 1
        assert matches[0]["factor_value"] == pytest.approx(2.0844, abs=0.001)

    def test_all_factors_have_required_fields(self, activity_factors_2024):
        required = {"source", "category", "scope", "factor_value", "unit",
                     "factor_type", "year", "region"}
        for f in activity_factors_2024:
            missing = required - set(f.keys())
            assert not missing, f"Missing fields {missing} in {f['category']}"

    def test_all_factor_values_positive(self, activity_factors_2024):
        for f in activity_factors_2024:
            assert f["factor_value"] > 0, f"Non-positive factor: {f}"
