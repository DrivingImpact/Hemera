"""Social value & community impact — Layer 13.

Checks:
- Social Enterprise UK Directory
- Community Interest Company (CIC) status via Companies House
- B Corp (cross-reference with Layer 6)
"""

import httpx


async def check_social_enterprise(company_name: str) -> dict:
    """Check Social Enterprise UK directory."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.socialenterprise.org.uk/members/",
                params={"s": company_name},
            )
            if resp.status_code == 200:
                found = company_name.lower() in resp.text.lower()
                return {"is_social_enterprise": found, "source": "socialenterprise.org.uk"}
    except Exception:
        pass
    return {"is_social_enterprise": False, "source": "socialenterprise.org.uk"}


def check_cic_status(entity_type: str | None) -> dict:
    """Check if company is a Community Interest Company.

    CIC status is already available from Companies House data (Layer 1).
    entity_type will be 'community-interest-company' if CIC.
    """
    is_cic = entity_type and "community-interest" in str(entity_type).lower()
    return {"is_cic": bool(is_cic), "source": "companies_house"}


async def check_all_social_value(company_name: str, entity_type: str | None = None) -> dict:
    """Run all Layer 13 checks."""
    social_enterprise = await check_social_enterprise(company_name)
    cic = check_cic_status(entity_type)

    return {
        "social_enterprise": social_enterprise,
        "cic": cic,
        "is_social_enterprise": social_enterprise.get("is_social_enterprise", False),
        "is_cic": cic.get("is_cic", False),
    }
