# Data Quality Improvement Report — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a data quality analysis engine and API endpoint that decomposes uncertainty, detects vague financial codes, and generates ranked recommendations for improving carbon footprint accuracy.

**Architecture:** One new pure-function service (`data_quality.py`) with no DB writes. One modified route file (`reports.py`) replacing placeholder. No model changes, no migrations. Tests use pytest with in-memory SQLite.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, pytest

---

## Task 0: Install pytest and create test infrastructure

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Install pytest**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/pip install pytest httpx
```

- [ ] **Step 2: Create test conftest with in-memory DB and test fixtures**

Create `tests/conftest.py`:

```python
"""Shared test fixtures — in-memory SQLite database and sample transactions."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hemera.database import Base
from hemera.models.transaction import Transaction
from hemera.models.engagement import Engagement
from hemera.models.supplier import Supplier
from hemera.models.emission_factor import EmissionFactor


@pytest.fixture
def db():
    """In-memory SQLite session for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_engagement(db):
    """A delivered engagement with summary stats."""
    e = Engagement(
        org_name="Test SU",
        status="delivered",
        transaction_count=6,
        total_co2e=5.0,
        gsd_total=1.5,
    )
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def sample_transactions(db, sample_engagement):
    """Six transactions covering key data quality scenarios.

    - 2 vague-code transactions (raw_category='Sundries', low confidence)
    - 1 unclassified transaction (classification_method='none')
    - 1 well-classified electricity transaction (scope 2, keyword, high confidence)
    - 1 spend-based catering transaction (scope 3, Level 4)
    - 1 high-spend supplier transaction (scope 3, Level 4)
    """
    txns = [
        # Vague code — classified as office supplies with low confidence
        Transaction(
            engagement_id=sample_engagement.id,
            row_number=1,
            raw_description="Office bits",
            raw_supplier="Generic Supplies Ltd",
            raw_category="Sundries",
            raw_amount=5000.0,
            amount_gbp=5000.0,
            scope=3, ghg_category=1,
            category_name="Purchased goods — office supplies",
            classification_method="keyword",
            classification_confidence=0.5,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2022, ef_region="UK",
            co2e_kg=2500.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=2, pedigree_geographical=1,
            pedigree_technological=4,
            gsd_total=1.82,
        ),
        # Vague code — classified as IT with low confidence
        Transaction(
            engagement_id=sample_engagement.id,
            row_number=2,
            raw_description="Computer stuff",
            raw_supplier="Tech World",
            raw_category="Sundries",
            raw_amount=3000.0,
            amount_gbp=3000.0,
            scope=3, ghg_category=1,
            category_name="Purchased goods — IT equipment",
            classification_method="keyword",
            classification_confidence=0.6,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2022, ef_region="UK",
            co2e_kg=1500.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=2, pedigree_geographical=1,
            pedigree_technological=4,
            gsd_total=1.82,
        ),
        # Unclassified
        Transaction(
            engagement_id=sample_engagement.id,
            row_number=3,
            raw_description="Payment ref 9921",
            raw_supplier="Unknown Co",
            raw_category="Miscellaneous",
            raw_amount=1000.0,
            amount_gbp=1000.0,
            scope=3, ghg_category=1,
            category_name="Unclassified — needs review",
            classification_method="none",
            classification_confidence=0.0,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=5, ef_year=2022, ef_region="UK",
            co2e_kg=500.0,
            pedigree_reliability=4, pedigree_completeness=4,
            pedigree_temporal=2, pedigree_geographical=1,
            pedigree_technological=5,
            gsd_total=2.1,
            needs_review=True,
        ),
        # Well-classified electricity (scope 2, keyword match)
        Transaction(
            engagement_id=sample_engagement.id,
            row_number=4,
            raw_description="Electricity bill Q1",
            raw_supplier="EDF Energy",
            raw_category="Utilities",
            raw_amount=2000.0,
            amount_gbp=2000.0,
            scope=2, ghg_category=None,
            category_name="Purchased electricity",
            classification_method="keyword",
            classification_confidence=0.95,
            ef_value=0.23, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2024, ef_region="UK",
            co2e_kg=460.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=1, pedigree_geographical=1,
            pedigree_technological=4,
            gsd_total=1.69,
        ),
        # Catering — scope 3 cat 1, spend-based
        Transaction(
            engagement_id=sample_engagement.id,
            row_number=5,
            raw_description="Monthly catering",
            raw_supplier="Compass Group",
            raw_category="Catering",
            raw_amount=8000.0,
            amount_gbp=8000.0,
            scope=3, ghg_category=1,
            category_name="Purchased goods — catering/food",
            classification_method="keyword",
            classification_confidence=0.85,
            ef_value=0.5, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2022, ef_region="UK",
            co2e_kg=4000.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=2, pedigree_geographical=1,
            pedigree_technological=4,
            gsd_total=1.82,
            supplier_id=None,
        ),
        # High-spend gas — scope 1
        Transaction(
            engagement_id=sample_engagement.id,
            row_number=6,
            raw_description="Gas bill",
            raw_supplier="British Gas",
            raw_category="Utilities",
            raw_amount=1500.0,
            amount_gbp=1500.0,
            scope=1, ghg_category=None,
            category_name="Stationary combustion — gas/heating fuel",
            classification_method="keyword",
            classification_confidence=0.95,
            ef_value=0.2, ef_unit="kgCO2e/GBP", ef_source="defra",
            ef_level=4, ef_year=2024, ef_region="UK",
            co2e_kg=300.0,
            pedigree_reliability=3, pedigree_completeness=2,
            pedigree_temporal=1, pedigree_geographical=1,
            pedigree_technological=4,
            gsd_total=1.69,
        ),
    ]
    db.add_all(txns)
    db.flush()
    return txns
```

- [ ] **Step 3: Verify fixtures load**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/ --co -q
```
Expected: no errors (no tests collected yet, but conftest loads cleanly)

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/Hemera
git add tests/conftest.py
git commit -m "test: add conftest with in-memory DB and sample transaction fixtures"
```

---

## Task 1: Vague code detection

**Files:**
- Create: `hemera/services/data_quality.py`
- Create: `tests/test_data_quality.py`

- [ ] **Step 1: Write failing test for vague code detection**

Create `tests/test_data_quality.py`:

```python
"""Tests for the data quality analysis engine."""

from hemera.services.data_quality import detect_vague_codes


def test_detect_vague_codes(sample_transactions):
    """Sundries and Miscellaneous should be flagged as vague."""
    result = detect_vague_codes(sample_transactions)

    assert len(result) == 2  # "Sundries" group and "Miscellaneous" group

    # Find the Sundries group
    sundries = next(r for r in result if r["raw_category"] == "Sundries")
    assert sundries["transaction_count"] == 2
    assert sundries["spend_gbp"] == 8000.0
    assert set(sundries["classified_as"]) == {
        "Purchased goods — office supplies",
        "Purchased goods — IT equipment",
    }

    # Miscellaneous group
    misc = next(r for r in result if r["raw_category"] == "Miscellaneous")
    assert misc["transaction_count"] == 1
    assert misc["spend_gbp"] == 1000.0


def test_well_classified_not_flagged(sample_transactions):
    """Utilities with high confidence should not be flagged."""
    result = detect_vague_codes(sample_transactions)
    raw_cats = [r["raw_category"] for r in result]
    assert "Utilities" not in raw_cats
    assert "Catering" not in raw_cats
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'hemera.services.data_quality'`

- [ ] **Step 3: Implement vague code detection**

Create `hemera/services/data_quality.py`:

```python
"""Data Quality Improvement Report engine.

Analyses engagement transactions to identify uncertainty sources and
generate ranked recommendations for improving carbon footprint accuracy.
Pure functions — no DB writes, no side effects.
"""

import math
from hemera.services.pedigree import (
    RELIABILITY_GSD, COMPLETENESS_GSD, TEMPORAL_GSD,
    GEOGRAPHICAL_GSD, TECHNOLOGICAL_GSD, BASIC_GSD,
)

# Nominal codes too vague for precise emission factor matching
VAGUE_CODES = {
    "sundries", "general expenses", "miscellaneous", "other costs",
    "office costs", "general supplies", "other expenses", "admin",
    "administration", "various", "petty cash", "other overheads",
    "general overheads", "sundry expenses", "other purchases",
    "unclassified", "general", "misc",
}


def detect_vague_codes(transactions: list) -> list[dict]:
    """Identify transactions with vague nominal codes.

    A transaction is vague if:
    - classification_method == 'none', OR
    - classification_confidence < 0.7, OR
    - raw_category (lowercased) is in the VAGUE_CODES set

    Returns list of vague code groups, each with:
    - raw_category, transaction_count, spend_gbp, classified_as
    """
    vague_txns = []
    for t in transactions:
        if t.co2e_kg is None or t.is_duplicate:
            continue
        raw_cat = (t.raw_category or "").strip()
        is_vague = (
            t.classification_method == "none"
            or (t.classification_confidence is not None and t.classification_confidence < 0.7)
            or raw_cat.lower() in VAGUE_CODES
        )
        if is_vague:
            vague_txns.append(t)

    # Group by raw_category
    groups: dict[str, list] = {}
    for t in vague_txns:
        key = (t.raw_category or "(blank)").strip()
        groups.setdefault(key, []).append(t)

    result = []
    for raw_cat, txns in groups.items():
        spend = sum(abs(t.amount_gbp or 0) for t in txns)
        classified_as = sorted({t.category_name for t in txns if t.category_name})
        result.append({
            "raw_category": raw_cat,
            "transaction_count": len(txns),
            "spend_gbp": spend,
            "classified_as": classified_as,
        })

    # Sort by spend descending
    result.sort(key=lambda r: r["spend_gbp"], reverse=True)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/data_quality.py tests/test_data_quality.py
git commit -m "feat: add vague code detection for data quality analysis"
```

---

## Task 2: Uncertainty contribution decomposition

**Files:**
- Modify: `hemera/services/data_quality.py`
- Modify: `tests/test_data_quality.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_data_quality.py`:

```python
from hemera.services.data_quality import compute_uncertainty_contributors


def test_uncertainty_contributors_sum_to_100(sample_transactions):
    """Contribution percentages must sum to ~100%."""
    result = compute_uncertainty_contributors(sample_transactions)
    total_pct = sum(r["uncertainty_contribution_pct"] for r in result)
    assert abs(total_pct - 100.0) < 0.1


def test_uncertainty_contributors_ranked_descending(sample_transactions):
    """Contributors should be ranked by uncertainty contribution."""
    result = compute_uncertainty_contributors(sample_transactions)
    pcts = [r["uncertainty_contribution_pct"] for r in result]
    assert pcts == sorted(pcts, reverse=True)


def test_uncertainty_contributors_fields(sample_transactions):
    """Each contributor should have required fields."""
    result = compute_uncertainty_contributors(sample_transactions)
    assert len(result) > 0
    first = result[0]
    assert "raw_category" in first
    assert "transaction_count" in first
    assert "spend_gbp" in first
    assert "co2e_kg" in first
    assert "avg_gsd" in first
    assert "uncertainty_contribution_pct" in first
    assert "dominant_pedigree_indicator" in first
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py::test_uncertainty_contributors_sum_to_100 -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement uncertainty contribution decomposition**

Add to `hemera/services/data_quality.py`:

```python
def _uncertainty_contribution(co2e: float, gsd: float, total_co2e: float) -> float:
    """Compute a single transaction's contribution to overall uncertainty.

    Uses the error propagation formula:
    contribution_i = (w_i * ln(GSD_i))^2
    where w_i = co2e_i / total_co2e
    """
    if total_co2e == 0 or gsd <= 0 or co2e <= 0:
        return 0.0
    weight = co2e / total_co2e
    return (weight * math.log(gsd)) ** 2


def _dominant_pedigree_indicator(t) -> str:
    """Return which pedigree indicator contributes most uncertainty for a transaction."""
    indicators = {
        "reliability": RELIABILITY_GSD.get(t.pedigree_reliability or 3, 1.61),
        "completeness": COMPLETENESS_GSD.get(t.pedigree_completeness or 3, 1.04),
        "temporal": TEMPORAL_GSD.get(t.pedigree_temporal or 3, 1.10),
        "geographical": GEOGRAPHICAL_GSD.get(t.pedigree_geographical or 3, 1.08),
        "technological": TECHNOLOGICAL_GSD.get(t.pedigree_technological or 3, 1.12),
    }
    # Dominant = highest ln(GSD)^2
    return max(indicators, key=lambda k: math.log(indicators[k]) ** 2)


def compute_uncertainty_contributors(transactions: list) -> list[dict]:
    """Decompose total uncertainty into contributions by raw_category.

    Returns list ranked by uncertainty_contribution_pct (descending).
    """
    valid = [t for t in transactions if t.co2e_kg and t.co2e_kg > 0 and not t.is_duplicate]
    total_co2e = sum(t.co2e_kg for t in valid)

    if total_co2e == 0:
        return []

    # Compute per-transaction contributions
    txn_contributions = []
    for t in valid:
        contrib = _uncertainty_contribution(t.co2e_kg, t.gsd_total or 1.0, total_co2e)
        txn_contributions.append((t, contrib))

    total_variance = sum(c for _, c in txn_contributions)
    if total_variance == 0:
        return []

    # Group by raw_category
    groups: dict[str, list[tuple]] = {}
    for t, contrib in txn_contributions:
        key = (t.raw_category or "(blank)").strip()
        groups.setdefault(key, []).append((t, contrib))

    result = []
    for raw_cat, items in groups.items():
        txns_in_group = [t for t, _ in items]
        group_variance = sum(c for _, c in items)
        group_co2e = sum(t.co2e_kg for t in txns_in_group)
        group_spend = sum(abs(t.amount_gbp or 0) for t in txns_in_group)
        gsd_values = [t.gsd_total for t in txns_in_group if t.gsd_total]

        # Find dominant indicator across the group (from the highest-contributing txn)
        top_txn = max(items, key=lambda x: x[1])[0]

        result.append({
            "raw_category": raw_cat,
            "transaction_count": len(txns_in_group),
            "spend_gbp": group_spend,
            "co2e_kg": group_co2e,
            "avg_gsd": sum(gsd_values) / len(gsd_values) if gsd_values else 1.0,
            "uncertainty_contribution_pct": round(group_variance / total_variance * 100, 1),
            "dominant_pedigree_indicator": _dominant_pedigree_indicator(top_txn),
        })

    result.sort(key=lambda r: r["uncertainty_contribution_pct"], reverse=True)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/data_quality.py tests/test_data_quality.py
git commit -m "feat: add uncertainty contribution decomposition by raw_category"
```

---

## Task 3: Cascade level distribution and pedigree breakdown

**Files:**
- Modify: `hemera/services/data_quality.py`
- Modify: `tests/test_data_quality.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_data_quality.py`:

```python
from hemera.services.data_quality import (
    compute_cascade_distribution,
    compute_pedigree_breakdown,
)


def test_cascade_distribution_sums_to_100(sample_transactions):
    """Spend percentages across levels should sum to ~100%."""
    result = compute_cascade_distribution(sample_transactions)
    spend_total = sum(result["current_by_spend_pct"].values())
    assert abs(spend_total - 100.0) < 0.1


def test_cascade_distribution_has_target(sample_transactions):
    """Should include target benchmarks."""
    result = compute_cascade_distribution(sample_transactions)
    assert "target_by_spend_pct" in result
    assert result["target_by_spend_pct"]["L2"] == 30  # from spec benchmarks


def test_cascade_all_level_4(sample_transactions):
    """Sample data is mostly Level 4 — verify it shows up."""
    result = compute_cascade_distribution(sample_transactions)
    # 5 of 6 transactions are L4, 1 is L5
    assert result["current_by_spend_pct"]["L4"] > 50


def test_pedigree_breakdown_contributions_sum_to_100(sample_transactions):
    """Pedigree indicator contributions should sum to ~100%."""
    result = compute_pedigree_breakdown(sample_transactions)
    total = sum(v["contribution_pct"] for v in result.values())
    assert abs(total - 100.0) < 0.1


def test_pedigree_technological_dominates(sample_transactions):
    """For spend-based Level 4 data, technological should dominate."""
    result = compute_pedigree_breakdown(sample_transactions)
    assert result["technological"]["contribution_pct"] > result["reliability"]["contribution_pct"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -k "cascade or pedigree" -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement cascade distribution and pedigree breakdown**

Add to `hemera/services/data_quality.py`:

```python
# Benchmark targets (hardcoded — will be replaced by real sector medians)
CASCADE_TARGET = {"L1": 10, "L2": 30, "L3": 20, "L4": 30, "L5": 10, "L6": 0}


def compute_cascade_distribution(transactions: list) -> dict:
    """Compute spend and emissions distribution across EF cascade levels."""
    valid = [t for t in transactions if t.co2e_kg is not None and not t.is_duplicate]
    total_spend = sum(abs(t.amount_gbp or 0) for t in valid)
    total_co2e = sum(t.co2e_kg for t in valid)

    spend_by_level = {f"L{i}": 0.0 for i in range(1, 7)}
    co2e_by_level = {f"L{i}": 0.0 for i in range(1, 7)}

    for t in valid:
        level_key = f"L{t.ef_level or 5}"
        if level_key not in spend_by_level:
            level_key = "L6"
        spend_by_level[level_key] += abs(t.amount_gbp or 0)
        co2e_by_level[level_key] += t.co2e_kg

    spend_pct = {
        k: round(v / total_spend * 100, 1) if total_spend > 0 else 0.0
        for k, v in spend_by_level.items()
    }
    co2e_pct = {
        k: round(v / total_co2e * 100, 1) if total_co2e > 0 else 0.0
        for k, v in co2e_by_level.items()
    }

    return {
        "current_by_spend_pct": spend_pct,
        "current_by_co2e_pct": co2e_pct,
        "target_by_spend_pct": CASCADE_TARGET.copy(),
    }


def compute_pedigree_breakdown(transactions: list) -> dict:
    """Compute weighted average and uncertainty contribution for each pedigree indicator."""
    valid = [t for t in transactions if t.co2e_kg and t.co2e_kg > 0 and not t.is_duplicate]
    total_co2e = sum(t.co2e_kg for t in valid)

    if total_co2e == 0:
        return {ind: {"weighted_avg_score": 0, "contribution_pct": 0}
                for ind in ["reliability", "completeness", "temporal", "geographical", "technological"]}

    gsd_maps = {
        "reliability": RELIABILITY_GSD,
        "completeness": COMPLETENESS_GSD,
        "temporal": TEMPORAL_GSD,
        "geographical": GEOGRAPHICAL_GSD,
        "technological": TECHNOLOGICAL_GSD,
    }
    score_attrs = {
        "reliability": "pedigree_reliability",
        "completeness": "pedigree_completeness",
        "temporal": "pedigree_temporal",
        "geographical": "pedigree_geographical",
        "technological": "pedigree_technological",
    }

    # Weighted average scores
    weighted_scores = {}
    for ind, attr in score_attrs.items():
        weighted_sum = sum(
            (getattr(t, attr) or 3) * t.co2e_kg for t in valid
        )
        weighted_scores[ind] = round(weighted_sum / total_co2e, 1)

    # Contribution: how much of total ln(GSD)^2 comes from each indicator
    # Total variance per indicator = sum over txns of (w_i * ln(GSD_indicator_i))^2
    indicator_variance = {ind: 0.0 for ind in gsd_maps}
    for t in valid:
        weight = t.co2e_kg / total_co2e
        for ind, gsd_map in gsd_maps.items():
            score = getattr(t, score_attrs[ind]) or 3
            gsd_val = gsd_map.get(score, 1.0)
            indicator_variance[ind] += (weight * math.log(gsd_val)) ** 2

    total_indicator_variance = sum(indicator_variance.values())
    if total_indicator_variance == 0:
        total_indicator_variance = 1.0  # avoid division by zero

    result = {}
    for ind in gsd_maps:
        result[ind] = {
            "weighted_avg_score": weighted_scores[ind],
            "contribution_pct": round(
                indicator_variance[ind] / total_indicator_variance * 100, 1
            ),
        }

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -v
```
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/data_quality.py tests/test_data_quality.py
git commit -m "feat: add cascade distribution and pedigree breakdown analysis"
```

---

## Task 4: Data quality grade and summary

**Files:**
- Modify: `hemera/services/data_quality.py`
- Modify: `tests/test_data_quality.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_data_quality.py`:

```python
from hemera.services.data_quality import compute_data_quality_grade, compute_summary


def test_grade_c_for_mostly_level4(sample_transactions):
    """Sample data is mostly Level 4 — should be grade C."""
    cascade = compute_cascade_distribution(sample_transactions)
    grade = compute_data_quality_grade(cascade["current_by_spend_pct"])
    assert grade == "C"


def test_grade_a_for_high_l1_l2():
    """Grade A when >60% at L1-2."""
    dist = {"L1": 40, "L2": 25, "L3": 15, "L4": 15, "L5": 5, "L6": 0}
    assert compute_data_quality_grade(dist) == "A"


def test_grade_b_for_moderate_l1_l3():
    """Grade B when >40% at L1-3."""
    dist = {"L1": 15, "L2": 15, "L3": 15, "L4": 40, "L5": 15, "L6": 0}
    assert compute_data_quality_grade(dist) == "B"


def test_summary_has_all_fields(sample_transactions):
    """Summary should contain all required fields."""
    result = compute_summary(sample_transactions)
    required = [
        "overall_gsd", "ci_95_percent", "total_spend_gbp", "total_co2e_tonnes",
        "data_quality_grade", "transactions_analysed", "vague_code_count",
        "vague_code_spend_gbp", "vague_code_spend_pct",
    ]
    for field in required:
        assert field in result, f"Missing field: {field}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -k "grade or summary" -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement grade and summary**

Add to `hemera/services/data_quality.py`:

```python
def compute_data_quality_grade(cascade_spend_pct: dict) -> str:
    """Assign A-E grade based on cascade level distribution (by spend).

    A: >60% at L1-2
    B: >40% at L1-3
    C: >60% at L4+ (typical Year 1)
    D: >80% at L4+
    E: majority unclassified or no EF matched
    """
    l1_l2 = cascade_spend_pct.get("L1", 0) + cascade_spend_pct.get("L2", 0)
    l1_l3 = l1_l2 + cascade_spend_pct.get("L3", 0)
    l4_plus = (
        cascade_spend_pct.get("L4", 0)
        + cascade_spend_pct.get("L5", 0)
        + cascade_spend_pct.get("L6", 0)
    )

    if l1_l2 > 60:
        return "A"
    if l1_l3 > 40:
        return "B"
    if l4_plus > 80:
        return "D"
    if l4_plus > 60:
        return "C"
    return "E"


def compute_summary(transactions: list) -> dict:
    """Compute the top-level summary for the data quality report."""
    valid = [t for t in transactions if t.co2e_kg is not None and not t.is_duplicate]
    total_spend = sum(abs(t.amount_gbp or 0) for t in valid)
    total_co2e_kg = sum(t.co2e_kg for t in valid)

    # Reuse existing functions
    vague_codes = detect_vague_codes(transactions)
    vague_count = sum(v["transaction_count"] for v in vague_codes)
    vague_spend = sum(v["spend_gbp"] for v in vague_codes)

    cascade = compute_cascade_distribution(transactions)
    grade = compute_data_quality_grade(cascade["current_by_spend_pct"])

    # Overall GSD from transaction-level data
    gsd_values = [t.gsd_total for t in valid if t.gsd_total and t.gsd_total > 0]
    co2e_values = [t.co2e_kg for t in valid if t.gsd_total and t.gsd_total > 0]

    if gsd_values and co2e_values:
        total = sum(co2e_values)
        ln_sq_sum = 0.0
        for gsd, co2e in zip(gsd_values, co2e_values):
            weight = co2e / total
            ln_sq_sum += (weight * math.log(gsd)) ** 2
        overall_gsd = math.exp(math.sqrt(ln_sq_sum))
    else:
        overall_gsd = 1.0

    ci_pct = round((overall_gsd ** 2 - 1) * 100, 0)

    return {
        "overall_gsd": round(overall_gsd, 3),
        "ci_95_percent": f"+/-{int(ci_pct)}%",
        "total_spend_gbp": round(total_spend, 2),
        "total_co2e_tonnes": round(total_co2e_kg / 1000, 2),
        "data_quality_grade": grade,
        "transactions_analysed": len(valid),
        "vague_code_count": vague_count,
        "vague_code_spend_gbp": round(vague_spend, 2),
        "vague_code_spend_pct": round(vague_spend / total_spend * 100, 1) if total_spend > 0 else 0.0,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -v
```
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/data_quality.py tests/test_data_quality.py
git commit -m "feat: add data quality grade and summary computation"
```

---

## Task 5: Recommendations engine

**Files:**
- Modify: `hemera/services/data_quality.py`
- Modify: `tests/test_data_quality.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_data_quality.py`:

```python
from hemera.services.data_quality import generate_recommendations


def test_recommendations_include_chart_of_accounts(sample_transactions):
    """Sundries code with 2 different classifications should trigger a split rec."""
    recs = generate_recommendations(sample_transactions)
    coa_recs = [r for r in recs if r["type"] == "chart_of_accounts"]
    assert len(coa_recs) >= 1
    sundries_rec = next(r for r in coa_recs if r["current_code"] == "Sundries")
    assert set(sundries_rec["suggested_splits"]) == {
        "Purchased goods — office supplies",
        "Purchased goods — IT equipment",
    }
    assert sundries_rec["spend_gbp"] == 8000.0


def test_recommendations_include_activity_data(sample_transactions):
    """Electricity at Level 4 should trigger activity data recommendation."""
    recs = generate_recommendations(sample_transactions)
    act_recs = [r for r in recs if r["type"] == "activity_data"]
    elec = [r for r in act_recs if r["category"] == "Purchased electricity"]
    assert len(elec) == 1
    assert elec[0]["data_needed"] == "kWh from electricity bills or supplier portal"


def test_recommendations_include_gas_activity_data(sample_transactions):
    """Gas at Level 4 should trigger activity data recommendation."""
    recs = generate_recommendations(sample_transactions)
    act_recs = [r for r in recs if r["type"] == "activity_data"]
    gas = [r for r in act_recs if "gas" in r["category"].lower() or "combustion" in r["category"].lower()]
    assert len(gas) == 1


def test_recommendations_ranked_by_impact(sample_transactions):
    """Recommendations should be ranked by impact_score descending."""
    recs = generate_recommendations(sample_transactions)
    scores = [r["impact_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)


def test_recommendations_have_required_fields(sample_transactions):
    """Every recommendation should have type, rank, impact_score, explanation."""
    recs = generate_recommendations(sample_transactions)
    for r in recs:
        assert "type" in r
        assert "rank" in r
        assert "impact_score" in r
        assert "explanation" in r
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -k "recommendations" -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement recommendations engine**

Add to `hemera/services/data_quality.py`:

```python
# Categories where activity data is achievable (Level 2) but often calculated spend-based (Level 4+)
ACTIVITY_DATA_CATEGORIES = {
    "Purchased electricity": {
        "data_needed": "kWh from electricity bills or supplier portal",
        "recommended_method": "activity-based kWh (Level 2)",
        "projected_gsd": 1.05,
    },
    "Purchased heat/steam/cooling": {
        "data_needed": "kWh from heating bills",
        "recommended_method": "activity-based kWh (Level 2)",
        "projected_gsd": 1.10,
    },
    "Stationary combustion — gas/heating fuel": {
        "data_needed": "kWh or litres from gas bills",
        "recommended_method": "activity-based kWh/litres (Level 2)",
        "projected_gsd": 1.05,
    },
    "Mobile combustion — company vehicles": {
        "data_needed": "Litres from fuel card statements",
        "recommended_method": "activity-based litres (Level 2)",
        "projected_gsd": 1.10,
    },
    "Waste generated in operations": {
        "data_needed": "Tonnes by waste type from contractor reports",
        "recommended_method": "waste-type based tonnes (Level 2)",
        "projected_gsd": 1.15,
    },
    "Business travel — rail": {
        "data_needed": "Passenger-km from booking confirmations",
        "recommended_method": "distance-based pax-km (Level 2)",
        "projected_gsd": 1.10,
    },
    "Business travel — air": {
        "data_needed": "Passenger-km and cabin class from bookings",
        "recommended_method": "distance-based pax-km (Level 2)",
        "projected_gsd": 1.10,
    },
    "Purchased services — water supply": {
        "data_needed": "m3 from water bills",
        "recommended_method": "activity-based m3 (Level 2)",
        "projected_gsd": 1.05,
    },
}


def _projected_gsd_one_level_better(current_gsd: float) -> float:
    """Estimate GSD if emission factor moved up one cascade level.

    Conservative: reduce ln(GSD) by ~20% (roughly one level of technological improvement).
    """
    ln_gsd = math.log(current_gsd)
    return math.exp(ln_gsd * 0.8)


def generate_recommendations(transactions: list) -> list[dict]:
    """Generate ranked recommendations for improving data quality.

    Three types: chart_of_accounts, activity_data, supplier_engagement.
    Ranked by impact_score = spend_gbp * (current_gsd - projected_gsd).
    """
    valid = [t for t in transactions if t.co2e_kg is not None and not t.is_duplicate]
    recs = []

    # 1. Chart-of-accounts: vague codes with 2+ distinct classifications
    vague = detect_vague_codes(transactions)
    for v in vague:
        if len(v["classified_as"]) >= 2:
            # Find transactions in this group to compute GSD
            group_txns = [
                t for t in valid
                if (t.raw_category or "").strip() == v["raw_category"]
            ]
            gsd_vals = [t.gsd_total for t in group_txns if t.gsd_total]
            avg_gsd = sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5
            projected = _projected_gsd_one_level_better(avg_gsd)
            impact = v["spend_gbp"] * (avg_gsd - projected)
            reduction_pct = round((1 - projected / avg_gsd) * 100, 1)

            recs.append({
                "type": "chart_of_accounts",
                "impact_score": round(impact, 1),
                "current_code": v["raw_category"],
                "suggested_splits": v["classified_as"],
                "spend_gbp": v["spend_gbp"],
                "current_avg_gsd": round(avg_gsd, 2),
                "projected_avg_gsd": round(projected, 2),
                "uncertainty_reduction_pct": reduction_pct,
                "explanation": (
                    f"{v['transaction_count']} transactions under this code were classified "
                    f"into {len(v['classified_as'])} distinct categories. Splitting the nominal "
                    f"code would allow more specific emission factors."
                ),
            })

    # 2. Activity data: categories where Level 2 is achievable
    category_groups: dict[str, list] = {}
    for t in valid:
        if t.category_name and (t.ef_level or 0) >= 4:
            category_groups.setdefault(t.category_name, []).append(t)

    for cat_name, txns in category_groups.items():
        if cat_name in ACTIVITY_DATA_CATEGORIES:
            info = ACTIVITY_DATA_CATEGORIES[cat_name]
            spend = sum(abs(t.amount_gbp or 0) for t in txns)
            gsd_vals = [t.gsd_total for t in txns if t.gsd_total]
            avg_gsd = sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5
            impact = spend * (avg_gsd - info["projected_gsd"])

            recs.append({
                "type": "activity_data",
                "impact_score": round(impact, 1),
                "category": cat_name,
                "current_method": f"spend-based (Level {txns[0].ef_level})",
                "recommended_method": info["recommended_method"],
                "spend_gbp": spend,
                "current_gsd": round(avg_gsd, 2),
                "projected_gsd": info["projected_gsd"],
                "data_needed": info["data_needed"],
                "explanation": (
                    f"{cat_name} spend is currently estimated from GBP. "
                    f"Providing {info['data_needed'].split(' from ')[0].lower()} would "
                    f"move this from Level {txns[0].ef_level} to Level 2."
                ),
            })

    # 3. Supplier engagement: high-spend suppliers at Level 4+
    supplier_groups: dict[str, list] = {}
    for t in valid:
        if t.raw_supplier and (t.ef_level or 0) >= 4:
            supplier_groups.setdefault(t.raw_supplier.strip(), []).append(t)

    for supplier_name, txns in supplier_groups.items():
        spend = sum(abs(t.amount_gbp or 0) for t in txns)
        if spend < 2000:  # only recommend for meaningful spend
            continue
        gsd_vals = [t.gsd_total for t in txns if t.gsd_total]
        avg_gsd = sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5
        projected = 1.05  # Level 1 supplier-specific
        impact = spend * (avg_gsd - projected)

        recs.append({
            "type": "supplier_engagement",
            "impact_score": round(impact, 1),
            "supplier_name": supplier_name,
            "supplier_id": txns[0].supplier_id,
            "spend_gbp": spend,
            "current_ef_level": txns[0].ef_level,
            "projected_ef_level": 1,
            "explanation": (
                f"{supplier_name} is a significant supplier by spend. "
                f"Requesting their emission intensity data would reduce uncertainty "
                f"from GSD {round(avg_gsd, 2)} to ~1.05."
            ),
        })

    # Sort by impact_score descending and assign ranks
    recs.sort(key=lambda r: r["impact_score"], reverse=True)
    for i, r in enumerate(recs, 1):
        r["rank"] = i

    return recs
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -v
```
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/data_quality.py tests/test_data_quality.py
git commit -m "feat: add recommendations engine (chart-of-accounts, activity data, supplier engagement)"
```

---

## Task 6: Full report assembly function

**Files:**
- Modify: `hemera/services/data_quality.py`
- Modify: `tests/test_data_quality.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_data_quality.py`:

```python
from hemera.services.data_quality import generate_data_quality_report


def test_full_report_structure(sample_transactions, sample_engagement):
    """Full report should have all top-level sections."""
    report = generate_data_quality_report(sample_transactions, sample_engagement.id)
    assert report["engagement_id"] == sample_engagement.id
    assert "generated_at" in report
    assert "summary" in report
    assert "cascade_distribution" in report
    assert "uncertainty_contributors" in report
    assert "pedigree_breakdown" in report
    assert "recommendations" in report


def test_full_report_summary_grade(sample_transactions, sample_engagement):
    """Full report summary should have a valid grade."""
    report = generate_data_quality_report(sample_transactions, sample_engagement.id)
    assert report["summary"]["data_quality_grade"] in ("A", "B", "C", "D", "E")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -k "full_report" -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement full report assembly**

Add to `hemera/services/data_quality.py`:

```python
from datetime import datetime, timezone


def generate_data_quality_report(transactions: list, engagement_id: int) -> dict:
    """Assemble the complete data quality report from all analysis components.

    This is the top-level function called by the API endpoint.
    """
    return {
        "engagement_id": engagement_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": compute_summary(transactions),
        "cascade_distribution": compute_cascade_distribution(transactions),
        "uncertainty_contributors": compute_uncertainty_contributors(transactions),
        "pedigree_breakdown": compute_pedigree_breakdown(transactions),
        "recommendations": generate_recommendations(transactions),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -v
```
Expected: 21 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/services/data_quality.py tests/test_data_quality.py
git commit -m "feat: add full data quality report assembly function"
```

---

## Task 7: API endpoint

**Files:**
- Modify: `hemera/api/reports.py`
- Modify: `tests/test_data_quality.py`

- [ ] **Step 1: Write failing API test**

Append to `tests/test_data_quality.py`:

```python
from fastapi.testclient import TestClient
from hemera.database import Base, get_db
from hemera.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_api_data_quality_endpoint():
    """Integration test: hit the endpoint and verify response shape."""
    # Set up in-memory DB
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    # Override FastAPI dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Create engagement + transactions
    from hemera.models.engagement import Engagement
    from hemera.models.transaction import Transaction

    eng = Engagement(org_name="API Test SU", status="delivered", transaction_count=1)
    session.add(eng)
    session.flush()

    txn = Transaction(
        engagement_id=eng.id,
        row_number=1,
        raw_description="Test electricity",
        raw_supplier="EDF Energy",
        raw_category="Utilities",
        raw_amount=1000.0,
        amount_gbp=1000.0,
        scope=2, ghg_category=None,
        category_name="Purchased electricity",
        classification_method="keyword",
        classification_confidence=0.95,
        ef_value=0.23, ef_unit="kgCO2e/GBP", ef_source="defra",
        ef_level=4, ef_year=2024, ef_region="UK",
        co2e_kg=230.0,
        pedigree_reliability=3, pedigree_completeness=2,
        pedigree_temporal=1, pedigree_geographical=1,
        pedigree_technological=4,
        gsd_total=1.69,
    )
    session.add(txn)
    session.flush()

    client = TestClient(app)
    response = client.get(f"/api/reports/{eng.id}/data-quality")
    assert response.status_code == 200

    data = response.json()
    assert data["engagement_id"] == eng.id
    assert "summary" in data
    assert "recommendations" in data

    # Cleanup
    app.dependency_overrides.clear()
    session.close()


def test_api_data_quality_not_found():
    """Should return 404 for non-existent engagement."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/reports/99999/data-quality")
    assert response.status_code == 404

    app.dependency_overrides.clear()
    session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py::test_api_data_quality_endpoint -v
```
Expected: FAIL — 404 or wrong response (placeholder endpoint)

- [ ] **Step 3: Replace placeholder in reports.py**

Rewrite `hemera/api/reports.py`:

```python
"""Report generation endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.transaction import Transaction
from hemera.services.data_quality import generate_data_quality_report

router = APIRouter()


@router.get("/reports/{engagement_id}/data-quality")
def get_data_quality_report(engagement_id: int, db: Session = Depends(get_db)):
    """Generate a Data Quality Improvement Report for an engagement.

    Analyses transaction data to identify uncertainty sources and
    generate ranked recommendations for improving accuracy.
    """
    engagement = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    transactions = (
        db.query(Transaction)
        .filter(Transaction.engagement_id == engagement_id)
        .all()
    )

    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found for engagement")

    return generate_data_quality_report(transactions, engagement_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/test_data_quality.py -v
```
Expected: 23 passed

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/Hemera
git add hemera/api/reports.py tests/test_data_quality.py
git commit -m "feat: add GET /api/reports/{id}/data-quality endpoint"
```

---

## Task 8: Final integration test and cleanup

**Files:**
- Modify: `tests/test_data_quality.py`

- [ ] **Step 1: Run full test suite**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -m pytest tests/ -v
```
Expected: All 23 tests pass

- [ ] **Step 2: Verify the app starts cleanly**

Run:
```bash
cd ~/Documents/Hemera && .venv/bin/python -c "from hemera.main import app; print('App loads OK')"
```
Expected: `App loads OK`

- [ ] **Step 3: Final commit with plan reference**

```bash
cd ~/Documents/Hemera
git add -A
git commit -m "chore: data quality report implementation complete

Implements spec: docs/superpowers/specs/2026-04-06-data-quality-report-design.md
Plan: docs/superpowers/plans/2026-04-06-data-quality-report.md"
```
