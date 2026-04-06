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
        if value is None or value == 0:
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
