# DEFRA Factor Parser & Seeder — Design Spec

**Date:** 2026-04-06
**Status:** Draft

## Problem

`hemera/services/seed_factors.py` contains ~25 hardcoded approximate emission factors with a comment saying "will be replaced with exact values from the workbook." This is insufficient for production use:

- Values are approximate (transcribed by hand, no traceability)
- Only 2024, no multi-year support
- Missing most activity-based factors (only 3 fuels + electricity)
- Spend-based factors use made-up categories instead of official SIC-code-based EEIO factors

## Solution

Parse the official DEFRA Excel workbooks at seed time. No hardcoded values — every factor traces back to a specific cell in a government-published file.

## Data Sources

### Level 2 — Activity-Based (main DEFRA workbook)

**Source:** UK Government GHG Conversion Factors for Company Reporting — Flat File format
**Publisher:** DEFRA/DESNZ via gov.uk
**URLs:**
- 2024: `https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024`
- 2023: `https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2023`

**Structure (per year):**
- Sheet: `Factors by Category`
- Header row: 6 (1-indexed)
- Columns: ID, Scope, Level 1, Level 2, Level 3, Level 4, Column Text, UOM, GHG/Unit, GHG Conversion Factor YYYY
- ~8,700 rows total, ~3,400 are `kg CO2e` totals (the rest are individual gas breakdowns + kWh conversions)

**Filtering:**
- Keep only rows where `GHG/Unit == "kg CO2e"` (total CO2e, not individual gas breakdowns)
- Exclude `Scope == "Outside of Scopes"` (biogenic CO2, not counted in GHG Protocol)
- Exclude `Scope == "END"` and null rows
- Result: ~3,350 factors per year

**Scope mapping:**
- "Scope 1" → scope 1
- "Scope 2" → scope 2
- "Scope 3" → scope 3

**Category mapping:**
- `category` = Level 1 (e.g. "Fuels", "UK electricity", "Business travel- air")
- `subcategory` = Level 2 + Level 3 + Level 4 joined with " > " where non-null
- `unit` = "kgCO2e/{UOM}" (e.g. "kgCO2e/litres", "kgCO2e/kWh")
- `factor_type` = "activity"
- `keywords` = generated from category/subcategory names, lowercased

### Level 4 — Spend-Based EEIO (separate DEFRA dataset)

**Source:** UK's Carbon Footprint — Conversion factors kgCO2 per £ spent, by SIC code
**Publisher:** DEFRA via gov.uk
**URL:** `https://www.gov.uk/government/statistics/uks-carbon-footprint`

**Structure:**
- ODS format, single sheet
- Columns: SIC code, Description, GHG (kgCO2e per £), CO2 (kgCO2 per £)
- 111 rows covering all SIC codes
- Currently 2022 data (matches the ~3-year lag noted in Hemera methodology)

**Mapping:**
- `category` = Description (e.g. "Products of agriculture, hunting and related services")
- `subcategory` = SIC code (e.g. "01")
- `unit` = "kgCO2e/GBP"
- `factor_type` = "spend"
- `scope` = 3 (all EEIO factors are Scope 3)
- `source` = "defra-eeio"
- `keywords` = generated from description + common synonyms

## File Layout

```
data/defra/
  ghg-conversion-factors-2024-flat.xlsx
  ghg-conversion-factors-2023-flat.xlsx
  eeio-factors-by-sic-2022.ods
  README.md                              # Source URLs, download dates, checksums

hemera/services/
  defra_parser.py    # NEW — parse xlsx/ods → list[dict]
  seed_factors.py    # REWRITTEN — calls parser, seeds DB
```

### data/defra/README.md

Documents the provenance of each file: official URL, download date, SHA256 checksum. This is the audit trail.

## Parser Design (`defra_parser.py`)

Two public functions:

### `parse_activity_factors(file_path: str, year: int) -> list[dict]`

Reads a DEFRA flat-format xlsx file and returns a list of dicts matching the EmissionFactor model fields. Each dict includes:
- `source`: "defra"
- `category`, `subcategory`, `scope`, `factor_value`, `unit`, `factor_type`, `year`, `region`
- `keywords`: auto-generated from category hierarchy + UOM

### `parse_eeio_factors(file_path: str, year: int) -> list[dict]`

Reads the EEIO ODS file and returns a list of dicts. Each dict includes:
- `source`: "defra-eeio"
- `category` (description), `subcategory` (SIC code), `scope` (always 3)
- `factor_value` (kgCO2e per £), `unit` ("kgCO2e/GBP"), `factor_type` ("spend")
- `keywords`: auto-generated from description with common business synonyms

### Keyword Generation

For activity-based factors, keywords are derived from the Level 1-4 hierarchy, lowercased, with common aliases added (e.g. "petrol" → also "gasoline,unleaded").

For spend-based factors, keywords map SIC descriptions to common business terms (e.g. "Accommodation services" → "hotel,accommodation,airbnb,booking").

## Seeder Design (`seed_factors.py`)

### `seed_emission_factors(db: Session) -> int`

1. Discover all files in `data/defra/`
2. Parse each file using the appropriate parser function
3. Clear existing DEFRA/DEFRA-EEIO factors from DB
4. Insert all parsed factors
5. Return count of factors inserted

The seeder is idempotent — safe to re-run. It replaces all DEFRA-sourced factors each time (allowing workbook updates).

## EmissionFactor Model

No schema changes needed. The existing model handles everything:
- `source`: "defra" or "defra-eeio"
- `factor_type`: "activity" or "spend"
- All other fields map directly

## Cascade Lookup Impact

`emission_calc.py::_find_emission_factor()` currently does a simple category name match. With ~3,350 activity factors per year (vs the current 3), the matching logic needs to be more precise. However, that's a separate concern — the current task is seeding the factors. The cascade lookup improvements can follow.

## Testing

- Unit tests for `defra_parser.py`: parse a known subset, verify exact values match the workbook
- Integration test: seed from real files, verify row counts and spot-check specific factors
- Regression: existing 75 tests must still pass (the seeder is called during test setup)

## What This Does NOT Cover

- Level 3 (Exiobase MRIO) — separate dataset, separate task
- Level 5 (USEEIO) — separate dataset, separate task
- Level 6 (Climatiq API) — runtime API calls, not seed data
- Cascade lookup improvements — follow-up task
- Automatic DEFRA workbook downloads — manual process for now
