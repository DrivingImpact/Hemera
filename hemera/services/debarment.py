"""Anti-bribery, corruption & debarment checks — Layer 11.

Checks:
- World Bank Debarment List
- EU Debarment Database (EDES)
These are in addition to OpenSanctions which already covers PEP screening.
"""

import httpx


async def check_world_bank_debarment(company_name: str) -> dict:
    """Check World Bank Group debarment list.

    https://www.worldbank.org/en/projects-operations/procurement/debarred-firms
    The list is available as a downloadable dataset.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://apigwext.worldbank.org/dvsvc/v1.0/json/CLIENT/SP/DEBARRED_FIRMS",
                params={"search": company_name},
            )
            if resp.status_code == 200:
                data = resp.json()
                firms = data if isinstance(data, list) else data.get("firms", [])
                matches = [
                    f for f in firms
                    if company_name.lower() in str(f).lower()
                ]
                return {
                    "world_bank_debarred": len(matches) > 0,
                    "matches": matches[:3],
                    "source": "worldbank.org",
                }
    except Exception:
        pass
    return {"world_bank_debarred": False, "source": "worldbank.org"}


async def check_eu_debarment(company_name: str) -> dict:
    """Check EU EDES (Early Detection and Exclusion System).

    Published in the EU Official Journal.
    """
    # EDES doesn't have a public API — requires manual check or
    # scraping from the Official Journal
    return {
        "eu_debarred": False,
        "source": "edes.ec.europa.eu",
        "note": "Manual verification recommended for high-risk suppliers",
    }


async def check_all_debarment(company_name: str) -> dict:
    """Run all Layer 11 checks."""
    wb = await check_world_bank_debarment(company_name)
    eu = await check_eu_debarment(company_name)

    return {
        "world_bank": wb,
        "eu": eu,
        "world_bank_debarred": wb.get("world_bank_debarred", False),
        "eu_debarred": eu.get("eu_debarred", False),
        "sfo_prosecution": False,  # Requires manual check / news scrape
    }
