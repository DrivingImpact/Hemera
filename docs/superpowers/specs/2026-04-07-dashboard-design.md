# Dashboard — Design Spec

**Date:** 2026-04-07
**Status:** Approved

## Overview

Client-facing Next.js dashboard deployed on Vercel. Consumes the existing FastAPI backend at hemera.onrender.com. Multi-page sidebar app with Clerk auth, Plotly.js charts, and Tailwind CSS styled to the Hemera brand guidelines.

## Audience

Same dual audience as the PDF report: CEOs/founders (Overview page, hero numbers) and finance/ops teams (deep-dive pages, data tables, uncertainty analysis).

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | Next.js 14 (App Router) | SSR for initial loads, client components for Plotly |
| Language | TypeScript | Type safety for API responses |
| Auth | @clerk/nextjs | Same provider as backend — JWT forwarded to API |
| Charts | react-plotly.js (lazy-loaded) | Chart parity with PDF backend, has every chart type needed |
| Styling | Tailwind CSS | Custom theme matching brand guidelines |
| Deployment | Vercel | Auto-deploys, pairs naturally with Next.js |
| Project location | `dashboard/` at repo root | Monorepo — Python API + Next.js frontend |

## API Integration

- Base URL from `NEXT_PUBLIC_API_URL` env var (`https://hemera.onrender.com` in prod, `http://localhost:8000` in dev)
- Thin typed `fetch` wrapper — no heavy SDK
- Clerk JWT forwarded in `Authorization: Bearer <token>` header
- Types defined manually from FastAPI response shapes (no codegen)

### Endpoints Consumed

| Endpoint | Used By |
|----------|---------|
| `GET /api/engagements` | Engagement selector dropdown |
| `GET /api/engagements/{id}` | Overview hero, all pages (totals, CI, scope splits) |
| `GET /api/suppliers` | Suppliers page (list, search) |
| `GET /api/suppliers/{id}` | Supplier detail page (ESG radar, sources) |
| `POST /api/upload` | Upload page |
| `GET /api/reports/{id}/data-quality` | Data Quality page |
| `GET /api/reports/{id}/pdf` | PDF download button |
| `POST /api/engagements/{id}/qc/generate` | QC page |
| `GET /api/engagements/{id}/qc` | QC page |
| `POST /api/engagements/{id}/qc/submit` | QC page |

### New Endpoints Needed

The current API returns engagement-level totals but not the per-transaction and per-category breakdowns the dashboard charts need. New endpoints:

| Endpoint | Returns | Used By |
|----------|---------|---------|
| `GET /api/engagements/{id}/categories` | Categories with tCO2e, spend, scope, GSD, sorted by tCO2e desc | Carbon page (hotspots, treemap, scope breakdown) |
| `GET /api/engagements/{id}/monthly` | Monthly emissions by scope (array of {month, scope1, scope2, scope3}) | Carbon page (area chart, cumulative line) |
| `GET /api/engagements/{id}/transactions` | Paginated transaction list with filters (scope, category, supplier) | Carbon page tables, appendix-style views |
| `GET /api/engagements/{id}/reduction` | Reduction recommendations with projections | Reduction page |
| `GET /api/engagements/{id}/suppliers` | Suppliers for this engagement with tCO2e, spend, intensity, risk tier | Suppliers page (engagement-scoped, not global registry) |

These endpoints aggregate data that `pdf_report.py` already computes inline. Extracting them into API endpoints lets the dashboard and PDF share the same data pipeline.

## App Layout

### Sidebar (permanent, 220px)

```
HEMERA (brand)
Acme Ltd (org name)
─────────────────
ANALYSIS
  ● Overview
  ○ Carbon
  ○ Suppliers
  ○ Data Quality
ACTIONS
  ○ Reduction
  ○ Upload
ADMIN (admin users only)
  ○ QC Review
```

### Top Bar

- Left: Engagement selector dropdown (from GET /api/engagements)
- Right: PDF download button, user avatar (Clerk)

### Engagement Selector

- Dropdown populated from `GET /api/engagements`, showing org name + fiscal year + status
- Selecting an engagement navigates to `/dashboard/[id]`
- URL-based state — no client-side store needed
- New users with no engagements → redirected to Upload page

## Route Structure

```
/                                       → Marketing landing (public)
/sign-in                                → Clerk sign-in
/sign-up                                → Clerk sign-up
/dashboard                              → Redirect to latest engagement or Upload
/dashboard/[id]                         → Overview
/dashboard/[id]/carbon                  → Carbon deep-dive
/dashboard/[id]/suppliers               → Supplier list
/dashboard/[id]/suppliers/[supplierId]  → Supplier detail
/dashboard/[id]/quality                 → Data quality & uncertainty
/dashboard/[id]/reduction               → Reduction roadmap & projections
/dashboard/upload                       → CSV upload
/dashboard/[id]/qc                      → QC review (admin only)
```

## Pages

### Overview (`/dashboard/[id]`)

The landing page. Executive summary.

**Hero Banner** (dark slate #1E293B background, full width):
- Total tCO₂e (large, teal)
- Fiscal year + 95% CI range (subtitle)
- Secondary KPIs: Data quality grade, Supplier count, Transaction count

**Asymmetric Chart Grid** (below hero):
- Left (large, 2 rows): Scope donut (Scope 1/2/3 with percentages)
- Top right: Top 5 hotspot categories (horizontal bar, coloured by scope)
- Bottom right: Supplier risk overview (bar chart: low/medium/high count)
- Each chart card links to its deep-dive page ("View full carbon breakdown →")

**Data source:** `GET /api/engagements/{id}` for hero KPIs. `GET /api/engagements/{id}/categories` (top 5) for hotspots. Supplier risk from `GET /api/engagements/{id}/suppliers`.

### Carbon (`/dashboard/[id]/carbon`)

Full carbon footprint analysis. Maps to PDF pages 3–5.

**Charts:**
- Stacked bar — Scope 1/2/3 with CI error whiskers on total
- Grouped bar — All categories by scope (replaces PDF treemap for interactivity)
- Horizontal bar — Top 10 categories ranked by tCO₂e, coloured by scope
- Scatter — Spend (x) vs tCO₂e (y), bubble size = GSD uncertainty, labelled top 5
- Stacked area — Monthly emissions by scope (conditional: skipped if <50% have dates)
- Line — Cumulative actual vs linear projection

**Table:** Category summary — Category, Scope, Spend, tCO₂e, % of total, GSD. Sortable.

**Data source:** `GET /api/engagements/{id}/categories`, `GET /api/engagements/{id}/monthly`.

### Suppliers (`/dashboard/[id]/suppliers`)

Searchable supplier registry. Maps to Doc 2 (Supplier Engagement Report) content.

**List View:**
- Searchable, sortable table: Name, Sector, Spend, tCO₂e, Intensity (kgCO₂e/£), ESG Score, Risk (badge)
- Filters: risk tier, sector
- Top 15 by tCO₂e (horizontal bar)
- Top 15 by carbon intensity (horizontal bar)
- ESG score vs spend (scatter, flagged outliers)
- Donut — suppliers by risk tier

**Detail View** (`/dashboard/[id]/suppliers/[supplierId]`):
- Supplier header: name, sector, SIC codes, Companies House number
- ESG radar chart (8 domains)
- Score history (if multiple scores)
- Source evidence trail table (layer, source, tier, summary, verified status)
- Transactions for this supplier in this engagement

**Data source:** `GET /api/engagements/{id}/suppliers` for list, `GET /api/suppliers/{id}` for detail.

### Data Quality (`/dashboard/[id]/quality`)

Uncertainty analysis and improvement recommendations. Maps to PDF pages 9–10.

**KPIs:** Overall grade (A–E), Average GSD

**Charts:**
- Error bars — Central estimate ± 95% CI per scope + total
- Radar — 5 pedigree indicators (reliability, completeness, temporal, geographical, technological)
- Stacked horizontal bar — Pedigree indicator contribution to total uncertainty (%)
- Grouped bar — Cascade distribution L1–L6 current vs target (% spend)
- Impact bar — Top 5 data quality recommendations by uncertainty reduction

**Cards:** Recommendation cards with action, current state, target, impact score

**Data source:** `GET /api/reports/{id}/data-quality`.

### Reduction (`/dashboard/[id]/reduction`)

Reduction roadmap and projections. Maps to PDF pages 6–8.

**Charts:**
- Quadrant scatter — Impact (y) vs Effort (x), bubble size = tCO₂e reduction, quadrants: Quick Wins / Strategic / Easy Saves / Deprioritise
- Waterfall — Current total → each reduction action → projected total
- Horizontal bar — tCO₂e reduction potential per recommendation, coloured by type
- Fan chart — 3-year projection with 3 scenarios (do nothing / improve data / data + reductions), narrowing CI bands
- Stepped waterfall — Year 1 baseline → Year 2 (better data) → Year 3 (reductions) → target

**KPIs:** Projected Year 3 tCO₂e, Projected CI reduction (%)

**Table:** Recommendation table — Rank, Action, Type (badge), Current tCO₂e, Potential Reduction, Effort, Timeline

**Data source:** `GET /api/engagements/{id}/reduction`.

### Upload (`/dashboard/upload`)

Entry point for new engagements. No engagement ID needed.

- Drag-and-drop zone for CSV/Excel files
- File validation (type, size) before upload
- Upload progress indicator
- Processing pipeline steps displayed as they complete: Parse → Classify → Match Suppliers → Calculate Emissions
- Results summary on completion: transactions parsed, duplicates removed, total tCO₂e, scope split, supplier count
- "View Results" button → redirects to Overview for the new engagement

**Data source:** `POST /api/upload`.

### QC Review (`/dashboard/[id]/qc`) — Admin Only

Analyst sampling workflow. Hidden from non-admin sidebar.

- "Generate Sample" button → `POST /api/engagements/{id}/qc/generate`
- Displays QC cards for each sampled transaction with check fields:
  - Classification pass (yes/no)
  - Emission factor pass (yes/no)
  - Arithmetic pass (yes/no)
  - Supplier match pass (yes/no)
  - Pedigree pass (yes/no)
  - Notes (text)
- Progress bar: reviewed / total sampled
- Submit button → `POST /api/engagements/{id}/qc/submit`
- Results: error rate, acceptance status, engagement status update

**Data source:** QC endpoints.

## Empty States

- **No engagements:** Redirect to Upload page. Upload page shows welcome message + drag-and-drop.
- **Engagement not delivered:** Show engagement status with explanation. Only delivered engagements show full dashboard.
- **No monthly data:** Monthly chart section shows "Insufficient date data — add transaction dates to enable monthly analysis."
- **No suppliers enriched:** Supplier detail shows "Not yet enriched" with enrich button (if admin).

## Brand Implementation (Tailwind Config)

```js
// tailwind.config.ts — extend theme
{
  colors: {
    slate: '#1E293B',
    teal: '#0D9488',
    amber: '#F59E0B',
    paper: '#F5F5F0',
    surface: '#FFFFFF',
    muted: '#64748B',
    success: '#10B981',
    error: '#EF4444',
    'teal-tint': '#CCFBF1',
    'amber-tint': '#FEF3C7',
    'red-tint': '#FEE2E2',
    'slate-tint': '#F1F5F9',
  },
  fontFamily: {
    sans: ['Plus Jakarta Sans', 'system-ui', '-apple-system', 'sans-serif'],
  },
}
```

Scope colours: Scope 1 = slate (#1E293B), Scope 2 = teal (#0D9488), Scope 3 = amber (#F59E0B). Consistent across all charts and UI elements.

## Plotly Theme (reused from PDF backend)

```ts
export const HEMERA_THEME = {
  layout: {
    font: { family: "Plus Jakarta Sans, system-ui, sans-serif", color: "#1E293B" },
    paper_bgcolor: "#FFFFFF",
    plot_bgcolor: "#FFFFFF",
    colorway: ["#1E293B", "#0D9488", "#F59E0B", "#10B981", "#EF4444", "#64748B"],
    margin: { l: 60, r: 20, t: 40, b: 40 },
  },
};
```

## Data Fetching Strategy

- **Server Components** for initial page loads — fetch engagement data with Clerk JWT on the server
- **Client Components** only where DOM is needed: Plotly charts, upload drag-and-drop, QC form interactions
- **URL-based state** — engagement ID in the URL, no client-side state library
- **Loading states** — skeleton cards matching the final layout while data loads
- **Error boundaries** — per-section, so a failed chart doesn't break the whole page

## File Structure

```
dashboard/
├── app/
│   ├── layout.tsx                    # Root layout (Clerk provider, font)
│   ├── page.tsx                      # Landing page (public)
│   ├── sign-in/[[...sign-in]]/page.tsx
│   ├── sign-up/[[...sign-up]]/page.tsx
│   └── dashboard/
│       ├── layout.tsx                # Dashboard layout (sidebar, topbar, auth gate)
│       ├── page.tsx                  # Redirect to latest engagement
│       ├── upload/page.tsx           # Upload page
│       └── [id]/
│           ├── layout.tsx            # Engagement layout (fetches engagement, provides context)
│           ├── page.tsx              # Overview
│           ├── carbon/page.tsx
│           ├── suppliers/
│           │   ├── page.tsx          # Supplier list
│           │   └── [supplierId]/page.tsx  # Supplier detail
│           ├── quality/page.tsx
│           ├── reduction/page.tsx
│           └── qc/page.tsx
├── components/
│   ├── layout/
│   │   ├── sidebar.tsx
│   │   ├── topbar.tsx
│   │   └── engagement-selector.tsx
│   ├── charts/                       # Plotly chart wrapper components
│   │   ├── scope-donut.tsx
│   │   ├── category-bar.tsx
│   │   ├── monthly-area.tsx
│   │   ├── scatter-bubble.tsx
│   │   ├── waterfall.tsx
│   │   ├── quadrant.tsx
│   │   ├── radar.tsx
│   │   ├── fan-chart.tsx
│   │   ├── error-bars.tsx
│   │   └── plotly-wrapper.tsx        # Lazy-loaded Plotly with loading skeleton
│   ├── ui/
│   │   ├── kpi-card.tsx
│   │   ├── hero-banner.tsx
│   │   ├── data-table.tsx
│   │   ├── badge.tsx
│   │   ├── chart-card.tsx
│   │   └── skeleton.tsx
│   └── upload/
│       ├── dropzone.tsx
│       └── pipeline-progress.tsx
├── lib/
│   ├── api.ts                        # Typed fetch wrapper
│   ├── types.ts                      # API response types
│   ├── plotly-theme.ts               # HEMERA_THEME constant
│   └── utils.ts                      # Formatters (tCO2e, GBP, percentages)
├── middleware.ts                      # Clerk auth middleware
├── tailwind.config.ts
├── next.config.ts
├── package.json
└── tsconfig.json
```

## Prerequisites

The following new API endpoints must be added to the FastAPI backend before the dashboard pages that consume them can be built:

- `GET /api/engagements/{id}/categories`
- `GET /api/engagements/{id}/monthly`
- `GET /api/engagements/{id}/transactions`
- `GET /api/engagements/{id}/reduction`
- `GET /api/engagements/{id}/suppliers`

These extract aggregation logic already present in `pdf_report.py` into standalone endpoints. They should be implemented as part of the dashboard implementation plan (early steps, before the pages that need them).

## What This Does NOT Cover

- Marketing landing page design (just a redirect for now)
- Email notifications
- Multi-tenancy admin panel
- Year-on-year comparison (requires returning client)
- Supplier Engagement Report (Doc 2) PDF generation
- Real-time data updates / websockets
