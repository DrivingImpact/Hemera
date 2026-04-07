"""CDP, SBTi, and Carbon Trust checks — Layer 4 data sources.

Checks whether a company has:
- CDP disclosure (Carbon Disclosure Project)
- SBTi target (Science Based Targets initiative)
- Carbon Trust Standard certification

These are public registers searchable by company name.
"""

import httpx


async def check_sbti(company_name: str) -> dict:
    """Check if company has a Science Based Target.

    SBTi publishes a list of companies with targets at:
    https://sciencebasedtargets.org/companies-taking-action
    Their API/data is available as a downloadable Excel.
    For MVP, we do a web search against their site.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://sciencebasedtargets.org/api/companies",
                params={"search": company_name},
            )
            if resp.status_code == 200:
                data = resp.json()
                companies = data if isinstance(data, list) else data.get("data", [])
                matches = [
                    c for c in companies
                    if company_name.lower() in str(c).lower()
                ]
                if matches:
                    return {
                        "has_sbti_target": True,
                        "matches": matches[:3],
                        "source": "sciencebasedtargets.org",
                    }
    except Exception:
        pass

    return {"has_sbti_target": False, "source": "sciencebasedtargets.org"}


async def check_cdp(company_name: str) -> dict:
    """Check if company has CDP disclosure.

    CDP scores are published annually. The public search is at:
    https://www.cdp.net/en/responses
    For MVP, we check if the company appears in CDP's public data.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.cdp.net/en/responses",
                params={"queries[name]": company_name},
            )
            if resp.status_code == 200:
                # CDP doesn't have a clean API — check if name appears in response
                if company_name.lower() in resp.text.lower():
                    return {
                        "has_cdp_disclosure": True,
                        "source": "cdp.net",
                    }
    except Exception:
        pass

    return {"has_cdp_disclosure": False, "source": "cdp.net"}


async def check_carbon_trust(company_name: str) -> dict:
    """Check Carbon Trust Standard certification."""
    # Carbon Trust doesn't have a public API
    # For MVP, this is a placeholder that can be enriched manually
    return {
        "carbon_trust_certified": False,
        "source": "carbontrust.com",
        "note": "Manual verification required",
    }


async def check_all_carbon_registries(company_name: str) -> dict:
    """Run all carbon registry checks for Layer 4."""
    sbti = await check_sbti(company_name)
    cdp = await check_cdp(company_name)
    carbon_trust = await check_carbon_trust(company_name)

    return {
        "sbti": sbti,
        "cdp": cdp,
        "carbon_trust": carbon_trust,
        "has_sbti_target": sbti.get("has_sbti_target", False),
        "has_cdp_disclosure": cdp.get("has_cdp_disclosure", False),
        "carbon_trust_certified": carbon_trust.get("carbon_trust_certified", False),
    }
