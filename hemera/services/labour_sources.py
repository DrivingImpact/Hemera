"""Labour, Ethics & Modern Slavery sources — Layer 5.

Checks:
- UK Modern Slavery Statement Registry (GOV.UK)
- HSE enforcement database
- Living Wage Foundation employer register
- GLAA licence register
- Gender Pay Gap Service
- Disability Confident employer register
"""

import httpx


async def check_modern_slavery_statement(company_name: str) -> dict:
    """Check if company has published a Modern Slavery Statement.

    The UK Modern Slavery Act Statement Registry:
    https://modern-slavery-statement-registry.service.gov.uk
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://modern-slavery-statement-registry.service.gov.uk/search",
                params={"q": company_name},
            )
            if resp.status_code == 200:
                has_statement = company_name.lower() in resp.text.lower()
                return {
                    "modern_slavery_statement": has_statement,
                    "source": "modern-slavery-statement-registry.service.gov.uk",
                }
    except Exception:
        pass

    return {"modern_slavery_statement": False, "source": "modern-slavery-statement-registry"}


async def check_hse_enforcement(company_name: str) -> dict:
    """Check HSE enforcement database for actions against the company.

    HSE public register of enforcement notices and prosecutions:
    https://resources.hse.gov.uk/notices/
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://resources.hse.gov.uk/notices/notices/search",
                params={"SearchForm.SearchTerm": company_name},
            )
            if resp.status_code == 200:
                # Count enforcement notices found
                count = resp.text.lower().count("notice number")
                return {
                    "hse_enforcement_count": count,
                    "has_hse_enforcement": count > 0,
                    "source": "hse.gov.uk",
                }
    except Exception:
        pass

    return {"hse_enforcement_count": 0, "has_hse_enforcement": False, "source": "hse.gov.uk"}


async def check_living_wage(company_name: str) -> dict:
    """Check Living Wage Foundation accredited employer register.

    https://www.livingwage.org.uk/accredited-living-wage-employers
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.livingwage.org.uk/accredited-living-wage-employers",
                params={"search": company_name},
            )
            if resp.status_code == 200:
                is_accredited = company_name.lower() in resp.text.lower()
                return {
                    "living_wage_accredited": is_accredited,
                    "source": "livingwage.org.uk",
                }
    except Exception:
        pass

    return {"living_wage_accredited": False, "source": "livingwage.org.uk"}


async def check_glaa_licence(company_name: str) -> dict:
    """Check GLAA (Gangmasters & Labour Abuse Authority) licence register.

    https://www.gla.gov.uk/i-am-a/i-use-workers/find-a-licensed-labour-provider/
    Critical for food, agriculture, and shellfish supply chains.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.gla.gov.uk/i-am-a/i-use-workers/find-a-licensed-labour-provider/",
                params={"keyword": company_name},
            )
            if resp.status_code == 200:
                found = company_name.lower() in resp.text.lower()
                return {
                    "glaa_licensed": found,
                    "glaa_licence_revoked": False,
                    "source": "gla.gov.uk",
                }
    except Exception:
        pass

    return {"glaa_licensed": False, "glaa_licence_revoked": False, "source": "gla.gov.uk"}


async def check_gender_pay_gap(company_name: str) -> dict:
    """Check Gender Pay Gap Service.

    https://gender-pay-gap.service.gov.uk
    Free API. Required for employers with 250+ staff.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://gender-pay-gap.service.gov.uk/api/v1/viewing/search",
                params={"t": 1, "search": company_name},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data if isinstance(data, list) else data.get("Results", [])
                if results:
                    top = results[0]
                    return {
                        "has_gender_pay_data": True,
                        "employer_name": top.get("Name") or top.get("EmployerName"),
                        "gender_pay_gap_median": top.get("MedianHourlyPercent")
                            or top.get("DiffMedianHourlyPercent"),
                        "gender_pay_gap_mean": top.get("MeanHourlyPercent")
                            or top.get("DiffMeanHourlyPercent"),
                        "employer_size": top.get("EmployerSize"),
                        "source": "gender-pay-gap.service.gov.uk",
                    }
    except Exception:
        pass

    return {"has_gender_pay_data": False, "source": "gender-pay-gap.service.gov.uk"}


async def check_disability_confident(company_name: str) -> dict:
    """Check Disability Confident employer register."""
    # No public API — would need scraping from GOV.UK
    return {
        "disability_confident": False,
        "source": "gov.uk/disability-confident",
        "note": "Manual verification required",
    }


async def check_all_labour_sources(company_name: str) -> dict:
    """Run all Layer 5 checks."""
    modern_slavery = await check_modern_slavery_statement(company_name)
    hse = await check_hse_enforcement(company_name)
    living_wage = await check_living_wage(company_name)
    glaa = await check_glaa_licence(company_name)
    gpg = await check_gender_pay_gap(company_name)
    disability = await check_disability_confident(company_name)

    return {
        "modern_slavery": modern_slavery,
        "hse": hse,
        "living_wage": living_wage,
        "glaa": glaa,
        "gender_pay_gap": gpg,
        "disability_confident": disability,
        # Summary flags for scoring
        "modern_slavery_statement": modern_slavery.get("modern_slavery_statement", False),
        "hse_enforcement_count": hse.get("hse_enforcement_count", 0),
        "living_wage_accredited": living_wage.get("living_wage_accredited", False),
        "glaa_licence_revoked": glaa.get("glaa_licence_revoked", False),
        "eti_member": False,  # Requires manual check
        "disability_confident": disability.get("disability_confident", False),
        "gender_pay_gap_median": gpg.get("gender_pay_gap_median"),
    }
