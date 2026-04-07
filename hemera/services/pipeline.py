"""Standalone processing pipeline — classification, supplier matching, emission calculation.

Separated from the upload endpoint so that upload is parse-only (free) and
processing can be triggered explicitly by an admin.
"""

from sqlalchemy.orm import Session
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.services.classifier import classify_transaction
from hemera.services.supplier_match import match_suppliers_batch
from hemera.services.emission_calc import calculate_emissions
from hemera.services.seed_factors import seed_emission_factors


def run_processing_pipeline(
    engagement: Engagement,
    transactions: list[Transaction],
    db: Session,
) -> dict:
    """Run the full classification + emission calculation pipeline.

    Expects engagement.status == "uploaded". Raises ValueError otherwise.
    Updates the engagement in-place and commits.

    Returns a summary dict.
    """
    if engagement.status != "uploaded":
        raise ValueError(
            f"Cannot process engagement {engagement.id}: "
            f"expected status 'uploaded', got '{engagement.status}'"
        )

    # Mark as in-progress
    engagement.status = "processing"
    db.flush()

    # 1. Classify each transaction
    classified_count = 0
    unclassified_count = 0
    for t in transactions:
        result = classify_transaction(t.raw_supplier, t.raw_description, t.raw_category)
        if result:
            t.scope = result.scope
            t.ghg_category = result.ghg_category
            t.category_name = result.category_name
            t.classification_method = result.method
            t.classification_confidence = result.confidence
            classified_count += 1
        else:
            t.scope = 3
            t.ghg_category = 1
            t.category_name = "Unclassified — needs review"
            t.classification_method = "none"
            t.classification_confidence = 0.0
            t.needs_review = True
            unclassified_count += 1

    # 2. Match suppliers
    raw_names = [t.raw_supplier for t in transactions if t.raw_supplier]
    supplier_map = match_suppliers_batch(raw_names, db)

    new_suppliers = 0
    for t in transactions:
        if t.raw_supplier and t.raw_supplier.strip() in supplier_map:
            supplier, method = supplier_map[t.raw_supplier.strip()]
            t.supplier_id = supplier.id
            t.supplier_match_method = method
            if method == "new":
                new_suppliers += 1

    db.flush()

    # 3. Seed emission factors then calculate emissions
    seed_emission_factors(db)
    calc_results = calculate_emissions(transactions, db)

    # 4. Update engagement summary
    engagement.total_co2e = calc_results["total_co2e_tonnes"]
    engagement.scope1_co2e = calc_results["scope1_kg"] / 1000
    engagement.scope2_co2e = calc_results["scope2_kg"] / 1000
    engagement.scope3_co2e = calc_results["scope3_kg"] / 1000
    engagement.gsd_total = calc_results["overall_gsd"]
    engagement.ci_lower = calc_results["ci_lower_tonnes"]
    engagement.ci_upper = calc_results["ci_upper_tonnes"]
    engagement.status = "delivered"

    db.commit()

    return {
        "engagement_id": engagement.id,
        "status": "delivered",
        "classification": {
            "classified": classified_count,
            "unclassified_needs_review": unclassified_count,
        },
        "suppliers": {
            "new_suppliers_created": new_suppliers,
        },
        "carbon_footprint": {
            "total_tCO2e": round(calc_results["total_co2e_tonnes"], 2),
            "scope1_tCO2e": round(calc_results["scope1_kg"] / 1000, 2),
            "scope2_tCO2e": round(calc_results["scope2_kg"] / 1000, 2),
            "scope3_tCO2e": round(calc_results["scope3_kg"] / 1000, 2),
            "uncertainty": {
                "overall_gsd": round(calc_results["overall_gsd"], 3),
                "ci_95_lower_tCO2e": round(calc_results["ci_lower_tonnes"], 2),
                "ci_95_upper_tCO2e": round(calc_results["ci_upper_tonnes"], 2),
            },
            "transactions_with_ef": calc_results["transactions_calculated"],
            "transactions_missing_ef": calc_results["transactions_missing_ef"],
        },
    }
