"""Batch of additional free data sources across multiple layers.

All sources here are either free APIs, free downloadable data, or
lightweight web checks (name-presence only, minimal bandwidth).
"""

import httpx

TIMEOUT = 12.0


async def _safe_get(url: str, params: dict = None, headers: dict = None) -> httpx.Response | None:
    """GET with timeout and error swallowing. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers, follow_redirects=True)
            if resp.status_code == 200:
                return resp
    except Exception:
        pass
    return None


async def _name_in_page(url: str, company_name: str, params: dict = None) -> bool:
    """Lightweight check — does company name appear on the page?"""
    resp = await _safe_get(url, params=params)
    if resp:
        return company_name.lower() in resp.text.lower()
    return False


# ── LAYER 1 EXTRAS ──

async def check_opencorporates(company_name: str, country: str = "gb") -> dict:
    """OpenCorporates — free tier, 500 calls/month. Overseas parent tracing."""
    resp = await _safe_get(
        "https://api.opencorporates.com/v0.4/companies/search",
        params={"q": company_name, "jurisdiction_code": country, "per_page": 3},
    )
    if resp:
        data = resp.json()
        companies = data.get("results", {}).get("companies", [])
        if companies:
            c = companies[0].get("company", {})
            return {
                "found": True,
                "name": c.get("name"),
                "jurisdiction": c.get("jurisdiction_code"),
                "company_number": c.get("company_number"),
                "status": c.get("current_status"),
                "incorporation_date": c.get("incorporation_date"),
                "opencorporates_url": c.get("opencorporates_url"),
                "source": "opencorporates.com",
            }
    return {"found": False, "source": "opencorporates.com"}


async def check_oscr(company_name: str) -> dict:
    """OSCR — Scottish Charity Regulator. Free search."""
    found = await _name_in_page(
        "https://www.oscr.org.uk/search/charity-register/charity-search-results",
        company_name,
        params={"cp": "", "q": company_name},
    )
    return {"is_scottish_charity": found, "source": "oscr.org.uk"}


# ── LAYER 5 EXTRAS ──

async def check_eti_membership(company_name: str) -> dict:
    """Ethical Trading Initiative membership check."""
    found = await _name_in_page(
        "https://www.ethicaltrade.org/about-eti/our-members",
        company_name,
    )
    return {"eti_member": found, "source": "ethicaltrade.org"}


async def check_global_slavery_index(country: str = "GBR") -> dict:
    """Global Slavery Index — country-level modern slavery risk.

    Hardcoded risk levels from the Walk Free Foundation data.
    """
    high_risk = {"IND", "CHN", "PAK", "BGD", "UZB", "PRK", "RUS", "NGA",
                 "IDN", "TUR", "MMR", "ETH", "THA", "COD", "IRN"}
    medium_risk = {"BRA", "MEX", "PHL", "VNM", "ZAF", "MYS", "IRQ",
                   "SAU", "EGY", "POL", "ROU", "BGR", "UKR"}

    if country in high_risk:
        level = "high"
    elif country in medium_risk:
        level = "medium"
    else:
        level = "low"

    return {"slavery_risk_level": level, "country": country, "source": "globalslaveryindex.org"}


async def check_employment_tribunals(company_name: str) -> dict:
    """UK Employment Tribunal decisions — GOV.UK."""
    found = await _name_in_page(
        "https://www.gov.uk/employment-tribunal-decisions",
        company_name,
        params={"search[q]": company_name},
    )
    return {"tribunal_decisions_found": found, "source": "gov.uk/employment-tribunal-decisions"}


# ── LAYER 6 EXTRAS ──

async def check_pefc(company_name: str) -> dict:
    """PEFC forest certification check."""
    found = await _name_in_page(
        "https://www.pefc.org/find-certified",
        company_name,
        params={"q": company_name},
    )
    return {"pefc_certified": found, "source": "pefc.org"}


async def check_better_cotton(company_name: str) -> dict:
    """Better Cotton Initiative membership."""
    found = await _name_in_page(
        "https://bettercotton.org/who-we-are/our-members/",
        company_name,
    )
    return {"better_cotton_member": found, "source": "bettercotton.org"}


async def check_grs(company_name: str) -> dict:
    """Global Recycled Standard certification."""
    found = await _name_in_page(
        "https://certifications.controlunion.com/en/certification-programs/certification-programs/grs-global-recycled-standard",
        company_name,
    )
    return {"grs_certified": found, "source": "textileexchange.org"}


# ── LAYER 7 EXTRAS ──

async def check_fca_register(company_name: str) -> dict:
    """FCA Register — Financial Conduct Authority."""
    resp = await _safe_get(
        "https://register.fca.org.uk/s/search",
        params={"q": company_name, "type": "Companies"},
    )
    if resp:
        found = company_name.lower() in resp.text.lower()
        return {"fca_registered": found, "source": "register.fca.org.uk"}
    return {"fca_registered": False, "source": "register.fca.org.uk"}


async def check_ofsted(company_name: str) -> dict:
    """Ofsted reports — education/training providers."""
    resp = await _safe_get(
        "https://reports.ofsted.gov.uk/search",
        params={"q": company_name, "type": "provider"},
    )
    if resp:
        found = company_name.lower() in resp.text.lower()
        return {"has_ofsted_record": found, "source": "reports.ofsted.gov.uk"}
    return {"has_ofsted_record": False, "source": "reports.ofsted.gov.uk"}


async def check_gazette_broader(company_name: str) -> dict:
    """The Gazette — broader search (not just insolvency, all notice types)."""
    resp = await _safe_get(
        "https://www.thegazette.co.uk/notice/search",
        params={"text": company_name, "results-page-size": 5},
        headers={"Accept": "text/html"},
    )
    if resp:
        # Count approximate matches
        count = resp.text.lower().count("notice-title")
        return {
            "gazette_total_notices": count,
            "has_gazette_notices": count > 0,
            "source": "thegazette.co.uk",
        }
    return {"gazette_total_notices": 0, "has_gazette_notices": False, "source": "thegazette.co.uk"}


async def check_planning_portal(company_name: str) -> dict:
    """Planning Portal — planning applications."""
    found = await _name_in_page(
        "https://www.planningportal.co.uk/planning/planning-applications/find-out-more/search",
        company_name,
        params={"q": company_name},
    )
    return {"planning_applications_found": found, "source": "planningportal.co.uk"}


# ── LAYER 9 EXTRAS ──

async def check_find_a_tender(company_name: str) -> dict:
    """Find a Tender Service — UK above-threshold public procurement."""
    resp = await _safe_get(
        "https://www.find-tender.service.gov.uk/Search/Results",
        params={"searchTerm": company_name, "stage": "award"},
    )
    if resp:
        found = company_name.lower() in resp.text.lower()
        return {"find_a_tender_found": found, "source": "find-tender.service.gov.uk"}
    return {"find_a_tender_found": False, "source": "find-tender.service.gov.uk"}


# ── LAYER 11 EXTRAS ──

async def check_sfo_cases(company_name: str) -> dict:
    """Serious Fraud Office — prosecution/investigation history."""
    found = await _name_in_page(
        "https://www.sfo.gov.uk/our-cases/",
        company_name,
    )
    return {"sfo_case_found": found, "source": "sfo.gov.uk"}


# ── BATCH RUNNERS (called by enrichment orchestrator) ──

async def get_extra_layer_1(company_name: str) -> dict:
    """All additional Layer 1 sources."""
    oc = await check_opencorporates(company_name)
    oscr = await check_oscr(company_name)
    return {
        "opencorporates": oc,
        "oscr": oscr,
        "has_opencorporates_record": oc.get("found", False),
        "is_scottish_charity": oscr.get("is_scottish_charity", False),
    }


async def get_extra_layer_5(company_name: str) -> dict:
    """All additional Layer 5 sources."""
    eti = await check_eti_membership(company_name)
    gsi = await check_global_slavery_index()  # Default UK
    tribunals = await check_employment_tribunals(company_name)
    return {
        "eti": eti,
        "global_slavery_index": gsi,
        "tribunals": tribunals,
        "eti_member": eti.get("eti_member", False),
        "slavery_country_risk": gsi.get("slavery_risk_level"),
        "tribunal_decisions_found": tribunals.get("tribunal_decisions_found", False),
    }


async def get_extra_layer_6(company_name: str) -> dict:
    """All additional Layer 6 sources."""
    pefc = await check_pefc(company_name)
    bc = await check_better_cotton(company_name)
    grs = await check_grs(company_name)
    return {
        "pefc": pefc,
        "better_cotton": bc,
        "grs": grs,
        "pefc_certified": pefc.get("pefc_certified", False),
        "better_cotton_member": bc.get("better_cotton_member", False),
        "grs_certified": grs.get("grs_certified", False),
    }


async def get_extra_layer_7(company_name: str) -> dict:
    """All additional Layer 7 sources."""
    fca = await check_fca_register(company_name)
    ofsted = await check_ofsted(company_name)
    gazette = await check_gazette_broader(company_name)
    planning = await check_planning_portal(company_name)
    sfo = await check_sfo_cases(company_name)
    return {
        "fca": fca,
        "ofsted": ofsted,
        "gazette_broad": gazette,
        "planning": planning,
        "sfo": sfo,
        "fca_registered": fca.get("fca_registered", False),
        "has_ofsted_record": ofsted.get("has_ofsted_record", False),
        "gazette_total_notices": gazette.get("gazette_total_notices", 0),
        "planning_applications_found": planning.get("planning_applications_found", False),
        "sfo_prosecution": sfo.get("sfo_case_found", False),
    }


async def get_extra_layer_9(company_name: str) -> dict:
    """Additional Layer 9 sources."""
    fat = await check_find_a_tender(company_name)
    return {
        "find_a_tender": fat,
        "find_a_tender_found": fat.get("find_a_tender_found", False),
    }
