"""Government contract intelligence — Layer 9.

Uses Contracts Finder (OCDS API) to check if a supplier holds
government contracts and what that reveals.

Free API: https://www.contractsfinder.service.gov.uk/apidocumentation
"""

import httpx


CF_BASE = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"


async def search_contracts(company_name: str, limit: int = 10) -> dict:
    """Search Contracts Finder for government contracts held by a company."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                CF_BASE,
                params={
                    "supplierName": company_name,
                    "size": limit,
                    "order": "desc",
                },
            )
            if resp.status_code != 200:
                return {
                    "has_government_contracts": False,
                    "contract_count": 0,
                    "source": "contractsfinder.service.gov.uk",
                }

            data = resp.json()
            releases = data.get("releases", [])

            contracts = []
            total_value = 0
            for release in releases:
                tender = release.get("tender", {})
                awards = release.get("awards", [])
                for award in awards:
                    value = award.get("value", {}).get("amount", 0)
                    total_value += value or 0
                    contracts.append({
                        "title": tender.get("title", ""),
                        "buyer": release.get("buyer", {}).get("name", ""),
                        "value": value,
                        "currency": award.get("value", {}).get("currency", "GBP"),
                        "date": award.get("date", ""),
                        "status": award.get("status", ""),
                    })

            # Check if any contract >£5M (PPN 006 threshold)
            has_large_contract = any(
                c.get("value", 0) and c["value"] > 5_000_000 for c in contracts
            )

            return {
                "has_government_contracts": len(contracts) > 0,
                "contract_count": len(contracts),
                "total_contract_value": total_value,
                "contracts": contracts[:5],  # Top 5 only
                "ppn006_applicable": has_large_contract,
                "ppn006_carbon_plan": None,  # Would need manual check
                "source": "contractsfinder.service.gov.uk",
            }

    except Exception:
        return {
            "has_government_contracts": False,
            "contract_count": 0,
            "source": "contractsfinder.service.gov.uk",
        }
