# Hemera Brand Guidelines

**Date:** 2026-04-06
**Status:** Approved

## Brand Personality

Precise, confident, clean, accessible. Hemera is rigorous and offers something no one else does — but the work speaks for itself. The brand should feel inviting enough that a supplier receiving a report thinks "these people want to work with me."

**Audience:** Dual — CEOs/founders (headline numbers, boardroom credibility) and finance/ops teams (auditability, detail). The design needs clear visual hierarchy for both.

## Colour Palette

### Core Colours

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| Primary | Slate | #1E293B | Headings, report headers, Scope 1, dark backgrounds |
| Accent | Teal | #0D9488 | Brand accent, key metrics, Scope 2, links, interactive elements |
| Highlight | Amber | #F59E0B | Warnings, attention, Scope 3, data quality flags |
| Background | Paper | #F5F5F0 | Page backgrounds, card tints |
| Surface | White | #FFFFFF | Card surfaces, content areas, inputs |
| Secondary text | Muted | #64748B | Labels, captions, secondary text |

### Semantic Colours

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| Success | Green | #10B981 | Improvements, positive change, good scores |
| Error | Red | #EF4444 | Critical issues, negative change, failures |

### Scope Colours (charts and breakdowns)

| Scope | Colour | Hex |
|-------|--------|-----|
| Scope 1 | Slate | #1E293B |
| Scope 2 | Teal | #0D9488 |
| Scope 3 | Amber | #F59E0B |

### Tint Variants (for backgrounds and badges)

| Base | Tint | Usage |
|------|------|-------|
| Teal | #CCFBF1 | Success badges, positive highlights |
| Amber | #FEF3C7 | Warning badges, attention cards |
| Red | #FEE2E2 | Error badges, critical highlights |
| Slate | #F1F5F9 | Neutral card backgrounds |

## Typography

**Font:** Plus Jakarta Sans (Google Fonts, free, OFL licence)

**Import:** `https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap`

**Fallback stack:** `'Plus Jakarta Sans', system-ui, -apple-system, sans-serif`

### Type Scale

| Role | Size | Weight | Style | Usage |
|------|------|--------|-------|-------|
| Display | 32px | 800 | — | Report titles, hero numbers |
| Heading 1 | 24px | 700 | — | Section headers |
| Heading 2 | 18px | 700 | — | Subsection headers |
| Heading 3 | 14px | 600 | — | Minor headers |
| Body | 14px | 400 | line-height: 1.65 | Body text, descriptions |
| Caption | 12px | 500 | — | Sources, footnotes |
| Label | 11px | 600 | uppercase, letter-spacing: 1.5px | Stat labels, field labels |
| Metric | 32px | 700 | tabular-nums | Key numbers (tCO2e, percentages) |

### Numeric Display

Use `font-variant-numeric: tabular-nums` for all data tables and metrics to ensure columns align.

## Component Patterns

### Report Header

- Dark slate (#1E293B) background
- "HEMERA" in teal, 12px, uppercase, letter-spacing: 2px, weight 700
- Title in white, display size
- Subtitle (client name, date) in muted (#94A3B8)

### Stat Cards

- Paper (#F5F5F0) background, 8px border-radius
- Label in uppercase (Label style)
- Value in Metric style, colour depends on meaning (teal for primary metric, slate for secondary, amber for warnings)

### Data Tables

- Header row: paper background, uppercase labels, 2px bottom border
- Data rows: 1px bottom border (#F0F0EB), hover state (#FAFAF7)
- Numbers right-aligned, tabular-nums
- Badges for data quality: teal (high), amber (medium), red (low)

### Scope Breakdown Bar

- Stacked horizontal bar, 14px height, 7px border-radius
- Scope 1 slate, Scope 2 teal, Scope 3 amber
- Legend below with coloured dots (3px border-radius squares)

## Design Principles

1. **Let the data breathe** — generous whitespace, don't crowd metrics
2. **Hierarchy over decoration** — size, weight, and colour create hierarchy; no ornamental elements
3. **Consistent colour semantics** — teal always means "brand/positive," amber always means "attention," red always means "problem"
4. **Tables are first-class** — they carry the audit trail; invest in readable, well-spaced tables
5. **Paper warmth** — the off-white background softens the technical content without sacrificing precision
