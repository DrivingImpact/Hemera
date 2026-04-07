# Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js dashboard that consumes the Hemera API, giving clients an interactive view of their carbon footprint, suppliers, data quality, and reduction roadmap.

**Architecture:** Two phases — (1) add 5 new API endpoints to the FastAPI backend extracting aggregation logic from pdf_report.py, (2) scaffold and build the Next.js dashboard in `dashboard/`. The frontend uses Clerk auth, Plotly.js charts, and Tailwind CSS with the Hemera brand theme.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, @clerk/nextjs, react-plotly.js, Vercel deployment. Backend additions in Python/FastAPI.

**Spec:** `docs/superpowers/specs/2026-04-07-dashboard-design.md`

---

## Phase 1: Backend API Endpoints

### Task 1: Categories endpoint

**Files:**
- Modify: `hemera/api/engagements.py`
- Test: `tests/test_engagements_api.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_engagements_api.py`:

```python
"""Tests for engagement detail endpoints."""

from unittest.mock import MagicMock
import pytest
from hemera.services.engagement_data import build_category_summary


def _make_txn(**kwargs):
    t = MagicMock()
    t.co2e_kg = kwargs.get("co2e_kg", 100)
    t.amount_gbp = kwargs.get("amount_gbp", 1000)
    t.scope = kwargs.get("scope", 3)
    t.category_name = kwargs.get("category_name", "General")
    t.gsd_total = kwargs.get("gsd_total", 1.5)
    t.is_duplicate = kwargs.get("is_duplicate", False)
    return t


class TestBuildCategorySummary:
    def test_groups_by_category(self):
        txns = [
            _make_txn(category_name="Electricity", co2e_kg=5000, scope=2, amount_gbp=2000),
            _make_txn(category_name="Electricity", co2e_kg=3000, scope=2, amount_gbp=1000),
            _make_txn(category_name="Travel", co2e_kg=2000, scope=3, amount_gbp=500),
        ]
        result = build_category_summary(txns)
        assert len(result) == 2
        elec = next(c for c in result if c["name"] == "Electricity")
        assert elec["co2e_tonnes"] == 8.0
        assert elec["spend_gbp"] == 3000
        assert elec["scope"] == 2

    def test_sorted_descending_by_co2e(self):
        txns = [
            _make_txn(category_name="Small", co2e_kg=100),
            _make_txn(category_name="Big", co2e_kg=9000),
        ]
        result = build_category_summary(txns)
        assert result[0]["name"] == "Big"

    def test_skips_duplicates(self):
        txns = [
            _make_txn(category_name="A", co2e_kg=500, is_duplicate=True),
            _make_txn(category_name="A", co2e_kg=500, is_duplicate=False),
        ]
        result = build_category_summary(txns)
        assert result[0]["co2e_tonnes"] == 0.5

    def test_returns_gsd_average(self):
        txns = [
            _make_txn(category_name="A", co2e_kg=100, gsd_total=1.2),
            _make_txn(category_name="A", co2e_kg=100, gsd_total=1.8),
        ]
        result = build_category_summary(txns)
        assert result[0]["gsd"] == pytest.approx(1.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_engagements_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'hemera.services.engagement_data'`

- [ ] **Step 3: Create the service function**

Create `hemera/services/engagement_data.py`:

```python
"""Engagement data aggregation.

Extracts the category/monthly/supplier aggregation logic from pdf_report.py
into reusable functions for both the PDF report and the dashboard API.
"""

from collections import defaultdict


def build_category_summary(transactions: list) -> list[dict]:
    """Group transactions by category, return sorted list of category dicts."""
    groups = defaultdict(lambda: {"co2e_kg": 0, "spend_gbp": 0, "gsd_values": [], "scope": 3})
    for t in transactions:
        if t.co2e_kg and not t.is_duplicate:
            key = t.category_name or "Unclassified"
            groups[key]["co2e_kg"] += t.co2e_kg
            groups[key]["spend_gbp"] += abs(t.amount_gbp or 0)
            if t.gsd_total:
                groups[key]["gsd_values"].append(t.gsd_total)
            groups[key]["scope"] = t.scope or 3

    categories = []
    for name, data in groups.items():
        gsd_vals = data["gsd_values"]
        categories.append({
            "name": name,
            "scope": data["scope"],
            "co2e_tonnes": data["co2e_kg"] / 1000,
            "spend_gbp": data["spend_gbp"],
            "gsd": sum(gsd_vals) / len(gsd_vals) if gsd_vals else 1.5,
        })
    categories.sort(key=lambda c: c["co2e_tonnes"], reverse=True)
    return categories


def build_monthly_summary(transactions: list) -> dict:
    """Group transactions by month and scope. Returns {has_data, months}."""
    dated_count = sum(1 for t in transactions if t.transaction_date)
    has_data = dated_count > len(transactions) * 0.5
    if not has_data:
        return {"has_data": False, "months": []}

    groups = defaultdict(lambda: {"scope1": 0, "scope2": 0, "scope3": 0})
    for t in transactions:
        if t.transaction_date and t.co2e_kg and not t.is_duplicate:
            month_key = (
                t.transaction_date.strftime("%Y-%m")
                if hasattr(t.transaction_date, "strftime")
                else str(t.transaction_date)[:7]
            )
            scope_key = f"scope{t.scope or 3}"
            groups[month_key][scope_key] += t.co2e_kg / 1000

    months = [{"month": k, **v} for k, v in sorted(groups.items())]
    return {"has_data": True, "months": months}


def build_engagement_suppliers(transactions: list) -> list[dict]:
    """Group transactions by supplier for this engagement."""
    groups = defaultdict(lambda: {
        "supplier_id": None, "name": "Unknown", "co2e_kg": 0,
        "spend_gbp": 0, "transaction_count": 0,
    })
    for t in transactions:
        if t.is_duplicate:
            continue
        key = t.supplier_id or t.raw_supplier or "Unknown"
        groups[key]["supplier_id"] = t.supplier_id
        groups[key]["name"] = t.raw_supplier or "Unknown"
        groups[key]["co2e_kg"] += t.co2e_kg or 0
        groups[key]["spend_gbp"] += abs(t.amount_gbp or 0)
        groups[key]["transaction_count"] += 1

    suppliers = []
    for data in groups.values():
        spend = data["spend_gbp"]
        co2e = data["co2e_kg"]
        suppliers.append({
            "supplier_id": data["supplier_id"],
            "name": data["name"],
            "co2e_tonnes": co2e / 1000,
            "spend_gbp": spend,
            "intensity_kg_per_gbp": co2e / spend if spend > 0 else 0,
            "transaction_count": data["transaction_count"],
        })
    suppliers.sort(key=lambda s: s["co2e_tonnes"], reverse=True)
    return suppliers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_engagements_api.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add hemera/services/engagement_data.py tests/test_engagements_api.py
git commit -m "feat: add engagement data aggregation service (categories, monthly, suppliers)"
```

### Task 2: Wire up the 5 new API endpoints

**Files:**
- Modify: `hemera/api/engagements.py`
- Modify: `hemera/main.py` (no change needed — engagements router already mounted)

- [ ] **Step 1: Add all 5 endpoints to engagements.py**

Append to `hemera/api/engagements.py`:

```python
from hemera.models.transaction import Transaction
from hemera.services.engagement_data import (
    build_category_summary, build_monthly_summary, build_engagement_suppliers,
)
from hemera.services.reduction_recs import generate_reduction_recommendations, compute_projections
from hemera.services.data_quality import compute_summary, generate_recommendations


def _load_engagement(engagement_id: int, db, current_user):
    """Load engagement with auth check. Raises HTTPException on failure."""
    e = db.query(Engagement).filter(Engagement.id == engagement_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role != "admin" and e.org_name != current_user.org_name:
        raise HTTPException(status_code=403, detail="Access denied")
    return e


def _load_transactions(engagement_id: int, db):
    return db.query(Transaction).filter(Transaction.engagement_id == engagement_id).all()


@router.get("/engagements/{engagement_id}/categories")
def get_engagement_categories(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    return build_category_summary(txns)


@router.get("/engagements/{engagement_id}/monthly")
def get_engagement_monthly(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    return build_monthly_summary(txns)


@router.get("/engagements/{engagement_id}/suppliers")
def get_engagement_suppliers(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    return build_engagement_suppliers(txns)


@router.get("/engagements/{engagement_id}/reduction")
def get_engagement_reduction(
    engagement_id: int,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    e = _load_engagement(engagement_id, db, current_user)
    txns = _load_transactions(engagement_id, db)
    recs = generate_reduction_recommendations(txns)
    dq_recs = generate_recommendations(txns)

    total_co2e = e.total_co2e or 0
    ci_lower = e.ci_lower or total_co2e * 0.7
    ci_upper = e.ci_upper or total_co2e * 1.4

    projections = compute_projections(
        total_co2e_kg=total_co2e * 1000,
        ci_lower_kg=ci_lower * 1000,
        ci_upper_kg=ci_upper * 1000,
        reduction_recs=recs,
        data_quality_recs=dq_recs,
    )

    return {
        "recommendations": recs,
        "projections": {
            "baseline": total_co2e,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "year2_ci_lower": projections["year2_ci_lower_kg"] / 1000,
            "year2_ci_upper": projections["year2_ci_upper_kg"] / 1000,
            "year3_target": projections["year3_target_kg"] / 1000,
            "year3_ci_lower": projections["year3_ci_lower_kg"] / 1000,
            "year3_ci_upper": projections["year3_ci_upper_kg"] / 1000,
            "total_reduction": projections["total_reduction_kg"] / 1000,
        },
    }


@router.get("/engagements/{engagement_id}/transactions")
def get_engagement_transactions(
    engagement_id: int,
    scope: int | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    _load_engagement(engagement_id, db, current_user)
    query = db.query(Transaction).filter(
        Transaction.engagement_id == engagement_id,
        Transaction.is_duplicate == False,
    )
    if scope:
        query = query.filter(Transaction.scope == scope)
    if category:
        query = query.filter(Transaction.category_name == category)

    total = query.count()
    txns = query.order_by(Transaction.co2e_kg.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "transactions": [
            {
                "id": t.id,
                "date": str(t.transaction_date) if t.transaction_date else None,
                "description": t.raw_description,
                "supplier": t.raw_supplier,
                "amount_gbp": t.amount_gbp,
                "scope": t.scope,
                "category": t.category_name,
                "ef_source": t.ef_source,
                "ef_level": t.ef_level,
                "co2e_kg": t.co2e_kg,
                "gsd": t.gsd_total,
            }
            for t in txns
        ],
    }
```

- [ ] **Step 2: Add missing imports to the top of engagements.py**

Add these imports at the top of the file (after existing imports):

```python
from hemera.models.transaction import Transaction
from hemera.services.engagement_data import (
    build_category_summary, build_monthly_summary, build_engagement_suppliers,
)
from hemera.services.reduction_recs import generate_reduction_recommendations, compute_projections
from hemera.services.data_quality import generate_recommendations
from hemera.dependencies import get_current_user
from hemera.services.clerk import ClerkUser
```

Note: `get_current_user` and `ClerkUser` are likely already imported — check and don't duplicate.

- [ ] **Step 3: Run existing tests to make sure nothing broke**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: 136+ PASS, 0 FAIL

- [ ] **Step 4: Commit**

```bash
git add hemera/api/engagements.py
git commit -m "feat: add 5 dashboard API endpoints (categories, monthly, suppliers, reduction, transactions)"
```

### Task 3: Refactor pdf_report.py to use shared service

**Files:**
- Modify: `hemera/services/pdf_report.py`

- [ ] **Step 1: Replace inline category/monthly logic with shared functions**

In `hemera/services/pdf_report.py`, replace the category grouping block (lines 59-79) and monthly block (lines 82-92) with calls to the shared service:

Replace:
```python
    # Build category summaries
    cat_groups = defaultdict(lambda: {"co2e_kg": 0, "spend_gbp": 0, "gsd_values": [], "scope": 3})
    ...
    categories.sort(key=lambda c: c["co2e_tonnes"], reverse=True)

    # Monthly data
    monthly_groups = defaultdict(lambda: {"scope1": 0, "scope2": 0, "scope3": 0})
    ...
    monthly_data = [{"month": k, **v} for k, v in sorted(monthly_groups.items())]
```

With:
```python
    from hemera.services.engagement_data import build_category_summary, build_monthly_summary
    categories = build_category_summary(transactions)
    monthly_result = build_monthly_summary(transactions)
    has_monthly = monthly_result["has_data"]
    monthly_data = monthly_result["months"]
```

Remove the now-unused `defaultdict` import if it's only used for these blocks.

- [ ] **Step 2: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All 136+ tests pass (PDF report tests should still work identically)

- [ ] **Step 3: Commit**

```bash
git add hemera/services/pdf_report.py
git commit -m "refactor: use shared engagement_data service in pdf_report"
```

---

## Phase 2: Next.js Dashboard

### Task 4: Scaffold the Next.js project

**Files:**
- Create: `dashboard/` directory with Next.js project

- [ ] **Step 1: Create the Next.js project**

```bash
cd /Users/nicohenry/Documents/Hemera
npx create-next-app@latest dashboard --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --no-turbopack
```

Accept defaults. This creates `dashboard/` with App Router, TypeScript, Tailwind.

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/nicohenry/Documents/Hemera/dashboard
npm install @clerk/nextjs react-plotly.js plotly.js
npm install -D @types/react-plotly.js
```

- [ ] **Step 3: Set up environment variables**

Create `dashboard/.env.local`:

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_REPLACE_ME
CLERK_SECRET_KEY=sk_test_REPLACE_ME
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
```

Create `dashboard/.env.example` (same but with placeholder values for git).

- [ ] **Step 4: Add dashboard/.env.local to .gitignore**

Append to the repo root `.gitignore`:

```
# Dashboard
dashboard/.env.local
dashboard/node_modules/
dashboard/.next/
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/ .gitignore
git commit -m "feat: scaffold Next.js dashboard project"
```

### Task 5: Tailwind brand theme + global styles

**Files:**
- Modify: `dashboard/tailwind.config.ts`
- Modify: `dashboard/app/globals.css`
- Modify: `dashboard/app/layout.tsx`

- [ ] **Step 1: Configure Tailwind theme**

Replace `dashboard/tailwind.config.ts`:

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: "#1E293B",
        teal: "#0D9488",
        amber: "#F59E0B",
        paper: "#F5F5F0",
        surface: "#FFFFFF",
        muted: "#64748B",
        success: "#10B981",
        error: "#EF4444",
        "teal-tint": "#CCFBF1",
        "amber-tint": "#FEF3C7",
        "red-tint": "#FEE2E2",
        "slate-tint": "#F1F5F9",
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 2: Set up globals.css**

Replace `dashboard/app/globals.css`:

```css
@import "tailwindcss";
@import url("https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap");
```

- [ ] **Step 3: Set up root layout with Clerk**

Replace `dashboard/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hemera",
  description: "Supply Chain & Carbon Intelligence",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="bg-paper text-slate font-sans antialiased">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
```

- [ ] **Step 4: Verify it builds**

```bash
cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build
```

Expected: Build succeeds (may warn about Clerk keys — that's fine for now).

- [ ] **Step 5: Commit**

```bash
git add dashboard/tailwind.config.ts dashboard/app/globals.css dashboard/app/layout.tsx
git commit -m "feat: configure Hemera brand theme and Clerk auth"
```

### Task 6: API client + types

**Files:**
- Create: `dashboard/lib/api.ts`
- Create: `dashboard/lib/types.ts`
- Create: `dashboard/lib/plotly-theme.ts`
- Create: `dashboard/lib/format.ts`

- [ ] **Step 1: Create API types**

Create `dashboard/lib/types.ts`:

```ts
export interface Engagement {
  id: number;
  org_name: string;
  status: string;
  transaction_count: number;
  supplier_count: number;
  total_co2e: number;
  scope1_co2e: number;
  scope2_co2e: number;
  scope3_co2e: number;
  gsd_total: number;
  ci_lower: number;
  ci_upper: number;
  created_at: string;
}

export interface EngagementListItem {
  id: number;
  org_name: string;
  status: string;
  transaction_count: number;
  total_co2e: number;
  created_at: string;
}

export interface CategorySummary {
  name: string;
  scope: number;
  co2e_tonnes: number;
  spend_gbp: number;
  gsd: number;
}

export interface MonthlyData {
  has_data: boolean;
  months: { month: string; scope1: number; scope2: number; scope3: number }[];
}

export interface EngagementSupplier {
  supplier_id: number | null;
  name: string;
  co2e_tonnes: number;
  spend_gbp: number;
  intensity_kg_per_gbp: number;
  transaction_count: number;
}

export interface ReductionRec {
  type: string;
  category: string;
  action: string;
  current_co2e_kg: number;
  potential_reduction_pct: number;
  potential_reduction_kg: number;
  effort: string;
  timeline: string;
  explanation: string;
}

export interface Projections {
  baseline: number;
  ci_lower: number;
  ci_upper: number;
  year2_ci_lower: number;
  year2_ci_upper: number;
  year3_target: number;
  year3_ci_lower: number;
  year3_ci_upper: number;
  total_reduction: number;
}

export interface ReductionData {
  recommendations: ReductionRec[];
  projections: Projections;
}

export interface TransactionItem {
  id: number;
  date: string | null;
  description: string;
  supplier: string;
  amount_gbp: number;
  scope: number;
  category: string;
  ef_source: string;
  ef_level: number;
  co2e_kg: number;
  gsd: number;
}

export interface TransactionPage {
  total: number;
  offset: number;
  limit: number;
  transactions: TransactionItem[];
}

export interface SupplierListItem {
  id: number;
  ch_number: string;
  name: string;
  sector: string;
  esg_score: number;
  confidence: string;
  critical_flag: boolean;
}

export interface SupplierDetail {
  id: number;
  ch_number: string;
  hemera_id: string;
  name: string;
  legal_name: string;
  status: string;
  sic_codes: string[];
  sector: string;
  entity_type: string;
  registered_address: string;
  esg_score: number;
  confidence: string;
  critical_flag: boolean;
  created_at: string;
  updated_at: string;
  score_history: {
    total_score: number;
    confidence: string;
    critical_flag: boolean;
    layers_completed: number;
    domains: Record<string, number>;
    scored_at: string;
  }[];
  sources: {
    layer: number;
    source_name: string;
    tier: number;
    summary: string;
    is_verified: boolean;
    fetched_at: string;
  }[];
}
```

- [ ] **Step 2: Create API client**

Create `dashboard/lib/api.ts`:

```ts
import { auth } from "@clerk/nextjs/server";
import type {
  Engagement,
  EngagementListItem,
  CategorySummary,
  MonthlyData,
  EngagementSupplier,
  ReductionData,
  TransactionPage,
  SupplierListItem,
  SupplierDetail,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${API_URL}/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }

  return res.json();
}

export async function listEngagements() {
  return apiFetch<EngagementListItem[]>("/engagements");
}

export async function getEngagement(id: number) {
  return apiFetch<Engagement>(`/engagements/${id}`);
}

export async function getCategories(id: number) {
  return apiFetch<CategorySummary[]>(`/engagements/${id}/categories`);
}

export async function getMonthly(id: number) {
  return apiFetch<MonthlyData>(`/engagements/${id}/monthly`);
}

export async function getEngagementSuppliers(id: number) {
  return apiFetch<EngagementSupplier[]>(`/engagements/${id}/suppliers`);
}

export async function getReduction(id: number) {
  return apiFetch<ReductionData>(`/engagements/${id}/reduction`);
}

export async function getTransactions(
  id: number,
  params?: { scope?: number; category?: string; limit?: number; offset?: number }
) {
  const searchParams = new URLSearchParams();
  if (params?.scope) searchParams.set("scope", String(params.scope));
  if (params?.category) searchParams.set("category", params.category);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch<TransactionPage>(`/engagements/${id}/transactions${qs ? `?${qs}` : ""}`);
}

export async function getSuppliers(q?: string, limit = 50) {
  const searchParams = new URLSearchParams();
  if (q) searchParams.set("q", q);
  searchParams.set("limit", String(limit));
  return apiFetch<SupplierListItem[]>(`/suppliers?${searchParams}`);
}

export async function getSupplier(id: number) {
  return apiFetch<SupplierDetail>(`/suppliers/${id}`);
}

export async function getDataQuality(engagementId: number) {
  return apiFetch<Record<string, unknown>>(`/reports/${engagementId}/data-quality`);
}

export function getPdfUrl(engagementId: number) {
  return `${API_URL}/api/reports/${engagementId}/pdf`;
}
```

- [ ] **Step 3: Create Plotly theme**

Create `dashboard/lib/plotly-theme.ts`:

```ts
export const HEMERA_THEME = {
  font: { family: "Plus Jakarta Sans, system-ui, sans-serif", color: "#1E293B" },
  paper_bgcolor: "#FFFFFF",
  plot_bgcolor: "#FFFFFF",
  colorway: ["#1E293B", "#0D9488", "#F59E0B", "#10B981", "#EF4444", "#64748B"],
  margin: { l: 60, r: 20, t: 40, b: 40 },
};

export const SCOPE_COLORS: Record<number, string> = {
  1: "#1E293B",
  2: "#0D9488",
  3: "#F59E0B",
};

export const SCOPE_LABELS: Record<number, string> = {
  1: "Scope 1",
  2: "Scope 2",
  3: "Scope 3",
};
```

- [ ] **Step 4: Create formatters**

Create `dashboard/lib/format.ts`:

```ts
export function fmtTonnes(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return value.toFixed(1);
}

export function fmtGBP(value: number): string {
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 }).format(value);
}

export function fmtPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function fmtNumber(value: number): string {
  return new Intl.NumberFormat("en-GB").format(Math.round(value));
}
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/
git commit -m "feat: add API client, types, Plotly theme, and formatters"
```

### Task 7: Dashboard layout (sidebar + topbar)

**Files:**
- Create: `dashboard/components/layout/sidebar.tsx`
- Create: `dashboard/components/layout/topbar.tsx`
- Create: `dashboard/app/dashboard/layout.tsx`
- Create: `dashboard/app/dashboard/page.tsx`
- Create: `dashboard/middleware.ts`

- [ ] **Step 1: Create Clerk middleware**

Create `dashboard/middleware.ts`:

```ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isProtectedRoute = createRouteMatcher(["/dashboard(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: ["/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)"],
};
```

- [ ] **Step 2: Create sidebar**

Create `dashboard/components/layout/sidebar.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_SECTIONS = [
  {
    label: "Analysis",
    items: [
      { name: "Overview", href: "", icon: "◉" },
      { name: "Carbon", href: "/carbon", icon: "◯" },
      { name: "Suppliers", href: "/suppliers", icon: "◯" },
      { name: "Data Quality", href: "/quality", icon: "◯" },
    ],
  },
  {
    label: "Actions",
    items: [
      { name: "Reduction", href: "/reduction", icon: "◯" },
      { name: "Upload", href: "/upload", icon: "◯", absolute: true },
    ],
  },
];

export function Sidebar({ engagementId, orgName }: { engagementId?: number; orgName: string }) {
  const pathname = usePathname();
  const basePath = engagementId ? `/dashboard/${engagementId}` : "/dashboard";

  return (
    <aside className="w-[220px] bg-slate flex flex-col flex-shrink-0 min-h-screen">
      <div className="px-5 pt-5 pb-4 border-b border-white/10">
        <div className="text-teal text-[11px] font-bold uppercase tracking-[2px]">Hemera</div>
        <div className="text-[#94A3B8] text-xs mt-1">{orgName}</div>
      </div>
      <nav className="mt-3 flex-1">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <div className="px-5 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-[1px] text-[#475569]">
              {section.label}
            </div>
            {section.items.map((item) => {
              const href = item.absolute ? `/dashboard${item.href}` : `${basePath}${item.href}`;
              const isActive = item.href === ""
                ? pathname === basePath
                : pathname.startsWith(href);

              return (
                <Link
                  key={item.name}
                  href={href}
                  className={`flex items-center gap-2.5 px-5 py-2 text-[13px] transition-colors ${
                    isActive
                      ? "text-white bg-teal/12 border-r-2 border-teal"
                      : "text-[#94A3B8] hover:text-white"
                  }`}
                >
                  <span className="w-4 text-center text-xs">{isActive ? "●" : item.icon}</span>
                  {item.name}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 3: Create topbar**

Create `dashboard/components/layout/topbar.tsx`:

```tsx
"use client";

import { UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import type { EngagementListItem } from "@/lib/types";
import { getPdfUrl } from "@/lib/api";

export function Topbar({
  engagements,
  currentId,
}: {
  engagements: EngagementListItem[];
  currentId?: number;
}) {
  const router = useRouter();

  return (
    <div className="bg-surface px-6 py-3 border-b border-[#E5E5E0] flex items-center justify-between">
      <div className="flex items-center gap-2 text-[13px] text-muted">
        <span>Engagement:</span>
        <select
          className="border border-[#E5E5E0] rounded px-2 py-1 text-xs font-sans bg-[#FAFAF7]"
          value={currentId || ""}
          onChange={(e) => {
            const id = e.target.value;
            if (id) router.push(`/dashboard/${id}`);
          }}
        >
          {engagements.map((e) => (
            <option key={e.id} value={e.id}>
              {e.org_name} — {e.status}
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-3">
        {currentId && (
          <a
            href={getPdfUrl(currentId)}
            className="px-3 py-1.5 rounded-md text-xs font-semibold text-muted border border-[#E5E5E0] hover:bg-slate-tint"
          >
            ↓ PDF Report
          </a>
        )}
        <UserButton afterSignOutUrl="/" />
      </div>
    </div>
  );
}
```

Note: `getPdfUrl` needs to be exported from a client-accessible module. Since `lib/api.ts` uses server-only `auth()`, create a small client helper or just inline the URL. Simplest fix — `getPdfUrl` doesn't need auth import, so it can be imported directly. But the `apiFetch` function uses server-only imports. Split: move `getPdfUrl` to a separate file or make it a plain function. Since it's just a string concatenation, keep it in `lib/api.ts` but note that the topbar should reference `NEXT_PUBLIC_API_URL` directly:

Replace the import in topbar.tsx with:

```tsx
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

And use `${API_URL}/api/reports/${currentId}/pdf` directly in the `href`.

- [ ] **Step 4: Create dashboard layout**

Create `dashboard/app/dashboard/layout.tsx`:

```tsx
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { listEngagements } from "@/lib/api";

export default async function DashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id?: string }>;
}) {
  const engagements = await listEngagements();
  const resolvedParams = await params;
  const currentId = resolvedParams.id ? Number(resolvedParams.id) : engagements[0]?.id;
  const orgName = engagements[0]?.org_name || "Hemera";

  return (
    <div className="flex min-h-screen">
      <Sidebar engagementId={currentId} orgName={orgName} />
      <div className="flex-1 flex flex-col">
        <Topbar engagements={engagements} currentId={currentId} />
        <main className="flex-1 p-6 bg-paper">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create dashboard redirect page**

Create `dashboard/app/dashboard/page.tsx`:

```tsx
import { redirect } from "next/navigation";
import { listEngagements } from "@/lib/api";

export default async function DashboardPage() {
  const engagements = await listEngagements();
  if (engagements.length === 0) {
    redirect("/dashboard/upload");
  }
  redirect(`/dashboard/${engagements[0].id}`);
}
```

- [ ] **Step 6: Commit**

```bash
git add dashboard/middleware.ts dashboard/components/layout/ dashboard/app/dashboard/
git commit -m "feat: dashboard layout with sidebar, topbar, and Clerk auth"
```

### Task 8: Shared UI components

**Files:**
- Create: `dashboard/components/ui/kpi-card.tsx`
- Create: `dashboard/components/ui/hero-banner.tsx`
- Create: `dashboard/components/ui/chart-card.tsx`
- Create: `dashboard/components/ui/badge.tsx`
- Create: `dashboard/components/ui/data-table.tsx`
- Create: `dashboard/components/charts/plotly-wrapper.tsx`

- [ ] **Step 1: Create KPI card**

Create `dashboard/components/ui/kpi-card.tsx`:

```tsx
export function KpiCard({
  label,
  value,
  unit,
  color = "teal",
}: {
  label: string;
  value: string;
  unit?: string;
  color?: "teal" | "slate" | "amber" | "success" | "error";
}) {
  const colorMap = {
    teal: "text-teal",
    slate: "text-slate",
    amber: "text-amber",
    success: "text-success",
    error: "text-error",
  };

  return (
    <div className="bg-paper rounded-lg p-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.5px] text-muted">
        {label}
      </div>
      <div className={`text-[32px] font-bold mt-1 tabular-nums ${colorMap[color]}`}>
        {value}
        {unit && <span className="text-sm font-normal text-[#94A3B8] ml-1">{unit}</span>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create hero banner**

Create `dashboard/components/ui/hero-banner.tsx`:

```tsx
import type { Engagement } from "@/lib/types";
import { fmtNumber } from "@/lib/format";

export function HeroBanner({ engagement }: { engagement: Engagement }) {
  const total = engagement.total_co2e || 0;
  const ciLower = engagement.ci_lower || 0;
  const ciUpper = engagement.ci_upper || 0;

  return (
    <div className="bg-slate rounded-xl px-7 py-6 flex items-center gap-6 mb-5">
      <div>
        <div className="text-[10px] uppercase tracking-[1px] text-[#94A3B8]">
          Total Carbon Footprint
        </div>
        <div className="text-4xl font-extrabold text-teal mt-0.5">
          {fmtNumber(total)}
        </div>
        <div className="text-xs text-[#94A3B8] mt-0.5">
          tCO₂e · 95% CI: {fmtNumber(ciLower)} – {fmtNumber(ciUpper)}
        </div>
      </div>
      <div className="ml-auto flex gap-5">
        <div className="text-center">
          <div className="text-[9px] text-[#94A3B8] uppercase tracking-[0.5px]">Suppliers</div>
          <div className="text-xl font-bold text-amber mt-0.5">
            {engagement.supplier_count || 0}
          </div>
        </div>
        <div className="text-center">
          <div className="text-[9px] text-[#94A3B8] uppercase tracking-[0.5px]">Transactions</div>
          <div className="text-xl font-bold text-white mt-0.5">
            {fmtNumber(engagement.transaction_count || 0)}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create chart card**

Create `dashboard/components/ui/chart-card.tsx`:

```tsx
import Link from "next/link";

export function ChartCard({
  title,
  linkHref,
  linkText,
  className,
  children,
}: {
  title: string;
  linkHref?: string;
  linkText?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`bg-surface rounded-lg p-4 border border-[#E5E5E0] ${className || ""}`}>
      <h4 className="text-xs font-semibold mb-2">{title}</h4>
      {children}
      {linkHref && (
        <Link href={linkHref} className="text-[11px] text-teal font-semibold mt-2 block">
          {linkText || "View details →"}
        </Link>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create badge**

Create `dashboard/components/ui/badge.tsx`:

```tsx
const VARIANTS = {
  teal: "bg-teal-tint text-[#0F766E]",
  amber: "bg-amber-tint text-[#92400E]",
  red: "bg-red-tint text-[#991B1B]",
  green: "bg-[#D1FAE5] text-[#065F46]",
  slate: "bg-slate-tint text-[#475569]",
};

export function Badge({
  children,
  variant = "slate",
}: {
  children: React.ReactNode;
  variant?: keyof typeof VARIANTS;
}) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${VARIANTS[variant]}`}>
      {children}
    </span>
  );
}
```

- [ ] **Step 5: Create Plotly wrapper (lazy-loaded)**

Create `dashboard/components/charts/plotly-wrapper.tsx`:

```tsx
"use client";

import dynamic from "next/dynamic";
import type { PlotParams } from "react-plotly.js";
import { HEMERA_THEME } from "@/lib/plotly-theme";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export function PlotlyChart({
  data,
  layout,
  config,
  className,
  style,
}: {
  data: PlotParams["data"];
  layout?: Partial<Plotly.Layout>;
  config?: Partial<Plotly.Config>;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <Plot
      data={data}
      layout={{
        ...HEMERA_THEME,
        autosize: true,
        ...layout,
      }}
      config={{
        displayModeBar: false,
        responsive: true,
        ...config,
      }}
      className={className}
      style={{ width: "100%", ...style }}
      useResizeHandler
    />
  );
}
```

- [ ] **Step 6: Create data table**

Create `dashboard/components/ui/data-table.tsx`:

```tsx
export interface Column<T> {
  key: string;
  label: string;
  align?: "left" | "right";
  render?: (row: T) => React.ReactNode;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
}: {
  columns: Column<T>[];
  rows: T[];
}) {
  return (
    <table className="w-full text-[13px] border-collapse">
      <thead>
        <tr>
          {columns.map((col) => (
            <th
              key={col.key}
              className={`text-left px-3 py-2.5 bg-paper text-[11px] font-semibold uppercase tracking-[0.5px] text-muted border-b-2 border-[#E5E5E0] ${
                col.align === "right" ? "text-right" : ""
              }`}
            >
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="hover:bg-[#FAFAF7]">
            {columns.map((col) => (
              <td
                key={col.key}
                className={`px-3 py-2.5 border-b border-[#F0F0EB] ${
                  col.align === "right" ? "text-right tabular-nums" : ""
                }`}
              >
                {col.render ? col.render(row) : String(row[col.key] ?? "")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 7: Commit**

```bash
git add dashboard/components/
git commit -m "feat: add shared UI components and Plotly chart wrapper"
```

### Task 9: Overview page

**Files:**
- Create: `dashboard/app/dashboard/[id]/layout.tsx`
- Create: `dashboard/app/dashboard/[id]/page.tsx`
- Create: `dashboard/components/charts/scope-donut.tsx`

- [ ] **Step 1: Create engagement layout (provides engagement context)**

Create `dashboard/app/dashboard/[id]/layout.tsx`:

```tsx
export default function EngagementLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
```

- [ ] **Step 2: Create scope donut chart**

Create `dashboard/components/charts/scope-donut.tsx`:

```tsx
"use client";

import { PlotlyChart } from "./plotly-wrapper";
import { SCOPE_COLORS, SCOPE_LABELS } from "@/lib/plotly-theme";

export function ScopeDonut({
  scope1,
  scope2,
  scope3,
}: {
  scope1: number;
  scope2: number;
  scope3: number;
}) {
  return (
    <PlotlyChart
      data={[
        {
          type: "pie",
          hole: 0.55,
          values: [scope1, scope2, scope3],
          labels: [SCOPE_LABELS[1], SCOPE_LABELS[2], SCOPE_LABELS[3]],
          marker: { colors: [SCOPE_COLORS[1], SCOPE_COLORS[2], SCOPE_COLORS[3]] },
          textinfo: "percent+label",
          textposition: "outside",
          hovertemplate: "%{label}: %{value:.1f} tCO₂e (%{percent})<extra></extra>",
        },
      ]}
      layout={{
        showlegend: false,
        margin: { l: 20, r: 20, t: 20, b: 20 },
        height: 280,
      }}
    />
  );
}
```

- [ ] **Step 3: Create the Overview page**

Create `dashboard/app/dashboard/[id]/page.tsx`:

```tsx
import { getEngagement, getCategories, getEngagementSuppliers } from "@/lib/api";
import { HeroBanner } from "@/components/ui/hero-banner";
import { ChartCard } from "@/components/ui/chart-card";
import { ScopeDonut } from "@/components/charts/scope-donut";
import { SCOPE_COLORS } from "@/lib/plotly-theme";
import { fmtTonnes } from "@/lib/format";

export default async function OverviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const engagementId = Number(id);
  const [engagement, categories, suppliers] = await Promise.all([
    getEngagement(engagementId),
    getCategories(engagementId),
    getEngagementSuppliers(engagementId),
  ]);

  const top5 = categories.slice(0, 5);

  // Simple risk tier counts from supplier data
  const riskCounts = { low: 0, med: 0, high: 0 };
  for (const s of suppliers) {
    if (s.intensity_kg_per_gbp > 2) riskCounts.high++;
    else if (s.intensity_kg_per_gbp > 0.5) riskCounts.med++;
    else riskCounts.low++;
  }

  return (
    <div>
      <HeroBanner engagement={engagement} />

      <div className="grid grid-cols-[1.5fr_1fr] gap-4">
        <ChartCard
          title="Scope Breakdown"
          linkHref={`/dashboard/${id}/carbon`}
          linkText="View full carbon breakdown →"
          className="row-span-2"
        >
          <ScopeDonut
            scope1={engagement.scope1_co2e}
            scope2={engagement.scope2_co2e}
            scope3={engagement.scope3_co2e}
          />
        </ChartCard>

        <ChartCard
          title="Top 5 Hotspots"
          linkHref={`/dashboard/${id}/carbon`}
          linkText="View all hotspots →"
        >
          <div className="space-y-2">
            {top5.map((cat) => (
              <div key={cat.name} className="flex items-center gap-2">
                <span className="text-[10px] text-muted w-24 truncate">{cat.name}</span>
                <div className="flex-1 h-2 bg-paper rounded">
                  <div
                    className="h-2 rounded"
                    style={{
                      width: `${(cat.co2e_tonnes / (top5[0]?.co2e_tonnes || 1)) * 100}%`,
                      backgroundColor: SCOPE_COLORS[cat.scope] || "#64748B",
                    }}
                  />
                </div>
                <span className="text-[10px] text-muted tabular-nums">{fmtTonnes(cat.co2e_tonnes)}</span>
              </div>
            ))}
          </div>
        </ChartCard>

        <ChartCard
          title="Supplier Risk Overview"
          linkHref={`/dashboard/${id}/suppliers`}
          linkText="View supplier details →"
        >
          <div className="flex gap-4 items-end h-20">
            {[
              { label: "Low", count: riskCounts.low, color: "#10B981", maxH: 60 },
              { label: "Med", count: riskCounts.med, color: "#F59E0B", maxH: 60 },
              { label: "High", count: riskCounts.high, color: "#EF4444", maxH: 60 },
            ].map((tier) => {
              const total = riskCounts.low + riskCounts.med + riskCounts.high || 1;
              const h = Math.max(8, (tier.count / total) * tier.maxH);
              return (
                <div key={tier.label} className="flex-1 text-center">
                  <div
                    className="mx-auto rounded"
                    style={{ height: h, backgroundColor: tier.color, width: "100%" }}
                  />
                  <div className="text-[9px] text-muted mt-1">
                    {tier.label} ({tier.count})
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build
```

Expected: Build succeeds (runtime API calls will fail without backend, but build should pass).

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/dashboard/[id]/ dashboard/components/charts/scope-donut.tsx
git commit -m "feat: Overview page with hero banner, scope donut, hotspots, supplier risk"
```

### Task 10: Carbon page

**Files:**
- Create: `dashboard/app/dashboard/[id]/carbon/page.tsx`
- Create: `dashboard/components/charts/category-bar.tsx`
- Create: `dashboard/components/charts/monthly-area.tsx`
- Create: `dashboard/components/charts/scatter-bubble.tsx`

- [ ] **Step 1: Create category bar chart**

Create `dashboard/components/charts/category-bar.tsx`:

```tsx
"use client";

import { PlotlyChart } from "./plotly-wrapper";
import { SCOPE_COLORS } from "@/lib/plotly-theme";
import type { CategorySummary } from "@/lib/types";

export function CategoryBar({ categories, limit = 10 }: { categories: CategorySummary[]; limit?: number }) {
  const top = categories.slice(0, limit).reverse();

  return (
    <PlotlyChart
      data={[
        {
          type: "bar",
          orientation: "h",
          y: top.map((c) => c.name),
          x: top.map((c) => c.co2e_tonnes),
          marker: { color: top.map((c) => SCOPE_COLORS[c.scope] || "#64748B") },
          hovertemplate: "%{y}: %{x:.1f} tCO₂e<extra></extra>",
        },
      ]}
      layout={{
        height: Math.max(300, limit * 35),
        margin: { l: 180, r: 20, t: 10, b: 40 },
        xaxis: { title: "tCO₂e" },
      }}
    />
  );
}
```

- [ ] **Step 2: Create scatter bubble chart**

Create `dashboard/components/charts/scatter-bubble.tsx`:

```tsx
"use client";

import { PlotlyChart } from "./plotly-wrapper";
import { SCOPE_COLORS } from "@/lib/plotly-theme";
import type { CategorySummary } from "@/lib/types";

export function SpendVsEmissions({ categories }: { categories: CategorySummary[] }) {
  const top = categories.slice(0, 15);

  return (
    <PlotlyChart
      data={[
        {
          type: "scatter",
          mode: "markers+text",
          x: top.map((c) => c.spend_gbp),
          y: top.map((c) => c.co2e_tonnes),
          text: top.slice(0, 5).map((c) => c.name).concat(top.slice(5).map(() => "")),
          textposition: "top center",
          textfont: { size: 9 },
          marker: {
            size: top.map((c) => Math.max(8, c.gsd * 15)),
            color: top.map((c) => SCOPE_COLORS[c.scope] || "#64748B"),
            opacity: 0.7,
          },
          hovertemplate: "%{text}<br>Spend: £%{x:,.0f}<br>tCO₂e: %{y:.1f}<br><extra></extra>",
        },
      ]}
      layout={{
        height: 350,
        xaxis: { title: "Spend (GBP)" },
        yaxis: { title: "tCO₂e" },
        margin: { l: 60, r: 20, t: 20, b: 50 },
      }}
    />
  );
}
```

- [ ] **Step 3: Create monthly area chart**

Create `dashboard/components/charts/monthly-area.tsx`:

```tsx
"use client";

import { PlotlyChart } from "./plotly-wrapper";
import { SCOPE_COLORS, SCOPE_LABELS } from "@/lib/plotly-theme";
import type { MonthlyData } from "@/lib/types";

export function MonthlyArea({ data }: { data: MonthlyData }) {
  if (!data.has_data || data.months.length === 0) {
    return (
      <div className="text-sm text-muted py-8 text-center">
        Insufficient date data — add transaction dates to enable monthly analysis.
      </div>
    );
  }

  const months = data.months;

  return (
    <PlotlyChart
      data={[1, 2, 3].map((scope) => ({
        type: "scatter" as const,
        mode: "lines" as const,
        fill: "tonexty" as const,
        name: SCOPE_LABELS[scope],
        x: months.map((m) => m.month),
        y: months.map((m) => m[`scope${scope}` as keyof typeof m] as number),
        line: { color: SCOPE_COLORS[scope] },
        hovertemplate: `${SCOPE_LABELS[scope]}: %{y:.2f} tCO₂e<extra></extra>`,
      }))}
      layout={{
        height: 300,
        xaxis: { title: "Month" },
        yaxis: { title: "tCO₂e" },
        margin: { l: 60, r: 20, t: 20, b: 50 },
        legend: { orientation: "h", y: -0.2 },
      }}
    />
  );
}
```

- [ ] **Step 4: Create Carbon page**

Create `dashboard/app/dashboard/[id]/carbon/page.tsx`:

```tsx
import { getEngagement, getCategories, getMonthly } from "@/lib/api";
import { ChartCard } from "@/components/ui/chart-card";
import { CategoryBar } from "@/components/charts/category-bar";
import { SpendVsEmissions } from "@/components/charts/scatter-bubble";
import { MonthlyArea } from "@/components/charts/monthly-area";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { fmtTonnes, fmtGBP, fmtPct } from "@/lib/format";
import type { CategorySummary } from "@/lib/types";

export default async function CarbonPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const engagementId = Number(id);
  const [engagement, categories, monthly] = await Promise.all([
    getEngagement(engagementId),
    getCategories(engagementId),
    getMonthly(engagementId),
  ]);

  const totalCo2e = categories.reduce((sum, c) => sum + c.co2e_tonnes, 0) || 1;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Carbon Footprint</h1>
      <p className="text-sm text-muted mb-6">{engagement.org_name} — detailed breakdown</p>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <ChartCard title="Top 10 Categories by tCO₂e">
          <CategoryBar categories={categories} limit={10} />
        </ChartCard>
        <ChartCard title="Spend vs Emissions">
          <SpendVsEmissions categories={categories} />
        </ChartCard>
      </div>

      <div className="mb-6">
        <ChartCard title="Monthly Emission Pattern">
          <MonthlyArea data={monthly} />
        </ChartCard>
      </div>

      <ChartCard title="Category Summary">
        <DataTable<CategorySummary>
          columns={[
            { key: "name", label: "Category" },
            {
              key: "scope",
              label: "Scope",
              render: (row) => (
                <Badge variant={row.scope === 1 ? "slate" : row.scope === 2 ? "teal" : "amber"}>
                  Scope {row.scope}
                </Badge>
              ),
            },
            { key: "spend_gbp", label: "Spend", align: "right", render: (row) => fmtGBP(row.spend_gbp) },
            { key: "co2e_tonnes", label: "tCO₂e", align: "right", render: (row) => fmtTonnes(row.co2e_tonnes) },
            {
              key: "pct",
              label: "% of Total",
              align: "right",
              render: (row) => fmtPct((row.co2e_tonnes / totalCo2e) * 100),
            },
            { key: "gsd", label: "GSD", align: "right", render: (row) => row.gsd.toFixed(2) },
          ]}
          rows={categories}
        />
      </ChartCard>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/dashboard/[id]/carbon/ dashboard/components/charts/
git commit -m "feat: Carbon page with category bars, scatter, monthly area, and data table"
```

### Task 11: Suppliers page (list + detail)

**Files:**
- Create: `dashboard/app/dashboard/[id]/suppliers/page.tsx`
- Create: `dashboard/app/dashboard/[id]/suppliers/[supplierId]/page.tsx`
- Create: `dashboard/components/charts/radar.tsx`

- [ ] **Step 1: Create radar chart component**

Create `dashboard/components/charts/radar.tsx`:

```tsx
"use client";

import { PlotlyChart } from "./plotly-wrapper";

export function EsgRadar({ domains }: { domains: Record<string, number> }) {
  const labels = Object.keys(domains).map((k) =>
    k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
  const values = Object.values(domains);

  return (
    <PlotlyChart
      data={[
        {
          type: "scatterpolar",
          r: [...values, values[0]],
          theta: [...labels, labels[0]],
          fill: "toself",
          fillcolor: "rgba(13,148,136,0.15)",
          line: { color: "#0D9488" },
          hovertemplate: "%{theta}: %{r:.0f}/100<extra></extra>",
        },
      ]}
      layout={{
        height: 300,
        polar: {
          radialaxis: { range: [0, 100], showticklabels: false },
        },
        margin: { l: 40, r: 40, t: 40, b: 40 },
        showlegend: false,
      }}
    />
  );
}
```

- [ ] **Step 2: Create Suppliers list page**

Create `dashboard/app/dashboard/[id]/suppliers/page.tsx`:

```tsx
import Link from "next/link";
import { getEngagementSuppliers } from "@/lib/api";
import { ChartCard } from "@/components/ui/chart-card";
import { CategoryBar } from "@/components/charts/category-bar";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { fmtTonnes, fmtGBP } from "@/lib/format";
import type { EngagementSupplier } from "@/lib/types";

function riskTier(intensity: number): { label: string; variant: "green" | "amber" | "red" } {
  if (intensity > 2) return { label: "High", variant: "red" };
  if (intensity > 0.5) return { label: "Medium", variant: "amber" };
  return { label: "Low", variant: "green" };
}

export default async function SuppliersPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const suppliers = await getEngagementSuppliers(Number(id));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Suppliers</h1>
      <p className="text-sm text-muted mb-6">{suppliers.length} suppliers in this engagement</p>

      <ChartCard title="Supplier Summary" className="mb-6">
        <DataTable<EngagementSupplier>
          columns={[
            {
              key: "name",
              label: "Supplier",
              render: (row) =>
                row.supplier_id ? (
                  <Link href={`/dashboard/${id}/suppliers/${row.supplier_id}`} className="text-teal font-medium hover:underline">
                    {row.name}
                  </Link>
                ) : (
                  row.name
                ),
            },
            { key: "spend_gbp", label: "Spend", align: "right", render: (row) => fmtGBP(row.spend_gbp) },
            { key: "co2e_tonnes", label: "tCO₂e", align: "right", render: (row) => fmtTonnes(row.co2e_tonnes) },
            {
              key: "intensity_kg_per_gbp",
              label: "kgCO₂e/£",
              align: "right",
              render: (row) => row.intensity_kg_per_gbp.toFixed(2),
            },
            { key: "transaction_count", label: "Transactions", align: "right" },
            {
              key: "risk",
              label: "Risk",
              render: (row) => {
                const tier = riskTier(row.intensity_kg_per_gbp);
                return <Badge variant={tier.variant}>{tier.label}</Badge>;
              },
            },
          ]}
          rows={suppliers}
        />
      </ChartCard>
    </div>
  );
}
```

- [ ] **Step 3: Create Supplier detail page**

Create `dashboard/app/dashboard/[id]/suppliers/[supplierId]/page.tsx`:

```tsx
import { getSupplier } from "@/lib/api";
import { ChartCard } from "@/components/ui/chart-card";
import { EsgRadar } from "@/components/charts/radar";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";

export default async function SupplierDetailPage({
  params,
}: {
  params: Promise<{ id: string; supplierId: string }>;
}) {
  const { supplierId } = await params;
  const supplier = await getSupplier(Number(supplierId));
  const latestScore = supplier.score_history[0];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">{supplier.name}</h1>
      <p className="text-sm text-muted mb-6">
        {supplier.sector} · {supplier.ch_number} · {supplier.entity_type}
      </p>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <ChartCard title="ESG Score">
          {latestScore ? (
            <>
              <div className="text-3xl font-bold text-teal mb-2">
                {latestScore.total_score?.toFixed(0)}/100
              </div>
              <EsgRadar domains={latestScore.domains} />
            </>
          ) : (
            <div className="text-sm text-muted py-8 text-center">Not yet scored</div>
          )}
        </ChartCard>

        <ChartCard title="Source Evidence">
          <DataTable
            columns={[
              { key: "layer", label: "Layer" },
              { key: "source_name", label: "Source" },
              { key: "tier", label: "Tier", render: (row) => `T${row.tier}` },
              { key: "summary", label: "Summary" },
              {
                key: "is_verified",
                label: "Verified",
                render: (row) => (
                  <Badge variant={row.is_verified ? "green" : "amber"}>
                    {row.is_verified ? "Yes" : "No"}
                  </Badge>
                ),
              },
            ]}
            rows={supplier.sources}
          />
        </ChartCard>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/dashboard/[id]/suppliers/ dashboard/components/charts/radar.tsx
git commit -m "feat: Suppliers page with list, detail view, and ESG radar"
```

### Task 12: Data Quality page

**Files:**
- Create: `dashboard/app/dashboard/[id]/quality/page.tsx`

- [ ] **Step 1: Create Data Quality page**

Create `dashboard/app/dashboard/[id]/quality/page.tsx`:

```tsx
import { getDataQuality, getEngagement } from "@/lib/api";
import { ChartCard } from "@/components/ui/chart-card";
import { KpiCard } from "@/components/ui/kpi-card";
import { PlotlyChart } from "@/components/charts/plotly-wrapper";
import { Badge } from "@/components/ui/badge";

export default async function QualityPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const engagementId = Number(id);
  const [engagement, dq] = await Promise.all([
    getEngagement(engagementId),
    getDataQuality(engagementId),
  ]);

  const report = dq as Record<string, any>;
  const summary = report.summary || {};
  const cascade = report.cascade_distribution || {};
  const pedigree = report.pedigree_breakdown || {};
  const recommendations = (report.recommendations || []) as Record<string, any>[];

  // Pedigree radar data
  const pedigreeLabels = Object.keys(pedigree).map((k) =>
    k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
  const pedigreeScores = Object.values(pedigree).map((v: any) => v.weighted_avg_score || 0);

  // Cascade data
  const cascadeLevels = ["L1", "L2", "L3", "L4", "L5", "L6"];
  const currentPcts = cascade.current_by_spend_pct || {};
  const targetPcts = cascade.target_by_spend_pct || {};

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Data Quality</h1>
      <p className="text-sm text-muted mb-6">Uncertainty analysis and improvement recommendations</p>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <KpiCard label="Data Quality Grade" value={summary.data_quality_grade || "—"} color="teal" />
        <KpiCard label="Average GSD" value={(summary.avg_gsd || 0).toFixed(2)} color="slate" />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <ChartCard title="Pedigree Indicators">
          <PlotlyChart
            data={[
              {
                type: "scatterpolar",
                r: [...pedigreeScores, pedigreeScores[0] || 0],
                theta: [...pedigreeLabels, pedigreeLabels[0] || ""],
                fill: "toself",
                fillcolor: "rgba(13,148,136,0.15)",
                line: { color: "#0D9488" },
              },
            ]}
            layout={{
              height: 300,
              polar: { radialaxis: { range: [0, 5], showticklabels: true } },
              margin: { l: 40, r: 40, t: 40, b: 40 },
              showlegend: false,
            }}
          />
        </ChartCard>

        <ChartCard title="Cascade Distribution (Current vs Target)">
          <PlotlyChart
            data={[
              {
                type: "bar",
                name: "Current",
                x: cascadeLevels,
                y: cascadeLevels.map((l) => currentPcts[l] || 0),
                marker: { color: "#1E293B" },
              },
              {
                type: "bar",
                name: "Target",
                x: cascadeLevels,
                y: cascadeLevels.map((l) => targetPcts[l] || 0),
                marker: { color: "#0D9488" },
              },
            ]}
            layout={{
              height: 300,
              barmode: "group",
              yaxis: { title: "% of Spend" },
              margin: { l: 60, r: 20, t: 20, b: 40 },
              legend: { orientation: "h", y: -0.2 },
            }}
          />
        </ChartCard>
      </div>

      {recommendations.length > 0 && (
        <ChartCard title="Improvement Recommendations">
          <div className="space-y-3 mt-2">
            {recommendations.slice(0, 8).map((rec, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-paper rounded-lg">
                <div className="text-lg font-bold text-teal w-6">{i + 1}</div>
                <div className="flex-1">
                  <div className="text-sm font-semibold">{rec.action || rec.category}</div>
                  <div className="text-xs text-muted mt-0.5">
                    {rec.explanation || `Impact score: ${rec.impact_score?.toFixed(1) || "—"}`}
                  </div>
                </div>
                <Badge variant={rec.impact_score > 5 ? "teal" : "amber"}>
                  Impact: {rec.impact_score?.toFixed(1) || "—"}
                </Badge>
              </div>
            ))}
          </div>
        </ChartCard>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/app/dashboard/[id]/quality/
git commit -m "feat: Data Quality page with pedigree radar, cascade bars, and recommendations"
```

### Task 13: Reduction page

**Files:**
- Create: `dashboard/app/dashboard/[id]/reduction/page.tsx`
- Create: `dashboard/components/charts/waterfall.tsx`
- Create: `dashboard/components/charts/quadrant.tsx`

- [ ] **Step 1: Create waterfall chart**

Create `dashboard/components/charts/waterfall.tsx`:

```tsx
"use client";

import { PlotlyChart } from "./plotly-wrapper";

export function ReductionWaterfall({
  baseline,
  reductions,
}: {
  baseline: number;
  reductions: { action: string; reduction_tonnes: number }[];
}) {
  const target = baseline - reductions.reduce((s, r) => s + r.reduction_tonnes, 0);

  return (
    <PlotlyChart
      data={[
        {
          type: "waterfall",
          orientation: "v",
          x: ["Current", ...reductions.map((r) => r.action), "Target"],
          y: [baseline, ...reductions.map((r) => -r.reduction_tonnes), target],
          measure: ["absolute", ...reductions.map(() => "relative"), "total"],
          connector: { line: { color: "#E5E5E0" } },
          increasing: { marker: { color: "#EF4444" } },
          decreasing: { marker: { color: "#0D9488" } },
          totals: { marker: { color: "#1E293B" } },
          hovertemplate: "%{x}: %{y:.1f} tCO₂e<extra></extra>",
        },
      ]}
      layout={{
        height: 350,
        yaxis: { title: "tCO₂e" },
        margin: { l: 60, r: 20, t: 20, b: 80 },
        xaxis: { tickangle: -30 },
      }}
    />
  );
}
```

- [ ] **Step 2: Create quadrant chart**

Create `dashboard/components/charts/quadrant.tsx`:

```tsx
"use client";

import { PlotlyChart } from "./plotly-wrapper";
import type { ReductionRec } from "@/lib/types";

const EFFORT_MAP: Record<string, number> = { low: 1, medium: 2, high: 3 };

export function ImpactEffortQuadrant({ recs }: { recs: ReductionRec[] }) {
  const top = recs.slice(0, 8);

  return (
    <PlotlyChart
      data={[
        {
          type: "scatter",
          mode: "markers+text",
          x: top.map((r) => EFFORT_MAP[r.effort] || 2),
          y: top.map((r) => r.potential_reduction_kg / 1000),
          text: top.map((r) => r.action.slice(0, 25)),
          textposition: "top center",
          textfont: { size: 9 },
          marker: {
            size: top.map((r) => Math.max(12, (r.potential_reduction_kg / 1000) * 2)),
            color: "#0D9488",
            opacity: 0.7,
          },
          hovertemplate: "%{text}<br>Effort: %{x}<br>Reduction: %{y:.1f} tCO₂e<extra></extra>",
        },
      ]}
      layout={{
        height: 350,
        xaxis: {
          title: "Effort",
          tickvals: [1, 2, 3],
          ticktext: ["Low", "Medium", "High"],
          range: [0.5, 3.5],
        },
        yaxis: { title: "Reduction (tCO₂e)" },
        margin: { l: 60, r: 20, t: 20, b: 50 },
        shapes: [
          { type: "line", x0: 2, x1: 2, y0: 0, y1: 1, yref: "paper", line: { dash: "dot", color: "#E5E5E0" } },
          { type: "line", x0: 0, x1: 1, y0: 0.5, y1: 0.5, xref: "paper", line: { dash: "dot", color: "#E5E5E0" } },
        ],
      }}
    />
  );
}
```

- [ ] **Step 3: Create Reduction page**

Create `dashboard/app/dashboard/[id]/reduction/page.tsx`:

```tsx
import { getReduction } from "@/lib/api";
import { ChartCard } from "@/components/ui/chart-card";
import { KpiCard } from "@/components/ui/kpi-card";
import { ReductionWaterfall } from "@/components/charts/waterfall";
import { ImpactEffortQuadrant } from "@/components/charts/quadrant";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { fmtTonnes } from "@/lib/format";
import type { ReductionRec } from "@/lib/types";

export default async function ReductionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const data = await getReduction(Number(id));
  const { recommendations: recs, projections } = data;

  const waterfallData = recs.slice(0, 6).map((r) => ({
    action: r.action.slice(0, 30),
    reduction_tonnes: r.potential_reduction_kg / 1000,
  }));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Reduction Roadmap</h1>
      <p className="text-sm text-muted mb-6">Prioritised actions and 3-year projections</p>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <KpiCard
          label="Year 3 Projected tCO₂e"
          value={fmtTonnes(projections.year3_target)}
          unit="tCO₂e"
          color="teal"
        />
        <KpiCard
          label="Total Reduction Potential"
          value={fmtTonnes(projections.total_reduction)}
          unit="tCO₂e"
          color="success"
        />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <ChartCard title="Impact vs Effort">
          <ImpactEffortQuadrant recs={recs} />
        </ChartCard>
        <ChartCard title="Reduction Waterfall">
          <ReductionWaterfall baseline={projections.baseline} reductions={waterfallData} />
        </ChartCard>
      </div>

      <ChartCard title="All Recommendations">
        <DataTable<ReductionRec>
          columns={[
            { key: "action", label: "Action" },
            {
              key: "type",
              label: "Type",
              render: (row) => (
                <Badge variant={row.type === "energy" ? "teal" : row.type === "transport" ? "amber" : "slate"}>
                  {row.type}
                </Badge>
              ),
            },
            { key: "current_co2e_kg", label: "Current tCO₂e", align: "right", render: (row) => fmtTonnes(row.current_co2e_kg / 1000) },
            { key: "potential_reduction_kg", label: "Reduction", align: "right", render: (row) => fmtTonnes(row.potential_reduction_kg / 1000) },
            { key: "effort", label: "Effort", render: (row) => <Badge variant={row.effort === "low" ? "green" : row.effort === "high" ? "red" : "amber"}>{row.effort}</Badge> },
            { key: "timeline", label: "Timeline" },
          ]}
          rows={recs}
        />
      </ChartCard>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/dashboard/[id]/reduction/ dashboard/components/charts/waterfall.tsx dashboard/components/charts/quadrant.tsx
git commit -m "feat: Reduction page with quadrant, waterfall, and recommendation table"
```

### Task 14: Upload page

**Files:**
- Create: `dashboard/app/dashboard/upload/page.tsx`
- Create: `dashboard/components/upload/dropzone.tsx`

- [ ] **Step 1: Create dropzone component**

Create `dashboard/components/upload/dropzone.tsx`:

```tsx
"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Stage = "idle" | "uploading" | "processing" | "done" | "error";

interface UploadResult {
  engagement_id: number;
  parsing: { transactions_parsed: number; duplicates_removed: number; total_spend_gbp: number };
  carbon_footprint: { total_tCO2e: number; scope1_tCO2e: number; scope2_tCO2e: number; scope3_tCO2e: number };
  suppliers: { unique_suppliers: number };
}

export function UploadDropzone() {
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState<UploadResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const router = useRouter();
  const { getToken } = useAuth();

  const handleFile = useCallback(
    async (file: File) => {
      setStage("uploading");
      setError("");

      try {
        const token = await getToken();
        const formData = new FormData();
        formData.append("file", file);

        setStage("processing");
        const res = await fetch(`${API_URL}/api/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });

        if (!res.ok) {
          throw new Error(await res.text());
        }

        const data = await res.json();
        setResult(data);
        setStage("done");
      } catch (e: any) {
        setError(e.message || "Upload failed");
        setStage("error");
      }
    },
    [getToken]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  if (stage === "done" && result) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">✓</div>
        <h3 className="text-xl font-bold mb-2">Upload Complete</h3>
        <div className="grid grid-cols-3 gap-4 max-w-md mx-auto mb-6">
          <div className="bg-paper rounded-lg p-3">
            <div className="text-2xl font-bold text-teal">{result.parsing.transactions_parsed}</div>
            <div className="text-[10px] text-muted uppercase">Transactions</div>
          </div>
          <div className="bg-paper rounded-lg p-3">
            <div className="text-2xl font-bold text-teal">{result.carbon_footprint.total_tCO2e.toFixed(1)}</div>
            <div className="text-[10px] text-muted uppercase">tCO₂e</div>
          </div>
          <div className="bg-paper rounded-lg p-3">
            <div className="text-2xl font-bold text-amber">{result.suppliers.unique_suppliers}</div>
            <div className="text-[10px] text-muted uppercase">Suppliers</div>
          </div>
        </div>
        <button
          onClick={() => router.push(`/dashboard/${result.engagement_id}`)}
          className="bg-teal text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:opacity-90"
        >
          View Results →
        </button>
      </div>
    );
  }

  return (
    <div
      className={`border-2 border-dashed rounded-xl p-16 text-center transition-colors cursor-pointer ${
        dragOver ? "border-teal bg-teal-tint" : "border-[#E5E5E0] hover:border-teal"
      }`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => document.getElementById("file-input")?.click()}
    >
      <input id="file-input" type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={onFileSelect} />

      {stage === "idle" && (
        <>
          <div className="text-3xl mb-3 text-muted">↑</div>
          <h3 className="text-lg font-bold mb-1">Drop your accounting file here</h3>
          <p className="text-sm text-muted">CSV or Excel. We'll classify, match suppliers, and calculate your footprint.</p>
        </>
      )}

      {(stage === "uploading" || stage === "processing") && (
        <>
          <div className="text-3xl mb-3 animate-pulse">⚡</div>
          <h3 className="text-lg font-bold mb-1">
            {stage === "uploading" ? "Uploading..." : "Processing..."}
          </h3>
          <p className="text-sm text-muted">Parse → Classify → Match Suppliers → Calculate Emissions</p>
        </>
      )}

      {stage === "error" && (
        <>
          <div className="text-3xl mb-3">⚠</div>
          <h3 className="text-lg font-bold text-error mb-1">Upload Failed</h3>
          <p className="text-sm text-muted">{error}</p>
          <button
            onClick={(e) => { e.stopPropagation(); setStage("idle"); }}
            className="mt-3 text-sm text-teal font-semibold"
          >
            Try again
          </button>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create Upload page**

Create `dashboard/app/dashboard/upload/page.tsx`:

```tsx
import { UploadDropzone } from "@/components/upload/dropzone";

export default function UploadPage() {
  return (
    <div className="max-w-2xl mx-auto mt-12">
      <h1 className="text-2xl font-bold mb-1">Upload Accounting Data</h1>
      <p className="text-sm text-muted mb-8">
        Upload a CSV or Excel file with your accounting transactions. Hemera will classify them,
        match suppliers, and calculate your carbon footprint.
      </p>
      <UploadDropzone />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/dashboard/upload/ dashboard/components/upload/
git commit -m "feat: Upload page with drag-and-drop and processing feedback"
```

### Task 15: QC page (admin only)

**Files:**
- Create: `dashboard/app/dashboard/[id]/qc/page.tsx`

- [ ] **Step 1: Create QC page**

Create `dashboard/app/dashboard/[id]/qc/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface QcCard {
  transaction_id: number;
  row_number: number;
  description: string;
  supplier: string;
  amount_gbp: number;
  scope: number;
  category: string;
  co2e_kg: number;
}

interface QcResult {
  transaction_id: number;
  classification_pass: boolean;
  emission_factor_pass: boolean;
  arithmetic_pass: boolean;
  supplier_match_pass: boolean;
  pedigree_pass: boolean;
  notes: string;
}

export default function QcPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();
  const [cards, setCards] = useState<QcCard[]>([]);
  const [results, setResults] = useState<Record<number, QcResult>>({});
  const [status, setStatus] = useState<"idle" | "loading" | "reviewing" | "submitted">("idle");
  const [submitResult, setSubmitResult] = useState<Record<string, any> | null>(null);

  const apiCall = async (path: string, method = "GET", body?: any) => {
    const token = await getToken();
    const res = await fetch(`${API_URL}/api${path}`, {
      method,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  };

  const generateSample = async () => {
    setStatus("loading");
    const data = await apiCall(`/engagements/${id}/qc/generate`, "POST");
    setCards(data.cards || []);
    const initial: Record<number, QcResult> = {};
    for (const card of data.cards || []) {
      initial[card.transaction_id] = {
        transaction_id: card.transaction_id,
        classification_pass: true,
        emission_factor_pass: true,
        arithmetic_pass: true,
        supplier_match_pass: true,
        pedigree_pass: true,
        notes: "",
      };
    }
    setResults(initial);
    setStatus("reviewing");
  };

  const toggleCheck = (txnId: number, field: keyof QcResult) => {
    setResults((prev) => ({
      ...prev,
      [txnId]: { ...prev[txnId], [field]: !prev[txnId][field] },
    }));
  };

  const submit = async () => {
    const data = await apiCall(`/engagements/${id}/qc/submit`, "POST", {
      results: Object.values(results),
    });
    setSubmitResult(data);
    setStatus("submitted");
  };

  const checks: { key: keyof QcResult; label: string }[] = [
    { key: "classification_pass", label: "Classification" },
    { key: "emission_factor_pass", label: "Emission Factor" },
    { key: "arithmetic_pass", label: "Arithmetic" },
    { key: "supplier_match_pass", label: "Supplier Match" },
    { key: "pedigree_pass", label: "Pedigree" },
  ];

  if (status === "submitted" && submitResult) {
    return (
      <div className="max-w-lg mx-auto mt-12 text-center">
        <h1 className="text-2xl font-bold mb-4">QC Complete</h1>
        <div className="bg-surface rounded-lg p-6 border border-[#E5E5E0]">
          <div className="text-3xl font-bold text-teal mb-2">
            {submitResult.current_error_rate?.toFixed(1)}% error rate
          </div>
          <Badge variant={submitResult.qc_complete ? "green" : "amber"}>
            {submitResult.qc_complete ? "QC Passed" : "QC Incomplete"}
          </Badge>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">QC Review</h1>
      <p className="text-sm text-muted mb-6">Analyst quality control sampling</p>

      {status === "idle" && (
        <button
          onClick={generateSample}
          className="bg-teal text-white px-6 py-2.5 rounded-lg font-semibold text-sm"
        >
          Generate Sample
        </button>
      )}

      {status === "loading" && <p className="text-muted">Generating sample...</p>}

      {status === "reviewing" && (
        <>
          <p className="text-sm text-muted mb-4">{cards.length} transactions to review</p>
          <div className="space-y-4">
            {cards.map((card) => (
              <div key={card.transaction_id} className="bg-surface rounded-lg p-4 border border-[#E5E5E0]">
                <div className="flex justify-between mb-2">
                  <span className="font-semibold text-sm">#{card.row_number} — {card.description}</span>
                  <span className="text-sm text-muted">{card.co2e_kg?.toFixed(1)} kgCO₂e</span>
                </div>
                <div className="text-xs text-muted mb-3">
                  {card.supplier} · £{card.amount_gbp?.toFixed(0)} · Scope {card.scope} · {card.category}
                </div>
                <div className="flex gap-2 flex-wrap">
                  {checks.map((check) => {
                    const pass = results[card.transaction_id]?.[check.key] as boolean;
                    return (
                      <button
                        key={check.key}
                        onClick={() => toggleCheck(card.transaction_id, check.key)}
                        className={`px-3 py-1 rounded text-xs font-semibold border ${
                          pass
                            ? "bg-teal-tint text-[#0F766E] border-teal"
                            : "bg-red-tint text-[#991B1B] border-error"
                        }`}
                      >
                        {check.label}: {pass ? "✓" : "✗"}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={submit}
            className="mt-6 bg-teal text-white px-6 py-2.5 rounded-lg font-semibold text-sm"
          >
            Submit Results
          </button>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/app/dashboard/[id]/qc/
git commit -m "feat: QC review page with sample generation and submission"
```

### Task 16: Sign-in / Sign-up pages

**Files:**
- Create: `dashboard/app/sign-in/[[...sign-in]]/page.tsx`
- Create: `dashboard/app/sign-up/[[...sign-up]]/page.tsx`
- Modify: `dashboard/app/page.tsx`

- [ ] **Step 1: Create sign-in page**

Create `dashboard/app/sign-in/[[...sign-in]]/page.tsx`:

```tsx
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <div className="text-center">
        <div className="text-teal text-sm font-bold uppercase tracking-[2px] mb-6">Hemera</div>
        <SignIn />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create sign-up page**

Create `dashboard/app/sign-up/[[...sign-up]]/page.tsx`:

```tsx
import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <div className="text-center">
        <div className="text-teal text-sm font-bold uppercase tracking-[2px] mb-6">Hemera</div>
        <SignUp />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update landing page**

Replace `dashboard/app/page.tsx`:

```tsx
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate">
      <div className="text-center">
        <div className="text-teal text-sm font-bold uppercase tracking-[2px] mb-2">Hemera</div>
        <h1 className="text-4xl font-extrabold text-white mb-3">
          Supply Chain Carbon Intelligence
        </h1>
        <p className="text-[#94A3B8] mb-8 max-w-md">
          Measure, understand, and reduce your supply chain emissions with rigorous methodology and actionable insights.
        </p>
        <Link
          href="/dashboard"
          className="bg-teal text-white px-8 py-3 rounded-lg font-semibold text-sm hover:opacity-90 inline-block"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/sign-in/ dashboard/app/sign-up/ dashboard/app/page.tsx
git commit -m "feat: sign-in, sign-up, and landing page"
```

### Task 17: Build verification + CORS fix

**Files:**
- Modify: `hemera/main.py` (update CORS)

- [ ] **Step 1: Run full dashboard build**

```bash
cd /Users/nicohenry/Documents/Hemera/dashboard && npm run build
```

Fix any TypeScript errors that come up. Common issues:
- Plotly type imports — may need `@ts-expect-error` for `react-plotly.js` types
- Missing `Plotly` namespace — add `import type Plotly from "plotly.js"` if needed in plotly-wrapper.tsx

- [ ] **Step 2: Update CORS in backend**

In `hemera/main.py`, update the CORS origins to include the Vercel URL:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 3: Run backend tests**

```bash
cd /Users/nicohenry/Documents/Hemera && .venv/bin/python -m pytest tests/ -v
```

Expected: 136+ PASS

- [ ] **Step 4: Commit**

```bash
git add hemera/main.py dashboard/
git commit -m "chore: build verification and CORS update for dashboard"
```

### Task 18: Run everything end-to-end

- [ ] **Step 1: Start the backend**

```bash
cd /Users/nicohenry/Documents/Hemera && .venv/bin/uvicorn hemera.main:app --reload
```

- [ ] **Step 2: Start the dashboard**

```bash
cd /Users/nicohenry/Documents/Hemera/dashboard && npm run dev
```

- [ ] **Step 3: Open http://localhost:3000 and verify:**

- Landing page renders with "Go to Dashboard" button
- Sign-in redirects to Clerk
- After sign-in, dashboard loads with sidebar
- If no engagements, redirects to Upload
- Upload page accepts a CSV file
- After upload, Overview page shows hero banner + charts
- Carbon, Suppliers, Quality, Reduction pages load with data
- PDF download button works
- Engagement selector switches between engagements

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Hemera dashboard — all pages functional"
```
