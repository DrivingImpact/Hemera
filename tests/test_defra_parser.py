"""Tests for DEFRA workbook parsers."""

import os
import pytest
from hemera.services.defra_parser import parse_activity_factors, parse_eeio_factors


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


EEIO_2022_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "defra",
    "eeio-factors-by-sic-2022.ods",
)


@pytest.fixture
def eeio_factors_2022():
    """Parse the real EEIO ODS file."""
    return parse_eeio_factors(EEIO_2022_PATH, 2022)


class TestParseEeioFactors:
    def test_returns_list_of_dicts(self, eeio_factors_2022):
        assert isinstance(eeio_factors_2022, list)
        assert len(eeio_factors_2022) > 0

    def test_expected_row_count(self, eeio_factors_2022):
        """Should have ~110 SIC-code-level factors."""
        assert 100 < len(eeio_factors_2022) < 130

    def test_all_scope_3(self, eeio_factors_2022):
        for f in eeio_factors_2022:
            assert f["scope"] == 3

    def test_all_spend_type(self, eeio_factors_2022):
        for f in eeio_factors_2022:
            assert f["factor_type"] == "spend"
            assert f["unit"] == "kgCO2e/GBP"

    def test_source_is_defra_eeio(self, eeio_factors_2022):
        for f in eeio_factors_2022:
            assert f["source"] == "defra-eeio"

    def test_agriculture_factor(self, eeio_factors_2022):
        """Spot-check: SIC 01 agriculture = 2.633029 kgCO2e/GBP."""
        matches = [f for f in eeio_factors_2022 if f["subcategory"] == "01"]
        assert len(matches) == 1
        assert matches[0]["factor_value"] == pytest.approx(2.633029, abs=0.001)
        assert "agriculture" in matches[0]["category"].lower()

    def test_textiles_factor(self, eeio_factors_2022):
        """Spot-check: SIC 13 textiles = 0.782675 kgCO2e/GBP."""
        matches = [f for f in eeio_factors_2022 if f["subcategory"] == "13"]
        assert len(matches) == 1
        assert matches[0]["factor_value"] == pytest.approx(0.782675, abs=0.001)

    def test_domestic_personnel_factor(self, eeio_factors_2022):
        """Spot-check: SIC 97 (last row) = 0.045117 kgCO2e/GBP."""
        matches = [f for f in eeio_factors_2022 if f["subcategory"] == "97"]
        assert len(matches) == 1
        assert matches[0]["factor_value"] == pytest.approx(0.045117, abs=0.001)

    def test_all_factors_have_required_fields(self, eeio_factors_2022):
        required = {"source", "category", "subcategory", "scope", "factor_value",
                     "unit", "factor_type", "year", "region"}
        for f in eeio_factors_2022:
            missing = required - set(f.keys())
            assert not missing, f"Missing fields {missing} in {f['category']}"

    def test_all_factor_values_positive(self, eeio_factors_2022):
        for f in eeio_factors_2022:
            assert f["factor_value"] > 0, f"Non-positive factor: {f}"


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hemera.database import Base
from hemera.models.emission_factor import EmissionFactor
from hemera.services.seed_factors import seed_emission_factors


@pytest.fixture
def db():
    """In-memory SQLite session for seeder tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


DEFRA_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "defra")


class TestSeedEmissionFactors:
    def test_seeds_from_real_files(self, db):
        """Seeder should populate factors from workbooks in data/defra/."""
        count = seed_emission_factors(db, data_dir=DEFRA_DATA_DIR)
        assert count > 3000  # At least activity factors from one year

    def test_has_both_sources(self, db):
        """Should have both defra (activity) and defra-eeio (spend) factors."""
        seed_emission_factors(db, data_dir=DEFRA_DATA_DIR)
        sources = {
            r[0] for r in db.query(EmissionFactor.source).distinct().all()
        }
        assert "defra" in sources
        assert "defra-eeio" in sources

    def test_has_multiple_years(self, db):
        """Should have factors from 2023 and 2024 (activity-based)."""
        seed_emission_factors(db, data_dir=DEFRA_DATA_DIR)
        years = {
            r[0]
            for r in db.query(EmissionFactor.year)
            .filter(EmissionFactor.source == "defra")
            .distinct()
            .all()
        }
        assert 2024 in years
        assert 2023 in years

    def test_idempotent(self, db):
        """Running seeder twice should produce same count (replaces, not duplicates)."""
        count1 = seed_emission_factors(db, data_dir=DEFRA_DATA_DIR)
        count2 = seed_emission_factors(db, data_dir=DEFRA_DATA_DIR)
        assert count1 == count2
        total = db.query(EmissionFactor).count()
        assert total == count1

    def test_spot_check_uk_electricity_2024(self, db):
        """After seeding, UK electricity 2024 should be 0.20705 kgCO2e/kWh."""
        seed_emission_factors(db, data_dir=DEFRA_DATA_DIR)
        ef = (
            db.query(EmissionFactor)
            .filter(
                EmissionFactor.source == "defra",
                EmissionFactor.category == "UK electricity",
                EmissionFactor.year == 2024,
                EmissionFactor.scope == 2,
            )
            .first()
        )
        assert ef is not None
        assert ef.factor_value == pytest.approx(0.20705, abs=0.0001)
