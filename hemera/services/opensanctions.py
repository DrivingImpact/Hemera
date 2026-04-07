"""OpenSanctions screening — Layer 2 & Layer 11 data source.

Screens company names and director/PSC names against:
- UK OFSI sanctions list
- EU sanctions
- UN sanctions
- PEP (Politically Exposed Persons) databases
- Interpol notices
- World Bank debarment list

API: https://api.opensanctions.org
Pricing: EUR 0.10 per successful match API call.
"""

import httpx


API_URL = "https://api.opensanctions.org/match/default"


async def screen_entity(
    name: str,
    schema: str = "LegalEntity",
    properties: dict | None = None,
) -> dict:
    """Screen a name against OpenSanctions.

    Args:
        name: entity name to screen
        schema: "LegalEntity" for companies, "Person" for individuals
        properties: additional properties (country, birthDate, etc.)

    Returns:
        dict with: matched (bool), results (list of matches), query details
    """
    props = {"name": [name]}
    if properties:
        props.update(properties)

    payload = {
        "schema": schema,
        "properties": props,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("responses", {}).get("results", [])
            # Filter to meaningful matches (score > 0.5)
            strong_matches = [
                {
                    "name": r.get("caption"),
                    "score": r.get("score"),
                    "schema": r.get("schema"),
                    "datasets": r.get("datasets", []),
                    "properties": {
                        k: v for k, v in r.get("properties", {}).items()
                        if k in ("country", "topics", "sanctions", "position",
                                 "birthDate", "nationality")
                    },
                }
                for r in results
                if r.get("score", 0) > 0.5
            ]

            return {
                "screened_name": name,
                "schema": schema,
                "matched": len(strong_matches) > 0,
                "match_count": len(strong_matches),
                "matches": strong_matches,
                "is_sanctioned": any(
                    "sanction" in str(m.get("properties", {}).get("topics", []))
                    for m in strong_matches
                ),
                "is_pep": any(
                    "role.pep" in str(m.get("properties", {}).get("topics", []))
                    for m in strong_matches
                ),
            }

    except httpx.HTTPStatusError as e:
        return {
            "screened_name": name,
            "matched": False,
            "error": f"API error: {e.response.status_code}",
        }
    except Exception as e:
        return {
            "screened_name": name,
            "matched": False,
            "error": str(e),
        }


async def screen_company(name: str, country: str = "gb") -> dict:
    """Screen a company name against sanctions and debarment lists."""
    return await screen_entity(
        name=name,
        schema="LegalEntity",
        properties={"country": [country]},
    )


async def screen_person(name: str, nationality: str | None = None) -> dict:
    """Screen an individual (director/PSC) against sanctions and PEP lists."""
    props = {}
    if nationality:
        props["nationality"] = [nationality]
    return await screen_entity(
        name=name,
        schema="Person",
        properties=props if props else None,
    )


async def screen_directors(officers: list[dict]) -> list[dict]:
    """Screen a list of company officers against sanctions/PEP.

    Args:
        officers: list from companies_house.get_officers()

    Returns:
        list of screening results, one per officer
    """
    results = []
    for officer in officers:
        name = officer.get("name")
        if not name or officer.get("resigned"):
            continue  # Skip resigned officers
        result = await screen_person(
            name=name,
            nationality=officer.get("nationality"),
        )
        result["role"] = officer.get("role")
        results.append(result)
    return results
