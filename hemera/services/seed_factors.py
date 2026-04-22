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
from hemera.services.defra_parser import parse_activity_factors, parse_eeio_factors, parse_full_set_factors


# Default location for DEFRA workbooks
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "defra"

# Pattern to extract year from activity flat file names
_ACTIVITY_FILE_PATTERN = re.compile(
    r"ghg-conversion-factors-(\d{4})-flat.*\.xlsx$"
)

# Pattern to extract year from full-set file names
_FULL_SET_FILE_PATTERN = re.compile(
    r"ghg-conversion-factors-(\d{4})-full-set\.xlsx$"
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

    # Discover and parse full-set files
    for f in sorted(data_path.iterdir()):
        match = _FULL_SET_FILE_PATTERN.search(f.name)
        if match:
            year = int(match.group(1))
            all_factors.extend(parse_full_set_factors(str(f), year))

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
            source_sheet=f.get("source_sheet"),
            source_row=f.get("source_row"),
            source_hierarchy=f.get("source_hierarchy"),
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
