"""Environment Agency — Layer 4 data source.

Checks for environmental permits, pollution incidents, and enforcement actions.
Free API: https://environment.data.gov.uk/
"""

import httpx


EA_BASE = "https://environment.data.gov.uk/public-register"


async def search_permits(company_name: str) -> list[dict]:
    """Search EA public register for environmental permits."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{EA_BASE}/waste-operations/registrations",
                params={"search": company_name, "_limit": 10},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("items", [])
            return [
                {
                    "permit_number": item.get("permitNumber"),
                    "operator": item.get("operator"),
                    "site_name": item.get("siteName"),
                    "permit_type": item.get("permitType"),
                    "status": item.get("status"),
                    "effective_date": item.get("effectiveDate"),
                }
                for item in items
            ]
    except Exception:
        return []


async def search_enforcement(company_name: str) -> list[dict]:
    """Search for EA enforcement actions against a company.

    Uses the EA enforcement data API.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://environment.data.gov.uk/public-register/enforcement-actions",
                params={"search": company_name, "_limit": 10},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [
                {
                    "offender": item.get("offender"),
                    "offence": item.get("offence"),
                    "action_taken": item.get("actionTaken"),
                    "date": item.get("date"),
                    "court": item.get("court"),
                    "fine": item.get("fine"),
                }
                for item in data.get("items", [])
            ]
    except Exception:
        return []


async def check_environmental_record(company_name: str) -> dict:
    """Full Layer 4 check — permits + enforcement."""
    permits = await search_permits(company_name)
    enforcement = await search_enforcement(company_name)
    return {
        "permits": permits,
        "permit_count": len(permits),
        "enforcement_actions": enforcement,
        "enforcement_count": len(enforcement),
        "has_environmental_permits": len(permits) > 0,
        "has_enforcement_actions": len(enforcement) > 0,
    }
