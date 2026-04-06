# Data Quality Improvement Report — Design Spec

**Date:** 2026-04-06
**Status:** Approved
**Scope:** New service + API endpoint for analysing data quality and recommending improvements

---

## 1. Purpose

Analyse an engagement's transaction data to identify where uncertainty comes from, quantify
its impact, and generate ranked recommendations for reducing it. This is a unique Hemera
feature (no competitor offers it — see Competitive Intelligence Grid Section 2) and a key
driver of the Progressive Accuracy Flywheel (Carbon Methodology Section 10).

**Audiences:**
- **Finance team:** Actionable chart-of-accounts restructuring recommendations
- **Sustainability/board:** Strategic overview of data quality, uncertainty breakdown, business case for improvement

**Delivery format:** JSON API response now, structured to feed directly into the PDF report
(a separate future feature).

---

## 2. Analysis Engine

The engine operates on existing transaction data — no re-calculation, no DB writes.
Four analysis dimensions:

### 2.1 Vague Code Detection

Identify transactions where the client's nominal code is too generic for precise emission
factor matching. Detection criteria (any of):

- `classification_method == "none"` (unclassified)
- `classification_confidence < 0.7` (low-confidence keyword match)
- `raw_category` matches a known vague-code list

**Known vague codes** (configurable list):
`sundries`, `general expenses`, `miscellaneous`, `other costs`, `office costs`,
`general supplies`, `other expenses`, `admin`, `administration`, `various`,
`petty cash`, `other overheads`, `general overheads`, `sundry expenses`,
`other purchases`, `unclassified`, `general`, `misc`

Output: list of vague codes with transaction count, total spend, and affected category_names.

### 2.2 Uncertainty Contribution Decomposition

For each transaction, compute its marginal contribution to overall footprint uncertainty
using the existing error propagation formula from `pedigree.py`:

```
contribution_i = (w_i * ln(GSD_i))^2 / sum_j((w_j * ln(GSD_j))^2)
where w_i = co2e_i / total_co2e
```

Group contributions by:
- `raw_category` (client's nominal code)
- `category_name` (Hemera classification)
- Supplier
- Scope (1/2/3)
- EF cascade level (1-6)

Rank by uncertainty contribution percentage (descending).

### 2.3 Cascade Level Distribution

Compute what percentage of spend (GBP) and emissions (tCO2e) sits at each EF cascade
level (1-6). Per the Carbon Methodology:

- Level 1-2: Low uncertainty (supplier-specific or activity-based DEFRA)
- Level 3: Moderate uncertainty (Exiobase MRIO)
- Level 4: Moderate-high (DEFRA EEIO spend-based)
- Level 5-6: High uncertainty (USEEIO/Climatiq fallback)

### 2.4 Pedigree Indicator Breakdown

For each of the 5 pedigree indicators (reliability, completeness, temporal, geographical,
technological), compute:

- Weighted average score across all transactions (weighted by co2e)
- Contribution to total uncertainty (% of total ln(GSD)^2)

Per the Carbon Methodology Section 7 Key Insight: "Technological correlation is often the
dominant contributor to Scope 3 uncertainty." The report proves this with data rather than
asserting it.

---

## 3. Recommendations Engine

Recommendations ranked by **impact score** = `spend_gbp * (current_gsd - projected_gsd)`.
This matches the Carbon Methodology Section 9: "ranked by impact (spend x uncertainty
reduction potential)."

### 3.1 Chart-of-Accounts Restructuring

**Trigger:** A vague nominal code covers transactions that Hemera classified into 2+
distinct `category_name` values.

**Output per recommendation:**
- The vague code and its total spend
- Suggested splits (derived from actual classification results for those transactions)
- Current average GSD for transactions under this code
- Projected GSD if transactions used more specific emission factors (one cascade level improvement)
- Uncertainty reduction percentage
- Human-readable explanation

**Example:** "47 transactions (GBP 82,000, 23% of Scope 3) used broad category codes
with average GSD 1.8. Splitting 'General Office Supplies' into 'Paper & Stationery',
'IT Equipment', and 'Cleaning Products' would reduce footprint uncertainty from +/-38%
to +/-19%."

### 3.2 Activity Data Collection

**Trigger:** Transactions use spend-based factors (Level 4-5) where activity-based
factors (Level 2) are achievable. Specifically:

| Category | Data needed | Source |
|----------|------------|--------|
| Electricity | kWh | Energy bills or supplier portal |
| Natural gas | kWh | Gas bills |
| Fleet fuel | Litres | Fuel card statements |
| Waste | Tonnes by type | Waste contractor reports |
| Business travel (rail) | Passenger-km | Booking confirmations |
| Business travel (air) | Passenger-km | Booking confirmations |
| Water | m3 | Water bills |

These map directly to the Carbon Methodology Section 4 Scope 3 table ("Best Method"
vs "Fallback" columns).

**Output per recommendation:**
- Category and current calculation method
- Recommended method and data needed
- Current GSD vs projected GSD
- Spend affected

### 3.3 Supplier Data Engagement

**Trigger:** High-spend suppliers currently at EF cascade Level 4+.

**Output per recommendation:**
- Supplier name and ID
- Total spend with this supplier
- Current EF level
- Projected EF level if supplier provides verified data (Level 1)
- Projected uncertainty reduction

This ties into the Supplier Engagement Service (Tier 3 pricing, GBP 200-500/supplier)
and the Progressive Accuracy Flywheel.

---

## 4. Benchmarks

Two benchmark types, both hardcoded constants for now (to be replaced by real sector
medians from the anonymised Benchmark Layer as client base grows):

### 4.1 Cascade Level Target

| Level | Current (typical Year 1) | Target (well-structured) |
|-------|-------------------------|-------------------------|
| L1 (supplier-specific) | 0% | 10% |
| L2 (activity-based) | 5% | 30% |
| L3 (Exiobase MRIO) | 0% | 20% |
| L4 (DEFRA EEIO) | 68% | 30% |
| L5-6 (fallback) | 27% | 10% |

### 4.2 Overall Data Quality Grade

Derived from cascade level distribution (by spend):

| Grade | Criteria |
|-------|---------|
| A | >60% of spend at L1-2 |
| B | >40% of spend at L1-3 |
| C | >60% of spend at L4+ (typical Year 1) |
| D | >80% of spend at L4+ |
| E | Majority unclassified or no EF matched |

---

## 5. API Endpoint

### `GET /api/engagements/{id}/data-quality`

Returns the full analysis as JSON. Computed on-demand from existing transaction data
(always reflects current state if transactions are re-classified or EFs updated).

### Response Schema

```json
{
  "engagement_id": 1,
  "generated_at": "2026-04-06T12:00:00Z",
  "summary": {
    "overall_gsd": 1.232,
    "ci_95_percent": "+/-55%",
    "total_spend_gbp": 245000.00,
    "total_co2e_tonnes": 17.6,
    "data_quality_grade": "C",
    "transactions_analysed": 150,
    "vague_code_count": 47,
    "vague_code_spend_gbp": 82000.00,
    "vague_code_spend_pct": 33.5,
    "projected_gsd_if_improved": 1.12,
    "projected_ci_95_percent": "+/-25%"
  },
  "cascade_distribution": {
    "current_by_spend_pct": {"L1": 0, "L2": 5, "L3": 0, "L4": 68, "L5": 27, "L6": 0},
    "current_by_co2e_pct": {"L1": 0, "L2": 8, "L3": 0, "L4": 62, "L5": 30, "L6": 0},
    "target_by_spend_pct": {"L1": 10, "L2": 30, "L3": 20, "L4": 30, "L5": 10, "L6": 0}
  },
  "uncertainty_contributors": [
    {
      "rank": 1,
      "raw_category": "General Office Supplies",
      "category_name": "Purchased goods — office supplies",
      "transaction_count": 23,
      "spend_gbp": 45000.00,
      "co2e_kg": 3200.0,
      "avg_gsd": 1.82,
      "uncertainty_contribution_pct": 34.2,
      "dominant_pedigree_indicator": "technological"
    }
  ],
  "pedigree_breakdown": {
    "reliability": {"weighted_avg_score": 3.2, "contribution_pct": 18},
    "completeness": {"weighted_avg_score": 2.8, "contribution_pct": 8},
    "temporal": {"weighted_avg_score": 1.5, "contribution_pct": 5},
    "geographical": {"weighted_avg_score": 1.2, "contribution_pct": 4},
    "technological": {"weighted_avg_score": 3.8, "contribution_pct": 65}
  },
  "recommendations": [
    {
      "rank": 1,
      "type": "chart_of_accounts",
      "impact_score": 892.0,
      "current_code": "General Office Supplies",
      "suggested_splits": ["Paper & Stationery", "IT Equipment", "Cleaning Products"],
      "spend_gbp": 45000.00,
      "current_avg_gsd": 1.82,
      "projected_avg_gsd": 1.35,
      "uncertainty_reduction_pct": 26.0,
      "explanation": "47 transactions under this code were classified into 3 distinct categories. Splitting the nominal code would allow more specific emission factors."
    },
    {
      "rank": 2,
      "type": "activity_data",
      "impact_score": 650.0,
      "category": "Purchased electricity",
      "current_method": "spend-based (Level 4)",
      "recommended_method": "activity-based kWh (Level 2)",
      "spend_gbp": 32000.00,
      "current_gsd": 1.69,
      "projected_gsd": 1.05,
      "data_needed": "kWh from electricity bills or supplier portal",
      "explanation": "Electricity spend is currently estimated from GBP. Providing kWh readings would move this from Level 4 to Level 2."
    },
    {
      "rank": 3,
      "type": "supplier_engagement",
      "impact_score": 420.0,
      "supplier_name": "Compass Group",
      "supplier_id": 12,
      "spend_gbp": 78000.00,
      "current_ef_level": 4,
      "projected_ef_level": 1,
      "explanation": "Compass Group is your largest supplier by spend. Requesting their emission intensity data would significantly reduce Scope 3 Cat 1 uncertainty."
    }
  ]
}
```

---

## 6. Architecture

### New files

| File | Purpose |
|------|---------|
| `hemera/services/data_quality.py` | Analysis + recommendations engine. Pure functions taking Transaction list, returning analysis dict. No DB writes. |

### Modified files

| File | Change |
|------|--------|
| `hemera/api/reports.py` | Replace placeholder with real `GET /api/engagements/{id}/data-quality` endpoint |

### No changes to

- Database models (no new tables, no migrations)
- Existing services (emission_calc, pedigree, classifier — consumed read-only)
- Upload pipeline

The report is computed on-demand. No caching needed for MVP — engagement sizes
(50-500 transactions) are small enough that computation is fast.

---

## 7. Testing Strategy

- Unit tests for each analysis function in `data_quality.py` using synthetic transaction data
- Test with the known 15-transaction test dataset (17.6 tCO2e, GSD 1.232)
- Verify uncertainty contribution percentages sum to 100%
- Verify recommendations are ranked by impact score descending
- Verify data quality grade matches cascade level distribution
- API integration test: upload CSV, then hit data-quality endpoint, verify response schema

---

## 8. What This Does NOT Include

- PDF report generation (separate priority item)
- Analyst QC sampling (separate priority item)
- Cross-client benchmarking from real data (future — requires Database 2 Benchmark Layer)
- Year-on-year data quality comparison (future — requires returning clients)
- Caching or background computation (not needed at current scale)
