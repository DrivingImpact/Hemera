# Upload Flow & Dashboard Guards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split upload into parse-only (free) and admin-triggered processing (costs tokens). Show empty states on all dashboard pages until analyst approves.

**Architecture:** Strip the upload endpoint to parse-only. Extract the classification/calculation pipeline into a new service function. Add a new admin-only endpoint to trigger processing. Update all frontend pages to check engagement status and show a pending banner when not `qc_passed`.

**Tech Stack:** Python/FastAPI (backend changes), Next.js/TypeScript (frontend changes)

**Spec:** `docs/superpowers/specs/2026-04-07-upload-flow-design.md`

---

### Task 1: Extract pipeline into standalone service

**Files:**
- Create: `hemera/services/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the test**

Create `tests/test_pipeline.py`:

```python
"""Tests for the processing pipeline service."""

from unittest.mock import MagicMock, patch
import pytest
from hemera.services.pipeline import run_processing_pipeline


def _make_txn(**kwargs):
    t = MagicMock()
    t.raw_supplier = kwargs.get("raw_supplier", "Test Supplier")
    t.raw_description = kwargs.get("raw_description", "Office supplies")
    t.raw_category = kwargs.get("raw_category", "")
    t.co2e_kg = kwargs.get("co2e_kg", None)
    t.scope = kwargs.get("scope", None)
    t.amount_gbp = kwargs.get("amount_gbp", 100.0)
    t.supplier_id = None
    t.supplier_match_method = None
    t.is_duplicate = False
    t.needs_review = False
    return t


def _make_engagement(**kwargs):
    e = MagicMock()
    e.id = kwargs.get("id", 1)
    e.status = kwargs.get("status", "uploaded")
    e.org_name = kwargs.get("org_name", "Test Org")
    return e


class TestRunProcessingPipeline:
    @patch("hemera.services.pipeline.calculate_emissions")
    @patch("hemera.services.pipeline.match_suppliers_batch")
    @patch("hemera.services.pipeline.classify_transaction")
    @patch("hemera.services.pipeline.seed_emission_factors")
    def test_updates_engagement_to_delivered(self, mock_seed, mock_classify, mock_match, mock_calc):
        mock_classify.return_value = MagicMock(
            scope=3, ghg_category=1, category_name="Office supplies",
            method="keyword", confidence=0.9,
        )
        mock_match.return_value = {}
        mock_calc.return_value = {
            "total_co2e_tonnes": 1.5, "scope1_kg": 0, "scope2_kg": 0, "scope3_kg": 1500,
            "overall_gsd": 1.4, "ci_lower_tonnes": 0.8, "ci_upper_tonnes": 2.5,
            "transactions_calculated": 1, "transactions_missing_ef": 0,
        }

        eng = _make_engagement(status="uploaded")
        txns = [_make_txn()]
        db = MagicMock()

        result = run_processing_pipeline(eng, txns, db)

        assert eng.status == "delivered"
        assert eng.total_co2e == 1.5
        assert result["status"] == "delivered"
        assert result["total_tCO2e"] == 1.5

    def test_rejects_non_uploaded_status(self):
        eng = _make_engagement(status="delivered")
        with pytest.raises(ValueError, match="Cannot process"):
            run_processing_pipeline(eng, [], MagicMock())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'hemera.services.pipeline'`

- [ ] **Step 3: Create the pipeline service**

Create `hemera/services/pipeline.py`:

```python
"""Processing pipeline — classify, match, calculate.

Extracted from upload.py so it can be triggered separately by admins.
This is where Anthropic API tokens get consumed.
"""

from sqlalchemy.orm import Session
from hemera.services.classifier import classify_transaction
from hemera.services.supplier_match import match_suppliers_batch
from hemera.services.emission_calc import calculate_emissions
from hemera.services.seed_factors import seed_emission_factors


def run_processing_pipeline(engagement, transactions: list, db: Session) -> dict:
    """Run the full classification + calculation pipeline on an engagement.

    Requires engagement.status == 'uploaded'. Updates status to 'delivered'.
    Returns a summary dict.
    """
    if engagement.status != "uploaded":
        raise ValueError(f"Cannot process engagement with status '{engagement.status}'. Must be 'uploaded'.")

    # Ensure emission factors are seeded
    seed_emission_factors(db)

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

    # 3. Calculate emissions + pedigree uncertainty
    calc_results = calculate_emissions(transactions, db)

    # 4. Update engagement summary
    engagement.status = "delivered"
    engagement.total_co2e = calc_results["total_co2e_tonnes"]
    engagement.scope1_co2e = calc_results["scope1_kg"] / 1000
    engagement.scope2_co2e = calc_results["scope2_kg"] / 1000
    engagement.scope3_co2e = calc_results["scope3_kg"] / 1000
    engagement.gsd_total = calc_results["overall_gsd"]
    engagement.ci_lower = calc_results["ci_lower_tonnes"]
    engagement.ci_upper = calc_results["ci_upper_tonnes"]

    db.commit()

    return {
        "status": "delivered",
        "total_tCO2e": round(calc_results["total_co2e_tonnes"], 2),
        "classified": classified_count,
        "unclassified": unclassified_count,
        "new_suppliers": new_suppliers,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_pipeline.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add hemera/services/pipeline.py tests/test_pipeline.py
git commit -m "feat: extract processing pipeline into standalone service"
```

---

### Task 2: Strip upload endpoint to parse-only

**Files:**
- Modify: `hemera/api/upload.py`

- [ ] **Step 1: Replace upload.py with parse-only version**

Replace the entire content of `hemera/api/upload.py` with:

```python
"""CSV upload endpoint — parse only, no classification or calculation.

Processing is triggered separately by admins via POST /engagements/{id}/process.
"""

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from hemera.database import get_db
from hemera.models.engagement import Engagement
from hemera.services.csv_parser import parse_accounting_csv
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser

router = APIRouter()


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Upload an accounting CSV/Excel file — parse and store only.

    No classification, no emission calculation, no AI token usage.
    The data sits in 'uploaded' status until an admin triggers processing.
    """
    contents = await file.read()
    filename = file.filename or "upload.csv"

    # Create engagement
    engagement = Engagement(
        org_name=current_user.org_name,
        upload_filename=filename,
        status="uploaded",
    )
    db.add(engagement)
    db.flush()

    # Parse the file — creates Transaction objects with raw fields only
    transactions, parse_summary = parse_accounting_csv(contents, filename, engagement.id)

    # Save transactions
    engagement.transaction_count = len(transactions)
    engagement.supplier_count = parse_summary["unique_suppliers"]
    db.add_all(transactions)
    db.commit()

    return {
        "engagement_id": engagement.id,
        "filename": filename,
        "status": "uploaded",
        "parsing": {
            "transactions_parsed": len(transactions),
            "duplicates_removed": parse_summary["duplicates_removed"],
            "date_range": parse_summary["date_range"],
            "total_spend_gbp": round(parse_summary["total_spend"], 2),
            "unique_suppliers": parse_summary["unique_suppliers"],
        },
    }
```

- [ ] **Step 2: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All existing tests pass (upload tests may need adjustment if they test the full pipeline — check and fix).

- [ ] **Step 3: Commit**

```bash
git add hemera/api/upload.py
git commit -m "feat: strip upload endpoint to parse-only (no AI token usage)"
```

---

### Task 3: Add admin process endpoint

**Files:**
- Modify: `hemera/api/engagements.py`

- [ ] **Step 1: Add the process endpoint**

Add this endpoint to `hemera/api/engagements.py` (after the existing endpoints, with the other new endpoints):

```python
from hemera.services.pipeline import run_processing_pipeline
from hemera.dependencies import require_admin


@router.post("/engagements/{engagement_id}/process")
def process_engagement(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(require_admin),
):
    """Admin-only: trigger full classification + calculation pipeline."""
    e = _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    if not txns:
        raise HTTPException(status_code=404, detail="No transactions found")
    try:
        result = run_processing_pipeline(e, txns, db)
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    return result
```

Note: `require_admin` is already imported in `hemera/dependencies.py`. Import it at the top of engagements.py alongside `get_current_user`. Also import `run_processing_pipeline` from `hemera.services.pipeline`.

- [ ] **Step 2: Update QC submit to set status to qc_passed**

In `hemera/api/qc.py`, line 132, change:

```python
        eng.status = "delivered"
```

to:

```python
        eng.status = "qc_passed"
```

- [ ] **Step 3: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All pass (may need to fix test_auth.py assertions if they check for `"delivered"` status after QC).

- [ ] **Step 4: Commit**

```bash
git add hemera/api/engagements.py hemera/api/qc.py
git commit -m "feat: add admin process endpoint, update QC to set qc_passed status"
```

---

### Task 4: Pending banner component

**Files:**
- Create: `dashboard/components/ui/pending-banner.tsx`

- [ ] **Step 1: Create the banner component**

Create `dashboard/components/ui/pending-banner.tsx`:

```tsx
import Link from "next/link";

const STATUS_CONFIG: Record<string, { title: string; description: string; color: string }> = {
  uploaded: {
    title: "Your data has been uploaded",
    description: "Our team will review your submission and get back to you shortly.",
    color: "border-amber bg-amber-tint",
  },
  processing: {
    title: "Your data is being processed",
    description: "We're classifying transactions and calculating your carbon footprint. This may take a few minutes.",
    color: "border-teal bg-teal-tint",
  },
  delivered: {
    title: "Awaiting analyst approval",
    description: "Your carbon footprint has been calculated and is pending quality review by our team.",
    color: "border-teal bg-teal-tint",
  },
};

export function PendingBanner({ status }: { status: string }) {
  const config = STATUS_CONFIG[status];
  if (!config) return null;

  return (
    <div className={`rounded-lg border-l-4 p-4 mb-6 ${config.color}`}>
      <h3 className="text-sm font-semibold">{config.title}</h3>
      <p className="text-xs text-muted mt-1">{config.description}</p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/nicohenry/Documents/Hemera/dashboard
git add components/ui/pending-banner.tsx
git commit -m "feat: add PendingBanner component for engagement status"
```

---

### Task 5: Update engagement layout to pass status

**Files:**
- Modify: `dashboard/app/dashboard/[id]/layout.tsx`

- [ ] **Step 1: Update the layout to fetch engagement and pass status via URL**

Replace `dashboard/app/dashboard/[id]/layout.tsx`:

```tsx
export default function EngagementLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
```

No change needed here — each page already fetches its own engagement data. The status check will happen in each page individually.

Actually, skip this task — each page already calls `getEngagement()` and has access to `engagement.status`. The pending banner will be added directly to each page in the next tasks.

- [ ] **Step 2: Commit** (skip — no changes)

---

### Task 6: Update Overview page with empty state

**Files:**
- Modify: `dashboard/app/dashboard/[id]/page.tsx`

- [ ] **Step 1: Update Overview page**

Replace `dashboard/app/dashboard/[id]/page.tsx` with:

```tsx
import { getEngagement, getCategories, getEngagementSuppliers } from "@/lib/api";
import { HeroBanner } from "@/components/ui/hero-banner";
import { ChartCard } from "@/components/ui/chart-card";
import { ScopeDonut } from "@/components/charts/scope-donut";
import { PendingBanner } from "@/components/ui/pending-banner";
import { SCOPE_COLORS } from "@/lib/plotly-theme";
import { fmtTonnes, fmtGBP } from "@/lib/format";
import type { CategorySummary, EngagementSupplier } from "@/lib/types";

export default async function OverviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const engagementId = Number(id);

  let engagement;
  try {
    engagement = await getEngagement(engagementId);
  } catch {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-bold mb-2">No data yet</h2>
        <p className="text-muted text-sm">Upload your accounting data to get started.</p>
      </div>
    );
  }

  if (engagement.status !== "qc_passed") {
    return (
      <div>
        <HeroBanner engagement={engagement} />
        <PendingBanner status={engagement.status} />
        <div className="grid grid-cols-[1.5fr_1fr] gap-4">
          <ChartCard title="Emissions by Scope" className="row-span-2">
            <div className="h-[280px] flex items-center justify-center text-muted text-sm">—</div>
          </ChartCard>
          <ChartCard title="Top 5 Emission Hotspots">
            <div className="h-[120px] flex items-center justify-center text-muted text-sm">—</div>
          </ChartCard>
          <ChartCard title="Supplier Risk Overview">
            <div className="h-[120px] flex items-center justify-center text-muted text-sm">—</div>
          </ChartCard>
        </div>
      </div>
    );
  }

  const [categories, suppliers] = await Promise.all([
    getCategories(engagementId),
    getEngagementSuppliers(engagementId),
  ]);

  const topHotspots = [...categories]
    .sort((a, b) => b.co2e_tonnes - a.co2e_tonnes)
    .slice(0, 5);
  const maxCo2e = topHotspots[0]?.co2e_tonnes ?? 1;

  const riskCounts = suppliers.reduce(
    (acc: { low: number; medium: number; high: number }, s: EngagementSupplier) => {
      if (s.intensity_kg_per_gbp > 2) acc.high++;
      else if (s.intensity_kg_per_gbp > 0.5) acc.medium++;
      else acc.low++;
      return acc;
    },
    { low: 0, medium: 0, high: 0 }
  );
  const riskTotal = riskCounts.low + riskCounts.medium + riskCounts.high || 1;

  return (
    <div className="space-y-5">
      <HeroBanner engagement={engagement} />
      <div className="grid grid-cols-[1.5fr_1fr] gap-4">
        <ChartCard
          title="Emissions by Scope"
          className="row-span-2"
          linkHref={`/dashboard/${id}/carbon`}
          linkText="View carbon breakdown →"
        >
          <ScopeDonut
            scope1={engagement.scope1_co2e}
            scope2={engagement.scope2_co2e}
            scope3={engagement.scope3_co2e}
          />
        </ChartCard>
        <ChartCard
          title="Top 5 Emission Hotspots"
          linkHref={`/dashboard/${id}/carbon`}
          linkText="View all categories →"
        >
          <div className="space-y-2 mt-2">
            {topHotspots.map((cat: CategorySummary) => {
              const pct = (cat.co2e_tonnes / maxCo2e) * 100;
              const color = SCOPE_COLORS[cat.scope] ?? "#64748B";
              return (
                <div key={cat.name}>
                  <div className="flex justify-between text-[12px] mb-0.5">
                    <span className="truncate max-w-[60%] font-medium" title={cat.name}>{cat.name}</span>
                    <span className="tabular-nums text-muted">{fmtTonnes(cat.co2e_tonnes)} tCO₂e</span>
                  </div>
                  <div className="h-2 rounded-full bg-[#F0F0EB] overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>
        <ChartCard
          title="Supplier Risk Overview"
          linkHref={`/dashboard/${id}/suppliers`}
          linkText="View all suppliers →"
        >
          <div className="space-y-2 mt-2">
            {[
              { label: "Low Risk", count: riskCounts.low, color: "#10B981", bg: "#D1FAE5" },
              { label: "Medium Risk", count: riskCounts.medium, color: "#F59E0B", bg: "#FEF3C7" },
              { label: "High Risk", count: riskCounts.high, color: "#EF4444", bg: "#FEE2E2" },
            ].map(({ label, count, color, bg }) => {
              const pct = (count / riskTotal) * 100;
              return (
                <div key={label}>
                  <div className="flex justify-between text-[12px] mb-0.5">
                    <span className="font-medium">{label}</span>
                    <span className="tabular-nums text-muted">{count} suppliers</span>
                  </div>
                  <div className="h-2 rounded-full bg-[#F0F0EB] overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color, background: bg }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 pt-2 border-t border-[#F0F0EB]">
            <div className="text-[11px] text-muted">
              Total spend tracked: {fmtGBP(suppliers.reduce((s: number, sup: EngagementSupplier) => s + sup.spend_gbp, 0))}
            </div>
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/app/dashboard/[id]/page.tsx
git commit -m "feat: Overview page shows empty state when not qc_passed"
```

---

### Task 7: Update remaining pages with empty states

**Files:**
- Modify: `dashboard/app/dashboard/[id]/carbon/page.tsx`
- Modify: `dashboard/app/dashboard/[id]/suppliers/page.tsx`
- Modify: `dashboard/app/dashboard/[id]/quality/page.tsx`
- Modify: `dashboard/app/dashboard/[id]/reduction/page.tsx`

Each page needs the same pattern: fetch engagement, check status, show pending banner + empty chart outlines if not `qc_passed`.

- [ ] **Step 1: Update Carbon page**

At the top of `dashboard/app/dashboard/[id]/carbon/page.tsx`, after the existing imports, add:

```tsx
import { PendingBanner } from "@/components/ui/pending-banner";
```

Then wrap the page body. After `const engagementId = Number(id);` and before the `Promise.all` call, add the status check:

```tsx
  let engagement;
  try {
    engagement = await getEngagement(engagementId);
  } catch {
    return <div className="text-center py-20"><h2 className="text-xl font-bold mb-2">No data yet</h2><p className="text-muted text-sm">Upload your accounting data to get started.</p></div>;
  }

  if (engagement.status !== "qc_passed") {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-1">Carbon Footprint</h1>
        <p className="text-sm text-muted mb-6">{engagement.org_name} — detailed breakdown</p>
        <PendingBanner status={engagement.status} />
        <div className="grid grid-cols-2 gap-4 mb-6">
          <ChartCard title="Top 10 Categories by tCO₂e"><div className="h-[300px] flex items-center justify-center text-muted text-sm">—</div></ChartCard>
          <ChartCard title="Spend vs Emissions"><div className="h-[300px] flex items-center justify-center text-muted text-sm">—</div></ChartCard>
        </div>
        <ChartCard title="Monthly Emission Pattern"><div className="h-[200px] flex items-center justify-center text-muted text-sm">—</div></ChartCard>
      </div>
    );
  }
```

Remove the separate `getEngagement` call from the `Promise.all` below (since we already fetched it), and use the `engagement` variable we already have.

- [ ] **Step 2: Update Suppliers page**

Same pattern for `dashboard/app/dashboard/[id]/suppliers/page.tsx`. Add `PendingBanner` import and status check:

```tsx
import { getEngagement } from "@/lib/api";
import { PendingBanner } from "@/components/ui/pending-banner";
```

After getting the `id`, fetch engagement and check status:

```tsx
  let engagement;
  try {
    engagement = await getEngagement(Number(id));
  } catch {
    return <div className="text-center py-20"><h2 className="text-xl font-bold mb-2">No data yet</h2><p className="text-muted text-sm">Upload your accounting data to get started.</p></div>;
  }

  if (engagement.status !== "qc_passed") {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-1">Suppliers</h1>
        <PendingBanner status={engagement.status} />
        <ChartCard title="Supplier Summary"><div className="h-[200px] flex items-center justify-center text-muted text-sm">—</div></ChartCard>
      </div>
    );
  }
```

- [ ] **Step 3: Update Data Quality page**

Same pattern for `dashboard/app/dashboard/[id]/quality/page.tsx`. Add imports and status check before the data quality API call:

```tsx
import { PendingBanner } from "@/components/ui/pending-banner";
```

```tsx
  if (engagement.status !== "qc_passed") {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-1">Data Quality</h1>
        <PendingBanner status={engagement.status} />
        <div className="grid grid-cols-2 gap-4 mb-6">
          <ChartCard title="Pedigree Indicators"><div className="h-[300px] flex items-center justify-center text-muted text-sm">—</div></ChartCard>
          <ChartCard title="Cascade Distribution"><div className="h-[300px] flex items-center justify-center text-muted text-sm">—</div></ChartCard>
        </div>
      </div>
    );
  }
```

- [ ] **Step 4: Update Reduction page**

Same pattern for `dashboard/app/dashboard/[id]/reduction/page.tsx`:

```tsx
import { getEngagement } from "@/lib/api";
import { PendingBanner } from "@/components/ui/pending-banner";
```

```tsx
  let engagement;
  try {
    engagement = await getEngagement(Number(id));
  } catch {
    return <div className="text-center py-20"><h2 className="text-xl font-bold mb-2">No data yet</h2><p className="text-muted text-sm">Upload your accounting data to get started.</p></div>;
  }

  if (engagement.status !== "qc_passed") {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-1">Reduction Roadmap</h1>
        <PendingBanner status={engagement.status} />
        <div className="grid grid-cols-2 gap-4 mb-6">
          <ChartCard title="Impact vs Effort"><div className="h-[350px] flex items-center justify-center text-muted text-sm">—</div></ChartCard>
          <ChartCard title="Reduction Waterfall"><div className="h-[350px] flex items-center justify-center text-muted text-sm">—</div></ChartCard>
        </div>
      </div>
    );
  }
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/dashboard/[id]/carbon/page.tsx dashboard/app/dashboard/[id]/suppliers/page.tsx dashboard/app/dashboard/[id]/quality/page.tsx dashboard/app/dashboard/[id]/reduction/page.tsx
git commit -m "feat: add empty states with pending banner to all dashboard pages"
```

---

### Task 8: Update Upload page with engagement list

**Files:**
- Modify: `dashboard/app/dashboard/upload/page.tsx`
- Modify: `dashboard/components/upload/dropzone.tsx`

- [ ] **Step 1: Update Upload page to show engagement list**

Replace `dashboard/app/dashboard/upload/page.tsx`:

```tsx
import { UploadDropzone } from "@/components/upload/dropzone";
import { listEngagements } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

const STATUS_BADGES: Record<string, { label: string; variant: "amber" | "teal" | "green" }> = {
  uploaded: { label: "Awaiting review", variant: "amber" },
  processing: { label: "Processing", variant: "amber" },
  delivered: { label: "Ready for QC", variant: "teal" },
  qc_passed: { label: "Approved", variant: "green" },
};

export default async function UploadPage() {
  let engagements: Awaited<ReturnType<typeof listEngagements>> = [];
  try {
    engagements = await listEngagements();
  } catch {
    // Not authenticated or API down — show upload only
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Upload Spend Data</h1>
        <p className="text-muted text-sm mt-0.5">
          Upload a CSV or Excel file to create a new engagement. Our team will
          review your data and calculate your carbon footprint.
        </p>
      </div>

      <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6">
        <UploadDropzone />
      </div>

      {engagements.length > 0 && (
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-4">
          <h4 className="text-xs font-semibold uppercase tracking-[0.5px] mb-3">
            Your Uploads
          </h4>
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr>
                {["Engagement", "Transactions", "Status", ""].map((col) => (
                  <th
                    key={col}
                    className="text-left px-3 py-2 bg-paper text-[11px] font-semibold uppercase tracking-[0.5px] text-muted border-b-2 border-[#E5E5E0]"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {engagements.map((e) => {
                const badge = STATUS_BADGES[e.status] || { label: e.status, variant: "amber" as const };
                return (
                  <tr key={e.id} className="hover:bg-[#FAFAF7]">
                    <td className="px-3 py-2.5 border-b border-[#F0F0EB]">
                      {e.org_name || "Upload"} #{e.id}
                    </td>
                    <td className="px-3 py-2.5 border-b border-[#F0F0EB] tabular-nums">
                      {e.transaction_count || "—"}
                    </td>
                    <td className="px-3 py-2.5 border-b border-[#F0F0EB]">
                      <Badge variant={badge.variant}>{badge.label}</Badge>
                    </td>
                    <td className="px-3 py-2.5 border-b border-[#F0F0EB] text-right">
                      {e.status === "qc_passed" && (
                        <Link href={`/dashboard/${e.id}`} className="text-teal text-xs font-semibold">
                          View →
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-paper rounded-lg border border-[#E5E5E0] p-4">
        <h4 className="text-xs font-semibold uppercase tracking-[0.5px] mb-3">
          Expected Format
        </h4>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              {["date", "supplier", "description", "amount"].map((col) => (
                <th key={col} className="text-left px-2 py-1.5 bg-[#F0F0EB] font-mono font-semibold border border-[#E5E5E0]">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {["2024-01-15", "Heathrow Express", "Rail travel LHR", "42.50"].map((v, i) => (
                <td key={i} className="px-2 py-1.5 border border-[#E5E5E0] text-muted font-mono">{v}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Update dropzone to not redirect after upload**

In `dashboard/components/upload/dropzone.tsx`, the "done" state currently redirects to `/dashboard/{id}`. Change it to show a success message and refresh the page instead (so the engagement list updates):

Find the success/done state in the dropzone and replace the "View Results" button action. Instead of `router.push(\`/dashboard/${result.engagement_id}\`)`, use `router.refresh()` to reload the page and show the new engagement in the list.

The success state should say: "Upload complete! Our team will review your data." with a "Upload Another" button that resets the state.

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/dashboard/upload/page.tsx dashboard/components/upload/dropzone.tsx
git commit -m "feat: upload page shows engagement list with status badges"
```

---

### Task 9: Update QC page with processing trigger

**Files:**
- Modify: `dashboard/app/dashboard/[id]/qc/page.tsx`

- [ ] **Step 1: Add processing trigger for uploaded engagements**

In the QC page, before the existing QC flow, add a check: if the engagement status is `uploaded`, show a "Start Processing" button that calls `POST /api/engagements/{id}/process`. After processing completes, the page refreshes and shows the normal QC flow.

Add a new state `processingStatus` to track: "idle" | "running" | "done".

At the top of the component, add an API call to check the engagement status:

```tsx
const [engagementStatus, setEngagementStatus] = useState<string>("loading");

useEffect(() => {
  const fetchStatus = async () => {
    const token = await getToken();
    const res = await fetch(`${API_URL}/api/engagements/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const data = await res.json();
      setEngagementStatus(data.status);
    }
  };
  fetchStatus();
}, [id, getToken]);
```

Then render based on status:
- `uploaded`: Show "Start Processing" button
- `processing`: Show "Processing..." spinner
- `delivered`: Show existing QC flow (generate sample, review, submit)
- `qc_passed`: Show "QC Complete" message

The "Start Processing" button calls:
```tsx
const triggerProcessing = async () => {
  setEngagementStatus("processing");
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/engagements/${id}/process`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.ok) {
    setEngagementStatus("delivered");
  } else {
    const text = await res.text();
    setEngagementStatus("uploaded");
    alert(`Processing failed: ${text}`);
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/app/dashboard/[id]/qc/page.tsx
git commit -m "feat: QC page shows processing trigger for uploaded engagements"
```

---

### Task 10: Build verification and push

- [ ] **Step 1: Run backend tests**

```bash
cd /Users/nicohenry/Documents/Hemera && .venv/bin/python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Run frontend build**

```bash
cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Fix any issues**

If tests or build fail, fix the issues.

- [ ] **Step 4: Push**

```bash
git push origin main
```
