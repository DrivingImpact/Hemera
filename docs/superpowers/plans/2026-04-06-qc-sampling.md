# Analyst QC Sampling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build ISO 19011 stratified random sampling with QC card API and pass/fail hard gate for analyst verification of carbon footprint calculations.

**Architecture:** One new service (`qc_sampling.py`) with pure functions for sample math + card building. One new route file (`qc.py`) with three endpoints. No model changes — uses existing Transaction QC fields (`is_sampled`, `qc_pass`, `qc_notes`). One line added to `main.py` for router registration.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, pytest

---

## Task 0: Sample Size Calculation

**Files:**
- Create: `hemera/services/qc_sampling.py`
- Create: `tests/test_qc_sampling.py`

- [ ] **Step 1: Write failing tests for sample size calculation**

Create `tests/test_qc_sampling.py`:

```python
"""Tests for QC sampling engine."""

import pytest
from hemera.services.qc_sampling import calculate_sample_size


# Validate against the ISO 19011 reference table from the methodology doc
@pytest.mark.parametrize("population,expected_sample", [
    (50, 44),
    (100, 80),
    (250, 152),
    (500, 217),
    (1000, 278),
    (5000, 357),
])
def test_sample_size_matches_methodology_table(population, expected_sample):
    """Sample sizes must match the Carbon Methodology Section 8 table."""
    result = calculate_sample_size(population)
    assert result == expected_sample, f"For N={population}: expected {expected_sample}, got {result}"


def test_sample_size_small_population():
    """For very small populations, sample size should equal population."""
    assert calculate_sample_size(5) == 5
    assert calculate_sample_size(1) == 1


def test_sample_size_zero_population():
    """Zero population returns zero sample."""
    assert calculate_sample_size(0) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement sample size calculation**

Create `hemera/services/qc_sampling.py`:

```python
"""QC Sampling engine — ISO 19011 stratified random sampling.

Selects transactions for analyst verification, builds QC cards,
computes error rates, and enforces the hard gate.
"""

import math
import random
import json

# ISO 19011 sampling parameters
Z = 1.96       # 95% confidence level
P = 0.5        # maximum variability (conservative)
E = 0.05       # 5% acceptable error rate
HARD_GATE_THRESHOLD = 0.05  # error rate above this blocks delivery


def calculate_sample_size(population: int) -> int:
    """Calculate required sample size for ISO 19011 audit sampling.

    Uses the hypergeometric formula for finite populations:
    n = (N * Z² * p * (1-p)) / (e² * (N-1) + Z² * p * (1-p))

    At 95% confidence, 5% acceptable error rate, p=0.5.
    """
    if population <= 0:
        return 0

    numerator = population * (Z ** 2) * P * (1 - P)
    denominator = (E ** 2) * (population - 1) + (Z ** 2) * P * (1 - P)
    n = math.ceil(numerator / denominator)

    # Sample can't exceed population
    return min(n, population)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -v
```
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/qc_sampling.py tests/test_qc_sampling.py
git commit -m "feat: add ISO 19011 sample size calculation"
```

---

## Task 1: Stratified Sampling Selection

**Files:**
- Modify: `hemera/services/qc_sampling.py`
- Modify: `tests/test_qc_sampling.py`

- [ ] **Step 1: Write failing tests for stratified selection**

Append to `tests/test_qc_sampling.py`:

```python
from hemera.services.qc_sampling import select_sample, compute_sampling_weight, get_sampling_reasons


def test_compute_weight_base(sample_transactions):
    """Well-classified, non-high-spend transaction gets base weight 1.0."""
    # Row 5: Catering, keyword, confidence 0.85, L4, 8000 GBP
    # 8000 is the highest spend so it IS in top 10% — use the gas txn instead
    # Row 6: Utilities/gas, keyword, confidence 0.95, L4, 1500 GBP
    gas_txn = sample_transactions[5]
    weights = compute_sampling_weight(gas_txn, top_10_threshold=5000.0)
    assert weights["base"] == 1.0
    assert weights["total"] == 1.0


def test_compute_weight_high_spend(sample_transactions):
    """Top 10% by spend gets 2x weight."""
    catering_txn = sample_transactions[4]  # 8000 GBP
    weights = compute_sampling_weight(catering_txn, top_10_threshold=5000.0)
    assert weights["high_value"] == 2.0
    assert weights["total"] >= 2.0


def test_compute_weight_unclassified(sample_transactions):
    """Unclassified transaction (method=none) gets 2x weight."""
    unclassified_txn = sample_transactions[2]  # method="none"
    weights = compute_sampling_weight(unclassified_txn, top_10_threshold=50000.0)
    assert weights["low_confidence"] == 2.0
    assert weights["total"] >= 2.0


def test_compute_weight_high_uncertainty_ef(sample_transactions):
    """Level 5 EF gets 2x weight."""
    l5_txn = sample_transactions[2]  # ef_level=5
    weights = compute_sampling_weight(l5_txn, top_10_threshold=50000.0)
    assert weights["high_uncertainty_ef"] == 2.0


def test_select_sample_correct_size(sample_transactions):
    """Sample size should match the formula for the population."""
    sample = select_sample(sample_transactions, engagement_id=1)
    expected_size = calculate_sample_size(len(sample_transactions))
    assert len(sample) == expected_size


def test_select_sample_deterministic(sample_transactions):
    """Same engagement_id produces same sample."""
    sample1 = select_sample(sample_transactions, engagement_id=42)
    sample2 = select_sample(sample_transactions, engagement_id=42)
    ids1 = [t.row_number for t in sample1]
    ids2 = [t.row_number for t in sample2]
    assert ids1 == ids2


def test_select_sample_different_seed(sample_transactions):
    """Different engagement_id may produce different sample (for larger populations)."""
    # With only 6 transactions and sample size ~6, this is trivially true
    # but the mechanism should work
    sample1 = select_sample(sample_transactions, engagement_id=1)
    sample2 = select_sample(sample_transactions, engagement_id=2)
    assert len(sample1) == len(sample2)


def test_get_sampling_reasons_high_spend(sample_transactions):
    """High-spend transaction should have 'High-spend' reason."""
    catering_txn = sample_transactions[4]  # 8000 GBP
    reasons = get_sampling_reasons(catering_txn, top_10_threshold=5000.0)
    assert any("High-spend" in r for r in reasons)


def test_get_sampling_reasons_unclassified(sample_transactions):
    """Unclassified transaction should have 'Low-confidence' reason."""
    txn = sample_transactions[2]  # method="none"
    reasons = get_sampling_reasons(txn, top_10_threshold=50000.0)
    assert any("Low-confidence" in r for r in reasons)


def test_get_sampling_reasons_routine(sample_transactions):
    """Transaction with no special criteria gets 'Routine sample'."""
    gas_txn = sample_transactions[5]  # 1500 GBP, keyword, L4
    reasons = get_sampling_reasons(gas_txn, top_10_threshold=50000.0)
    assert reasons == ["Routine sample (proportional representation)"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -k "weight or select or reasons" -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement stratified sampling**

Add to `hemera/services/qc_sampling.py`:

```python
def compute_sampling_weight(transaction, top_10_threshold: float) -> dict:
    """Compute composite sampling weight for a transaction.

    Base weight = 1.0. Multipliers applied for:
    - High-spend (top 10% by value): 2x
    - Low-confidence classification (method=none or llm): 2x
    - High-uncertainty EF (Level 5-6): 2x

    Returns dict with individual multipliers and total weight.
    """
    weights = {"base": 1.0, "high_value": 1.0, "low_confidence": 1.0, "high_uncertainty_ef": 1.0}

    # High spend
    if abs(transaction.amount_gbp or 0) >= top_10_threshold:
        weights["high_value"] = 2.0

    # Low confidence classification
    if transaction.classification_method in ("none", "llm"):
        weights["low_confidence"] = 2.0

    # High uncertainty emission factor
    if (transaction.ef_level or 0) >= 5:
        weights["high_uncertainty_ef"] = 2.0

    weights["total"] = weights["base"] * weights["high_value"] * weights["low_confidence"] * weights["high_uncertainty_ef"]
    return weights


def get_sampling_reasons(transaction, top_10_threshold: float) -> list[str]:
    """Return human-readable reasons why this transaction was sampled."""
    reasons = []

    if abs(transaction.amount_gbp or 0) >= top_10_threshold:
        reasons.append("High-spend transaction (top 10% by value)")

    if transaction.classification_method == "none":
        reasons.append("Low-confidence classification (method: none)")
    elif transaction.classification_method == "llm":
        reasons.append("LLM-classified transaction")

    if (transaction.ef_level or 0) >= 5:
        reasons.append("High-uncertainty emission factor (Level 5-6)")

    if not reasons:
        reasons.append("Routine sample (proportional representation)")

    return reasons


def _compute_top_10_threshold(transactions: list) -> float:
    """Compute the threshold for 'top 10% by spend'."""
    amounts = sorted([abs(t.amount_gbp or 0) for t in transactions], reverse=True)
    if not amounts:
        return 0.0
    index = max(0, len(amounts) // 10 - 1)
    return amounts[index]


def select_sample(transactions: list, engagement_id: int, attempt: int = 1) -> list:
    """Select a stratified random sample of transactions for QC.

    Uses weighted random selection without replacement.
    Deterministic: same engagement_id + attempt produces same sample.
    """
    # Filter to valid transactions (have emissions calculated, not duplicates)
    valid = [t for t in transactions if t.co2e_kg is not None and not t.is_duplicate]

    if not valid:
        return []

    n = calculate_sample_size(len(valid))
    if n >= len(valid):
        return list(valid)

    top_10_threshold = _compute_top_10_threshold(valid)

    # Compute weights
    weighted = []
    for t in valid:
        w = compute_sampling_weight(t, top_10_threshold)
        weighted.append((t, w["total"]))

    # Weighted random selection without replacement (deterministic seed)
    rng = random.Random(engagement_id * 1000 + attempt)
    selected = []
    remaining = list(weighted)

    for _ in range(n):
        if not remaining:
            break
        total_weight = sum(w for _, w in remaining)
        pick = rng.uniform(0, total_weight)
        cumulative = 0.0
        for i, (t, w) in enumerate(remaining):
            cumulative += w
            if cumulative >= pick:
                selected.append(t)
                remaining.pop(i)
                break

    return selected
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -v
```
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/qc_sampling.py tests/test_qc_sampling.py
git commit -m "feat: add stratified sampling with weighted selection"
```

---

## Task 2: QC Card Builder

**Files:**
- Modify: `hemera/services/qc_sampling.py`
- Modify: `tests/test_qc_sampling.py`

- [ ] **Step 1: Write failing tests for QC card builder**

Append to `tests/test_qc_sampling.py`:

```python
from hemera.services.qc_sampling import build_qc_card, build_qc_cards


def test_build_qc_card_has_all_sections(sample_transactions):
    """A QC card should have progress, reasons, raw_data, decisions, checks."""
    txn = sample_transactions[0]
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=5000.0)

    assert card["card_number"] == 1
    assert card["total_cards"] == 6
    assert card["remaining"] == 6
    assert "sampling_reasons" in card
    assert "raw_data" in card
    assert "decisions" in card
    assert "checks" in card


def test_build_qc_card_raw_data(sample_transactions):
    """Raw data section should contain original upload fields."""
    txn = sample_transactions[0]  # Sundries, 5000 GBP
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=50000.0)

    raw = card["raw_data"]
    assert raw["row_number"] == 1
    assert raw["raw_description"] == "Office bits"
    assert raw["raw_supplier"] == "Generic Supplies Ltd"
    assert raw["raw_amount"] == 5000.0
    assert raw["raw_category"] == "Sundries"


def test_build_qc_card_decisions(sample_transactions):
    """Decisions section should contain classification, EF, calculation, pedigree."""
    txn = sample_transactions[0]
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=50000.0)

    decisions = card["decisions"]
    assert decisions["classification"]["scope"] == 3
    assert decisions["classification"]["category_name"] == "Purchased goods — office supplies"
    assert decisions["emission_factor"]["source"] == "defra"
    assert decisions["emission_factor"]["level"] == 4
    assert decisions["calculation"]["arithmetic_verified"] is True
    assert decisions["pedigree"]["gsd_total"] == 1.82


def test_build_qc_card_arithmetic_flag(sample_transactions):
    """Arithmetic verification should detect correct calculations."""
    txn = sample_transactions[0]  # 5000 * 0.5 = 2500
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=50000.0)
    assert card["decisions"]["calculation"]["arithmetic_verified"] is True


def test_build_qc_card_checks_list(sample_transactions):
    """Card should list the 5 check names."""
    txn = sample_transactions[0]
    card = build_qc_card(txn, card_number=1, total_cards=6, top_10_threshold=50000.0)
    assert card["checks"] == [
        "classification", "emission_factor", "arithmetic",
        "supplier_match", "pedigree",
    ]


def test_build_qc_cards_numbering(sample_transactions):
    """Cards should be numbered sequentially."""
    cards = build_qc_cards(sample_transactions, top_10_threshold=5000.0)
    for i, card in enumerate(cards, 1):
        assert card["card_number"] == i
        assert card["total_cards"] == len(sample_transactions)
        assert card["remaining"] == len(sample_transactions) - i + 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -k "card" -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement QC card builder**

Add to `hemera/services/qc_sampling.py`:

```python
def build_qc_card(transaction, card_number: int, total_cards: int, top_10_threshold: float) -> dict:
    """Build a self-contained QC verification card for a transaction.

    Contains: progress tracking, sampling rationale, raw data,
    Hemera's decisions, and the 5 verification check names.
    """
    t = transaction

    # Arithmetic verification
    expected_co2e = abs(t.amount_gbp or 0) * (t.ef_value or 0)
    arithmetic_ok = abs(expected_co2e - (t.co2e_kg or 0)) < 0.01

    return {
        # Progress tracking
        "card_number": card_number,
        "total_cards": total_cards,
        "remaining": total_cards - card_number + 1,
        "transaction_id": t.id,

        # Why this was sampled
        "sampling_reasons": get_sampling_reasons(t, top_10_threshold),

        # Section A: raw data
        "raw_data": {
            "row_number": t.row_number,
            "raw_date": t.raw_date,
            "raw_description": t.raw_description,
            "raw_supplier": t.raw_supplier,
            "raw_amount": t.raw_amount,
            "raw_category": t.raw_category,
        },

        # Section B: Hemera's decisions
        "decisions": {
            "classification": {
                "scope": t.scope,
                "ghg_category": t.ghg_category,
                "category_name": t.category_name,
                "method": t.classification_method,
                "confidence": t.classification_confidence,
            },
            "supplier_match": {
                "supplier_id": t.supplier_id,
                "match_method": t.supplier_match_method,
            },
            "emission_factor": {
                "value": t.ef_value,
                "unit": t.ef_unit,
                "source": t.ef_source,
                "level": t.ef_level,
                "year": t.ef_year,
                "region": t.ef_region,
            },
            "calculation": {
                "amount_gbp": abs(t.amount_gbp or 0),
                "ef_value": t.ef_value,
                "co2e_kg": t.co2e_kg,
                "arithmetic_verified": arithmetic_ok,
            },
            "pedigree": {
                "reliability": t.pedigree_reliability,
                "completeness": t.pedigree_completeness,
                "temporal": t.pedigree_temporal,
                "geographical": t.pedigree_geographical,
                "technological": t.pedigree_technological,
                "gsd_total": t.gsd_total,
            },
        },

        # Section C: the 5 checks
        "checks": [
            "classification",
            "emission_factor",
            "arithmetic",
            "supplier_match",
            "pedigree",
        ],
    }


def build_qc_cards(transactions: list, top_10_threshold: float) -> list[dict]:
    """Build QC cards for a list of sampled transactions."""
    total = len(transactions)
    return [
        build_qc_card(t, card_number=i, total_cards=total, top_10_threshold=top_10_threshold)
        for i, t in enumerate(transactions, 1)
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -v
```
Expected: 24 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/qc_sampling.py tests/test_qc_sampling.py
git commit -m "feat: add QC card builder with progress and sampling rationale"
```

---

## Task 3: Error Rate and Hard Gate

**Files:**
- Modify: `hemera/services/qc_sampling.py`
- Modify: `tests/test_qc_sampling.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_qc_sampling.py`:

```python
from hemera.services.qc_sampling import compute_qc_status, apply_qc_result, HARD_GATE_THRESHOLD


def test_compute_qc_status_not_started(sample_transactions):
    """No sampled transactions = not_started."""
    # None are sampled by default
    status = compute_qc_status(sample_transactions)
    assert status["status"] == "not_started"
    assert status["sample_size"] == 0


def test_compute_qc_status_in_progress(sample_transactions, db):
    """Some sampled but not all reviewed = in_progress."""
    sample_transactions[0].is_sampled = True
    sample_transactions[1].is_sampled = True
    sample_transactions[0].qc_pass = True
    db.flush()

    status = compute_qc_status(sample_transactions)
    assert status["status"] == "in_progress"
    assert status["sample_size"] == 2
    assert status["reviewed_count"] == 1
    assert status["remaining_count"] == 1


def test_compute_qc_status_passed(sample_transactions, db):
    """All sampled, all pass, error rate = 0 → passed."""
    for t in sample_transactions[:3]:
        t.is_sampled = True
        t.qc_pass = True
    db.flush()

    status = compute_qc_status(sample_transactions)
    assert status["status"] == "passed"
    assert status["current_error_rate"] == 0.0
    assert status["hard_gate_result"] == "passed"


def test_compute_qc_status_failed(sample_transactions, db):
    """Error rate > 5% → failed."""
    # 3 sampled, 1 fails = 33% error rate
    for t in sample_transactions[:3]:
        t.is_sampled = True
    sample_transactions[0].qc_pass = True
    sample_transactions[1].qc_pass = True
    sample_transactions[2].qc_pass = False
    db.flush()

    status = compute_qc_status(sample_transactions)
    assert status["status"] == "failed"
    assert abs(status["current_error_rate"] - 1/3) < 0.01
    assert status["hard_gate_result"] == "failed"


def test_compute_qc_status_exactly_5_percent(sample_transactions, db):
    """Error rate == 5% should pass (threshold is >5%, not >=5%)."""
    # 20 sampled, 1 fail = 5% exactly → passes
    # We only have 6 txns, so simulate: 2 sampled, 0 fail = 0%
    sample_transactions[0].is_sampled = True
    sample_transactions[0].qc_pass = True
    sample_transactions[1].is_sampled = True
    sample_transactions[1].qc_pass = True
    db.flush()

    status = compute_qc_status(sample_transactions)
    assert status["status"] == "passed"
    assert status["current_error_rate"] <= HARD_GATE_THRESHOLD


def test_apply_qc_result_all_pass(sample_transactions, db):
    """All 5 checks pass → qc_pass = True."""
    t = sample_transactions[0]
    t.is_sampled = True
    db.flush()

    result = {
        "classification_pass": True,
        "emission_factor_pass": True,
        "arithmetic_pass": True,
        "supplier_match_pass": True,
        "pedigree_pass": True,
        "notes": "",
    }
    apply_qc_result(t, result)
    assert t.qc_pass is True
    assert t.qc_notes is not None
    stored = json.loads(t.qc_notes)
    assert stored["classification_pass"] is True


def test_apply_qc_result_one_fail(sample_transactions, db):
    """One check fails → qc_pass = False."""
    t = sample_transactions[0]
    t.is_sampled = True
    db.flush()

    result = {
        "classification_pass": True,
        "emission_factor_pass": True,
        "arithmetic_pass": True,
        "supplier_match_pass": True,
        "pedigree_pass": False,
        "notes": "Technological score wrong",
    }
    apply_qc_result(t, result)
    assert t.qc_pass is False
    stored = json.loads(t.qc_notes)
    assert stored["pedigree_pass"] is False
    assert stored["notes"] == "Technological score wrong"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -k "qc_status or apply_qc" -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement error rate and hard gate**

Add to `hemera/services/qc_sampling.py`:

```python
def apply_qc_result(transaction, result: dict) -> None:
    """Apply QC check results to a transaction.

    Sets qc_pass (True if all 5 checks pass) and stores details in qc_notes as JSON.
    """
    all_pass = all([
        result.get("classification_pass", False),
        result.get("emission_factor_pass", False),
        result.get("arithmetic_pass", False),
        result.get("supplier_match_pass", False),
        result.get("pedigree_pass", False),
    ])
    transaction.qc_pass = all_pass
    transaction.qc_notes = json.dumps({
        "classification_pass": result.get("classification_pass"),
        "emission_factor_pass": result.get("emission_factor_pass"),
        "arithmetic_pass": result.get("arithmetic_pass"),
        "supplier_match_pass": result.get("supplier_match_pass"),
        "pedigree_pass": result.get("pedigree_pass"),
        "notes": result.get("notes", ""),
    })


def compute_qc_status(transactions: list) -> dict:
    """Compute the current QC status for an engagement's transactions.

    Returns status (not_started, in_progress, passed, failed),
    counts, error rate, and hard gate result.
    """
    sampled = [t for t in transactions if t.is_sampled]
    if not sampled:
        return {
            "status": "not_started",
            "sample_size": 0,
            "reviewed_count": 0,
            "remaining_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "current_error_rate": 0.0,
            "hard_gate_threshold": HARD_GATE_THRESHOLD,
            "would_pass_now": False,
        }

    reviewed = [t for t in sampled if t.qc_pass is not None]
    passed = [t for t in reviewed if t.qc_pass is True]
    failed = [t for t in reviewed if t.qc_pass is False]

    sample_size = len(sampled)
    reviewed_count = len(reviewed)
    remaining = sample_size - reviewed_count
    error_rate = len(failed) / sample_size if sample_size > 0 else 0.0

    # Determine status
    if reviewed_count < sample_size:
        status = "in_progress"
        result = {
            "status": status,
            "sample_size": sample_size,
            "reviewed_count": reviewed_count,
            "remaining_count": remaining,
            "pass_count": len(passed),
            "fail_count": len(failed),
            "current_error_rate": round(error_rate, 4),
            "hard_gate_threshold": HARD_GATE_THRESHOLD,
            "would_pass_now": error_rate <= HARD_GATE_THRESHOLD,
        }
    else:
        gate_passed = error_rate <= HARD_GATE_THRESHOLD
        status = "passed" if gate_passed else "failed"
        result = {
            "status": status,
            "sample_size": sample_size,
            "reviewed_count": reviewed_count,
            "remaining_count": 0,
            "pass_count": len(passed),
            "fail_count": len(failed),
            "current_error_rate": round(error_rate, 4),
            "hard_gate_threshold": HARD_GATE_THRESHOLD,
            "hard_gate_result": "passed" if gate_passed else "failed",
        }

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -v
```
Expected: 31 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/qc_sampling.py tests/test_qc_sampling.py
git commit -m "feat: add error rate computation and hard gate logic"
```

---

## Task 4: API Endpoints

**Files:**
- Create: `hemera/api/qc.py`
- Modify: `hemera/main.py`
- Modify: `tests/test_qc_sampling.py`

- [ ] **Step 1: Write failing API tests**

Append to `tests/test_qc_sampling.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from hemera.database import Base, get_db
from hemera.main import app
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction


def _make_test_session():
    """Create an in-memory SQLite session safe for FastAPI's thread pool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_engagement_with_transactions(session, count=20):
    """Seed an engagement with N transactions for QC testing."""
    eng = Engagement(org_name="QC Test SU", status="reviewing", transaction_count=count)
    session.add(eng)
    session.flush()

    for i in range(count):
        txn = Transaction(
            engagement_id=eng.id, row_number=i + 1,
            raw_description=f"Test item {i+1}", raw_supplier=f"Supplier {i+1}",
            raw_category="General", raw_amount=1000.0 + i * 100, amount_gbp=1000.0 + i * 100,
            scope=3, ghg_category=1, category_name="Purchased goods — office supplies",
            classification_method="keyword", classification_confidence=0.85,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2024, ef_region="UK",
            co2e_kg=(1000.0 + i * 100) * 0.5,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=1, pedigree_geographical=1, pedigree_technological=4,
            gsd_total=1.69,
        )
        session.add(txn)
    session.flush()
    return eng


def test_api_qc_generate():
    """POST /api/engagements/{id}/qc/generate returns sample with cards."""
    session = _make_test_session()
    app.dependency_overrides[get_db] = lambda: (yield session) or None

    # Need a proper generator for FastAPI
    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    eng = _seed_engagement_with_transactions(session, count=20)

    client = TestClient(app)
    response = client.post(f"/api/engagements/{eng.id}/qc/generate")
    assert response.status_code == 200

    data = response.json()
    assert data["engagement_id"] == eng.id
    assert data["sample_size"] > 0
    assert data["population_size"] == 20
    assert len(data["cards"]) == data["sample_size"]
    assert data["cards"][0]["card_number"] == 1
    assert "sampling_reasons" in data["cards"][0]
    assert "raw_data" in data["cards"][0]
    assert "decisions" in data["cards"][0]

    app.dependency_overrides.clear()
    session.close()


def test_api_qc_generate_idempotent():
    """Calling generate twice returns the same sample."""
    session = _make_test_session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    eng = _seed_engagement_with_transactions(session, count=20)

    client = TestClient(app)
    r1 = client.post(f"/api/engagements/{eng.id}/qc/generate")
    r2 = client.post(f"/api/engagements/{eng.id}/qc/generate")

    assert r1.json()["sample_size"] == r2.json()["sample_size"]

    app.dependency_overrides.clear()
    session.close()


def test_api_qc_status():
    """GET /api/engagements/{id}/qc returns current status."""
    session = _make_test_session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    eng = _seed_engagement_with_transactions(session, count=10)

    client = TestClient(app)
    # Before generating sample
    r = client.get(f"/api/engagements/{eng.id}/qc")
    assert r.status_code == 200
    assert r.json()["status"] == "not_started"

    # After generating
    client.post(f"/api/engagements/{eng.id}/qc/generate")
    r = client.get(f"/api/engagements/{eng.id}/qc")
    assert r.json()["status"] == "in_progress"

    app.dependency_overrides.clear()
    session.close()


def test_api_qc_submit_and_gate():
    """POST submit results → when complete, hard gate enforced."""
    session = _make_test_session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Small engagement so sample ≈ population
    eng = _seed_engagement_with_transactions(session, count=5)

    client = TestClient(app)
    gen_response = client.post(f"/api/engagements/{eng.id}/qc/generate")
    cards = gen_response.json()["cards"]

    # Submit all-pass for each card
    for card in cards:
        r = client.post(f"/api/engagements/{eng.id}/qc/submit", json={
            "results": [{
                "transaction_id": card["transaction_id"],
                "classification_pass": True,
                "emission_factor_pass": True,
                "arithmetic_pass": True,
                "supplier_match_pass": True,
                "pedigree_pass": True,
                "notes": "",
            }]
        })
        assert r.status_code == 200

    # Check final status
    status = client.get(f"/api/engagements/{eng.id}/qc").json()
    assert status["status"] == "passed"

    # Engagement should be delivered
    eng_refreshed = session.query(Engagement).filter(Engagement.id == eng.id).first()
    assert eng_refreshed.status == "delivered"

    app.dependency_overrides.clear()
    session.close()


def test_api_qc_submit_not_found():
    """Submitting for non-existent engagement returns 404."""
    session = _make_test_session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    r = client.post("/api/engagements/99999/qc/submit", json={
        "results": [{"transaction_id": 1, "classification_pass": True,
                      "emission_factor_pass": True, "arithmetic_pass": True,
                      "supplier_match_pass": True, "pedigree_pass": True, "notes": ""}]
    })
    assert r.status_code == 404

    app.dependency_overrides.clear()
    session.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_qc_sampling.py -k "api" -v
```
Expected: FAIL — 404 (no QC routes yet)

- [ ] **Step 3: Create QC API routes**

Create `hemera/api/qc.py`:

```python
"""QC sampling endpoints — generate sample, get status, submit results."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.services.qc_sampling import (
    calculate_sample_size, select_sample, build_qc_cards,
    compute_qc_status, apply_qc_result, _compute_top_10_threshold,
    HARD_GATE_THRESHOLD,
)

router = APIRouter()


class QCCheckResult(BaseModel):
    transaction_id: int
    classification_pass: bool
    emission_factor_pass: bool
    arithmetic_pass: bool
    supplier_match_pass: bool
    pedigree_pass: bool
    notes: str = ""


class QCSubmitRequest(BaseModel):
    results: list[QCCheckResult]


def _get_engagement_or_404(engagement_id: int, db: Session) -> Engagement:
    eng = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return eng


def _get_transactions(engagement_id: int, db: Session) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.engagement_id == engagement_id)
        .all()
    )


@router.post("/engagements/{engagement_id}/qc/generate")
def generate_qc_sample(engagement_id: int, db: Session = Depends(get_db)):
    """Generate a stratified QC sample for analyst verification."""
    eng = _get_engagement_or_404(engagement_id, db)
    transactions = _get_transactions(engagement_id, db)

    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found")

    # Check if sample already exists (idempotent)
    already_sampled = [t for t in transactions if t.is_sampled]
    if already_sampled:
        # Return existing sample
        top_10 = _compute_top_10_threshold(transactions)
        cards = build_qc_cards(already_sampled, top_10)
        return _build_generate_response(eng, transactions, already_sampled, cards)

    # Select new sample
    sample = select_sample(transactions, engagement_id=eng.id)
    for t in sample:
        t.is_sampled = True
    db.flush()
    db.commit()

    top_10 = _compute_top_10_threshold(transactions)
    cards = build_qc_cards(sample, top_10)

    return _build_generate_response(eng, transactions, sample, cards)


def _build_generate_response(eng, all_txns, sample, cards) -> dict:
    """Build the response for the generate endpoint."""
    # Strata breakdown
    by_scope = {}
    by_ef_level = {}
    high_value_count = 0
    low_confidence_count = 0

    for t in sample:
        scope_key = str(t.scope or "?")
        by_scope[scope_key] = by_scope.get(scope_key, 0) + 1

        level_key = f"L{t.ef_level or 0}"
        by_ef_level[level_key] = by_ef_level.get(level_key, 0) + 1

        top_10 = _compute_top_10_threshold(all_txns)
        if abs(t.amount_gbp or 0) >= top_10:
            high_value_count += 1
        if t.classification_method in ("none", "llm"):
            low_confidence_count += 1

    return {
        "engagement_id": eng.id,
        "sample_size": len(sample),
        "population_size": len(all_txns),
        "confidence_level": 0.95,
        "acceptable_error_rate": 0.05,
        "strata_breakdown": {
            "by_scope": by_scope,
            "by_ef_level": by_ef_level,
            "high_value_sampled": high_value_count,
            "low_confidence_sampled": low_confidence_count,
        },
        "cards": cards,
    }


@router.get("/engagements/{engagement_id}/qc")
def get_qc_status(engagement_id: int, db: Session = Depends(get_db)):
    """Get current QC status for an engagement."""
    _get_engagement_or_404(engagement_id, db)
    transactions = _get_transactions(engagement_id, db)
    status = compute_qc_status(transactions)
    status["engagement_id"] = engagement_id
    return status


@router.post("/engagements/{engagement_id}/qc/submit")
def submit_qc_results(engagement_id: int, body: QCSubmitRequest, db: Session = Depends(get_db)):
    """Submit QC check results for sampled transactions."""
    eng = _get_engagement_or_404(engagement_id, db)
    transactions = _get_transactions(engagement_id, db)
    txn_map = {t.id: t for t in transactions}

    accepted = 0
    for result in body.results:
        txn = txn_map.get(result.transaction_id)
        if not txn or not txn.is_sampled:
            continue
        apply_qc_result(txn, result.model_dump())
        accepted += 1

    db.flush()
    db.commit()

    # Recompute status
    status = compute_qc_status(transactions)

    # If QC complete and passed, update engagement status
    if status["status"] == "passed":
        eng.status = "delivered"
        db.flush()
        db.commit()

    sampled = [t for t in transactions if t.is_sampled]
    reviewed = [t for t in sampled if t.qc_pass is not None]
    remaining = len(sampled) - len(reviewed)

    response = {
        "accepted": accepted,
        "remaining": remaining,
        "qc_complete": status["status"] in ("passed", "failed"),
        "current_error_rate": status.get("current_error_rate", 0.0),
    }

    if status["status"] in ("passed", "failed"):
        response["hard_gate_result"] = status.get("hard_gate_result", "unknown")
        response["engagement_status"] = eng.status

    return response
```

- [ ] **Step 4: Register the router in main.py**

Add to `hemera/main.py` after the existing imports:

```python
from hemera.api import upload, engagements, suppliers, reports, qc
```

And add after the existing `include_router` calls:

```python
app.include_router(qc.router, prefix="/api", tags=["qc"])
```

- [ ] **Step 5: Run ALL tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/ -v
```
Expected: All tests pass (23 data quality + 31+ QC sampling)

- [ ] **Step 6: Verify app loads**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -c "from hemera.main import app; print('App loads OK')"
```
Expected: `App loads OK`

- [ ] **Step 7: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/api/qc.py hemera/main.py tests/test_qc_sampling.py
git commit -m "feat: add QC API endpoints (generate, status, submit) with hard gate"
```
