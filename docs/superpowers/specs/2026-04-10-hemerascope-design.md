# HemeraScope — Comprehensive Client Report System Design

**Date:** 2026-04-10
**Status:** Design approved
**Product:** HemeraScope (part of Hemera Intelligence)

## Overview

HemeraScope is Hemera Intelligence's comprehensive client report product. It encompasses the full picture a client receives: carbon footprint analysis (emissions, uncertainty, data quality), supplier intelligence (three-layer risk assessment, analyst curation), and actionable recommendations — delivered as an interactive dashboard and branded PDF report.

This spec focuses on the **supplier intelligence layer**, which is the major new build. The carbon footprint pipeline and report already exist and will be integrated into HemeraScope as sections of the unified deliverable.

### Branding

- **Hemera Intelligence** — the business
- **HemeraScope** — the complete client product (carbon footprint + supplier intelligence + uncertainty, delivered as dashboard + PDF)
- **Hemera Score** — the 0-100 weighted score per supplier (replaces "ESG Score" throughout)
- **Hemera Verified** — badge for suppliers who engage with Hemera and meet a sustainability threshold

### Design Principles

1. **Full audit trail** — every piece of text on the client report traces back: report text → report_selection → supplier_finding → supplier_source → external source URL
2. **Enrich once, curate per client** — findings live on the supplier, selections are per engagement
3. **AI mode flexibility** — every AI task has two buttons: "Generate (API)" and "Copy Prompt (Max)". Both build the identical prompt. API mode calls Claude directly and tracks cost. Max mode copies the prompt to clipboard, analyst pastes into Claude Max, then pastes the response back. Both modes store the prompt, response, and metadata identically in `ai_tasks`. This applies to ALL five AI touchpoints — no exceptions
4. **Collaborative tone** — reports frame findings as improvement opportunities, not compliance failures. Hemera is a partner, not an auditor
5. **Hemera as service** — recommended actions position Hemera as the solution, not just the flag-raiser

## Architecture

### Approach: Hybrid Pipeline with Preview

Two-stage pipeline (curate → review) with live report preview during curation. Clean data model underneath (separate tables for findings, selections, and AI tasks) with a fluid analyst experience.

### Three Intelligence Layers

| Layer | Source | How it works | When it runs |
|---|---|---|---|
| **Deterministic** | `esg_scorer.py` rules | Hard-coded rules evaluate supplier_sources data. Each flag/score becomes a finding. | Automatically after enrichment |
| **Statistical outlier** | Peer comparison | Compares a supplier's domain scores against sector averages. Flags significant deviations. | Automatically when sufficient data exists (sector has 10+ suppliers) |
| **AI analysis** | Claude (API or Max) | Receives all supplier_sources + deterministic findings + context. Identifies patterns, combinations, and risks the rules miss. | On-demand: analyst triggers via API button or copies prompt for Max |

### Pipeline Flow

```
Engagement uploaded
  ├── Carbon pipeline (existing)
  │   Upload → Classify → Calculate → Carbon QC
  │
  └── Supplier pipeline (new, runs in parallel)
      Match Suppliers → Enrich (13 layers) → Generate deterministic findings
        → Generate outlier findings (if data exists)
        → Analyst triggers AI analysis (API or Max)
        → Analyst curates per engagement (Stage 1)
        → AI generates client language + actions (API or Max)

  Both pipelines feed into:
  └── HemeraScope Report (unified deliverable)
      Analyst reviews full report (Stage 2) — carbon + supplier + uncertainty combined
        → Publish to client dashboard + PDF available
```

Enrichment starts as soon as suppliers are matched — does not wait for carbon calculations. The final HemeraScope report combines both pipelines into a single client deliverable.

## Data Model

### New Tables

#### `supplier_findings`

All findings about a supplier from any intelligence layer. Lives on the supplier, reusable across engagements. Re-analysis supersedes old findings without deleting them.

| Column | Type | Description |
|---|---|---|
| `id` | PK | |
| `supplier_id` | FK → suppliers | |
| `source` | enum | `deterministic`, `outlier`, `ai_automated`, `ai_manual` |
| `domain` | enum | `governance`, `labour`, `carbon`, `water`, `product`, `transparency`, `anti_corruption`, `social_value` |
| `severity` | enum | `critical`, `high`, `medium`, `info`, `positive` |
| `title` | text | Short label: "HSE enforcement actions" |
| `detail` | text | Full description with evidence |
| `evidence_url` | text (nullable) | Link to source (gov.uk, registry, etc.) |
| `evidence_data` | JSON (nullable) | Raw evidence payload |
| `layer` | int (nullable) | 1-13, for deterministic findings |
| `source_name` | text | "hse", "opensanctions", "sbti", etc. |
| `is_active` | bool | False when superseded by re-analysis |
| `ai_task_id` | FK → ai_tasks (nullable) | Links AI-sourced findings to their prompt/response |
| `created_at` | timestamp | |
| `superseded_at` | timestamp (nullable) | When re-analysis replaced this finding |

**Indexes:** `(supplier_id, is_active)`, `(supplier_id, domain)`, `(supplier_id, severity)`

#### `report_selections`

Per-engagement curation decisions. Each row = one analyst decision about one finding for one client report.

| Column | Type | Description |
|---|---|---|
| `id` | PK | |
| `engagement_id` | FK → engagements | |
| `finding_id` | FK → supplier_findings | |
| `included` | bool | Whether this finding appears on the client report |
| `client_title` | text (nullable) | Analyst override of finding title for this client |
| `client_detail` | text (nullable) | AI-generated or manually written client-facing language |
| `client_language_source` | enum (nullable) | `ai_automated`, `ai_manual`, `analyst` |
| `analyst_note` | text (nullable) | Internal note — not shown to client |
| `selected_by` | FK → users | |
| `selected_at` | timestamp | |

**Unique constraint:** `(engagement_id, finding_id)` — one decision per finding per engagement.

#### `report_actions`

Recommended actions per supplier per engagement. Positioned as Hemera services.

| Column | Type | Description |
|---|---|---|
| `id` | PK | |
| `engagement_id` | FK → engagements | |
| `supplier_id` | FK → suppliers | |
| `action_text` | text | The recommended action (Hemera-as-service framing) |
| `priority` | int | Display order |
| `linked_finding_ids` | JSON | Which findings prompted this action |
| `language_source` | enum | `ai_automated`, `ai_manual`, `analyst` |
| `ai_task_id` | FK → ai_tasks (nullable) | |
| `created_by` | FK → users | |
| `created_at` | timestamp | |

#### `supplier_engagements`

Hemera's real-world engagement with suppliers. Supplier-level (not per client engagement). Functions as a lightweight CRM.

| Column | Type | Description |
|---|---|---|
| `id` | PK | |
| `supplier_id` | FK → suppliers | |
| `engagement_type` | enum | `outreach`, `meeting`, `workshop`, `ongoing_programme`, `data_request` |
| `subject` | text | "SBTi Commitment Discussion" |
| `status` | enum | `planned`, `contacted`, `in_progress`, `completed`, `no_response`, `declined` |
| `notes` | text | Internal detail |
| `contact_name` | text (nullable) | |
| `contact_email` | text (nullable) | |
| `contacted_at` | timestamp (nullable) | |
| `responded_at` | timestamp (nullable) | |
| `next_action` | text (nullable) | |
| `next_action_date` | date (nullable) | |
| `created_by` | FK → users | |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

#### `ai_tasks`

Tracks every AI interaction regardless of mode. Enables cost tracking, reproducibility, and the manual/API toggle.

| Column | Type | Description |
|---|---|---|
| `id` | PK | |
| `task_type` | enum | `risk_analysis`, `client_language`, `recommended_actions`, `engagement_summary`, `exec_summary` |
| `target_type` | enum | `supplier`, `engagement` |
| `target_id` | int | |
| `mode` | enum | `api`, `manual` |
| `status` | enum | `pending`, `prompt_copied`, `completed`, `failed` |
| `prompt_text` | text | The full prompt (same for API and manual) |
| `response_text` | text (nullable) | Claude's response (API) or pasted response (manual) |
| `prompt_hash` | text | SHA-256 for deduplication |
| `token_count` | int (nullable) | API mode only |
| `cost_usd` | float (nullable) | API mode only |
| `created_at` | timestamp | |
| `completed_at` | timestamp (nullable) | |

### Modified Tables

#### `engagements` — add column

| Column | Type | Description |
|---|---|---|
| `supplier_report_status` | enum (nullable) | `pending`, `curating`, `language_review`, `approved`, `published` |

#### `suppliers` — rename column

| Change | Description |
|---|---|
| `esg_score` → `hemera_score` | Rename to match branding |

All code, UI, and report references to "ESG Score" become "Hemera Score".

### Relationship Summary

```
suppliers
├── supplier_findings[] (all intelligence about this supplier)
├── supplier_sources[] (raw data, unchanged)
├── supplier_scores[] (score history, unchanged — rename total_score field)
├── supplier_engagements[] (Hemera's CRM with this supplier)
└── monitoring_alerts[] (unchanged)

engagements
├── report_selections[] (curation decisions for this client report)
├── report_actions[] (recommended actions per supplier for this report)
└── transactions[] (unchanged)

ai_tasks (standalone, linked by target_type + target_id)
```

## Analyst Workflow

### Stage 1: Supplier Curation

Split-panel view, supplier-by-supplier.

**Left panel — Findings:** All findings for the current supplier, grouped by source (deterministic, outlier, AI). Each finding shows severity badge, domain tag, title, detail, evidence link. Include/Skip toggle per finding.

**Right panel — Report Preview:** Live preview of what the client report will say for this supplier:
- Included findings with client-facing language
- Recommended actions (Hemera-as-service framing)
- Hemera engagement status (from `supplier_engagements`)
- "Generate Language" (API) / "Copy Prompt" (Max) buttons
- "Log Engagement" button for the CRM

**AI paste-back flow:** After clicking "Copy Prompt", a "Paste Response" input appears. Pasting completes the `ai_tasks` row and applies results (creates findings, updates client language, etc.).

**Navigation:** "Save & Next" persists all selections incrementally and moves to the next supplier. Analyst can leave and resume — progress is saved per-selection.

**Supplier ordering:** Critical and high-risk suppliers shown first. Clean suppliers can be bulk-skipped.

### Stage 2: Report Review

Full report preview matching the client view. Table of contents on left, content on right.

Sections:
1. Executive summary (AI-generated, editable)
2. Methodology overview (templated, light-touch description of process)
3. Aggregate risk dashboard (charts: risk distribution, domain averages)
4. Per-supplier pages (findings, actions, engagement status)
5. Recommendations summary (grouped by urgency)

Analyst can edit any text, regenerate AI sections, reorder. Two final actions: "Export PDF" and "Publish to Client Dashboard."

### Five AI Touchpoints

All follow the same pattern: system builds prompt, analyst chooses API or Max, response stored identically.

| # | Task Type | Input | Output | Stored On |
|---|---|---|---|---|
| 1 | Risk analysis | supplier_sources + deterministic findings + context | New `supplier_findings` rows | `supplier_findings` |
| 2 | Client-friendly language | Raw findings selected for report | Professional, constructive text | `report_selections.client_detail` |
| 3 | Recommended actions | Included findings for supplier | Hemera-as-service action items | `report_actions` |
| 4 | Engagement summary | `supplier_engagements` records | Client-facing narrative | `report_selections` (engagement section) |
| 5 | Executive summary | All included findings + actions across all suppliers | Report-level narrative | `engagements.supplier_report_exec_summary` (text field) |

## Client-Facing Views

### Client Dashboard — Supplier Overview

Table of all suppliers in the engagement showing:
- Supplier name, sector, spend
- Hemera Score with colour coding
- Risk level badge (Critical / Needs Attention / Strong)
- Key findings summary
- Hemera engagement status (active count)
- "View detail →" link

Filterable by risk level, sortable by score/spend/name. Export PDF button.

### Client Dashboard — Supplier Detail Page

Per-supplier page showing:
- Header: name, CH number, sector, spend, Hemera Score (large)
- Domain score breakdown (7 colour-coded boxes)
- Key findings (colour-coded by severity, client-facing language)
- Recommended actions (numbered, Hemera-as-service framing)
- Hemera engagement status (narrative + status badges per engagement)

### Hemera Verified Badge

Suppliers who engage with Hemera and meet a defined threshold receive the "Hemera Verified" badge. Displayed on:
- Supplier detail page (prominent badge)
- Supplier overview table (badge column)
- PDF report (per-supplier page)

Threshold criteria TBD — likely a combination of: Hemera Score above X, active engagement programme, key certifications in place, no critical flags.

### PDF Report

Branded document — the single HemeraScope deliverable combining carbon footprint and supplier intelligence. Collaborative tone throughout.

**Structure:**
1. Cover page — "HemeraScope Report" + client name + fiscal year
2. Executive summary — aggregate carbon footprint + supplier risk narrative, key numbers, overall assessment
3. Methodology — "Our Approach" page explaining both the carbon and supplier analysis processes without revealing proprietary methods. Frame as collaborative: "Every supply chain has areas for improvement. This report is the first step in a collaborative process — identifying where targeted engagement can drive the greatest impact."
4. **Carbon Footprint** — scope breakdown, hotspots, monthly trends, reduction roadmap (existing 11-page carbon report content, integrated as sections)
5. **Data Quality & Uncertainty** — pedigree scores, cascade distribution, confidence intervals, data quality recommendations (existing uncertainty content)
6. **Supplier Intelligence** — aggregate risk overview (risk distribution chart, domain average heatmap)
7. Per-supplier pages (1 per supplier) — Hemera Score, domain breakdown, findings, recommended actions, Hemera engagement status, Hemera Verified badge if applicable
8. Recommendations summary — grouped by urgency (immediate/short-term/ongoing), covering both carbon reduction and supplier engagement actions, Hemera services pitch
9. Back cover — "Helping organisations build transparent, resilient supply chains."

**Tone guidelines:** Frame negatives as improvement opportunities. "Supplier X does not currently hold a validated Science Based Target" not "Supplier X failed SBTi check." Emphasise Hemera's active role in helping suppliers improve. Each report should leave the client feeling that Hemera is already working on the problems identified, and that this is a journey everyone goes through — not a pass/fail assessment.

## API Endpoints

### Findings Management (admin only)

| Method | Path | Description |
|---|---|---|
| `GET` | `/suppliers/{id}/findings` | All findings (active + historical) |
| `POST` | `/suppliers/{id}/findings` | Add manual/AI finding |
| `POST` | `/suppliers/{id}/re-analyse` | Re-run enrichment + regenerate findings |
| `GET` | `/suppliers/{id}/engagements` | Hemera engagement history |
| `POST` | `/suppliers/{id}/engagements` | Log new engagement touchpoint |
| `PATCH` | `/suppliers/{id}/engagements/{eid}` | Update engagement status/notes |

### Report Curation (admin only)

| Method | Path | Description |
|---|---|---|
| `GET` | `/engagements/{id}/supplier-report` | All suppliers + findings + current selections |
| `PATCH` | `/engagements/{id}/supplier-report/selections` | Save include/exclude decisions (incremental) |
| `POST` | `/engagements/{id}/supplier-report/actions` | Save recommended actions |
| `POST` | `/engagements/{id}/supplier-report/publish` | Publish to client dashboard |
| `GET` | `/engagements/{id}/supplier-report/preview` | Full report preview data |

### AI Tasks

| Method | Path | Description |
|---|---|---|
| `POST` | `/ai-tasks` | Create task (API: triggers call; manual: returns prompt) |
| `PATCH` | `/ai-tasks/{id}` | Paste back response (manual mode) |
| `GET` | `/ai-tasks` | Query by target_type + target_id |

### Client-Facing

| Method | Path | Description |
|---|---|---|
| `GET` | `/engagements/{id}/supplier-intelligence` | Published supplier report data |
| `GET` | `/engagements/{id}/supplier-intelligence/pdf` | PDF export |
| `GET` | `/engagements/{id}/supplier-intelligence/suppliers/{sid}` | Single supplier detail |

## Changes to Existing Code

### `esg_scorer.py`

- Rename `ESGResult.total_score` → `ESGResult.hemera_score`
- Add `generate_findings_from_result(result: ESGResult, supplier: Supplier) → list[SupplierFinding]` — converts flags + domain scores into `supplier_findings` rows
- Scorer itself unchanged — still produces scores and flags

### `enrichment.py`

- After enrichment completes, call `generate_findings_from_result()` to create deterministic findings
- Add outlier detection: compare supplier's domain scores against sector averages in database

### `supplier_review.py`

- Current endpoint becomes obsolete
- Replace with new curation endpoints
- Sampling logic repurposed: determines supplier display order (critical first), not which claims to verify

### `pdf_report.py`

- Evolves into the unified HemeraScope report generator
- Existing carbon/uncertainty sections become part of the larger HemeraScope PDF
- New supplier intelligence sections added (aggregate risk, per-supplier pages, recommendations)
- Same pattern: data gathering → Jinja2 templates → WeasyPrint PDF
- Single PDF output that covers everything: carbon footprint, uncertainty, supplier intelligence

### Supplier model

- Rename `esg_score` → `hemera_score`
- Add relationships: `findings`, `hemera_engagements`
- Add `hemera_verified` bool column

### Engagement model

- Add `supplier_report_status` column
- Add `supplier_report_exec_summary` text column (AI-generated, analyst-editable)

## Out of Scope (for this iteration)

- Client comments/feedback on supplier findings
- Automated re-enrichment scheduling
- Client-level domain weight preferences (analyst handles manually for now)
- Multi-language report support
- Hemera Verified threshold definition (badge exists in UI, criteria defined later)
- Statistical outlier detection implementation (data model supports it, algorithm built when supplier volume justifies it)
