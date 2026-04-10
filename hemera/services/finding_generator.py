"""Generates supplier findings from raw source data.

Creates one finding per significant data point from each layer,
showing exactly what was found and how it affects the Hemera Score.
"""
from hemera.models.supplier import SupplierSource


def _get_data(sources: list[SupplierSource], layer: int) -> dict:
    """Merge all data from sources in a given layer."""
    merged = {}
    for s in sources:
        if s.layer == layer and s.data:
            merged.update(s.data)
    return merged


def _source_name_for_layer(sources: list[SupplierSource], layer: int) -> str:
    """Get the primary source name for a layer."""
    for s in sources:
        if s.layer == layer:
            return s.source_name
    return "unknown"


# Each check: (data_key, positive_check, title_if_true, title_if_false, domain, layer, severity_if_bad)
# positive_check: if True, having the data is good; if False, having it is bad
LAYER_CHECKS = [
    # Layer 1: Corporate Identity
    {"layer": 1, "key": "status", "domain": "governance",
     "check": lambda v: v == "active",
     "title_good": "Company status: Active",
     "title_bad": "Company status: {value}",
     "severity_bad": "high", "severity_good": "positive"},
    {"layer": 1, "key": "has_recent_filings", "domain": "governance",
     "check": lambda v: bool(v),
     "title_good": "Recent filings on record",
     "title_bad": "No recent filings found",
     "severity_bad": "medium", "severity_good": "info"},
    {"layer": 1, "key": "has_insolvency_history", "domain": "governance",
     "check": lambda v: not v,
     "title_good": "No insolvency history",
     "title_bad": "Insolvency history detected",
     "severity_bad": "high", "severity_good": "positive"},
    {"layer": 1, "key": "filing_count", "domain": "governance",
     "check": lambda v: (v or 0) > 0,
     "title_good": "{value} filings on record",
     "title_bad": "No filings on record",
     "severity_bad": "medium", "severity_good": "info"},

    # Layer 2: Ownership & Sanctions
    {"layer": 2, "key": "psc_count", "domain": "governance",
     "check": lambda v: (v or 0) > 0,
     "title_good": "{value} persons of significant control disclosed",
     "title_bad": "No PSCs disclosed",
     "severity_bad": "medium", "severity_good": "info"},
    {"layer": 2, "key": "is_sanctioned", "domain": "governance",
     "check": lambda v: not v,
     "title_good": "No sanctions detected",
     "title_bad": "SANCTIONS HIT",
     "severity_bad": "critical", "severity_good": "positive"},
    {"layer": 2, "key": "is_pep", "domain": "governance",
     "check": lambda v: not v,
     "title_good": "No PEPs detected",
     "title_bad": "PEP detected among directors/PSCs",
     "severity_bad": "medium", "severity_good": "info"},

    # Layer 3: Financial Health
    {"layer": 3, "key": "charges_count", "domain": "transparency",
     "check": lambda v: (v or 0) <= 5,
     "title_good": "{value} charges on record (within normal range)",
     "title_bad": "{value} charges on record (elevated)",
     "severity_bad": "medium", "severity_good": "info"},
    {"layer": 3, "key": "has_outstanding_charges", "domain": "transparency",
     "check": lambda v: not v,
     "title_good": "No outstanding charges",
     "title_bad": "Outstanding charges detected",
     "severity_bad": "medium", "severity_good": "info"},
    {"layer": 3, "key": "prompt_payment_code", "domain": "transparency",
     "check": lambda v: bool(v),
     "title_good": "Signed up to Prompt Payment Code",
     "title_bad": "Not signed up to Prompt Payment Code",
     "severity_bad": "info", "severity_good": "positive"},

    # Layer 4: Carbon & Environmental
    {"layer": 4, "key": "has_cdp_disclosure", "domain": "carbon",
     "check": lambda v: bool(v),
     "title_good": "CDP disclosure on record",
     "title_bad": "No CDP disclosure found",
     "severity_bad": "medium", "severity_good": "positive"},
    {"layer": 4, "key": "has_sbti_target", "domain": "carbon",
     "check": lambda v: bool(v),
     "title_good": "Science Based Target validated",
     "title_bad": "No Science Based Target",
     "severity_bad": "medium", "severity_good": "positive"},
    {"layer": 4, "key": "carbon_trust_certified", "domain": "carbon",
     "check": lambda v: bool(v),
     "title_good": "Carbon Trust certified",
     "title_bad": "No Carbon Trust certification",
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 4, "key": "has_enforcement_actions", "domain": "carbon",
     "check": lambda v: not v,
     "title_good": "No Environment Agency enforcement actions",
     "title_bad": "Environment Agency enforcement actions detected",
     "severity_bad": "high", "severity_good": "positive"},
    {"layer": 4, "key": "enforcement_count", "domain": "carbon",
     "check": lambda v: (v or 0) == 0,
     "title_good": "No environmental enforcement actions",
     "title_bad": "{value} environmental enforcement actions",
     "severity_bad": "high", "severity_good": "info",
     "skip_if_also": "has_enforcement_actions"},
    {"layer": 4, "key": "has_environmental_permits", "domain": "carbon",
     "check": lambda v: bool(v),
     "title_good": "Environmental permits held (regulated activity)",
     "title_bad": "No environmental permits on record",
     "severity_bad": "info", "severity_good": "info"},

    # Layer 5: Labour & Ethics
    {"layer": 5, "key": "modern_slavery_statement", "domain": "labour",
     "check": lambda v: bool(v),
     "title_good": "Modern Slavery Statement published",
     "title_bad": "No Modern Slavery Statement found",
     "severity_bad": "medium", "severity_good": "positive"},
    {"layer": 5, "key": "living_wage_accredited", "domain": "labour",
     "check": lambda v: bool(v),
     "title_good": "Living Wage accredited",
     "title_bad": "Not Living Wage accredited",
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 5, "key": "hse_enforcement_count", "domain": "labour",
     "check": lambda v: (v or 0) == 0,
     "title_good": "No HSE enforcement actions",
     "title_bad": "HSE: {value} enforcement actions",
     "severity_bad": "high", "severity_good": "positive"},
    {"layer": 5, "key": "glaa_licence_revoked", "domain": "labour",
     "check": lambda v: not v,
     "title_good": "No GLAA issues",
     "title_bad": "CRITICAL: GLAA licence revoked",
     "severity_bad": "critical", "severity_good": "info"},
    {"layer": 5, "key": "eti_member", "domain": "labour",
     "check": lambda v: bool(v),
     "title_good": "Ethical Trading Initiative member",
     "title_bad": "Not an ETI member",
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 5, "key": "disability_confident", "domain": "labour",
     "check": lambda v: bool(v),
     "title_good": "Disability Confident accredited",
     "title_bad": None,  # Don't create a finding if not present
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 5, "key": "gender_pay_gap_median", "domain": "labour",
     "check": lambda v: v is not None and abs(v) < 5,
     "title_good": "Gender pay gap: {value}% (within acceptable range)",
     "title_bad": "Gender pay gap: {value}%",
     "severity_bad": "medium", "severity_good": "positive"},

    # Layer 6: Certifications
    {"layer": 6, "key": "b_corp", "domain": "product",
     "check": lambda v: bool(v),
     "title_good": "B Corp certified",
     "title_bad": None,
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 6, "key": "iso_14001", "domain": "product",
     "check": lambda v: bool(v),
     "title_good": "ISO 14001 certified",
     "title_bad": None,
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 6, "key": "fsc_certified", "domain": "product",
     "check": lambda v: bool(v),
     "title_good": "FSC certified",
     "title_bad": None,
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 6, "key": "fairtrade", "domain": "product",
     "check": lambda v: bool(v),
     "title_good": "Fairtrade certified",
     "title_bad": None,
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 6, "key": "cyber_essentials", "domain": "product",
     "check": lambda v: bool(v),
     "title_good": "Cyber Essentials certified",
     "title_bad": None,
     "severity_bad": "info", "severity_good": "positive"},

    # Layer 7: Regulator Actions
    {"layer": 7, "key": "ico_enforcement", "domain": "governance",
     "check": lambda v: not v,
     "title_good": "No ICO enforcement actions",
     "title_bad": "ICO enforcement action on record",
     "severity_bad": "medium", "severity_good": "info"},
    {"layer": 7, "key": "charity_commission_inquiry", "domain": "governance",
     "check": lambda v: not v,
     "title_good": "No Charity Commission inquiries",
     "title_bad": "Active Charity Commission inquiry",
     "severity_bad": "medium", "severity_good": "info"},
    {"layer": 7, "key": "asa_rulings", "domain": "carbon",
     "check": lambda v: (v or 0) == 0,
     "title_good": "No ASA rulings",
     "title_bad": "{value} ASA rulings — potential greenwashing",
     "severity_bad": "medium", "severity_good": "info"},
    {"layer": 7, "key": "cma_cases", "domain": "anti_corruption",
     "check": lambda v: (v or 0) == 0,
     "title_good": "No CMA cases",
     "title_bad": "{value} CMA competition cases",
     "severity_bad": "medium", "severity_good": "info"},

    # Layer 9: Government Contracts
    {"layer": 9, "key": "has_government_contracts", "domain": "governance",
     "check": lambda v: bool(v),
     "title_good": "Holds government contracts (passed procurement screening)",
     "title_bad": "No government contracts on record",
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 9, "key": "ppn006_carbon_plan", "domain": "carbon",
     "check": lambda v: bool(v),
     "title_good": "PPN 06/21 Carbon Reduction Plan in place",
     "title_bad": None,
     "severity_bad": "info", "severity_good": "positive"},

    # Layer 10: Nature & Water
    {"layer": 10, "key": "water_stress_level", "domain": "water",
     "check": lambda v: v not in ("extreme", "high"),
     "title_good": "Water stress: {value} (acceptable)",
     "title_bad": "Water stress: {value}",
     "severity_bad": "high" if "extreme" else "medium", "severity_good": "info"},
    {"layer": 10, "key": "deforestation_alerts", "domain": "water",
     "check": lambda v: (v or 0) == 0,
     "title_good": "No deforestation alerts",
     "title_bad": "{value} deforestation alerts in supply geography",
     "severity_bad": "high", "severity_good": "info"},

    # Layer 11: Debarment
    {"layer": 11, "key": "world_bank_debarred", "domain": "anti_corruption",
     "check": lambda v: not v,
     "title_good": "Not on World Bank debarment list",
     "title_bad": "CRITICAL: World Bank debarment",
     "severity_bad": "critical", "severity_good": "info"},
    {"layer": 11, "key": "eu_debarred", "domain": "anti_corruption",
     "check": lambda v: not v,
     "title_good": "Not on EU EDES list",
     "title_bad": "CRITICAL: EU debarment (EDES)",
     "severity_bad": "critical", "severity_good": "info"},
    {"layer": 11, "key": "sfo_prosecution", "domain": "anti_corruption",
     "check": lambda v: not v,
     "title_good": "No SFO prosecution history",
     "title_bad": "SFO prosecution history",
     "severity_bad": "high", "severity_good": "info"},

    # Layer 13: Social Value
    {"layer": 13, "key": "is_social_enterprise", "domain": "social_value",
     "check": lambda v: bool(v),
     "title_good": "Registered social enterprise",
     "title_bad": None,
     "severity_bad": "info", "severity_good": "positive"},
    {"layer": 13, "key": "is_cic", "domain": "social_value",
     "check": lambda v: bool(v),
     "title_good": "Community Interest Company (CIC)",
     "title_bad": None,
     "severity_bad": "info", "severity_good": "positive"},
]


def generate_findings_from_sources(sources: list[SupplierSource], supplier_name: str) -> list[dict]:
    """Generate one finding per significant data point from each layer.

    Args:
        sources: All SupplierSource records for this supplier
        supplier_name: For detail text

    Returns:
        List of finding dicts ready for SupplierFinding rows.
    """
    findings = []
    layers_present = set(s.layer for s in sources)

    for check in LAYER_CHECKS:
        layer = check["layer"]
        if layer not in layers_present:
            continue

        data = _get_data(sources, layer)
        key = check["key"]

        if key not in data:
            continue

        value = data[key]
        is_good = check["check"](value)
        source_name = _source_name_for_layer(sources, layer)

        if is_good:
            title_template = check["title_good"]
            severity = check.get("severity_good", "info")
        else:
            title_template = check["title_bad"]
            severity = check.get("severity_bad", "medium")

        if title_template is None:
            continue  # Don't create a finding for this state

        title = title_template.format(value=value) if "{value}" in title_template else title_template

        findings.append({
            "source": "deterministic",
            "domain": check["domain"],
            "severity": severity,
            "title": title,
            "detail": f"Source: {source_name} (Layer {layer}). Data field: {key} = {value}",
            "layer": layer,
            "source_name": source_name,
        })

    # Low data coverage warning
    if len(layers_present) < 4:
        findings.append({
            "source": "deterministic",
            "domain": "governance",
            "severity": "info",
            "title": f"Low data coverage ({len(layers_present)}/13 layers)",
            "detail": f"Only {len(layers_present)} of 13 data layers returned information for {supplier_name}. The Hemera Score may not fully reflect this supplier's risk profile.",
            "layer": None,
            "source_name": "hemera_scorer",
        })

    return findings


# Keep backward compatibility
def generate_findings_from_result(result, supplier_name: str) -> list[dict]:
    """Legacy wrapper — generates findings from ESGResult flags.

    Prefer generate_findings_from_sources() which creates granular per-data-point findings.
    """
    findings = []
    for flag_text in result.flags:
        findings.append({
            "source": "deterministic",
            "domain": "governance",
            "severity": "high",
            "title": flag_text,
            "detail": f"{supplier_name}: {flag_text}.",
            "layer": None,
            "source_name": "esg_scorer",
        })

    if result.confidence == "low":
        findings.append({
            "source": "deterministic",
            "domain": "governance",
            "severity": "info",
            "title": f"Low data coverage ({result.layers_completed}/13 layers)",
            "detail": f"Only {result.layers_completed} of 13 data layers returned information for {supplier_name}.",
            "layer": None,
            "source_name": "hemera_scorer",
        })

    return findings
