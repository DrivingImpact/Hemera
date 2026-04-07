"""Additional Layer 1 sources — corporate identity beyond Companies House.

- HMRC VAT Number Checker
- The Insolvency Service Register
- Food Standards Agency hygiene ratings
- Charity Commission (detailed)
- UK Visa & Immigration Sponsor Licence Register
"""

import httpx


async def check_vat_number(vat_number: str) -> dict:
    """Verify a UK VAT number via HMRC.

    https://api.service.hmrc.gov.uk/organisations/vat/check-vat-number/lookup
    """
    if not vat_number:
        return {"vat_valid": None, "source": "hmrc.gov.uk"}
    try:
        clean = vat_number.replace("GB", "").replace(" ", "").strip()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.service.hmrc.gov.uk/organisations/vat/check-vat-number/lookup/{clean}"
            )
            if resp.status_code == 200:
                data = resp.json()
                target = data.get("target", {})
                return {
                    "vat_valid": True,
                    "vat_number": clean,
                    "name": target.get("name"),
                    "address": target.get("address"),
                    "source": "hmrc.gov.uk",
                }
            elif resp.status_code == 404:
                return {"vat_valid": False, "vat_number": clean, "source": "hmrc.gov.uk"}
    except Exception:
        pass
    return {"vat_valid": None, "source": "hmrc.gov.uk"}


async def check_insolvency_register(company_name: str) -> dict:
    """Check The Insolvency Service individual insolvency register.

    https://www.insolvencydirect.bis.gov.uk/eiir/
    Checks for directors/individuals associated with the company.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.insolvencydirect.bis.gov.uk/eiir/IIRCaseIndivSearchResult.asp",
                params={"surname": "", "forename": "", "tradingname": company_name},
            )
            if resp.status_code == 200:
                found = "case details" in resp.text.lower()
                return {
                    "insolvency_records_found": found,
                    "source": "insolvencydirect.bis.gov.uk",
                }
    except Exception:
        pass
    return {"insolvency_records_found": False, "source": "insolvencydirect.bis.gov.uk"}


async def check_fsa_hygiene(company_name: str) -> dict:
    """Check Food Standards Agency food hygiene ratings.

    https://api.ratings.food.gov.uk/
    Free API, no key required.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.ratings.food.gov.uk/Establishments",
                params={"name": company_name, "pageSize": 5},
                headers={
                    "x-api-version": "2",
                    "Accept": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                establishments = data.get("establishments", [])
                if establishments:
                    ratings = []
                    for est in establishments[:5]:
                        ratings.append({
                            "name": est.get("BusinessName"),
                            "rating": est.get("RatingValue"),
                            "date": est.get("RatingDate"),
                            "address": est.get("AddressLine1"),
                            "local_authority": est.get("LocalAuthorityName"),
                        })
                    avg_rating = sum(
                        int(r["rating"]) for r in ratings
                        if r["rating"] and r["rating"].isdigit()
                    ) / max(1, len([r for r in ratings if r["rating"] and r["rating"].isdigit()]))
                    return {
                        "has_fsa_ratings": True,
                        "establishment_count": len(ratings),
                        "ratings": ratings,
                        "average_rating": round(avg_rating, 1),
                        "source": "food.gov.uk",
                    }
    except Exception:
        pass
    return {"has_fsa_ratings": False, "source": "food.gov.uk"}


async def check_charity_commission_detailed(company_name: str) -> dict:
    """Detailed Charity Commission check — income, activities, inquiries.

    https://register-of-charities.charitycommission.gov.uk/
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.charitycommission.gov.uk/register/api/allcharitydetailsV2",
                params={"searchText": company_name, "pageSize": 3},
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                charities = data if isinstance(data, list) else data.get("charities", data.get("list", []))
                if charities and len(charities) > 0:
                    c = charities[0]
                    return {
                        "is_charity": True,
                        "charity_number": c.get("registeredCharityNumber") or c.get("charityNumber"),
                        "charity_name": c.get("charityName") or c.get("name"),
                        "income": c.get("latestIncome") or c.get("income"),
                        "spending": c.get("latestSpending") or c.get("spending"),
                        "trustees_count": c.get("numberOfTrustees"),
                        "activities": c.get("activities"),
                        "registration_status": c.get("registrationStatus"),
                        "source": "charitycommission.gov.uk",
                    }
    except Exception:
        pass
    return {"is_charity": False, "source": "charitycommission.gov.uk"}


async def check_visa_sponsor(company_name: str) -> dict:
    """Check UK Visa & Immigration Sponsor Licence Register.

    Published as a downloadable spreadsheet by GOV.UK.
    For MVP, we do a basic check.
    """
    # The register is a downloadable CSV, not an API
    # In production, we'd download and index it periodically
    return {
        "is_visa_sponsor": None,
        "source": "gov.uk/visa-sponsor-register",
        "note": "Requires periodic download of sponsor register",
    }


async def check_all_corporate_identity(
    company_name: str,
    vat_number: str | None = None,
) -> dict:
    """Run all additional Layer 1 checks."""
    vat = await check_vat_number(vat_number) if vat_number else {"vat_valid": None}
    insolvency = await check_insolvency_register(company_name)
    fsa = await check_fsa_hygiene(company_name)
    charity = await check_charity_commission_detailed(company_name)
    visa = await check_visa_sponsor(company_name)

    return {
        "vat": vat,
        "insolvency": insolvency,
        "fsa": fsa,
        "charity_detail": charity,
        "visa_sponsor": visa,
        "insolvency_records_found": insolvency.get("insolvency_records_found", False),
        "has_fsa_ratings": fsa.get("has_fsa_ratings", False),
        "fsa_average_rating": fsa.get("average_rating"),
        "is_charity": charity.get("is_charity", False),
        "charity_income": charity.get("income"),
    }
