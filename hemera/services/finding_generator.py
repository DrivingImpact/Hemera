# hemera/services/finding_generator.py
"""Generates supplier findings from ESGResult and domain scores.

Converts the deterministic scorer's output into structured finding dicts
ready to be stored as SupplierFinding rows.
"""

FLAG_MAPPING = {
    "SANCTIONS HIT": ("governance", "critical", 2, "opensanctions"),
    "CRITICAL: GLAA licence revoked": ("labour", "critical", 5, "glaa"),
    "CRITICAL: World Bank debarment": ("anti_corruption", "critical", 11, "world_bank"),
    "CRITICAL: EU debarment (EDES)": ("anti_corruption", "critical", 11, "eu_edes"),
    "Company dissolved or in liquidation": ("governance", "high", 1, "companies_house"),
    "Insolvency history detected": ("governance", "high", 1, "companies_house"),
    "PEP detected among directors/PSCs": ("governance", "medium", 2, "opensanctions"),
    "ICO enforcement action on record": ("governance", "medium", 7, "ico"),
    "Active Charity Commission inquiry": ("governance", "medium", 7, "charity_commission"),
    "Environment Agency enforcement actions": ("carbon", "high", 4, "environment_agency"),
    "ASA ruling — potential greenwashing": ("carbon", "medium", 7, "asa"),
    "Deforestation alerts in supply geography": ("water", "high", 10, "global_forest_watch"),
    "SFO prosecution history": ("anti_corruption", "high", 11, "sfo"),
}

DOMAIN_LOW_THRESHOLD = 35
DOMAIN_MEDIUM_THRESHOLD = 45
DOMAIN_HIGH_THRESHOLD = 70

DOMAIN_NAMES = {
    "governance_identity": "governance",
    "labour_ethics": "labour",
    "carbon_climate": "carbon",
    "water_biodiversity": "water",
    "product_supply_chain": "product",
    "transparency_disclosure": "transparency",
    "anti_corruption": "anti_corruption",
    "social_value": "social_value",
}

DOMAIN_LABELS = {
    "governance": "Governance & Identity",
    "labour": "Labour, Ethics & Modern Slavery",
    "carbon": "Carbon & Climate",
    "water": "Water, Biodiversity & Natural Capital",
    "product": "Product & Supply Chain",
    "transparency": "Transparency & Disclosure",
    "anti_corruption": "Anti-Corruption & Integrity",
    "social_value": "Social Value & Community",
}


def generate_findings_from_result(result, supplier_name: str) -> list[dict]:
    findings = []

    # 1. Convert each flag to a finding
    for flag_text in result.flags:
        if flag_text in FLAG_MAPPING:
            domain, severity, layer, source_name = FLAG_MAPPING[flag_text]
            findings.append({
                "source": "deterministic",
                "domain": domain,
                "severity": severity,
                "title": flag_text,
                "detail": f"{supplier_name}: {flag_text}. Identified from {source_name} data (Layer {layer}).",
                "layer": layer,
                "source_name": source_name,
            })
        else:
            if flag_text.startswith("HSE:"):
                findings.append({
                    "source": "deterministic",
                    "domain": "labour",
                    "severity": "high",
                    "title": flag_text,
                    "detail": f"{supplier_name}: {flag_text}. Health & Safety Executive enforcement records.",
                    "layer": 5,
                    "source_name": "hse",
                })
            else:
                findings.append({
                    "source": "deterministic",
                    "domain": "governance",
                    "severity": "medium",
                    "title": flag_text,
                    "detail": f"{supplier_name}: {flag_text}.",
                    "layer": None,
                    "source_name": "esg_scorer",
                })

    # 2. Generate findings from domain scores
    for attr, domain in DOMAIN_NAMES.items():
        score = getattr(result, attr)
        label = DOMAIN_LABELS[domain]

        if score < DOMAIN_LOW_THRESHOLD:
            existing_domains = {f["domain"] for f in findings if f["severity"] in ("critical", "high")}
            if domain not in existing_domains:
                findings.append({
                    "source": "deterministic",
                    "domain": domain,
                    "severity": "high",
                    "title": f"Low {label} score ({score:.0f}/100)",
                    "detail": f"{supplier_name} scores {score:.0f}/100 in {label}, significantly below the baseline of 50.",
                    "layer": None,
                    "source_name": "hemera_scorer",
                })
        elif score < DOMAIN_MEDIUM_THRESHOLD:
            existing_domains = {f["domain"] for f in findings}
            if domain not in existing_domains:
                findings.append({
                    "source": "deterministic",
                    "domain": domain,
                    "severity": "medium",
                    "title": f"Below-average {label} score ({score:.0f}/100)",
                    "detail": f"{supplier_name} scores {score:.0f}/100 in {label}, below the baseline of 50.",
                    "layer": None,
                    "source_name": "hemera_scorer",
                })
        elif score >= DOMAIN_HIGH_THRESHOLD:
            findings.append({
                "source": "deterministic",
                "domain": domain,
                "severity": "positive",
                "title": f"Strong {label} ({score:.0f}/100)",
                "detail": f"{supplier_name} demonstrates strong performance in {label} with a score of {score:.0f}/100.",
                "layer": None,
                "source_name": "hemera_scorer",
            })

    # 3. Low confidence / data coverage warning
    if result.confidence == "low":
        findings.append({
            "source": "deterministic",
            "domain": "governance",
            "severity": "info",
            "title": f"Low data coverage ({result.layers_completed}/13 layers)",
            "detail": f"Only {result.layers_completed} of 13 data layers returned information for {supplier_name}. The Hemera Score may not fully reflect this supplier's risk profile.",
            "layer": None,
            "source_name": "hemera_scorer",
        })

    return findings
