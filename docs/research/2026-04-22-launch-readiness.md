# HemeraScope — Launch Readiness & Certifications Roadmap

**Last updated:** 2026-04-22
**Status:** ~70% ready. Main blockers are company details, ICO registration, and cookie consent.

---

## Part 1: Before Going Public (Blockers)

These must be done before hemerascope.com is shared with anyone outside the team.

### 1.1 Company Details — Fill All Placeholders

Every `[pending]` in the codebase needs a real value. There are **~25 instances** across 10 files.

**What you need:**

| Detail | Where to get it | Used in |
|--------|----------------|---------|
| Companies House number | companies-house.gov.uk (your registration) | Privacy, Terms, Legal footer, Landing footer |
| Registered office address | Your Companies House registration | Privacy, Terms, Legal footer, Landing footer |
| ICO registration number | After paying the ICO fee (see 1.2) | Privacy, Legal footer, Security page, Landing footer |
| Privacy email | Set up after domain DNS is configured (e.g. privacy@hemerascope.com) | Privacy page (x2), Sub-processor page |
| Security email | Same (e.g. security@hemerascope.com) | Security page (x2), security.txt |
| Accessibility email | Same (e.g. accessibility@hemerascope.com) | Accessibility page |
| Whistleblowing email | Same (e.g. ethics@hemerascope.com) | Modern Slavery page |
| Effective date | Set when solicitor approves, or set to publication date | All 8 legal pages |
| Founder name for Modern Slavery signature | Your name | Modern Slavery page |
| Trust page URL | Will be /legal/security once live | Privacy page |
| Cyber Essentials expected date | After booking assessment | Security page |
| Terms payment clause | Your invoicing terms (e.g. "Net 30, GBP, VAT inclusive") | Terms page line 59 |

**Once you have these, give them to Claude and all 25 placeholders get filled in one commit.**

### 1.2 ICO Data Protection Registration

**Required by law** for any UK organisation processing personal data.

- **Go to:** ico.org.uk/for-organisations/register
- **Cost:** £40/year (Tier 1, under 10 staff, under £632k turnover) or £60/year (Tier 2)
- **Time:** ~10 minutes online, registration number issued within days
- **You need this before launch** — the number goes in Privacy, Legal footer, Security page, and Landing footer

### 1.3 Cookie Consent Banner

**Status:** NOT IMPLEMENTED — this is a legal blocker.

The UK PECR (Privacy and Electronic Communications Regulations) and the Data (Use and Access) Act 2025 require explicit consent before setting non-essential cookies. You have a cookie policy page but no actual consent UI.

**What's needed:**
- A banner/modal on first visit asking for consent
- Options: "Accept all", "Reject non-essential", "Manage preferences"
- Store the user's choice in a `hemera_consent` cookie (already referenced in cookie policy)
- Block non-essential cookies until consent is given

**Options:**
- **Build it** — simple banner component, ~2 hours, no external dependency
- **CookieYes** (cookieyes.com) — managed solution, free tier for small sites, handles PECR compliance
- **Osano** — similar managed solution

**Recommendation:** Build a simple one. You currently run zero analytics or advertising cookies — Clerk's session cookie is essential (doesn't need consent). The banner is mostly about future-proofing and showing compliance.

### 1.4 Solicitor Review

**Status:** Drafts ready, not reviewed.

Send to a UK solicitor who knows GDPR/data protection for SaaS:
- Privacy Policy — especially the anonymised supplier retention clause (Recital 26)
- Terms & Conditions — especially the 12-month liability cap
- Data Processing Agreement — referenced but not drafted as a standalone doc
- Cookie Statement — PECR/DUAA compliance

**Estimated cost:** £500-2,000 for a review of all four.
**Timeline:** 1-2 weeks turnaround.

### 1.5 Domain & Email Setup

- **Domain:** hemerascope.com (registered — confirm DNS is pointing to Vercel)
- **Email forwarding:** Set up privacy@, security@, accessibility@, ethics@ — either via Cloudflare Email Routing (free) or Google Workspace
- **Clerk:** Add hemerascope.com to allowed domains in Clerk dashboard
- **Render webhook:** Ensure Clerk webhook URL is set to `https://your-render-url.onrender.com/api/webhooks/clerk`

### 1.6 Favicon & Social Sharing

**Status:** MISSING — no favicon, no og:image, no og:title/description meta tags.

Before sharing the URL publicly:
- Design a favicon (the teal Hemera "H" or HemeraScope wordmark)
- Create an og:image (1200x630px) for social sharing previews
- Add meta tags to the root layout

### 1.7 robots.txt & Sitemap

**Status:** MISSING

- `robots.txt` — controls search engine crawling. At minimum: allow all, link to sitemap
- `sitemap.xml` — lists all public pages for SEO. Next.js can auto-generate this

---

## Part 2: Launch Week (High Priority)

These should be done in the first week after going public.

### 2.1 Visual Testing

The following UI areas have never been tested in a browser:

- [ ] Upload data-type picker on mobile (narrow screens)
- [ ] Legal page tables on mobile
- [ ] Client queue email pill wrapping
- [ ] New admin suppliers page (search, filters, CH lookup)
- [ ] Supplier detail page (AI Intelligence cards, enrichment layers)
- [ ] Admin bin page (restore, permanent delete)
- [ ] Emission factor verification modal
- [ ] Excel export button + downloaded file
- [ ] Landing page video placeholder (functional? remove?)
- [ ] Cookie consent banner (once built)

### 2.2 Activity Data End-to-End Test

Upload a real activity dataset (kWh, km, tonnes) and verify:
- [ ] Parser detects activity columns
- [ ] Calculator finds matching DEFRA 2025 activity factors
- [ ] Carbon calculation completes
- [ ] Results display correctly on dashboard

### 2.3 Vercel Environment Variables

Confirm these are set in Vercel project settings:
- `NEXT_PUBLIC_API_URL` → your Render backend URL
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` → your Clerk publishable key
- `CLERK_SECRET_KEY` → your Clerk secret key

### 2.4 Render Environment Variables

Confirm these are set in Render:
- `DATABASE_URL` → your PostgreSQL connection string
- `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `CLERK_WEBHOOK_SECRET`
- `ANTHROPIC_API_KEY`
- `COMPANIES_HOUSE_API_KEY`

### 2.5 Remove Old Preview Domains from CORS

Once live on hemerascope.com, consider removing the old Vercel preview URLs from the CORS allowlist in `hemera/main.py` to tighten security.

---

## Part 3: Certifications & Compliance Roadmap

### Immediate (This Week)

| Action | Cost | Time | Why |
|--------|------|------|-----|
| **ICO Data Protection Fee** | £40-60/year | 10 min to apply, days to process | Legally required. Gives you the registration number for all legal pages. |
| **Enable MFA everywhere** | £0 | 1 hour | Required for Cyber Essentials. Enable on: GitHub, Vercel, Render, Clerk dashboard, Cloudflare, all email accounts. |
| **Run dependency audits** | £0 | 15 min | `pip audit` and `npm audit`. Fix any known vulnerabilities. Required within 14 days for CE. |

### Month 1 (Weeks 2-4)

| Action | Cost | Time | Why |
|--------|------|------|-----|
| **Cyber Essentials certification** | ~£320+VAT | 2-6 weeks | Highest trust-per-pound UK certification. Self-assessment questionnaire (~80 questions). Use CyberSmart (cybersmart.co.uk) for guided process. |
| **UNGC Participant application** | £0 (under $1M revenue) | 2 hours to apply | Yields "We Support the UN Global Compact" logo. CEO signs commitment letter. Annual Communication on Progress required. |
| **Data Processing Agreement** | £0 (template) + solicitor review | 1-2 weeks | Standalone DPA for clients. Can use a standard template; solicitor should review. Referenced in T&Cs but not yet drafted. |

### Month 2-3

| Action | Cost | Time | Why |
|--------|------|------|-----|
| **Cyber Essentials Plus** | ~£1,500-2,500 | 2-4 weeks after CE | Technical audit on top of self-assessment. Required for some government contracts. |
| **CDP Accredited Solutions Provider** | Application fee varies | 4-8 weeks | If you want to work with CDP-reporting companies. Formal application required. |
| **Begin B Impact Assessment** | Free to assess | 12-month journey | B Corp certification is a long process (~£500-25k to certify depending on size). Start the free assessment now to understand the gap. |

### Month 4-6

| Action | Cost | Time | Why |
|--------|------|------|-----|
| **ISO 27001 readiness assessment** | £2,000-5,000 | 2-4 weeks | Gap analysis before full certification. Only pursue if enterprise clients require it. |
| **SOC 2 Type I** | £15,000-40,000 | 3-6 months | Only if US enterprise clients require it. Very expensive for early stage. |
| **Methodology disclosure review** | £0 | 1-2 hours | Update /legal/methodology with any new enrichment layers, factor sources, or QC changes. |

### Deferred (6+ months)

| Action | Cost | Time | Why |
|--------|------|------|-----|
| **ISO 27001 full certification** | £6,000-25,000+ | 6-12 months | Gold standard for information security. Requires documented ISMS. |
| **SOC 2 Type II** | £15,000-80,000 | 6-12 months | Requires 3-6 months of operational evidence after Type I. |
| **B Corp certification** | £500-25,000 | 12-18 months from start | Full assessment + verification. Yields the B Corp logo. |
| **SBTi commitment** | £0 to commit, varies to validate | 6-24 months | Only relevant if Hemera sets its own science-based targets (not just helping clients). |

---

## Part 4: Logos & Trust Signals — What You CAN Display

### Safe to display now (text-only, no logos)

These are legitimate alignment claims you can make today:

- "GHG Protocol-aligned reporting"
- "ISO 14064-1 compatible methodology"
- "TCFD-aligned disclosure framework"
- "DEFRA GHG Conversion Factors (current year)"
- "ISO 19011-inspired quality control"
- "ISO 14044 Pedigree Matrix uncertainty scoring"
- "UK GDPR compliant"

**Format:** Text statements on landing page, methodology page, and reports. No logos.

### Logos you can earn (with action)

| Logo | How to get it | Timeline |
|------|---------------|----------|
| **Cyber Essentials badge** | Pass self-assessment | 2-6 weeks |
| **Cyber Essentials Plus badge** | Pass technical audit | 2-4 weeks after CE |
| **UNGC "We Support" logo** | Submit participant application | 2-4 weeks |
| **ICO registered badge** | Pay the fee | Days |
| **B Corp logo** | Complete full assessment + verification | 12-18 months |

### Logos you CANNOT display (brand protection)

Do NOT display these logos without formal certification/partnership:
- SBTi (Science Based Targets initiative)
- CDP
- GRI (Global Reporting Initiative)
- TCFD
- GHG Protocol
- ISO (any standard)
- FSC, MSC, Rainforest Alliance

**All of these have brand-protection policies.** Displaying them without authorisation is an own-goal in front of exactly the buyers HemeraScope targets.

---

## Part 5: Quick Reference — Pending Values Needed

When you have these, give them to Claude for a one-pass fill:

```
Company number:        _______________
Registered address:    _______________
ICO registration:      _______________
Privacy email:         _______________
Security email:        _______________
Accessibility email:   _______________
Whistleblowing email:  _______________
Founder name:          _______________
Effective date:        _______________
CE expected date:      _______________
Payment terms:         _______________
```

---

## Part 6: Ongoing Compliance Calendar

| Frequency | Action |
|-----------|--------|
| **Every 14 days** | Check for security patches: `pip audit`, `npm audit`, OS updates |
| **Monthly** | Review sub-processor list — notify clients 30 days before adding new ones |
| **Quarterly** | Review and update legal pages (dates, sub-processors, policy changes) |
| **Annually** | Renew ICO registration (~£40-60) |
| **Annually** | Renew Cyber Essentials certification (~£320+VAT) |
| **Annually** | Submit UNGC Communication on Progress (if participant) |
| **Annually** | Review DEFRA conversion factors — new set published each June |
| **As needed** | DPIA (Data Protection Impact Assessment) before new data processing activities |
| **As needed** | Update security.txt expiry date (currently set to 2027-04-22) |
