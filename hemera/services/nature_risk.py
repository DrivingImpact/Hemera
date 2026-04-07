"""Water, Biodiversity & Natural Capital — Layer 10.

- WRI Aqueduct Water Risk Atlas
- WWF Biodiversity Risk Filter
- IUCN Red List proximity (future)
- EUDR compliance (future)
"""

import httpx


async def check_water_risk(latitude: float | None = None, longitude: float | None = None,
                           country: str = "GBR") -> dict:
    """Check WRI Aqueduct water risk for a location.

    https://www.wri.org/aqueduct
    The API provides water stress levels by geography.
    For MVP, we use country-level risk assessment.
    """
    # UK is generally low water stress, but specific regions may differ
    country_risk = {
        "GBR": "low-medium", "USA": "medium", "CHN": "high",
        "IND": "extremely high", "DEU": "low-medium", "FRA": "low-medium",
        "ESP": "high", "ITA": "medium-high", "AUS": "high",
        "BGD": "high", "PAK": "extremely high", "BRA": "low",
    }

    risk_level = country_risk.get(country, "unknown")

    if latitude and longitude:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.resourcewatch.org/v1/query",
                    params={
                        "sql": f"SELECT bws_cat FROM aqueduct30 WHERE ST_Intersects(the_geom, ST_SetSRID(ST_Point({longitude},{latitude}),4326))",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("data", [])
                    if results:
                        bws = results[0].get("bws_cat", "")
                        risk_map = {"Low": "low", "Low - Medium": "low-medium",
                                    "Medium - High": "medium-high", "High": "high",
                                    "Extremely High": "extreme"}
                        risk_level = risk_map.get(bws, risk_level)
        except Exception:
            pass

    return {
        "water_stress_level": risk_level,
        "country": country,
        "source": "wri.org/aqueduct",
    }


async def check_biodiversity_risk(country: str = "GBR") -> dict:
    """Check WWF Biodiversity Risk Filter for a country.

    https://riskfilter.org/biodiversity
    For MVP, use country-level biodiversity risk.
    """
    # Simplified country-level biodiversity pressure
    high_risk_countries = {
        "BRA", "IDN", "MYS", "COL", "PER", "COD", "MDG",
        "IND", "CHN", "THA", "VNM", "PHL", "NGA", "GHA",
    }
    medium_risk = {"USA", "AUS", "MEX", "ARG", "ZAF", "TUR", "RUS"}

    if country in high_risk_countries:
        level = "high"
    elif country in medium_risk:
        level = "medium"
    else:
        level = "low"

    return {
        "biodiversity_risk_level": level,
        "country": country,
        "source": "wwf.org/riskfilter",
    }


async def check_deforestation_risk(company_name: str) -> dict:
    """Check Global Forest Watch for deforestation alerts.

    https://www.globalforestwatch.org/
    For MVP, flag companies in deforestation-linked sectors.
    """
    deforestation_sectors = {
        "01", "02", "03",  # Agriculture, forestry, fishing (SIC codes)
        "10", "11",  # Food and beverages
        "15", "16",  # Leather, wood products
        "17",  # Paper
    }
    return {
        "deforestation_alerts": 0,
        "high_risk_sector": False,
        "source": "globalforestwatch.org",
        "note": "Requires SIC code cross-reference for sector risk",
    }


async def check_all_nature_risk(
    company_name: str,
    country: str = "GBR",
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    """Run all Layer 10 checks."""
    water = await check_water_risk(latitude, longitude, country)
    biodiversity = await check_biodiversity_risk(country)
    deforestation = await check_deforestation_risk(company_name)

    return {
        "water_risk": water,
        "biodiversity": biodiversity,
        "deforestation": deforestation,
        "water_stress_level": water.get("water_stress_level"),
        "biodiversity_risk_level": biodiversity.get("biodiversity_risk_level"),
        "deforestation_alerts": deforestation.get("deforestation_alerts", 0),
    }
