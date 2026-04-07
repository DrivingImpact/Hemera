# Upload Flow & Dashboard Guards — Design Spec

**Date:** 2026-04-07
**Status:** Approved

## Overview

Restructure the upload pipeline so users can upload freely (no AI token cost), admins review and trigger processing, and clients only see charts after analyst approval. Add empty states to all dashboard pages so nothing crashes.

## Status Flow

```
uploaded → processing → delivered → qc_passed
```

| Status | Set By | Meaning |
|--------|--------|---------|
| `uploaded` | Upload endpoint | Raw data parsed and stored. No classification or calculation yet. |
| `processing` | Admin triggers pipeline | AI classification + emission calculation running. |
| `delivered` | Pipeline completion | Full results calculated, awaiting QC. |
| `qc_passed` | Admin submits QC | Analyst has verified. Charts unlocked for client. |

## Changes

### 1. Upload endpoint — parse only

**Modify:** `POST /api/upload`

Current behaviour: parse → classify → match → calculate → deliver.
New behaviour: parse → store raw transactions → done. Status = `uploaded`.

What it does:
- Parse CSV/Excel into rows
- Create engagement with status `uploaded`
- Save raw transactions (raw_date, raw_supplier, raw_description, raw_amount, amount_gbp)
- Count unique suppliers, total spend, date range
- No classification, no supplier matching, no emission calculation, no pedigree scoring
- No Anthropic API calls

Returns:
```json
{
  "engagement_id": 1,
  "filename": "accounts.csv",
  "status": "uploaded",
  "parsing": {
    "transactions_parsed": 35,
    "duplicates_removed": 0,
    "date_range": "2025-04-01 to 2025-09-30",
    "total_spend_gbp": 38099.30,
    "unique_suppliers": 22
  }
}
```

### 2. New endpoint — admin triggers processing

**Create:** `POST /api/engagements/{id}/process`

Admin-only. Runs the full pipeline on an `uploaded` engagement:
1. Classify each transaction (Anthropic API)
2. Match suppliers to registry
3. Calculate emissions with cascading factor lookup
4. Score pedigree uncertainty
5. Aggregate to overall footprint with 95% CI
6. Update engagement status to `delivered`

Rejects if status is not `uploaded` (can't reprocess a delivered engagement).

### 3. Upload page — dropzone + engagement list

**Modify:** `dashboard/app/dashboard/upload/page.tsx`

Two sections:
- **Top:** Upload dropzone (same as now)
- **Bottom:** "Your Uploads" table showing all engagements for the user:
  - Filename, Upload date, Transactions, Spend, Status badge

Status badges:
- `uploaded` → amber "Awaiting review"
- `processing` → amber "Processing"
- `delivered` → teal "Ready for QC"
- `qc_passed` → green "Approved" (linked to dashboard)

### 4. Dashboard pages — empty states when not approved

**All pages under `/dashboard/[id]/`:**

If the engagement status is not `qc_passed`:
- Show the page layout (section headers, chart card outlines)
- Charts show empty/greyed out placeholders
- Banner at top: "Your data has been uploaded and is awaiting analyst approval"
- No actual data values displayed

Implementation: the `[id]/layout.tsx` fetches the engagement and passes the status down. Each page checks status before rendering data.

### 5. Admin view enhancements

**Modify:** QC page (`/dashboard/[id]/qc`)

Add to the QC page (admin only):
- If status is `uploaded`: show raw data preview (row count, spend, suppliers) + "Start Processing" button that calls `POST /api/engagements/{id}/process`
- If status is `delivered`: show existing QC sampling workflow
- If status is `qc_passed`: show "QC Complete" summary

### 6. Sidebar behaviour

Sidebar links always work. All pages always render their layout. The content is either:
- Real charts + data (status = `qc_passed`)
- Empty placeholders + "awaiting approval" banner (any other status)

## Files Changed

| File | Action | What |
|------|--------|------|
| `hemera/api/upload.py` | Modify | Strip to parse-only, remove classification/calculation |
| `hemera/api/engagements.py` | Modify | Add `POST /engagements/{id}/process` endpoint |
| `hemera/services/pipeline.py` | Create | Extract full pipeline (classify → match → calculate) into standalone function |
| `dashboard/app/dashboard/upload/page.tsx` | Modify | Add engagement list below dropzone |
| `dashboard/app/dashboard/[id]/layout.tsx` | Modify | Fetch engagement status, pass to children |
| `dashboard/app/dashboard/[id]/page.tsx` | Modify | Show empty state if not qc_passed |
| `dashboard/app/dashboard/[id]/carbon/page.tsx` | Modify | Show empty state if not qc_passed |
| `dashboard/app/dashboard/[id]/suppliers/page.tsx` | Modify | Show empty state if not qc_passed |
| `dashboard/app/dashboard/[id]/quality/page.tsx` | Modify | Show empty state if not qc_passed |
| `dashboard/app/dashboard/[id]/reduction/page.tsx` | Modify | Show empty state if not qc_passed |
| `dashboard/app/dashboard/[id]/qc/page.tsx` | Modify | Add processing trigger for uploaded engagements |
| `dashboard/components/ui/pending-banner.tsx` | Create | Reusable "awaiting approval" banner component |

## What This Does NOT Cover

- Pricing / payment integration
- Email notifications to admin when new upload arrives
- Email notifications to client when QC passes
- File storage (CSV is parsed and discarded — raw data lives in transactions table)
