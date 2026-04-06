"""CSV upload endpoint — accepts accounting data and runs the full pipeline."""

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.services.csv_parser import parse_accounting_csv
from hemera.services.classifier import classify_transaction
from hemera.services.supplier_match import match_suppliers_batch
from hemera.services.emission_calc import calculate_emissions
from hemera.services.seed_factors import seed_emission_factors
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser

router = APIRouter()


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: ClerkUser = Depends(get_current_user)):
    """Upload an accounting CSV/Excel file — runs the full carbon pipeline.

    Pipeline:
    1. Parse CSV -> transactions
    2. Classify each transaction (scope, GHG category)
    3. Match suppliers to registry (or create new)
    4. Calculate emissions with cascading factor lookup
    5. Score pedigree uncertainty per line item
    6. Aggregate to overall footprint with 95% CI
    """
    contents = await file.read()
    filename = file.filename or "upload.csv"

    # Ensure emission factors are seeded
    seed_emission_factors(db)

    # 1. Create engagement
    engagement = Engagement(
        org_name=current_user.org_name,
        upload_filename=filename,
        status="classifying",
    )
    db.add(engagement)
    db.flush()

    # 2. Parse the file
    transactions, parse_summary = parse_accounting_csv(contents, filename, engagement.id)

    # 3. Classify each transaction
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
            # Unclassified — default to Scope 3 Cat 1 with low confidence
            t.scope = 3
            t.ghg_category = 1
            t.category_name = "Unclassified — needs review"
            t.classification_method = "none"
            t.classification_confidence = 0.0
            t.needs_review = True
            unclassified_count += 1

    # 4. Match suppliers
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

    # Save transactions before calculating (need IDs)
    db.add_all(transactions)
    db.flush()

    # 5. Calculate emissions + pedigree uncertainty
    engagement.status = "calculating"
    calc_results = calculate_emissions(transactions, db)

    # 6. Update engagement summary
    engagement.status = "delivered"
    engagement.transaction_count = len(transactions)
    engagement.supplier_count = parse_summary["unique_suppliers"]
    engagement.total_co2e = calc_results["total_co2e_tonnes"]
    engagement.scope1_co2e = calc_results["scope1_kg"] / 1000
    engagement.scope2_co2e = calc_results["scope2_kg"] / 1000
    engagement.scope3_co2e = calc_results["scope3_kg"] / 1000
    engagement.gsd_total = calc_results["overall_gsd"]
    engagement.ci_lower = calc_results["ci_lower_tonnes"]
    engagement.ci_upper = calc_results["ci_upper_tonnes"]

    db.commit()

    return {
        "engagement_id": engagement.id,
        "filename": filename,
        "status": "delivered",
        "parsing": {
            "transactions_parsed": len(transactions),
            "duplicates_removed": parse_summary["duplicates_removed"],
            "date_range": parse_summary["date_range"],
            "total_spend_gbp": round(parse_summary["total_spend"], 2),
        },
        "classification": {
            "classified_by_keyword": classified_count,
            "unclassified_needs_review": unclassified_count,
        },
        "suppliers": {
            "unique_suppliers": parse_summary["unique_suppliers"],
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
