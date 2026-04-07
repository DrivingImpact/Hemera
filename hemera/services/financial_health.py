"""Additional Layer 3 sources — financial health beyond Companies House.

- Gender Pay Gap API (detailed)
- Prompt Payment Code Register
- The Gazette (insolvency notices, winding-up petitions)
"""

import httpx


async def get_gender_pay_gap_detailed(company_name: str) -> dict:
    """Get detailed Gender Pay Gap data from GOV.UK.

    https://gender-pay-gap.service.gov.uk
    Free API. Required for employers with 250+ staff.
    Returns hourly pay gaps, bonus gaps, and pay quartiles.
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
                    r = results[0]
                    return {
                        "has_gender_pay_data": True,
                        "employer_name": r.get("Name") or r.get("EmployerName"),
                        "employer_size": r.get("EmployerSize"),
                        "gender_pay_gap_median": r.get("DiffMedianHourlyPercent")
                            or r.get("MedianHourlyPercent"),
                        "gender_pay_gap_mean": r.get("DiffMeanHourlyPercent")
                            or r.get("MeanHourlyPercent"),
                        "bonus_gap_median": r.get("DiffMedianBonusPercent"),
                        "bonus_gap_mean": r.get("DiffMeanBonusPercent"),
                        "male_bonus_pct": r.get("MaleBonusPercent"),
                        "female_bonus_pct": r.get("FemaleBonusPercent"),
                        "lower_quartile_female": r.get("FemaleLowerQuartile"),
                        "upper_quartile_female": r.get("FemaleUpperQuartile"),
                        "source": "gender-pay-gap.service.gov.uk",
                    }
    except Exception:
        pass
    return {"has_gender_pay_data": False, "source": "gender-pay-gap.service.gov.uk"}


async def check_prompt_payment_code(company_name: str) -> dict:
    """Check if company is a signatory of the Prompt Payment Code.

    https://www.smallbusinesscommissioner.gov.uk/ppc/signatories/
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.smallbusinesscommissioner.gov.uk/ppc/signatories/",
                params={"search": company_name},
            )
            if resp.status_code == 200:
                found = company_name.lower() in resp.text.lower()
                return {
                    "prompt_payment_code": found,
                    "source": "smallbusinesscommissioner.gov.uk",
                }
    except Exception:
        pass
    return {"prompt_payment_code": False, "source": "smallbusinesscommissioner.gov.uk"}


async def check_gazette_notices(company_name: str) -> dict:
    """Check The Gazette for insolvency notices, winding-up petitions.

    https://www.thegazette.co.uk/
    Free API available.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.thegazette.co.uk/notice/search",
                params={
                    "text": company_name,
                    "categorycode": "G406000000",  # Corporate insolvency
                    "results-page-size": 5,
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total", 0) if isinstance(data, dict) else 0
                return {
                    "gazette_insolvency_notices": total,
                    "has_gazette_notices": total > 0,
                    "source": "thegazette.co.uk",
                }
    except Exception:
        pass
    return {"gazette_insolvency_notices": 0, "has_gazette_notices": False, "source": "thegazette.co.uk"}


async def check_all_financial_health(company_name: str) -> dict:
    """Run all additional Layer 3 checks."""
    gpg = await get_gender_pay_gap_detailed(company_name)
    ppc = await check_prompt_payment_code(company_name)
    gazette = await check_gazette_notices(company_name)

    return {
        "gender_pay_gap": gpg,
        "prompt_payment_code": ppc,
        "gazette": gazette,
        "has_gender_pay_data": gpg.get("has_gender_pay_data", False),
        "gender_pay_gap_median": gpg.get("gender_pay_gap_median"),
        "prompt_payment_code_signatory": ppc.get("prompt_payment_code", False),
        "gazette_insolvency_notices": gazette.get("gazette_insolvency_notices", 0),
    }
