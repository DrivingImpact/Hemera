# Carbon Footprint PDF Report — Design Spec

**Date:** 2026-04-07
**Status:** Approved

## Overview

Generate a board-ready PDF carbon footprint report from an engagement's calculated data. Plot-heavy (19 charts + 4 KPIs across 9 data pages), styled with the Hemera brand guidelines, rendered via HTML→SVG→WeasyPrint.

This is Document 1 of 2. Document 2 (Supplier Engagement Report) is a follow-up task.

## Audience

Dual: CEOs/founders (headline numbers, one-page executive summary) and finance/ops teams (full detail, audit trail, methodology). Clear visual hierarchy serves both.

## Tech Stack

- **Charts:** Plotly (Python) → static SVG export via `plotly.io.to_image` or inline SVG via `plotly.io.to_html(full_html=False)`
- **Templates:** Jinja2 HTML templates with embedded SVG charts
- **PDF rendering:** WeasyPrint (pure Python, CSS `@page` support, no headless browser)
- **Font:** Plus Jakarta Sans (embedded via Google Fonts or local woff2)
- **Brand:** As defined in `docs/superpowers/specs/2026-04-06-brand-guidelines-design.md`

## API Endpoint

```
GET /api/reports/{engagement_id}/pdf
```

Returns a `application/pdf` response. Requires authentication (Clerk JWT). The engagement must be in `delivered` status.

## Page Structure

### Page 1: Cover

- Dark slate (#1E293B) full-page background
- "HEMERA" wordmark in teal, uppercase, letter-spaced
- "Carbon Footprint Report" in white, display size
- Client org name, reporting period (fiscal year start–end), generation date
- No charts

### Page 2: Executive Summary

One-page boardroom snapshot. Everything the CEO needs.

- **3 KPI cards:** Total tCO2e (teal), 95% CI range (slate), Data quality grade (amber/teal/red depending on grade)
- **Donut chart:** Scope 1/2/3 split using scope colours (slate/teal/amber)
- **Mini horizontal bar:** Top 5 emission categories by tCO2e
- Brief text: 2-3 sentence summary of the footprint

### Page 3: Scope Breakdown

- **Stacked bar chart:** Scope 1, 2, 3 as stacked bars with CI error whiskers on total
- **Treemap:** All categories nested within their scope. Size = tCO2e. Colour by scope.
- Summary table below: Scope | tCO2e | % of total | 95% CI

Data source: `engagement.scope1_co2e`, `scope2_co2e`, `scope3_co2e`, and transactions grouped by `scope` and `category_name`.

### Page 4: Emission Hotspots

- **Horizontal bar chart:** Top 10 categories ranked by tCO2e. Bars coloured by scope.
- **Scatter plot:** X = spend (GBP), Y = tCO2e, bubble size = GSD (uncertainty). Each dot is a category. Labels on top 5.

Data source: transactions grouped by `category_name`, aggregating `amount_gbp`, `co2e_kg`, avg `gsd_total`.

### Page 5: Monthly Pattern

- **Stacked area chart:** Monthly emissions by scope (requires `transaction_date`). X = month, Y = tCO2e, areas stacked by scope.
- **Line chart overlay:** Cumulative actual emissions vs linear projection (total ÷ 12 × month).

Data source: transactions grouped by month of `transaction_date` and `scope`. If `transaction_date` is null for >50% of transactions, skip this page with a note.

### Page 6: Reduction Roadmap

- **Quadrant chart (scatter):** X = effort (estimated), Y = impact (tCO2e reduction). Quadrants labelled: Quick Wins (high impact, low effort), Strategic (high/high), Easy Saves (low/low), Deprioritise (low impact, high effort).
- **Waterfall chart:** Starting at current total, each bar shows a reduction action, ending at projected total.

Data source: `generate_recommendations()` from `data_quality.py` provides the base recommendations. Reduction-specific recommendations are a new addition (see New Logic section).

### Page 7: Quick Wins & Strategic Actions

- **Horizontal bar chart:** tCO2e reduction potential per recommendation, coloured by type (chart-of-accounts = teal, activity data = amber, supplier engagement = slate).
- **Recommendation table:** Columns: Rank | Action | Type | Current tCO2e | Potential reduction | Effort | Timeline

Data source: recommendations sorted by `impact_score`.

### Page 8: Your Footprint Journey — Projections

The motivational page. Shows three scenarios over 3 years:

- **Fan chart:** Central line = current footprint held flat. Three bands:
  - Scenario A (do nothing): flat line, same CI band
  - Scenario B (improve data quality): same central estimate, CI narrows year-over-year
  - Scenario C (data quality + reductions): central estimate drops, CI narrows
- **Stepped waterfall:** Year 1 baseline → Year 2 (better data, tighter CI) → Year 3 (reductions implemented) → projected target
- **2 KPI cards:** Projected Year 3 tCO2e, Projected CI reduction (% narrower)

Data source: current totals + projected improvements from recommendations. Projection logic is estimative (see New Logic section).

### Page 9: Uncertainty Analysis

- **Error bar chart:** Central estimate with 95% CI whiskers, one bar per scope + total
- **Radar chart:** 5 pedigree indicators (reliability, completeness, temporal, geographical, technological) with weighted average scores. Pentagon shape.
- **Stacked horizontal bar:** Contribution of each pedigree indicator to total uncertainty (%)

Data source: `compute_pedigree_breakdown()` and `compute_summary()` from `data_quality.py`.

### Page 10: Data Quality Improvement

- **Grouped bar chart:** Current vs target cascade distribution (L1-L6) by spend %. Two bars per level.
- **Impact bar chart:** Top 5 data quality recommendations ranked by uncertainty reduction potential.

Data source: `compute_cascade_distribution()` and `generate_recommendations()` from `data_quality.py`.

### Page 11: Methodology Note

Single page of text. Content:
- Standards alignment (GHG Protocol, DEFRA, ISO 14064, SECR)
- Calculation approach (hybrid: activity-based where physical data exists, spend-based as baseline)
- 6-level cascade model (brief description)
- Pedigree uncertainty method (ecoinvent, 5 indicators, GSD, 95% CI)
- QC process (ISO 19011 statistical sampling)
- Data sources (DEFRA 2023/2024, EEIO 2022)

### Pages 12+: Transaction Detail (Appendix)

Paginated table with all transactions. Columns:
- Row # | Date | Description | Supplier | Amount (GBP) | Scope | Category | EF Source | EF Level | tCO2e | GSD

Sorted by tCO2e descending. Page breaks every ~30 rows. Header repeated on each page.

## New Logic Required

### Reduction Recommendations Engine

The existing `generate_recommendations()` in `data_quality.py` focuses on data quality improvements. We need a separate function for *emission reduction* recommendations:

```python
def generate_reduction_recommendations(transactions: list) -> list[dict]
```

Returns recommendations like:
- "Switch to renewable electricity tariff" (if Scope 2 electricity is significant)
- "Consolidate freight shipments" (if transport is a top category)
- "Implement remote work policy" (if employee commuting/business travel is high)
- "Switch supplier to lower-carbon alternative" (if a supplier has known alternatives)

Each recommendation includes:
- `type`: energy, transport, procurement, operations
- `category`: which emission category it targets
- `current_co2e_kg`: current emissions from that category
- `potential_reduction_pct`: estimated % reduction (conservative)
- `potential_reduction_kg`: estimated kg saved
- `effort`: low, medium, high
- `timeline`: quick (< 3 months), medium (3-12 months), strategic (> 12 months)
- `explanation`: human-readable description

The reduction percentages are conservative estimates based on published benchmarks (e.g., UK grid renewable tariff typically saves ~80% of Scope 2 electricity emissions). These are indicative, not precise — the report should note this.

### Projection Logic

For the "Footprint Journey" page:
- **Year 1 (baseline):** Current totals and CI from the engagement
- **Year 2 (better data):** Same central estimate, CI narrows by the projected improvement from data quality recommendations (e.g., moving from L4→L2 for electricity reduces GSD)
- **Year 3 (reductions):** Central estimate reduced by sum of reduction recommendations implemented, CI continues to narrow

This is estimative — the report should include a disclaimer that projections are indicative and depend on implementation.

## Plotly Brand Theme

A reusable Plotly theme dict that applies Hemera brand colours and typography:

```python
HEMERA_THEME = {
    "layout": {
        "font": {"family": "Plus Jakarta Sans, system-ui, sans-serif", "color": "#1E293B"},
        "paper_bgcolor": "#FFFFFF",
        "plot_bgcolor": "#FFFFFF",
        "colorway": ["#1E293B", "#0D9488", "#F59E0B", "#10B981", "#EF4444", "#64748B"],
        "margin": {"l": 60, "r": 20, "t": 40, "b": 40},
    }
}
```

All charts use this theme. Scope colours are always: Scope 1 = #1E293B, Scope 2 = #0D9488, Scope 3 = #F59E0B.

## WeasyPrint Page Setup

```css
@page {
    size: A4;
    margin: 20mm 18mm 25mm 18mm;
    @bottom-center {
        content: "Confidential | " attr(data-client) " | Page " counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #94A3B8;
    }
}

@page cover {
    margin: 0;
    @bottom-center { content: none; }
}

.page-break { page-break-before: always; }
.no-break { page-break-inside: avoid; }
```

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `hemera/services/pdf_report.py` | Create | Orchestrator: gathers data, generates charts, renders HTML, converts to PDF |
| `hemera/services/report_charts.py` | Create | All Plotly chart generation functions (19 charts) |
| `hemera/services/reduction_recs.py` | Create | Reduction recommendation engine |
| `hemera/templates/report_base.html` | Create | Jinja2 base template with brand CSS, page setup |
| `hemera/templates/report_pages/` | Create | One template per page (cover.html, executive_summary.html, etc.) |
| `hemera/api/reports.py` | Modify | Add GET /api/reports/{id}/pdf endpoint |
| `tests/test_pdf_report.py` | Create | Tests for chart generation, recommendation engine, PDF output |

## Testing

- Unit tests for each chart function (returns valid SVG/HTML string)
- Unit tests for reduction recommendation engine
- Unit tests for projection logic
- Integration test: generate full PDF from sample engagement, verify it's valid PDF, check page count
- Spot-check: specific chart contains expected data points

## Dependencies

New pip packages:
- `weasyprint` — HTML→PDF rendering
- `kaleido` — Plotly static image/SVG export (alternative: use Plotly's to_html for inline SVG)

## What This Does NOT Cover

- Document 2 (Supplier Engagement Report) — separate spec
- Year-on-year comparison — requires returning client with prior engagement (future feature)
- Interactive dashboard versions of these charts — separate spec (Next.js)
- Email delivery of PDF — separate feature
