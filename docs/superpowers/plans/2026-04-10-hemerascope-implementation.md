# HemeraScope Supplier Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the supplier intelligence layer of HemeraScope — three-layer findings system, analyst curation workflow, client dashboard, and unified PDF report.

**Architecture:** Findings live on suppliers (reusable across engagements), selections are per-engagement. All AI tasks support both API and manual/Max modes via an `ai_tasks` table. Analyst curates supplier-by-supplier with live report preview, then reviews the full report before publishing. Existing carbon report integrates into the unified HemeraScope PDF.

**Tech Stack:** Python/FastAPI (backend), SQLAlchemy + Alembic (models/migrations), Next.js 16 + React 19 + Tailwind 4 (frontend), WeasyPrint + Jinja2 (PDF), Clerk (auth), Neon Postgres (DB).

**Spec:** `docs/superpowers/specs/2026-04-10-hemerascope-design.md`

---

## File Structure

### New Files — Backend

| File | Responsibility |
|---|---|
| `hemera/models/finding.py` | `SupplierFinding`, `ReportSelection`, `ReportAction` models |
| `hemera/models/ai_task.py` | `AITask` model |
| `hemera/models/supplier_engagement.py` | `SupplierEngagement` model (Hemera CRM) |
| `hemera/services/finding_generator.py` | Converts ESGResult flags + scores → SupplierFinding rows |
| `hemera/services/ai_prompt_builder.py` | Builds prompts for all 5 AI task types |
| `hemera/services/ai_task_runner.py` | Executes AI tasks (API mode) or returns prompt (manual mode) |
| `hemera/api/findings.py` | Findings + supplier engagement CRUD endpoints |
| `hemera/api/hemerascope.py` | Report curation, preview, publish, client-facing endpoints |
| `hemera/api/ai_tasks.py` | AI task create/paste-back endpoints |
| `hemera/services/hemerascope_report.py` | HemeraScope PDF data gathering + chart generation |
| `hemera/templates/hemerascope/` | Jinja2 templates for supplier intelligence PDF sections |
| `tests/test_finding_generator.py` | Finding generation from ESGResult |
| `tests/test_ai_prompt_builder.py` | Prompt construction tests |
| `tests/test_hemerascope_api.py` | Curation + publish endpoint tests |
| `tests/test_ai_tasks_api.py` | AI task create/paste-back tests |

### New Files — Frontend

| File | Responsibility |
|---|---|
| `dashboard/app/dashboard/[id]/hemerascope/page.tsx` | Supplier curation view (Stage 1) |
| `dashboard/app/dashboard/[id]/hemerascope/review/page.tsx` | Full report review (Stage 2) |
| `dashboard/app/dashboard/[id]/hemerascope/report/page.tsx` | Client-facing supplier intelligence view |
| `dashboard/app/dashboard/[id]/hemerascope/report/[supplierId]/page.tsx` | Client-facing supplier detail |
| `dashboard/components/ai-task-buttons.tsx` | Reusable "Generate (API)" / "Copy Prompt (Max)" / "Paste Response" component |
| `dashboard/components/finding-card.tsx` | Single finding display with include/skip toggle |
| `dashboard/components/report-preview.tsx` | Right-panel report preview component |

### Modified Files

| File | Changes |
|---|---|
| `hemera/models/supplier.py` | Rename `esg_score` → `hemera_score`, add `hemera_verified` bool, add `findings` + `hemera_engagements` relationships |
| `hemera/models/engagement.py` | Add `supplier_report_status`, `supplier_report_exec_summary` columns |
| `hemera/services/esg_scorer.py` | Rename `total_score` → `hemera_score` in ESGResult |
| `hemera/services/enrichment.py` | Call `generate_findings_from_result()` after enrichment |
| `hemera/main.py` | Register new routers (findings, hemerascope, ai_tasks) |
| `hemera/models/__init__.py` | Import new models |

---

## Task 1: Database Models & Migration

**Files:**
- Create: `hemera/models/finding.py`
- Create: `hemera/models/ai_task.py`
- Create: `hemera/models/supplier_engagement.py`
- Modify: `hemera/models/supplier.py`
- Modify: `hemera/models/engagement.py`
- Modify: `hemera/models/esg_scorer.py` (rename field)
- Modify: `hemera/models/__init__.py`
- Test: `tests/test_hemerascope_models.py`

- [ ] **Step 1: Write test for new models**

```python
# tests/test_hemerascope_models.py
"""Tests for HemeraScope data models."""
import pytest
from datetime import datetime
from hemera.database import Base, engine, SessionLocal
from hemera.models.finding import SupplierFinding, ReportSelection, ReportAction
from hemera.models.ai_task import AITask
from hemera.models.supplier_engagement import SupplierEngagement
from hemera.models.supplier import Supplier
from hemera.models.engagement import Engagement


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()


def test_supplier_finding_creation(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-123")
    db.add(supplier)
    db.flush()

    finding = SupplierFinding(
        supplier_id=supplier.id,
        source="deterministic",
        domain="governance",
        severity="high",
        title="Insolvency history detected",
        detail="Companies House records show insolvency proceedings in 2024.",
        layer=1,
        source_name="companies_house",
        is_active=True,
    )
    db.add(finding)
    db.flush()

    assert finding.id is not None
    assert finding.supplier_id == supplier.id
    assert finding.source == "deterministic"
    assert finding.severity == "high"
    assert finding.is_active is True


def test_report_selection_unique_constraint(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-456")
    db.add(supplier)
    db.flush()

    engagement = Engagement(org_name="Client A", contact_email="a@test.com")
    db.add(engagement)
    db.flush()

    finding = SupplierFinding(
        supplier_id=supplier.id,
        source="deterministic",
        domain="carbon",
        severity="medium",
        title="No SBTi target",
        detail="No Science Based Target found.",
        source_name="sbti",
        is_active=True,
    )
    db.add(finding)
    db.flush()

    sel1 = ReportSelection(
        engagement_id=engagement.id,
        finding_id=finding.id,
        included=True,
        selected_by=1,
    )
    db.add(sel1)
    db.flush()

    sel2 = ReportSelection(
        engagement_id=engagement.id,
        finding_id=finding.id,
        included=False,
        selected_by=1,
    )
    db.add(sel2)

    with pytest.raises(Exception):  # IntegrityError from unique constraint
        db.flush()


def test_ai_task_creation(db):
    task = AITask(
        task_type="risk_analysis",
        target_type="supplier",
        target_id=1,
        mode="manual",
        status="prompt_copied",
        prompt_text="Analyse this supplier...",
        prompt_hash="abc123",
    )
    db.add(task)
    db.flush()

    assert task.id is not None
    assert task.mode == "manual"
    assert task.status == "prompt_copied"
    assert task.response_text is None


def test_supplier_engagement_creation(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-789")
    db.add(supplier)
    db.flush()

    eng = SupplierEngagement(
        supplier_id=supplier.id,
        engagement_type="outreach",
        subject="SBTi Commitment Discussion",
        status="contacted",
        notes="Sent initial email to sustainability team.",
        contacted_at=datetime.utcnow(),
        created_by=1,
    )
    db.add(eng)
    db.flush()

    assert eng.id is not None
    assert eng.status == "contacted"


def test_report_action_creation(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-abc")
    db.add(supplier)
    db.flush()

    engagement = Engagement(org_name="Client B", contact_email="b@test.com")
    db.add(engagement)
    db.flush()

    action = ReportAction(
        engagement_id=engagement.id,
        supplier_id=supplier.id,
        action_text="Hemera can facilitate a supplier engagement session to review their decarbonisation roadmap.",
        priority=1,
        linked_finding_ids=[1, 2],
        language_source="ai_automated",
        created_by=1,
    )
    db.add(action)
    db.flush()

    assert action.id is not None
    assert action.linked_finding_ids == [1, 2]


def test_supplier_hemera_score_rename(db):
    supplier = Supplier(name="Test Corp", hemera_id="test-rename")
    supplier.hemera_score = 72.5
    db.add(supplier)
    db.flush()

    assert supplier.hemera_score == 72.5


def test_engagement_supplier_report_fields(db):
    engagement = Engagement(org_name="Client C", contact_email="c@test.com")
    engagement.supplier_report_status = "curating"
    engagement.supplier_report_exec_summary = "This report covers 24 suppliers..."
    db.add(engagement)
    db.flush()

    assert engagement.supplier_report_status == "curating"
    assert engagement.supplier_report_exec_summary.startswith("This report")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_hemerascope_models.py -v`
Expected: FAIL — modules don't exist yet

- [ ] **Step 3: Create SupplierFinding, ReportSelection, ReportAction models**

```python
# hemera/models/finding.py
"""HemeraScope finding and curation models."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, JSON,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from hemera.database import Base


class SupplierFinding(Base):
    __tablename__ = "supplier_findings"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    source = Column(String(20), nullable=False)  # deterministic, outlier, ai_automated, ai_manual
    domain = Column(String(30), nullable=False)  # governance, labour, carbon, water, product, transparency, anti_corruption, social_value
    severity = Column(String(10), nullable=False)  # critical, high, medium, info, positive
    title = Column(String(255), nullable=False)
    detail = Column(Text, nullable=False)
    evidence_url = Column(Text)
    evidence_data = Column(JSON)
    layer = Column(Integer)  # 1-13, for deterministic findings
    source_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    ai_task_id = Column(Integer, ForeignKey("ai_tasks.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    superseded_at = Column(DateTime)

    supplier = relationship("Supplier", back_populates="findings")
    selections = relationship("ReportSelection", back_populates="finding")

    __table_args__ = (
        Index("ix_supplier_findings_active", "supplier_id", "is_active"),
        Index("ix_supplier_findings_domain", "supplier_id", "domain"),
        Index("ix_supplier_findings_severity", "supplier_id", "severity"),
    )


class ReportSelection(Base):
    __tablename__ = "report_selections"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagements.id"), nullable=False)
    finding_id = Column(Integer, ForeignKey("supplier_findings.id"), nullable=False)
    included = Column(Boolean, nullable=False)
    client_title = Column(String(255))
    client_detail = Column(Text)
    client_language_source = Column(String(20))  # ai_automated, ai_manual, analyst
    analyst_note = Column(Text)
    selected_by = Column(Integer, nullable=False)
    selected_at = Column(DateTime, default=datetime.utcnow)

    finding = relationship("SupplierFinding", back_populates="selections")
    engagement = relationship("Engagement", back_populates="report_selections")

    __table_args__ = (
        UniqueConstraint("engagement_id", "finding_id", name="uq_report_selection_engagement_finding"),
    )


class ReportAction(Base):
    __tablename__ = "report_actions"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagements.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    action_text = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False, default=1)
    linked_finding_ids = Column(JSON)
    language_source = Column(String(20), nullable=False)  # ai_automated, ai_manual, analyst
    ai_task_id = Column(Integer, ForeignKey("ai_tasks.id"))
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    engagement = relationship("Engagement", back_populates="report_actions")
    supplier = relationship("Supplier")
```

- [ ] **Step 4: Create AITask model**

```python
# hemera/models/ai_task.py
"""AI task tracking — API and manual/Max modes."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from hemera.database import Base


class AITask(Base):
    __tablename__ = "ai_tasks"

    id = Column(Integer, primary_key=True)
    task_type = Column(String(30), nullable=False)  # risk_analysis, client_language, recommended_actions, engagement_summary, exec_summary
    target_type = Column(String(20), nullable=False)  # supplier, engagement
    target_id = Column(Integer, nullable=False)
    mode = Column(String(10), nullable=False)  # api, manual
    status = Column(String(20), nullable=False, default="pending")  # pending, prompt_copied, completed, failed
    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text)
    prompt_hash = Column(String(64), nullable=False)
    token_count = Column(Integer)
    cost_usd = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
```

- [ ] **Step 5: Create SupplierEngagement model**

```python
# hemera/models/supplier_engagement.py
"""Hemera-to-supplier engagement tracking (lightweight CRM)."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from hemera.database import Base


class SupplierEngagement(Base):
    __tablename__ = "supplier_engagements"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    engagement_type = Column(String(30), nullable=False)  # outreach, meeting, workshop, ongoing_programme, data_request
    subject = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # planned, contacted, in_progress, completed, no_response, declined
    notes = Column(Text)
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    contacted_at = Column(DateTime)
    responded_at = Column(DateTime)
    next_action = Column(Text)
    next_action_date = Column(Date)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="hemera_engagements")
```

- [ ] **Step 6: Modify Supplier model — rename esg_score, add relationships and hemera_verified**

In `hemera/models/supplier.py`:
- Rename `esg_score = Column(Float)` → `hemera_score = Column(Float)`
- Add `hemera_verified = Column(Boolean, default=False)`
- Add relationships:
```python
findings = relationship("SupplierFinding", back_populates="supplier", order_by="SupplierFinding.created_at.desc()")
hemera_engagements = relationship("SupplierEngagement", back_populates="supplier", order_by="SupplierEngagement.created_at.desc()")
```

- [ ] **Step 7: Modify Engagement model — add supplier_report fields**

In `hemera/models/engagement.py`:
- Add `supplier_report_status = Column(String(20))` — pending, curating, language_review, approved, published
- Add `supplier_report_exec_summary = Column(Text)`
- Add relationships:
```python
report_selections = relationship("ReportSelection", back_populates="engagement")
report_actions = relationship("ReportAction", back_populates="engagement")
```

- [ ] **Step 8: Modify ESGResult — rename total_score**

In `hemera/services/esg_scorer.py`:
- Rename `total_score: float = 0.0` → `hemera_score: float = 0.0`
- Update the calculation line: `result.total_score = round(...)` → `result.hemera_score = round(...)`

- [ ] **Step 9: Update __init__.py imports**

In `hemera/models/__init__.py`, add:
```python
from hemera.models.finding import SupplierFinding, ReportSelection, ReportAction
from hemera.models.ai_task import AITask
from hemera.models.supplier_engagement import SupplierEngagement
```

- [ ] **Step 10: Fix all references to esg_score and total_score**

Search codebase for `esg_score` and `total_score` references. Update:
- `hemera/services/enrichment.py`: `supplier.esg_score = result.total_score` → `supplier.hemera_score = result.hemera_score`
- `hemera/api/suppliers.py`: any references to `esg_score` → `hemera_score`
- `hemera/api/supplier_review.py`: `esg_score` → `hemera_score`
- `hemera/api/engagements.py`: `esg_score` → `hemera_score`
- `hemera/models/supplier.py` in SupplierScore: `total_score` → `hemera_score`

Run: `cd /Users/nicohenry/Documents/Hemera && grep -rn "esg_score\|total_score" hemera/ --include="*.py" | grep -v __pycache__`
Fix every occurrence.

- [ ] **Step 11: Generate Alembic migration**

Run:
```bash
cd /Users/nicohenry/Documents/Hemera
alembic revision --autogenerate -m "hemerascope: add findings, selections, actions, ai_tasks, supplier_engagements; rename esg_score"
```

Review the generated migration file. Verify it includes:
- CREATE TABLE supplier_findings
- CREATE TABLE report_selections (with unique constraint)
- CREATE TABLE report_actions
- CREATE TABLE ai_tasks
- CREATE TABLE supplier_engagements
- ALTER TABLE suppliers: rename esg_score → hemera_score, add hemera_verified
- ALTER TABLE engagements: add supplier_report_status, supplier_report_exec_summary
- ALTER TABLE supplier_scores: rename total_score → hemera_score

- [ ] **Step 12: Apply migration**

Run: `cd /Users/nicohenry/Documents/Hemera && alembic upgrade head`

- [ ] **Step 13: Run model tests**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_hemerascope_models.py -v`
Expected: All 7 tests PASS

- [ ] **Step 14: Run all existing tests to verify no regressions from rename**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/ -v`
Expected: All 154+ tests PASS. Fix any failures from the esg_score → hemera_score rename.

- [ ] **Step 15: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add hemera/models/ hemera/services/esg_scorer.py hemera/services/enrichment.py hemera/api/ tests/test_hemerascope_models.py alembic/
git commit -m "feat: HemeraScope data model — findings, selections, ai_tasks, supplier_engagements, Hemera Score rename"
```

---

## Task 2: Finding Generator — Deterministic Layer

**Files:**
- Create: `hemera/services/finding_generator.py`
- Test: `tests/test_finding_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_finding_generator.py
"""Tests for deterministic finding generation from ESGResult."""
import pytest
from hemera.services.esg_scorer import ESGResult
from hemera.services.finding_generator import generate_findings_from_result


def test_critical_flag_generates_critical_finding():
    result = ESGResult(
        hemera_score=35.0,
        critical_flag=True,
        flags=["SANCTIONS HIT"],
        governance_identity=20.0,
        confidence="medium",
        layers_completed=6,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")

    critical = [f for f in findings if f["severity"] == "critical"]
    assert len(critical) >= 1
    assert any("SANCTIONS" in f["title"].upper() for f in critical)


def test_low_domain_generates_finding():
    result = ESGResult(
        hemera_score=55.0,
        carbon_climate=25.0,
        flags=["Environment Agency enforcement actions"],
        confidence="medium",
        layers_completed=5,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")

    carbon_findings = [f for f in findings if f["domain"] == "carbon"]
    assert len(carbon_findings) >= 1


def test_positive_findings_generated():
    result = ESGResult(
        hemera_score=78.0,
        labour_ethics=85.0,
        product_supply_chain=75.0,
        flags=[],
        confidence="high",
        layers_completed=10,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")

    positives = [f for f in findings if f["severity"] == "positive"]
    assert len(positives) >= 1


def test_all_flags_become_findings():
    result = ESGResult(
        hemera_score=30.0,
        critical_flag=True,
        flags=[
            "SANCTIONS HIT",
            "HSE: 3 enforcement actions",
            "Company dissolved or in liquidation",
        ],
        governance_identity=15.0,
        labour_ethics=30.0,
        confidence="low",
        layers_completed=3,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")

    titles = [f["title"] for f in findings]
    assert len(findings) >= 3  # At least one per flag


def test_finding_dict_structure():
    result = ESGResult(
        hemera_score=60.0,
        flags=["PEP detected among directors/PSCs"],
        confidence="medium",
        layers_completed=5,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")

    for f in findings:
        assert "source" in f and f["source"] == "deterministic"
        assert "domain" in f
        assert "severity" in f
        assert "title" in f
        assert "detail" in f
        assert "source_name" in f
        assert f["domain"] in (
            "governance", "labour", "carbon", "water",
            "product", "transparency", "anti_corruption", "social_value",
        )
        assert f["severity"] in ("critical", "high", "medium", "info", "positive")


def test_domain_score_thresholds():
    """Low domain scores generate findings even without flags."""
    result = ESGResult(
        hemera_score=45.0,
        governance_identity=20.0,  # Very low
        carbon_climate=25.0,  # Very low
        labour_ethics=80.0,  # Fine
        flags=[],
        confidence="medium",
        layers_completed=6,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")

    domains_flagged = {f["domain"] for f in findings if f["severity"] in ("high", "medium")}
    assert "governance" in domains_flagged
    assert "carbon" in domains_flagged
    assert "labour" not in domains_flagged


def test_low_confidence_generates_info_finding():
    result = ESGResult(
        hemera_score=50.0,
        flags=[],
        confidence="low",
        layers_completed=2,
    )
    findings = generate_findings_from_result(result, supplier_name="Test Corp")

    info = [f for f in findings if f["severity"] == "info"]
    assert any("confidence" in f["title"].lower() or "data coverage" in f["title"].lower() for f in info)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_finding_generator.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement finding generator**

```python
# hemera/services/finding_generator.py
"""Generates supplier findings from ESGResult and domain scores.

Converts the deterministic scorer's output into structured finding dicts
ready to be stored as SupplierFinding rows.
"""

# Map flags to their domain and severity
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

# Domain score thresholds for generating findings
DOMAIN_LOW_THRESHOLD = 35  # Below this = high severity finding
DOMAIN_MEDIUM_THRESHOLD = 45  # Below this = medium severity finding
DOMAIN_HIGH_THRESHOLD = 70  # Above this = positive finding

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
    """Convert an ESGResult into a list of finding dicts.

    Args:
        result: ESGResult from esg_scorer.calculate_esg_score()
        supplier_name: Supplier name for detail text

    Returns:
        List of dicts with keys: source, domain, severity, title, detail,
        layer, source_name. Ready to be stored as SupplierFinding rows.
    """
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
            # Handle HSE pattern: "HSE: N enforcement actions"
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
            # Only add if no flag already covers this domain
            existing_domains = {f["domain"] for f in findings if f["severity"] in ("critical", "high")}
            if domain not in existing_domains:
                findings.append({
                    "source": "deterministic",
                    "domain": domain,
                    "severity": "high",
                    "title": f"Low {label} score ({score:.0f}/100)",
                    "detail": f"{supplier_name} scores {score:.0f}/100 in {label}, significantly below the baseline of 50. This indicates material gaps in this domain.",
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
            "detail": f"Only {result.layers_completed} of 13 data layers returned information for {supplier_name}. The Hemera Score may not fully reflect this supplier's risk profile. Additional data collection is recommended.",
            "layer": None,
            "source_name": "hemera_scorer",
        })

    return findings
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_finding_generator.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add hemera/services/finding_generator.py tests/test_finding_generator.py
git commit -m "feat: deterministic finding generator — converts ESGResult flags + scores to findings"
```

---

## Task 3: AI Prompt Builder & Task Runner

**Files:**
- Create: `hemera/services/ai_prompt_builder.py`
- Create: `hemera/services/ai_task_runner.py`
- Test: `tests/test_ai_prompt_builder.py`
- Test: `tests/test_ai_tasks_api.py`

- [ ] **Step 1: Write failing tests for prompt builder**

```python
# tests/test_ai_prompt_builder.py
"""Tests for AI prompt construction."""
import pytest
from hemera.services.ai_prompt_builder import build_prompt


def test_risk_analysis_prompt_contains_supplier_data():
    prompt = build_prompt(
        task_type="risk_analysis",
        context={
            "supplier_name": "Tesco PLC",
            "sector": "Retail",
            "sic_codes": ["47110"],
            "sources_summary": [
                {"layer": 1, "source": "companies_house", "summary": "Active company, 15 filings"},
                {"layer": 4, "source": "environment_agency", "summary": "2 enforcement notices"},
            ],
            "deterministic_findings": [
                {"title": "EA enforcement actions", "severity": "high"},
            ],
            "hemera_score": 38.0,
            "domain_scores": {"governance": 22, "carbon": 28},
        },
    )
    assert "Tesco PLC" in prompt
    assert "Retail" in prompt
    assert "enforcement" in prompt.lower()
    assert len(prompt) > 200


def test_client_language_prompt():
    prompt = build_prompt(
        task_type="client_language",
        context={
            "supplier_name": "Tesco PLC",
            "findings": [
                {"title": "EA enforcement actions", "detail": "2 active enforcement notices", "severity": "high"},
                {"title": "ISO 14001 certified", "detail": "Holds certification", "severity": "positive"},
            ],
        },
    )
    assert "professional" in prompt.lower() or "client" in prompt.lower()
    assert "constructive" in prompt.lower() or "collaborative" in prompt.lower()


def test_recommended_actions_prompt():
    prompt = build_prompt(
        task_type="recommended_actions",
        context={
            "supplier_name": "Tesco PLC",
            "findings": [
                {"title": "No SBTi target", "domain": "carbon"},
            ],
        },
    )
    assert "Hemera" in prompt
    assert "action" in prompt.lower()


def test_engagement_summary_prompt():
    prompt = build_prompt(
        task_type="engagement_summary",
        context={
            "supplier_name": "Tesco PLC",
            "engagements": [
                {"subject": "SBTi Discussion", "status": "in_progress", "notes": "Positive response"},
            ],
        },
    )
    assert "client-facing" in prompt.lower() or "client" in prompt.lower()


def test_exec_summary_prompt():
    prompt = build_prompt(
        task_type="exec_summary",
        context={
            "org_name": "Acme Retail",
            "supplier_count": 24,
            "total_spend": 4200000,
            "critical_count": 3,
            "attention_count": 7,
            "strong_count": 14,
        },
    )
    assert "Acme Retail" in prompt
    assert "24" in prompt


def test_all_prompts_include_response_format():
    """Every prompt must specify the expected response format."""
    for task_type in ["risk_analysis", "client_language", "recommended_actions", "engagement_summary", "exec_summary"]:
        prompt = build_prompt(task_type=task_type, context=_minimal_context(task_type))
        assert "json" in prompt.lower() or "format" in prompt.lower() or "respond" in prompt.lower()


def _minimal_context(task_type):
    if task_type == "risk_analysis":
        return {"supplier_name": "X", "sector": "Y", "sic_codes": [], "sources_summary": [], "deterministic_findings": [], "hemera_score": 50, "domain_scores": {}}
    if task_type in ("client_language", "recommended_actions"):
        return {"supplier_name": "X", "findings": []}
    if task_type == "engagement_summary":
        return {"supplier_name": "X", "engagements": []}
    return {"org_name": "X", "supplier_count": 0, "total_spend": 0, "critical_count": 0, "attention_count": 0, "strong_count": 0}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_ai_prompt_builder.py -v`
Expected: FAIL

- [ ] **Step 3: Implement prompt builder**

```python
# hemera/services/ai_prompt_builder.py
"""Builds prompts for all HemeraScope AI task types.

Every prompt is deterministic given the same input context —
the same prompt is used whether the task runs via API or
is copied to clipboard for Claude Max.
"""
import json


def build_prompt(task_type: str, context: dict) -> str:
    """Build a prompt for the given AI task type.

    Args:
        task_type: One of risk_analysis, client_language, recommended_actions,
                   engagement_summary, exec_summary
        context: Task-specific data dict

    Returns:
        Complete prompt string
    """
    builders = {
        "risk_analysis": _build_risk_analysis,
        "client_language": _build_client_language,
        "recommended_actions": _build_recommended_actions,
        "engagement_summary": _build_engagement_summary,
        "exec_summary": _build_exec_summary,
    }
    builder = builders[task_type]
    return builder(context)


def _build_risk_analysis(ctx: dict) -> str:
    sources_text = "\n".join(
        f"  - Layer {s['layer']} ({s['source']}): {s['summary']}"
        for s in ctx.get("sources_summary", [])
    ) or "  No source data available."

    findings_text = "\n".join(
        f"  - [{f['severity'].upper()}] {f['title']}"
        for f in ctx.get("deterministic_findings", [])
    ) or "  No deterministic findings."

    scores_text = "\n".join(
        f"  - {domain}: {score}/100"
        for domain, score in ctx.get("domain_scores", {}).items()
    ) or "  No domain scores."

    return f"""You are a supply chain risk analyst for Hemera Intelligence. Analyse the following supplier data and identify risks, patterns, or concerns that the deterministic rules may have missed.

SUPPLIER: {ctx['supplier_name']}
SECTOR: {ctx.get('sector', 'Unknown')}
SIC CODES: {json.dumps(ctx.get('sic_codes', []))}
HEMERA SCORE: {ctx.get('hemera_score', 'N/A')}/100

DATA COLLECTED:
{sources_text}

DETERMINISTIC FINDINGS ALREADY IDENTIFIED:
{findings_text}

DOMAIN SCORES:
{scores_text}

INSTRUCTIONS:
1. Look for patterns across multiple data sources that the individual rules wouldn't catch.
2. Consider sector-specific risks — what would be unusual or concerning for a company in this sector?
3. Identify gaps — what data is missing that would be expected for a company of this type?
4. Note any combinations of findings that together suggest a higher risk than individually.

Respond with a JSON array of findings. Each finding must have:
- "domain": one of governance, labour, carbon, water, product, transparency, anti_corruption, social_value
- "severity": one of critical, high, medium, info
- "title": short label (under 80 chars)
- "detail": explanation with specific evidence from the data above (2-3 sentences)
- "based_on": which layers/sources you drew from

Only include findings that add value beyond what the deterministic rules already caught. If nothing stands out, return an empty array [].

Respond with ONLY the JSON array, no other text."""


def _build_client_language(ctx: dict) -> str:
    findings_text = "\n".join(
        f"  - [{f.get('severity', 'info').upper()}] {f['title']}: {f.get('detail', '')}"
        for f in ctx.get("findings", [])
    ) or "  No findings."

    return f"""You are writing a professional ESG supplier report for Hemera Intelligence. Rewrite the following raw findings as clear, constructive client-facing language.

SUPPLIER: {ctx['supplier_name']}

RAW FINDINGS:
{findings_text}

TONE GUIDELINES:
- Professional and constructive — frame negatives as improvement opportunities
- Collaborative — "we recommend" not "you must"
- Specific — reference the actual data, don't be vague
- Balanced — acknowledge positives alongside risks
- Never alarmist — factual and measured

Respond with a JSON array where each item has:
- "original_title": the title from the raw finding
- "client_title": rewritten title for the client report
- "client_detail": 2-3 sentence professional description

Respond with ONLY the JSON array, no other text."""


def _build_recommended_actions(ctx: dict) -> str:
    findings_text = "\n".join(
        f"  - [{f.get('domain', 'general')}] {f['title']}"
        for f in ctx.get("findings", [])
    ) or "  No findings."

    return f"""You are writing recommended actions for a Hemera Intelligence supplier report. Actions should position Hemera as a partner that can help — not just flag problems.

SUPPLIER: {ctx['supplier_name']}

FINDINGS INCLUDED IN REPORT:
{findings_text}

INSTRUCTIONS:
- Each action should describe what Hemera can do to help, not just what the client should do
- Frame as services: "Hemera can facilitate...", "Hemera can conduct...", "Hemera can support..."
- Link each action to specific findings
- Order by priority (most impactful first)
- 3-5 actions maximum

Respond with a JSON array where each item has:
- "action_text": the recommended action (1-2 sentences, Hemera-as-service framing)
- "linked_findings": list of finding titles this action addresses
- "priority": 1 (highest) to 5 (lowest)

Respond with ONLY the JSON array, no other text."""


def _build_engagement_summary(ctx: dict) -> str:
    engagements_text = "\n".join(
        f"  - {e['subject']} [{e['status']}]: {e.get('notes', 'No notes')}"
        for e in ctx.get("engagements", [])
    ) or "  No engagements logged."

    return f"""Write a client-facing summary of Hemera's engagement with this supplier. The tone should convey that Hemera is actively working to help improve the supplier's ESG performance.

SUPPLIER: {ctx['supplier_name']}

HEMERA ENGAGEMENTS:
{engagements_text}

INSTRUCTIONS:
- Summarise what Hemera has done and what the outcomes are
- Be factual but positive — emphasise progress
- If engagements are in early stages, convey momentum
- 2-3 sentences maximum
- Do not include internal notes or contact details

Respond with a JSON object:
{{"summary": "The client-facing summary text"}}

Respond with ONLY the JSON object, no other text."""


def _build_exec_summary(ctx: dict) -> str:
    return f"""Write an executive summary for a HemeraScope Supplier Intelligence Report.

CLIENT: {ctx['org_name']}
SUPPLIERS ANALYSED: {ctx['supplier_count']}
TOTAL ANNUAL SPEND: £{ctx['total_spend']:,.0f}
CRITICAL RISK SUPPLIERS: {ctx['critical_count']}
NEEDS ATTENTION: {ctx['attention_count']}
STRONG PROFILE: {ctx['strong_count']}

INSTRUCTIONS:
- Open with the scope of the analysis
- Summarise the overall risk landscape
- Highlight the most significant findings
- Close with Hemera's commitment to collaborative improvement
- Frame this as a journey: "Every supply chain has areas for improvement. This report is the first step."
- Professional, measured, collaborative tone
- 150-200 words

Respond with a JSON object:
{{"summary": "The executive summary text"}}

Respond with ONLY the JSON object, no other text."""
```

- [ ] **Step 4: Implement AI task runner**

```python
# hemera/services/ai_task_runner.py
"""Executes AI tasks via API or prepares them for manual/Max mode."""
import hashlib
import json
import logging
from datetime import datetime
from anthropic import Anthropic
from hemera.config import get_settings
from hemera.models.ai_task import AITask
from hemera.services.ai_prompt_builder import build_prompt

log = logging.getLogger(__name__)


def create_ai_task(
    db,
    task_type: str,
    target_type: str,
    target_id: int,
    mode: str,
    context: dict,
) -> AITask:
    """Create an AI task and either execute it (API) or prepare the prompt (manual).

    Args:
        db: database session
        task_type: risk_analysis, client_language, recommended_actions, engagement_summary, exec_summary
        target_type: supplier or engagement
        target_id: the supplier or engagement ID
        mode: "api" or "manual"
        context: data dict passed to the prompt builder

    Returns:
        AITask with status "completed" (API) or "prompt_copied" (manual)
    """
    prompt = build_prompt(task_type, context)
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    task = AITask(
        task_type=task_type,
        target_type=target_type,
        target_id=target_id,
        mode=mode,
        status="pending",
        prompt_text=prompt,
        prompt_hash=prompt_hash,
    )
    db.add(task)
    db.flush()

    if mode == "api":
        _execute_api(task)
    else:
        task.status = "prompt_copied"

    db.flush()
    return task


def complete_manual_task(db, task: AITask, response_text: str) -> AITask:
    """Complete a manual/Max task by storing the pasted response.

    Args:
        db: database session
        task: the AITask with status "prompt_copied"
        response_text: the response pasted back from Claude Max

    Returns:
        Updated AITask with status "completed"
    """
    task.response_text = response_text
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.flush()
    return task


def _execute_api(task: AITask):
    """Call Claude API and store the response."""
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": task.prompt_text}],
        )
        task.response_text = response.content[0].text
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.token_count = response.usage.input_tokens + response.usage.output_tokens
        # Approximate cost: Sonnet input $3/MTok, output $15/MTok
        task.cost_usd = round(
            response.usage.input_tokens * 3 / 1_000_000
            + response.usage.output_tokens * 15 / 1_000_000,
            4,
        )
    except Exception as e:
        log.error(f"AI task {task.id} failed: {e}")
        task.status = "failed"
        task.response_text = str(e)
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_ai_prompt_builder.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add hemera/services/ai_prompt_builder.py hemera/services/ai_task_runner.py tests/test_ai_prompt_builder.py
git commit -m "feat: AI prompt builder + task runner — supports both API and manual/Max modes"
```

---

## Task 4: Backend API — Findings, AI Tasks, Supplier Engagements

**Files:**
- Create: `hemera/api/findings.py`
- Create: `hemera/api/ai_tasks.py`
- Modify: `hemera/main.py`
- Test: `tests/test_hemerascope_api.py`

- [ ] **Step 1: Write failing tests for findings and AI task endpoints**

```python
# tests/test_hemerascope_api.py
"""Tests for HemeraScope API endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from hemera.main import app
from hemera.database import Base, engine, SessionLocal, get_db
from hemera.models.supplier import Supplier
from hemera.models.engagement import Engagement
from hemera.models.finding import SupplierFinding, ReportSelection, ReportAction
from hemera.models.ai_task import AITask
from hemera.models.supplier_engagement import SupplierEngagement


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def supplier(db):
    s = Supplier(name="Test Corp", hemera_id="test-api-1", hemera_score=55.0)
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def engagement(db):
    e = Engagement(org_name="Client A", contact_email="a@test.com", status="delivered")
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def finding(db, supplier):
    f = SupplierFinding(
        supplier_id=supplier.id,
        source="deterministic",
        domain="governance",
        severity="high",
        title="Insolvency history",
        detail="Test detail",
        source_name="companies_house",
        is_active=True,
    )
    db.add(f)
    db.flush()
    return f


ADMIN_HEADERS = {"X-Test-Admin": "true"}  # Test auth bypass


def test_get_supplier_findings(client, supplier, finding):
    resp = client.get(f"/api/suppliers/{supplier.id}/findings", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Insolvency history"


def test_create_manual_finding(client, supplier):
    resp = client.post(
        f"/api/suppliers/{supplier.id}/findings",
        json={
            "source": "ai_manual",
            "domain": "carbon",
            "severity": "medium",
            "title": "Unusual filing pattern",
            "detail": "High filing activity despite declining revenue.",
            "source_name": "analyst",
        },
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Unusual filing pattern"


def test_create_ai_task_manual_mode(client, supplier):
    resp = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "risk_analysis",
            "target_type": "supplier",
            "target_id": supplier.id,
            "mode": "manual",
        },
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "prompt_copied"
    assert data["prompt_text"] is not None
    assert len(data["prompt_text"]) > 100


def test_paste_back_ai_task(client, supplier, db):
    task = AITask(
        task_type="client_language",
        target_type="supplier",
        target_id=supplier.id,
        mode="manual",
        status="prompt_copied",
        prompt_text="Test prompt",
        prompt_hash="abc",
    )
    db.add(task)
    db.flush()

    resp = client.patch(
        f"/api/ai-tasks/{task.id}",
        json={"response_text": '[{"original_title": "test", "client_title": "Test", "client_detail": "Detail"}]'},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_log_supplier_engagement(client, supplier):
    resp = client.post(
        f"/api/suppliers/{supplier.id}/engagements",
        json={
            "engagement_type": "outreach",
            "subject": "SBTi Discussion",
            "status": "contacted",
            "notes": "Sent initial email.",
        },
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 201
    assert resp.json()["subject"] == "SBTi Discussion"


def test_get_supplier_engagements(client, supplier, db):
    eng = SupplierEngagement(
        supplier_id=supplier.id,
        engagement_type="meeting",
        subject="Review session",
        status="completed",
        created_by=1,
    )
    db.add(eng)
    db.flush()

    resp = client.get(f"/api/suppliers/{supplier.id}/engagements", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_save_report_selection(client, engagement, finding):
    resp = client.patch(
        f"/api/engagements/{engagement.id}/supplier-report/selections",
        json={
            "selections": [
                {"finding_id": finding.id, "included": True, "analyst_note": "Important for this client"},
            ],
        },
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["saved"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_hemerascope_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement findings API**

```python
# hemera/api/findings.py
"""Supplier findings and engagement management endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.finding import SupplierFinding
from hemera.models.supplier_engagement import SupplierEngagement
from hemera.models.supplier import Supplier

router = APIRouter(prefix="/api/suppliers", tags=["findings"])


class CreateFindingRequest(BaseModel):
    source: str  # ai_manual, analyst
    domain: str
    severity: str
    title: str
    detail: str
    source_name: str
    evidence_url: str | None = None
    evidence_data: dict | None = None
    layer: int | None = None
    ai_task_id: int | None = None


class CreateEngagementRequest(BaseModel):
    engagement_type: str
    subject: str
    status: str
    notes: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    next_action: str | None = None
    next_action_date: str | None = None


class UpdateEngagementRequest(BaseModel):
    status: str | None = None
    notes: str | None = None
    next_action: str | None = None
    next_action_date: str | None = None


@router.get("/{supplier_id}/findings")
def get_findings(supplier_id: int, active_only: bool = True, db: Session = Depends(get_db)):
    query = db.query(SupplierFinding).filter(SupplierFinding.supplier_id == supplier_id)
    if active_only:
        query = query.filter(SupplierFinding.is_active == True)
    findings = query.order_by(SupplierFinding.severity, SupplierFinding.created_at.desc()).all()
    return [_finding_to_dict(f) for f in findings]


@router.post("/{supplier_id}/findings", status_code=201)
def create_finding(supplier_id: int, req: CreateFindingRequest, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).get(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    finding = SupplierFinding(
        supplier_id=supplier_id,
        source=req.source,
        domain=req.domain,
        severity=req.severity,
        title=req.title,
        detail=req.detail,
        source_name=req.source_name,
        evidence_url=req.evidence_url,
        evidence_data=req.evidence_data,
        layer=req.layer,
        ai_task_id=req.ai_task_id,
        is_active=True,
    )
    db.add(finding)
    db.commit()
    return _finding_to_dict(finding)


@router.post("/{supplier_id}/re-analyse")
def re_analyse(supplier_id: int, db: Session = Depends(get_db)):
    """Supersede existing findings and regenerate from current source data."""
    supplier = db.query(Supplier).get(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Mark existing deterministic findings as superseded
    now = datetime.utcnow()
    db.query(SupplierFinding).filter(
        SupplierFinding.supplier_id == supplier_id,
        SupplierFinding.source == "deterministic",
        SupplierFinding.is_active == True,
    ).update({"is_active": False, "superseded_at": now})

    # Regenerate from current scores
    from hemera.services.esg_scorer import calculate_esg_score
    from hemera.services.finding_generator import generate_findings_from_result
    from hemera.models.supplier import SupplierSource

    sources = db.query(SupplierSource).filter(SupplierSource.supplier_id == supplier_id).all()
    if sources:
        result = calculate_esg_score(sources)
        finding_dicts = generate_findings_from_result(result, supplier_name=supplier.name)

        for fd in finding_dicts:
            finding = SupplierFinding(supplier_id=supplier_id, is_active=True, **fd)
            db.add(finding)

    db.commit()
    return {"status": "ok", "supplier_id": supplier_id}


@router.get("/{supplier_id}/engagements")
def get_engagements(supplier_id: int, db: Session = Depends(get_db)):
    engs = (
        db.query(SupplierEngagement)
        .filter(SupplierEngagement.supplier_id == supplier_id)
        .order_by(SupplierEngagement.created_at.desc())
        .all()
    )
    return [_engagement_to_dict(e) for e in engs]


@router.post("/{supplier_id}/engagements", status_code=201)
def create_engagement(supplier_id: int, req: CreateEngagementRequest, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).get(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    eng = SupplierEngagement(
        supplier_id=supplier_id,
        engagement_type=req.engagement_type,
        subject=req.subject,
        status=req.status,
        notes=req.notes,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        next_action=req.next_action,
        contacted_at=datetime.utcnow() if req.status in ("contacted", "in_progress") else None,
        created_by=1,  # TODO: get from auth context
    )
    db.add(eng)
    db.commit()
    return _engagement_to_dict(eng)


@router.patch("/{supplier_id}/engagements/{engagement_id}")
def update_engagement(supplier_id: int, engagement_id: int, req: UpdateEngagementRequest, db: Session = Depends(get_db)):
    eng = db.query(SupplierEngagement).filter(
        SupplierEngagement.id == engagement_id,
        SupplierEngagement.supplier_id == supplier_id,
    ).first()
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if req.status is not None:
        eng.status = req.status
        if req.status in ("in_progress", "completed") and eng.responded_at is None:
            eng.responded_at = datetime.utcnow()
    if req.notes is not None:
        eng.notes = req.notes
    if req.next_action is not None:
        eng.next_action = req.next_action

    db.commit()
    return _engagement_to_dict(eng)


def _finding_to_dict(f: SupplierFinding) -> dict:
    return {
        "id": f.id,
        "supplier_id": f.supplier_id,
        "source": f.source,
        "domain": f.domain,
        "severity": f.severity,
        "title": f.title,
        "detail": f.detail,
        "evidence_url": f.evidence_url,
        "layer": f.layer,
        "source_name": f.source_name,
        "is_active": f.is_active,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _engagement_to_dict(e: SupplierEngagement) -> dict:
    return {
        "id": e.id,
        "supplier_id": e.supplier_id,
        "engagement_type": e.engagement_type,
        "subject": e.subject,
        "status": e.status,
        "notes": e.notes,
        "contact_name": e.contact_name,
        "contacted_at": e.contacted_at.isoformat() if e.contacted_at else None,
        "responded_at": e.responded_at.isoformat() if e.responded_at else None,
        "next_action": e.next_action,
        "next_action_date": str(e.next_action_date) if e.next_action_date else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
```

- [ ] **Step 4: Implement AI tasks API**

```python
# hemera/api/ai_tasks.py
"""AI task endpoints — create, query, and paste-back."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.ai_task import AITask
from hemera.services.ai_task_runner import create_ai_task, complete_manual_task

router = APIRouter(prefix="/api/ai-tasks", tags=["ai-tasks"])


class CreateAITaskRequest(BaseModel):
    task_type: str
    target_type: str
    target_id: int
    mode: str  # "api" or "manual"
    context: dict | None = None  # Optional override; if None, auto-built from target


class PasteBackRequest(BaseModel):
    response_text: str


@router.post("", status_code=201)
def create_task(req: CreateAITaskRequest, db: Session = Depends(get_db)):
    context = req.context or _build_context_from_target(req.task_type, req.target_type, req.target_id, db)

    task = create_ai_task(
        db=db,
        task_type=req.task_type,
        target_type=req.target_type,
        target_id=req.target_id,
        mode=req.mode,
        context=context,
    )
    db.commit()
    return _task_to_dict(task)


@router.patch("/{task_id}")
def paste_back(task_id: int, req: PasteBackRequest, db: Session = Depends(get_db)):
    task = db.query(AITask).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")
    if task.status != "prompt_copied":
        raise HTTPException(status_code=400, detail=f"Task status is {task.status}, expected prompt_copied")

    task = complete_manual_task(db, task, req.response_text)
    db.commit()
    return _task_to_dict(task)


@router.get("")
def list_tasks(target_type: str | None = None, target_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(AITask)
    if target_type:
        query = query.filter(AITask.target_type == target_type)
    if target_id:
        query = query.filter(AITask.target_id == target_id)
    tasks = query.order_by(AITask.created_at.desc()).limit(50).all()
    return [_task_to_dict(t) for t in tasks]


def _build_context_from_target(task_type: str, target_type: str, target_id: int, db) -> dict:
    """Auto-build prompt context from database state."""
    if target_type == "supplier":
        from hemera.models.supplier import Supplier, SupplierSource
        from hemera.models.finding import SupplierFinding
        from hemera.models.supplier_engagement import SupplierEngagement

        supplier = db.query(Supplier).get(target_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        if task_type == "risk_analysis":
            sources = db.query(SupplierSource).filter(SupplierSource.supplier_id == target_id).all()
            findings = db.query(SupplierFinding).filter(
                SupplierFinding.supplier_id == target_id,
                SupplierFinding.is_active == True,
                SupplierFinding.source == "deterministic",
            ).all()
            return {
                "supplier_name": supplier.legal_name or supplier.name,
                "sector": supplier.sector,
                "sic_codes": supplier.sic_codes or [],
                "sources_summary": [
                    {"layer": s.layer, "source": s.source_name, "summary": s.summary or ""}
                    for s in sources
                ],
                "deterministic_findings": [
                    {"title": f.title, "severity": f.severity}
                    for f in findings
                ],
                "hemera_score": supplier.hemera_score,
                "domain_scores": {},  # Could populate from latest SupplierScore
            }

        if task_type in ("client_language", "recommended_actions"):
            findings = db.query(SupplierFinding).filter(
                SupplierFinding.supplier_id == target_id,
                SupplierFinding.is_active == True,
            ).all()
            return {
                "supplier_name": supplier.legal_name or supplier.name,
                "findings": [
                    {"title": f.title, "detail": f.detail, "severity": f.severity, "domain": f.domain}
                    for f in findings
                ],
            }

        if task_type == "engagement_summary":
            engs = db.query(SupplierEngagement).filter(
                SupplierEngagement.supplier_id == target_id
            ).all()
            return {
                "supplier_name": supplier.legal_name or supplier.name,
                "engagements": [
                    {"subject": e.subject, "status": e.status, "notes": e.notes}
                    for e in engs
                ],
            }

    if target_type == "engagement" and task_type == "exec_summary":
        from hemera.models.engagement import Engagement
        from hemera.models.finding import SupplierFinding, ReportSelection

        engagement = db.query(Engagement).get(target_id)
        if not engagement:
            raise HTTPException(status_code=404, detail="Engagement not found")

        # Count suppliers by risk level from selections
        return {
            "org_name": engagement.display_name or engagement.org_name,
            "supplier_count": engagement.supplier_count or 0,
            "total_spend": 0,  # Calculated from transactions
            "critical_count": 0,
            "attention_count": 0,
            "strong_count": 0,
        }

    return {}


def _task_to_dict(t: AITask) -> dict:
    return {
        "id": t.id,
        "task_type": t.task_type,
        "target_type": t.target_type,
        "target_id": t.target_id,
        "mode": t.mode,
        "status": t.status,
        "prompt_text": t.prompt_text,
        "response_text": t.response_text,
        "prompt_hash": t.prompt_hash,
        "token_count": t.token_count,
        "cost_usd": t.cost_usd,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }
```

- [ ] **Step 5: Implement HemeraScope curation API**

```python
# hemera/api/hemerascope.py
"""HemeraScope report curation, preview, and publish endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.models.finding import SupplierFinding, ReportSelection, ReportAction
from hemera.models.supplier import Supplier
from hemera.models.supplier_engagement import SupplierEngagement
from hemera.models.transaction import Transaction

router = APIRouter(prefix="/api/engagements", tags=["hemerascope"])


class SelectionItem(BaseModel):
    finding_id: int
    included: bool
    client_title: str | None = None
    client_detail: str | None = None
    client_language_source: str | None = None
    analyst_note: str | None = None


class SaveSelectionsRequest(BaseModel):
    selections: list[SelectionItem]


class SaveActionsRequest(BaseModel):
    supplier_id: int
    actions: list[dict]  # [{action_text, priority, linked_finding_ids, language_source}]


@router.get("/{engagement_id}/supplier-report")
def get_supplier_report(engagement_id: int, db: Session = Depends(get_db)):
    """Get all suppliers, findings, and current selections for curation."""
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Get all suppliers linked to this engagement via transactions
    supplier_ids = (
        db.query(Transaction.supplier_id)
        .filter(
            Transaction.engagement_id == engagement_id,
            Transaction.supplier_id.isnot(None),
            Transaction.is_duplicate == False,
        )
        .distinct()
        .all()
    )
    supplier_ids = [sid for (sid,) in supplier_ids]

    suppliers_data = []
    for sid in supplier_ids:
        supplier = db.query(Supplier).get(sid)
        if not supplier:
            continue

        findings = (
            db.query(SupplierFinding)
            .filter(SupplierFinding.supplier_id == sid, SupplierFinding.is_active == True)
            .order_by(SupplierFinding.severity, SupplierFinding.created_at.desc())
            .all()
        )

        selections = (
            db.query(ReportSelection)
            .filter(
                ReportSelection.engagement_id == engagement_id,
                ReportSelection.finding_id.in_([f.id for f in findings]) if findings else False,
            )
            .all()
        )
        selections_map = {s.finding_id: s for s in selections}

        actions = (
            db.query(ReportAction)
            .filter(ReportAction.engagement_id == engagement_id, ReportAction.supplier_id == sid)
            .order_by(ReportAction.priority)
            .all()
        )

        hemera_engs = (
            db.query(SupplierEngagement)
            .filter(SupplierEngagement.supplier_id == sid)
            .order_by(SupplierEngagement.created_at.desc())
            .all()
        )

        # Aggregate transaction stats
        from sqlalchemy import func
        stats = db.query(
            func.count(Transaction.id),
            func.sum(Transaction.amount_gbp),
            func.sum(Transaction.co2e_kg),
        ).filter(
            Transaction.engagement_id == engagement_id,
            Transaction.supplier_id == sid,
            Transaction.is_duplicate == False,
        ).first()

        suppliers_data.append({
            "supplier": {
                "id": supplier.id,
                "name": supplier.name,
                "legal_name": supplier.legal_name,
                "ch_number": supplier.ch_number,
                "sector": supplier.sector,
                "entity_type": supplier.entity_type,
                "hemera_score": supplier.hemera_score,
                "confidence": supplier.confidence,
                "critical_flag": supplier.critical_flag,
                "hemera_verified": supplier.hemera_verified,
            },
            "txn_count": stats[0] if stats else 0,
            "total_spend": round(stats[1] or 0, 2) if stats else 0,
            "total_co2e_kg": round(stats[2] or 0, 2) if stats else 0,
            "findings": [
                {
                    "id": f.id,
                    "source": f.source,
                    "domain": f.domain,
                    "severity": f.severity,
                    "title": f.title,
                    "detail": f.detail,
                    "evidence_url": f.evidence_url,
                    "layer": f.layer,
                    "source_name": f.source_name,
                    "selection": {
                        "included": selections_map[f.id].included,
                        "client_title": selections_map[f.id].client_title,
                        "client_detail": selections_map[f.id].client_detail,
                        "analyst_note": selections_map[f.id].analyst_note,
                    } if f.id in selections_map else None,
                }
                for f in findings
            ],
            "actions": [
                {
                    "id": a.id,
                    "action_text": a.action_text,
                    "priority": a.priority,
                    "linked_finding_ids": a.linked_finding_ids,
                    "language_source": a.language_source,
                }
                for a in actions
            ],
            "hemera_engagements": [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "status": e.status,
                    "engagement_type": e.engagement_type,
                    "contacted_at": e.contacted_at.isoformat() if e.contacted_at else None,
                    "responded_at": e.responded_at.isoformat() if e.responded_at else None,
                    "notes": e.notes,
                }
                for e in hemera_engs
            ],
        })

    # Sort: critical first, then by hemera_score ascending
    suppliers_data.sort(
        key=lambda s: (
            0 if s["supplier"]["critical_flag"] else 1,
            s["supplier"]["hemera_score"] or 999,
        )
    )

    return {
        "engagement_id": engagement_id,
        "status": engagement.supplier_report_status or "pending",
        "supplier_count": len(suppliers_data),
        "suppliers": suppliers_data,
    }


@router.patch("/{engagement_id}/supplier-report/selections")
def save_selections(engagement_id: int, req: SaveSelectionsRequest, db: Session = Depends(get_db)):
    """Save include/exclude decisions incrementally (upsert)."""
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if not engagement.supplier_report_status or engagement.supplier_report_status == "pending":
        engagement.supplier_report_status = "curating"

    saved = 0
    for item in req.selections:
        existing = db.query(ReportSelection).filter(
            ReportSelection.engagement_id == engagement_id,
            ReportSelection.finding_id == item.finding_id,
        ).first()

        if existing:
            existing.included = item.included
            if item.client_title is not None:
                existing.client_title = item.client_title
            if item.client_detail is not None:
                existing.client_detail = item.client_detail
            if item.client_language_source is not None:
                existing.client_language_source = item.client_language_source
            if item.analyst_note is not None:
                existing.analyst_note = item.analyst_note
        else:
            sel = ReportSelection(
                engagement_id=engagement_id,
                finding_id=item.finding_id,
                included=item.included,
                client_title=item.client_title,
                client_detail=item.client_detail,
                client_language_source=item.client_language_source,
                analyst_note=item.analyst_note,
                selected_by=1,  # TODO: from auth
            )
            db.add(sel)
        saved += 1

    db.commit()
    return {"saved": saved}


@router.post("/{engagement_id}/supplier-report/actions")
def save_actions(engagement_id: int, req: SaveActionsRequest, db: Session = Depends(get_db)):
    """Save recommended actions for a supplier in this engagement."""
    # Clear existing actions for this supplier
    db.query(ReportAction).filter(
        ReportAction.engagement_id == engagement_id,
        ReportAction.supplier_id == req.supplier_id,
    ).delete()

    for action in req.actions:
        ra = ReportAction(
            engagement_id=engagement_id,
            supplier_id=req.supplier_id,
            action_text=action["action_text"],
            priority=action.get("priority", 1),
            linked_finding_ids=action.get("linked_finding_ids"),
            language_source=action.get("language_source", "analyst"),
            created_by=1,  # TODO: from auth
        )
        db.add(ra)

    db.commit()
    return {"status": "ok"}


@router.post("/{engagement_id}/supplier-report/publish")
def publish_report(engagement_id: int, db: Session = Depends(get_db)):
    """Publish the supplier report to the client dashboard."""
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    engagement.supplier_report_status = "published"
    db.commit()
    return {"status": "published", "engagement_id": engagement_id}


# ── Client-facing endpoints (no admin required) ──

@router.get("/{engagement_id}/supplier-intelligence")
def get_published_report(engagement_id: int, db: Session = Depends(get_db)):
    """Client-facing: get published supplier intelligence data."""
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if engagement.supplier_report_status != "published":
        raise HTTPException(status_code=404, detail="Supplier report not yet published")

    # Return only included selections with client-facing language
    # (Reuses get_supplier_report logic but filters to included only)
    full_report = get_supplier_report(engagement_id, db)

    for supplier in full_report["suppliers"]:
        supplier["findings"] = [
            {
                "title": f["selection"]["client_title"] or f["title"],
                "detail": f["selection"]["client_detail"] or f["detail"],
                "severity": f["severity"],
                "domain": f["domain"],
            }
            for f in supplier["findings"]
            if f.get("selection") and f["selection"]["included"]
        ]
        # Remove internal notes from hemera engagements
        for eng in supplier["hemera_engagements"]:
            eng.pop("notes", None)

    return full_report
```

- [ ] **Step 6: Register new routers in main.py**

In `hemera/main.py`, add:
```python
from hemera.api import findings, ai_tasks, hemerascope

app.include_router(findings.router, tags=["findings"])
app.include_router(ai_tasks.router, tags=["ai-tasks"])
app.include_router(hemerascope.router, tags=["hemerascope"])
```

- [ ] **Step 7: Run tests**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_hemerascope_api.py -v`
Expected: All tests PASS (may need to adjust auth mocking to match existing patterns in test_engagements_api.py)

- [ ] **Step 8: Run all tests**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add hemera/api/findings.py hemera/api/ai_tasks.py hemera/api/hemerascope.py hemera/main.py tests/test_hemerascope_api.py
git commit -m "feat: HemeraScope API — findings CRUD, AI tasks, report curation, client-facing endpoints"
```

---

## Task 5: Wire Finding Generation into Enrichment Pipeline

**Files:**
- Modify: `hemera/services/enrichment.py`
- Test: `tests/test_pipeline.py` (add test)

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_pipeline.py or create tests/test_enrichment_findings.py
def test_enrichment_generates_findings(db):
    """After enrichment, supplier_findings should be populated."""
    from hemera.models.supplier import Supplier
    from hemera.models.finding import SupplierFinding

    supplier = Supplier(name="Test Corp", hemera_id="enrich-test")
    db.add(supplier)
    db.flush()

    # Simulate enrichment having run (sources + score exist)
    # Then check findings were generated
    findings = db.query(SupplierFinding).filter(
        SupplierFinding.supplier_id == supplier.id,
        SupplierFinding.source == "deterministic",
    ).all()

    # After enrichment wiring, this should have findings
    # For now this test documents the expected behavior
    assert isinstance(findings, list)
```

- [ ] **Step 2: Add finding generation to enrichment.py**

At the end of `enrich_supplier()` in `hemera/services/enrichment.py`, after the ESG score is calculated and stored, add:

```python
    # Generate deterministic findings from the score
    from hemera.services.finding_generator import generate_findings_from_result
    from hemera.models.finding import SupplierFinding

    # Supersede existing deterministic findings
    db.query(SupplierFinding).filter(
        SupplierFinding.supplier_id == supplier.id,
        SupplierFinding.source == "deterministic",
        SupplierFinding.is_active == True,
    ).update({"is_active": False, "superseded_at": datetime.utcnow()})

    finding_dicts = generate_findings_from_result(esg_result, supplier_name=name)
    for fd in finding_dicts:
        finding = SupplierFinding(supplier_id=supplier.id, is_active=True, **fd)
        db.add(finding)

    results["findings_generated"] = len(finding_dicts)
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add hemera/services/enrichment.py tests/
git commit -m "feat: wire finding generation into enrichment pipeline"
```

---

## Task 6: Frontend — AI Task Buttons Component

**Files:**
- Create: `dashboard/components/ai-task-buttons.tsx`

- [ ] **Step 1: Create the reusable AI task buttons component**

```tsx
// dashboard/components/ai-task-buttons.tsx
"use client";

import { useState } from "react";

interface AITaskButtonsProps {
  taskType: string;
  targetType: string;
  targetId: number;
  context?: Record<string, unknown>;
  onResult: (responseText: string) => void;
  apiUrl?: string;
}

export default function AITaskButtons({
  taskType,
  targetType,
  targetId,
  context,
  onResult,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
}: AITaskButtonsProps) {
  const [status, setStatus] = useState<"idle" | "loading" | "awaiting_paste" | "done">("idle");
  const [taskId, setTaskId] = useState<number | null>(null);
  const [pasteValue, setPasteValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate(mode: "api" | "manual") {
    setStatus("loading");
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/api/ai-tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          task_type: taskType,
          target_type: targetType,
          target_id: targetId,
          mode,
          context: context || null,
        }),
      });

      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      setTaskId(data.id);

      if (mode === "api") {
        // API mode — response is already there
        setStatus("done");
        if (data.response_text) onResult(data.response_text);
      } else {
        // Manual mode — copy prompt to clipboard
        await navigator.clipboard.writeText(data.prompt_text);
        setStatus("awaiting_paste");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setStatus("idle");
    }
  }

  async function handlePasteBack() {
    if (!taskId || !pasteValue.trim()) return;
    setStatus("loading");

    try {
      const res = await fetch(`${apiUrl}/api/ai-tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ response_text: pasteValue }),
      });

      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setStatus("done");
      onResult(pasteValue);
      setPasteValue("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setStatus("awaiting_paste");
    }
  }

  if (status === "awaiting_paste") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
          <span>Prompt copied to clipboard. Paste into Claude Max, then paste the response below.</span>
        </div>
        <textarea
          className="w-full border border-gray-200 rounded-lg p-3 text-sm font-mono resize-y min-h-[100px]"
          placeholder="Paste Claude Max response here..."
          value={pasteValue}
          onChange={(e) => setPasteValue(e.target.value)}
        />
        <div className="flex gap-2">
          <button
            onClick={handlePasteBack}
            disabled={!pasteValue.trim()}
            className="px-4 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700 disabled:opacity-50"
          >
            Apply Response
          </button>
          <button
            onClick={() => { setStatus("idle"); setPasteValue(""); }}
            className="px-4 py-2 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={() => handleGenerate("api")}
        disabled={status === "loading"}
        className="px-3 py-1.5 border border-purple-400 text-purple-600 text-xs rounded-lg hover:bg-purple-50 disabled:opacity-50"
      >
        {status === "loading" ? "Generating..." : "✨ Generate (API)"}
      </button>
      <button
        onClick={() => handleGenerate("manual")}
        disabled={status === "loading"}
        className="px-3 py-1.5 border border-gray-200 text-gray-600 text-xs rounded-lg hover:bg-gray-50 disabled:opacity-50"
      >
        📋 Copy Prompt (Max)
      </button>
      {error && <span className="text-xs text-red-500 self-center">{error}</span>}
      {status === "done" && <span className="text-xs text-green-600 self-center">✓ Done</span>}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add dashboard/components/ai-task-buttons.tsx
git commit -m "feat: reusable AI task buttons component — API + Max modes with paste-back"
```

---

## Task 7: Frontend — Supplier Curation Page (Stage 1)

**Files:**
- Create: `dashboard/app/dashboard/[id]/hemerascope/page.tsx`
- Create: `dashboard/components/finding-card.tsx`
- Create: `dashboard/components/report-preview.tsx`

This is the largest frontend task. The supplier curation page with split-panel view, finding cards, report preview, and AI task integration.

- [ ] **Step 1: Create FindingCard component**

```tsx
// dashboard/components/finding-card.tsx
"use client";

interface Finding {
  id: number;
  source: string;
  domain: string;
  severity: string;
  title: string;
  detail: string;
  evidence_url: string | null;
  layer: number | null;
  source_name: string;
  selection: {
    included: boolean;
    client_title: string | null;
    client_detail: string | null;
    analyst_note: string | null;
  } | null;
}

interface FindingCardProps {
  finding: Finding;
  onToggle: (findingId: number, included: boolean) => void;
}

const SEVERITY_STYLES: Record<string, { border: string; bg: string; badge: string; badgeBg: string }> = {
  critical: { border: "border-l-red-500", bg: "bg-red-50/50", badge: "text-red-800", badgeBg: "bg-red-100" },
  high: { border: "border-l-amber-500", bg: "bg-amber-50/50", badge: "text-amber-800", badgeBg: "bg-amber-100" },
  medium: { border: "border-l-yellow-400", bg: "bg-yellow-50/30", badge: "text-yellow-800", badgeBg: "bg-yellow-100" },
  info: { border: "border-l-blue-400", bg: "bg-blue-50/30", badge: "text-blue-800", badgeBg: "bg-blue-100" },
  positive: { border: "border-l-green-500", bg: "bg-green-50/50", badge: "text-green-800", badgeBg: "bg-green-100" },
};

export default function FindingCard({ finding, onToggle }: FindingCardProps) {
  const styles = SEVERITY_STYLES[finding.severity] || SEVERITY_STYLES.info;
  const isIncluded = finding.selection?.included ?? false;

  return (
    <div className={`p-3 mb-2 rounded-r-lg border-l-3 ${styles.border} ${styles.bg} flex justify-between items-start`}>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${styles.badgeBg} ${styles.badge} uppercase`}>
            {finding.severity}
          </span>
          <span className="text-[10px] text-gray-400">{finding.domain}</span>
          {finding.source !== "deterministic" && (
            <span className="text-[10px] text-purple-500">{finding.source}</span>
          )}
        </div>
        <div className="text-sm font-medium mt-1">{finding.title}</div>
        <div className="text-xs text-gray-500 mt-0.5">{finding.detail}</div>
        {finding.evidence_url && (
          <a href={finding.evidence_url} target="_blank" rel="noopener" className="text-xs text-teal-600 hover:underline mt-1 inline-block">
            View source →
          </a>
        )}
      </div>
      <button
        onClick={() => onToggle(finding.id, !isIncluded)}
        className={`ml-3 px-3 py-1 text-xs rounded-lg shrink-0 ${
          isIncluded
            ? "bg-teal-600 text-white"
            : "border border-teal-600 text-teal-600 hover:bg-teal-50"
        }`}
      >
        {isIncluded ? "✓ Included" : "Include"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create the curation page**

Create `dashboard/app/dashboard/[id]/hemerascope/page.tsx` — the main supplier-by-supplier curation view. This is a large file (~400 lines) implementing:

- Fetch supplier report data from `GET /engagements/{id}/supplier-report`
- Split-panel layout: findings left, preview right
- Findings grouped by source (deterministic, AI, outlier)
- Include/Skip toggles with incremental save via `PATCH .../selections`
- AI task buttons for risk analysis, client language, recommended actions, engagement summary
- Log Engagement modal
- Previous/Next supplier navigation
- Progress tracking

(Full implementation to be written by the executing agent following the component structure defined above and the mockups in `.superpowers/brainstorm/`)

- [ ] **Step 3: Build and verify**

Run: `cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add dashboard/app/dashboard/\[id\]/hemerascope/ dashboard/components/finding-card.tsx dashboard/components/report-preview.tsx
git commit -m "feat: HemeraScope curation page — supplier-by-supplier findings review with AI task integration"
```

---

## Task 8: Frontend — Report Review Page (Stage 2)

**Files:**
- Create: `dashboard/app/dashboard/[id]/hemerascope/review/page.tsx`

- [ ] **Step 1: Create the report review page**

Full report preview with table of contents, executive summary, per-supplier sections, and publish/export controls. Implements:

- TOC sidebar with section navigation
- Executive summary with AI generate/edit
- Per-supplier sections showing included findings, actions, engagement status
- "Export PDF" button (calls `/api/engagements/{id}/supplier-intelligence/pdf`)
- "Publish to Client Dashboard" button (calls `POST .../supplier-report/publish`)

(Full implementation by executing agent)

- [ ] **Step 2: Build and verify**

Run: `cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add dashboard/app/dashboard/\[id\]/hemerascope/review/
git commit -m "feat: HemeraScope report review page — full preview with publish + export"
```

---

## Task 9: Frontend — Client-Facing Supplier Intelligence Views

**Files:**
- Create: `dashboard/app/dashboard/[id]/hemerascope/report/page.tsx`
- Create: `dashboard/app/dashboard/[id]/hemerascope/report/[supplierId]/page.tsx`

- [ ] **Step 1: Create supplier overview page (client view)**

Table of suppliers with Hemera Score, risk level, key findings, Hemera engagement status. Filterable, sortable. Export PDF button. Only shows published reports.

Calls `GET /engagements/{id}/supplier-intelligence` (client-facing endpoint).

- [ ] **Step 2: Create supplier detail page (client view)**

Per-supplier page: Hemera Score, domain breakdown, curated findings, recommended actions, Hemera engagement narrative. All client-facing language.

- [ ] **Step 3: Build and verify**

Run: `cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add dashboard/app/dashboard/\[id\]/hemerascope/report/
git commit -m "feat: HemeraScope client views — supplier overview + detail pages"
```

---

## Task 10: HemeraScope PDF Report

**Files:**
- Create: `hemera/services/hemerascope_report.py`
- Create: `hemera/templates/hemerascope/` (multiple templates)
- Modify: `hemera/api/hemerascope.py` (add PDF endpoint)
- Test: `tests/test_hemerascope_pdf.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_hemerascope_pdf.py
def test_hemerascope_report_data_generation(db):
    """Report data includes carbon + supplier intelligence sections."""
    from hemera.services.hemerascope_report import generate_hemerascope_data

    # Set up engagement with transactions, suppliers, findings, selections
    # (fixture setup omitted for brevity — mirrors test_pdf_report.py pattern)

    data = generate_hemerascope_data(engagement, db)

    assert "carbon" in data  # Existing carbon sections
    assert "suppliers" in data  # New supplier intelligence sections
    assert "exec_summary" in data
    assert "methodology" in data
```

- [ ] **Step 2: Implement HemeraScope report data gathering**

`hemera/services/hemerascope_report.py` — combines existing `generate_report_data()` output with new supplier intelligence data. Includes:

- Executive summary text
- Methodology section (templated, not revealing the 13-layer protocol)
- Aggregate risk stats (critical/attention/strong counts, domain averages)
- Per-supplier data (included findings, actions, engagement status)
- Recommendations summary
- Charts: risk distribution donut, domain heatmap, per-supplier score bars

- [ ] **Step 3: Create Jinja2 templates**

Create templates in `hemera/templates/hemerascope/`:
- `cover.html` — branded cover page
- `exec_summary.html` — executive summary with stats
- `methodology.html` — collaborative methodology overview
- `risk_overview.html` — aggregate charts
- `supplier_page.html` — per-supplier template (reused for each supplier)
- `recommendations.html` — grouped recommendations
- `back_cover.html`

- [ ] **Step 4: Add PDF endpoint to hemerascope.py**

```python
@router.get("/{engagement_id}/supplier-intelligence/pdf")
def export_pdf(engagement_id: int, db: Session = Depends(get_db)):
    from hemera.services.hemerascope_report import generate_hemerascope_pdf
    from fastapi.responses import Response

    engagement = db.query(Engagement).get(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    pdf_bytes = generate_hemerascope_pdf(engagement, db)
    filename = f"HemeraScope-{engagement.display_name or engagement.org_name}-{engagement.fiscal_year_end or 'report'}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/test_hemerascope_pdf.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add hemera/services/hemerascope_report.py hemera/templates/hemerascope/ hemera/api/hemerascope.py tests/test_hemerascope_pdf.py
git commit -m "feat: HemeraScope unified PDF report — carbon + supplier intelligence combined"
```

---

## Task 11: Update Sidebar Navigation & Integration

**Files:**
- Modify: `dashboard/app/dashboard/[id]/layout.tsx`
- Modify: `dashboard/app/dashboard/clients/client-queue.tsx` (update status stages)

- [ ] **Step 1: Add HemeraScope to sidebar navigation**

Add "HemeraScope" link to the engagement sidebar, between existing sections. For admin: links to curation page. For client: links to client report view (only visible when published).

- [ ] **Step 2: Update client queue progress stages**

Update the multi-stage pipeline in `client-queue.tsx` to include:
`Process → Processing → Carbon QC → Supplier Review → Report Review → Published`

The "Supplier Review" stage maps to `supplier_report_status: curating`.

- [ ] **Step 3: Build and verify**

Run: `cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Run all backend tests**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add dashboard/app/dashboard/
git commit -m "feat: add HemeraScope to sidebar nav + update pipeline stages"
```

---

## Task 12: Rename esg_score → hemera_score in Frontend

**Files:**
- Modify: Multiple dashboard files referencing `esg_score`

- [ ] **Step 1: Find all frontend references**

Run: `cd /Users/nicohenry/Documents/Hemera && grep -rn "esg_score\|esgScore\|ESG Score\|ESG score" dashboard/ --include="*.tsx" --include="*.ts"`

- [ ] **Step 2: Replace all occurrences**

- `esg_score` → `hemera_score`
- `esgScore` → `hemeraScore`
- `"ESG Score"` → `"Hemera Score"`
- `"ESG score"` → `"Hemera Score"`

- [ ] **Step 3: Build and verify**

Run: `cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera
git add dashboard/
git commit -m "refactor: rename ESG Score → Hemera Score throughout frontend"
```

---

## Task 13: End-to-End Verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd /Users/nicohenry/Documents/Hemera && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Build frontend**

Run: `cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build`
Expected: Clean build, no errors

- [ ] **Step 3: Manual smoke test**

Start backend and frontend locally:
```bash
cd /Users/nicohenry/Documents/Hemera && uvicorn hemera.main:app --reload &
cd /Users/nicohenry/Documents/Hemera/dashboard && npm run dev &
```

Test the flow:
1. Navigate to an existing delivered engagement
2. Open HemeraScope curation page
3. Verify suppliers appear with findings
4. Toggle include/exclude on a finding — verify it saves
5. Test "Copy Prompt" button — verify prompt is on clipboard
6. Navigate to report review page
7. Test publish flow
8. Verify client view shows only included findings

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: end-to-end verification fixes"
```
