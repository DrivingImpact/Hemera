"""Complex scraping sources — structured data extraction from free public registers.

These sources require actual HTML parsing rather than simple name-in-page checks.
All scraping is polite: single sequential requests, reasonable timeouts, no parallelism.
No tokens/LLM used — pure HTML parsing with string operations.
"""

import re
import httpx
from datetime import datetime

TIMEOUT = 15.0
HEADERS = {
    "User-Agent": "Hemera-ESG-Research/1.0 (supply chain intelligence; contact@hemera.co.uk)",
    "Accept": "text/html,application/xhtml+xml",
}


async def _get_html(url: str, params: dict = None) -> str | None:
    """Fetch HTML with polite headers. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=HEADERS, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text
    except Exception:
        pass
    return None


# ── LAYER 2: ICIJ Offshore Leaks ──

async def check_icij_offshore(company_name: str) -> dict:
    """Search ICIJ Offshore Leaks database via their public search.

    Covers: Panama Papers, Paradise Papers, Pandora Papers, Offshore Leaks.
    https://offshoreleaks.icij.org/
    """
    html = await _get_html(
        "https://offshoreleaks.icij.org/search",
        params={"q": company_name, "c": "", "j": "", "d": ""},
    )
    if not html:
        return {"offshore_links": False, "source": "offshoreleaks.icij.org", "error": "fetch_failed"}

    # Count result entries
    lower = html.lower()
    result_count = lower.count('class="result"') + lower.count('class="search-result"')

    # Check for specific dataset mentions
    datasets_found = []
    for dataset in ["Panama Papers", "Paradise Papers", "Pandora Papers", "Offshore Leaks", "Bahamas Leaks"]:
        if dataset.lower() in lower:
            datasets_found.append(dataset)

    has_matches = result_count > 0 or len(datasets_found) > 0

    return {
        "offshore_links": has_matches,
        "result_count": result_count,
        "datasets_mentioned": datasets_found,
        "source": "offshoreleaks.icij.org",
    }


# ── LAYER 5: Modern Slavery Statement Registry (detailed) ──

async def scrape_modern_slavery_detailed(company_name: str) -> dict:
    """Detailed scrape of the Modern Slavery Statement Registry.

    Extracts: whether statement exists, reporting period, sector, turnover band.
    https://modern-slavery-statement-registry.service.gov.uk/
    """
    html = await _get_html(
        "https://modern-slavery-statement-registry.service.gov.uk/search",
        params={"Search": company_name},
    )
    if not html:
        return {"modern_slavery_statement": False, "source": "mss-registry", "error": "fetch_failed"}

    lower = html.lower()
    name_lower = company_name.lower()

    # Check if company appears in results
    if name_lower not in lower:
        return {"modern_slavery_statement": False, "source": "mss-registry"}

    # Try to extract details from the results page
    statement_data = {
        "modern_slavery_statement": True,
        "source": "mss-registry",
    }

    # Look for turnover band
    turnover_patterns = [
        r'turnover[^<]*?(\£[\d,]+\s*(?:million|billion|m|bn))',
        r'turnover[^<]*?(under|over|between)\s*\£[\d,]+',
    ]
    for pattern in turnover_patterns:
        match = re.search(pattern, lower)
        if match:
            statement_data["turnover_band"] = match.group(0).strip()
            break

    # Look for sector
    sector_match = re.search(r'sector[^<]*?:\s*([^<]+)', lower)
    if sector_match:
        statement_data["sector"] = sector_match.group(1).strip()[:100]

    return statement_data


# ── LAYER 7: Employment Tribunal (detailed) ──

async def scrape_employment_tribunals(company_name: str) -> dict:
    """Scrape Employment Tribunal decisions from GOV.UK.

    Extracts: case count, case types (unfair dismissal, discrimination, etc.),
    most recent decision date.
    https://www.gov.uk/employment-tribunal-decisions
    """
    html = await _get_html(
        "https://www.gov.uk/employment-tribunal-decisions",
        params={"tribunal_decision_categories[]": "", "query": company_name},
    )
    if not html:
        return {"tribunal_cases": 0, "source": "gov.uk/tribunals", "error": "fetch_failed"}

    lower = html.lower()
    name_lower = company_name.lower()

    if name_lower not in lower:
        return {"tribunal_cases": 0, "case_details": [], "source": "gov.uk/tribunals"}

    # Count case listings
    case_count = lower.count('class="gem-c-document-list__item"')
    if case_count == 0:
        case_count = lower.count('class="document-row"')
    if case_count == 0:
        # Fallback: count links that look like tribunal decisions
        case_count = len(re.findall(r'/employment-tribunal-decisions/[^"]+', html))

    # Extract case types from the page
    case_types = set()
    type_keywords = {
        "unfair dismissal": "Unfair Dismissal",
        "discrimination": "Discrimination",
        "redundancy": "Redundancy",
        "wages": "Unpaid Wages",
        "whistleblowing": "Whistleblowing",
        "harassment": "Harassment",
        "maternity": "Maternity/Paternity",
        "disability": "Disability Discrimination",
        "race": "Race Discrimination",
        "sex discrimination": "Sex Discrimination",
        "age discrimination": "Age Discrimination",
        "breach of contract": "Breach of Contract",
        "working time": "Working Time",
        "transfer of undertakings": "TUPE",
    }
    for keyword, label in type_keywords.items():
        if keyword in lower:
            case_types.add(label)

    # Try to find most recent date
    date_matches = re.findall(
        r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
        html,
    )
    most_recent = date_matches[0] if date_matches else None

    return {
        "tribunal_cases": case_count,
        "case_types": list(case_types),
        "most_recent_decision": most_recent,
        "has_discrimination_cases": bool(case_types & {
            "Discrimination", "Disability Discrimination",
            "Race Discrimination", "Sex Discrimination", "Age Discrimination",
        }),
        "has_whistleblowing": "Whistleblowing" in case_types,
        "source": "gov.uk/tribunals",
    }


# ── LAYER 7: Google News (adverse media search) ──

async def search_adverse_news(company_name: str) -> dict:
    """Search Google News for adverse coverage.

    Uses Google News RSS feed (no API key needed).
    Searches for company name + negative keywords.
    Minimal bandwidth: RSS XML only, no full article fetches.
    """
    negative_terms = [
        "scandal", "fraud", "fine", "fined", "prosecution", "lawsuit",
        "pollution", "contamination", "violation", "breach", "penalty",
        "investigation", "whistleblower", "corruption", "bribery",
        "modern slavery", "exploitation", "greenwashing", "recall",
    ]

    # Search company name in Google News RSS
    query = f'"{company_name}" UK'
    html = await _get_html(
        "https://news.google.com/rss/search",
        params={"q": query, "hl": "en-GB", "gl": "GB", "ceid": "GB:en"},
    )

    results = {
        "news_articles_found": 0,
        "adverse_articles": 0,
        "adverse_keywords_found": [],
        "source": "news.google.com",
    }

    if not html:
        return results

    # Count <item> entries (RSS items)
    items = re.findall(r'<item>(.*?)</item>', html, re.DOTALL)
    results["news_articles_found"] = len(items)

    # Check each item for adverse keywords
    adverse_keywords = set()
    adverse_count = 0
    for item in items:
        item_lower = item.lower()
        for term in negative_terms:
            if term in item_lower:
                adverse_keywords.add(term)
                adverse_count += 1
                break  # Only count once per article

    results["adverse_articles"] = adverse_count
    results["adverse_keywords_found"] = list(adverse_keywords)

    return results


# ── LAYER 4: UK ETS Registry ──

async def check_uk_ets(company_name: str) -> dict:
    """Check UK Emissions Trading Scheme registry.

    Companies in the UK ETS have verified annual emissions data.
    https://www.gov.uk/government/publications/uk-ets-registry
    """
    # The UK ETS account holder list is published as an Excel download
    # For MVP, we check the GOV.UK page for the company name
    html = await _get_html(
        "https://www.gov.uk/government/publications/uk-emissions-trading-scheme-and-eu-emissions-trading-system-installations",
    )
    if html and company_name.lower() in html.lower():
        return {
            "in_uk_ets": True,
            "source": "gov.uk/uk-ets",
            "note": "Company found in UK ETS publications — verified emissions data likely available",
        }
    return {"in_uk_ets": False, "source": "gov.uk/uk-ets"}


# ── LAYER 4: RSPO (Roundtable on Sustainable Palm Oil) ──

async def check_rspo(company_name: str) -> dict:
    """Check RSPO certification for palm oil supply chain.

    https://rspo.org/members/
    """
    html = await _get_html(
        "https://rspo.org/members/",
        params={"keywords": company_name},
    )
    if html and company_name.lower() in html.lower():
        # Try to extract membership type
        membership_type = None
        for mtype in ["Ordinary", "Supply Chain Associate", "Affiliate"]:
            if mtype.lower() in html.lower():
                membership_type = mtype
                break
        return {
            "rspo_member": True,
            "membership_type": membership_type,
            "source": "rspo.org",
        }
    return {"rspo_member": False, "source": "rspo.org"}


# ── LAYER 10: Global Forest Watch ──

async def check_global_forest_watch_detailed(company_name: str, country: str = "GBR") -> dict:
    """Check Global Forest Watch for deforestation data.

    Uses GFW's public API for country-level deforestation data.
    https://www.globalforestwatch.org/
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # GFW country-level tree cover loss
            resp = await client.get(
                f"https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/latest/query",
                params={
                    "sql": f"SELECT SUM(area__ha) as total_loss_ha, umd_tree_cover_loss__year "
                           f"FROM data WHERE iso = '{country[:3]}' "
                           f"AND umd_tree_cover_loss__year >= 2020 "
                           f"GROUP BY umd_tree_cover_loss__year "
                           f"ORDER BY umd_tree_cover_loss__year DESC LIMIT 5",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("data", [])
                if rows:
                    return {
                        "deforestation_data_available": True,
                        "country": country,
                        "recent_loss_hectares": rows,
                        "source": "globalforestwatch.org",
                    }
    except Exception:
        pass

    return {
        "deforestation_data_available": False,
        "country": country,
        "source": "globalforestwatch.org",
    }


# ── LAYER 7: UK Regulatory Decisions (GOV.UK) ──

async def scrape_gov_uk_regulatory(company_name: str) -> dict:
    """Search GOV.UK for regulatory decisions mentioning the company.

    Covers CMA, Ofgem, Ofcom, Ofwat, ORR decisions.
    """
    html = await _get_html(
        "https://www.gov.uk/search/all",
        params={"keywords": company_name, "content_purpose_supergroup[]": "transparency"},
    )
    if not html:
        return {"regulatory_decisions": 0, "source": "gov.uk/regulatory"}

    lower = html.lower()
    name_lower = company_name.lower()

    if name_lower not in lower:
        return {"regulatory_decisions": 0, "source": "gov.uk/regulatory"}

    # Count result items
    count = len(re.findall(r'class="gem-c-document-list__item"', html))
    if count == 0:
        count = lower.count('class="result-')

    return {
        "regulatory_decisions": count,
        "has_regulatory_decisions": count > 0,
        "source": "gov.uk/regulatory",
    }


# ── LAYER 6: BPMA (British Promotional Merchandise Association) ──

async def check_bpma(company_name: str) -> dict:
    """Check BPMA membership — relevant for SU merchandise suppliers."""
    html = await _get_html(
        "https://www.bpma.co.uk/find-a-member",
        params={"search": company_name},
    )
    if html and company_name.lower() in html.lower():
        return {"bpma_member": True, "source": "bpma.co.uk"}
    return {"bpma_member": False, "source": "bpma.co.uk"}


# ── LAYER 6: Portman Group (alcohol industry) ──

async def check_portman_group(company_name: str) -> dict:
    """Check Portman Group complaints rulings — alcohol industry regulation."""
    html = await _get_html(
        "https://www.portmangroup.org.uk/complaints-and-cases/",
        params={"s": company_name},
    )
    if html and company_name.lower() in html.lower():
        # Count rulings
        count = html.lower().count("ruling")
        return {"portman_rulings": count, "has_portman_rulings": count > 0, "source": "portmangroup.org.uk"}
    return {"portman_rulings": 0, "has_portman_rulings": False, "source": "portmangroup.org.uk"}


# ── BATCH RUNNERS ──

async def get_scraping_layer_2(company_name: str) -> dict:
    """Complex L2 scraping: ICIJ Offshore Leaks."""
    return await check_icij_offshore(company_name)


async def get_scraping_layer_4(company_name: str) -> dict:
    """Complex L4 scraping: UK ETS + RSPO."""
    ets = await check_uk_ets(company_name)
    rspo = await check_rspo(company_name)
    return {
        "uk_ets": ets,
        "rspo": rspo,
        "in_uk_ets": ets.get("in_uk_ets", False),
        "rspo_member": rspo.get("rspo_member", False),
    }


async def get_scraping_layer_5(company_name: str) -> dict:
    """Complex L5 scraping: Modern Slavery detailed."""
    return await scrape_modern_slavery_detailed(company_name)


async def get_scraping_layer_7(company_name: str) -> dict:
    """Complex L7 scraping: tribunals + news + regulatory."""
    tribunals = await scrape_employment_tribunals(company_name)
    news = await search_adverse_news(company_name)
    regulatory = await scrape_gov_uk_regulatory(company_name)

    return {
        "tribunals": tribunals,
        "adverse_news": news,
        "regulatory": regulatory,
        "tribunal_cases": tribunals.get("tribunal_cases", 0),
        "has_discrimination_cases": tribunals.get("has_discrimination_cases", False),
        "adverse_news_count": news.get("adverse_articles", 0),
        "adverse_keywords": news.get("adverse_keywords_found", []),
        "regulatory_decisions": regulatory.get("regulatory_decisions", 0),
    }


async def get_scraping_layer_6(company_name: str) -> dict:
    """Complex L6 scraping: BPMA + Portman Group."""
    bpma = await check_bpma(company_name)
    portman = await check_portman_group(company_name)
    return {
        "bpma": bpma,
        "portman": portman,
        "bpma_member": bpma.get("bpma_member", False),
        "portman_rulings": portman.get("portman_rulings", 0),
    }


async def get_scraping_layer_10(company_name: str) -> dict:
    """Complex L10 scraping: Global Forest Watch detailed."""
    return await check_global_forest_watch_detailed(company_name)
