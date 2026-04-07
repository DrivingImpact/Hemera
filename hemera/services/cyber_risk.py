"""Digital, Data & Cyber Risk — Layer 12.

- Cyber Essentials (already in L6, cross-referenced here)
- ICO data breach notifications
- Basic website security check
"""

import httpx
import ssl


async def check_ico_breaches(company_name: str) -> dict:
    """Check ICO for reported data breaches involving the company.

    ICO publishes enforcement actions and data breach summaries.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://ico.org.uk/action-weve-taken/data-security-incident-trends/",
                params={"q": company_name},
            )
            if resp.status_code == 200:
                found = company_name.lower() in resp.text.lower()
                return {
                    "ico_breach_found": found,
                    "source": "ico.org.uk/breaches",
                }
    except Exception:
        pass
    return {"ico_breach_found": False, "source": "ico.org.uk/breaches"}


async def check_website_security(domain: str | None) -> dict:
    """Basic website security assessment.

    Checks: HTTPS support, valid SSL certificate.
    """
    if not domain:
        return {"website_checked": False, "note": "No domain provided"}

    # Ensure domain has https
    url = domain if domain.startswith("http") else f"https://{domain}"

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=True) as client:
            resp = await client.head(url, follow_redirects=True)
            has_https = str(resp.url).startswith("https")

            # Check security headers
            headers = resp.headers
            has_hsts = "strict-transport-security" in headers
            has_csp = "content-security-policy" in headers
            has_xframe = "x-frame-options" in headers

            header_score = sum([has_hsts, has_csp, has_xframe])

            return {
                "website_checked": True,
                "has_https": has_https,
                "has_hsts": has_hsts,
                "has_csp": has_csp,
                "has_xframe_options": has_xframe,
                "security_header_score": header_score,
                "ssl_valid": True,
                "source": "direct_check",
            }
    except httpx.ConnectError:
        return {"website_checked": True, "has_https": False, "ssl_valid": False,
                "source": "direct_check", "error": "Connection failed"}
    except Exception as e:
        return {"website_checked": True, "has_https": False, "ssl_valid": False,
                "source": "direct_check", "error": str(e)[:100]}


async def check_all_cyber_risk(company_name: str, domain: str | None = None) -> dict:
    """Run all Layer 12 checks."""
    ico = await check_ico_breaches(company_name)
    website = await check_website_security(domain) if domain else {"website_checked": False}

    return {
        "ico_breaches": ico,
        "website_security": website,
        "ico_breach_found": ico.get("ico_breach_found", False),
        "has_https": website.get("has_https"),
        "ssl_valid": website.get("ssl_valid"),
        "security_header_score": website.get("security_header_score"),
    }
