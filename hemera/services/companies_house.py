"""Companies House API integration — Layers 1, 2, 3 data source.

Provides: company profile, officers, PSC, filing history, charges,
insolvency history. All free, 600 requests per 5 minutes.
"""

import httpx
from hemera.config import get_settings


BASE_URL = "https://api.company-information.service.gov.uk"


def _auth() -> tuple[str, str]:
    return (get_settings().companies_house_api_key, "")


async def search_company(name: str, limit: int = 5) -> list[dict]:
    """Search Companies House by company name."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/search/companies",
            params={"q": name, "items_per_page": limit},
            auth=(settings.companies_house_api_key, ""),
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "ch_number": item.get("company_number"),
                "name": item.get("title"),
                "status": item.get("company_status"),
                "type": item.get("company_type"),
                "address": item.get("address_snippet"),
                "date_of_creation": item.get("date_of_creation"),
            }
            for item in data.get("items", [])
        ]


async def get_company(ch_number: str) -> dict | None:
    """Get full company profile by Companies House number."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/company/{ch_number}",
            auth=(settings.companies_house_api_key, ""),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return {
            "ch_number": data.get("company_number"),
            "name": data.get("company_name"),
            "status": data.get("company_status"),
            "type": data.get("type"),
            "sic_codes": data.get("sic_codes", []),
            "registered_address": data.get("registered_office_address"),
            "date_of_creation": data.get("date_of_creation"),
            "accounts": data.get("accounts"),
            "has_charges": data.get("has_charges"),
            "has_insolvency_history": data.get("has_insolvency_history"),
        }


async def get_officers(ch_number: str) -> list[dict]:
    """Get company officers (directors, secretaries)."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/company/{ch_number}/officers",
            auth=(settings.companies_house_api_key, ""),
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "name": item.get("name"),
                "role": item.get("officer_role"),
                "appointed": item.get("appointed_on"),
                "resigned": item.get("resigned_on"),
                "nationality": item.get("nationality"),
                "occupation": item.get("occupation"),
            }
            for item in data.get("items", [])
        ]


async def get_psc(ch_number: str) -> list[dict]:
    """Get Persons of Significant Control (beneficial owners)."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/company/{ch_number}/persons-with-significant-control",
            auth=(settings.companies_house_api_key, ""),
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "name": item.get("name"),
                "kind": item.get("kind"),
                "natures_of_control": item.get("natures_of_control", []),
                "nationality": item.get("nationality"),
                "country_of_residence": item.get("country_of_residence"),
                "notified_on": item.get("notified_on"),
            }
            for item in data.get("items", [])
        ]


async def get_filing_history(ch_number: str, limit: int = 10) -> list[dict]:
    """Get recent filing history."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/company/{ch_number}/filing-history",
            params={"items_per_page": limit},
            auth=(settings.companies_house_api_key, ""),
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "date": item.get("date"),
                "category": item.get("category"),
                "type": item.get("type"),
                "description": item.get("description"),
            }
            for item in data.get("items", [])
        ]


async def get_charges(ch_number: str) -> list[dict]:
    """Get charges (mortgages/debentures) registered against the company."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/company/{ch_number}/charges",
            auth=(settings.companies_house_api_key, ""),
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "status": item.get("status"),
                "created_on": item.get("created_on"),
                "delivered_on": item.get("delivered_on"),
                "classification": item.get("classification", {}).get("description"),
                "secured_details": item.get("particulars", {}).get("description"),
            }
            for item in data.get("items", [])
        ]
