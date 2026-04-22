# Admin Features — Design Spec

**Date:** 2026-04-22

## Overview

Five interconnected features to strengthen the admin experience: soft-delete with bin, ownership info dropdown, a full admin Suppliers page with search/filters/CH lookup, emission factor verification viewer, and DEFRA 2025 factor seeding.

---

## 1. Client Queue — Soft Delete + Admin Bin

### Database
Add to `Engagement` model:
- `deleted_at: DateTime, nullable` — NULL = active, timestamp = soft-deleted
- `deleted_by: String(255), nullable` — email of who deleted

Migration: additive, two nullable columns.

### API
- `DELETE /engagements/{id}` — change from hard delete to soft delete. Set `deleted_at=now()`, `deleted_by=current_user.email`. Auth: admin OR `uploaded_by_email` matches current user. Remove the status restriction (currently blocks non-uploaded/processing).
- `GET /engagements` — add `WHERE deleted_at IS NULL` by default. New query param `?deleted=true` (admin-only) returns soft-deleted items.
- `POST /engagements/{id}/restore` — admin-only. Sets `deleted_at=NULL`, `deleted_by=NULL`.
- `DELETE /engagements/{id}/permanent` — admin-only. Hard deletes engagement + cascading transactions, selections, actions.

### Frontend
- Trash icon on each engagement card (visible to admin and the uploader).
- Confirmation dialog before delete.
- New `/dashboard/bin` route (admin-only) listing deleted engagements with restore and permanent delete actions.
- New sidebar item "Bin" with count badge under Admin section.

---

## 2. Client Queue — Ownership Dropdown

### No database changes.

### Frontend
- Clickable info chevron on each engagement card.
- Opens a styled popover showing: uploaded_by_email, org_name, contact_email (if present), upload date, upload filename, transaction count, total CO2e.
- View-only. Closes on click-outside or Escape.
- If Clerk user name is available via the existing user data, show it alongside email.

---

## 3. Admin Suppliers Page

### New routes
- `/dashboard/suppliers` — list page (admin-only)
- `/dashboard/suppliers/[supplierId]` — detail page

### Sidebar
Add "Suppliers" to ADMIN_SECTIONS, under Admin alongside Clients.

### List page
- **Search:** by name or CH number against DB. Below results: "Not found? Search Companies House" button that hits CH API live. Each CH result has "Run analysis & add to database" button.
- **Filters:** risk level, Hemera Score range, sector, enrichment status (enriched/not enriched), last analysis date range.
- **Sort:** alphabetical (default), Hemera Score, last analysis date.
- **Per row:** name, CH number, status, sector, Hemera Score badge, critical flag, confidence, last analysis date, engagement count. Expandable for quick preview. Clickable to detail page.

### Quick preview (expandable accordion)
- Domain scores as mini bars
- Top findings by severity
- Engagement links
- "View full profile" and "Rerun analysis" buttons

### Detail page
- **Overview:** full supplier info, Hemera Score with history chart
- **Enrichment layers:** 13 collapsible sections with source data, fetch date, verified status
- **Findings:** filterable by domain/severity
- **Score history:** chart over time
- **Engagements:** clickable links to each engagement
- **Rerun analysis:** button that queues background enrichment job with progress indicator

### API additions
- `GET /suppliers` — extend with filter params: `risk_level`, `min_score`, `max_score`, `sector`, `enrichment_status`, `analysed_after`, `analysed_before`, `sort_by`, `offset` for pagination. Add `last_analysed_at` and `engagement_count` to response.
- `GET /suppliers/search/companies-house?q=...` — new endpoint proxying CH API.
- `POST /suppliers/from-companies-house` — create supplier from CH data, optionally trigger enrichment.
- `GET /suppliers/{id}` — extend response with engagement list and findings.

---

## 4. Emission Factor Verification — In-App DEFRA Viewer

### Database
Add to `EmissionFactor` model:
- `source_sheet: String(100), nullable` — Excel sheet/tab name
- `source_row: Integer, nullable` — row number in original Excel
- `source_hierarchy: JSON, nullable` — full category path as array

Migration: three nullable columns.

### Parser changes
The 2025 full-set Excel has per-sheet tables (Fuels, UK electricity, etc.) NOT a single "Factors by Category" flat sheet. Need a new parser `parse_full_set_factors()` that:
- Iterates each data sheet
- Finds the header row (contains "Activity", "Unit", "kg CO2e")
- Parses data rows with Activity (L1), Fuel/type (L2), Unit, kg CO2e
- Records sheet name, row number, and hierarchy
- Handles the varying column layouts per sheet (Fuels has 4 cols, UK electricity has Year col, etc.)

### Seed script
Update `seed_factors.py` to also discover full-set files (`ghg-conversion-factors-YYYY-full-set.xlsx`), and store `source_sheet`, `source_row`, `source_hierarchy`.

### API
- `GET /emission-factors/{id}/context` — returns factor details + surrounding rows from same sheet (by `source_sheet` and `source_row ± 7`). Accepts optional `transaction_id` to include calculation breakdown.

### Frontend
- Replace the "Verify" link on QC cards with a button that opens a modal.
- Modal top: calculation breakdown (quantity × factor = CO2e).
- Modal bottom: DEFRA table context with highlighted matched row and surrounding rows.
- Footer: link to gov.uk page as fallback.

---

## 5. DEFRA 2025 Activity Factor Seeding

- Copy `ghg-conversion-factors-2025-full-set.xlsx` to `data/defra/`.
- Parser handles the full-set per-sheet format.
- Seed script loads all factors with positional metadata.
- This unblocks activity-based carbon calculations.
