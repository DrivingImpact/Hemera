# Admin Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add soft-delete + bin, ownership dropdown, admin suppliers page, DEFRA factor viewer, and seed 2025 factors.

**Architecture:** Backend-first — migrations and API endpoints first, then frontend. The DEFRA parser/seeder is independent and can be done in parallel with the engagement soft-delete work.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Next.js 16 (App Router), React 19, Tailwind CSS 4, Clerk auth, Companies House API

---

### Task 1: Alembic migration — soft delete columns on Engagement

**Files:**
- Create: `alembic/versions/XXXX_add_soft_delete_to_engagements.py`
- Modify: `hemera/models/engagement.py:51-52`

- [ ] **Step 1: Add columns to Engagement model**

Add after line 52 (`delivered_at`):
```python
deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
deleted_by: Mapped[str | None] = mapped_column(String(255))
```

- [ ] **Step 2: Generate Alembic migration**

Run: `cd /Users/nicohenry/Documents/Hemera && .venv/bin/alembic revision --autogenerate -m "add soft delete to engagements"`

- [ ] **Step 3: Commit**

```bash
git add hemera/models/engagement.py alembic/versions/
git commit -m "feat: add deleted_at/deleted_by columns to Engagement model"
```

---

### Task 2: Alembic migration — DEFRA factor source metadata columns

**Files:**
- Modify: `hemera/models/emission_factor.py:28-33`
- Create: new alembic version file

- [ ] **Step 1: Add columns to EmissionFactor model**

Add before `__table_args__`:
```python
# Source traceability — which sheet/row in the original DEFRA Excel
source_sheet: Mapped[str | None] = mapped_column(String(100))
source_row: Mapped[int | None] = mapped_column(Integer)
source_hierarchy: Mapped[list | None] = mapped_column(JSON)
```

- [ ] **Step 2: Generate Alembic migration**

Run: `cd /Users/nicohenry/Documents/Hemera && .venv/bin/alembic revision --autogenerate -m "add source metadata to emission factors"`

- [ ] **Step 3: Commit**

```bash
git add hemera/models/emission_factor.py alembic/versions/
git commit -m "feat: add source_sheet/source_row/source_hierarchy to EmissionFactor"
```

---

### Task 3: DEFRA 2025 full-set parser + seeder update

**Files:**
- Modify: `hemera/services/defra_parser.py`
- Modify: `hemera/services/seed_factors.py`
- Copy: `~/Downloads/ghg-conversion-factors-2025-full-set.xlsx` → `data/defra/`

- [ ] **Step 1: Copy 2025 file into project**

```bash
cp ~/Downloads/ghg-conversion-factors-2025-full-set.xlsx /Users/nicohenry/Documents/Hemera/data/defra/
```

- [ ] **Step 2: Add `parse_full_set_factors()` to defra_parser.py**

New function that iterates per-sheet, finds header rows, parses data rows with sheet name + row number metadata. Returns list of dicts with `source_sheet`, `source_row`, `source_hierarchy` fields.

- [ ] **Step 3: Update seed_factors.py**

Add pattern for full-set files. When inserting factors, populate `source_sheet`, `source_row`, `source_hierarchy` from parser output.

- [ ] **Step 4: Test seed locally**

Run: `.venv/bin/python -m hemera.services.seed_factors`

- [ ] **Step 5: Commit**

```bash
git add data/defra/ hemera/services/defra_parser.py hemera/services/seed_factors.py
git commit -m "feat: parse DEFRA 2025 full-set Excel + seed with source metadata"
```

---

### Task 4: Soft delete API endpoints

**Files:**
- Modify: `hemera/api/engagements.py:121-134` (delete endpoint)
- Modify: `hemera/api/engagements.py:34-41` (list endpoint filter)

- [ ] **Step 1: Update DELETE endpoint to soft delete**

Change `delete_engagement` to set `deleted_at` and `deleted_by` instead of hard-deleting. Allow admin or uploader. Remove status restriction.

- [ ] **Step 2: Filter deleted from list endpoint**

Add `deleted_at IS NULL` to the default query in `list_engagements`. Add `deleted` query param for admin bin view.

- [ ] **Step 3: Add restore endpoint**

`POST /engagements/{id}/restore` — admin-only, clears `deleted_at` and `deleted_by`.

- [ ] **Step 4: Add permanent delete endpoint**

`DELETE /engagements/{id}/permanent` — admin-only, hard deletes with cascade.

- [ ] **Step 5: Add deleted engagement fields to list response**

Include `deleted_at`, `deleted_by` in the response when `?deleted=true`.

- [ ] **Step 6: Commit**

```bash
git add hemera/api/engagements.py
git commit -m "feat: soft delete, restore, and permanent delete for engagements"
```

---

### Task 5: Extended suppliers API

**Files:**
- Modify: `hemera/api/suppliers.py`
- Modify: `hemera/services/companies_house.py` (if CH search exists, else create helper)

- [ ] **Step 1: Extend GET /suppliers with filters and pagination**

Add query params: `risk_level`, `min_score`, `max_score`, `sector`, `enrichment_status`, `analysed_after`, `analysed_before`, `sort_by`, `offset`. Add `last_analysed_at` (from latest SupplierSource.fetched_at) and `engagement_count` to response.

- [ ] **Step 2: Extend GET /suppliers/{id} with engagements and findings**

Add engagement list (via Transaction → Engagement join) and findings to the detail response.

- [ ] **Step 3: Add Companies House search endpoint**

`GET /suppliers/search/companies-house?q=...` — proxies the CH API search endpoint.

- [ ] **Step 4: Add create-from-CH endpoint**

`POST /suppliers/from-companies-house` — accepts CH data, creates Supplier record, optionally triggers enrichment.

- [ ] **Step 5: Add emission factor context endpoint**

`GET /emission-factors/{id}/context` — returns factor + surrounding rows from same sheet + optional calculation breakdown.

- [ ] **Step 6: Commit**

```bash
git add hemera/api/suppliers.py hemera/api/emission_factors.py
git commit -m "feat: extended supplier API with filters, CH search, and emission factor context"
```

---

### Task 6: Frontend — types, API client, sidebar

**Files:**
- Modify: `dashboard/lib/types.ts`
- Modify: `dashboard/lib/api.ts`
- Modify: `dashboard/components/layout/sidebar.tsx`

- [ ] **Step 1: Add new types**

Add `AdminSupplierListItem`, `EmissionFactorContext`, extend `EngagementListItem` with `deleted_at`, `deleted_by`, `upload_filename`, `contact_email`.

- [ ] **Step 2: Add API functions**

`deleteEngagement`, `restoreEngagement`, `permanentDeleteEngagement`, `listDeletedEngagements`, `searchCompaniesHouse`, `createSupplierFromCH`, `getEmissionFactorContext`, extended `getSuppliers` with filter params.

- [ ] **Step 3: Add Suppliers and Bin to admin sidebar**

Add to ADMIN_SECTIONS: "Suppliers" href "/suppliers" and "Bin" href "/bin".

- [ ] **Step 4: Commit**

```bash
git add dashboard/lib/types.ts dashboard/lib/api.ts dashboard/components/layout/sidebar.tsx
git commit -m "feat: frontend types, API client, and sidebar for admin features"
```

---

### Task 7: Frontend — Client Queue delete + ownership dropdown

**Files:**
- Modify: `dashboard/app/dashboard/clients/client-queue.tsx`

- [ ] **Step 1: Add delete button to EngagementCard**

Trash icon in top-right. Confirmation dialog. Calls DELETE endpoint. Fades card out and removes from state.

- [ ] **Step 2: Add ownership info dropdown**

Info chevron that opens a popover with uploader email, org, contact, upload date, filename.

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/dashboard/clients/client-queue.tsx
git commit -m "feat: delete button and ownership dropdown on client queue cards"
```

---

### Task 8: Frontend — Admin Bin page

**Files:**
- Create: `dashboard/app/dashboard/bin/page.tsx`

- [ ] **Step 1: Build bin page**

Server component that fetches `?deleted=true`. Lists deleted engagements with name, who deleted, when, original upload date. Restore and permanent delete buttons per item. "Empty bin" button at top.

- [ ] **Step 2: Commit**

```bash
git add dashboard/app/dashboard/bin/
git commit -m "feat: admin bin page for deleted engagements"
```

---

### Task 9: Frontend — Admin Suppliers list page

**Files:**
- Create: `dashboard/app/dashboard/suppliers/page.tsx`
- Create: `dashboard/app/dashboard/suppliers/supplier-list.tsx` (client component)

- [ ] **Step 1: Build supplier list with search, filters, sort**

Search box, filter bar (risk level, score range, sector, enrichment status, last analysis date), sort controls. Each row shows key supplier info with expand chevron.

- [ ] **Step 2: Add expandable quick preview**

Accordion showing domain scores, top findings, engagement links, rerun analysis button.

- [ ] **Step 3: Add Companies House lookup flow**

"Not found? Search Companies House" below DB results. CH results with "Run analysis & add" button. Progress indicator during enrichment.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/dashboard/suppliers/
git commit -m "feat: admin suppliers list page with search, filters, and CH lookup"
```

---

### Task 10: Frontend — Supplier detail page

**Files:**
- Create: `dashboard/app/dashboard/suppliers/[supplierId]/page.tsx`

- [ ] **Step 1: Build detail page**

Overview section, enrichment layers (13 collapsible), findings list, score history, engagement links (clickable to engagement), rerun analysis button with background job progress.

- [ ] **Step 2: Commit**

```bash
git add dashboard/app/dashboard/suppliers/[supplierId]/
git commit -m "feat: supplier detail page with full enrichment data and engagement links"
```

---

### Task 11: Frontend — Emission Factor Verification Modal

**Files:**
- Modify: `dashboard/app/dashboard/[id]/qc/page.tsx`

- [ ] **Step 1: Replace verify link with modal trigger**

Change the "Verify" anchor to a button that opens a modal/slide-over.

- [ ] **Step 2: Build verification modal**

Top: calculation breakdown. Bottom: DEFRA table with highlighted row and surrounding context. Footer: fallback link to gov.uk.

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/dashboard/[id]/qc/page.tsx
git commit -m "feat: in-app DEFRA factor verification modal on QC cards"
```
