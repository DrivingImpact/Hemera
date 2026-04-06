# Analyst QC Sampling — Design Spec

**Date:** 2026-04-06
**Status:** Approved
**Scope:** Stratified random sampling engine, QC card API, pass/fail hard gate

---

## 1. Purpose

Provide ISO 19011-aligned statistical sampling of carbon footprint calculations for
human analyst verification. The system selects the sample, presents each transaction
as a self-contained "QC card" with all context needed to verify, and enforces a hard
gate: error rate >5% blocks delivery.

This is a core differentiator — "analyst-verified" is part of the value proposition
(Carbon Methodology Section 8, Business Value Section 3.1). No competitor in the SME
market offers this.

---

## 2. Sample Size Calculation

ISO 19011 audit sampling at 95% confidence level, 5% acceptable error rate.

Formula (hypergeometric for finite populations):

```
n = (N * Z² * p * (1-p)) / (e² * (N-1) + Z² * p * (1-p))
where Z = 1.96, p = 0.5 (maximum variability), e = 0.05
```

Reference table (from Carbon Methodology):

| Population | Sample Size |
|-----------|-------------|
| 50 | 44 |
| 100 | 80 |
| 250 | 152 |
| 500 | 217 |
| 1,000 | 278 |
| 5,000 | 357 |

The function computes dynamically from the formula — the table is for validation only.

---

## 3. Stratified Sampling

The sample must be representative across risk dimensions. Four strata with weighting:

### 3.1 Scope (1/2/3)
Proportional to transaction count per scope. Ensures all scopes are represented.

### 3.2 EF Cascade Level (1-6)
Proportional, but Level 5-6 transactions get 2x sampling weight (higher uncertainty =
higher risk of error in factor selection).

### 3.3 Transaction Value
Top 10% of transactions by `abs(amount_gbp)` get 2x sampling weight. High-spend items
have disproportionate impact on the total footprint.

### 3.4 Classification Method
Transactions classified by `method="none"` or `method="llm"` get 2x sampling weight.
These are less certain than keyword matches.

**Selection algorithm:** Assign each transaction a composite weight (product of applicable
multipliers, base weight = 1.0). Draw `n` transactions using weighted random selection
without replacement.

**Deterministic seeding:** `random.seed(engagement_id)` ensures the same sample is
produced for the same engagement data. Re-generating after transaction changes produces
a new sample.

---

## 4. QC Card Format

Each sampled transaction is served as a self-contained verification card with three
sections.

### Sampling Rationale

Each card explains WHY this transaction was selected, so the analyst understands the
risk profile they're verifying:

```json
{
  "card_number": 12,
  "total_cards": 80,
  "remaining": 68,
  "sampling_reasons": [
    "High-spend transaction (top 10% by value)",
    "Level 5 emission factor (high uncertainty)"
  ]
}
```

`sampling_reasons` is a list of human-readable strings explaining which weighting
criteria applied. Possible reasons:
- "High-spend transaction (top 10% by value)"
- "Low-confidence classification (method: none)"
- "LLM-classified transaction"
- "High-uncertainty emission factor (Level 5-6)"
- "Routine sample (proportional representation)"

If no special weighting applied, the reason is "Routine sample."

### Section A — Raw Data (what the client uploaded)

```json
{
  "row_number": 5,
  "raw_date": "2024-03-15",
  "raw_description": "Monthly catering",
  "raw_supplier": "Compass Group",
  "raw_amount": 8000.00,
  "raw_category": "Catering"
}
```

### Section B — Hemera's Decisions (what we computed)

```json
{
  "classification": {
    "scope": 3,
    "ghg_category": 1,
    "category_name": "Purchased goods — catering/food",
    "method": "keyword",
    "confidence": 0.85
  },
  "supplier_match": {
    "matched_name": "Compass Group PLC",
    "match_method": "exact",
    "companies_house_number": "02457590"
  },
  "emission_factor": {
    "value": 0.5,
    "unit": "kgCO2e/GBP",
    "source": "defra",
    "level": 4,
    "year": 2022,
    "region": "UK"
  },
  "calculation": {
    "amount_gbp": 8000.00,
    "ef_value": 0.5,
    "co2e_kg": 4000.0,
    "arithmetic_verified": true
  },
  "pedigree": {
    "reliability": 3,
    "completeness": 2,
    "temporal": 2,
    "geographical": 1,
    "technological": 4,
    "gsd_total": 1.82
  }
}
```

The `arithmetic_verified` flag is pre-computed: `abs(amount_gbp * ef_value - co2e_kg) < 0.01`.

### Section C — Verification Prompts

Five checks for the analyst:

| # | Check | Question | Context Provided |
|---|-------|----------|-----------------|
| 1 | Classification | Is this the right scope and category? | Raw description + supplier + nominal code → assigned category |
| 2 | Emission factor | Is this the right emission factor? | Category → EF source, value, year |
| 3 | Arithmetic | Is the calculation correct? | amount × EF = result, pre-verified flag |
| 4 | Supplier match | Is this the right supplier entity? | Raw name → matched entity + Companies House number |
| 5 | Pedigree | Are the pedigree scores reasonable? | EF metadata → auto-assigned scores with scoring rules |

---

## 5. QC Workflow and Hard Gate

### Engagement Status Flow

```
uploaded → classifying → calculating → reviewing → delivered
                                          ↑
                                    QC lives here
```

When calculation completes, status moves to `reviewing`. The analyst generates the
QC sample, works through cards, submits results.

### Hard Gate

When all sampled transactions have been reviewed:

- **Error rate ≤ 5%**: QC passes. Engagement status → `delivered`.
- **Error rate > 5%**: QC fails. Engagement stays at `reviewing`. Cannot be delivered
  until errors are investigated and a re-sample passes.

**Error rate** = (transactions with any check failed) / (total sampled transactions)

### Re-sampling

If QC fails, the analyst investigates the failures, the pipeline is re-run or
manually corrected, and a new sample is generated. The new sample is independent
(different seed: `engagement_id + attempt_number`).

---

## 6. API Endpoints

### `POST /api/engagements/{id}/qc/generate`

Generate the QC sample for an engagement.

**Precondition:** Engagement status must be `reviewing` or `delivered`.

**Response:**
```json
{
  "engagement_id": 1,
  "sample_size": 80,
  "population_size": 100,
  "confidence_level": 0.95,
  "acceptable_error_rate": 0.05,
  "strata_breakdown": {
    "by_scope": {"1": 5, "2": 8, "3": 67},
    "by_ef_level": {"L4": 62, "L5": 18},
    "high_value_sampled": 12,
    "low_confidence_sampled": 15
  },
  "cards": [
    {
      "card_number": 1,
      "total_cards": 80,
      "remaining": 80,
      "sampling_reasons": ["High-spend transaction (top 10% by value)"],
      "raw_data": { "...Section A..." },
      "decisions": { "...Section B..." },
      "checks": ["classification", "emission_factor", "arithmetic", "supplier_match", "pedigree"]
    }
  ]
}
```

Sets `is_sampled = True` on selected transactions. Idempotent: if sample already
exists (transactions with `is_sampled = True`), returns existing sample.

### `GET /api/engagements/{id}/qc`

Get current QC status.

**Response:**
```json
{
  "engagement_id": 1,
  "status": "in_progress",
  "sample_size": 80,
  "reviewed_count": 45,
  "remaining_count": 35,
  "pass_count": 43,
  "fail_count": 2,
  "current_error_rate": 0.044,
  "hard_gate_threshold": 0.05,
  "would_pass_now": true
}
```

Status values: `not_started` (no sample), `in_progress`, `passed`, `failed`.

### `POST /api/engagements/{id}/qc/submit`

Submit QC results for one or more transactions.

**Request:**
```json
{
  "results": [
    {
      "transaction_id": 42,
      "classification_pass": true,
      "emission_factor_pass": true,
      "arithmetic_pass": true,
      "supplier_match_pass": true,
      "pedigree_pass": false,
      "notes": "Technological score should be 3 not 4"
    }
  ]
}
```

**Behavior:**
- Sets `qc_pass` on each transaction (True if all 5 checks pass, False otherwise)
- Stores check details + notes in `qc_notes` as JSON string
- When last sampled transaction is submitted, auto-computes error rate
- If error rate ≤ 5%: sets engagement status to `delivered`
- If error rate > 5%: keeps engagement at `reviewing`, returns failure details

**Response:**
```json
{
  "accepted": 1,
  "remaining": 34,
  "qc_complete": false,
  "current_error_rate": 0.044
}
```

Or when complete:
```json
{
  "accepted": 1,
  "remaining": 0,
  "qc_complete": true,
  "current_error_rate": 0.025,
  "hard_gate_result": "passed",
  "engagement_status": "delivered"
}
```

---

## 7. Architecture

### New files

| File | Purpose |
|------|---------|
| `hemera/services/qc_sampling.py` | Sample size calc, stratified selection, QC card builder, error rate computation, hard gate. Pure functions except for DB reads on card generation. |
| `hemera/api/qc.py` | Three QC endpoints |

### Modified files

| File | Change |
|------|--------|
| `hemera/main.py` | Add `app.include_router(qc.router, prefix="/api", tags=["qc"])` |

### No model changes

Transaction already has `is_sampled` (bool), `qc_pass` (bool|None), `qc_notes` (Text).
Per-check results stored as JSON in `qc_notes`:
```json
{
  "classification_pass": true,
  "emission_factor_pass": true,
  "arithmetic_pass": true,
  "supplier_match_pass": true,
  "pedigree_pass": false,
  "notes": "Technological score should be 3 not 4"
}
```

No new tables. No migrations.

---

## 8. Testing Strategy

- Unit tests for sample size calculation (validate against the methodology table)
- Unit tests for stratified selection (verify strata are represented, weights applied)
- Unit tests for QC card builder (verify all three sections populated)
- Unit tests for error rate computation and hard gate logic
- API integration tests: generate sample, submit results, verify gate enforcement
- Edge cases: engagement with 0 transactions, all-pass, all-fail, exactly 5% error rate

---

## 9. What This Does NOT Include

- Dashboard UI for QC cards (future — Next.js dashboard priority item)
- Automated pre-checks beyond arithmetic verification
- QC history/audit trail across multiple attempts (future)
- Analyst user accounts / assignment (depends on auth, separate priority item)
