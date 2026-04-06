# DEFRA Emission Factor Workbooks

Official UK Government emission factor datasets. These files are parsed at
seed time by `hemera/services/defra_parser.py`.

## Level 2 — Activity-Based (main DEFRA/DESNZ conversion factors)

Flat file format, designed for automated processing.

| File | Year | Source URL | SHA256 |
|------|------|-----------|--------|
| ghg-conversion-factors-2024-flat.xlsx | 2024 | https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024 | 1b063892ad1f00c5bc73029c016e54bc4c3050a71219202b545f8aea2f9f75c4 |
| ghg-conversion-factors-2023-flat.xlsx | 2023 | https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2023 | 804885cb9d8f02bbb97dcd92b79ca294080ba892ba67e3c95fcfbae52af359a6 |

## Level 4 — Spend-Based EEIO (kgCO2e per GBP by SIC code)

| File | Year | Source URL | SHA256 |
|------|------|-----------|--------|
| eeio-factors-by-sic-2022.ods | 2022 | https://www.gov.uk/government/statistics/uks-carbon-footprint | 71e057c54ce2b52c827de6287dbb3ae45f22fc7b141beb8558f24f8705c0f11e |

## Adding a new year

1. Download the flat file from gov.uk (the "for automatic processing" version)
2. Place in this directory with the naming convention: `ghg-conversion-factors-YYYY-flat.xlsx`
3. Update this README with the SHA256 checksum
4. Re-run the seeder: `.venv/bin/python -m hemera.services.seed_factors`
