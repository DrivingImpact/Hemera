"""Supplier enrichment orchestrator — runs the 13-layer intelligence protocol.

Coordinates data collection across all available layers for a given supplier,
stores results in supplier_sources, and calculates the ESG score.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from hemera.models.supplier import Supplier, SupplierScore, SupplierSource
from hemera.services import companies_house, opensanctions
from hemera.services.corporate_identity import check_all_corporate_identity
from hemera.services.environment_agency import check_environmental_record
from hemera.services.carbon_registries import check_all_carbon_registries
from hemera.services.financial_health import check_all_financial_health
from hemera.services.labour_sources import check_all_labour_sources
from hemera.services.certification_sources import check_all_certifications
from hemera.services.adverse_media import check_all_adverse_media
from hemera.services.government_contracts import search_contracts
from hemera.services.nature_risk import check_all_nature_risk
from hemera.services.debarment import check_all_debarment
from hemera.services.cyber_risk import check_all_cyber_risk
from hemera.services.social_value import check_all_social_value
from hemera.services.extra_sources import (
    get_extra_layer_1, get_extra_layer_5, get_extra_layer_6,
    get_extra_layer_7, get_extra_layer_9,
)
from hemera.services.scraping_sources import (
    get_scraping_layer_2, get_scraping_layer_4, get_scraping_layer_5,
    get_scraping_layer_6, get_scraping_layer_7, get_scraping_layer_10,
)
from hemera.services.esg_scorer import calculate_esg_score
from hemera.models.finding import SupplierFinding
from hemera.services.finding_generator import generate_findings_from_sources
from hemera.services.ai_task_runner import create_ai_task

log = logging.getLogger(__name__)


async def enrich_supplier(
    supplier: Supplier,
    db: Session,
    layers: list[int] | None = None,
) -> dict:
    """Run the enrichment protocol for a single supplier.

    Args:
        supplier: Supplier entity to enrich
        db: database session
        layers: specific layers to run (default: all available)

    Returns:
        dict with enrichment summary
    """
    if layers is None:
        layers = [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13]  # All built layers

    results = {"supplier_id": supplier.id, "name": supplier.name, "layers_run": []}
    name = supplier.legal_name or supplier.name

    # ── Layer 1: Corporate Identity (Companies House + extras) ──
    if 1 in layers:
        l1_data = await _run_layer_1(supplier, db)
        results["layers_run"].append({"layer": 1, "sources": len(l1_data)})
        name = supplier.legal_name or supplier.name

        # Additional L1 sources (OpenCorporates, OSCR)
        l1_extra = await _run_layer_1_extra(name, supplier.id, db)
        results["layers_run"][-1]["sources"] += l1_extra
        l1_extra2 = await _run_extra(name, supplier.id, 1, get_extra_layer_1, "extra_corporate", db)
        results["layers_run"][-1]["sources"] += l1_extra2

    # ── Layer 2: Ownership & Sanctions ──
    if 2 in layers:
        l2_data = await _run_layer_2(supplier, db)
        results["layers_run"].append({"layer": 2, "sources": len(l2_data)})
        l2_scrape = await _run_extra(name, supplier.id, 2, get_scraping_layer_2, "icij_offshore", db)
        results["layers_run"][-1]["sources"] += l2_scrape

    # ── Layer 3: Financial Health (CH charges + extras) ──
    if 3 in layers:
        l3_data = await _run_layer_3(supplier, db)
        results["layers_run"].append({"layer": 3, "sources": len(l3_data)})
        l3_extra = await _run_layer_3_extra(name, supplier.id, db)
        results["layers_run"][-1]["sources"] += l3_extra

    # ── Layer 4: Carbon & Environmental ──
    if 4 in layers:
        l4_data = await _run_layer_4(name, supplier.id, db)
        results["layers_run"].append({"layer": 4, "sources": l4_data})
        l4_scrape = await _run_extra(name, supplier.id, 4, get_scraping_layer_4, "scrape_carbon", db)
        results["layers_run"][-1]["sources"] += l4_scrape

    # ── Layer 5: Labour, Ethics & Modern Slavery ──
    if 5 in layers:
        l5_data = await _run_layer_5(name, supplier.id, db)
        results["layers_run"].append({"layer": 5, "sources": l5_data})
        l5_extra = await _run_extra(name, supplier.id, 5, get_extra_layer_5, "extra_labour", db)
        results["layers_run"][-1]["sources"] += l5_extra
        l5_scrape = await _run_extra(name, supplier.id, 5, get_scraping_layer_5, "scrape_slavery", db)
        results["layers_run"][-1]["sources"] += l5_scrape

    # ── Layer 6: Certifications ──
    if 6 in layers:
        l6_data = await _run_layer_6(name, supplier.id, db)
        results["layers_run"].append({"layer": 6, "sources": l6_data})
        l6_extra = await _run_extra(name, supplier.id, 6, get_extra_layer_6, "extra_certs", db)
        results["layers_run"][-1]["sources"] += l6_extra
        l6_scrape = await _run_extra(name, supplier.id, 6, get_scraping_layer_6, "scrape_certs", db)
        results["layers_run"][-1]["sources"] += l6_scrape

    # ── Layer 7: Adverse Media & Legal Record ──
    if 7 in layers:
        l7_data = await _run_layer_7(name, supplier.id, db)
        results["layers_run"].append({"layer": 7, "sources": l7_data})
        l7_extra = await _run_extra(name, supplier.id, 7, get_extra_layer_7, "extra_adverse", db)
        results["layers_run"][-1]["sources"] += l7_extra
        l7_scrape = await _run_extra(name, supplier.id, 7, get_scraping_layer_7, "scrape_adverse", db)
        results["layers_run"][-1]["sources"] += l7_scrape

    # ── Layer 9: Government Contracts ──
    if 9 in layers:
        l9_data = await _run_layer_9(name, supplier.id, db)
        results["layers_run"].append({"layer": 9, "sources": l9_data})
        l9_extra = await _run_extra(name, supplier.id, 9, get_extra_layer_9, "extra_procurement", db)
        results["layers_run"][-1]["sources"] += l9_extra

    # ── Layer 10: Water, Biodiversity & Nature ──
    if 10 in layers:
        l10_data = await _run_layer_10(name, supplier.id, db)
        results["layers_run"].append({"layer": 10, "sources": l10_data})
        l10_scrape = await _run_extra(name, supplier.id, 10, get_scraping_layer_10, "scrape_gfw", db)
        results["layers_run"][-1]["sources"] += l10_scrape

    # ── Layer 11: Anti-Bribery & Corruption ──
    if 11 in layers:
        l11_data = await _run_layer_11(name, supplier.id, db)
        results["layers_run"].append({"layer": 11, "sources": l11_data})

    # ── Layer 12: Digital, Data & Cyber Risk ──
    if 12 in layers:
        l12_data = await _run_layer_12(name, supplier.id, db)
        results["layers_run"].append({"layer": 12, "sources": l12_data})

    # ── Layer 13: Social Value ──
    if 13 in layers:
        l13_data = await _run_layer_13(name, supplier.entity_type, supplier.id, db)
        results["layers_run"].append({"layer": 13, "sources": l13_data})

    # ── Calculate ESG Score ──
    db.flush()  # Ensure all new sources are visible to the query
    all_sources = (
        db.query(SupplierSource)
        .filter(SupplierSource.supplier_id == supplier.id)
        .all()
    )
    esg_result = calculate_esg_score(all_sources)

    # Save score
    score = SupplierScore(
        supplier_id=supplier.id,
        governance_identity=esg_result.governance_identity,
        labour_ethics=esg_result.labour_ethics,
        carbon_climate=esg_result.carbon_climate,
        water_biodiversity=esg_result.water_biodiversity,
        product_supply_chain=esg_result.product_supply_chain,
        transparency_disclosure=esg_result.transparency_disclosure,
        anti_corruption=esg_result.anti_corruption,
        social_value=esg_result.social_value,
        hemera_score=esg_result.hemera_score,
        critical_flag=esg_result.critical_flag,
        staleness_penalty=esg_result.staleness_penalty,
        confidence=esg_result.confidence,
        layers_completed=esg_result.layers_completed,
    )
    db.add(score)

    # Supersede existing deterministic findings and generate fresh ones
    db.query(SupplierFinding).filter(
        SupplierFinding.supplier_id == supplier.id,
        SupplierFinding.source == "deterministic",
        SupplierFinding.is_active == True,
    ).update({"is_active": False, "superseded_at": datetime.utcnow()})

    all_sources = db.query(SupplierSource).filter(SupplierSource.supplier_id == supplier.id).all()
    finding_dicts = generate_findings_from_sources(all_sources, supplier_name=name)
    for fd in finding_dicts:
        finding = SupplierFinding(supplier_id=supplier.id, is_active=True, **fd)
        db.add(finding)

    # Update supplier summary
    supplier.hemera_score = esg_result.hemera_score
    supplier.confidence = esg_result.confidence
    supplier.critical_flag = esg_result.critical_flag
    supplier.updated_at = datetime.utcnow()
    if esg_result.layers_completed >= 3:
        supplier.status = "enriched"

    db.commit()

    results["hemera_score"] = esg_result.hemera_score
    results["confidence"] = esg_result.confidence
    results["critical_flag"] = esg_result.critical_flag
    results["flags"] = esg_result.flags
    results["layers_completed"] = esg_result.layers_completed
    results["findings_generated"] = len(finding_dicts)

    return results


# ── GENERIC EXTRA SOURCE RUNNER ──

async def _run_extra(name: str, supplier_id: int, layer: int, fetch_fn, source_name: str, db: Session) -> int:
    """Generic runner for extra sources. Calls fetch_fn(name), stores result."""
    try:
        data = await fetch_fn(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=layer, source_name=source_name,
            tier=2, data=data,
            summary=f"{source_name}: {sum(1 for v in data.values() if v is True)} positive signals",
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"Extra {source_name} error for '{name}': {e}")
        return 0


# ── LAYER RUNNERS ──

async def _run_layer_1(supplier: Supplier, db: Session) -> list:
    """Layer 1: Corporate Identity via Companies House."""
    sources_created = []
    try:
        if supplier.ch_number:
            profile = await companies_house.get_company(supplier.ch_number)
        else:
            search_results = await companies_house.search_company(supplier.name, limit=3)
            if not search_results:
                return sources_created
            profile = await companies_house.get_company(search_results[0]["ch_number"])

        if profile:
            supplier.ch_number = profile["ch_number"]
            supplier.legal_name = profile["name"]
            supplier.status = profile["status"]
            supplier.sic_codes = profile.get("sic_codes")
            supplier.entity_type = profile.get("type")
            if profile.get("registered_address"):
                addr = profile["registered_address"]
                if isinstance(addr, dict):
                    parts = [addr.get(k, "") for k in
                             ["address_line_1", "address_line_2", "locality",
                              "region", "postal_code", "country"]]
                    supplier.registered_address = ", ".join(p for p in parts if p)

            src = SupplierSource(
                supplier_id=supplier.id, layer=1, source_name="companies_house_profile",
                tier=1, data={**profile, "has_recent_filings": True,
                              "has_insolvency_history": profile.get("has_insolvency_history", False)},
                summary=f"CH {profile['ch_number']}: {profile['name']} ({profile['status']})",
                is_verified=True,
            )
            db.add(src)
            sources_created.append(src)

            filings = await companies_house.get_filing_history(profile["ch_number"])
            if filings:
                src2 = SupplierSource(
                    supplier_id=supplier.id, layer=1, source_name="companies_house_filings",
                    tier=1, data={"filings": filings, "filing_count": len(filings)},
                    summary=f"{len(filings)} recent filings", is_verified=True,
                )
                db.add(src2)
                sources_created.append(src2)

    except Exception as e:
        log.error(f"L1 error for '{supplier.name}': {e}")
    return sources_created


async def _run_layer_2(supplier: Supplier, db: Session) -> list:
    """Layer 2: Ownership & Sanctions."""
    sources_created = []
    try:
        if not supplier.ch_number:
            return sources_created

        pscs = await companies_house.get_psc(supplier.ch_number)
        if pscs:
            src = SupplierSource(
                supplier_id=supplier.id, layer=2, source_name="companies_house_psc",
                tier=1, data={"pscs": pscs, "psc_count": len(pscs)},
                summary=f"{len(pscs)} persons of significant control", is_verified=True,
            )
            db.add(src)
            sources_created.append(src)

        officers = await companies_house.get_officers(supplier.ch_number)
        company_screen = await opensanctions.screen_company(supplier.legal_name or supplier.name)
        sanctions_data = {
            "company_screening": company_screen,
            "is_sanctioned": company_screen.get("is_sanctioned", False),
            "is_pep": False, "director_screens": [],
        }

        if officers:
            director_screens = await opensanctions.screen_directors(officers)
            sanctions_data["director_screens"] = director_screens
            sanctions_data["is_pep"] = any(d.get("is_pep") for d in director_screens)
            if any(d.get("is_sanctioned") for d in director_screens):
                sanctions_data["is_sanctioned"] = True

        src2 = SupplierSource(
            supplier_id=supplier.id, layer=2, source_name="opensanctions",
            tier=1, data=sanctions_data,
            summary=f"Sanctions: {'HIT' if sanctions_data['is_sanctioned'] else 'clear'}, PEP: {'detected' if sanctions_data['is_pep'] else 'none'}",
            is_verified=True,
        )
        db.add(src2)
        sources_created.append(src2)

    except Exception as e:
        log.error(f"L2 error for '{supplier.name}': {e}")
    return sources_created


async def _run_layer_3(supplier: Supplier, db: Session) -> list:
    """Layer 3: Financial Health."""
    sources_created = []
    try:
        if not supplier.ch_number:
            return sources_created
        charges = await companies_house.get_charges(supplier.ch_number)
        src = SupplierSource(
            supplier_id=supplier.id, layer=3, source_name="companies_house_charges",
            tier=1, data={"charges": charges, "charges_count": len(charges),
                          "has_outstanding_charges": any(c.get("status") == "outstanding" for c in charges)},
            summary=f"{len(charges)} charges registered", is_verified=True,
        )
        db.add(src)
        sources_created.append(src)
    except Exception as e:
        log.error(f"L3 error for '{supplier.name}': {e}")
    return sources_created


async def _run_layer_4(name: str, supplier_id: int, db: Session) -> int:
    """Layer 4: Carbon & Environmental."""
    count = 0
    try:
        ea_data = await check_environmental_record(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=4, source_name="environment_agency",
            tier=1, data=ea_data,
            summary=f"EA: {ea_data['permit_count']} permits, {ea_data['enforcement_count']} enforcement actions",
            is_verified=True,
        )
        db.add(src)
        count += 1

        carbon_data = await check_all_carbon_registries(name)
        src2 = SupplierSource(
            supplier_id=supplier_id, layer=4, source_name="carbon_registries",
            tier=2, data=carbon_data,
            summary=f"SBTi: {'yes' if carbon_data['has_sbti_target'] else 'no'}, CDP: {'yes' if carbon_data['has_cdp_disclosure'] else 'no'}",
            is_verified=True,
        )
        db.add(src2)
        count += 1
    except Exception as e:
        log.error(f"L4 error for '{name}': {e}")
    return count


async def _run_layer_5(name: str, supplier_id: int, db: Session) -> int:
    """Layer 5: Labour, Ethics & Modern Slavery."""
    try:
        data = await check_all_labour_sources(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=5, source_name="labour_sources",
            tier=1, data=data,
            summary=(
                f"Modern slavery: {'yes' if data['modern_slavery_statement'] else 'no'}, "
                f"Living wage: {'yes' if data['living_wage_accredited'] else 'no'}, "
                f"HSE: {data['hse_enforcement_count']} actions"
            ),
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L5 error for '{name}': {e}")
        return 0


async def _run_layer_6(name: str, supplier_id: int, db: Session) -> int:
    """Layer 6: Certifications."""
    try:
        data = await check_all_certifications(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=6, source_name="certifications",
            tier=2, data=data,
            summary=f"{len(data.get('certifications', []))} verified certifications",
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L6 error for '{name}': {e}")
        return 0


async def _run_layer_7(name: str, supplier_id: int, db: Session) -> int:
    """Layer 7: Adverse Media & Legal Record."""
    try:
        data = await check_all_adverse_media(name)
        flags = []
        if data.get("ico_enforcement"):
            flags.append("ICO enforcement")
        if data.get("asa_rulings", 0) > 0:
            flags.append("ASA rulings")
        if data.get("cma_cases", 0) > 0:
            flags.append("CMA cases")

        src = SupplierSource(
            supplier_id=supplier_id, layer=7, source_name="adverse_media",
            tier=1, data=data,
            summary=f"{'No adverse findings' if not flags else ', '.join(flags)}",
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L7 error for '{name}': {e}")
        return 0


async def _run_layer_9(name: str, supplier_id: int, db: Session) -> int:
    """Layer 9: Government Contracts."""
    try:
        data = await search_contracts(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=9, source_name="contracts_finder",
            tier=1, data=data,
            summary=f"{data['contract_count']} government contracts found",
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L9 error for '{name}': {e}")
        return 0


async def _run_layer_11(name: str, supplier_id: int, db: Session) -> int:
    """Layer 11: Anti-Bribery & Corruption."""
    try:
        data = await check_all_debarment(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=11, source_name="debarment_checks",
            tier=1, data=data,
            summary=f"World Bank: {'DEBARRED' if data['world_bank_debarred'] else 'clear'}, EU: {'DEBARRED' if data['eu_debarred'] else 'clear'}",
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L11 error for '{name}': {e}")
        return 0


async def _run_layer_13(name: str, entity_type: str | None, supplier_id: int, db: Session) -> int:
    """Layer 13: Social Value & Community Impact."""
    try:
        data = await check_all_social_value(name, entity_type)
        src = SupplierSource(
            supplier_id=supplier_id, layer=13, source_name="social_value",
            tier=2, data=data,
            summary=f"Social enterprise: {'yes' if data['is_social_enterprise'] else 'no'}, CIC: {'yes' if data['is_cic'] else 'no'}",
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L13 error for '{name}': {e}")
        return 0


async def _run_layer_1_extra(name: str, supplier_id: int, db: Session) -> int:
    """Layer 1 extras: FSA ratings, Insolvency Service, Charity Commission detail."""
    try:
        data = await check_all_corporate_identity(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=1, source_name="corporate_identity_extra",
            tier=1, data=data,
            summary=(
                f"FSA: {'rated' if data.get('has_fsa_ratings') else 'n/a'}, "
                f"Charity: {'yes' if data.get('is_charity') else 'no'}, "
                f"Insolvency: {'found' if data.get('insolvency_records_found') else 'clear'}"
            ),
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L1 extra error for '{name}': {e}")
        return 0


async def _run_layer_3_extra(name: str, supplier_id: int, db: Session) -> int:
    """Layer 3 extras: Gender Pay Gap, Prompt Payment Code, Gazette."""
    try:
        data = await check_all_financial_health(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=3, source_name="financial_health_extra",
            tier=1, data=data,
            summary=(
                f"GPG: {'data' if data.get('has_gender_pay_data') else 'n/a'}, "
                f"PPC: {'yes' if data.get('prompt_payment_code_signatory') else 'no'}, "
                f"Gazette: {data.get('gazette_insolvency_notices', 0)} notices"
            ),
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L3 extra error for '{name}': {e}")
        return 0


async def _run_layer_10(name: str, supplier_id: int, db: Session) -> int:
    """Layer 10: Water, Biodiversity & Nature."""
    try:
        data = await check_all_nature_risk(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=10, source_name="nature_risk",
            tier=2, data=data,
            summary=f"Water: {data.get('water_stress_level', 'unknown')}, Biodiversity: {data.get('biodiversity_risk_level', 'unknown')}",
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L10 error for '{name}': {e}")
        return 0


async def _run_layer_12(name: str, supplier_id: int, db: Session) -> int:
    """Layer 12: Cyber Risk."""
    try:
        data = await check_all_cyber_risk(name)
        src = SupplierSource(
            supplier_id=supplier_id, layer=12, source_name="cyber_risk",
            tier=2, data=data,
            summary=f"ICO breach: {'yes' if data.get('ico_breach_found') else 'no'}",
            is_verified=True,
        )
        db.add(src)
        return 1
    except Exception as e:
        log.error(f"L12 error for '{name}': {e}")
        return 0


async def enrich_batch(
    suppliers: list[Supplier],
    db: Session,
    layers: list[int] | None = None,
) -> list[dict]:
    """Enrich multiple suppliers. Sequential to respect API rate limits."""
    results = []
    for supplier in suppliers:
        result = await enrich_supplier(supplier, db, layers)
        results.append(result)
    return results
