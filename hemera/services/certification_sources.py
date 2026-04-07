"""Certification verification — Layer 6.

Checks certifications against the issuing body's own register.
"""

import httpx


async def check_b_corp(company_name: str) -> dict:
    """Check B Corp certification directory.

    https://www.bcorporation.net/en-us/find-a-b-corp/
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.bcorporation.net/en-us/find-a-b-corp/",
                params={"search": company_name, "country": "United Kingdom"},
            )
            if resp.status_code == 200:
                found = company_name.lower() in resp.text.lower()
                return {"b_corp": found, "source": "bcorporation.net"}
    except Exception:
        pass
    return {"b_corp": False, "source": "bcorporation.net"}


async def check_cyber_essentials(company_name: str) -> dict:
    """Check Cyber Essentials / Cyber Essentials Plus certification.

    NCSC maintains a public register of certified organisations.
    https://www.ncsc.gov.uk/cyberessentials/search
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.ncsc.gov.uk/api/cyberessentials/search",
                params={"q": company_name},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data if isinstance(data, list) else data.get("results", [])
                if results:
                    return {
                        "cyber_essentials": True,
                        "level": results[0].get("level", "Basic"),
                        "source": "ncsc.gov.uk",
                    }
    except Exception:
        pass
    return {"cyber_essentials": False, "source": "ncsc.gov.uk"}


async def check_iso_14001(company_name: str) -> dict:
    """Check ISO 14001 environmental management certification.

    UKAS accredited certification bodies maintain registers.
    For MVP, this is a flag that can be enriched from supplier engagement.
    """
    return {
        "iso_14001": False,
        "source": "ukas.com",
        "note": "Requires supplier engagement or manual verification",
    }


async def check_fairtrade(company_name: str) -> dict:
    """Check Fairtrade certification."""
    return {
        "fairtrade": False,
        "source": "fairtrade.org.uk",
        "note": "Manual verification from Fairtrade producer register",
    }


async def check_fsc(company_name: str) -> dict:
    """Check FSC (Forest Stewardship Council) certification.

    https://info.fsc.org/certificate.php
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://info.fsc.org/api/v1/certificate",
                params={"searchterm": company_name, "country": "GB"},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("data", [])
                if results:
                    return {
                        "fsc_certified": True,
                        "certificate_code": results[0].get("certificateCode"),
                        "source": "fsc.org",
                    }
    except Exception:
        pass
    return {"fsc_certified": False, "source": "fsc.org"}


async def check_all_certifications(company_name: str) -> dict:
    """Run all Layer 6 checks."""
    b_corp = await check_b_corp(company_name)
    cyber = await check_cyber_essentials(company_name)
    iso = await check_iso_14001(company_name)
    fairtrade = await check_fairtrade(company_name)
    fsc = await check_fsc(company_name)

    certifications = []
    if b_corp.get("b_corp"):
        certifications.append({"name": "B Corp", "verified": True})
    if cyber.get("cyber_essentials"):
        certifications.append({"name": f"Cyber Essentials {cyber.get('level', '')}", "verified": True})
    if fsc.get("fsc_certified"):
        certifications.append({"name": "FSC", "verified": True})

    # Additional certifications
    msc = await check_msc(company_name)
    soil = await check_soil_association(company_name)
    rainforest = await check_rainforest_alliance(company_name)

    if msc.get("msc_certified"):
        certifications.append({"name": "MSC", "verified": True})
    if soil.get("soil_association"):
        certifications.append({"name": "Soil Association", "verified": True})
    if rainforest.get("rainforest_alliance"):
        certifications.append({"name": "Rainforest Alliance", "verified": True})

    return {
        "b_corp": b_corp.get("b_corp", False),
        "cyber_essentials": cyber.get("cyber_essentials", False),
        "iso_14001": iso.get("iso_14001", False),
        "fairtrade": fairtrade.get("fairtrade", False),
        "fsc_certified": fsc.get("fsc_certified", False),
        "msc_certified": msc.get("msc_certified", False),
        "soil_association": soil.get("soil_association", False),
        "rainforest_alliance": rainforest.get("rainforest_alliance", False),
        "certifications": certifications,
    }


async def check_msc(company_name: str) -> dict:
    """Check Marine Stewardship Council certification."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://cert.msc.org/supplierdirectory/VController/GetSearchResults",
                params={"term": company_name},
            )
            if resp.status_code == 200:
                found = company_name.lower() in resp.text.lower()
                return {"msc_certified": found, "source": "msc.org"}
    except Exception:
        pass
    return {"msc_certified": False, "source": "msc.org"}


async def check_soil_association(company_name: str) -> dict:
    """Check Soil Association organic certification."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.soilassociation.org/certification/find-a-licensee/",
                params={"q": company_name},
            )
            if resp.status_code == 200:
                found = company_name.lower() in resp.text.lower()
                return {"soil_association": found, "source": "soilassociation.org"}
    except Exception:
        pass
    return {"soil_association": False, "source": "soilassociation.org"}


async def check_rainforest_alliance(company_name: str) -> dict:
    """Check Rainforest Alliance certification."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.rainforest-alliance.org/find-certified/",
                params={"search": company_name},
            )
            if resp.status_code == 200:
                found = company_name.lower() in resp.text.lower()
                return {"rainforest_alliance": found, "source": "rainforest-alliance.org"}
    except Exception:
        pass
    return {"rainforest_alliance": False, "source": "rainforest-alliance.org"}
