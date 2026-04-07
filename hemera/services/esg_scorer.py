"""ESG Scoring Engine — 7 weighted domains with modifiers.

Reads data from SupplierSource records (populated by the enrichment
orchestrator) and produces a 0-100 score across 7 weighted domains.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from hemera.models.supplier import SupplierSource


DOMAIN_WEIGHTS = {
    "governance_identity": 0.15,
    "labour_ethics": 0.20,
    "carbon_climate": 0.20,
    "water_biodiversity": 0.10,
    "product_supply_chain": 0.10,
    "transparency_disclosure": 0.10,
    "anti_corruption": 0.10,
    "social_value": 0.05,
}


@dataclass
class ESGResult:
    governance_identity: float = 50.0
    labour_ethics: float = 50.0
    carbon_climate: float = 50.0
    water_biodiversity: float = 50.0
    product_supply_chain: float = 50.0
    transparency_disclosure: float = 50.0
    anti_corruption: float = 50.0
    social_value: float = 50.0

    total_score: float = 0.0
    critical_flag: bool = False
    staleness_penalty: float = 1.0
    confidence: str = "low"
    layers_completed: int = 0

    flags: list[str] = field(default_factory=list)


def _get_data(sources: list[SupplierSource], layer: int) -> dict:
    """Merge all data from sources in a given layer into one dict."""
    merged = {}
    for s in sources:
        if s.layer == layer and s.data:
            merged.update(s.data)
    return merged


def calculate_esg_score(sources: list[SupplierSource]) -> ESGResult:
    """Calculate ESG score from all collected supplier source data."""
    result = ESGResult()
    layers_present = set(s.layer for s in sources)
    result.layers_completed = len(layers_present)

    # ── GOVERNANCE & IDENTITY (L1, L2, L9, L11) — 15% ──
    gov_score = 50.0

    l1 = _get_data(sources, 1)
    if l1:
        if l1.get("status") == "active":
            gov_score += 15
        elif l1.get("status") in ("dissolved", "liquidation"):
            gov_score -= 30
            result.flags.append("Company dissolved or in liquidation")
        if l1.get("has_recent_filings"):
            gov_score += 10
        if l1.get("has_insolvency_history"):
            gov_score -= 20
            result.flags.append("Insolvency history detected")
        if l1.get("filing_count", 0) > 0:
            gov_score += 5

    l2 = _get_data(sources, 2)
    if l2:
        if l2.get("psc_count", 0) > 0:
            gov_score += 5  # Transparency — PSCs disclosed
        if l2.get("is_sanctioned"):
            result.critical_flag = True
            result.flags.append("SANCTIONS HIT")
        if l2.get("is_pep"):
            gov_score -= 10
            result.flags.append("PEP detected among directors/PSCs")

    l9 = _get_data(sources, 9)
    if l9:
        if l9.get("has_government_contracts"):
            gov_score += 10  # Holding govt contracts = passed procurement screening

    l7 = _get_data(sources, 7)
    if l7:
        if l7.get("ico_enforcement"):
            gov_score = min(50, gov_score)
            result.flags.append("ICO enforcement action on record")
        if l7.get("charity_commission_inquiry"):
            gov_score = min(50, gov_score)
            result.flags.append("Active Charity Commission inquiry")

    result.governance_identity = max(0, min(100, gov_score))

    # ── LABOUR, ETHICS & MODERN SLAVERY (L5) — 20% ──
    labour_score = 50.0

    l5 = _get_data(sources, 5)
    if l5:
        if l5.get("modern_slavery_statement"):
            labour_score += 10
        if l5.get("living_wage_accredited"):
            labour_score += 15
        hse_count = l5.get("hse_enforcement_count", 0)
        if hse_count > 0:
            labour_score -= min(25, hse_count * 10)
            result.flags.append(f"HSE: {hse_count} enforcement actions")
        if l5.get("glaa_licence_revoked"):
            labour_score = 0
            result.critical_flag = True
            result.flags.append("CRITICAL: GLAA licence revoked")
        if l5.get("eti_member"):
            labour_score += 10
        if l5.get("disability_confident"):
            labour_score += 5

        gpg = l5.get("gender_pay_gap_median")
        if gpg is not None:
            if abs(gpg) < 5:
                labour_score += 10
            elif abs(gpg) > 20:
                labour_score -= 10

    result.labour_ethics = max(0, min(100, labour_score))

    # ── CARBON & CLIMATE (L4) — 20% ──
    carbon_score = 30.0  # Start lower — need evidence to score well

    l4 = _get_data(sources, 4)
    if l4:
        if l4.get("has_cdp_disclosure"):
            carbon_score += 25
        if l4.get("has_sbti_target"):
            carbon_score += 20
        if l4.get("carbon_trust_certified"):
            carbon_score += 10
        if l4.get("enforcement_count", 0) > 0 or l4.get("has_enforcement_actions"):
            carbon_score -= 20
            result.flags.append("Environment Agency enforcement actions")
        if l4.get("has_environmental_permits"):
            carbon_score += 5  # Having permits = regulated = some compliance
        if l4.get("self_reported_only"):
            carbon_score *= 0.85

    if l7:
        if l7.get("asa_rulings", 0) > 0:
            carbon_score -= 10
            result.flags.append("ASA ruling — potential greenwashing")

    if l9:
        if l9.get("ppn006_carbon_plan"):
            carbon_score += 10

    result.carbon_climate = max(0, min(100, carbon_score))

    # ── WATER, BIODIVERSITY & NATURAL CAPITAL (L10) — 10% ──
    water_score = 50.0
    l10 = _get_data(sources, 10)
    if l10:
        water_risk = l10.get("water_stress_level")
        if water_risk == "extreme":
            water_score -= 25
        elif water_risk == "high":
            water_score -= 15
        if l10.get("deforestation_alerts", 0) > 0:
            water_score -= 20
            result.flags.append("Deforestation alerts in supply geography")

    result.water_biodiversity = max(0, min(100, water_score))

    # ── PRODUCT & SUPPLY CHAIN (L6) — 10% ──
    product_score = 40.0

    l6 = _get_data(sources, 6)
    if l6:
        certs = l6.get("certifications", [])
        for cert in certs:
            if isinstance(cert, dict) and cert.get("verified"):
                product_score += 8
            else:
                product_score += 4
        if l6.get("b_corp"):
            product_score += 15
        if l6.get("iso_14001"):
            product_score += 10
        if l6.get("fsc_certified"):
            product_score += 8
        if l6.get("fairtrade"):
            product_score += 8
        if l6.get("cyber_essentials"):
            product_score += 5

    result.product_supply_chain = max(0, min(100, product_score))

    # ── TRANSPARENCY & DISCLOSURE (L3, L9) — 10% ──
    transparency_score = 50.0

    l3 = _get_data(sources, 3)
    if l3:
        charges = l3.get("charges_count", 0)
        if charges > 5:
            transparency_score -= 15
        elif charges > 0:
            transparency_score -= 5
        if l3.get("has_outstanding_charges"):
            transparency_score -= 10
        if l3.get("prompt_payment_code"):
            transparency_score += 10

    if l9:
        if l9.get("has_government_contracts"):
            transparency_score += 10

    result.transparency_disclosure = max(0, min(100, transparency_score))

    # ── ANTI-CORRUPTION & INTEGRITY (L2, L7, L11) — 10% ──
    integrity_score = 60.0  # Start slightly positive — assume clean unless flagged

    l11 = _get_data(sources, 11)
    if l11:
        if l11.get("world_bank_debarred"):
            result.critical_flag = True
            result.flags.append("CRITICAL: World Bank debarment")
        if l11.get("eu_debarred"):
            result.critical_flag = True
            result.flags.append("CRITICAL: EU debarment (EDES)")
        if l11.get("sfo_prosecution"):
            integrity_score -= 30
            result.flags.append("SFO prosecution history")

    if l2:
        if l2.get("is_pep"):
            integrity_score -= 15
        if l2.get("offshore_links"):
            integrity_score -= 15

    if l7:
        if l7.get("cma_cases", 0) > 0:
            integrity_score -= 15

    result.anti_corruption = max(0, min(100, integrity_score))

    # ── SOCIAL VALUE & COMMUNITY (L13) — 5% ──
    social_score = 40.0

    l13 = _get_data(sources, 13)
    if l13:
        if l13.get("is_social_enterprise"):
            social_score += 20
        if l13.get("is_cic"):
            social_score += 15
        if l13.get("b_corp") or (l6 and l6.get("b_corp")):
            social_score += 10

    # Living wage from L5 also counts here
    if l5 and l5.get("living_wage_accredited"):
        social_score += 15

    result.social_value = max(0, min(100, social_score))

    # ── STALENESS PENALTY ──
    fetched_dates = [s.fetched_at for s in sources if s.fetched_at]
    if fetched_dates:
        most_recent = max(fetched_dates)
        age = datetime.utcnow() - most_recent
        if age > timedelta(days=730):
            result.staleness_penalty = 0.70
        elif age > timedelta(days=365):
            result.staleness_penalty = 0.85

    # ── CALCULATE WEIGHTED TOTAL ──
    weighted = (
        result.governance_identity * DOMAIN_WEIGHTS["governance_identity"]
        + result.labour_ethics * DOMAIN_WEIGHTS["labour_ethics"]
        + result.carbon_climate * DOMAIN_WEIGHTS["carbon_climate"]
        + result.water_biodiversity * DOMAIN_WEIGHTS["water_biodiversity"]
        + result.product_supply_chain * DOMAIN_WEIGHTS["product_supply_chain"]
        + result.transparency_disclosure * DOMAIN_WEIGHTS["transparency_disclosure"]
        + result.anti_corruption * DOMAIN_WEIGHTS["anti_corruption"]
        + result.social_value * DOMAIN_WEIGHTS["social_value"]
    )

    weighted *= result.staleness_penalty

    if result.critical_flag:
        weighted = min(40, weighted)

    result.total_score = round(max(0, min(100, weighted)), 1)

    # ── CONFIDENCE RATING ──
    tier1_count = sum(1 for s in sources if s.tier and s.tier <= 1)
    if result.layers_completed >= 8 and tier1_count >= 5:
        result.confidence = "high"
    elif result.layers_completed >= 4:
        result.confidence = "medium"
    else:
        result.confidence = "low"

    return result
