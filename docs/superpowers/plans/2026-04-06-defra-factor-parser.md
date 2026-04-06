# DEFRA Factor Parser & Seeder — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded approximate emission factors with exact values parsed from official DEFRA Excel workbooks at seed time.

**Architecture:** Two parsers (activity-based xlsx, spend-based ods) feed into a rewritten seeder. The DEFRA workbooks live in `data/defra/` and are parsed at runtime — no hardcoded factor values in Python code. Each factor traces back to a specific row in a government-published file.

**Tech Stack:** Python 3.14, openpyxl (xlsx), odfpy/pandas (ods), SQLAlchemy, pytest

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `hemera/services/defra_parser.py` | Create | Parse DEFRA xlsx flat files and EEIO ods files → list[dict] |
| `hemera/services/seed_factors.py` | Rewrite | Discover workbooks in data/defra/, call parsers, seed DB |
| `tests/test_defra_parser.py` | Create | Unit tests for both parsers + integration test for seeder |
| `data/defra/README.md` | Create | Provenance: source URLs, download dates, checksums |
| `data/defra/.gitkeep` | Create | Ensure directory tracked by git |

Existing files unchanged: `hemera/models/emission_factor.py`, `hemera/api/upload.py`, `hemera/services/emission_calc.py`, `tests/conftest.py`.

---

### Task 1: Data provenance README

**Files:**
- Create: `data/defra/README.md`

- [ ] **Step 1: Generate checksums for the downloaded workbooks**

```bash
cd data/defra && shasum -a 256 *.xlsx *.ods
```

- [ ] **Step 2: Write README.md with provenance**

Create `data/defra/README.md` with the following content (substitute actual checksums from step 1):

```markdown
# DEFRA Emission Factor Workbooks

Official UK Government emission factor datasets. These files are parsed at
seed time by `hemera/services/defra_parser.py`.

## Level 2 — Activity-Based (main DEFRA/DESNZ conversion factors)

Flat file format, designed for automated processing.

| File | Year | Source URL | SHA256 |
|------|------|-----------|--------|
| ghg-conversion-factors-2024-flat.xlsx | 2024 | https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024 | <checksum> |
| ghg-conversion-factors-2023-flat.xlsx | 2023 | https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2023 | <checksum> |

## Level 4 — Spend-Based EEIO (kgCO2e per GBP by SIC code)

| File | Year | Source URL | SHA256 |
|------|------|-----------|--------|
| eeio-factors-by-sic-2022.ods | 2022 | https://www.gov.uk/government/statistics/uks-carbon-footprint | <checksum> |

## Adding a new year

1. Download the flat file from gov.uk (the "for automatic processing" version)
2. Place in this directory with the naming convention: `ghg-conversion-factors-YYYY-flat.xlsx`
3. Update this README with the SHA256 checksum
4. Re-run the seeder: `.venv/bin/python -m hemera.services.seed_factors`
```

- [ ] **Step 3: Commit**

```bash
git add data/defra/README.md
git commit -m "docs: add DEFRA workbook provenance README with source URLs and checksums"
```

---

### Task 2: Activity-based parser — tests

**Files:**
- Create: `tests/test_defra_parser.py`

- [ ] **Step 1: Write failing tests for `parse_activity_factors`**

Create `tests/test_defra_parser.py`:

```python
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
        """Should have ~3300-3400 factors (kg CO2e rows only, no biogenic)."""
        assert 3000 < len(activity_factors_2024) < 4000

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_defra_parser.py -v
```

Expected: `ModuleNotFoundError: No module named 'hemera.services.defra_parser'`

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_defra_parser.py
git commit -m "test: add failing tests for DEFRA activity-based factor parser"
```

---

### Task 3: Activity-based parser — implementation

**Files:**
- Create: `hemera/services/defra_parser.py`

- [ ] **Step 1: Implement `parse_activity_factors`**

Create `hemera/services/defra_parser.py`:

```python
"""Parse official DEFRA/DESNZ emission factor workbooks.

Reads the flat-format xlsx files (activity-based, Level 2) and the EEIO
ODS file (spend-based, Level 4) into lists of dicts matching the
EmissionFactor model.

Sources:
  - Activity: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-{year}
  - EEIO:     https://www.gov.uk/government/statistics/uks-carbon-footprint
"""

from pathlib import Path
import openpyxl


# Rows with these scopes are excluded (biogenic CO2, not GHG Protocol)
_EXCLUDED_SCOPES = {"Outside of Scopes", "END", None}

# Only keep total CO2e rows, not individual gas breakdowns
_KEEP_GHG_UNIT = "kg CO2e"

# Map scope strings from the workbook to integers
_SCOPE_MAP = {
    "Scope 1": 1,
    "Scope 2": 2,
    "Scope 3": 3,
}


def parse_activity_factors(file_path: str, year: int) -> list[dict]:
    """Parse a DEFRA flat-format xlsx file into emission factor dicts.

    Args:
        file_path: Path to the flat-format xlsx workbook.
        year: The factor year (e.g. 2024).

    Returns:
        List of dicts with keys matching EmissionFactor model fields.
    """
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb["Factors by Category"]

    factors = []
    for row in ws.iter_rows(min_row=7, values_only=True):
        row_id, scope_str, l1, l2, l3, l4, col_text, uom, ghg_unit, value = row[:10]

        # Filter: only total kg CO2e, exclude biogenic/outside scopes
        if ghg_unit != _KEEP_GHG_UNIT:
            continue
        if scope_str in _EXCLUDED_SCOPES:
            continue
        if value is None:
            continue

        scope = _SCOPE_MAP.get(scope_str)
        if scope is None:
            continue

        # Build subcategory from the hierarchy levels below Level 1
        sub_parts = [p for p in (l2, l3, l4) if p]
        subcategory = " > ".join(sub_parts) if sub_parts else None

        # Build keywords from category hierarchy
        keyword_parts = [p for p in (l1, l2, l3, l4) if p]
        keywords = ",".join(p.lower() for p in keyword_parts)

        factors.append({
            "source": "defra",
            "category": l1,
            "subcategory": subcategory,
            "scope": scope,
            "factor_value": float(value),
            "unit": f"kgCO2e/{uom}",
            "factor_type": "activity",
            "year": year,
            "region": "UK",
            "keywords": keywords,
        })

    wb.close()
    return factors
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_defra_parser.py::TestParseActivityFactors -v
```

Expected: All 10 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add hemera/services/defra_parser.py
git commit -m "feat: add DEFRA activity-based factor parser (reads flat xlsx)"
```

---

### Task 4: EEIO spend-based parser — tests

**Files:**
- Modify: `tests/test_defra_parser.py`

- [ ] **Step 1: Add failing tests for `parse_eeio_factors`**

Append to `tests/test_defra_parser.py`:

```python
from hemera.services.defra_parser import parse_eeio_factors


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
```

- [ ] **Step 2: Run tests to verify new tests fail**

```bash
.venv/bin/python -m pytest tests/test_defra_parser.py::TestParseEeioFactors -v
```

Expected: `ImportError: cannot import name 'parse_eeio_factors'`

- [ ] **Step 3: Commit**

```bash
git add tests/test_defra_parser.py
git commit -m "test: add failing tests for DEFRA EEIO spend-based factor parser"
```

---

### Task 5: EEIO spend-based parser — implementation

**Files:**
- Modify: `hemera/services/defra_parser.py`

- [ ] **Step 1: Add `parse_eeio_factors` to `defra_parser.py`**

Add the following imports at the top of `hemera/services/defra_parser.py`:

```python
import pandas as pd
```

Then add this function after `parse_activity_factors`:

```python
def parse_eeio_factors(file_path: str, year: int) -> list[dict]:
    """Parse the DEFRA EEIO spend-based factors (kgCO2e per GBP by SIC code).

    Args:
        file_path: Path to the EEIO ODS file.
        year: The factor year (e.g. 2022).

    Returns:
        List of dicts with keys matching EmissionFactor model fields.
    """
    df = pd.read_excel(file_path, engine="odf", header=None)

    factors = []
    for _, row in df.iterrows():
        sic_code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
        description = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else None
        ghg_value = row.iloc[2]

        # Skip header/empty rows
        if sic_code is None or description is None:
            continue
        try:
            factor_value = float(ghg_value)
        except (ValueError, TypeError):
            continue

        keywords = description.lower()

        factors.append({
            "source": "defra-eeio",
            "category": description,
            "subcategory": sic_code,
            "scope": 3,
            "factor_value": factor_value,
            "unit": "kgCO2e/GBP",
            "factor_type": "spend",
            "year": year,
            "region": "UK",
            "keywords": keywords,
        })

    return factors
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_defra_parser.py -v
```

Expected: All 21 tests PASS (10 activity + 11 EEIO).

- [ ] **Step 3: Commit**

```bash
git add hemera/services/defra_parser.py
git commit -m "feat: add DEFRA EEIO spend-based factor parser (reads ODS by SIC code)"
```

---

### Task 6: Rewrite seeder — tests

**Files:**
- Modify: `tests/test_defra_parser.py`

- [ ] **Step 1: Add failing tests for the rewritten seeder**

Append to `tests/test_defra_parser.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_defra_parser.py::TestSeedEmissionFactors -v
```

Expected: FAIL — `seed_emission_factors()` doesn't accept `data_dir` parameter yet.

- [ ] **Step 3: Commit**

```bash
git add tests/test_defra_parser.py
git commit -m "test: add failing tests for rewritten emission factor seeder"
```

---

### Task 7: Rewrite seeder — implementation

**Files:**
- Rewrite: `hemera/services/seed_factors.py`

- [ ] **Step 1: Rewrite `seed_factors.py`**

Replace the entire contents of `hemera/services/seed_factors.py` with:

```python
"""Seed the emission_factors table from official DEFRA workbooks.

Parses workbooks from data/defra/ at runtime — no hardcoded factor values.
Every factor traces back to a specific row in a government-published file.

Sources:
  - Activity-based (Level 2): DEFRA/DESNZ GHG Conversion Factors flat files
  - Spend-based (Level 4): DEFRA EEIO factors by SIC code
"""

import re
from pathlib import Path
from sqlalchemy.orm import Session
from hemera.models.emission_factor import EmissionFactor
from hemera.services.defra_parser import parse_activity_factors, parse_eeio_factors


# Default location for DEFRA workbooks
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "defra"

# Pattern to extract year from activity flat file names
_ACTIVITY_FILE_PATTERN = re.compile(
    r"ghg-conversion-factors-(\d{4})-flat.*\.xlsx$"
)

# Pattern to extract year from EEIO file names
_EEIO_FILE_PATTERN = re.compile(
    r"eeio-factors-by-sic-(\d{4})\.ods$"
)


def seed_emission_factors(db: Session, data_dir: str | Path | None = None) -> int:
    """Seed emission factors from DEFRA workbooks in data_dir.

    Discovers workbooks by filename convention, parses them, and replaces
    all existing DEFRA-sourced factors in the database.

    Args:
        db: SQLAlchemy session.
        data_dir: Directory containing DEFRA workbooks. Defaults to data/defra/.

    Returns:
        Count of factors inserted.
    """
    data_path = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR

    if not data_path.exists():
        return 0

    all_factors: list[dict] = []

    # Discover and parse activity-based flat files
    for f in sorted(data_path.iterdir()):
        match = _ACTIVITY_FILE_PATTERN.search(f.name)
        if match:
            year = int(match.group(1))
            all_factors.extend(parse_activity_factors(str(f), year))

    # Discover and parse EEIO files
    for f in sorted(data_path.iterdir()):
        match = _EEIO_FILE_PATTERN.search(f.name)
        if match:
            year = int(match.group(1))
            all_factors.extend(parse_eeio_factors(str(f), year))

    if not all_factors:
        return 0

    # Replace all existing DEFRA-sourced factors
    db.query(EmissionFactor).filter(
        EmissionFactor.source.in_(["defra", "defra-eeio"])
    ).delete(synchronize_session=False)

    count = 0
    for f in all_factors:
        ef = EmissionFactor(
            source=f["source"],
            category=f["category"],
            subcategory=f.get("subcategory"),
            scope=f["scope"],
            factor_value=f["factor_value"],
            unit=f["unit"],
            factor_type=f["factor_type"],
            year=f["year"],
            region=f["region"],
            keywords=f.get("keywords"),
        )
        db.add(ef)
        count += 1

    db.commit()
    return count


if __name__ == "__main__":
    from hemera.database import SessionLocal
    db = SessionLocal()
    try:
        n = seed_emission_factors(db)
        print(f"Seeded {n} emission factors from DEFRA workbooks.")
    finally:
        db.close()
```

- [ ] **Step 2: Run seeder tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_defra_parser.py::TestSeedEmissionFactors -v
```

Expected: All 5 seeder tests PASS.

- [ ] **Step 3: Run all new tests together**

```bash
.venv/bin/python -m pytest tests/test_defra_parser.py -v
```

Expected: All 26 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add hemera/services/seed_factors.py
git commit -m "feat: rewrite seeder to parse DEFRA workbooks at runtime — no hardcoded values"
```

---

### Task 8: Regression — ensure existing tests still pass

**Files:** None modified — verification only.

- [ ] **Step 1: Run the full test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: All 75 existing tests + 26 new tests = 101 tests PASS.

If any existing tests fail, it will likely be because they relied on the old hardcoded factors being present without workbook files. The `conftest.py` fixtures create transactions with pre-set `ef_value` fields, so they should be unaffected. But the upload endpoint calls `seed_emission_factors(db)` — if tests hit that path, they'll need `data/defra/` to exist.

Check: if upload-related tests fail, the fix is to ensure the test creates the DB fixtures directly (which `conftest.py` already does) rather than going through the upload endpoint.

- [ ] **Step 2: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: update tests for new DEFRA workbook-based seeder"
```

---

### Task 9: Update .gitignore for xlsx/ods data files

**Files:**
- Modify: `.gitignore`

The commit `794d77b` added xlsx to gitignore. The DEFRA workbooks in `data/defra/` need to be tracked.

- [ ] **Step 1: Check current gitignore**

```bash
cat .gitignore | grep -i xls
```

- [ ] **Step 2: Update .gitignore to allow data/defra/ files**

If xlsx/xls/ods are gitignored globally, add an exception:

```gitignore
# Allow DEFRA workbooks (official government data, needed for seeding)
!data/defra/*.xlsx
!data/defra/*.xls
!data/defra/*.ods
```

- [ ] **Step 3: Add the DEFRA workbook files to git**

```bash
git add data/defra/ghg-conversion-factors-2024-flat.xlsx
git add data/defra/ghg-conversion-factors-2023-flat.xlsx
git add data/defra/eeio-factors-by-sic-2022.ods
git add .gitignore
git commit -m "feat: add official DEFRA workbooks to repo and update gitignore"
```

---

### Task 10: Final verification and cleanup

- [ ] **Step 1: Run the seeder manually against local Postgres**

```bash
.venv/bin/python -m hemera.services.seed_factors
```

Expected output: `Seeded NNNN emission factors from DEFRA workbooks.` where NNNN is ~6800+ (2 years of activity + EEIO).

- [ ] **Step 2: Verify factors in the database**

```bash
.venv/bin/python -c "
from hemera.database import SessionLocal
from hemera.models.emission_factor import EmissionFactor
db = SessionLocal()
print('Total:', db.query(EmissionFactor).count())
for source, in db.query(EmissionFactor.source).distinct():
    count = db.query(EmissionFactor).filter(EmissionFactor.source == source).count()
    print(f'  {source}: {count}')
for year, in db.query(EmissionFactor.year).distinct().order_by(EmissionFactor.year):
    count = db.query(EmissionFactor).filter(EmissionFactor.year == year).count()
    print(f'  {year}: {count}')
db.close()
"
```

- [ ] **Step 3: Run full test suite one final time**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 4: Final commit if any small fixes**

```bash
git add -A
git commit -m "chore: final cleanup after DEFRA factor parser implementation"
```
