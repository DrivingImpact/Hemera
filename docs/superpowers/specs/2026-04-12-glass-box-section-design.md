# Glass Box — Landing Page Section Design

**Date:** 2026-04-12
**Scope:** New section for the Hemera landing page (`dashboard/app/page.tsx`) that makes transparency and methodological rigor a load-bearing sales moment — not a scattered aside.
**Status:** Approved in brainstorm, ready for implementation plan.

---

## Problem

Hemera's biggest competitive differentiator — that every number, finding, and supplier claim is auditable to source — is currently invisible on the landing page:

- The phrase *"No black-box calculations. No unexplained figures"* exists in a single sentence buried in the italic About paragraph at line 745.
- The `Science` section ("Rigorous by design") lists standards (DEFRA, GHG Protocol, ISO 19011, Pedigree Matrix, Monte Carlo) but reads as a compliance badge wall, not as a claim.
- The hero tagline *"Supply chains made transparent"* hints at it but never cashes the cheque.

Competitors (Watershed, Persefoni, Sweep, Plan A, Normative, and similar) all ship opaque numbers behind "proprietary methodology" language. Hemera does the opposite and never says so loudly. This section fixes that.

## Goal

A named, visually distinct section that:
1. Makes the contrast with competitor black boxes explicit and memorable in one hero moment
2. Backs the claim with five concrete proof points, each tied to something Hemera actually does
3. Gives a skeptical buyer (CFO, sustainability lead, auditor) something they can point to when they ask *"how do I know this number is real?"*

Tone: **medium-to-hard competitive contrast.** We don't name names; we do show the delta.

## Placement

`dashboard/app/page.tsx` — new `GlassBox()` section inserted between `Approach()` and `Science()`:

```tsx
<Hero />
<Stats />
<HemeraScope />
<Approach />
<GlassBox />   {/* new */}
<Science />
<Collaboration />
<About />
<CTA />
<Footer />
```

Rationale: `Approach` establishes *how we work* conceptually, `GlassBox` proves it concretely with an evidence-backed example, and `Science` then widens the lens to the academic standards that back the proof. The three sections form a funnel — philosophy → proof → pedigree.

When `GlassBox` ships, the buried "No black-box calculations" sentence in `About` (line 745) should be deleted from that paragraph — the claim now lives in its own section.

## Visual Direction

Dark-background section with a glass-morphism aesthetic that literally renders the "glass box" metaphor. Contrasts with the mostly-light landing page and creates a distinct sales moment.

**Background:** radial gradient from `#1e293b` to `#0f172a` (slate-800 → slate-900), with a subtle 32px grid overlay at ~3% opacity for texture.

**Glass panels:** `backdrop-filter: blur(14px)`, semi-transparent gradients (`rgba(255,255,255,0.06)` to `rgba(255,255,255,0.02)` for neutral panels; `rgba(20,184,166,0.18)` to `rgba(255,255,255,0.04)` for the hero Hemera panel), thin `rgba(255,255,255,0.1–0.4)` borders, inset highlight via `inset 0 1px 0 rgba(255,255,255,0.28)`, outer glow via `0 0 50px rgba(20,184,166,0.22)` on accent panels only.

**Accent colour:** teal-300 `#5eead4` for the Hemera-side highlights, teal-500 `#14b8a6` for kicker/label chrome — consistent with the rest of the landing page.

**Black-box treatment:** pure `#000` background, `rgba(255,255,255,0.08)` border, low-opacity white text. The point is to look slightly sad next to the glowing Hemera panel.

## Content

### Kicker

Small teal pill, upper-left of the section.

> **THE GLASS BOX**

### Headline

Two lines, 44px (desktop) / 32–36px (mobile), 800 weight, letter-spacing −0.8px. Second line in teal-300.

> **Most platforms hand you a number.**
> **We hand you the evidence behind it.**

### Subhead

Max-width ~680px, 16px, 60–65% white opacity.

> Click any figure in a Hemera report and see what's underneath — the exact emission factor, the statistical confidence interval, the public registry link, the analyst who signed off on it. No "proprietary methodology." No "trust us." Just evidence.

### Hero comparison

Three-column grid (`1fr auto 1fr`) directly under the subhead. Max-width ~820px. On mobile, stacks vertically.

**Left — "Typical platform" (black box)**
- Label: `Typical platform` (uppercase, tracked, 40% white)
- Centered figure: `1,234` in 48px 800-weight, `tCO₂e` in 12px muted
- Footer line, italic, 30% white:
  > *"DEFRA-aligned methodology"*
  > *(trust us)*

**Divider:** small `VS` label between the two columns with thin vertical gradient lines above and below.

**Right — "Hemera" (glass box)**
- Label: `Hemera` (uppercase, tracked, teal-300)
- Headline value: `1,234 ± 4.2%` — number in white, uncertainty in teal-300
- Sub-line: `tCO₂e · 95% confidence interval`
- Detail block (monospace, 10px, 75% white, aligned key/value pairs):
  ```
  factor    DEFRA '24 · HGV Artic.
  method    Monte Carlo simulation
  quality   Pedigree 2.1 / 5
  source    defra.gov.uk/ghg-2024
  verified  J.Martin, 12 Apr 2026
  ```
  The `source` URL and `verified` value are teal-300; key labels are 38% white.

The example numbers are placeholders for a real figure from a real Hemera report. Before launch, replace with an actual anonymised example that we're confident defending.

### Proof tiles

Section label above the grid: **WHAT'S INSIDE EVERY HEMERA NUMBER** (uppercase, tracked, 40% white, 11px).

Five-column responsive grid (5 → 3 → 2 → 1 on narrowing viewports). Each tile is a small glass card with:
- 2-digit index in teal-300, 800-weight, 18px
- Title in white, 13px, 700-weight
- Body in 55% white, 11px, line-height 1.5

**01 — The exact factor**
> Every number tells you which DEFRA factor produced it, with a direct link to the published government reference.

**02 — Quantified uncertainty**
> Every figure carries a 95% confidence interval — the same statistical bar used in peer-reviewed climate science. An analyst validates the inputs before we stamp that confidence on them.

**03 — Traceable sources**
> We won't make a supplier claim you can't trace. Every finding links to its public registry — Companies House, HSE, SBTi, CDP, Environment Agency.

**04 — Analyst challenged**
> Our purpose-trained research AI does the heavy lifting at scale. But every assumption it makes is then pushed back on by a Hemera analyst — who weighs the evidence and decides whether to stand by the finding, soften it, or throw it out.

**05 — Gaps you can act on**
> Every data point is scored. You see which numbers are solid, where better inputs would tighten your footprint, and what we honestly can't know about your supply chain yet.

## Component Structure

Single function component in `dashboard/app/page.tsx`, following the existing pattern (`Hero`, `Stats`, `HemeraScope`, `Approach`, `Science`, etc.):

```tsx
function GlassBox() {
  const { ref, inView } = useInView(0.15);
  // ...
}
```

Use the existing `useInView` hook for entry animations (fade + translateY, staggered delays — same pattern as `Science`).

Suggested internal layout: one outer `<section>`, max-width-1100px inner container, and three subcomponents in sequence:
1. Header block (kicker + headline + subhead)
2. `<ComparisonPanels>` (BlackBox + VS + GlassBox)
3. `<ProofTiles>` (label + 5-column grid)

These can be inlined or factored — match whatever the existing sections do. No new files required.

## Responsive Behaviour

- **Hero comparison:** 3-column grid on ≥768px; stacks vertically on <768px. The `VS` divider becomes a horizontal line with the `VS` label centered.
- **Proof tiles:** 5 cols ≥1024px; 3 cols 768–1023px (with the last two wrapping); 2 cols 480–767px; 1 col <480px.
- **Headline:** 44px desktop, 32px tablet, 28px mobile.
- **Section padding:** 72px top / 80px bottom desktop; 48px / 56px mobile.

## Animation

Match existing landing-page motion language: `cubic-bezier(0.16, 1, 0.3, 1)` easing, 0.8s duration, 20–30px `translateY` on entry, staggered delays (header → comparison → tiles) of roughly 100ms each.

No hover animations on tiles in v1 — the section is already rich enough. Optional micro-interaction for v2: when a user hovers the glass panel, the detail rows subtly highlight sequentially (defer for now).

## Out of Scope

- **Clickable drill-down.** The subhead promises *"click any figure and see what's underneath"* — this is a real HemeraScope/report feature, not a landing-page interaction. Copy aspirationally describes what the product does; we don't build a click-to-reveal widget on the landing page.
- **Real report data.** Placeholder numbers (`1,234`, `± 4.2%`, `J.Martin`) are sufficient for v1. Real anonymised example can replace them in a follow-up pass.
- **Removing the About-section sentence.** The buried *"No black-box calculations"* sentence at `page.tsx:745` should be deleted when this section ships — treat as a single-line cleanup inside the same implementation plan, not a separate effort.
- **Competitor screenshots or named comparisons.** Medium-to-hard contrast only — we never name names or show competitor UI.
- **New assets, icons, or imagery.** Everything is CSS + type.

## Success Criteria

1. A first-time visitor who lands on `hemera-nx8p.vercel.app`, scrolls to the Glass Box section, and reads only the headline + hero comparison can articulate Hemera's differentiator in one sentence.
2. A skeptical sustainability lead scrolling through the proof tiles can cite at least two specific things Hemera does that competitors don't.
3. The About-section sentence at `page.tsx:745` is removed as part of the same change.
4. Section renders correctly at 1440px, 1024px, 768px, and 375px widths.
5. Section is keyboard-navigable and passes baseline Lighthouse accessibility.

## References

- Current landing page: `dashboard/app/page.tsx` (928 lines)
- Related section structure: `Science()` at line 576 (layout pattern), `Approach()` at line 426 (section rhythm), `About()` at line 717 (sentence to delete after ship)
- Brainstorm artifacts (for visual reference, not committed): `.superpowers/brainstorm/*/content/glass-box-section-v3.html`
